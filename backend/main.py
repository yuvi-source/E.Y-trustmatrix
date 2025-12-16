from dotenv import load_dotenv
load_dotenv(".env.local")

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import batch, stats, providers, manual_review, reports
from backend.api import router as explain_router
from .db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Provider Data Validation & Directory (Agentic AI) — Stage 1–11",
    lifespan=lifespan
)

# CORS configuration - restrict to known origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3020",
        "http://127.0.0.1:3020",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(batch.router)
app.include_router(stats.router)
app.include_router(providers.router)
app.include_router(manual_review.router)
app.include_router(reports.router)
app.include_router(explain_router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
