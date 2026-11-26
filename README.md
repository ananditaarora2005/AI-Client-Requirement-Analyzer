# AI Client Requirement Analyzer

An intelligent full-stack-style Python & Streamlit SaaS application that converts unstructured client conversations, emails, meeting notes, and PDF/DOCX requirement documents into structured software project plans.

## Key Capabilities

1. **Executive SaaS Dashboard**: Equal-height KPI cards, functional priority mix, non-functional category distribution, readiness breakdown, and recent projects table.
2. **Day (Light) & Night (Dark) Themes**: Instant sidebar theme switcher with adaptive Plotly charts and high-contrast UI components.
3. **Multi-Mode Requirement Intake**: Paste raw emails/transcripts (with built-in sample briefs) or upload `.pdf`, `.docx`, and `.txt` documents.
4. **Structured AI Analysis**: Provider-agnostic LLM integration (`OpenAI`, `OpenAI-compatible`, `Google Gemini`) with strict Pydantic schema validation, plus an **Offline Smart Mode (`offline_demo`)** for running without an API key.
5. **Requirement Extraction**: Generates categorized Functional Requirements (MoSCoW priority + acceptance criteria) and Non-Functional Requirements (category + measurable targets).
6. **Tech Stack & Roadmap Planning**: Recommends an architecture stack with rationale/alternatives and generates a phased project timeline rendered as an interactive Plotly Gantt chart.
7. **Completeness Scoring & Gap Detection**: Evaluates 7 weighted dimensions (0–100%), detects missing details/ambiguities by severity, and drafts a client clarification email.
8. **SQLite History & PDF Export**: Persists all analyses in a normalized SQLite database with search/filter/CSV export and generates multi-section executive PDF reports via ReportLab.

## Architecture & Folder Structure

```text
AI_Client_Requirement_Analyzer/
├── app.py                     # Streamlit entry point, theme switcher & sidebar router
├── requirements.txt           # Project dependencies
├── .env.example               # Environment variable template
├── .streamlit/
│   └── config.toml            # Streamlit server & theme defaults
├── config/
│   └── settings.py            # Environment loading & scoring rubric config
├── models/
│   └── schemas.py             # Pydantic v2 domain & AI output schemas
├── prompts/
│   └── analysis_prompts.py    # Structured JSON LLM system/user prompts
├── services/
│   ├── document_parser.py     # PDF, DOCX, TXT extraction & sanitization
│   ├── ai_analyzer.py         # OpenAI / Gemini / Offline engine & schema validation
│   ├── scoring_service.py     # Weighted completeness score & readiness tier
│   └── report_generator.py    # ReportLab multi-section PDF report builder
├── database/
│   └── db_manager.py          # Normalized SQLite schema & CRUD repository
├── ui/
│   ├── styles/theme.css       # Light & Night (Dark) SaaS styling
│   ├── components/            # KPI cards, Plotly charts, Pandas tables
│   └── pages/                 # Dashboard, New Analysis, Details, History
├── utils/
│   ├── validators.py          # Input & upload validation helpers
│   └── logger.py              # Secret-redacting application logger
├── data/
│   └── samples/               # Sample client briefs for instant testing
├── exports/                   # Generated PDF export folder
└── tests/                     # Pytest unit & integration test suite
```

## Setup & Running Locally

1. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Configure environment variables (optional for Offline Smart Mode)**:
   ```powershell
   Copy-Item .env.example .env
   ```
   You can edit `.env` directly (`OPENAI_API_KEY` or `GEMINI_API_KEY`, plus `LLM_PROVIDER`), **or** configure and save your key directly inside the app's **AI Engine Setup** sidebar panel.

3. **Run the automated test suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -v
   ```

4. **Launch the Streamlit application**:
   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run app.py
   ```
