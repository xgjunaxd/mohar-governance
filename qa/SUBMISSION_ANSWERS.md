# CodeNexus India 2026 - Submission Answers

## Features Completed
* Multi-stage deterministic and AI review pipeline.
* Automatic PII masking before content is sent to the LLM.
* Creator dashboard with exact source citations, confidence scores, and one-click fixes.
* Manager approval queue with version control and audit logging.
* Governance analytics dashboard calculating status breakdowns and rule violation frequencies.
* Reviewer portal to add, edit, and bulk-import rules and facts via CSV.

## Technology & Implementation Details
* **APIs & Models:** FastAPI for the backend. `gemini-2.5-flash` (temperature 0.2, JSON response mode) for semantic brand checking.
* **Validation:** Custom Pydantic models enforce the exact finding JSON structure. A secondary Python validator cross-references all AI citations against the database to prevent hallucinations ("No source, no flag").
* **Database:** Supabase PostgreSQL handles the relational data (workspaces, submissions, versions, findings, audit_log).

## Changes from the Original Plan
1. **Pipeline Architecture:** We consolidated from five independent AI agents into one streamlined pipeline (deterministic rules + single Gemini call + validator) to dramatically improve speed and reduce API costs.
2. **Authentication:** We replaced the real login system with a UI Role Switcher (Creator / Manager / Reviewer) to provide judges with a zero-friction testing experience.
3. **Context Handling:** Because the demo knowledge base is concise, we pass all rules and facts directly into the Gemini prompt rather than using a RAG/vector search, ensuring 100% recall.
4. **Scope Adjustment:** Visual and accessibility checks (checking images/logos) were moved to Round 3 to ensure the core text pipeline was bulletproof.
5. **Team Roles:** Role distribution was adjusted slightly from Round 1 based on the team's working dynamics (Junaid handled all Python, Prasanna handled all React).

## Three Major Round 3 Improvements (Planned)
1. **Claim verification with fact expiry and conflict handling:** Automated logic to detect if a creator is citing a fact or promotion that has expired or conflicts with a newer product policy.
2. **Visual compliance and accessibility checks:** Analysing image alt text, brand contrast ratios, and correct logo usage.
3. **Accuracy analytics and reviewer intelligence:** Tracking which AI-suggested fixes are most frequently rejected by creators in order to automatically refine and tune the system prompt over time.
