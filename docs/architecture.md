# Architecture

Pramaan AI is a local multi-role MVP workflow with a React browser client and a FastAPI service. Business records persist in SQLite by default; uploaded source documents are stored in a backend-only directory using UUID-based names. The browser receives document metadata and extracted text through authenticated API responses, never a filesystem path or public static URL.

## Components

- `backend/app/api/routes/`: auth, application/dashboard/validation/audit, document upload/list/synthetic verification, and reviewer actions.
- `backend/app/core/`: environment configuration, SQLAlchemy engine/session, schema initialization and PBKDF2/HMAC authentication.
- `backend/app/models/`: application, document, extracted field, validation run/finding, verification, reviewer action and audit event tables.
- `backend/app/schemas/`: request/response validation models.
- `backend/app/services/`: document validation and extraction, optional Tesseract OCR, illustrative validation, synthetic-data lookup and audit persistence.
- `backend/app/rules/`: JSON illustrative rules and a small synthetic issuer lookup dataset.
- `frontend/src/`: React application, typed Axios API client, workflow screens and responsive styling.

Managed users are stored in a dedicated database table using salted PBKDF2 password hashes. The environment-configured admin and reviewer remain bootstrap identities. Admins can create and deactivate Admin, Reviewer and Viewer accounts from the User management screen. Each authenticated request rechecks managed-user activity and role, so deactivation invalidates existing tokens. Viewer access is read-only; reviewers may record finding actions; creating applications, uploading, validation and synthetic issuer checks are admin-only.

## Data flow

1. Admin creates an application; a reviewer or admin can view it. The dashboard summarizes persisted status counts, recent audit activity and findings from each application's latest validation run.
2. Admin uploads a permitted PDF/image. The API streams the request under a configured size limit, validates filename/extension/MIME/signature, hashes the original bytes, and saves to `storage/<application UUID>/<random UUID>.<ext>`.
3. PyMuPDF extracts embedded PDF text. Only pages with fewer than 30 extracted characters are rendered for OCR. Images are decoded/verified with Pillow. Tesseract absence is returned explicitly as `OCR_UNAVAILABLE`; manual review is not disguised as successful OCR.
4. Label-based field extraction returns institution name, document number, issue date and expiry date. Missing values are null and marked `NEEDS_MANUAL_REVIEW`. Page numbers are one-based. Pattern confidence is an estimate (0.9 for a labelled digital-text match); OCR-derived confidence reflects the OCR engine's mean word confidence.
5. Only admins can initiate validation. The service loads `backend/app/rules/validation_rules.json` on each run. Every run owns its findings; reruns are retained as distinct historical runs instead of duplicating findings within a run. Expiry uses the explicit evaluation date (UTC current date by default); a document is considered expired only if its expiry date is before that date, meaning it remains valid through its printed expiry date.
6. Only admins can initiate synthetic issuer checks. A request compares extracted institution/number values with local synthetic records only. Results include `MATCH`, `MISMATCH`, `NOT_FOUND` or `NEEDS_MANUAL_REVIEW` and the response label `SIMULATED — SYNTHETIC TEST DATA`.
7. Uploads, processing, validation, verification and review actions create audit events without source text or credentials.

## Decisions and limits

- SQLAlchemy models use portable string UUID keys and relationships. SQLite tables are created on startup for a simple local install; there are no migrations yet. Use Alembic before schema evolution on a shared database.
- Rules are illustrative and configurable, not official AICTE policy. `institution_certificate` is a demo document type.
- Basic metadata checks are review indicators only. Exact duplicate detection compares SHA-256 within one application. No heuristic proves fraud.
- The local synthetic issuer dataset is not a real integration. Real issuers require explicit authorization and separately implemented adapters.
- Demo password hashes and the signing secret are intentionally configured for first-run convenience; change them before any deployment. There is no password reset/recovery, token refresh, encrypted storage, malware scanning or production-grade identity management.