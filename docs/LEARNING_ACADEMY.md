# AI Skills and Learning Academy

The authenticated Career OS workspace includes a Skills Academy for curated learning tracks, progress tracking, career-oriented recommendations, and platform learning records.

## Learning and recommendations

The Academy catalog contains technical and soft-skill tracks, short lessons, assessments, practical project prompts, and links to external learning resources. Track recommendations use resume text matches, saved career goals and preferred roles, existing skill progress, and any skill gaps supplied when generating a roadmap. Resume matches are evidence of text only, not verified proficiency.

Users can edit a saved roadmap's target role, goal, skill gaps, selected tracks, and track order. The original AI guidance remains visible and is labeled after editing; generating a new roadmap refreshes that guidance.

External resources and certification programs are links to their providers. The Academy does not claim that a user completed an external course or earned an external credential.

## AI features and privacy

Generating a personalized roadmap, asking the learning assistant, and evaluating a project description require AI profile sharing to be enabled in the existing Career Coach settings. These requests use the configured server-side AI provider; credentials are not sent to the browser. The service sends limited resume-derived skill/section evidence, relevant skill progress and career preferences, plus the content needed for the requested task. The assistant uses recent Academy conversation context.

Roadmaps, assessment submissions and results, project descriptions and evaluations, skill-evidence descriptions, and assistant conversations are stored in account-scoped Academy tables. Sensitive text is protected using the existing backend data-protection service. As elsewhere in the career platform, the backend encryption key must remain configured and backed up.

Project evaluation reviews the description and a transparent completeness rubric only. The Academy does not fetch project URLs, inspect repositories, execute project code, or verify authorship or claims.

## Assessments and coding practice

Knowledge assessments are scored against the fixed questions in the selected track. A passing result is recorded as Academy assessment evidence, not an external qualification.

Coding exercises currently cover Python. Submitted code is interpreted by a restricted AST evaluator against fixed cases; it is not run with Python `eval`/`exec` and is not a general-purpose execution environment. The evaluator supports a deliberately limited function and expression subset. Passing exercises count as platform practice evidence, not proof of professional proficiency.

## Skill evidence and certificates

Users may record project, portfolio, or external-certificate evidence. User-submitted evidence is labeled as unverified. Assessment evidence is labeled as platform assessment evidence and is not equivalent to independent professional verification.

A platform completion certificate is available only after completing all lessons and coding activities in a track and passing its assessment with at least 70%. The downloadable PDF identifies the record as a platform completion certificate and explicitly states that it is not an external, accredited, or professional certification.

## Persistence and API

The authenticated API is mounted under `/api/v1/career/academy`. Academy storage is introduced by the additive `0007_learning_academy.sql` migration. It adds account-scoped tables for activity progress, assessments, roadmaps, projects, skill evidence, completion certificates, and assistant messages; it does not change or remove existing records. The project applies pending numbered migrations through its existing database startup migration mechanism.
