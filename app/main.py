import os
import re
import uuid
import csv
from io import StringIO
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db import get_db
from app.models import (
    WorkspaceResponse, SubmissionCreateRequest, FindingDecisionRequest, 
    ResubmitRequest, ApprovalRequest, RuleCreateRequest, RuleUpdateRequest,
    FactCreateRequest, FactUpdateRequest
)
from app.seed import WORKSPACE_DATA, RULES_SEED, FACTS_SEED, SAMPLE_CONTENT_SEED
from app.pipeline import run_review_pipeline
from app.status import calculate_status

load_dotenv()

app = FastAPI(
    title="Mohar Brand Governance API",
    description="Pre-publication brand-governance backend for AstraPay (Demo Brand)",
    version="1.0.0",
)
bearer_scheme = HTTPBearer(auto_error=False)

# Set REQUIRE_AUTH=true on Render only after the frontend has a sign-in screen.
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").strip().lower() == "true"
APPROVER_ROLES = {"manager", "reviewer"}


def resolve_actor(credentials, claimed_role):
    """Real Supabase sign-in when a token is sent (or REQUIRE_AUTH=true);
    otherwise the role picked in the top bar."""
    if credentials is not None or REQUIRE_AUTH:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Sign in required")
        db = get_db()
        try:
            user = db.auth.get_user(credentials.credentials).user
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired sign-in")
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in required")
        rows = db.table("user_roles").select("role").eq("user_id", user.id).execute().data or []
        if not rows:
            raise HTTPException(status_code=403, detail="No role assigned")
        role = rows[0]["role"]
    else:
        role = (claimed_role or "").strip()

    if role.lower() not in APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Only Managers or Reviewers can approve")
    return {"role": role}
    
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def mask_sensitive_data(text: str) -> str:
    """Masks PII before sending to AI."""
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL MASKED]', text)
    text = re.sub(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE MASKED]', text)
    text = re.sub(r'\b\d{8,}\b', '[ACCOUNT MASKED]', text)
    return text

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "mohar-backend", "brand": "AstraPay (Demo)"}

@app.get("/api/workspace", response_model=WorkspaceResponse)
def get_workspace():
    try:
        db = get_db()
        rules_res = db.table("rules").select("*").order("id").execute()
        facts_res = db.table("facts").select("*").order("id").execute()
        ws_res = db.table("workspaces").select("*").eq("id", "astrapay-demo").execute()
        return {
            "workspace": ws_res.data[0] if ws_res.data else WORKSPACE_DATA,
            "rules": rules_res.data if rules_res.data else RULES_SEED,
            "facts": facts_res.data if facts_res.data else FACTS_SEED,
            "sample_content": SAMPLE_CONTENT_SEED,
        }
    except Exception as e:
        return {"workspace": WORKSPACE_DATA, "rules": RULES_SEED, "facts": FACTS_SEED, "sample_content": SAMPLE_CONTENT_SEED}

@app.post("/api/submissions")
def create_submission(req: SubmissionCreateRequest):
    db = get_db()
    
    # Bug 3 Fix: Fetch live rules and facts from the database
    rules_res = db.table("rules").select("*").execute()
    facts_res = db.table("facts").select("*").execute()
    live_rules = rules_res.data if rules_res.data else None
    live_facts = facts_res.data if facts_res.data else None
    
    masked_text = mask_sensitive_data(req.text)
    # Pass live rules and facts to the pipeline
    pipeline_result = run_review_pipeline(
        text=masked_text, 
        channel=req.channel, 
        audience=req.audience,
        rules=live_rules,
        facts=live_facts
    )
    status = calculate_status(pipeline_result["findings"], pipeline_result["fallback_used"])
    
    sub_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    
    try:
        db.table("submissions").insert({
            "id": sub_id, "title": req.title, "channel": req.channel, 
            "audience": req.audience, "creator": req.creator, 
            "status": status, "current_version": 1
        }).execute()
        
        db.table("versions").insert({
            "id": version_id, "submission_id": sub_id, 
            "version_no": 1, "body": req.text, "created_at": now_iso
        }).execute()
        
        db_findings = []
        for f in pipeline_result["findings"]:
            f_record = {
                "id": str(uuid.uuid4()), "version_id": version_id,
                "category": f.get("category"), "severity": f.get("severity"),
                "confidence": f.get("confidence"), "excerpt": f.get("excerpt"),
                "rule_or_fact_id": f.get("rule_or_fact_id"), "explanation": f.get("explanation"),
                "fix_1": f.get("fix_1"), "fix_2": f.get("fix_2"),
                "needs_human": f.get("needs_human", False),  # Bug 4 Fix: Added BEFORE insertion
                "evidence_valid": f.get("evidence_valid", True),
                "decision": "pending"
            }
            db.table("findings").insert(f_record).execute()
            db_findings.append(f_record)
            
        db.table("audit_log").insert({
            "id": str(uuid.uuid4()), "submission_id": sub_id,
            "role": req.creator, "action": "created_submission",
            "detail": "Submitted version 1 for review",
            "created_at": now_iso
        }).execute()
        
        return {
            "submission_id": sub_id, "version_id": version_id,
            "status": status, "ai_used": not pipeline_result["fallback_used"],
            "findings": db_findings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {str(e)}")

@app.get("/api/submissions")
def list_submissions():
    db = get_db()
    res = db.table("submissions").select("*").order("id", desc=True).execute()
    return res.data

@app.get("/api/submissions/{sub_id}")
def get_submission_detail(sub_id: str):
    db = get_db()
    sub_res = db.table("submissions").select("*").eq("id", sub_id).execute()
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    versions_res = db.table("versions").select("*").eq("submission_id", sub_id).order("version_no", desc=True).execute()
    versions = versions_res.data
    current_version_id = versions[0]["id"] if versions else None
    
    findings = []
    if current_version_id:
        findings_res = db.table("findings").select("*").eq("version_id", current_version_id).execute()
        findings = findings_res.data
        
    comments_res = db.table("comments").select("*").eq("submission_id", sub_id).order("created_at").execute()

    # The audit log is returned so the approval seal is still visible after a page reload.
    audit_res = db.table("audit_log").select("*").eq("submission_id", sub_id).order("created_at", desc=True).execute()
    
    return {
        "submission": sub_res.data[0],
        "versions": versions,
        "current_findings": findings,
        "comments": comments_res.data,
        "audit_logs": audit_res.data or []
    }

@app.post("/api/findings/{finding_id}/decision")
def record_finding_decision(finding_id: str, req: FindingDecisionRequest):
    db = get_db()
    if req.action == "reject" and not req.reason:
        raise HTTPException(status_code=400, detail="A reason is required when rejecting a finding.")
        
    f_res = db.table("findings").select("version_id").eq("id", finding_id).execute()
    if not f_res.data:
        raise HTTPException(status_code=404, detail="Finding not found")
        
    update_data = {"decision": req.action, "decision_reason": req.reason if req.action == "reject" else None}
    if req.action == "edit" and req.edited_text:
        update_data["fix_1"] = req.edited_text
        
    db.table("findings").update(update_data).eq("id", finding_id).execute()
    
    version_id = f_res.data[0]["version_id"]
    v_res = db.table("versions").select("submission_id").eq("id", version_id).execute()
    sub_id = v_res.data[0]["submission_id"]
    
    all_findings = db.table("findings").select("*").eq("version_id", version_id).execute()
    new_status = calculate_status(all_findings.data)
    
    db.table("submissions").update({"status": new_status}).eq("id", sub_id).execute()
    db.table("audit_log").insert({
        "id": str(uuid.uuid4()), "submission_id": sub_id,
        "role": "Creator", "action": f"finding_{req.action}",
        "detail": f"Decided '{req.action}' on finding {finding_id}",
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    
    return {"status": "success", "new_submission_status": new_status}

@app.post("/api/submissions/{sub_id}/resubmit")
def resubmit_content(sub_id: str, req: ResubmitRequest):
    db = get_db()
    sub_res = db.table("submissions").select("*").eq("id", sub_id).execute()
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Submission not found")
    submission = sub_res.data[0]
    
    # Bug 3 Fix: Fetch live rules and facts from the database for resubmissions
    rules_res = db.table("rules").select("*").execute()
    facts_res = db.table("facts").select("*").execute()
    live_rules = rules_res.data if rules_res.data else None
    live_facts = facts_res.data if facts_res.data else None
    
    new_version_no = submission["current_version"] + 1
    new_version_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    
    masked_text = mask_sensitive_data(req.text)
    # Pass live rules and facts to the pipeline
    pipeline_result = run_review_pipeline(
        text=masked_text, 
        channel=submission["channel"], 
        audience=submission["audience"],
        rules=live_rules,
        facts=live_facts
    )
    new_status = calculate_status(pipeline_result["findings"], pipeline_result["fallback_used"])
    
    try:
        db.table("versions").insert({
            "id": new_version_id, "submission_id": sub_id,
            "version_no": new_version_no, "body": req.text, "created_at": now_iso
        }).execute()
        
        db_findings = []
        for f in pipeline_result["findings"]:
            f_record = {
                "id": str(uuid.uuid4()), "version_id": new_version_id,
                "category": f.get("category"), "severity": f.get("severity"),
                "confidence": f.get("confidence"), "excerpt": f.get("excerpt"),
                "rule_or_fact_id": f.get("rule_or_fact_id"), "explanation": f.get("explanation"),
                "fix_1": f.get("fix_1"), "fix_2": f.get("fix_2"),
                "needs_human": f.get("needs_human", False),  # Bug 4 Fix: Added BEFORE insertion
                "evidence_valid": f.get("evidence_valid", True),
                "decision": "pending"
            }
            db.table("findings").insert(f_record).execute()
            db_findings.append(f_record)
            
        db.table("submissions").update({
            "current_version": new_version_no,
            "status": new_status
        }).eq("id", sub_id).execute()
        
        db.table("audit_log").insert({
            "id": str(uuid.uuid4()), "submission_id": sub_id,
            "role": "Creator", "action": "resubmitted",
            "detail": f"Submitted version {new_version_no}",
            "created_at": now_iso
        }).execute()
        
        return {
            "submission_id": sub_id, "new_version_id": new_version_id,
            "new_version_no": new_version_no, "status": new_status,
            "ai_used": not pipeline_result["fallback_used"],
            "findings": db_findings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resubmission failed: {str(e)}")

@app.post("/api/submissions/{subid}/approval")
def approve_submission(
    subid: str,
    req: ApprovalRequest,
    credentials=Depends(bearer_scheme),
):
    actor = resolve_actor(credentials, req.role)
    db = get_db()

    sub_res = db.table("submissions").select("*").eq("id", subid).execute()
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub = sub_res.data[0]

    active_version = sub["current_version"]

    if req.decision == "approve":
        if sub["status"] == "approved":
            raise HTTPException(status_code=409, detail="This submission is already approved.")

        # 'blocked' (unresolved high-severity findings) can never be approved.
        if sub["status"] not in ("ready_for_approval", "needs_review"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot approve a submission with status '{sub['status']}'. Resolve the high-severity findings first.",
            )

        # Accepted fixes only change the editor text; the saved text must be re-analysed first.
        cur_v = (
            db.table("versions").select("id")
            .eq("submission_id", subid).eq("version_no", active_version).execute()
        )
        if cur_v.data:
            f_res = db.table("findings").select("decision").eq("version_id", cur_v.data[0]["id"]).execute()
            if any(f.get("decision") in ("accept", "edit") for f in (f_res.data or [])):
                raise HTTPException(
                    status_code=409,
                    detail="Accepted fixes have not been applied yet. The creator must click 'Save Edits & Re-Analyze' first.",
                )
    
    # Bug 1 & 2 Fix: Cryptographically seal the approved version
    crypto_seal = None
    if req.decision == "approve":
        import hashlib
        v_res = db.table("versions").select("body").eq("submission_id", subid).eq("version_no", active_version).execute()
        if v_res.data:
            approved_text = v_res.data[0]["body"]
            crypto_seal = hashlib.sha256(approved_text.encode("utf-8")).hexdigest()

    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "request_changes": "changes_requested",
    }

    new_status = status_map.get(req.decision)
    if new_status is None:
        raise HTTPException(status_code=400, detail="Invalid approval decision")

    db.table("submissions").update(
        {"status": new_status}
    ).eq("id", subid).execute()

    log_detail = req.comment or f"Decision on version {active_version}"
    if crypto_seal:
        log_detail += f" | SHA-256 Seal: {crypto_seal}"

    db.table("audit_log").insert({
        "submission_id": subid,
        "role": actor["role"],
        "action": f"{req.decision}_v{active_version}",
        "detail": log_detail,
    }).execute()

    return {
        "message": "Decision recorded",
        "sealed_version": active_version,
        "crypto_seal": crypto_seal,
    }

@app.get("/api/submissions/{sub_id}/history")
def get_submission_history(sub_id: str):
    db = get_db()
    audit_res = db.table("audit_log").select("*").eq("submission_id", sub_id).order("created_at", desc=True).execute()
    return {"submission_id": sub_id, "history": audit_res.data}

@app.get("/api/dashboard")
def get_dashboard():
    """Returns analytics based ONLY on the current active version of submissions."""
    db = get_db()
    
    # 1. Get all submissions and their active version number
    subs_res = db.table("submissions").select("id, current_version, status").execute()
    subs = subs_res.data or []
    
    pending_reviews = sum(1 for s in subs if s["status"] == "needs_review")
    
    # 2. Get the specific version IDs that are currently active
    active_version_ids = []
    for s in subs:
        v_res = db.table("versions").select("id").eq("submission_id", s["id"]).eq("version_no", s["current_version"]).execute()
        if v_res.data:
            active_version_ids.append(v_res.data[0]["id"])
            
    # 3. Fetch findings only for active versions
    findings = []
    if active_version_ids:
        # Supabase Python client 'in_' takes a list
        f_res = db.table("findings").select("*").in_("version_id", active_version_ids).execute()
        findings = f_res.data or []

    counts_by_category = {}
    rule_violations = {}
    
    for f in findings:
        cat = f["category"]
        counts_by_category[cat] = counts_by_category.get(cat, 0) + 1
        
        rule_id = f["rule_or_fact_id"]
        rule_violations[rule_id] = rule_violations.get(rule_id, 0) + 1

    # Sort violated rules descending
    most_violated = [{"rule": k, "count": v} for k, v in sorted(rule_violations.items(), key=lambda item: item[1], reverse=True)]

    return {
        "counts_by_category": counts_by_category,
        "most_violated_rules": most_violated,
        "pending_reviews": pending_reviews
    }

# --- M4: Rule and Fact Management (Reviewer) ---

@app.post("/api/rules")
def create_rule(req: RuleCreateRequest):
    """Reviewer creates a new rule."""
    db = get_db()
    db.table("rules").insert(req.model_dump()).execute()
    return {"status": "success", "rule_id": req.id}

@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: str, req: RuleUpdateRequest):
    """Reviewer updates an existing rule (creates a new version internally)."""
    db = get_db()
    existing = db.table("rules").select("*").eq("id", rule_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    update_data["version"] = existing.data[0]["version"] + 1
    
    db.table("rules").update(update_data).eq("id", rule_id).execute()
    return {"status": "success", "rule_id": rule_id, "new_version": update_data["version"]}

@app.post("/api/facts")
def create_fact(req: FactCreateRequest):
    """Reviewer creates a new fact (with optional expiry)."""
    db = get_db()
    db.table("facts").insert(req.model_dump()).execute()
    return {"status": "success", "fact_id": req.id}

@app.put("/api/facts/{fact_id}")
def update_fact(fact_id: str, req: FactUpdateRequest):
    """Reviewer updates an existing fact."""
    db = get_db()
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    db.table("facts").update(update_data).eq("id", fact_id).execute()
    return {"status": "success", "fact_id": fact_id}

@app.post("/api/rules/import")
async def import_rules_csv(file: UploadFile = File(...)):
    """Imports Rules from a CSV file upload."""
    content = await file.read()
    text_data = content.decode("utf-8")
    reader = csv.DictReader(StringIO(text_data))
    
    db = get_db()
    count = 0
    for row in reader:
        try:
            db.table("rules").upsert({
                "id": row.get("id"),
                "category": row.get("category"),
                "text": row.get("text"),
                "severity": row.get("severity", "medium"),
                "is_mandatory": str(row.get("is_mandatory", "false")).lower() == "true",
                "version": 1
            }).execute()
            count += 1
        except Exception:
            continue # Skip bad rows
            
    return {"status": "success", "imported": count}
