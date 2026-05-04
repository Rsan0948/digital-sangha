from sqlmodel import SQLModel, create_engine, Session
from backend.config import settings

settings.absolute_db_path.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{settings.absolute_db_path}"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def init_db():
    from backend.models import pose, flow, session, track, theme, assessment, spotify

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
