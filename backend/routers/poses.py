from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select
from backend.config import CONFIG_PATH
from backend.database import get_session
from backend.models import Pose, PoseFollowup
from backend.services.vector_store import search, collection_exists
from typing import Optional
import json
from pydantic import BaseModel

router = APIRouter(prefix="/api/poses", tags=["poses"])
# Anchored next to config.yaml like every other data file, so the overrides
# survive launching the backend from a different working directory.
OVERRIDES_PATH = CONFIG_PATH.parent / "data" / "pose_name_overrides.json"


class PoseNameOverrides(BaseModel):
    overrides: dict[str, str]


@router.get("")
def list_poses(
    category: Optional[str] = None,
    level: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 500,
    session: Session = Depends(get_session),
):
    if search_query and collection_exists("poses"):
        results = search("poses", search_query, n_results=limit)
        pose_ids = [r["id"] for r in results]
        rows = session.exec(select(Pose).where(col(Pose.pose_id).in_(pose_ids))).all()
        by_id = {p.pose_id: p for p in rows}
        # Re-emit in vector-search relevance order; SQL IN does not preserve it.
        poses = [by_id[pid] for pid in pose_ids if pid in by_id]
        return [_format_pose(p) for p in poses]
    stmt = select(Pose)
    if level:
        stmt = stmt.where(Pose.expertise_level == level)
    if category:
        # Filter in SQL so the limit applies after filtering; otherwise poses
        # in the requested category beyond the first `limit` rows vanish.
        stmt = stmt.where(col(Pose.pose_categories).ilike(f"%{category}%"))
    poses = session.exec(stmt.limit(limit)).all()
    return [_format_pose(p) for p in poses]


@router.get("/categories")
def get_categories(session: Session = Depends(get_session)):
    poses = session.exec(select(Pose)).all()
    categories = set()
    for p in poses:
        if p.pose_categories:
            try:
                cats = json.loads(p.pose_categories)
                categories.update(cats)
            except (ValueError, TypeError):
                categories.add(p.pose_categories)
    return sorted(list(categories))


# NOTE: static paths must be declared before the /{pose_id} catch-all below,
# or FastAPI matches them as pose ids and they 404.
@router.get("/data-status")
def poses_data_status(session: Session = Depends(get_session)):
    count = len(session.exec(select(Pose)).all())
    return {"loaded": count > 0, "count": count}


@router.get("/name-overrides")
def get_pose_name_overrides():
    if not OVERRIDES_PATH.exists():
        return {"overrides": {}}
    try:
        data = json.loads(OVERRIDES_PATH.read_text())
        if isinstance(data, dict):
            return {"overrides": data}
    except Exception:
        pass
    return {"overrides": {}}


@router.put("/name-overrides")
def set_pose_name_overrides(payload: PoseNameOverrides):
    OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES_PATH.write_text(json.dumps(payload.overrides, indent=2))
    return {"status": "ok", "count": len(payload.overrides)}


@router.get("/{pose_id}")
def get_pose(pose_id: str, session: Session = Depends(get_session)):
    pose = session.get(Pose, pose_id)
    if not pose:
        raise HTTPException(status_code=404, detail="Pose not found")
    followups = session.exec(select(PoseFollowup).where(PoseFollowup.pose_id == pose_id)).all()
    followup_poses = []
    for f in followups:
        fp = session.get(Pose, f.followup_pose_id)
        if fp:
            followup_poses.append({"pose_id": fp.pose_id, "name": fp.name})
    return {**_format_pose(pose), "followup_poses": followup_poses}


def _parse_json_list(raw: Optional[str]) -> list:
    """Parse a JSON-list column, tolerating legacy plain-string values the
    same way get_categories does instead of 500-ing the whole endpoint."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return [raw]
    return value if isinstance(value, list) else [value]


def _format_pose(pose: Pose) -> dict:
    return {
        "pose_id": pose.pose_id,
        "name": pose.name,
        "sanskrit_name": pose.sanskrit_name,
        "expertise_level": pose.expertise_level,
        "pose_categories": _parse_json_list(pose.pose_categories),
        "image_url": pose.image_url,
        "description": pose.description,
        "tags": _parse_json_list(pose.tags),
    }
