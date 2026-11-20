# Resume ATS Score Checker - Web Application

A responsive React + TypeScript + Vite web client for the **Resume ATS Score Checker** and targeted resume builder.

Built with accessible HTML/ARIA controls, deterministic resume analysis, and optional user-invoked AI writing.

---

## 1. Prerequisites

- **Node.js**: 18.0.0+ (Tested on Node.js v24.19.0)
- **npm**: 9.0.0+ (Tested on npm 11.17.0)
- **FastAPI Backend Server**: Running locally on `http://127.0.0.1:8000` (see [Backend Instructions](../README.md))

---

## 2. Installation & Setup

1. Navigate to the `web` directory:
   ```bash
   cd resume-ats-checker/web
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

---

## 3. Environment Configuration

Copy the sample environment file to create your local environment:
```bash
cp .env.example .env.local
```

Configurable variables:
- `VITE_API_BASE_URL`: Base URL of the backend API (defaults to `http://127.0.0.1:8000`).

---

## 4. Running the Application

### 4.1 Start the Backend Server (Terminal 1)
```bash
cd resume-ats-checker/backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```
Backend will be live at `http://127.0.0.1:8000` (`/docs` for Swagger UI).

### 4.2 Start the Web Frontend (Terminal 2)
```bash
cd resume-ats-checker/web
npm run dev
```
Open your browser at **[http://localhost:5173](http://localhost:5173)**.

---

## 5. Running Frontend Tests & Type Checking

### 5.1 Run TypeScript Type Checking
```bash
npm run typecheck
```

### 5.2 Run Vitest Unit & Component Tests
```bash
npm run test
```

### 5.3 Run Vitest in Watch Mode (Interactive)
```bash
npm run test:watch
```

---

## 6. Building for Production

Create an optimized, tree-shaken production bundle in `dist/`:
```bash
npm run build
```

Preview the production build locally:
```bash
npm run preview
```
Production preview runs at **[http://localhost:4173](http://localhost:4173)**.

---

## 7. Key Features Implemented

- **Landing Page**: Modern hero section, value propositions, and transparency disclosures.
- **Drag & Drop Resume Upload**:
  - Supports `.pdf` and `.docx` documents.
  - Enforces a 5 MB upload limit with user-friendly formatting and error messages.
  - Allows replacing or removing selected files.
- **Job Description Workspace**:
  - Multi-line textarea with live word and character counters.
  - Helpful validation indicators (minimum 5 words recommended).
- **Live 5-Layer ATS Scan**: Backend-emitted SSE events show file validation and extraction, section detection, keyword matching, impact analysis, scoring, and report generation as they run. The browser reconnects and replays events after network interruptions or page refresh; progress findings expose counts and skill/keyword terms, not extracted resume text or contact details.
- **Interactive Results Dashboard**:
  - **Estimated Resume–Job Match Score**: 0–100 circular gauge indicator with dynamic match tiers (`Exceptional`, `Strong`, `Good`, `Fair`, `Low`).
  - **5-Category Breakdown**: Earned vs maximum points, percentages, progress bars, and transparent explanations.
  - **Requirements & Keywords**: Matched requirements, missing mandatory/preferred requirements, and weakly evidenced items.
  - **Actionable Recommendations**: Prioritized suggestions (`High`, `Medium`, `Low`) that discourage keyword stuffing and dishonesty.
  - **Resume quality report**: Section review, grammar-pattern flags, approximate readability and impact signals, ATS compatibility checks, and final QA checklist.
  - **Professional summary draft**: Resume-derived text that candidates can copy and verify.
  - **Warnings & Disclaimers**: Scanned document warnings and methodology limitations.
  - **"Analyze Another Resume" Action**: Safely resets the form and view without persistent traces.
- **Targeted Resume Builder**:
  - Evidence-grounded summary and experience rewrites, achievement guidance, action-verb suggestions, and PDF/DOCX export.
  - Explicitly saved named resume versions, browser-local history, section-by-section comparison, restore, and export of saved versions.
- **Resume Studio**:
  - Build from scratch with editable profile, skills, experience, education, projects, certifications, and custom-section fields.
  - Browse industry-specific single-column ATS-safe templates, customize fonts and section order, and apply template styling in PDF/DOCX exports.
  - Fresher, experienced, executive, and career-change starter structures; five international date-format presets.
  - Use the backend-configured AI provider for summaries, experience and project rewrites, achievement/bullet optimization, skills guidance, and reviewable job-targeted optimization.
  - Save and duplicate multiple resume profiles locally; signed-in users can sync encrypted profiles and versions to their account.
  - Create editable cover letter, LinkedIn, and portfolio text drafts.
  - Resume translation is unavailable in local-only mode; the UI explains that full translation requires a translation model.
- **Privacy Controls**:
  - Uploaded files are processed by the backend and are not retained there; the analysis page does not store them.
  - Resume-version snapshots are written to browser `localStorage` when explicitly saved; signed-in users can also sync them encrypted to the authenticated account.
  - Browser-local history is not encrypted; clearing site data removes its local copy. Cloud persistence requires `JOB_DATA_ENCRYPTION_KEY`.
  - AI requests transmit the selected resume context and job description to the backend-configured OpenAI provider; never include confidential information.
  - No third-party tracking or analytics.
  - No resume text printed to the browser console.

---

## 8. Known Limitations

- **OCR for Scanned Documents**: Image-only PDF resumes without selectable text cannot be parsed without OCR; the app detects and displays an explicit warning.
- **Document page counts**: PDF pages are counted during extraction. DOCX does not expose a reliable rendered page count, so its live progress explicitly marks page count as unavailable while still reporting the extracted word count.
- **Text-only quality checks**: Pattern-based grammar/readability signals can be wrong and cannot inspect visual page layout, columns, tables, or graphics. Confirm suggestions yourself.
- **AI configuration**: AI writing requires `RESUME_AI_API_KEY`; without it, AI requests return an explicit configuration error. The API key is backend-only.
- **External AI processing**: When AI is used, resume details are sent to OpenAI under the operator's account and provider terms. Review outputs; model responses can still contain mistakes.
- **Browser-local history**: Without signing in to Career Platform, resume versions stay in the current browser and are not available on other devices.
- **Translation**: Translation is not simulated with an incomplete phrasebook.
- **Local Network Default**: In local development, the backend must be running on port 8000 or proxied via Vite.
