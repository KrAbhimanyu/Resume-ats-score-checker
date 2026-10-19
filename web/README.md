# Web Client Foundation (React + TypeScript + Vite)

This directory serves as the responsive web frontend foundation for the **Resume ATS Score Checker**.

## Architectural Role

The web frontend communicates directly with the FastAPI backend service (`/api/v1/analyze` and `/api/v1/health`), providing a frictionless user experience across desktop and mobile browsers.

## Technology Stack (Milestone 2 Target)

- **Framework**: React 18+ with TypeScript
- **Bundler & Dev Server**: Vite
- **Styling**: Tailwind CSS / CSS Modules
- **State & Data Fetching**: React Query / Native Fetch API with typed schemas
- **Icons**: Lucide React

## Component Blueprint

```text
src/
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   └── Footer.tsx (includes limitations disclaimer)
│   ├── upload/
│   │   ├── ResumeUploader.tsx (Drag-and-drop, PDF/DOCX validation, 5MB limit)
│   │   └── JobDescriptionInput.tsx (Validation, minimum length check)
│   ├── results/
│   │   ├── OverallScoreCard.tsx (0-100 meter, Estimated Resume–Job Match Score label)
│   │   ├── CategoryBreakdown.tsx (5 categories: Keywords, Skills, Experience, Education, Structure)
│   │   ├── RequirementsList.tsx (Matched vs Missing requirements with evidence indicators)
│   │   └── RecommendationsSection.tsx (Prioritized, actionable improvement guidance)
│   └── common/
│       ├── LoadingSpinner.tsx
│       ├── ErrorAlert.tsx
│       └── WarningBanner.tsx (Scanned PDF / OCR alerts)
├── services/
│   └── atsApi.ts (Typed client for /api/v1 endpoints)
├── types/
│   └── ats.ts (Mirrors backend Pydantic models)
├── App.tsx
└── main.tsx
```

## Backend API Integration Contract

- **Health Check**: `GET /api/v1/health`
- **Analysis**: `POST /api/v1/analyze`
  - Request format: `multipart/form-data`
  - `resume_file`: Binary file (`.pdf` or `.docx`, max 5 MB)
  - `job_description`: String

## Planned Milestone 2 Execution

To initialize the frontend when starting Milestone 2:
```bash
cd web
npm create vite@latest . -- --template react-ts
npm install
npm run dev
```
