from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, JSON, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

DB_PATH = Path(__file__).resolve().parent / "provider_directory.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    address = Column(String)
    specialty = Column(String)
    license_no = Column(String)
    license_expiry = Column(String)
    affiliations = Column(String)
    last_verified_at = Column(DateTime)
    last_changed_at = Column(DateTime)

    scores = relationship("ProviderScore", back_populates="provider", uselist=False)
    drift = relationship("DriftScore", back_populates="provider", uselist=False)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    doc_type = Column(String)
    path = Column(String)
    ocr_text = Column(String)
    ocr_confidence = Column(Float)


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True)
    run_type = Column(String)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime)
    count_processed = Column(Integer, default=0)
    auto_updates = Column(Integer, default=0)
    manual_reviews = Column(Integer, default=0)


class ManualReviewItem(Base):
    __tablename__ = "manual_review_queue"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    field_name = Column(String)
    current_value = Column(String)
    suggested_value = Column(String)
    reason = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FieldConfidence(Base):
    __tablename__ = "field_confidence"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    field_name = Column(String)
    confidence = Column(Float)
    sources = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProviderScore(Base):
    __tablename__ = "provider_scores"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), unique=True)
    pcs = Column(Float)
    srm = Column(Float)
    fr = Column(Float)
    st = Column(Float)
    mb = Column(Float)
    dq = Column(Float)
    rp = Column(Float)
    lh = Column(Float)
    ha = Column(Float)
    band = Column(String)

    provider = relationship("Provider", back_populates="scores")


class DriftScore(Base):
    __tablename__ = "drift_scores"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), unique=True)
    score = Column(Float)
    bucket = Column(String)
    recommended_next_check_days = Column(Integer)

    provider = relationship("Provider", back_populates="drift")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    field_name = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    action = Column(String)  # auto_update / manual_approve / manual_override
    actor = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
