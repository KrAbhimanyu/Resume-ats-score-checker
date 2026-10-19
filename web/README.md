# Resume ATS Score Checker - Web Application

A responsive, production-oriented React + TypeScript + Vite web client for the **Resume ATS Score Checker**.

Built with modern SaaS aesthetics, accessible HTML/ARIA controls, zero persistent resume storage, and ₹0 external dependencies.

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
- **Interactive Results Dashboard**:
  - **Estimated Resume–Job Match Score**: 0–100 circular gauge indicator with dynamic match tiers (`Exceptional`, `Strong`, `Good`, `Fair`, `Low`).
  - **5-Category Breakdown**: Earned vs maximum points, percentages, progress bars, and transparent explanations.
  - **Requirements & Keywords**: Matched requirements, missing mandatory/preferred requirements, and weakly evidenced items.
  - **Actionable Recommendations**: Prioritized suggestions (`High`, `Medium`, `Low`) that discourage keyword stuffing and dishonesty.
  - **Warnings & Disclaimers**: Scanned document warnings and methodology limitations.
  - **"Analyze Another Resume" Action**: Safely resets the form and view without persistent traces.
- **Strict Client-Side Privacy**:
  - Resumes are never persisted in `localStorage` or `sessionStorage`.
  - No third-party tracking or analytics.
  - No resume text printed to the browser console.

---

## 8. Known Limitations

- **OCR for Scanned Documents**: Image-only PDF resumes without selectable text cannot be parsed without OCR; the app detects and displays an explicit warning.
- **Local Network Default**: In local development, the backend must be running on port 8000 or proxied via Vite.
