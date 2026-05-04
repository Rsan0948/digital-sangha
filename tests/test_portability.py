import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


def _setup_paths(monkeypatch: pytest.MonkeyPatch, tmp_data_dir: Path) -> None:
    """Re-point GUIDE_PATH and KEY_PATH at a tmp dir so tests stay isolated."""
    from backend.services import encryption, portability

    monkeypatch.setattr(portability, "GUIDE_PATH", tmp_data_dir / "transition_guides.json")
    monkeypatch.setattr(portability, "KEY_PATH", tmp_data_dir / "encryption.key")
    monkeypatch.setattr(encryption, "KEY_PATH", tmp_data_dir / "encryption.key")


def _fresh_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import backend.models  # noqa: F401 - registers SQLModel metadata

    SQLModel.metadata.create_all(engine)
    return engine


def _build_bundle_with_entry(entry_name: str, payload: bytes = b"x") -> bytes:
    """Construct a zip whose first entry has ``entry_name`` and includes a
    valid manifest so any rejection in apply_import is attributable to the
    entry name itself, not to a missing manifest.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        zf.writestr(entry_name, payload)
        zf.writestr(
            "manifest.json",
            json.dumps({"schema_version": 1, "table_counts": {}}),
        )
        zf.writestr("data.json", "{}")
    return buf.getvalue()


def test_export_bundle_structure(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.models import Flow
    from backend.services import portability

    with Session(test_engine) as session:
        session.add(Flow(flow_name="Sun A"))
        session.add(Flow(flow_name="Moon B"))
        session.commit()

    with Session(test_engine) as session:
        zip_bytes = portability.build_export(session)

    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = z.namelist()
    assert "manifest.json" in names
    assert "data.json" in names
    assert "transition_guides.json" in names

    manifest = json.loads(z.read("manifest.json"))
    assert manifest["schema_version"] == portability.EXPORT_SCHEMA_VERSION
    assert manifest["table_counts"]["flow"] == 2


def test_export_decrypts_spotify_tokens(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.models import SpotifyAuth
    from backend.services import encryption, portability

    # Generate a fresh Fernet key in tmp_data_dir.
    encryption.get_fernet()

    access_enc = encryption.encrypt("access-token-secret")
    refresh_enc = encryption.encrypt("refresh-token-secret")

    with Session(test_engine) as session:
        session.add(
            SpotifyAuth(
                id=1,
                access_token_enc=access_enc,
                refresh_token_enc=refresh_enc,
                expires_at=datetime(2026, 1, 1),
                user_id="user-1",
            )
        )
        session.commit()

    with Session(test_engine) as session:
        zip_bytes = portability.build_export(session)

    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    data = json.loads(z.read("data.json"))
    rows = data["spotifyauth"]
    assert len(rows) == 1
    row = rows[0]
    assert row["access_token"] == "access-token-secret"
    assert row["refresh_token"] == "refresh-token-secret"
    assert "access_token_enc" not in row
    assert "refresh_token_enc" not in row


def test_export_includes_encryption_key(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.services import portability

    key_bytes = b"ZmFrZS1mZXJuZXQta2V5LWZvci10ZXN0aW5nLW9ubHk="
    (tmp_data_dir / "encryption.key").write_bytes(key_bytes)

    with Session(test_engine) as session:
        zip_bytes = portability.build_export(session)

    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert "encryption.key" in z.namelist()
    assert z.read("encryption.key") == key_bytes

    manifest = json.loads(z.read("manifest.json"))
    assert manifest["files"]["encryption.key"] is True


def test_import_roundtrip(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.models import Flow
    from backend.services import portability

    src_engine = _fresh_engine()
    dst_engine = _fresh_engine()

    with Session(src_engine) as session:
        session.add(
            Flow(
                flow_id="abc-123",
                flow_name="Roundtrip Flow",
                description="hello",
            )
        )
        session.commit()

    with Session(src_engine) as session:
        zip_bytes = portability.build_export(session)

    with Session(dst_engine) as session:
        result = portability.apply_import(zip_bytes, session)

    assert result["applied"]["flow"] == 1
    assert result["warnings"] == []

    with Session(dst_engine) as session:
        flows = session.exec(select(Flow)).all()
        assert len(flows) == 1
        assert flows[0].flow_id == "abc-123"
        assert flows[0].flow_name == "Roundtrip Flow"
        assert flows[0].description == "hello"


def test_import_rejects_schema_mismatch(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.services import portability

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps({"schema_version": 99, "table_counts": {}}),
        )
        zf.writestr("data.json", "{}")

    with Session(test_engine) as session, pytest.raises(ValueError, match="schema_version"):
        portability.apply_import(buf.getvalue(), session)


def test_import_rejects_missing_manifest(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.services import portability

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        zf.writestr("data.json", "{}")

    with Session(test_engine) as session, pytest.raises(ValueError, match="manifest"):
        portability.apply_import(buf.getvalue(), session)


def test_import_rejects_zip_slip(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bundle entry whose name uses ``..`` to climb out of the zip root must
    be rejected before any payload is read. Regression for CVE-shape ZIP slip.
    """
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.services import portability

    bundle = _build_bundle_with_entry("../etc/passwd")
    with Session(test_engine) as session, pytest.raises(ValueError, match="parent-traversal"):
        portability.apply_import(bundle, session)


def test_import_rejects_absolute_path(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Absolute-path entries (POSIX or Windows-drive) must also be rejected."""
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.services import portability

    bundle = _build_bundle_with_entry("/tmp/evil")
    with Session(test_engine) as session, pytest.raises(ValueError, match="absolute path"):
        portability.apply_import(bundle, session)


def test_import_rejects_oversized_bundle(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bundles larger than ``MAX_IMPORT_BUNDLE_BYTES`` are rejected upfront,
    before any zip parsing happens, to avoid memory exhaustion attacks.
    """
    _setup_paths(monkeypatch, tmp_data_dir)
    from backend.services import portability

    payload = b"\0" * (portability.MAX_IMPORT_BUNDLE_BYTES + 1)
    with Session(test_engine) as session, pytest.raises(ValueError, match="exceeds"):
        portability.apply_import(payload, session)
