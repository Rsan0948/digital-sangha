import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from backend.config import CONFIG_PATH
from backend.database import get_session, engine
from backend.models import Flow, FlowVersion
from backend.services.llm_router import generate

router = APIRouter(prefix="/api/flows", tags=["flows"])
GUIDE_PATH = CONFIG_PATH.parent / "data" / "transition_guides.json"


class FlowCreate(BaseModel):
    flow_name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    context_type: str = Field(default="Both", max_length=20)
    tags: Optional[list[str]] = Field(default=None, max_length=100)


class FlowVersionCreate(BaseModel):
    blocks_json: str = Field(max_length=200000)
    vibe_profile: Optional[str] = Field(default=None, max_length=20000)


class FlowUpdate(BaseModel):
    flow_name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    context_type: Optional[str] = Field(default=None, max_length=20)
    tags: Optional[list[str]] = Field(default=None, max_length=100)


class TransitionGuideCreate(BaseModel):
    version_id: Optional[str] = Field(default=None, max_length=64)
    blocks_json: Optional[str] = Field(default=None, max_length=200000)
    flow_name: Optional[str] = Field(default=None, max_length=200)


def _load_guides() -> dict:
    if not GUIDE_PATH.exists():
        return {}
    try:
        data = json.loads(GUIDE_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_guides(guides: dict) -> None:
    GUIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = GUIDE_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(guides, indent=2))
    os.replace(tmp_path, GUIDE_PATH)


def _extract_pose_sequence(blocks_json: str) -> list[str]:
    try:
        sections = json.loads(blocks_json)
    except (ValueError, TypeError):
        return []
    if not isinstance(sections, list):
        return []
    poses: list[str] = []
    seen_pairs: set[str] = set()
    seen_pose_keys: set[str] = set()
    for section in sections:
        if not isinstance(section, dict):
            continue
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("block_type") != "pose":
                continue
            name = block.get("pose_name") or block.get("description") or "Pose"
            pair_id = block.get("pair_id")
            if pair_id:
                if pair_id in seen_pairs:
                    continue
                seen_pairs.add(pair_id)
                poses.append(name)
                continue
            # No pair id: avoid duplicates from left/right entries by name.
            key = name.lower().strip()
            if key in seen_pose_keys:
                continue
            seen_pose_keys.add(key)
            poses.append(name)
    return poses


def _build_transition_prompt(flow_name: str, poses: list[str]) -> tuple[str, str]:
    system = (
        "You are a yoga instructor writing a transition guide. "
        "Write clear, concise, body-focused instructions on how to move from one pose to the next. "
        "Do not include themes, metaphors, quotes, or breath cues unless necessary for safe movement. "
        "Output a numbered list. One line per transition. "
        'Each line must start with "Pose A -> Pose B:" so the transition is clearly labeled.'
    )
    if not poses:
        return system, "No poses were provided."
    if len(poses) == 1:
        return (
            system,
            f"Flow: {flow_name}\nOnly pose: {poses[0]}\nReturn a single line: End in {poses[0]}.",
        )
    user = (
        f"Flow: {flow_name}\n"
        "Poses in order:\n" + "\n".join([f"- {p}" for p in poses]) + "\n\n"
        "Write transitions between each consecutive pose. Keep each line under 25 words."
    )
    return system, user


@router.get("")
def list_flows(context_type: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(Flow)
    if context_type and context_type != "Both":
        stmt = stmt.where((Flow.context_type == context_type) | (Flow.context_type == "Both"))
    flows = session.exec(stmt).all()
    result = []
    for f in flows:
        versions = session.exec(
            select(FlowVersion)
            .where(FlowVersion.flow_id == f.flow_id)
            .order_by(FlowVersion.version_number.desc())
        ).all()
        result.append(
            {
                **f.model_dump(),
                "versions": [v.model_dump() for v in versions],
                "tags": json.loads(f.tags) if f.tags else [],
            }
        )
    return result


@router.post("")
def create_flow(flow: FlowCreate, session: Session = Depends(get_session)):
    db_flow = Flow(
        flow_name=flow.flow_name,
        description=flow.description,
        context_type=flow.context_type,
        tags=json.dumps(flow.tags) if flow.tags else None,
    )
    session.add(db_flow)
    session.commit()
    session.refresh(db_flow)
    return db_flow


@router.get("/{flow_id}")
def get_flow(flow_id: str, session: Session = Depends(get_session)):
    flow = session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    versions = session.exec(
        select(FlowVersion)
        .where(FlowVersion.flow_id == flow_id)
        .order_by(FlowVersion.version_number.desc())
    ).all()
    return {
        **flow.model_dump(),
        "versions": [v.model_dump() for v in versions],
        "tags": json.loads(flow.tags) if flow.tags else [],
    }


@router.patch("/{flow_id}")
def update_flow(flow_id: str, update: FlowUpdate, session: Session = Depends(get_session)):
    flow = session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    if update.flow_name:
        flow.flow_name = update.flow_name
    if update.description is not None:
        flow.description = update.description
    if update.context_type:
        flow.context_type = update.context_type
    if update.tags is not None:
        flow.tags = json.dumps(update.tags)
    flow.updated_at = datetime.utcnow()
    session.add(flow)
    session.commit()
    return flow


@router.delete("/{flow_id}")
def delete_flow(flow_id: str, session: Session = Depends(get_session)):
    flow = session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    versions = session.exec(select(FlowVersion).where(FlowVersion.flow_id == flow_id)).all()
    for v in versions:
        session.delete(v)
    session.delete(flow)
    session.commit()
    return {"status": "deleted"}


@router.post("/{flow_id}/versions")
def create_version(
    flow_id: str, version: FlowVersionCreate, session: Session = Depends(get_session)
):
    flow = session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    existing = session.exec(
        select(FlowVersion)
        .where(FlowVersion.flow_id == flow_id)
        .order_by(FlowVersion.version_number.desc())
    ).first()
    next_num = (existing.version_number + 1) if existing else 1
    from backend.services.sequencer import calculate_flow_duration

    duration = calculate_flow_duration(version.blocks_json)
    db_version = FlowVersion(
        flow_id=flow_id,
        version_number=next_num,
        blocks_json=version.blocks_json,
        vibe_profile=version.vibe_profile,
        duration_minutes=duration,
    )
    session.add(db_version)
    flow.updated_at = datetime.utcnow()
    session.add(flow)
    session.commit()
    session.refresh(db_version)
    return db_version


@router.get("/{flow_id}/versions/{version_id}")
def get_version(flow_id: str, version_id: str, session: Session = Depends(get_session)):
    version = session.get(FlowVersion, version_id)
    if not version or version.flow_id != flow_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.get("/{flow_id}/transition-guide")
def get_transition_guide(flow_id: str, version_id: Optional[str] = None):
    guides = _load_guides()
    entry = guides.get(flow_id)
    if not entry:
        return {"exists": False}
    if version_id and entry.get("version_id") != version_id:
        return {"exists": False, "version_id": entry.get("version_id")}
    return {
        "exists": True,
        "guide": entry.get("guide"),
        "version_id": entry.get("version_id"),
        "updated_at": entry.get("updated_at"),
    }


@router.post("/{flow_id}/transition-guide")
def generate_transition_guide(
    flow_id: str, payload: TransitionGuideCreate, session: Session = Depends(get_session)
):
    flow = session.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    blocks_json = payload.blocks_json
    version_id = payload.version_id
    if not blocks_json:
        if version_id:
            version = session.get(FlowVersion, version_id)
            if not version or version.flow_id != flow_id:
                raise HTTPException(status_code=404, detail="Version not found")
        else:
            version = session.exec(
                select(FlowVersion)
                .where(FlowVersion.flow_id == flow_id)
                .order_by(FlowVersion.version_number.desc())
            ).first()
            if not version:
                raise HTTPException(status_code=404, detail="No flow versions found")
        blocks_json = version.blocks_json
        version_id = version.version_id

    poses = _extract_pose_sequence(blocks_json)
    flow_name = payload.flow_name or flow.flow_name
    system, user = _build_transition_prompt(flow_name, poses)
    guide = generate(user, mode="power", system=system)

    guides = _load_guides()
    guides[flow_id] = {
        "flow_name": flow_name,
        "version_id": version_id,
        "guide": guide.strip(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _save_guides(guides)
    return {"guide": guide.strip(), "version_id": version_id}


@router.delete("/{flow_id}/transition-guide")
def delete_transition_guide(flow_id: str):
    guides = _load_guides()
    if flow_id in guides:
        del guides[flow_id]
        _save_guides(guides)
    return {"status": "deleted"}
