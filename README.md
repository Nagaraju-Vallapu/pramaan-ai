# Pramaan AI

### AI-Powered Regulatory Document Verification and Compliance Platform

**Smart India Hackathon 2026 · Problem Statement PS 26261 · Smart Automation**

Pramaan AI is a local MVP designed to support application validation, document authentication workflows, and regulatory compliance checks for the AICTE approval process.

<<<<<<< HEAD
> **Important:** Pramaan AI is a review-support prototype, not an official AICTE service, an authenticity guarantee, or an automated institution approval/rejection system. Its compliance rules are illustrative and configurable. Issuer verification uses clearly labelled synthetic local records only.
=======
- Protected FastAPI APIs for applications, document upload/processing, validation, review actions, synthetic issuer checks and audit history. Dashboard metrics include status distribution, recent activity and recent findings derived from persisted records.
- Local SQLite persistence with SQLAlchemy models; first startup creates missing tables. Use Alembic before managing production schema changes.
- PDF text extraction with PyMuPDF; image/scanned-page OCR with Tesseract when installed. OCR absence is returned as `OCR_UNAVAILABLE` and never represented as successful extraction.
- Responsive React + TypeScript dashboard backed by the API.
- Password-hashed local admin/reviewer credentials and signed, expiring bearer tokens. Admins create cases, upload documents, run validation and initiate synthetic checks; reviewers inspect cases and findings and record review actions.
- Admin-managed Reviewer, Viewer and additional Admin accounts with persistent storage, backend role enforcement, session revocation on deactivation and account audit history.
- Synthetic demo scenarios for missing, expired, mismatched, duplicate, suspicious-metadata, manual-review, synthetic issuer match/mismatch/not-found cases.
>>>>>>> 86e45bb (Complete Pramaan AI compliance workflow and UI improvements)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [Demo Workflow](#demo-workflow)
- [Testing](#testing)
- [Environment Configuration](#environment-configuration)
- [Security and Limitations](#security-and-limitations)
- [Future Enhancements](#future-enhancements)

## Overview

Manual document verification can involve repetitive checks and make it difficult to identify missing information, expired documents, inconsistencies, and potential anomalies.

Pramaan AI aims to streamline this workflow through document processing, configurable validation rules, evidence-linked findings, and human review. It helps authorized reviewers identify cases that may require correction, additional verification, or closer examination.

The prototype uses synthetic or authorized sample data and does not assume access to restricted AICTE systems.

## Features

### Document Processing
- Upload PDF, PNG, JPG, and JPEG files.
- Extract embedded PDF text using PyMuPDF.
- Extract text from scanned pages and images using Tesseract OCR when installed.
- Extract supported fields such as institution name, certificate number, issue date, and expiry date.
- Report unavailable OCR or extraction results explicitly instead of inventing document content.

### Validation Engine
- Detect missing mandatory documents and required fields.
- Check document expiry dates and unparseable dates.
- Identify duplicate files using SHA-256 hashes.
- Flag institution-name mismatches and low-confidence extraction.
- Identify suspicious metadata indicators for further review.
- Apply configurable illustrative rules.

### Dashboard and Application Management
- Responsive React and TypeScript dashboard.
- Application listing, overview, and application details.
- Document upload, extracted-field display, and validation results.
- Compliance statuses and evidence-linked findings.

### Synthetic Issuer Verification
- Match, mismatch, not-found, and manual-review outcomes.
- Uses a local synthetic issuer dataset.
- Clearly labels results as **SIMULATED — SYNTHETIC TEST DATA**.
- Does not claim live verification against AICTE or external issuers.

### Review and Audit
- Reviewer actions include acknowledging, confirming, resolving, requesting correction, and requesting manual verification.
- Findings include rule identifiers, severity, reasons, source documents, page or field references, evidence, and recommended actions where available.
- Audit events record key operations, including application creation, document uploads, validation, verification, and reviewer actions.

### Security Controls
- Password-hashed local admin and reviewer credentials.
- Signed, expiring bearer tokens.
- Role-based access restrictions.
- Upload extension, MIME type, signature, size, and format checks.
- Private backend-managed document storage and authenticated downloads.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| PDF text extraction | PyMuPDF |
| Image and scanned-document OCR | Tesseract OCR, when installed |
| Authentication | PBKDF2-SHA256 password hashing and signed bearer tokens |
| Testing | Pytest, HTTPX |
| Frontend checks | ESLint, TypeScript, Vite production build |

## Project Structure

```text
pramaan-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI endpoints
│   │   ├── core/             # Configuration, database, authentication
│   │   ├── models/           # SQLAlchemy models
│   │   ├── rules/            # Validation rules and synthetic issuer data
│   │   └── services/         # Document, OCR, validation, verification, audit
│   ├── tests/                # Backend tests
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
├── frontend/
│   └── src/                  # React dashboard and API client
├── docs/
│   ├── architecture.md
│   └── API.md
├── .gitignore
└── README.md
```

*Note: The tree highlights major project components. Refer to the repository for the complete file layout.*

## Prerequisites

Install the following:

- Python 3.11 or later.
- Node.js 20.19 or later; Node.js 24 is also supported.
- npm.
- Git.
- Tesseract OCR for scanned-document and image OCR (optional for startup).

## Installation and Setup

Run the following commands in Windows PowerShell from the repository root.

### 1. Create and activate a Python virtual environment

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If Python 3.13 is unavailable, use another installed Python version that meets the requirements.

### 2. Install backend dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

### 3. Configure environment variables

```powershell
Copy-Item backend\.env.example backend\.env
```

The example configuration contains public development-only credentials and a demo signing key. Replace them before using the application beyond a local demonstration.

To generate a password hash, run:

```powershell
Set-Location backend
python -m app.password_hash
```

Follow the prompts and copy the resulting hash into the appropriate setting in `backend\.env`:

- `PRAMAAN_ADMIN_PASSWORD_HASH`
- `PRAMAAN_REVIEWER_PASSWORD_HASH`

Set the corresponding usernames as required.

Generate a random signing secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `PRAMAAN_TOKEN_SECRET`.

<<<<<<< HEAD
Return to the repository root when needed:
=======
### Tesseract OCR

Install the Windows Tesseract distribution if it is not already present:
>>>>>>> 86e45bb (Complete Pramaan AI compliance workflow and UI improvements)

```powershell
Set-Location ..
```

<<<<<<< HEAD
### 4. Install frontend dependencies
=======
Restart the backend after installation. The app searches `PATH` and the standard `C:\Program Files\Tesseract-OCR\tesseract.exe` location automatically. For a custom install, set `PRAMAAN_TESSERACT_CMD` in `backend\.env`. OCR tests run against generated synthetic images when Tesseract is available; the missing-engine behavior test remains covered when it is not. Without the native engine, digital-PDF text processing still works; scanned pages and images return `OCR_UNAVAILABLE` and require manual review. The backend never fabricates extracted content.

### Start the API and frontend

In the first PowerShell window:
>>>>>>> 86e45bb (Complete Pramaan AI compliance workflow and UI improvements)

```powershell
Set-Location frontend
npm ci
```

If the repository does not contain a compatible `package-lock.json`, use `npm install` instead.

## Running the Application

Keep the backend and frontend running in separate PowerShell terminals.

### Terminal 1: Start the backend

From the repository root:

```powershell
Set-Location backend
python -m app.seed
python -m uvicorn app.main:app --reload
```

The seed command creates synthetic demo scenarios and skips already-seeded application references. It is intended to be safe to rerun and does not overwrite existing user records.

The API will normally be available at:

- API documentation: http://localhost:8000/docs
- Health endpoint: http://localhost:8000/health

### Terminal 2: Start the frontend

From the repository root:

```powershell
Set-Location frontend
npm run dev
```

<<<<<<< HEAD
Open the local URL displayed by Vite, normally:
=======
Open `http://localhost:5173` and sign in with the local demo admin credentials. Reviewers can use the demo reviewer login. Admins can create additional Admin, Reviewer or read-only Viewer accounts from **User management** in the sidebar. Managed accounts persist in SQLite; passwords are salted PBKDF2 hashes and are not retrievable. Environment-configured bootstrap accounts remain available and are not editable through the UI. Viewers can inspect permitted data but cannot make changes; only admins can create applications, upload documents, initiate validation or run simulated issuer checks. API tokens are held only in browser session storage.
>>>>>>> 86e45bb (Complete Pramaan AI compliance workflow and UI improvements)

http://localhost:5173

Sign in using the local admin or reviewer credentials configured in your environment.

- **Admin:** Can create applications and upload documents.
- **Reviewer:** Can inspect cases and perform permitted review actions.

API tokens are held in browser session storage.

### Database and File Storage

By default, the application stores:

- SQLite database: `backend/pramaan.db`
- Private uploaded documents: `backend/storage/`

Database tables are initialized automatically when the API starts. SQLite and local storage are intended for development and demonstration, not production deployment.

## Optional: Tesseract OCR Installation

Tesseract is required for OCR of scanned PDF pages and image documents. Digital PDFs containing embedded text can still be processed without it.

On Windows, one installation option is:

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

Verify the installation:

```powershell
tesseract --version
```

Restart the backend after installation. If Tesseract is not available on `PATH`, set `PRAMAAN_TESSERACT_CMD` in `backend\.env` to the actual path of `tesseract.exe`.

Without the native OCR engine, affected scanned documents return `OCR_UNAVAILABLE` and require manual review. The application does not fabricate extracted text.

## Demo Workflow

The seeded demo includes nine labelled scenarios covering:

1. Valid document.
2. Missing document.
3. Missing required field.
4. Expired document.
5. Institution mismatch.
6. Duplicate upload.
7. Future metadata indicator.
8. Scanned document requiring manual review.
9. Unknown issuer reference.

To demonstrate the workflow:

1. Start the backend and frontend.
2. Sign in as an administrator.
3. Open **Applications** and select a seeded scenario, or create a new application.
4. Inspect the document, extracted text, and available field values.
5. Run validation and review the findings, rule IDs, severity, supporting evidence, and recommended actions.
6. Use synthetic issuer verification on applicable scenarios.
7. Record a reviewer action and inspect the audit timeline.
8. Upload a sample PDF or image to demonstrate document processing.

Synthetic issuer checks use `backend/app/rules/synthetic_issuers.json`. They are local test lookups, not live issuer or AICTE integrations.

The illustrative required document type is `institution_certificate`. Configurable validation rules are defined in `backend/app/rules/validation_rules.json`.

No action automatically approves or rejects an institution.

## Testing

### Backend tests

From the repository root:

```powershell
Set-Location backend
python -m pytest -v
```

### Frontend lint

```powershell
Set-Location frontend
npm run lint
```

### Frontend production build

```powershell
npm run build
```

Run these checks after code changes and before the final demonstration. Do not describe the test suite as passing unless the command completes successfully.

<<<<<<< HEAD
## Environment Configuration
=======
1. Start the API, then open the frontend and sign in as admin.
2. Open **Applications**. The seeded demo includes nine labelled cases: valid, missing document, missing required field, expired, institution mismatch, duplicate upload, future metadata indicator, scanned/manual review, and unknown issuer reference.
3. Open an application. Review the uploaded document, text and extracted values; unavailable values remain unavailable rather than being guessed.
4. Run validation to see rule IDs, severity, status, source document, page/field evidence, recommended action and manual-review flag. The seeded data may be validated again; each run is separately recorded.
5. Use **SIMULATED — SYNTHETIC TEST DATA** verification on the valid, mismatch or unknown-reference records. These are lookups against `backend/app/rules/synthetic_issuers.json`, not issuer or AICTE integrations.
6. Record a reviewer action and inspect the audit timeline. No action automatically approves or rejects an institution.
7. Use **User management** to add a Viewer account and verify that it can read application details but cannot record review actions or make other changes.
>>>>>>> 86e45bb (Complete Pramaan AI compliance workflow and UI improvements)

| Setting | Default / Purpose |
|---|---|
| `PRAMAAN_DATABASE_URL` | SQLite database URL |
| `PRAMAAN_STORAGE_DIR` | Private document storage directory |
| `PRAMAAN_MAX_UPLOAD_BYTES` | `15728640` bytes (15 MiB) |
| `PRAMAAN_FRONTEND_ORIGINS` | Local Vite origin, normally `http://localhost:5173` |
| `PRAMAAN_TOKEN_SECRET` | HMAC signing key; replace the demo value |
| `PRAMAAN_TOKEN_TTL_SECONDS` | `28800` seconds (8 hours) |
| `PRAMAAN_ADMIN_USERNAME` | Local admin username |
| `PRAMAAN_ADMIN_PASSWORD_HASH` | Admin password hash |
| `PRAMAAN_REVIEWER_USERNAME` | Local reviewer username |
| `PRAMAAN_REVIEWER_PASSWORD_HASH` | Reviewer password hash |
| `PRAMAAN_TESSERACT_CMD` | Optional path to `tesseract.exe` |
| `VITE_API_URL` | Frontend API base URL, normally `http://localhost:8000` |

See [`docs/architecture.md`](docs/architecture.md) and [`docs/API.md`](docs/API.md) for additional technical details.

<<<<<<< HEAD
## Security and Limitations
=======
| Setting | Default | Purpose |
|---|---|---|
| `PRAMAAN_DATABASE_URL` | SQLite in `backend/pramaan.db` | SQLAlchemy database URL |
| `PRAMAAN_STORAGE_DIR` | `backend/storage` | Private backend-managed document directory |
| `PRAMAAN_MAX_UPLOAD_BYTES` | 15728640 | Upload limit (15 MiB) |
| `PRAMAAN_FRONTEND_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowlist; local `localhost` and `127.0.0.1` development ports are also accepted |
| `PRAMAAN_TOKEN_SECRET` | Local demo key | HMAC signing key; replace before use |
| `PRAMAAN_TOKEN_TTL_SECONDS` | 28800 | Token lifetime |
| `PRAMAAN_ADMIN_USERNAME` / `PRAMAAN_ADMIN_PASSWORD_HASH` | Local demo admin | Admin credential and PBKDF2-SHA256 hash |
| `PRAMAAN_REVIEWER_USERNAME` / `PRAMAAN_REVIEWER_PASSWORD_HASH` | Local demo reviewer | Reviewer credential and PBKDF2-SHA256 hash |
| `PRAMAAN_TESSERACT_CMD` | `PATH` or standard Windows install path | Optional explicit path to `tesseract.exe` |
| `VITE_API_URL` | `http://localhost:8000` | Optional frontend API base URL |
>>>>>>> 86e45bb (Complete Pramaan AI compliance workflow and UI improvements)

Pramaan AI is a local MVP and is not production-certified.

- Default demo credentials and signing keys are public development values. Replace them before any non-demo use.
- Upload validation checks file extensions, MIME types, signatures or formats, and configured size/page/pixel limits. The prototype does not include antivirus scanning, content disarm and reconstruction, or malware sandboxing.
- Local uploaded files are stored in backend-managed storage. Encryption at rest is not included.
- Tokens expire, but token revocation, refresh workflows, account recovery, and a production identity provider are not implemented.
- Admin and reviewer accounts are environment-configured rather than managed through a multi-user account database.
- Restrict CORS to trusted origins when deploying.
- SQLite automatic table creation is a startup convenience, not a database migration system. Use Alembic or an equivalent migration tool for managed schema changes.
- Production deployment requires a security review, deployment-managed secrets, TLS, rate limiting, suitable storage controls, monitoring, and backup procedures.
- OCR and heuristic extraction can be inaccurate. Metadata indicators and configurable validation rules can produce false positives or false negatives.
- Suspicious metadata is not proof of forgery. Extracting text does not authenticate a document. Synthetic verification does not confirm an issuer's records.
- External integrations must use authorized sources and are subject to availability and permissions.
- All findings are advisory. Final regulatory decisions remain with the competent AICTE authorities.

<<<<<<< HEAD
## Future Enhancements

Potential future improvements include:

- Authorized issuer API integrations where available.
- Improved OCR and document-specific field extraction.
- Configurable regulatory rules managed through an administrative interface.
- Enhanced evidence visualization and reviewer workflows.
- Production database migrations and managed storage.
- Additional security controls, monitoring, and deployment hardening.

These are planned enhancements, not claims about currently implemented functionality.

---

**Pramaan AI — Supporting transparent, evidence-based regulatory document review.**
=======
- This is a local demonstration, not production-certified. The documented default credentials and signing key are public and must be replaced.
- Uploads stay under backend storage and are not served as static files. The MVP checks extension, MIME, signatures/image format, PDF/image size and page/pixel limits; it does not include antivirus scanning, content-disarm/reconstruction, malware sandboxing or encryption at rest.
- Bearer tokens are signed and expire. Managed-user deactivation immediately revokes that user's sessions. Bootstrap admin/reviewer accounts remain environment-configured; password recovery and a production identity provider are not included.
- Managed accounts are stored in SQLite, and disabling one immediately invalidates its active sessions. Environment-configured bootstrap accounts remain separate; use a production identity provider and account-recovery workflow before deployment.
- CORS defaults to the local Vite origin. Restrict it to trusted origins when deploying.
- SQLite `create_all` is a startup convenience, not a migration system. Use migrations, deployment secrets, managed storage, TLS, rate limits and a security review before deployment.
- Heuristic extraction, metadata indicators and all illustrative rules can be wrong. Suspicious metadata is not proof of forgery, extraction is not authenticity verification, synthetic checks are not issuer confirmations, and this prototype does not make statutory decisions.
>>>>>>> 86e45bb (Complete Pramaan AI compliance workflow and UI improvements)
