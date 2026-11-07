# Mohar QA Evaluation Guide, Bug Report Template & 15-Point Checklist

## 1. How to Compute Precision, Recall & False-Positive Rate
After running all 30 samples from `test_samples.csv` on the live app and recording the real outputs in `test_results_template.csv`:
- **`correct` (True Positives, TP):** Number of rule/fact IDs in `detected_issues` that match `expected_issues`.
- **`missed` (False Negatives, FN):** Number of rule/fact IDs in `expected_issues` that Mohar did not flag.
- **`false_alarms` (False Positives, FP):** Number of findings returned by Mohar that are not in `expected_issues` (including any flags on clean samples `S-026` to `S-030`).
- **`evidence_valid_count`:** Number of findings for that sample where `evidence_valid = true`.

### Formulas
1. **Precision** = `Sum(correct) / (Sum(correct) + Sum(false_alarms))`
2. **Recall** = `Sum(correct) / (Sum(correct) + Sum(missed))`
3. **Clean Sample False-Positive Rate (FPR)** = `(Number of clean samples S-026 to S-030 where false_alarms > 0) / 5`
4. **Average False Alarms per Sample** = `Sum(false_alarms) / 30`
5. **Evidence Validity Rate** = `Sum(evidence_valid_count) / (Sum(correct) + Sum(false_alarms))`

---

## 2. Bug Report Template

### Bug ID: BUG-001
- **Title:** [Short summary of the bug]
- **Environment:** [Live Vercel URL / Render Backend URL] | [Laptop / Mobile] | [Browser]
- **Role Selected:** [Creator / Manager / Reviewer]
- **Severity:** [Blocker / High / Medium / Low]
- **Component:** [Frontend UI / Backend API / Rules Engine / Gemini Pipeline / Supabase DB]
- **Steps to Reproduce:**
  1. Open live URL in an Incognito window.
  2. Switch role to [...]
  3. Click [...] / Submit sample [...]
- **Expected Result:** [Expected behavior per MASTER CONTEXT]
- **Actual Result:** [Actual behavior / HTTP status code / UI glitch]
- **Console / Network Error Logs:** [Paste error from browser DevTools]
- **Status:** [Open / In Progress / Fixed / Verified]

---

## 3. 15-Point Incognito Live-Link Checklist
- [ ] **1. Zero-Login Access:** Live Vercel URL opens directly into the AstraPay demo workspace with no login wall or sign-up prompt.
- [ ] **2. Cold-Start Handling:** When the Render backend is waking up (~50s cold start), the UI displays *"Waking up the server, this can take up to a minute..."* without crashing.
- [ ] **3. Backend Health Check:** `GET /health` on the Render backend returns `200 OK`.
- [ ] **4. Workspace Seed Data:** Workspace page displays all 12 AstraPay rules (`CL-001` to `AC-001`) and 10 facts (`F-001` to `F-010`), with green valid badges and a red `EXPIRED` badge on `F-004` (15 Nov 2025).
- [ ] **5. Role Switcher:** Switching between **Creator**, **Manager**, and **Reviewer** in the top bar updates available actions immediately.
- [ ] **6. Try Sample Content Button:** Clicking **"Try sample content"** on the Submit page fills in a sample post with planted errors.
- [ ] **7. Submission & Review Execution:** Clicking **Submit** calls `POST /api/submissions` and loads the Findings view with an overall status badge (`Blocked`, `Needs review`, or `Ready for approval`).
- [ ] **8. Source-Backed Findings:** Every finding card shows category, severity, confidence, highlighted excerpt, `rule_or_fact_id`, explanation, and 2 suggested fixes (`fix_1`, `fix_2`).
- [ ] **9. Evidence Validator Guardrail:** Any finding with `evidence_valid = false` or `needs_human = true` is marked *"Needs human verification"*.
- [ ] **10. Creator Fix Actions:** Clicking **Accept**, **Edit** (custom text), or **Reject** (with reason) saves via `POST /api/findings/{id}/decision`.
- [ ] **11. Resubmission & Versioning:** Clicking **Resubmit** calls `POST /api/submissions/{id}/resubmit`, creates version `v2`, and re-runs the review pipeline.
- [ ] **12. Manager Approval Workflow:** Switching to **Manager** allows executing **Approve**, **Reject**, or **Request changes** with a comment via `POST /api/submissions/{id}/approval`.
- [ ] **13. Version History & Audit Log:** Opening the **History** tab (`GET /api/submissions/{id}/history`) shows all versions (`v1`, `v2`) and the chronological audit log.
- [ ] **14. Dashboard Analytics:** Opening the **Dashboard** page (`GET /api/dashboard`) shows counts by category, most violated rules, and pending reviews.
- [ ] **15. Mobile Layout & Clean Console:** Flow works cleanly on a mobile viewport (375px width) and browser DevTools Console shows zero unhandled errors or CORS failures.
