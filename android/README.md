# Native Android app

This directory contains a Kotlin/Jetpack Compose client for the existing FastAPI service. The Android app is an additional client; it does not replace the website, backend, or database.

## Architecture

- Single Android application module using Kotlin, Jetpack Compose, Material 3, and Navigation Compose.
- MVVM state management with `ViewModel`, coroutines, and `StateFlow`.
- Retrofit/OkHttp API client with Kotlin Serialization, a repository layer, and explicit HTTP error mapping.
- Bearer sessions are encrypted with AES/GCM using a key held by Android Keystore. Passwords are not persisted.
- Documents are selected with Android's Storage Access Framework and read into memory after the user chooses a file; the app does not create a temporary document copy.

## Configure and run

Requirements: Android Studio with Android SDK Platform 35, JDK 17, and Gradle 8.9. A Gradle wrapper is not included in this repository yet.

The default debug API URL is `http://10.0.2.2:8000/` for the Android emulator connecting to a backend on the host machine. Override it with a Gradle property or environment variable:

```powershell
gradle :app:installDebug -PAPI_BASE_URL=http://10.0.2.2:8000/
```

Run the command from this directory. For a physical device, use a reachable development-server address instead of `10.0.2.2`. The URL must end in `/`. Debug builds permit cleartext HTTP for local development; release builds reject non-HTTPS API URLs.

Do not put credentials, payment keys, or other secrets in Gradle properties committed to source control. The app has no frontend AI or payment credentials.

## Connected backend journeys

All paths below are relative to `/api/v1` and use the existing service:

| Android surface | Backend operations |
|---|---|
| Sign in, registration, and sign out | `POST /career/auth/login`, `POST /career/auth/register`, `GET /career/auth/me`, `POST /career/auth/logout` |
| Career dashboard | `GET /career/command-center` |
| Resume analysis and saved versions | `POST /analyze`, `GET /career/profile/resumes`, `POST /career/profile/resumes/upload` |
| Job search, saved jobs, matching, and resume tailoring | `POST /career/discover`, `/career/jobs/{id}/save`, `/career/jobs/match`, `/career/jobs/job/{id}/tailor`, `/career/tailoring/{id}`, `/career/tailoring/{id}/save-version` |
| Application tracker, notes, status history, interviews, and reminders | `/career/applications`, `/career/applications/{id}`, `/career/applications/{id}/history`, `/career/interviews`, `/career/reminders` |
| Career Coach, consent, goals, roadmaps, chat, and milestones | `/career/coach/state`, `/career/coach/consent`, `/career/coach/goals`, `/career/coach/roadmaps/generate`, `/career/coach/chat`, `/career/coach/milestones/{id}` |
| Learning Academy | `/career/academy/dashboard`, `/career/academy/tracks/{id}`, lessons, assessments, exercises, roadmaps, projects, evidence, and certificates |
| Personal branding | `/career/branding/dashboard`, `/career/branding/profile`, generation, and saved version APIs |
| Salary intelligence | `/career/salary/intelligence`, `/career/salary/offers`, `/career/salary/calculate`, `/career/salary/negotiation-guidance` |
| Career search and reminder preferences | `GET/PUT /career/profile/preferences` |
| Plan display, entitlements, and credits | `GET /career/business/plans`, `/career/business/status`, `/career/business/entitlements`, and `/career/business/credits` |

Resume analysis uses the existing public analysis endpoint; profile, job, career, salary, and account data use authenticated endpoints and the signed-in account. Job results and salary summaries are not fabricated; an empty result is shown when the service has none.

Job matching displays the backend's evidence-based compatibility and skill-gap result. Tailoring suggestions require an explicit per-edit approval; accepted changes save as a new resume version, leaving the source resume unchanged. Saved offers compare only in the same currency, with no assumed exchange rate. Academy evidence is marked user-submitted, and platform certificates are not represented as external accreditation.

## Current limitations and backend dependencies

- There is no password-recovery endpoint in the backend, so the app does not show a fake reset workflow.
- No general identity/profile edit endpoint is exposed; account email and identity remain read-only, while available career preferences are editable.
- Plans, subscription entitlement state, and credits are read-only. The backend currently provides web checkout flows; this app does not initiate checkout or claim payment success.
- The mobile client does not yet expose all backend capabilities, including interview history/rescheduling and the Academy learning assistant. No native notification/email delivery is claimed; reminder delivery remains backend-configured.
- The job provider sources available to the app depend on the backend's configuration and authorization.

No database migrations or production payment configuration are required for the Android client.
