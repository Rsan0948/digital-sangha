from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import Pose, PoseFollowup
from backend.services.vector_store import search, collection_exists
from typing import Optional
import json
from pathlib import Path
from pydantic import BaseModel

router = APIRouter(prefix="/api/poses", tags=["poses"])
OVERRIDES_PATH = Path("data/pose_name_overrides.json")


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
        poses = session.exec(select(Pose).where(Pose.pose_id.in_(pose_ids))).all()
        return [_format_pose(p) for p in poses]
    stmt = select(Pose)
    if level:
        stmt = stmt.where(Pose.expertise_level == level)
    poses = session.exec(stmt.limit(limit)).all()
    if category:
        poses = [p for p in poses if category.lower() in (p.pose_categories or "").lower()]
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
            except:
                categories.add(p.pose_categories)
    return sorted(list(categories))


@router.get("/{pose_id}")
def get_pose(pose_id: str, session: Session = Depends(get_session)):
    pose = session.get(Pose, pose_id)
    if not pose:
        return {"error": "Pose not found"}
    followups = session.exec(select(PoseFollowup).where(PoseFollowup.pose_id == pose_id)).all()
    followup_poses = []
    for f in followups:
        fp = session.get(Pose, f.followup_pose_id)
        if fp:
            followup_poses.append({"pose_id": fp.pose_id, "name": fp.name})
    return {**_format_pose(pose), "followup_poses": followup_poses}


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


def _format_pose(pose: Pose) -> dict:
    return {
        "pose_id": pose.pose_id,
        "name": pose.name,
        "sanskrit_name": pose.sanskrit_name,
        "expertise_level": pose.expertise_level,
        "pose_categories": json.loads(pose.pose_categories) if pose.pose_categories else [],
        "image_url": pose.image_url,
        "description": pose.description,
        "tags": json.loads(pose.tags) if pose.tags else [],
    }
