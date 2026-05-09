# Security Review

## Authentication

- JWT authentication is required for billing, async classification, batch processing and admin routes.
- Admin routes require `role == admin`.
- Production deployments must replace `.env.example` `JWT_SECRET_KEY`.

## Billing

- Inference uses reserve/capture/refund with idempotency keys.
- Worker failure paths refund reserved credits.
- Cache-hit billing captures the configured cache-hit cost and refunds the remaining hold.

## Prompt Data

- Raw prompt text is stored in `classification_requests.input_text` for MVP traceability.
- Dashboards must not display raw text.
- Production hardening should add retention policy, encryption-at-rest notes and optional redaction.

## Admin Surface

- Admin endpoints expose users, model catalog and promo-code creation.
- Future production work should add audit logs and stronger operator authentication.

## Secrets

- No secrets should be committed.
- Use environment variables or a secret manager for JWT, database and Redis credentials.
- CI should not use production credentials.

## Model Supply Chain

- Hugging Face adapters are opt-in and lazy-loaded.
- Pin model revisions before production use.
- Capture model license, checksum and eval report before enabling a model in the default registry.

## Remaining Risks

- Rate limiting is not implemented yet.
- Access-token revocation is not implemented yet.
- Admin audit log is not implemented yet.
- Raw text retention policy is documented but not enforced.
