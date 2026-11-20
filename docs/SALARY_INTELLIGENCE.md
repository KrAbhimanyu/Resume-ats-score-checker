# Salary and Negotiation Intelligence

The authenticated Career Platform exposes salary tools under `/api/v1/career/salary`.

- Salary benchmarks are descriptive statistics from authorized job listings already stored by the Career Platform. They retain source URLs, provider update dates, currency, reporting period, location, company, and experience metadata. AI interpretation is consent-gated and grounded in these disclosed listings; no estimate is returned when there are no matching ranges.
- Offers are stored per account with the existing encrypted career-data service. Offer records support multiple offers, editing, deletion, role/location/benefits/growth comparisons, total-compensation comparisons, and CSV export in the browser.
- Offer-letter analysis extracts text from text-based PDF or DOCX files in memory, highlights lines containing compensation-related terms, and does not persist the original document. After explicit user action, AI can explain the extracted terms when Career Coach consent is enabled. Scanned documents may not be readable.
- CTC and take-home calculations use user-entered annual components, a user-configured effective tax percentage, and monthly deductions. Take-home uses cash components; annualized equity is included in total compensation but excluded from monthly cash. Results do not encode current tax rules or constitute tax advice. Currency conversion is not performed.
- Salary growth outputs are arithmetic scenarios using the user's own rate and are not forecasts. Negotiation guidance uses the configured AI provider only after the account's existing Career Coach profile-sharing consent is enabled.
- The readiness score is a weighted preparation checklist, not a probability of success. All salary figures and AI drafts require user verification; salary outcomes are not guaranteed.

No new third-party services or package dependencies were added. The additive migration `0009_salary_intelligence.sql` creates the encrypted offer-record table.
