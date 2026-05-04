#!/usr/bin/env python3
"""
Ingest yoga poses from the omergoshen/yoga_poses dataset.
Download from: https://huggingface.co/datasets/omergoshen/yoga_poses
Place the JSON file in data/raw/yoga_poses.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from backend.database import engine, init_db
from backend.models import Pose, PoseFollowup
from backend.services.vector_store import add_documents

RAW_PATH = Path("data/raw/yoga_poses.json")


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


def ingest_poses():
    if not RAW_PATH.exists():
        print(f"❌ File not found: {RAW_PATH}")
        print("Download from: https://huggingface.co/datasets/omergoshen/yoga_poses")
        print("Place yoga_poses.json in data/raw/")
        return

    init_db()

    with open(RAW_PATH) as f:
        data = json.load(f)

    # Handle different JSON structures
    poses_data = data if isinstance(data, list) else data.get("poses", data.get("data", []))

    print(f"📚 Found {len(poses_data)} poses")

    pose_name_to_id = {}
    ids = []
    texts = []
    metas = []

    with Session(engine) as session:
        # First pass: create poses
        for item in poses_data:
            name = item.get("name", "")
            if not name:
                continue

            pose_id = slugify(item.get("sanskrit_name") or name)
            pose_name_to_id[name] = pose_id

            existing = session.get(Pose, pose_id)
            if existing:
                continue

            categories = item.get("pose_type", [])
            if isinstance(categories, str):
                categories = [categories]

            embed_text = " ".join(filter(None, [
                name,
                item.get("sanskrit_name", ""),
                " ".join(categories) if categories else "",
                item.get("description", "")
            ]))

            pose = Pose(
                pose_id=pose_id,
                name=name,
                sanskrit_name=item.get("sanskrit_name"),
                expertise_level=item.get("expertise_level", "").lower() if item.get("expertise_level") else None,
                pose_categories=json.dumps(categories),
                image_url=item.get("photo_url") or item.get("image_url"),
                description=item.get("description"),
                tags=json.dumps(item.get("tags", [])) if item.get("tags") else None,
                embed_text=embed_text
            )
            session.add(pose)

            ids.append(pose_id)
            texts.append(embed_text)
            metas.append({"name": name, "sanskrit": item.get("sanskrit_name", "")})

        session.commit()
        print(f"✅ Added {len(ids)} poses to database")

        # Second pass: create followup relationships
        followup_count = 0
        for item in poses_data:
            name = item.get("name", "")
            if not name or name not in pose_name_to_id:
                continue

            pose_id = pose_name_to_id[name]
            followups = item.get("followup_poses", [])

            for followup_name in followups:
                if followup_name in pose_name_to_id:
                    followup_id = pose_name_to_id[followup_name]

                    # Check if relationship exists
                    existing = session.exec(
                        select(PoseFollowup).where(
                            PoseFollowup.pose_id == pose_id,
                            PoseFollowup.followup_pose_id == followup_id
                        )
                    ).first()

                    if not existing:
                        pf = PoseFollowup(pose_id=pose_id, followup_pose_id=followup_id)
                        session.add(pf)
                        followup_count += 1

        session.commit()
        print(f"✅ Added {followup_count} followup relationships")

    # Add to vector store
    if ids:
        add_documents("poses", ids, texts, metas)
        print(f"✅ Indexed {len(ids)} poses in vector store")

    print("🧘 Pose ingestion complete!")


if __name__ == "__main__":
    ingest_poses()
