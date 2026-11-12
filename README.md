# Mohar (印) - Evidence-First Brand Governance

Mohar checks an organisation's posts and images **before they are published** against approved brand rules and approved facts. Every flag shows the exact rule or fact it comes from, every fix is a suggestion a human accepts or rejects, and nothing is approved automatically.

> **Core promise:** No source, no flag. No silent changes. No automatic approvals.

Built for **CodeNexus India 2026** (problem statement by Inkloom AI) by **Team nsmohit2008**. Demo brand: **AstraPay** (a fictional Indian UPI app).

| | Link |
|---|---|
| Live product | https://mohar-governance-snowy.vercel.app |
| API (Render) | https://mohar-api.onrender.com |
| Repository | https://github.com/xgjunaxd/mohar-governance |

---

## Try it in 3 minutes (for judges)

The first load can take up to a minute because the free server wakes up. After that it is fast.

1. Open the live link. On the sign-in page tap **Sign in as Creator**. (These are real accounts with real roles; no sign-up needed.)
2. Tap **Submit**, then **Try sample content**, then **Run Mohar Analysis**. You get a status (Blocked / Needs review / Ready) and findings, each with the rule or fact ID and the exact text it refers to.
3. Tap **Option 1** on a fix, then **Save Edits & Re-Analyze**. This creates version 2.
4. Optional: in **Submit** choose **Image / poster**, upload any picture and leave the alt text empty. You get accessibility and brand-colour findings.
5. Tap **Sign out**, then **Sign in as Manager**. Open **Approvals**, open the post and approve it. The approval is sealed with a SHA-256 hash and the audit trail shows the manager's email. A Creator never sees an Approve button, and the server refuses it even if you try the API directly.
6. Sign out, then **Sign in as Reviewer**. Open **Knowledge**, edit a fact, save, and open its history to see the old version. Set an expiry date within 30 days and look at the **Dashboard**: the fact appears under *Expiring & Expired Facts* with the approved posts that use it.

> The one-click demo accounts are public on purpose so judges can test without a sign-up. For a real team set `ALLOW_DEMO_LOGIN=false`.

## What it does

**Review text**
- Rules engine (deterministic): brand spelling, banned or casual words, tone, guaranteed-return claims, missing market-risk disclaimer, offer validity and T&C, expired offers.
- Fact checks against the approved fact ledger: wrong fees, limits, interest rates, cashback amounts and support hours are caught **without AI**.
- Unproven claims such as "best", "No.1", "fastest" are flagged.
- Gemini adds subtle tone and implied-claim checks. If Gemini is unavailable or out of quota, the rule-based checks still run.
- Evidence validator: a finding is only shown with a verified rule or fact ID and an exact excerpt from the post. Anything it cannot verify is marked *needs human verification*.
- Personal data (emails, phone numbers, account numbers) is masked before anything is sent to the AI.

**Review images (Round 3)**
- Missing or meaningless alt text, text contrast estimated against WCAG 4.5:1, and dominant colours compared with the approved brand palette. Findings use the same evidence-backed format as text.

**Workflow**
- Real sign-in with three roles. Roles are stored on the server and enforced by the API: Creators submit and edit their own posts, Managers approve / reject / request changes, Reviewers manage the knowledge base.
- Two suggested fixes per finding; accept, edit or reject with a reason; re-analysis creates a new version. Versions can be compared.
- Blocked posts can never be approved. Approval seals the approved text with SHA-256; copy certified text and download an audit certificate.
- Every action is written to an audit log tied to the real user.

**Reviewer workspace (Round 3)**
- In-app editor for facts and rules, version history for facts, valid-from and expiry dates, conflict detection between facts about the same topic, and alerts when an approved post repeats a fact that is expired or expiring within 30 days.

**Dashboard**: findings by status and category, most violated rules, pending reviews, expiring facts.

## Architecture

```
Browser (React + Vite + Tailwind, Vercel)
   |  HTTPS, Bearer token
   v
FastAPI (Render) ---- rate limiting, security headers, CORS
   |-- auth_service      sign-in through Supabase Auth, roles from user_roles
   |-- pipeline          1) rules_engine + fact_checks (deterministic)
   |                     2) gemini_client (one call, JSON output)
   |                     3) validator (checks every rule/fact ID and excerpt)
   |                     4) dedupe + status (blocked / needs_review / ready_for_approval)
   |-- visual            image checks with Pillow (alt text, contrast, brand colours)
   |-- facts_lifecycle   expiry state, conflicts, posts that rely on expiring facts
   v
Supabase PostgreSQL (rules, facts, fact_versions, submissions, versions, findings,
                     comments, audit_log, user_roles, workspaces)
```

The browser never talks to Supabase directly and no key is stored in the frontend. The service-role key lives only in the server's environment.

## Run it locally

You need Python 3.11+, Node 18+, a free Supabase project and (optional) a Gemini API key.

1. **Clone**
   ```
   git clone https://github.com/xgjunaxd/mohar-governance.git
   cd mohar-governance
   ```
2. **Database.** In the Supabase SQL Editor run `schema.sql`, then `schema_round3.sql`.
3. **Environment.** Copy `.env.example` to `.env` in the repo root and fill it in (see the table below).
4. **Backend** (run from the repo root, not from inside `app/`)
   ```
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python scripts/create_demo_users.py   # once: creates the Creator, Manager and Reviewer accounts
   uvicorn app.main:app --reload         # http://localhost:8000
   ```
5. **Frontend**
   ```
   cd mohar-frontend
   npm install
   echo "VITE_API_URL=http://localhost:8000" > .env.local
   npm run dev                            # http://localhost:5173
   ```
6. **Tests** (from the repo root)
   ```
   pip install pytest
   python -m pytest -q qa app/test_pipeline_samples.py
   ```

### Environment variables

| Variable | Purpose |
|---|---|
| `SUPABASE_URL`, `SUPABASE_KEY` | Database. `SUPABASE_KEY` is the service-role key (server only). |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | AI checks (default model `gemini-2.5-flash`). Optional: without it only rule-based checks run. |
| `REQUIRE_AUTH` | `true` = every request needs a real sign-in. Use `true` in production. |
| `ALLOW_DEMO_LOGIN`, `DEMO_PASSWORD` | One-click demo accounts and their password. |
| `ADMIN_API_KEY` | Optional key for scripts that edit rules and facts through the API. |
| `FRONTEND_URL`, `ALLOWED_ORIGINS` | CORS: which websites may call the API. |
| `ENABLE_DOCS` | `false` hides `/docs`. |
| `RATE_LIMIT_*` | Optional rate-limit settings (defaults in `.env.example`). |
| `VITE_API_URL` | Frontend: the API address. |

## Testing

- **76 automated tests** (`qa/`, `app/`): sign-in and role enforcement, per-user visibility, fact versions and conflicts, expiry alerts, the image checker, fact-number checks, rate limiting, CORS, headers, input limits and error handling. They use an in-memory fake database, so they need no keys.
- **Accuracy benchmark**: `qa/run_eval.py` runs 30 planted-issue samples against the live API (`MOHAR_API_URL`); results are saved in `qa/test_results_live.csv`.
- **Manual end-to-end passes** of the three journeys (Creator, Manager, Reviewer), bad input, empty states, refreshing a page, repeating an action, expired sessions.
- **Security**: `SECURITY.md` records the audit, the fixes and what remains.

## Known limitations (honest status)

- **Logo usage is not checked.** The image checker covers alt text, contrast and brand colours only.
- **Contrast is an estimate** taken from the two dominant colours of the image. It does not read the text itself.
- **Row-level security:** the database tables are locked so only the backend can read them; there are no per-user database policies, because all access goes through the API where roles are enforced.
- The one-click demo accounts are open to anyone (by design, for judging).
- Free hosting: the first request after a quiet period can take up to a minute. Gemini free-tier quota can run out; Mohar then falls back to rule-based checks, which cannot judge subtle tone.
- Rules have no version history (facts do). When two issues sit in the same sentence, one flag is shown for that sentence.

## Roadmap

1. Logo check (reference logo, minimum size and clear space) and real text detection for contrast.
2. Rule version history and an approval flow for knowledge-base changes.
3. Invite-based team accounts and per-team workspaces; turn off the public demo buttons.
4. Accuracy analytics: which fixes reviewers reject, which rules conflict.
5. Notifications by email when a fact is about to expire.

## Disclosures

- **Third-party services:** Gemini API, Supabase, Render, Vercel, GitHub.
- **AI assistants used:** Gemini and Claude were used for code generation, debugging, documentation and project planning.

## Team (nsmohit2008)

* **Junaid:** AI-1 Backend API, AI-2 AI-pipeline
* **Prasanna:** AI-3 Frontend React, AI-4 UI polish and Vercel deployment
* **Mohit:** AI-5 Testing/data, AI-6 Documentation & Submission
