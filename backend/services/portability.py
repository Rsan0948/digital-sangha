"""User data portability: export everything to a single ZIP, restore from it.

The export is intentionally **decrypted**: ``data/encryption.key`` already
lives plaintext on the user's disk, so encrypting bundle contents under that
key provides no meaningful protection. Spotify access/refresh tokens are
stored encrypted on disk; this module decrypts them into the export so the
bundle is portable across machines that may be using a different key, and
re-encrypts on import using whatever key is in effect at restore time.

The bundle is meant to be kept private by the user, same as ``data/``.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import typing
import zipfile
from datetime import date, datetime, time
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import delete
from sqlmodel import Session, select

from backend.config import CONFIG_PATH
from backend.models import (
    Assessment,
    ClassSession,
    Flow,
    FlowTheme,
    FlowVersion,
    GeneratedPlaylist,
    Playlist,
    PlaylistTrack,
    Pose,
    PoseFollowup,
    SpotifyAuth,
    Sutra,
    TalkingPoint,
    Theme,
    Track,
)
from backend.services.encryption import KEY_PATH, decrypt, encrypt

EXPORT_SCHEMA_VERSION = 1
APP_VERSION = "1.0.0"

# Hard cap on import bundle size. Rejected upfront before any zip parsing so a
# crafted oversized payload cannot exhaust memory in zipfile internals.
MAX_IMPORT_BUNDLE_BYTES = 50 * 1024 * 1024

# Files we recognize on import; anything else is rejected to keep the attack
# surface as narrow as the export format itself.
_ALLOWED_BUNDLE_ENTRIES = frozenset(
    {"manifest.json", "data.json", "transition_guides.json", "encryption.key"}
)

# Matches a Windows drive prefix like "C:" so we can reject absolute Windows
# paths even when the archive is opened on POSIX.
_WIN_DRIVE_RE = re.compile(r"^[A-Za-z]:")

GUIDE_PATH = CONFIG_PATH.parent / "data" / "transition_guides.json"


def _validate_bundle_entry(name: str) -> None:
    """Reject zip entry names that could escape the bundle's logical root.

    Raises ``ValueError`` on the first sign of path traversal so the caller
    aborts the entire import rather than silently skipping suspicious entries.
    """
    if not name or name.endswith("/"):
        raise ValueError(f"import bundle rejected: directory or empty entry not allowed ({name!r})")
    if "\x00" in name:
        raise ValueError("import bundle rejected: NUL byte in entry name")
    if name.startswith("/") or name.startswith("\\") or _WIN_DRIVE_RE.match(name):
        raise ValueError(f"import bundle rejected: absolute path entry ({name!r})")
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if any(part == ".." for part in parts):
        raise ValueError(f"import bundle rejected: parent-traversal entry ({name!r})")
    safe_root = PurePosixPath("/__yc_import_root__")
    candidate = safe_root / normalized
    try:
        candidate.relative_to(safe_root)
    except ValueError as exc:
        raise ValueError(f"import bundle rejected: entry escapes root ({name!r})") from exc
    if name not in _ALLOWED_BUNDLE_ENTRIES:
        raise ValueError(f"import bundle rejected: unexpected entry ({name!r})")


# Tables ordered parents-first so import can ``add_all`` in this order without
# tripping foreign keys; export uses the same order for stable diffability.
_TABLES: list[type] = [
    Pose,
    Theme,
    Sutra,
    Track,
    Playlist,
    Flow,
    FlowVersion,
    FlowTheme,
    PoseFollowup,
    PlaylistTrack,
    TalkingPoint,
    ClassSession,
    Assessment,
    SpotifyAuth,
    GeneratedPlaylist,
]


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, bytes):
        return {"__bytes_b64__": base64.b64encode(value).decode("ascii")}
    return value


def _serialize_row(row: Any, model: type) -> dict:
    raw = row.model_dump()
    if model is SpotifyAuth:
        access_enc = raw.pop("access_token_enc", None)
        refresh_enc = raw.pop("refresh_token_enc", None)
        out: dict[str, Any] = {k: _json_safe(v) for k, v in raw.items()}
        out["access_token"] = decrypt(access_enc) if access_enc else None
        out["refresh_token"] = decrypt(refresh_enc) if refresh_enc else None
        return out
    return {k: _json_safe(v) for k, v in raw.items()}


def _coerce(value: Any, annotation: Any) -> Any:
    if value is None:
        return None
    base = annotation
    args = typing.get_args(annotation)
    if args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            base = non_none[0]
    if base is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    if base is date and isinstance(value, str):
        return date.fromisoformat(value)
    if base is time and isinstance(value, str):
        return time.fromisoformat(value)
    if base is bytes and isinstance(value, dict) and "__bytes_b64__" in value:
        return base64.b64decode(value["__bytes_b64__"])
    return value


def _deserialize_row(data: dict, model: type) -> dict:
    fields = model.model_fields
    if model is SpotifyAuth:
        access = data.pop("access_token", None)
        refresh = data.pop("refresh_token", None)
        kwargs: dict[str, Any] = {}
        for k, v in data.items():
            if k in fields:
                kwargs[k] = _coerce(v, fields[k].annotation)
        if access:
            kwargs["access_token_enc"] = encrypt(access)
        if refresh:
            kwargs["refresh_token_enc"] = encrypt(refresh)
        return kwargs

    kwargs = {}
    for k, v in data.items():
        if k in fields:
            kwargs[k] = _coerce(v, fields[k].annotation)
    return kwargs


def build_export(session: Session) -> bytes:
    """Collect all user-data tables + transition guides + encryption key."""
    data: dict[str, list[dict]] = {}
    counts: dict[str, int] = {}
    for model in _TABLES:
        rows = session.exec(select(model)).all()
        table_name = model.__tablename__
        data[table_name] = [_serialize_row(r, model) for r in rows]
        counts[table_name] = len(rows)

    guides_text = GUIDE_PATH.read_text() if GUIDE_PATH.exists() else "{}"
    key_bytes = KEY_PATH.read_bytes() if KEY_PATH.exists() else None

    manifest = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "table_counts": counts,
        "files": {
            "data.json": True,
            "transition_guides.json": True,
            "encryption.key": key_bytes is not None,
        },
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("data.json", json.dumps(data, indent=2))
        zf.writestr("transition_guides.json", guides_text)
        if key_bytes is not None:
            zf.writestr("encryption.key", key_bytes)
    return buf.getvalue()


def apply_import(zip_bytes: bytes, session: Session) -> dict:
    """Replace local data with the contents of an export bundle.

    Returns ``{"applied": {<table>: count}, "warnings": [str, ...]}``.
    Raises ``ValueError`` for unrecoverable bundle problems (missing
    manifest, schema version mismatch, malformed zip, oversize bundle, or
    any zip entry that would escape the bundle's logical root).
    """
    if len(zip_bytes) > MAX_IMPORT_BUNDLE_BYTES:
        raise ValueError(
            f"import bundle rejected: size {len(zip_bytes)} exceeds "
            f"{MAX_IMPORT_BUNDLE_BYTES}-byte cap"
        )

    warnings: list[str] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"not a valid zip archive: {exc}") from exc

    # Validate every entry name BEFORE reading any payload. First bad entry
    # aborts the whole import so we never silently skip a malicious bundle.
    for info in zf.infolist():
        _validate_bundle_entry(info.filename)

    names = set(zf.namelist())
    if "manifest.json" not in names:
        raise ValueError("bundle is missing manifest.json")

    try:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"manifest.json is unreadable: {exc}") from exc

    schema = manifest.get("schema_version")
    if not isinstance(schema, int) or schema != EXPORT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported export schema_version={schema}; "
            f"this build expects {EXPORT_SCHEMA_VERSION}"
        )

    if "data.json" not in names:
        raise ValueError("bundle is missing data.json")
    try:
        data = json.loads(zf.read("data.json").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"data.json is unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("data.json is not a JSON object")

    # Replace encryption.key BEFORE re-encrypting Spotify tokens, so any tokens
    # in the bundle are interpreted with the bundle's key on the way in.
    if "encryption.key" in names:
        key_bytes = zf.read("encryption.key")
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        KEY_PATH.write_bytes(key_bytes)
        os.chmod(KEY_PATH, 0o600)

    # Wipe existing rows in reverse FK order, then insert new ones in forward order.
    for model in reversed(_TABLES):
        session.execute(delete(model))
    session.flush()

    applied: dict[str, int] = {}
    for model in _TABLES:
        table_name = model.__tablename__
        rows = data.get(table_name, [])
        if not isinstance(rows, list):
            warnings.append(f"{table_name}: skipped (expected list, got {type(rows).__name__})")
            applied[table_name] = 0
            continue
        instances = []
        for row_data in rows:
            if not isinstance(row_data, dict):
                warnings.append(f"{table_name}: row skipped (not a dict)")
                continue
            try:
                kwargs = _deserialize_row(dict(row_data), model)
                instances.append(model(**kwargs))
            except (TypeError, ValueError) as exc:
                warnings.append(f"{table_name}: row skipped ({exc})")
        session.add_all(instances)
        applied[table_name] = len(instances)
    session.commit()

    if "transition_guides.json" in names:
        try:
            guides_text = zf.read("transition_guides.json").decode("utf-8")
        except UnicodeDecodeError as exc:
            warnings.append(f"transition_guides.json: skipped ({exc})")
        else:
            GUIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = GUIDE_PATH.with_suffix(".json.tmp")
            tmp.write_text(guides_text)
            os.replace(tmp, GUIDE_PATH)

    return {"applied": applied, "warnings": warnings}
