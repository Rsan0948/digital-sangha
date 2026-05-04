import sys
import types
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock


def _stub_heavy_ml() -> None:
    # Pre-stub chromadb + sentence_transformers before backend.* loads them
    # transitively (via backend.services.vector_store, imported by
    # config_wizard / library / poses / flow_agent / feedback / archivist).
    # Without this, the real sentence_transformers import probes HuggingFace
    # Hub and hangs in offline test environments. Tests do not exercise
    # vector search, so stub modules are sufficient.
    if "chromadb" not in sys.modules:
        chromadb_stub = types.ModuleType("chromadb")
        chromadb_stub.PersistentClient = MagicMock()
        sys.modules["chromadb"] = chromadb_stub
        chromadb_config_stub = types.ModuleType("chromadb.config")
        chromadb_config_stub.Settings = MagicMock()
        sys.modules["chromadb.config"] = chromadb_config_stub
    if "sentence_transformers" not in sys.modules:
        st_stub = types.ModuleType("sentence_transformers")
        st_stub.SentenceTransformer = MagicMock()
        sys.modules["sentence_transformers"] = st_stub


_stub_heavy_ml()


import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def test_engine() -> Iterator:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import backend.models  # noqa: F401 - registers SQLModel metadata

    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(
    test_engine, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    from backend import database, main
    from backend.database import get_session

    monkeypatch.setattr(database, "engine", test_engine)

    import backend.routers.flows as flows_module

    monkeypatch.setattr(flows_module, "GUIDE_PATH", tmp_data_dir / "transition_guides.json")

    def _test_session() -> Iterator[Session]:
        with Session(test_engine) as session:
            yield session

    main.app.dependency_overrides[get_session] = _test_session
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()


def make_response(status_code: int, json_data: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json = MagicMock(return_value=json_data)
    return response


def patch_client_post(monkeypatch: pytest.MonkeyPatch, response: MagicMock) -> None:
    import httpx

    def _fake_post(self, *args, **kwargs):
        return response

    monkeypatch.setattr(httpx.Client, "post", _fake_post)
