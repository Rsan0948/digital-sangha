import contextlib
import os
from collections.abc import Iterator

from cryptography.fernet import Fernet

from backend.config import CONFIG_PATH

KEY_PATH = CONFIG_PATH.parent / "data" / "encryption.key"


@contextlib.contextmanager
def _restrictive_umask() -> Iterator[None]:
    """Force created files to be owner-only for the duration of the block."""
    prev = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(prev)


def _atomic_write_key(key: bytes) -> None:
    """Write the encryption key with no world-readable window.

    Using a tmp file + ``os.replace`` keeps the visible ``KEY_PATH`` either
    absent or fully written; chmod-on-tmp before replace closes the gap where
    a previous version of this code created the file under the default umask
    and only locked it down on the next line.
    """
    tmp_path = KEY_PATH.with_suffix(".key.tmp")
    with _restrictive_umask():
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        # KEY_PATH is a module-level constant derived from CONFIG_PATH, never
        # user input; the os.open call is safe from path traversal.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(tmp_path, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(key)
                fh.flush()
                os.fsync(fh.fileno())
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                tmp_path.unlink()
            raise
        # Belt-and-braces: enforce 0o600 on the tmp before publishing it,
        # in case the platform's open() did not honor the requested mode.
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, KEY_PATH)


def _load_or_create_key() -> bytes:
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes().strip()

    try:
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        _atomic_write_key(key)
        return key
    except OSError as exc:
        raise RuntimeError(f"unable to read or create encryption key at {KEY_PATH}: {exc}") from exc


def get_fernet() -> Fernet:
    key = _load_or_create_key()
    return Fernet(key)


def encrypt(data: str) -> bytes:
    return get_fernet().encrypt(data.encode())


def decrypt(data: bytes) -> str:
    return get_fernet().decrypt(data).decode()
