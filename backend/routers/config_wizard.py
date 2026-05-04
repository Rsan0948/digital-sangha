from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.config import save_config, load_config
from backend.services.llm_router import list_available_models
from backend.services.vector_store import collection_exists

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    llm_provider: str | None = None
    fast_model: str | None = None
    power_model: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None


@router.get("/status")
def get_config_status():
    cfg = load_config()
    return {
        "configured": bool(
            cfg.fast_model
            or cfg.openai_api_key
            or cfg.anthropic_api_key
            or cfg.google_api_key
            or cfg.deepseek_api_key
        ),
        "llm_provider": cfg.llm_provider,
        "fast_model": cfg.fast_model or None,
        "power_model": cfg.power_model or None,
        "openai_configured": bool(cfg.openai_api_key),
        "anthropic_configured": bool(cfg.anthropic_api_key),
        "google_configured": bool(cfg.google_api_key),
        "deepseek_configured": bool(cfg.deepseek_api_key),
        "spotify_connected": bool(cfg.spotify_client_id and cfg.spotify_client_secret),
        "data_loaded": {
            "poses": collection_exists("poses"),
            "themes": collection_exists("themes"),
            "tracks": collection_exists("tracks") if collection_exists("tracks") else False,
        },
    }


@router.get("/available-models")
def get_available_models():
    return {"models": list_available_models()}


@router.post("/update")
def update_config(update: ConfigUpdate):
    data = {k: v for k, v in update.model_dump().items() if v is not None}
    if data:
        data["configured"] = True
        save_config(data)
    return {"status": "ok"}
