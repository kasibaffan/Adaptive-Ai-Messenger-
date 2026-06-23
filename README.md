# Adaptive AI Messenger

A multi-tenant assistant platform: any company can sign up, upload its own
documentation, and immediately get a chat widget plus automatic reminder
delivery — without touching a line of code. One codebase, one running
service, isolated behavior per company.

## How it adapts per company

- **Tenancy**: every company gets its own row in `companies` and its own
  vector collection (`company_<id>`) in the embedded ChromaDB store. No
  cross-tenant data ever mixes.
- **Personality**: `tone` and `persona_name` are set per company and used to
  label replies — see [backend/services/llm.py](backend/services/llm.py).
- **Knowledge**: companies upload PDFs/DOCX/TXT through the dashboard; text
  is chunked and embedded into that company's collection
  ([backend/services/rag.py](backend/services/rag.py)). The widget only ever
  retrieves chunks from its own company's collection.
- **Retrieval + local extractive QA, no LLM API cost**: the chatbot never
  generates free-form text via an external model. It embeds the customer's
  question locally (ChromaDB's built-in sentence-transformers model), finds
  the best-matching passage from that company's uploaded documents, then runs
  a small local question-answering model (DistilBERT, downloaded once from
  Hugging Face and cached — no API key, no per-message cost) to pull the
  precise answer span out of that passage. If nothing matches well enough, it
  returns a fixed "I don't have that information yet" message and logs the
  question as a knowledge gap. The bot can only ever say what's grounded in
  the company's own documents — it can't hallucinate or answer from outside
  knowledge.
- **Self-improving**: when the assistant can't answer, the question is
  logged as a "knowledge gap." A human answers it once from the dashboard,
  and the answer is ingested straight back into the knowledge base — so the
  assistant gets smarter from real conversations instead of a manual
  re-training step.
- **Reminders**: each company can schedule follow-ups (fixed time, or "N
  hours after no reply") delivered by email, SMS, or WhatsApp automatically
  via APScheduler ([backend/services/scheduler.py](backend/services/scheduler.py)).
  Email goes through SMTP; SMS/WhatsApp go through Twilio
  ([backend/services/notify.py](backend/services/notify.py)). Whichever
  channel isn't configured just logs instead of sending, so the prototype
  works end-to-end without any messaging credentials.
- **Slack notifications**: a company pastes a Slack Incoming Webhook URL
  into Settings (no OAuth, no app install) and gets notified when a customer
  message is flagged negative-sentiment or when the assistant logs a new
  knowledge gap ([backend/services/slack.py](backend/services/slack.py)).
  No-ops silently if no webhook URL is set.
- **Branding**: `brand_color` and `logo_url` are set per company in the
  dashboard Settings tab. The widget fetches them from the public
  `GET /chat/{company_id}/profile` endpoint on load, so the embed snippet
  itself never has to be regenerated when a company changes its colors.
- **Plans & limits**: Free/Pro/Enterprise tiers (`backend/services/plans.py`)
  gate document count and messages/month per company. Billing runs on Stripe
  Checkout ([backend/services/billing.py](backend/services/billing.py)) but
  degrades gracefully without API keys configured — `/billing/checkout`
  returns a friendly 503 instead of erroring, so the rest of the product
  works fully before you ever set up Stripe.
- **Onboarding**: a 3-step wizard (name your assistant → upload a document →
  copy the embed snippet) shows automatically right after registration.

## Stack

- **Backend**: FastAPI + SQLAlchemy (SQLite by default) + ChromaDB (local,
  no external vector DB needed). No LLM API key required anywhere — chat
  replies are retrieved, not generated, and sentiment/escalation
  ([backend/services/llm.py](backend/services/llm.py)) is a free keyword
  check instead of a model call.
- **Frontend**: plain HTML/CSS/JS — no build step. A company dashboard
  (`frontend/dashboard.html`) and an embeddable widget script
  (`frontend/widget.js`) that any customer site can drop in with a single
  `<script>` tag.

## Running locally

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in SECRET_KEY at minimum; SMTP/ALLOWED_ORIGINS/DATABASE_URL are optional
uvicorn main:app --reload
```

Then open `http://localhost:8000/` for the company dashboard. Register a
company, upload a document, and copy the generated embed snippet from the
"Embed widget" tab into any HTML page (see `frontend/widget-demo.html` for
an example) to test the live chat widget end-to-end.

## Running tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Tests run against a fresh, isolated SQLite DB + Chroma store in a temp
directory — they never touch `messenger.db`/`chroma_store` from your dev
server.

## Key endpoints

| Endpoint | Purpose |
|---|---|
| `POST /auth/register`, `/auth/login` | Company account creation/auth |
| `PATCH /auth/settings` | Update tone/persona/brand color/logo/Slack webhook |
| `POST /documents/upload` | Upload + index a knowledge file (enforces plan limits) |
| `POST /chat/{company_id}` | Public chat endpoint used by the widget |
| `GET /chat/{company_id}/profile` | Public branding info used by the widget |
| `GET /chat/logs/all` | Dashboard conversation history |
| `GET /chat/stats` | Dashboard usage stats (messages, sentiment, plan usage) |
| `POST /reminders/` | Schedule an automatic follow-up message (email/SMS/WhatsApp) |
| `GET /gaps/`, `PATCH /gaps/{id}/resolve` | Review and close knowledge gaps |
| `GET /billing/plans`, `/billing/status` | Plan tiers and current company's plan/usage |
| `POST /billing/checkout` | Start a Stripe Checkout session (503 if Stripe isn't configured) |
| `POST /billing/webhook` | Stripe webhook — updates plan on subscription changes |

## Hardening already in place

- **Scoped CORS**: every endpoint except the public chat-send route
  (`POST /chat/{company_id}`) is restricted to the origins listed in
  `ALLOWED_ORIGINS`. The chat-send route stays open to any origin on purpose
  — it's the embeddable widget, meant to be called from arbitrary customer
  websites — see the `scoped_cors` middleware in `backend/main.py`.
- **Rate limiting**: `/auth/register` and `/auth/login` are capped at
  5/minute per IP (brute-force/spam protection); the public chat endpoint is
  capped at 20/minute per IP. Built with `slowapi`
  ([backend/services/rate_limit.py](backend/services/rate_limit.py)).
- **Postgres-ready database**: `DATABASE_URL` already drives the connection
  ([backend/database.py](backend/database.py)); SQLite is just the zero-setup
  dev default. Point it at a managed Postgres instance for production — the
  `psycopg` driver is already in `requirements.txt`, and the SQLite-only
  connect arg is now applied conditionally.
- **Durable file storage (optional)**: uploaded documents are always written
  to local disk first (parsing libraries need a real file path), but if
  `S3_BUCKET`/`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY` are set
  ([backend/services/storage.py](backend/services/storage.py)), every upload
  is also backed up to S3-compatible storage (AWS S3, Cloudflare R2,
  Backblaze B2) — set `S3_ENDPOINT_URL` for non-AWS providers. Without those
  vars, behavior is unchanged from before this existed: local disk only.
- **Logging & error tracking**: every request is logged with method, path,
  status, and duration (`backend/main.py`); a global exception handler turns
  unhandled errors into a clean 500 instead of leaking a stack trace, while
  still logging the full traceback. Set `SENTRY_DSN` to additionally forward
  errors to Sentry (free tier, no card required) — without it, errors just
  go to stdout, which most hosts capture for you already.
- **Automated tests**: `backend/tests/` covers auth, document upload + plan
  limits, billing status/checkout, and chat retrieval (including the
  knowledge-gap logging path), run via `pytest` against an isolated SQLite
  DB + Chroma store created fresh per test run — nothing touches your real
  dev database.
- **Privacy Policy & Terms of Service**: served at `/privacy` and `/terms`
  (`frontend/privacy.html`, `frontend/terms.html`), linked from the
  registration form (with a required consent checkbox) and from the
  dashboard sidebar.

  > ⚠️ **These are generic templates, not legal advice.** Every `[bracketed]`
  > placeholder (legal entity name, contact email, governing-law
  > jurisdiction) needs to be filled in, and you should have an actual lawyer
  > review both pages before relying on them commercially — data-protection
  > requirements (GDPR, CCPA, etc.) depend on where your company and
  > customers are located. Search both files for `[` to find every
  > placeholder.

## Deploying publicly (Google Cloud Run)

This stack (PyTorch + the local DistilBERT QA model + Chroma's embedding
model) needs more than the 512MB RAM ceiling that both Render's free *and*
$7/mo tiers cap out at. Cloud Run is the free option that actually fits: you
choose the container's memory (no fixed ceiling), it scales to zero when
idle (so cost stays $0 at low traffic — free quota is roughly 100
container-hours/month), and there's no server to patch or maintain.

**The trade-off to know going in**: Cloud Run containers are ephemeral, like
any serverless platform — local disk (SQLite, the Chroma vector store,
uploaded files) does **not** survive a cold start. The fix for the database
is a free external Postgres; the Chroma knowledge base and uploaded
documents will reset on cold starts unless you later add S3-compatible
backup (already supported, see `S3_BUCKET` below) plus a re-ingestion step.
For a launch/demo phase this is a reasonable trade — just know companies
may occasionally need to re-upload a document after a long idle period.

### 1. Free Postgres (Neon)

1. Sign up free at [neon.tech](https://neon.tech) (no card required).
2. Create a project, then copy the connection string from the dashboard —
   it looks like `postgresql://user:password@host/dbname`.
3. You can paste it exactly as given; `backend/database.py` automatically
   rewrites the `postgresql://` scheme to the `postgresql+psycopg://` form
   the driver needs.

### 2. Install the Google Cloud CLI

Install `gcloud` from [cloud.google.com/sdk](https://cloud.google.com/sdk),
then:

```bash
gcloud init                      # creates/selects a project, sets default region
gcloud auth login
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### 3. Generate a secret key

```bash
openssl rand -hex 32             # use the output as SECRET_KEY below
```

### 4. Deploy

From the repository root (where the `Dockerfile` lives) — `--source .`
uploads your code to Cloud Build, which builds the `Dockerfile` and deploys
it, no local Docker install required:

```bash
gcloud run deploy adaptive-ai-messenger \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --port 8080 \
  --set-env-vars "SECRET_KEY=<output from step 3>,DATABASE_URL=<your Neon connection string>"
```

The first build pulls PyTorch + transformers, so expect it to take several
minutes — that's normal. When it finishes, `gcloud` prints a service URL
like `https://adaptive-ai-messenger-xyz.run.app`.

### 5. Point the app at its own URL

`ALLOWED_ORIGINS` only gates cross-origin requests — the dashboard and
widget call the API same-origin, so this step isn't strictly required for
the app to work, but it's the correct setting if you ever add a separate
frontend on another domain:

```bash
gcloud run services update adaptive-ai-messenger \
  --region us-central1 \
  --set-env-vars "ALLOWED_ORIGINS=https://adaptive-ai-messenger-xyz.run.app,APP_BASE_URL=https://adaptive-ai-messenger-xyz.run.app"
```

### 6. Optional env vars

Add any of these the same way (`--set-env-vars`, comma-separated, or
`--update-env-vars` to add without replacing existing ones) whenever you set
them up — everything degrades gracefully without them: `STRIPE_SECRET_KEY` /
`STRIPE_WEBHOOK_SECRET` / `STRIPE_PRO_PRICE_ID` (billing), `SMTP_HOST` /
`SMTP_USER` / `SMTP_PASSWORD` (email reminders), `TWILIO_ACCOUNT_SID` /
`TWILIO_AUTH_TOKEN` / `TWILIO_SMS_FROM_NUMBER` (SMS/WhatsApp reminders),
`SENTRY_DSN` (error tracking), `S3_BUCKET` / `S3_ACCESS_KEY_ID` /
`S3_SECRET_ACCESS_KEY` (durable document backup).

### Notes

- **Cold starts will be slow** the first time after idle — loading PyTorch
  and the QA model takes real time. `--min-instances=1` keeps one instance
  warm permanently (eliminates cold starts) but moves you off the free tier
  into a small constant cost — leave it at the default (0) to stay free.
- A custom domain can be attached later with
  `gcloud run domain-mappings create` — the `*.run.app` URL works fine to
  start.
- Redeploy after any code change by re-running the `gcloud run deploy`
  command from step 4 — it rebuilds and replaces the running revision.

## Notes on remaining scope

This is a prototype meant to demonstrate the adaptive, multi-tenant pattern
end-to-end — auth, document-grounded retrieval, billing, branding, usage
tracking, onboarding, multi-channel reminders/notifications, keyword-based
escalation, and a feedback loop that grows the knowledge base. Still not
fully production-hardened beyond the items above: no database migration
tool (schema changes to `Company`/etc. require a fresh DB in dev — Alembic
would be the next step for a real deployment), and the chat widget itself
is web-only — Slack/WhatsApp here are one-way notification/reminder
channels, not full two-way chat bots (that would need Slack app
OAuth/install and WhatsApp Business approval, which need real external
accounts to set up and weren't something I could configure on your behalf).

If a customer later wants natural-language, generative answers instead of
direct passage retrieval, swap `chat_with_company_context` in
`backend/services/llm.py` to call an LLM API (Anthropic, OpenAI, Gemini,
etc.) using `context_chunks` as the grounding context — the function
signature is already set up for that swap.
