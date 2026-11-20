# AI Job Intelligence & Application Management

The Career Platform extends the existing React application and FastAPI service. It is an opt-in authenticated workspace; the pre-existing anonymous ATS analysis and resume-builder endpoints remain available and their contracts are unchanged.

## What is implemented

- Email/password account registration, login/logout, hashed bearer sessions, account scoping, and per-IP registration/login attempt limits.
- Encrypted-at-rest resume text and parsed resume data, job-search preferences, match evidence, recommendation explanations, private job descriptions, application notes/history notes, skill notes, interview links/details/preparation notes, reminders, notifications, and tailoring reviews.
- Additive SQLite migrations; existing data is not deleted or reset.
- Real provider adapters for Adzuna and authorized employer-specific Greenhouse and Lever boards. Listings retain source attribution, provider identifiers, URLs, and posting timestamps. Provider results are cached and throttled.
- Job discovery supports provider pagination, company, location/country, remote mode, employment type, explicitly indicated experience level, disclosed salary/currency, and sorting filters. Duplicate URLs and matching title/company/location listings are collapsed where possible.
- Related listing recommendations compare extracted skills and role-title terms. Recent skill, role, and category demand counts use only dated, non-expired records from configured authorized feeds and show the sample size.
- Optional AI recommendation re-ranking uses the existing OpenAI backend configuration only after the user opts in; it may reorder up to 30 real listings and cannot create listings or change compatibility evidence.
- Deterministic resume/job matching, job-description extraction, recommendation factors, skill-gap progress, approved-only resume tailoring, and PDF/DOCX export through the existing exporter.
- Persistent saved jobs, application status history, interviews, reminders, disclosed-listing salary summaries, and account-derived analytics. A deadline alert can be created only when the listing source supplies a valid future deadline.
- Application automation includes a persistent tracker with saved, applied, shortlisted, assessment, interview, offer, rejected, and withdrawn stages; resume associations; application notes and activity history; analytics; reminders; and a transparent priority queue based on recorded stage, available match evidence, user preferences, and source-provided deadlines.
- The Premium Career Command Center combines saved resume/profile, skills, learning activity, application analytics, coach goals and milestones, existing personalized job recommendations, notifications, and a chronological timeline without duplicating those records. Its five-part, evidence-based career score has equal 20-point defaults and user-configurable weights totaling 100; it is not an employability or hiring score.
- The command center records achievements only after corresponding persisted activity exists, dates awards using the qualifying source activity, and derives learning/career streaks from dated activity records. Professional evidence distinguishes assessment-verified platform evidence from user-submitted credentials; the trust indicator counts only platform assessment evidence and platform learning certificates, not unverified claims or external accreditation.
- The career timeline combines account-owned resume, job-search, application, coach milestone/goal, skills, learning, interview, and personal-brand activity. It is returned newest-first in pages of 50 with an older-activity control.
- In-app and email reminder preferences are persisted by reminder category and applied when reminders trigger. Email still requires an individually email-requested reminder and configured SMTP delivery.
- Consented AI application assistance generates editable next-step guidance, cover letters, application emails, recruiter follow-ups, and interview follow-ups from application details and the selected/primary resume. Users can revise and securely save multiple drafts per application; interview follow-up generation requires an existing interview record.
- AI-generated application drafts are not sent or submitted. Users must review the content and complete application or email actions themselves through the appropriate authorized service or source application page.
- Responsive application navigation for discovery, recommendations, job analysis, saved jobs, application tracking, interviews, reminders, company context, salary data, analytics, resume profiles, and preferences.
- An authenticated AI Career Coach with user-managed goals, archived goal history, regenerable and editable roadmap versions, editable milestones, progress tracking, career-path and transition suggestions, next-role options, strengths and development areas, actionable plans, daily tasks, structured career-decision chat, and readiness indicators.
- Career coach goals, roadmap content, milestone text, and conversation history are encrypted at rest. AI profile sharing is disabled until the user explicitly enables it; the user can revoke consent in the coach workspace.
- Coach roadmaps use the configured AI provider and are grounded in the selected resume, career preferences, saved skill progress, application history, target-role requirements, and a disclosed sample of recent authorized job listings. Readiness is deterministic: it uses the existing resume/job match when a job description is supplied, otherwise it reports profile completeness rather than job suitability.
- Company intelligence searches and attributes public company profile facts through the Wikidata API, caches profiles for up to 24 hours, and combines them with source-attributed authorized job listings already retrieved by this installation. Users can save target companies, compare up to four profiles, review dated hiring samples and disclosed salary listings, and request a role-specific resume review from an actual listing. Optimizer reviews reuse the existing approval and resume-version workflow; the FAANG-style option adds evidence-based technical-role guidance without claiming to reproduce proprietary hiring scores.
- The company research assistant reuses the configured Career Coach AI provider and requires the same explicit AI profile-sharing consent. It receives resume-derived skill/section evidence, career goals and progress, selected company facts, and source-attributed listing evidence. Saved target-company facts are also included in consented Career Coach context.
- Company culture, employee sentiment/reviews, verified interview processes and experiences, interview-question banks, and validated promotion paths remain explicitly unavailable because no authorized provider for those facts is configured. Preparation topics are labeled as skills extracted from actual job descriptions, not as confirmed interview questions.
- FastAPI request/response validation and OpenAPI documentation.

## Business and Revenue

The authenticated plans and billing workspace is available under **Plans & billing**. Its API is mounted at `/api/v1/career/business`; the additive SQLite schema is introduced in `0012_business_revenue.sql` and extended by `0013_stripe_checkout.sql`. No existing records are overwritten and migrations are applied by the normal application migration runner, not manually.

- Plans are administrator-configured. No monetary prices or paid plans are seeded; plan amounts, currency, included credits, and JSON feature entitlements must be explicitly supplied by an allowlisted administrator. Monetary amounts use the currency's minor unit.
- Razorpay is used for INR checkout when configured; Stripe-hosted Checkout is available for other supported currencies when backend credentials and trusted return URLs are configured. One-time orders are activated only after provider API verification or a valid signed webhook. Stripe webhook signatures are timestamp-checked and event IDs are persisted for replay protection. Stripe subscriptions support checkout, renewal/payment-state updates, and period-end cancellation; Razorpay supports its configured subscription lifecycle and scheduled plan changes.
- Stripe Checkout sessions use server-calculated prices and metadata, and the browser never grants entitlements. Subscription credits and transaction history are updated only from verified provider events or server-side verification. Merchant secrets remain backend-only; no card details are stored by this application.
- Configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, and `BUSINESS_ADMIN_EMAILS` on the backend only. Register `/api/v1/career/business/webhooks/razorpay` in the Razorpay merchant dashboard with the same webhook secret and enable the required payment captured/failed, subscription, and refund events. Keep the key ID public only as required for checkout; never put the secret or webhook secret in frontend configuration.
- For Stripe, configure `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and both `BUSINESS_CHECKOUT_*_URL` values on the backend. Register `/api/v1/career/business/webhooks/stripe` and enable Checkout Session completion/expiration, invoice paid/payment-failed, subscription created/updated/deleted, and refund events. Use Stripe test-mode credentials until live collection is explicitly approved.
- Administrators can create monthly, yearly, and one-time plans, publish/disable plans, configure coupons and AI-operation credit costs, set optional per-operation entitlement requirements, set free monthly credits and referral rewards, review institutional requests and marketplace listings, manage affiliates/commissions, and view captured revenue and refund reconciliation.
- The signed checkout flow never trusts browser-reported payment status. Full refunds are sent to the originating provider by an allowlisted administrator; provider-pending refunds remain pending until the signed webhook confirms their outcome. Credit-package refunds are blocked until a separate credit balance reconciliation is completed. No card details are stored.
- AI-credit reservations are enforced on the server for authenticated AI Career Coach, recommendation re-ranking, application drafting, resume writing, salary guidance, company research, learning assistance/project evaluation, and personal-brand generation requests. Credits are deducted only after a successful provider result; failed operations release reservations. Costs and optional required entitlements are administrator-configurable. Resume-writing pricing is seeded by migration `0016_resume_writing_ai_pricing.sql`.
- Referral rewards are issued once after a referred account's first captured payment. Approved affiliates can use their referral code; their commission remains pending until administrator reconciliation. Marketplace listings are inactive until approved, and marketplace checkouts use verified Razorpay or Stripe sessions. Order updates and dispute events are account-scoped.
- Student, enterprise, recruitment, and university offerings are handled as submitted partnership/pricing requests; this implementation does not automate third-party student-status verification. Provider service fulfillment, cancellation decisions, disputes, and affiliate payouts require administrator/provider follow-up; marketplace payments are not escrowed.
- Recurring checkout and cancellation require configured provider credentials and a valid signed webhook. Scheduled plan changes currently remain Razorpay-only. Recurring coupons are not applied by this checkout. Fixed coupon amounts and all configured plan prices are entered in currency minor units.
- Stripe return URLs must be explicitly configured. The success URL must contain Stripe's `{CHECKOUT_SESSION_ID}` placeholder; only HTTPS URLs are accepted outside localhost. Stripe payment acceptance depends on the merchant account, currency availability, tax setup, and current provider terms. GST/tax calculation and compliant invoice generation are not implemented; do not treat transaction history as a tax invoice.

| Capability | Endpoints |
|---|---|
| Plans and access | `GET /business/status`, `GET /business/plans`, `GET /business/entitlements` |
| Credits and usage | `GET /business/credits`; credit reservations wrap supported authenticated AI operations |
| Payment and transaction history | `POST /business/checkout`, `POST /business/checkout/verify`, `GET /business/transactions` |
| Recurring subscriptions | `POST /business/subscriptions/checkout`, `POST /business/subscriptions/verify`, `GET /business/subscriptions`, `POST /business/subscriptions/{id}/cancel`, `POST /business/subscriptions/{id}/change` |
| Stripe Checkout verification | `POST /business/stripe/checkout/verify` |
| Payment provider | Signed Razorpay webhook `POST /business/webhooks/razorpay`; signed Stripe webhook `POST /business/webhooks/stripe` |
| Referrals and affiliates | `POST /business/referrals/claim`, `GET /business/referrals`, `POST/GET /business/affiliates` |
| Institutional programs | `POST/GET /business/leads` |
| Marketplace | `GET /business/marketplace`, `POST /business/marketplace/listings`, `POST /business/marketplace/{listing_id}/orders`, `GET /business/marketplace/orders`, `PATCH /business/marketplace/orders/{order_id}` |
| Administration | `/business/admin/*` endpoints require an email in `BUSINESS_ADMIN_EMAILS`; include plan, pricing, coupon, settings, lead, listing, affiliate, transaction, refund, and revenue operations |

## Important product and data limitations

- Resume matching, parsing, default recommendations, and tailoring are deterministic local rules. AI recommendation re-ranking is optional, requires backend `RESUME_AI_API_KEY`, and is used only after explicit user opt-in. Scores are evidence comparisons, not hiring guarantees.
- When AI re-ranking is explicitly selected, limited resume evidence, saved preferences, and up to 30 listing summaries are sent to the configured OpenAI provider. Review provider data terms before enabling this option; without opt-in, resume evidence stays on the backend for deterministic matching.
- Career Coach AI requests require a separate persisted user consent setting. If enabled, resume excerpts (with email addresses, phone numbers, and profile links redacted), career goals, skill progress, a limited application history, and the request context may be sent to the configured OpenAI provider. AI-generated growth insights are possibilities, not employment, salary, or promotion guarantees; the market sample is limited to recently stored authorized listings.
- AI application drafting uses the existing Career Coach provider and requires the same explicit persisted consent. If enabled, the application and job context plus selected resume evidence (with email addresses and phone numbers redacted) may be sent to the configured provider. Generated text may contain errors and must be reviewed. Draft content is encrypted at rest; deleting a draft removes that stored draft. Application prioritization is a local heuristic, not an AI decision, and only uses deadlines supplied by a source.
- The command-center career score checks for a saved resume, a saved target role or career goal, tracked or resume-documented skills, an application or saved job, and a completed learning activity or career milestone. Users can configure each check's weight; weights must total 100. The evidence traceability indicator awards 20 points per distinct platform assessment-verified skill, then 10 per platform-issued learning certificate track until its total reaches 100; it is not a general reputation assessment. User-submitted certificates remain unverified unless an authorized verification integration is added.
- Wikidata is used only for public profile facts such as a company description, industry, headquarters, employee count, official website, and inception date; each profile links to its Wikidata source and shows its retrieval/source-modification time. Wikidata facts can be incomplete or community-maintained. Company hiring, skill, and compensation observations use only current authorized listings present in this installation and are a search-dependent sample, not a census. Predicted provider salary ranges are labeled separately from employer-reported ranges.
- No authorized culture/review/interview-experience provider is integrated; those fields are returned as unavailable rather than inferred or fabricated. AI company guidance is a synthesis, not an endorsement, verified hiring fact, or guarantee.
- Salary output aggregates only salary ranges disclosed in authorized listings. It is not a market-wide estimate and does not fabricate values.
- Current Adzuna, Greenhouse, and Lever adapters generally do not expose application deadlines. In that case the UI does not show a deadline alert action; it never infers a deadline from a posting date.
- Market-demand counts are a sample of listings recently retrieved into this installation, not complete labor-market statistics. The configured providers, countries, and prior search coverage limit representativeness.
- Adzuna is disabled unless credentials and an explicit commercial-use confirmation are configured. Its actual country availability, commercial permission, pricing, quota, and current rights must be verified by the operator. The default country is `gb`; India coverage is not assumed.
- Greenhouse and Lever are enabled only for configured employer boards with an explicit permission confirmation. These are not general job feeds.
- Remotive and Arbeitnow are intentionally not integrated because the reviewed public material did not establish permission for commercial republication. Do not scrape job websites or bypass their controls.
- Email verification and password reset are not implemented. Account email ownership is not verified.
- The reminder worker runs inside the FastAPI process. For multi-instance production deployment, move reminder processing to a singleton worker or durable queue before scaling horizontally.
- SQLite is suitable for local/single-instance use; use a managed transactional database and an operational backup/migration plan before a multi-instance deployment.
- The browser stores the bearer token in `sessionStorage` for the current tab session. Apply a strict Content Security Policy and protect against XSS before production exposure.
- Admin dashboards and usage/cost monitoring for an AI provider are not included. AI provider charges and retention terms depend on the operator's OpenAI account.

## Configuration and secure startup

Copy [`backend/.env.example`](../backend/.env.example) to `backend/.env` and set `JOB_DATA_ENCRYPTION_KEY` before using resume persistence, preferences, matching, or other private career functions:

```powershell
cd backend
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set the generated key in the process environment or a secret manager. Do not commit the real `.env` file. Keep the key stable and back it up separately from the SQLite database. The application rejects encrypted-data operations with HTTP 503 when the key is absent or invalid; it does not silently store those fields in plaintext. Values encrypted by an old key cannot be decrypted with a new key; key rotation requires an explicit decrypt/re-encrypt operation and backup.

The default database path is `backend/data/job-intelligence.sqlite3`. Migrations are additive and run during FastAPI startup. `JOB_DATABASE_PATH` can be set to an absolute path for deployment.

Optional variables:

| Variable | Purpose |
|---|---|
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Adzuna API credentials |
| `ADZUNA_COMMERCIAL_USE_CONFIRMED` | Operator confirmation of currently valid commercial-use rights |
| `ADZUNA_COUNTRIES` | Explicitly enabled two-letter provider country codes |
| `ADZUNA_MIN_INTERVAL_SECONDS`, `COMPANY_BOARD_MIN_INTERVAL_SECONDS` | Provider request throttling |
| `JOB_SEARCH_CACHE_SECONDS` | Provider-result cache duration |
| `JOB_MATCH_WEIGHT_SKILLS`, `JOB_MATCH_WEIGHT_EXPERIENCE`, `JOB_MATCH_WEIGHT_RESPONSIBILITIES`, `JOB_MATCH_WEIGHT_EDUCATION`, `JOB_MATCH_WEIGHT_CERTIFICATIONS`, `JOB_MATCH_WEIGHT_KEYWORDS`, `JOB_MATCH_WEIGHT_LOCATION` | Relative deterministic score weights; active factors are normalized |
| `CAREER_BOARD_PERMISSION_CONFIRMED` | Explicit permission gate for configured employer boards |
| `GREENHOUSE_BOARD_TOKENS`, `LEVER_SITE_NAMES` | Authorized employer-specific boards/sites |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | Optional in-app reminder email delivery |
| `RESUME_AI_API_KEY`, `RESUME_AI_MODEL`, `RESUME_AI_TIMEOUT_SECONDS` | Optional, explicitly requested AI re-ranking of real job listings |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Optional INR checkout and recurring billing credentials |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Optional Stripe Checkout and signed billing webhook credentials |
| `BUSINESS_CHECKOUT_SUCCESS_URL`, `BUSINESS_CHECKOUT_CANCEL_URL` | Trusted HTTPS return URLs; success URL must contain `{CHECKOUT_SESSION_ID}` |

Never set a permission confirmation merely to make a provider show as enabled. Confirm the provider's current terms and the specific employer's permission first.

Provider documentation reviewed for the adapters and exclusions:

- [Adzuna API overview](https://developer.adzuna.com/overview)
- [Greenhouse job board API](https://docs.greenhouse.io/job-board.html)
- [Lever postings API](https://github.com/lever/postings-api)
- [Remotive public API](https://remotive.com/remote-jobs/api) — not enabled; public redistribution terms do not authorize a third-party job board.
- [Arbeitnow API information](https://arbeitnow.com/blog/job-board-api) — not enabled because the reviewed public material did not establish commercial republication rights.

Documentation does not grant a license. Recheck each provider's live terms, commercial usage rights, country coverage, pricing, quotas, and employer permissions before enabling the integration in production.

## API reference

All career endpoints are under `/api/v1/career`; authentication uses `Authorization: Bearer <access_token>`. The interactive schema is available at `/docs` and `/openapi.json`.

| Capability | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Profile and resume versions | `GET/PUT /profile/preferences`, `POST /profile/resumes`, `POST /profile/resumes/upload`, `GET/DELETE /profile/resumes/{resume_id}` |
| Providers and discovery | `GET /providers`, `POST /discover`, `GET /jobs/recommendations?use_ai=false` (opt-in `use_ai=true`), `GET /jobs/job/{job_id}/similar`, `GET /market/demand` |
| Job descriptions and matching | `POST /jobs` (private entry), `POST /jobs/analyze`, `POST /jobs/analyze-url`, `POST /jobs/match`, `GET /jobs/matches`, `GET /jobs/job/{job_id}` |
| Saved jobs and skills | `POST/DELETE /jobs/{job_id}/save`, `GET /jobs/saved`, `POST /jobs/{job_id}/dismiss`, `GET /skills/progress`, `PUT /skills/{skill}/progress` |
| Company and salary | `GET /companies/{company_name}/research`, `GET /salary/intelligence` |
| Applications | `GET/POST /applications`, `PATCH /applications/{application_id}`, `GET /applications/{application_id}/history`, `POST /applications/{application_id}/draft`, `GET/POST /applications/{application_id}/drafts`, `PUT/DELETE /applications/{application_id}/drafts/{draft_id}`, `GET /applications/priorities` |
| Interviews and reminders | `GET/POST /interviews`, `PATCH /interviews/{interview_id}`, `GET /interviews/{interview_id}/history`, `GET/POST /reminders` (including provider-supplied job deadlines), `PATCH /reminders/{reminder_id}`, `GET /notifications` |
| Analytics | `GET /analytics`, `GET /analytics/search`, `GET /applications/analytics` |
| Premium Career Command Center | `GET /command-center?timeline_offset=0&timeline_limit=50`, `PUT /command-center/career-score-weights`, `PATCH /command-center/notifications/{notification_id}/read`, `GET/PUT /command-center/notification-preferences` |
| Tailoring | `POST /jobs/job/{job_id}/tailor`, `GET/PATCH /tailoring/{session_id}`, `POST /tailoring/{session_id}/save-version` |
| AI Career Coach | `GET /coach/state`, `PUT /coach/consent`, `POST /coach/goals`, `PATCH /coach/goals/{goal_id}`, `POST /coach/roadmaps/generate`, `PUT /coach/roadmaps/{roadmap_id}`, `POST /coach/roadmaps/{roadmap_id}/milestones`, `PATCH /coach/milestones/{milestone_id}`, `POST /coach/chat` |

## Run and validate

```powershell
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd web
npm install
npm run dev
```

Run backend tests from the repository root with `python -m pytest -q`; run the web checks from `web/` with `npm test` and `npm run build`.
