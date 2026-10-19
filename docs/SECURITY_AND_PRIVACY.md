# Security and Privacy Architecture

The **Resume ATS Score Checker** is engineered with a strict **zero-retention, privacy-first** security model.

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
  - Documents exceeding this limit are halted immediately with HTTP `413 Content Too Large`.

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
- No resume documents are retained on server disks after the HTTP response is returned.

### 2.2 Log Sanitization
- **Rule**: Never write raw resume text, applicant names, email addresses, phone numbers, or job description text to server logs.
- **Enforcement**: Logging is configured to output only operational metadata:
  ```text
  2026-10-19 23:37:50 | INFO | [ats_checker] Analysis completed in 63.83ms | File: senior_resume.pdf | Type: .pdf | Size: 1730B | Words: 127 | Score: 69.3/100 (Good Match)
  ```

### 2.3 Local-First & Zero Paid AI Dependency
- The engine operates entirely locally using deterministic natural language heuristics.
- No resume data is transmitted to third-party AI APIs (e.g., OpenAI, Anthropic, or external cloud parsers).

---

## 3. Network & CORS Security

- Explicit CORS origins configuration (`CORS_ORIGINS`) allows connections only from trusted client origins (e.g. `http://localhost:3000`, `http://localhost:5173`).
- Wildcard `allow_origins=["*"]` is strictly avoided in production settings.

---

## 4. Text Extraction Limitations & Scanned Documents

- **Vector/Digital PDFs**: Fully supported. Text streams are parsed cleanly.
- **Scanned Image PDFs**: Standard PDF extraction libraries read character text streams. If a user uploads a scanned image or rasterized resume, `extract_resume_text` detects that the page contains virtually no text words and generates an extraction warning:
  > *"Document appears to be a scanned image with minimal readable text. Standard ATS systems cannot parse scanned resumes without OCR. Please use a text-based PDF or DOCX file."*
