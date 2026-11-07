# Mohar – Security Audit Report

Audit date: 7 Nov 2026 · Scope: GitHub repo (12 commits), FastAPI backend, React/Vite frontend, Supabase schema, deploy config (Render + Vercel).
**This report does not claim the project is "completely secure". It lists what was checked, what was fixed, what was not, and what could not be verified.**

## 1. What the system is
| Part | What it is |
|---|---|
| Frontend | React 18 + Vite + Tailwind, static site on Vercel. Holds no keys (only `VITE_API_URL`). |
| Backend | FastAPI on Render. Rules engine + Gemini review + evidence validator. |
| Database | Supabase Postgres, accessed ONLY by the backend (`SUPABASE_KEY`). |
| Auth | Optional Supabase sign-in checked by the backend. The frontend has no login screen yet; the demo uses a Creator/Manager/Reviewer switch in the top bar. |

## 2. Issues found (before fixes)
| # | Severity | Issue | Status |
|---|---|---|---|
| 1 | **Critical** | Anyone could create/edit rules and facts (`POST/PUT /api/rules`, `/api/facts`, CSV import) with no login. Breaks the "no silent changes" promise. | **Fixed** |
| 2 | **High** | No rate limiting; anyone could spam `POST /api/submissions` and burn the Gemini quota. | **Fixed** |
| 3 | **High** | Approval role is self-declared: a request that says `"role":"Manager"` can approve (when `REQUIRE_AUTH=false`). | **Not fixed** (needs a login screen) |
| 4 | **High** | No access control on submissions: anyone can list all submissions, read them, and accept/reject findings. | **Not fixed** (open by design for the demo) |
| 5 | Medium | CORS allowed every website (`*`). | **Fixed** |
| 6 | Medium | No maximum input length; one huge repetitive post took the rules engine ~24 s (CPU denial of service). | **Fixed** (5,000 chars → 0.07 s) |
| 7 | Medium | Database error text was returned to users. | **Fixed** |
| 8 | Medium | No security headers on API or website. | **Fixed** (see "Unverified" for CSP) |
| 9 | Medium | User text goes into the Gemini prompt (prompt injection). | **Partly fixed** |
| 10 | Medium | Review cache was unbounded and not cleared when rules/facts changed. | **Fixed** |
| 11 | Medium | Audit-log identity can be faked (`creator` is free text; finding decisions are always logged as "Creator"). | **Not fixed** |
| 12 | Medium | CSV import had no size/row/format limits. | **Fixed** |
| 13 | Low | `/docs` (Swagger) is public. | Switch added, default left ON |
| 14 | Low | `react-router` (2 moderate advisories) and `vite/esbuild` (dev-server only). Not exploitable here: no server rendering, no user-controlled redirects, dev server is not deployed. | Not fixed (needs major upgrades) |
| 15 | Low | Python deps are unpinned (Render installs the newest at each build). | Not fixed |
| 16 | Low | Unused files/packages: `google-generativeai` (fallback only), `src/mock/mockData.js`, root `check_*.py`, `check_fix.mjs`. | Not removed (no deletions without permission) |

## 3. Checked and found OK
* **API keys / env:** no secrets in the repo or in ANY of the 12 commits (scanned for Google, Supabase, GitHub, JWT, DB-URL patterns; only placeholder text in `.env.example`). `.env` is git-ignored. Frontend contains no keys.
* **XSS:** no `dangerouslySetInnerHTML`, `innerHTML`, `eval`, or `document.write`; React escapes all user text.
* **Passwords:** the app never handles or stores passwords. If sign-in is added, Supabase Auth handles hashing.
* **Sessions:** no cookies or localStorage tokens; bearer tokens are verified server-side.
* **Python dependencies:** `pip-audit` found 0 known vulnerabilities in the app's packages (only in the `pip` tool itself). `bandit`: 0 findings after fixes.
* **SQL injection:** all queries use the Supabase client (parameterised).

## 4. Fixes implemented
* `app/security.py` (new): security headers + rate limiter (10 AI reviews/min per visitor, 30 other writes/min, 240 reads/min, 300 AI reviews/hour for everyone). `/health` is never limited.
* `app/main.py`: admin guard on all rule/fact/CSV routes (real Supabase sign-in as manager/reviewer **or** `X-Admin-Key` matching `ADMIN_API_KEY`); CORS limited to the Vercel site + localhost (extend with `ALLOWED_ORIGINS`), credentials off; generic error messages (details go to server logs only); safer CSV import; cache cleared on rule/fact changes; `ENABLE_DOCS=false` switch.
* `app/models.py`: max lengths on every text field; strict ID format for rules/facts.
* `app/pipeline.py`: review cache capped at 500 entries.
* `app/gemini_client.py`: one extra prompt rule telling the model to treat the post as data, not instructions.
* `mohar-frontend/vercel.json`: security headers incl. Content-Security-Policy.
* `qa/test_security.py` (new): 14 automated tests.

## 5. Tests performed
* Before: exploit attempts proved items 1, 5, 6, 8 and no rate limiting.
* After: same attempts now blocked (rules/facts → 401, evil origin → no CORS header, oversized post → 422, headers present, 11th AI call/min → 429).
* 14 new tests pass; original `check_approval.py`, `check_ds001.py` and `app/test_pipeline_samples.py` still pass; frontend production build passes; worst-case processing time measured.

## 6. Remaining vulnerabilities (accept for demo, fix before real use)
1. Self-declared roles (#3), public submissions (#4), spoofable audit identity (#11). **Real fix:** add a Supabase sign-in screen, then set `REQUIRE_AUTH=true` on Render.
2. Rate limit uses the first `X-Forwarded-For` address, which a determined attacker can fake. The global AI cap (300/hour) is the backstop. Limits reset when Render restarts.
3. Prompt injection cannot be fully prevented; the rules engine still runs on every post as a safety net.
4. react-router / vite advisories (upgrade after submission and re-test).

## 7. Could NOT be verified
* Live Render/Vercel responses (the audit tool could not call the live API); behaviour was tested on the same code locally.
* Whether Supabase **Row Level Security** is on, and whether Render uses the secret/service key or the public key.
* Render and Vercel environment variables, and Supabase Auth / `user_roles` setup (the `user_roles` table is not in `schema.sql`).
* The new Content-Security-Policy in a real browser.
* The new Gemini prompt rule against the live Gemini API.
* Forks, GitHub secret-scanning alerts, or secrets pasted elsewhere (chats, screenshots).

## 8. Final status
Backend and website are **hardened against the common, easy attacks** (open admin routes, open CORS, floods, oversized input, error leaks, missing headers). The project is suitable for a hackathon demo. It is **not production-ready** until real sign-in, Row Level Security and the upgrades above are done.
