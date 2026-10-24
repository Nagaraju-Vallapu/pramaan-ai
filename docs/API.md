# API reference

Base URL: `http://localhost:8000`. Interactive OpenAPI UI: `/docs`; machine schema: `/openapi.json`.

All `/api/*` endpoints require `Authorization: Bearer <token>`. Obtain a token from `POST /auth/login`. The default local demo users are `admin` / `admin-change-me` and `reviewer` / `reviewer-change-me`. Admin can create applications and upload files; both roles can review and run checks.

## Authentication and health

| Method | Route | Notes |
|---|---|---|
| `GET` | `/` | Preserved service greeting |
| `GET` | `/health` | Preserved health check |
| `POST` | `/auth/login` | JSON `{ "username": "...", "password": "..." }`; returns bearer token and role |

## Applications and dashboard

| Method | Route | Notes |
|---|---|---|
| `GET` | `/api/dashboard/summary` | Application/document/open-finding counts and status counts |
| `GET` | `/api/applications` | List applications and counts |
| `POST` | `/api/applications` | Admin; JSON `institution_name`, optional `reference_number` |
| `GET` | `/api/applications/{application_id}` | Application details |
| `POST` | `/api/applications/{application_id}/validate` | Optional JSON `evaluation_date` (`YYYY-MM-DD`); absent uses current UTC date |
| `GET` | `/api/applications/{application_id}/findings` | Findings for the latest validation run |
| `GET` | `/api/applications/{application_id}/audit?limit=100` | Latest audit entries, limit 1–500 |

Validation yields `PASS`, `FLAGGED` or `NEEDS_MANUAL_REVIEW`; these are check outcomes, not approval decisions. Each finding includes rule ID/name, severity, status, reason, document/page/field evidence, action guidance and a manual-review indicator.

## Documents and synthetic issuer checks

| Method | Route | Notes |
|---|---|---|
| `POST` | `/api/applications/{application_id}/documents` | Admin; multipart fields `file` and `document_type`; PDF/PNG/JPG/JPEG only, max 15 MiB by default |
| `GET` | `/api/applications/{application_id}/documents` | Documents and extracted fields/text |
| `GET` | `/api/documents/{document_id}/file` | Authenticated attachment download of the original stored file |
| `POST` | `/api/documents/{document_id}/verify` | **SIMULATED — SYNTHETIC TEST DATA** lookup only |
| `GET` | `/api/applications/{application_id}/verifications` | Historical synthetic verification attempts |

Document processing statuses include `PROCESSED`, `NEEDS_MANUAL_REVIEW` and `OCR_UNAVAILABLE`. OCR absence is visible in returned metadata (`ocr_message`) and is never a successful check. Unsupported, empty, malformed, encrypted, oversize and MIME/signature-mismatched uploads return a 4xx error with a safe message.

Synthetic verification returns one of `MATCH`, `MISMATCH`, `NOT_FOUND` or `NEEDS_MANUAL_REVIEW`. It reads only `backend/app/rules/synthetic_issuers.json`; no AICTE or issuer portal is contacted.

## Reviewer actions

`POST /api/findings/{finding_id}/actions` accepts:

```json
{
  "action": "acknowledge",
  "note": "Reviewed against the source scan."
}
```

Allowed actions: `acknowledge`, `confirm`, `resolve`, `request_correction`, `manual_verification`. The actor, note and timestamp are persisted, and an audit event is written. Reviewer decisions do not approve/reject an institution.

## Error codes

- `401`: missing/invalid/expired token or invalid login
- `403`: role is not permitted
- `404`: application/document/finding does not exist
- `413`: upload exceeds configured file/page/pixel limit
- `422`: malformed request
- `400`: unsupported extension, content type mismatch, corrupt or otherwise invalid source
- `500`: storage/database failure with a generic message; server-side details are not returned

API fields and routes may evolve during this MVP. No endpoint represents statutory compliance or real-world authenticity verification.