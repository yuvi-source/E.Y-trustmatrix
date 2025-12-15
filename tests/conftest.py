from dotenv import load_dotenv
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base

# Always load env from project root (.env.local preferred, fallback to .env)
root = Path(__file__).resolve().parent.parent
load_dotenv(root / ".env.local")
load_dotenv(root / ".env")

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()