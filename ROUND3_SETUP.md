# Mohar Round 3: setup steps (do them in this order)

## 0. Files
Upload every file in this zip to GitHub at the SAME path (new files are marked NEW). Do not delete anything.

Backend (Render redeploys by itself):
- app/main.py, app/models.py, app/security.py
- app/auth_service.py (NEW), app/facts_lifecycle.py (NEW), app/visual.py (NEW), app/brand_palette.json (NEW)
- requirements.txt, .env.example, schema_round3.sql (NEW), scripts/create_demo_users.py (NEW)
- qa/test_round3.py (NEW), qa/run_eval.py

Frontend (Vercel redeploys by itself) in mohar-frontend/:
- src/services/api.js, src/context/RoleContext.jsx, src/App.jsx, src/kage-fx.js, vercel.json
- src/components/Navbar.jsx
- src/pages/Login.jsx (NEW), src/pages/Knowledge.jsx (NEW)
- src/pages/Submit.jsx, Findings.jsx, Queue.jsx, Dashboard.jsx, Workspace.jsx

## 1. Database (Supabase -> SQL Editor)
Paste all of schema_round3.sql and press Run. Safe to run twice.

## 2. Render environment variables (Render -> your service -> Environment)
- SUPABASE_KEY  = the SERVICE ROLE key (Supabase -> Project Settings -> API). Not the anon key.
- DEMO_PASSWORD = a long password you invent (10+ characters). Do not share it publicly.
- ALLOW_DEMO_LOGIN = true
- REQUIRE_AUTH  = false   (keep false until step 5)
- RATE_LIMIT_AUTH_PER_MIN = 10 (optional)

## 3. Create the 3 demo accounts (on your computer, once)
Put SUPABASE_URL, SUPABASE_KEY (service role) and DEMO_PASSWORD in a local .env file (never commit it), then:
    pip install supabase python-dotenv
    python scripts/create_demo_users.py

## 4. Push the code
Upload the files (step 0). Wait for Render and Vercel to finish deploying. Open the site: you should see the sign-in page.

## 5. Turn enforcement on
Render -> Environment -> REQUIRE_AUTH = true -> save (Render restarts).
Now the server refuses every request without a valid sign-in.

## 6. Test it (5 minutes)
1. Sign in as Creator -> Submit a sample post -> you should see findings. The Approvals tab shows only YOUR posts.
2. Creator tries to approve -> there is no Approve button (and the API would answer 403).
3. Sign in as Manager -> Approvals -> approve it -> the audit log shows manager@mohar-demo.app.
4. Sign in as Reviewer -> Knowledge -> Edit F-002 (change the number) -> Save -> History shows the old version.
   Add a fact with the same topic and a different number -> a conflict warning appears.
5. Set F-003's expiry to a date within 30 days -> Dashboard shows it under "Expiring & Expired Facts".
6. Creator -> Submit -> "Image / poster" -> upload any picture with empty alt text -> findings for alt text (AC-001).

## 7. QA re-run (after everything is live)
    set MOHAR_API_URL=https://mohar-api.onrender.com      (Windows: set, Mac/Linux: export)
    python qa/run_eval.py
    python -m pytest -q qa
The script signs in as the demo Creator by itself and waits if the rate limiter says 429.

## Rollback
Set REQUIRE_AUTH=false on Render, and restore the old frontend files from GitHub history.
