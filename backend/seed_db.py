from dotenv import load_dotenv
load_dotenv(".env.local")

import os
import argparse
import csv
from pathlib import Path

from sqlalchemy.orm import Session

from .db import init_db, SessionLocal, Provider, Document
from .utils.npi import is_valid_npi


USE_REAL_NPI = os.getenv("USE_REAL_NPI", "false").lower() == "true"


def looks_like_npi(value: str) -> bool:
    """
    Returns True if the value looks like a real NPI:
    - exactly 10 digits
    """
    return value.isdigit() and len(value) == 10


def seed_db(providers_csv: Path, documents_dir: Path) -> None:
    init_db()
    db: Session = SessionLocal()

    # ---- Seed providers ----
    with providers_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            external_id = row["external_id"].strip()

            # Validate ONLY real-looking NPIs in real mode
            if USE_REAL_NPI and looks_like_npi(external_id):
                if not is_valid_npi(external_id):
                    raise ValueError(
                        f"Invalid NPI '{external_id}' for provider '{row.get('name')}'"
                    )

            # print("SEEDING ROW:", row)

            provider = Provider(
                external_id=external_id,
                name=row["name"],
                phone=row.get("phone") or None,
                address=row.get("address") or None,
                specialty=row.get("specialty") or None,
                license_no=row.get("license_no") or None,
                license_expiry=row.get("license_expiry") or None,
                affiliations=row.get("affiliations") or None,
            )
            db.add(provider)

        db.commit()

    # ---- Seed documents ----
    providers = db.query(Provider).all()
    for p in providers:
        img_path = documents_dir / f"{p.external_id}.png"
        if img_path.exists():
            doc = Document(
                provider_id=p.id,
                doc_type="license",
                path=str(img_path),
            )
            db.add(doc)

    db.commit()
    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", type=str, required=True)
    parser.add_argument("--documents", type=str, required=True)
    args = parser.parse_args()

    seed_db(Path(args.providers), Path(args.documents))
