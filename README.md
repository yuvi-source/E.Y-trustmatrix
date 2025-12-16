# Provider Data Validation & Directory (Agentic AI)

## 📌 Overview
This project is an **Agentic AI System** designed to automate the validation, enrichment, and management of healthcare provider directories. It addresses the industry-wide problem of inaccurate provider data (40-80% error rate) by using a multi-agent architecture to cross-reference data from multiple trusted sources, assign confidence scores, and predict future data drift.

## 🚀 Key Features

### Core AI Agents
1.  **Validation Agent:** Scrapes and verifies data against NPI Registry, State Medical Boards, Google Maps, and Hospital directories.
2.  **Enrichment Agent:** Extracts data from unstructured documents (PDFs/Images) using OCR and fills missing details.
3.  **QA Agent:** Computes field-level confidence scores (>70% = auto-update, <70% = manual review).
4.  **Directory Management Agent:** Orchestrates the workflow, updates the database, and manages the manual review queue.

### 🌟 Unique Capabilities
*   **Provider Credibility Score (PCS):** A "credit score" (0-100) for doctors based on:
    - Source Reliability Match (SRM) - 25%
    - Field Recency (FR) - 15%
    - Specialty Timeliness (ST) - 10%
    - Member Behavior (MB) - 15%
    - Data Quality (DQ) - 10%
    - Responsiveness (RP) - 10%
    - License Health (LH) - 10%
    - Historical Accuracy (HA) - 5%
*   **Provider Data Drift Detection (PDDD):** Predictive model that identifies providers likely to have outdated info soon (expiring licenses, volatile contact info).
*   **Auto-Correction:** Automatically fixes high-confidence errors (>70% confidence threshold).
*   **Smart Manual Review:** Routes only low-confidence conflicts to human reviewers with AI explanations.
*   **AI-Powered Explanations:** Google Gemini integration provides natural language explanations for validation decisions.

## 🛠️ Tech Stack
*   **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite, Pytesseract (OCR), ReportLab (PDF Generation), Google Gemini API.
*   **Frontend:** React 18, Webpack 5, Axios, CSS Modules.
*   **Orchestration:** Custom Python-based multi-agent workflow.
*   **Testing:** Pytest with comprehensive unit and integration tests.

## 📋 Prerequisites
*   **Python 3.10+**
*   **Node.js 14+**
*   **Tesseract OCR** (Optional, system has fallback if not installed)
*   **Google Gemini API Key** (Optional, for AI explanations - falls back to rule-based explanations)

## ⚙️ Installation & Setup

### 1. Backend Setup
Navigate to the root directory:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment (optional)
# Create .env.local file for Gemini API:
# GEMINI_API_KEY=your_api_key_here

# Initialize Database and Seed Data
python -m backend.reset_demo_state
```

### 2. Frontend Setup
Navigate to the frontend directory:
```bash
cd frontend
npm install
```

## ▶️ Running the Application

### Step 1: Start the Backend
In the root directory (with virtual environment activated):
```bash
# Windows PowerShell:
cd "c:\EY FULL"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000

# Mac/Linux:
uvicorn backend.main:app --reload --port 8000
```
*The backend will run at `http://127.0.0.1:8000`*
*API documentation available at `http://127.0.0.1:8000/docs`*

### Step 2: Start the Frontend
Open a new terminal, navigate to `frontend`, and run:
```bash
cd frontend
npm start
```
*The frontend will run at `http://localhost:3020`*
**Important: Frontend uses port 3020, not 3000**

### Optional: One-click start (Windows)
You can also start both servers using:
- `START-HERE.bat` (opens backend + frontend in separate windows)

### Step 3: Trigger Data Processing
Once both servers are running:
1.  Open the Frontend at `http://localhost:3020`.
2.  Click the **"Run Daily Batch"** button in the top right corner.
3.  Wait for the process to complete. The dashboard will populate with:
    *   **Last Run:** Timestamp and batch type
    *   **Processed:** Total providers processed
    *   **Auto-Updated:** Fields automatically corrected (>70% confidence)
    *   **Manual Review:** Current pending field-level reviews
    *   **Avg PCS:** Average Provider Credibility Score
    *   **Drift Distribution:** Low/Medium/High risk buckets
    *   **PCS Distribution:** Score bands (0-50, 50-70, 70-90, 90-100)
    *   **Trend:** Last 5 batch runs comparison

## 📂 Project Structure
```
EY FULL/
├── backend/
│   ├── agents.py              # Core logic for Validation, Enrichment, QA agents
│   ├── db.py                  # Database models (SQLite)
│   ├── main.py                # FastAPI entry point with CORS
│   ├── orchestrator.py        # Batch processing workflow (run_validation_batch)
│   ├── pcs_drift.py           # Logic for PCS and PDDD scoring
│   ├── llm/
│   │   ├── gemini_client.py   # Google Gemini API wrapper
│   │   └── qa_summarizer.py   # AI explanation generation
│   ├── data/                  # Mock data (NPI, State Board, Hospital, Maps)
│   ├── routers/               # API endpoints
│   │   ├── batch.py           # /run-batch (trigger validation)
│   │   ├── providers.py       # /providers (CRUD, details, list)
│   │   ├── manual_review.py   # /manual-review (approve/reject)
│   │   ├── reports.py         # /reports (PDF generation)
│   │   └── stats.py           # /stats (dashboard metrics)
│   ├── external/
│   │   └── npi_client.py      # NPI Registry API client
│   ├── utils/                 # Helper functions
│   ├── reset_demo_state.py    # Reset database to demo state
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main React UI (Dashboard, Providers, Manual Review)
│   │   ├── index.jsx          # React entry point
│   │   └── styles.css         # Dashboard and component styling
│   ├── webpack.config.js      # Proxy configuration (port 3020 → 8000)
│   └── package.json           # Node dependencies
├── tests/                     # Pytest test suite
├── .env.local                 # Environment variables (GEMINI_API_KEY)
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## 🔧 Troubleshooting

*   **Port Conflicts:**
    *   Backend: Port 8000 (change with `--port` flag)
    *   Frontend: Port 3020 (configured in webpack.config.js - DO NOT use default 3000)
    *   If `npm start` fails with `EADDRINUSE`, kill the process using port 3020
*   **Proxy Errors:**
    *   If the frontend shows "Network Error", ensure the backend is running on port 8000
    *   Check webpack proxy configuration in webpack.config.js
*   **OCR Issues:**
    *   If Tesseract is not found, the system will default to a 0.7 confidence score and continue processing
*   **Gemini API Errors:**
    *   If the API key is missing/invalid, quota is exceeded, or the model is unavailable, the system falls back to deterministic summaries/explanations.
    *   Create `.env.local` in the repo root with `GEMINI_API_KEY=...` (do not commit secrets).
*   **Database Issues:**
    *   Reset database: `python -m backend.reset_demo_state`
    *   Check database: `python check_db.py`

## 🎯 Key Validation Rules

### Confidence Scoring
- **Source Reliability Weights:**
  - NPI Registry: 1.0 (highest)
  - State Medical Board: 0.9
  - Hospital Directory: 0.7
  - Google Maps: 0.5
  - Original Data: 0.3 (lowest)

### Decision Thresholds
- **>70% confidence:** Auto-update field
- **<70% confidence:** Send to manual review
- **PCS Bands:**
  - Green (≥85): Safe for auto-publish
  - Amber (70-84): Requires audit trail
  - Red (<70): Manual review required

## 🧪 Demo Scenarios
1.  **Auto-Update:** Search for **Dr. Rohan Verma (P001)**. Multiple sources confirm updated phone number → auto-corrected.
2.  **Manual Review:** Check the "Manual Review Queue". **Dr. Meera Patel (P002)** has conflicting address data between sources.
3.  **Drift Detection:** Providers with **"High" drift** risk have upcoming license expirations or volatile data patterns.
4.  **AI Explanations:** Click "Explain" on manual review items to see AI-generated reasoning.
5.  **PDF Reports:** Download validation summary reports from provider detail pages.
6.  **QA History:** View all previous QA decisions with timestamps and confidence scores.

## 🧪 Testing
Run the test suite:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agents_qa_evaluate.py

# Run with coverage
pytest --cov=backend tests/
```

## 📊 API Endpoints
- `GET /health` - Health check
- `GET /stats` - Dashboard statistics
- `GET /providers` - List all providers
- `GET /providers/{id}/details` - Provider details with validation data
- `GET /providers/{id}/ocr` - OCR panel data (if a document exists)
- `GET /providers/{id}/qa` - Confidence history
- `POST /run-batch?type=daily` - Trigger daily batch
- `GET /manual-review` - List manual review items
- `POST /manual-review/{id}/approve` - Approve review item
- `POST /manual-review/{id}/reject` - Reject review item
- `POST /manual-review/{id}/override?value=...` - Override review item
- `GET /reports/latest` - Download latest PDF report
- `POST /explain` - Get AI explanation for a decision

## 🎓 Learn More
- **NPI Registry:** https://npiregistry.cms.hhs.gov/
- **Google Gemini API:** https://ai.google.dev/
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **React Documentation:** https://react.dev/

## 📝 License
This is a demonstration project for healthcare data validation automation.
