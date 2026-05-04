#!/usr/bin/env python3
"""
Ingest Yoga Sutras from a JSON file.
Expected format: array of objects with sutra_id, book, verse, sanskrit, transliteration, translation
Place the file in data/raw/sutras.json

If you don't have a JSON file, this script can create a starter set of sutras.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session
from backend.database import engine, init_db
from backend.models import Sutra
from backend.services.vector_store import add_documents

RAW_PATH = Path("data/raw/sutras.json")

# Starter sutras if no file exists
STARTER_SUTRAS = [
    {"sutra_id": "1.1", "book": 1, "verse": 1, "transliteration": "atha yoga-anushasanam",
     "translation": "Now begins the instruction on yoga.", "keywords": ["beginning", "discipline", "instruction"]},
    {"sutra_id": "1.2", "book": 1, "verse": 2, "transliteration": "yogas chitta-vritti-nirodhah",
     "translation": "Yoga is the cessation of the fluctuations of the mind.", "keywords": ["mind", "stillness", "definition"]},
    {"sutra_id": "1.3", "book": 1, "verse": 3, "transliteration": "tada drashtuh svarupe avasthanam",
     "translation": "Then the seer abides in their own true nature.", "keywords": ["self", "awareness", "true nature"]},
    {"sutra_id": "1.12", "book": 1, "verse": 12, "transliteration": "abhyasa-vairagyabhyam tan-nirodhah",
     "translation": "These fluctuations are stilled through practice and non-attachment.", "keywords": ["practice", "non-attachment", "discipline"]},
    {"sutra_id": "1.14", "book": 1, "verse": 14, "transliteration": "sa tu dirgha-kala-nairantarya-satkarasevito drdha-bhumih",
     "translation": "Practice becomes firmly established when done for a long time, without break, and with sincere devotion.", "keywords": ["consistency", "dedication", "patience"]},
    {"sutra_id": "2.1", "book": 2, "verse": 1, "transliteration": "tapah-svadhyayeshvara-pranidhanani kriya-yogah",
     "translation": "Yoga in action consists of self-discipline, self-study, and surrender to the divine.", "keywords": ["tapas", "svadhyaya", "ishvara pranidhana", "kriya yoga"]},
    {"sutra_id": "2.29", "book": 2, "verse": 29, "transliteration": "yama-niyamasana-pranayama-pratyahara-dharana-dhyana-samadhayo 'stav angani",
     "translation": "The eight limbs of yoga are: ethical restraints, observances, posture, breath control, sense withdrawal, concentration, meditation, and absorption.", "keywords": ["eight limbs", "ashtanga", "path"]},
    {"sutra_id": "2.33", "book": 2, "verse": 33, "transliteration": "vitarka-badhane pratipaksha-bhavanam",
     "translation": "When disturbed by negative thoughts, cultivate the opposite.", "keywords": ["pratipaksha bhavana", "positive thinking", "antidote"]},
    {"sutra_id": "2.35", "book": 2, "verse": 35, "transliteration": "ahimsa-pratishthayam tat-sannidhau vaira-tyagah",
     "translation": "When non-violence is established, hostility ceases in the presence of that person.", "keywords": ["ahimsa", "non-violence", "peace"]},
    {"sutra_id": "2.46", "book": 2, "verse": 46, "transliteration": "sthira-sukham asanam",
     "translation": "Asana is a steady, comfortable posture.", "keywords": ["asana", "posture", "steadiness", "ease"]},
]


def ingest_sutras():
    init_db()

    if RAW_PATH.exists():
        with open(RAW_PATH) as f:
            data = json.load(f)
        sutras_data = data if isinstance(data, list) else data.get("sutras", [])
        print(f"📖 Found {len(sutras_data)} sutras in file")
    else:
        print(f"📖 No sutras.json found at {RAW_PATH}")
        print("   Using starter set of key sutras...")
        sutras_data = STARTER_SUTRAS

    ids = []
    texts = []
    metas = []

    with Session(engine) as session:
        for item in sutras_data:
            sutra_id = item.get("sutra_id", f"{item.get('book', 1)}.{item.get('verse', 1)}")

            existing = session.get(Sutra, sutra_id)
            if existing:
                continue

            embed_text = " ".join(filter(None, [
                item.get("transliteration", ""),
                item.get("translation", ""),
                " ".join(item.get("keywords", []))
            ]))

            sutra = Sutra(
                sutra_id=sutra_id,
                book=item.get("book", 1),
                verse=item.get("verse", 1),
                sanskrit=item.get("sanskrit"),
                transliteration=item.get("transliteration"),
                translation=item.get("translation", ""),
                commentary=item.get("commentary"),
                keywords=json.dumps(item.get("keywords", [])) if item.get("keywords") else None,
                embed_text=embed_text
            )
            session.add(sutra)

            ids.append(sutra_id)
            texts.append(embed_text)
            metas.append({"book": sutra.book, "verse": sutra.verse})

        session.commit()
        print(f"✅ Added {len(ids)} sutras to database")

    if ids:
        add_documents("sutras", ids, texts, metas)
        print(f"✅ Indexed {len(ids)} sutras in vector store")

    print("📿 Sutra ingestion complete!")


if __name__ == "__main__":
    ingest_sutras()
