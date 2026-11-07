# Mohar - Brand Governance Platform

## Overview
Mohar is a pre-publication brand-governance web app built for CodeNexus India 2026 (Problem Statement by Inkloom AI). It checks an organisation's content BEFORE publishing against approved brand guidelines and facts. Mohar finds issues in tone, terminology, and facts, explains the issue with the exact rule ID, and suggests meaning-preserving fixes. Core promise: "No source, no flag. No silent changes. No automatic approvals."

## Live Demo
* **Live Link:** [Insert your Vercel link here]
* **Demo Brand:** AstraPay (Fictional Indian fintech/UPI app).

## Judge Testing Steps (2 Minutes)
1. Open the live link (no login required).
2. Ensure the Role Switcher at the top left is set to **Creator**.
3. Click **Submit Content** -> **Try sample content** -> **Run Mohar Analysis**.
4. View the findings. Notice the explicit rule/fact citations. Click **Option 1** on a fix to apply it to the editor, then click **Save Edits & Re-Analyze**.
5. Switch the Role to **Manager**. 
6. Go to **Manager Queue**, click **View Details** on your submission, and hit **Approve**.

## Architecture & Tech Stack
* **Frontend:** React (Vite) + Tailwind CSS, deployed on Vercel.
* **Backend:** Python FastAPI + Pydantic, deployed on Render (free tier).
* **Database:** Supabase PostgreSQL.
* **AI:** Gemini API (`gemini-2.5-flash` via `google-genai` SDK) for semantic checks, wrapped in a strict validation pipeline.

## How to Run Locally
1. Clone the repo to your machine.
2. **Backend:** `cd app` -> `python -m venv venv` -> `.\venv\Scripts\activate` -> `pip install -r requirements.txt` -> `uvicorn main:app --reload`.
3. **Frontend:** `cd mohar-frontend` -> `npm install` -> `npm run dev`.

## Environment Variables Needed
`GEMINI_API_KEY`, `GEMINI_MODEL`, `SUPABASE_URL`, `SUPABASE_KEY`, `FRONTEND_URL`, `VITE_API_URL`

## Disclosures
* **Third-Party Services:** Gemini API, Supabase, Render, Vercel, GitHub.
* **AI Assistants Used:** Gemini and Claude were utilised for code generation, debugging, and project planning.

## Built vs Planned & Limitations
* **Built:** Complete review pipeline (rules engine + Gemini + validator + normaliser), Creator submission flow, Manager approval queues, Reviewer knowledge base management, and full audit logs.
* **Limitations:** Render free tier has a ~50s cold start. Simple hashing is used for caching instead of Redis to keep costs at zero. 
* **Planned for later:** Image accessibility checks (deferred to Round 3).

## Team Contributions (nsmohit2008)
* **Junaid:** AI-1 Backend API, AI-2 AI-pipeline
* **Prasanna:** AI-3 Frontend React, AI-4 UI polish and Vercel deployment
* **Mohit:** AI-5 Testing/data, AI-6 Documentation & Submission
