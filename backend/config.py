from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class Settings(BaseSettings):
    db_path: str = "data/sangha.db"
    vector_db_path: str = "data/vectors"

    @property
    def absolute_db_path(self) -> Path:
        p = Path(self.db_path)
        if p.is_absolute():
            return p
        return CONFIG_PATH.parent / self.db_path

    @property
    def absolute_vector_path(self) -> Path:
        p = Path(self.vector_db_path)
        if p.is_absolute():
            return p
        return CONFIG_PATH.parent / self.vector_db_path

    # LLM Configuration
    llm_provider: str = "local"  # local, openai, anthropic, google, deepseek
    fast_model: str = ""
    power_model: str = ""

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""
    custom_api_base: str = ""

    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/api/spotify/callback"
    frontend_url: str = "http://localhost:5173"
    encryption_key: str = ""
    configured: bool = False
    data_loaded: bool = False

    class Config:
        env_file = ".env"
        # Tolerate legacy keys from older config.yaml versions (e.g. discord_token).
        extra = "ignore"


def load_config() -> Settings:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
        return Settings(**data)
    return Settings()


def save_config(settings: dict):
    existing = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            existing = yaml.safe_load(f) or {}
    existing.update(settings)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(existing, f)


settings = load_config()
