# LinkedIn and Personal Branding

The authenticated Career OS workspace adds a personal-branding dashboard under `/api/v1/career/branding`.

## Profile and AI drafts

Users maintain a unified professional profile using information they provide, including their own LinkedIn profile URL and profile text, and may review skill text matches from their saved resume. Profile strength is a transparent completeness checklist over saved sections; it is not a LinkedIn score, ranking, or prediction.

AI generation supports LinkedIn headlines, About and experience drafts, skill recommendations, profile optimization, personal-brand guidance, professional bios, portfolio project descriptions, and LinkedIn post drafts. Drafts are editable and account-scoped, with rename, save, duplicate, and delete operations. Generation uses the existing backend AI provider and requires AI profile sharing enabled in Career Coach settings. The AI receives the relevant saved profile and submitted task text. Generated content is not published.

The module does not scrape LinkedIn or claim to analyze private LinkedIn profile data. Users may enter the profile information they want analyzed. There is no configured LinkedIn API integration or automatic engagement-metrics access.

## GitHub public profile

GitHub analysis calls the public GitHub REST API for the submitted username. It reports public account fields and a sample of up to 100 recently updated public repositories. It does not access private repositories or code contents. Repository language summaries count each repository's primary-language label; they do not represent code volume. GitHub API rate limits and availability can temporarily prevent retrieval.

## Portfolio export

The portfolio action exports a standalone HTML file from the saved profile and requires explicit confirmation in the interface. A saved name and at least one professional section are required. Users can choose minimal, classic, or midnight themes and an accent color. User text is HTML-escaped. The platform creates a downloadable file only; it does not host, publish, or share the page.

## Brand growth analytics

Activity and engagement metrics can be recorded by the user from platforms they are authorized to access. Entries and their platform summaries are marked `user_reported`; no metrics are fabricated or represented as a live LinkedIn/GitHub integration. Users can delete their records.

## Persistence

The additive `0008_personal_branding.sql` migration introduces an encrypted account-scoped profile, encrypted and editable content versions, and user-reported activity metrics. Existing user data and integrations are preserved. The application's existing startup migration process applies pending numbered migrations. The existing `JOB_DATA_ENCRYPTION_KEY` configuration is required for encrypted profile and draft storage.
