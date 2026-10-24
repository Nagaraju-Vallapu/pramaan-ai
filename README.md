# Pramaan AI

Pramaan AI is a local MVP for Smart India Hackathon 2026 problem statement PS 26261: AI-powered application validation, document authentication and regulatory-compliance support.

It is a review-support prototype, **not an official AICTE service, authenticity guarantee, or institution approval/rejection system**. Compliance checks are configurable illustrative demo rules. Issuer checks use only clearly labelled synthetic local records.

## What is implemented

- Protected FastAPI APIs for applications, document upload/processing, validation, review actions, synthetic issuer checks and audit history.
- Local SQLite persistence with SQLAlchemy models; first startup creates missing tables. Use Alembic before managing production schema changes.
- PDF text extraction with PyMuPDF; image/scanned-page OCR with Tesseract when installed. OCR absence is returned as `OCR_UNAVAILABLE` and never represented as successful extraction.
- Responsive React + TypeScript dashboard backed by the API.
- Password-hashed local admin/reviewer credentials and signed, expiring bearer tokens.
- Synthetic demo scenarios for missing, expired, mismatched, duplicate, suspicious-metadata, manual-review, synthetic issuer match/mismatch/not-found cases.

## Repository layout

```text
backend/
  app/api/routes/       FastAPI route modules
  app/core/             configuration, SQLite/SQLAlchemy, authentication
  app/models/           SQLAlchemy records and relationships
  app/rules/             illustrative validation rules and synthetic issuer dataset
  app/services/          document/OCR, validation, verification, audit services
  tests/                 processor and API tests
frontend/src/            React dashboard and typed API client
docs/                    architecture and API reference
```

## Windows PowerShell setup

Requirements: Python 3.11+ (tested here with Python 3.13), Node.js 20.19+ (Node 24 is supported), and npm. Tesseract is optional for startup but required for OCR of scanned/image documents.

From the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

The example credentials are deliberately public development-only values: `admin` / `admin-change-me` and `reviewer` / `reviewer-change-me`. Change both hashes and the token secret before using anything beyond a local demo. Generate an individual password hash with the hidden-input utility:

```powershell
Set-Location backend
python -m app.password_hash
```

Copy the printed hash into `PRAMAAN_ADMIN_PASSWORD_HASH` or `PRAMAAN_REVIEWER_PASSWORD_HASH` in `backend\.env`, and change the matching username as needed. Create a random signing secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste it into `PRAMAAN_TOKEN_SECRET`. Configuration is read from `backend\.env` (environment variables override it). By default SQLite data is created in `backend\pramaan.db` and private uploads in `backend\storage\`; both are git-ignored.

### Optional Tesseract OCR

Install the Windows Tesseract distribution (for example):

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
tesseract --version
```

Restart PowerShell/backend after installation. If `tesseract.exe` is not on `PATH`, set `PRAMAAN_TESSERACT_CMD` in `backend\.env`, for example `C:\Program Files\Tesseract-OCR\tesseract.exe`. Without the native engine, digital-PDF text processing still works; scanned pages and images return `OCR_UNAVAILABLE` and require manual review. The backend does not manufacture extracted content.

### Start the API and frontend

In the first PowerShell window:

```powershell
Set-Location C:\Users\User\pramaan-ai\backend
python -m app.seed
python -m uvicorn app.main:app --reload
```

The seed command creates synthetic applications and documents only, skips already-seeded application references, and is safe to run again. It does not overwrite existing user records. Browse to `http://localhost:8000/docs` for interactive API docs and `http://localhost:8000/health` for health.

In a second PowerShell window:

```powershell
Set-Location C:\Users\User\pramaan-ai\frontend
npm ci
npm run dev
```

Open `http://localhost:5173` and sign in with the local demo admin credentials. Reviewers can sign in with the reviewer credentials; only admins can create applications or upload documents. API tokens are held only in browser session storage.

### Database initialization, tests and production build

Database initialization happens automatically at API startup. You may also initialize tables explicitly:

```powershell
Set-Location C:\Users\User\pramaan-ai\backend
python -c "from app.core.database import initialize_database; initialize_database()"
python -m pytest
```

Frontend checks:

```powershell
Set-Location C:\Users\User\pramaan-ai\frontend
npm run lint
npm run build
```

## Demo walkthrough

1. Start the API, then open the frontend and sign in as admin.
2. Open **Applications**. The seeded demo includes nine labelled cases: valid, missing document, missing required field, expired, institution mismatch, duplicate upload, future metadata indicator, scanned/manual review, and unknown issuer reference.
3. Open an application. Review the uploaded document, text and extracted values; unavailable values remain unavailable rather than being guessed.
4. Run validation to see rule IDs, severity, status, source document, page/field evidence, recommended action and manual-review flag. The seeded data may be validated again; each run is separately recorded.
5. Use **SIMULATED — SYNTHETIC TEST DATA** verification on the valid, mismatch or unknown-reference records. These are lookups against `backend/app/rules/synthetic_issuers.json`, not issuer or AICTE integrations.
6. Record a reviewer action and inspect the audit timeline. No action automatically approves or rejects an institution.

Create a new application and upload a PDF, PNG or JPEG to demonstrate the live workflow. The illustrative required document type is `institution_certificate`; the configured rules are in `backend/app/rules/validation_rules.json`.

## Environment configuration

| Setting | Default | Purpose |
|---|---|---|
| `PRAMAAN_DATABASE_URL` | SQLite in `backend/pramaan.db` | SQLAlchemy database URL |
| `PRAMAAN_STORAGE_DIR` | `backend/storage` | Private backend-managed document directory |
| `PRAMAAN_MAX_UPLOAD_BYTES` | 15728640 | Upload limit (15 MiB) |
| `PRAMAAN_FRONTEND_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowlist |
| `PRAMAAN_TOKEN_SECRET` | Local demo key | HMAC signing key; replace before use |
| `PRAMAAN_TOKEN_TTL_SECONDS` | 28800 | Token lifetime |
| `PRAMAAN_ADMIN_USERNAME` / `PRAMAAN_ADMIN_PASSWORD_HASH` | Local demo admin | Admin credential and PBKDF2-SHA256 hash |
| `PRAMAAN_REVIEWER_USERNAME` / `PRAMAAN_REVIEWER_PASSWORD_HASH` | Local demo reviewer | Reviewer credential and PBKDF2-SHA256 hash |
| `PRAMAAN_TESSERACT_CMD` | system `PATH` lookup | Optional explicit path to `tesseract.exe` |
| `VITE_API_URL` | `http://localhost:8000` | Optional frontend API base URL |

See [docs/architecture.md](docs/architecture.md) and [docs/API.md](docs/API.md) for system details and endpoints.

## Security and prototype limitations

- This is a local demonstration, not production-certified. The documented default credentials and signing key are public and must be replaced.
- Uploads stay under backend storage and are not served as static files. The MVP checks extension, MIME, signatures/image format, PDF/image size and page/pixel limits; it does not include antivirus scanning, content-disarm/reconstruction, malware sandboxing or encryption at rest.
- Bearer tokens are signed and expire, but there is no refresh/revocation workflow, multi-user database, account recovery or production identity provider. Admin/reviewer accounts are environment-configured.
- CORS defaults to the local Vite origin. Restrict it to trusted origins when deploying.
- SQLite `create_all` is a startup convenience, not a migration system. Use migrations, deployment secrets, managed storage, TLS, rate limits and a security review before deployment.
- Heuristic extraction, metadata indicators and all illustrative rules can be wrong. Suspicious metadata is not proof of forgery, extraction is not authenticity verification, synthetic checks are not issuer confirmations, and this prototype does not make statutory decisions.
