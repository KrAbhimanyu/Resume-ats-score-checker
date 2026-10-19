# Resume ATS Score Checker

A production-oriented, explainable **Resume ATS Score Checker** with a responsive web dashboard, native Android application, and deterministic Python/FastAPI analysis engine.

Initial budget: ₹0. Built exclusively with free, open-source technologies, local processing, and zero paid AI API dependencies.

---

## 1. Project Architecture

```text
resume-ats-checker/
├── web/                  # Web Client (React, TypeScript, Vite - Milestone 2)
├── android/              # Native Android App (Kotlin, Jetpack Compose - Milestone 3)
├── backend/              # Analysis Engine & REST API (FastAPI, Python 3.13)
│   ├── app/
│   │   ├── api/v1/       # REST Endpoints (/health, /analyze)
│   │   ├── core/         # Security, errors, and privacy logging
│   │   ├── models/       # Pydantic schemas and response contracts
│   │   └── services/     # Extractor, parser, scoring, synonyms, recommendations
│   ├── requirements.txt
│   └── requirements-dev.txt
├── tests/                # Automated Test Suite (Pytest)
│   ├── fixtures/         # Sample resumes (.pdf, .docx) & jobs (fictional data only)
│   ├── unit/             # Extraction, synonyms, scoring tests
│   └── integration/      # Endpoint, health, and security limit tests
├── docs/                 # Engineering Specifications & Reports
│   ├── IMPLEMENTATION_STATUS.md
│   ├── SCORING_METHODOLOGY.md
│   └── SECURITY_AND_PRIVACY.md
├── .gitignore
└── README.md
```

---

## 2. Prerequisites

- **Python**: 3.11+ (Developed and tested with Python 3.13)
- **Node.js**: 18+ (Required for Milestone 2 Web Client)
- **Java / Android Studio**: JDK 17+ (Required for Milestone 3 Android Client)
- **Git**

---

## 3. Local Setup & Execution

### 3.1 Backend Setup

1. Open a terminal in the backend directory:
   ```bash
   cd resume-ats-checker/backend
   ```

2. Create and activate a virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install production and development dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

### 3.2 Running the Backend Server

Start the FastAPI application with Uvicorn:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The service will be accessible at:
- **Interactive OpenAPI Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 4. Running Automated Tests

Run the complete test suite from the `backend/` directory:
```bash
pytest -v ../tests
```

To run unit or integration tests selectively:
```bash
# Run unit tests only
pytest -v ../tests/unit

# Run integration tests only
pytest -v ../tests/integration
```

---

## 5. API Usage Examples

### 5.1 Health Check (`GET /api/v1/health`)

```bash
curl -X GET http://127.0.0.1:8000/api/v1/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-10-19T18:09:22.882656+00:00",
  "service": "Resume ATS Score Checker API"
}
```

### 5.2 Analyze Resume (`POST /api/v1/analyze`)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -F "resume_file=@../tests/fixtures/sample_resumes/senior_software_engineer.pdf" \
  -F "job_description=Senior Software Engineer with 4+ years experience in Python, FastAPI, React, Docker, and PostgreSQL."
```

**Response Overview**:
```json
{
  "overall_score": 82.5,
  "score_label": "Estimated Resume–Job Match Score",
  "match_tier": "Strong Match",
  "summary": "Your resume achieved an Estimated Resume–Job Match Score of 82.5/100 (Strong Match).",
  "category_scores": [
    {
      "category_id": "keyword_coverage",
      "category_name": "Job-Relevant Keyword Coverage",
      "score": 31.5,
      "max_score": 35.0,
      "percentage": 90.0,
      "explanation": "Matched 9 out of 10 key terms from the job description (90.0% coverage). Repeated occurrences in the resume do not artificially inflate the score."
    },
    {
      "category_id": "skills_match",
      "category_name": "Required and Preferred Skills Match",
      "score": 22.0,
      "max_score": 25.0,
      "percentage": 88.0,
      "explanation": "Matched 5 of 5 target core skills. Evaluated against primary core qualifications."
    },
    {
      "category_id": "experience_evidence",
      "category_name": "Relevant Experience Evidence",
      "score": 18.5,
      "max_score": 20.0,
      "percentage": 92.5,
      "explanation": "Experience section: Found. Action verbs identified: 4. Quantified achievements / metrics: 4."
    },
    {
      "category_id": "education_qualifications",
      "category_name": "Education and Qualifications",
      "score": 10.0,
      "max_score": 10.0,
      "percentage": 100.0,
      "explanation": "Education section: Present. Detected degrees: bachelor."
    },
    {
      "category_id": "document_structure",
      "category_name": "Document Structure and Readability",
      "score": 9.0,
      "max_score": 10.0,
      "percentage": 90.0,
      "explanation": "Identified 4 standard resume sections (experience, education, skills, summary). Word count is 127 words with 4 bulleted entries."
    }
  ],
  "matched_requirements": [ ... ],
  "missing_requirements": [ ... ],
  "keywords_found": ["aws", "ci/cd", "docker", "fastapi", "git", "kubernetes", "postgresql", "python", "react"],
  "recommendations": [ ... ],
  "document_metadata": {
    "filename": "senior_software_engineer.pdf",
    "file_type": ".pdf",
    "file_size_bytes": 1730,
    "character_count": 894,
    "word_count": 127,
    "extraction_warnings": []
  },
  "limitations_disclaimer": "This score is an Estimated Resume–Job Match Score calculated via deterministic heuristic analysis. It does not represent a proprietary employer ATS system, a hiring guarantee, or an interview prediction."
}
```

---

## 6. Supported File Types & Extraction Behavior

- **Supported Formats**: `.pdf` (text-based/vector) and `.docx` (Microsoft Word).
- **Binary Signature Checks**: Files are validated using binary magic bytes (`%PDF-` and `PK\x03\x04` with OpenXML structures), rejecting disguised executables or text files.
- **Upload Limit**: 5 MB default (configurable via `MAX_UPLOAD_SIZE_BYTES`).
- **Scanned PDF Handling**: Detects image-only/scanned PDFs and provides a user-facing warning that OCR is required.
- **Empty / Insufficient Documents**: Rejects documents with fewer than 30 readable words with helpful guidance.

---

## 7. Security and Privacy Guarantees

1. **Zero Data Retention**: Uploaded documents are analyzed ephemerally and deleted immediately.
2. **Safe Temporary Files**: Handled through guaranteed context-manager cleanup (`safe_temp_file`), even in error conditions.
3. **No PII in Logs**: Resume text, applicant names, email addresses, and phone numbers are never logged.
4. **Local Execution**: No resume content is sent to third-party commercial AI APIs.
5. **Configurable CORS**: Restricts frontend origins to authorized domains.

---

## 8. Current Implementation Status

- [x] **Milestone 1**: Complete backend foundation, text extractor, synonym service, 5-category scoring engine, grounded recommendation engine, REST API, test fixtures, and automated test suite (32 tests passing).
- [ ] **Milestone 2**: React + TypeScript + Vite responsive web frontend.
- [ ] **Milestone 3**: Native Android application (Kotlin + Jetpack Compose).
