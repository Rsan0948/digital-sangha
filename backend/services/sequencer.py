from sqlmodel import Session, select
from backend.database import engine
from backend.models import Pose, PoseFollowup
from typing import Optional
import json


def get_followup_poses(pose_id: str) -> list[str]:
    with Session(engine) as session:
        stmt = select(PoseFollowup).where(PoseFollowup.pose_id == pose_id)
        results = session.exec(stmt).all()
        return [r.followup_pose_id for r in results]


def validate_transition(from_pose_id: str, to_pose_id: str) -> dict:
    followups = get_followup_poses(from_pose_id)
    if not followups:
        return {"valid": True, "suggested": True, "message": "No transition data available"}
    if to_pose_id in followups:
        return {"valid": True, "suggested": True, "message": "Recommended transition"}
    return {"valid": True, "suggested": False, "message": f"Consider: {', '.join(followups[:3])}"}


def calculate_flow_duration(blocks_json: str) -> int:
    try:
        sections = json.loads(blocks_json)
        total_seconds = 0
        for section in sections:
            for block in section.get("blocks", []):
                total_seconds += block.get("duration", 30)
        return total_seconds // 60
    except:
        return 0


def extract_energy_curve(blocks_json: str) -> list[dict]:
    """Extract minute-by-minute energy levels from flow blocks."""
    try:
        sections = json.loads(blocks_json)
        curve = []
        current_minute = 0
        section_energies = {
            "centering": 0.2,
            "warmup": 0.4,
            "sun_salutations": 0.6,
            "standing": 0.7,
            "peak": 0.85,
            "floor": 0.5,
            "cooldown": 0.3,
            "savasana": 0.1,
        }
        for section in sections:
            label = section.get("label", "").lower().replace(" ", "_")
            energy = section_energies.get(label, 0.5)
            section_duration = sum(b.get("duration", 30) for b in section.get("blocks", []))
            minutes = section_duration // 60
            for _ in range(max(1, minutes)):
                curve.append(
                    {
                        "minute": current_minute,
                        "energy": energy,
                        "section": section.get("label", ""),
                    }
                )
                current_minute += 1
        return curve
    except:
        return []
