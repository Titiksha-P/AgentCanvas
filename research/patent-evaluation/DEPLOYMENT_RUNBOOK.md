# Deployment and database runbook

## Current Vercel deployments

The public read-only demo is deployed as two Vercel projects:

- Frontend: https://agentcanvas-patent-console.vercel.app
- FastAPI backend: https://agentcanvas-patent-api.vercel.app
- API health: https://agentcanvas-patent-api.vercel.app/api/health
- Patent database readiness: https://agentcanvas-patent-api.vercel.app/api/patent-db-health
- OpenAPI docs: https://agentcanvas-patent-api.vercel.app/docs

The frontend is built in read-only demo mode and calls the backend's read-only `GET /api/patent-evaluate` endpoint. No API key is shipped to the browser.

These deployments were created from source snapshots through the Vercel API because the Vercel account did not yet have a GitHub Login Connection. They are live deployments, but are not yet linked for automatic Git-based redeployment.

## Vercel backend environment

The API project currently has:

- `APP_ENV=production`
- `CORS_ORIGINS=*` (read-only public demo; write routes remain separately protected)

Before enabling persisted evaluation history or write endpoints, configure these as encrypted/server-side environment variables in the Vercel backend project:

- `DATABASE_URL`: copy the **Transaction Pooler** URI from Supabase Project Settings → Database → Connection string. Do not paste the database password into source control or the browser. Include SSL as directed by the Supabase connection-string panel.
- `AGENTCANVAS_API_TOKEN`: a high-entropy bearer token generated in a password manager. The backend requires `Authorization: Bearer <token>` for mutation endpoints.
- `OPENAI_API_KEY`: optional, only if the LLM judge or existing agent-evaluation endpoint is to be enabled. Store it only in the backend environment.

After adding or changing environment variables, redeploy the backend. Then check `/api/patent-db-health`; it should report `{"status":"ok","table":"public.patent_evaluations"}`.

The public demo does not need a database connection to run the deterministic fixture preview. History persistence is unavailable until `DATABASE_URL` is configured.

## Supabase database

Existing project: `poeqhxjutuirlyyejcik` (region `ap-northeast-1`).

The project was restored rather than replaced. It contained no existing public tables or migration records before this work. Migration `create_patent_evaluations` was applied and verified:

- `public.patent_evaluations` exists
- RLS is enabled
- no public `anon` or `authenticated` privileges are granted
- only `service_role` is granted table access
- smoke query returned zero rows, as expected for a new table

The Supabase security advisor also identified a pre-existing `public.rls_auto_enable()` SECURITY DEFINER event-trigger function executable by `anon` and `authenticated`. Its function definition and event-trigger binding were inspected; EXECUTE was revoked from PUBLIC, anon, and authenticated. Verification confirmed both roles can no longer execute it. The remaining RLS-without-policy notice on `patent_evaluations` is intentional: browser roles must not access evaluation history directly.

## Public patent corpus

The selected initial source is the USPTO Patent Claims Research Dataset, OCE-PT-00002, with a CC0 1.0 Public Domain Dedication. The source file is large (the claim full-text CSV is listed at approximately 4.41 GB). The repository now contains a streaming CSV importer that emits provenance-preserving JSONL. It does not generate defect labels or model outputs. See:

- `research/patent-dataset/PUBLIC_CORPUS_ASSESSMENT.md`
- `research/patent-dataset/uspto_patent_claims_manifest.json`
- `backend/import_uspto_claims.py`

The corpus has not yet been downloaded or imported. Inspect the actual CSV headers first, then pass explicit identifier and claim-text column names to the importer. Expert-labelled paired candidate outputs and inter-annotator agreement remain separate work.

## GitHub continuous deployment

To enable automatic Vercel redeployments:

1. In Vercel, open your profile menu → Settings → Authentication.
2. Under Login Connections, add/connect GitHub and authorize the GitHub account that owns `Titiksha-P/AgentCanvas`.
3. Return here so the Git-linked projects can be created and configured for the `frontend/` and `backend/` roots.

The current source snapshot deployments remain available while GitHub linking is completed.

## Operational limitations

- LLM judge has not been exercised with a live authorized `OPENAI_API_KEY`.
- PostgreSQL schema is live and migrated, but the Vercel backend has not yet received `DATABASE_URL`; application-to-Postgres connectivity is therefore not yet verified.
- The current demo is read-only; authenticated mutation requires the server-side API token.
- The current batch executor is in-process; a distributed queue is not included.
- The 20-case benchmark remains synthetic. Public USPTO claim text is an unlabelled reference corpus, not defect ground truth.
