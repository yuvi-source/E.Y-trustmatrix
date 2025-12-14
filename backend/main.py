from dotenv import load_dotenv
load_dotenv("backend/.env.local")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import batch, stats, providers, manual_review, reports
from .db import init_db

app = FastAPI(title="Provider Data Validation & Directory (Agentic AI) — Stage 1–11")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(batch.router)
app.include_router(stats.router)
app.include_router(providers.router)
app.include_router(manual_review.router)
app.include_router(reports.router)

@app.on_event("startup")
async def on_startup() -> None:
    init_db()

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
