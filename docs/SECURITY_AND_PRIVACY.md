# Security and Privacy Architecture

The original **Resume ATS Score Checker** uses ephemeral server-side processing and opt-in browser-local version storage. The separately opt-in **Career Platform** persists user-owned resume and career data encrypted at rest; see [CAREER_PLATFORM.md](./CAREER_PLATFORM.md) for required configuration and limitations.

---

## 1. Threat Model & Safeguards

### 1.1 Malicious Upload & File Signature Validation
- **Risk**: Attackers uploading executable code, scripts, or polyglots renamed as `.pdf` or `.docx`.
- **Safeguard**: 
  - The server verifies binary magic numbers (signatures) before parsing:
    - **PDF**: Must begin with `%PDF-` (`0x25 0x50 0x44 0x46 0x2D`) in the first 1024 bytes.
    - **DOCX**: Must begin with the ZIP signature `PK\x03\x04` (`0x50 0x4B 0x03 0x04`) and must contain standard OpenXML components (`word/document.xml` or `[Content_Types].xml`).
  - File extension spoofing is detected immediately and rejected with HTTP `400 Bad Request`.

### 1.2 Resource Exhaustion & Denial of Service
- **Risk**: Oversized files or decompression bombs designed to consume server memory.
- **Safeguard**:
  - Upload size is capped at a strict configurable limit: `MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024` (5 MB).
  - Upload routes reject oversized request bodies before multipart parsing and read uploaded files in bounded chunks; documents exceeding the file limit return HTTP `413 Content Too Large`.

### 1.3 Execution Prevention
- **Risk**: Macros or embedded executable payloads running on the server.
- **Safeguard**:
  - The application uses pure-python extraction libraries (`pypdf`, `python-docx`) that parse data streams purely as text structures.
  - Macros, OLE objects, and external scripts are never evaluated or executed.

---

## 2. Privacy & Data Lifecycle

### 2.1 Zero File Retention
- Files uploaded for analysis are held in ephemeral memory or secure, randomized temporary files.
- All temporary files are managed via Python context managers (`safe_temp_file`) which guarantee immediate deletion in `finally` blocks, even if extraction or scoring throws an exception.
- The anonymous upload-and-analyze endpoint does not retain resume documents or extracted text after its response. The opt-in Career Platform is a separate authenticated flow that persists encrypted resume text and parsed records as described in section 2.5.

### 2.2 Log Sanitization
- **Rule**: Never write raw resume text, applicant names, email addresses, phone numbers, or job description text to server logs.
- **Enforcement**: Logging is configured to output only operational metadata:
  ```text
  2026-10-19 23:37:50 | INFO | [ats_checker] Analysis completed in 63.83ms | File: senior_resume.pdf | Type: .pdf | Size: 1730B | Words: 127 | Score: 69.3/100 (Good Match)
  ```

### 2.3 Explicit AI Resume Writing
- Standard ATS scoring and analysis remain deterministic. AI writing is an optional action in Resume Studio and is disabled until the backend operator configures `RESUME_AI_API_KEY`.
- Resume AI requires an authenticated Career Platform session, is limited to five requests per account per 15 minutes, and reserves two configured AI credits per successful operation.
- When a user explicitly requests an AI suggestion, the resume context and job description are transmitted from the backend to OpenAI using the operator's credentials. The key is never sent to or embedded in the frontend.
- AI output is displayed as a reviewable suggestion and is not applied automatically. Model responses may still be inaccurate; candidates must verify every claim and metric. Do not send confidential employer information.
- Configure `RESUME_AI_MODEL` and `RESUME_AI_TIMEOUT_SECONDS` on the backend. Provider data handling, availability, and charges are governed by the operator's OpenAI account and terms.

### 2.4 Explicit Resume Profiles and Versions
- Resume Studio profiles and resume snapshots are saved to browser `localStorage` after the user explicitly saves; local browser data is not encrypted.
- A user signed in through the Career Platform can explicitly sync profiles and versions to an authenticated account. Cloud document names and contents are Fernet-encrypted at rest using `JOB_DATA_ENCRYPTION_KEY` and scoped to the owning account.
- Clearing site data removes only the local copy; cloud records remain until explicitly deleted or the account is removed. Users should sign out on shared devices and protect account credentials.
- The standard upload-and-analyze flow does not save the selected source file or parsed resume in browser storage.
- Generated cover-letter, LinkedIn, and portfolio drafts remain in the current page until a profile is explicitly saved. Downloaded text files are controlled by the user.
- Resume AI writes are not sent to an external provider unless explicitly requested by the user and configured by the operator. Translation is not provided.

### 2.5 Authenticated Career Platform Storage
- Career Platform accounts are separate from the anonymous ATS analysis flow. Passwords are PBKDF2-SHA256 hashed; bearer session tokens are random and only their hashes are persisted.
- Resume text and parsed data, preferences, match evidence, private job descriptions, application/interview notes, meeting links, reminders, notifications, and tailoring reviews are Fernet-encrypted before SQLite persistence.
- `JOB_DATA_ENCRYPTION_KEY` is required for operations that persist encrypted values. It must be generated once, supplied via a secret manager or untracked environment file, and backed up. Losing or rotating the key without re-encrypting data makes those records unreadable.
- SQLite, its WAL/SHM files, backups, and hosting volumes still require restrictive filesystem permissions and encrypted backups. Field encryption is not a substitute for access controls, secure transport, CSP/XSS protections, or operational key management.
- Create database backups with SQLite's online backup API while the application is running, or stop all writers before taking a filesystem copy. Do not copy only the main database file while WAL writes may be pending. Validate each backup with `PRAGMA integrity_check`, compare its `schema_migrations` entries with the source, and keep the encryption key backed up separately.
- Test restores against a separate database path first. Before any production restore, stop writers, preserve the current database, restore and validate the chosen snapshot, and plan any pending migrations as a separate controlled operation. Integrity checks do not establish that a backup is current or complete.
- Legacy plaintext values, if any, are read for backward compatibility. This additive migration does not rewrite or erase existing records.
- The API does not claim email verification or password-reset support. Do not treat the current local-account flow as a complete enterprise identity system.

---

## 3. Network & CORS Security

- Explicit CORS origins configuration (`CORS_ORIGINS`) allows connections only from trusted client origins (e.g. `http://localhost:3000`, `http://localhost:5173`).
- Wildcard `allow_origins=["*"]` is strictly avoided in production settings.

---

## 4. Text Extraction Limitations & Scanned Documents

- **Vector/Digital PDFs**: Fully supported. Text streams are parsed cleanly.
- **Scanned Image PDFs**: Standard PDF extraction libraries read character text streams. If a user uploads a scanned image or rasterized resume, `extract_resume_text` detects that the page contains virtually no text words and generates an extraction warning:
  > *"Document appears to be a scanned image with minimal readable text. Standard ATS systems cannot parse scanned resumes without OCR. Please use a text-based PDF or DOCX file."*
