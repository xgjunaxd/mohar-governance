import os
import re
import uuid
import csv
import hmac
import time
import logging
from io import StringIO
from datetime import datetime
from datetime import date
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db import get_db
from app.models import (
    WorkspaceResponse, SubmissionCreateRequest, FindingDecisionRequest, 
    ResubmitRequest, ApprovalRequest, RuleCreateRequest, RuleUpdateRequest,
    FactCreateRequest, FactUpdateRequest, LoginRequest, DemoLoginRequest
)
from app.seed import WORKSPACE_DATA, RULES_SEED, FACTS_SEED, SAMPLE_CONTENT_SEED
from app.pipeline import run_review_pipeline
from app.status import calculate_status
from app.pipeline import clear_pipeline_cache
from app.security import SecurityHeadersMiddleware, RateLimitMiddleware
from app import auth_service, facts_lifecycle, visual

load_dotenv()

logger = logging.getLogger("mohar")

# Set ENABLE_DOCS=false on Render to hide /docs, /redoc and /openapi.json.
_docs_on = os.getenv("ENABLE_DOCS", "true").strip().lower() != "false"
app = FastAPI(
    title="Mohar Brand Governance API",
    description="Pre-publication brand-governance backend for AstraPay (Demo Brand)",
    version="1.0.0",
    docs_url="/docs" if _docs_on else None,
    redoc_url="/redoc" if _docs_on else None,
    openapi_url="/openapi.json" if _docs_on else None,
)
bearer_scheme = HTTPBearer(auto_error=False)

# Set REQUIRE_AUTH=true on Render only after the frontend has a sign-in screen.
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").strip().lower() == "true"
APPROVER_ROLES = {"manager"}          # only Managers approve / reject / request changes
KNOWLEDGE_ROLES = {"reviewer"}        # only Reviewers edit rules and facts
_TOKEN_CACHE = {}                     # token -> (expires_at, actor); avoids a Supabase call on every request
_TOKEN_TTL = 60


def get_actor(credentials, claimed_role=None):
    """Who is calling? Returns {"id", "email", "role"}.

    * A Supabase access token is verified, and the role comes from the user_roles table.
    * With no token: refused when REQUIRE_AUTH=true, otherwise the old top-bar role is used
      (kept so the old UI and the old tests keep working during the switch-over).
    """
    if credentials is not None or REQUIRE_AUTH:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Sign in required")
        token = credentials.credentials
        hit = _TOKEN_CACHE.get(token)
        now = time.time()
        if hit and hit[0] > now:
            return hit[1]
        db = get_db()
        try:
            user = db.auth.get_user(token).user
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired sign-in")
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in required")
        rows = db.table("user_roles").select("role").eq("user_id", user.id).execute().data or []
        if not rows:
            raise HTTPException(status_code=403, detail="No role assigned")
        actor = {"id": user.id, "email": getattr(user, "email", None), "role": str(rows[0]["role"]).strip().capitalize()}
        if len(_TOKEN_CACHE) > 500:
            _TOKEN_CACHE.clear()
        _TOKEN_CACHE[token] = (now + _TOKEN_TTL, actor)
        return actor
    return {"id": None, "email": None, "role": (claimed_role or "Creator").strip()}


def actor_dep(credentials=Depends(bearer_scheme)):
    return get_actor(credentials, None)


def creator_dep(credentials=Depends(bearer_scheme)):
    """Submitting, deciding on findings and resubmitting are Creator actions."""
    actor = get_actor(credentials, None)
    if actor["id"] is not None and actor["role"].lower() != "creator":
        raise HTTPException(status_code=403, detail="Only Creators can submit or edit content.")
    return actor


def resolve_actor(credentials, claimed_role):
    """Approval guard: real Manager sign-in (or, in legacy mode, the Manager role)."""
    actor = get_actor(credentials, claimed_role)
    if actor["role"].lower() not in APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Only Managers can approve, reject or request changes")
    return actor


def require_admin(request: Request, credentials=Depends(bearer_scheme)):
    """Guards rule/fact management. Allowed: (a) a signed-in Reviewer, or (b) the secret
    X-Admin-Key header matching ADMIN_API_KEY on Render. Everyone else is refused."""
    admin_key = os.getenv("ADMIN_API_KEY", "").strip()
    sent_key = request.headers.get("x-admin-key", "")
    if admin_key and hmac.compare_digest(sent_key.encode(), admin_key.encode()):
        return {"id": None, "email": "admin-key", "role": "admin"}
    if credentials is not None or REQUIRE_AUTH:
        actor = get_actor(credentials, None)
        if actor["role"].lower() not in KNOWLEDGE_ROLES:
            raise HTTPException(status_code=403, detail="Only Reviewers can change rules and facts")
        return actor
    raise HTTPException(status_code=401, detail="Admin access required")


def _own_or_staff(actor, sub):
    """Creators can only open their own submissions; Managers and Reviewers see all."""
    if actor["id"] and actor["role"].lower() == "creator" and sub.get("creator_id") and sub["creator_id"] != actor["id"]:
        raise HTTPException(status_code=403, detail="This submission belongs to another creator.")


def safe_insert(db, table, record, optional=()):
    """Insert a row; if the database does not have the new Round 3 columns yet
    (migration not run), retry without them so the app keeps working."""
    try:
        return db.table(table).insert(record).execute()
    except Exception:
        if not optional:
            raise
        slim = {k: v for k, v in record.items() if k not in optional}
        if slim == record:
            raise
        logger.warning("insert into %s retried without %s (run schema_round3.sql)", table, optional)
        return db.table(table).insert(slim).execute()


def log_audit(db, sub_id, actor, action, detail, when=None):
    rec = {"id": str(uuid.uuid4()), "submission_id": sub_id, "role": actor["role"], "action": action,
           "detail": detail, "actor_id": actor["id"], "actor_email": actor["email"]}
    if when:
        rec["created_at"] = when
    safe_insert(db, "audit_log", rec, optional=("actor_id", "actor_email"))


# CORS: only our own frontend may call the API from a browser.
# Add more with ALLOWED_ORIGINS="https://a.com,https://b.com" on Render.
_origins = {
    "https://mohar-governance-snowy.vercel.app",
    "http://localhost:5173", "http://localhost:3000", "http://localhost:4173",
}
for _o in (os.getenv("FRONTEND_URL", ""), *os.getenv("ALLOWED_ORIGINS", "").split(",")):
    _o = _o.strip().rstrip("/")
    if _o and _o != "*":
        _origins.add(_o)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key"],
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
def create_submission(req: SubmissionCreateRequest, actor=Depends(creator_dep)):
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
        safe_insert(db, "submissions", {
            "id": sub_id, "title": req.title, "channel": req.channel,
            "audience": req.audience, "creator": actor["email"] or req.creator,
            "creator_id": actor["id"],
            "status": status, "current_version": 1
        }, optional=("creator_id",))
        
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
            
        log_audit(db, sub_id, actor if actor["id"] else {**actor, "role": req.creator},
                  "created_submission", "Submitted version 1 for review", now_iso)
        
        return {
            "submission_id": sub_id, "version_id": version_id,
            "status": status, "ai_used": not pipeline_result["fallback_used"],
            "findings": db_findings
        }
    except Exception:
        logger.exception("create_submission failed")
        raise HTTPException(status_code=500, detail="Could not save the submission. Please try again.")

@app.get("/api/submissions")
def list_submissions(actor=Depends(actor_dep)):
    db = get_db()
    q = db.table("submissions").select("*")
    if actor["id"] and actor["role"].lower() == "creator":
        q = q.eq("creator_id", actor["id"])       # creators only see their own posts
    return q.order("id", desc=True).execute().data

@app.get("/api/submissions/{sub_id}")
def get_submission_detail(sub_id: str, actor=Depends(actor_dep)):
    db = get_db()
    sub_res = db.table("submissions").select("*").eq("id", sub_id).execute()
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Submission not found")
    _own_or_staff(actor, sub_res.data[0])
    
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
def record_finding_decision(finding_id: str, req: FindingDecisionRequest, actor=Depends(creator_dep)):
    db = get_db()
    if req.action == "reject" and not req.reason:
        raise HTTPException(status_code=400, detail="A reason is required when rejecting a finding.")

    f_res = db.table("findings").select("version_id").eq("id", finding_id).execute()
    if not f_res.data:
        raise HTTPException(status_code=404, detail="Finding not found")

    version_id = f_res.data[0]["version_id"]
    v_res = db.table("versions").select("submission_id").eq("id", version_id).execute()
    sub_id = v_res.data[0]["submission_id"]
    sub_row = db.table("submissions").select("*").eq("id", sub_id).execute().data
    if sub_row:
        _own_or_staff(actor, sub_row[0])

    update_data = {"decision": req.action, "decision_reason": req.reason if req.action == "reject" else None}
    if req.action == "edit" and req.edited_text:
        update_data["fix_1"] = req.edited_text

    db.table("findings").update(update_data).eq("id", finding_id).execute()

    all_findings = db.table("findings").select("*").eq("version_id", version_id).execute()
    new_status = calculate_status(all_findings.data)

    db.table("submissions").update({"status": new_status}).eq("id", sub_id).execute()
    log_audit(db, sub_id, actor, f"finding_{req.action}", f"Decided '{req.action}' on finding {finding_id}",
              datetime.utcnow().isoformat())

    return {"status": "success", "new_submission_status": new_status}

@app.post("/api/submissions/{sub_id}/resubmit")
def resubmit_content(sub_id: str, req: ResubmitRequest, actor=Depends(creator_dep)):
    db = get_db()
    sub_res = db.table("submissions").select("*").eq("id", sub_id).execute()
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Submission not found")
    submission = sub_res.data[0]
    _own_or_staff(actor, submission)
    if submission.get("channel") == "visual_asset":
        raise HTTPException(status_code=400, detail="Image submissions cannot be re-analysed from text. Upload the corrected image as a new submission.")

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
        
        log_audit(db, sub_id, actor, "resubmitted", f"Submitted version {new_version_no}", now_iso)
        
        return {
            "submission_id": sub_id, "new_version_id": new_version_id,
            "new_version_no": new_version_no, "status": new_status,
            "ai_used": not pipeline_result["fallback_used"],
            "findings": db_findings
        }
    except Exception:
        logger.exception("resubmit failed")
        raise HTTPException(status_code=500, detail="Could not save the new version. Please try again.")

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

    log_audit(db, subid, actor, f"{req.decision}_v{active_version}", log_detail)

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
def create_rule(req: RuleCreateRequest, admin=Depends(require_admin)):
    """Reviewer creates a new rule."""
    db = get_db()
    db.table("rules").insert(req.model_dump()).execute()
    clear_pipeline_cache()
    return {"status": "success", "rule_id": req.id}

@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: str, req: RuleUpdateRequest, admin=Depends(require_admin)):
    """Reviewer updates an existing rule (creates a new version internally)."""
    db = get_db()
    existing = db.table("rules").select("*").eq("id", rule_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    update_data["version"] = existing.data[0]["version"] + 1
    
    db.table("rules").update(update_data).eq("id", rule_id).execute()
    clear_pipeline_cache()
    return {"status": "success", "rule_id": rule_id, "new_version": update_data["version"]}

FACT_OPTIONAL_COLS = ("version", "topic", "updated_by", "updated_at")


def _all_facts(db):
    return db.table("facts").select("*").execute().data or []


@app.post("/api/facts")
def create_fact(req: FactCreateRequest, admin=Depends(require_admin)):
    """Reviewer creates a new fact (with optional validity dates). Returns conflict warnings."""
    db = get_db()
    who = admin.get("email") or admin["role"]
    record = req.model_dump()
    record.update({"version": 1, "updated_by": who})
    safe_insert(db, "facts", record, optional=FACT_OPTIONAL_COLS)
    clear_pipeline_cache()
    warnings = [c["message"] for c in facts_lifecycle.detect_conflicts(_all_facts(db), only_for=req.id)]
    return {"status": "success", "fact_id": req.id, "warnings": warnings}


@app.put("/api/facts/{fact_id}")
def update_fact(fact_id: str, req: FactUpdateRequest, admin=Depends(require_admin)):
    """Reviewer edits a fact. The old version is saved to fact_versions first, so nothing is lost."""
    db = get_db()
    existing = db.table("facts").select("*").eq("id", fact_id).execute().data
    if not existing:
        raise HTTPException(status_code=404, detail="Fact not found")
    cur = existing[0]
    who = admin.get("email") or admin["role"]

    data = req.model_dump()
    note = data.pop("change_note", None)
    clear_expiry = data.pop("clear_expiry", False)
    update = {k: v for k, v in data.items() if v is not None}
    if clear_expiry:
        update["expires_on"] = None
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to change.")

    new_from = update.get("valid_from", cur.get("valid_from"))
    new_exp = update.get("expires_on", cur.get("expires_on"))
    d_from, d_exp = facts_lifecycle.parse_date(new_from), facts_lifecycle.parse_date(new_exp)
    if d_from and d_exp and d_exp < d_from:
        raise HTTPException(status_code=400, detail="Expiry date cannot be before the valid-from date.")

    old_version = int(cur.get("version") or 1)
    try:  # keep the old version (history)
        db.table("fact_versions").insert({
            "id": str(uuid.uuid4()), "fact_id": fact_id, "version": old_version,
            "approved_text": cur.get("approved_text"), "source": cur.get("source"), "owner": cur.get("owner"),
            "valid_from": cur.get("valid_from"), "expires_on": cur.get("expires_on"),
            "status": cur.get("status"), "topic": cur.get("topic"),
            "changed_by": who, "change_note": note,
        }).execute()
    except Exception:
        logger.exception("could not archive fact version (run schema_round3.sql)")

    update.update({"version": old_version + 1, "updated_by": who, "updated_at": datetime.utcnow().isoformat()})
    try:
        db.table("facts").update(update).eq("id", fact_id).execute()
    except Exception:
        slim = {k: v for k, v in update.items() if k not in FACT_OPTIONAL_COLS}
        db.table("facts").update(slim).eq("id", fact_id).execute()
    clear_pipeline_cache()

    warnings = [c["message"] for c in facts_lifecycle.detect_conflicts(_all_facts(db), only_for=fact_id)]
    return {"status": "success", "fact_id": fact_id, "new_version": old_version + 1, "warnings": warnings}


@app.get("/api/facts/conflicts")
def list_fact_conflicts(actor=Depends(actor_dep)):
    return {"conflicts": facts_lifecycle.detect_conflicts(_all_facts(get_db()))}


@app.get("/api/facts/{fact_id}/versions")
def fact_versions(fact_id: str, actor=Depends(actor_dep)):
    db = get_db()
    cur = db.table("facts").select("*").eq("id", fact_id).execute().data
    if not cur:
        raise HTTPException(status_code=404, detail="Fact not found")
    try:
        old = db.table("fact_versions").select("*").eq("fact_id", fact_id).order("version", desc=True).execute().data or []
    except Exception:
        old = []
    return {"current": cur[0], "history": old}


@app.get("/api/alerts/expiring")
def expiring_alerts(actor=Depends(actor_dep)):
    """Facts that are expired or expire within 30 days, and the approved posts that repeat them."""
    db = get_db()
    facts = _all_facts(db)
    subs = db.table("submissions").select("id,title,current_version,status").eq("status", "approved").execute().data or []
    posts = []
    if subs:
        cur = {x["id"]: x["current_version"] for x in subs}
        titles = {x["id"]: x["title"] for x in subs}
        vers = db.table("versions").select("submission_id,version_no,body").in_("submission_id", list(cur)).execute().data or []
        for v in vers:
            if v["version_no"] == cur.get(v["submission_id"]):
                posts.append({"id": v["submission_id"], "title": titles.get(v["submission_id"]), "body": v["body"]})
    today = date.today()
    return {
        "as_of": today.isoformat(),
        "window_days": facts_lifecycle.EXPIRING_WINDOW_DAYS,
        "alerts": facts_lifecycle.expiry_alerts(facts, posts, today),
        "conflicts": facts_lifecycle.detect_conflicts(facts, today),
    }


# --- Round 3: sign-in -------------------------------------------------------

def _session_payload(session):
    rows = get_db().table("user_roles").select("role").eq("user_id", session["user_id"]).execute().data or []
    if not rows:
        raise HTTPException(status_code=403, detail="This account has no role assigned.")
    return {"access_token": session["access_token"], "expires_in": session["expires_in"],
            "email": session["email"], "role": str(rows[0]["role"]).strip().capitalize()}


@app.post("/api/auth/login")
def auth_login(req: LoginRequest):
    try:
        return _session_payload(auth_service.sign_in_password(req.email.strip(), req.password))
    except auth_service.AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/demo")
def auth_demo(req: DemoLoginRequest):
    """One-click sign-in to a real demo account (Creator / Manager / Reviewer)."""
    try:
        return _session_payload(auth_service.demo_sign_in(req.role))
    except auth_service.AuthError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/api/auth/me")
def auth_me(actor=Depends(actor_dep)):
    return {"email": actor["email"], "role": actor["role"]}


# --- Round 3: visual compliance & accessibility ------------------------------

@app.post("/api/visual-review")
async def visual_review(
    file: UploadFile = File(...),
    alt_text: str = Form(default=""),
    title: str = Form(default="Image asset"),
    actor=Depends(creator_dep),
):
    data = await file.read(visual.MAX_BYTES + 1)
    alt_text = alt_text.strip()[:500]
    title = (title.strip() or "Image asset")[:200]
    try:
        result = visual.analyze_image(data, alt_text)
    except visual.VisualError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db = get_db()
    rules = {r["id"]: r for r in (db.table("rules").select("*").execute().data or [])}
    findings = []
    for f in result["findings"]:
        rule = rules.get(f["rule"])
        findings.append({
            "id": str(uuid.uuid4()), "category": f["category"], "severity": f["severity"],
            "confidence": f["confidence"], "excerpt": f["excerpt"], "rule_or_fact_id": f["rule"],
            "source_ref": rule["text"] if rule else None, "explanation": f["explanation"],
            "fix_1": f["fix_1"], "fix_2": f["fix_2"],
            "needs_human": bool(f.get("needs_human")) or rule is None,   # no source in the rules table -> human check
            "evidence_valid": rule is not None, "decision": "pending",
        })
    status = calculate_status(findings, False)

    sub_id, version_id = str(uuid.uuid4()), str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    body = visual.describe_for_record(file.filename or "image", alt_text, result["metrics"])
    try:
        safe_insert(db, "submissions", {
            "id": sub_id, "title": title, "channel": "visual_asset", "audience": "general",
            "creator": actor["email"] or "Creator", "creator_id": actor["id"],
            "status": status, "current_version": 1,
        }, optional=("creator_id",))
        db.table("versions").insert({"id": version_id, "submission_id": sub_id, "version_no": 1,
                                     "body": body, "created_at": now_iso}).execute()
        for f in findings:
            f["version_id"] = version_id
            db.table("findings").insert(f).execute()
        log_audit(db, sub_id, actor, "created_visual_submission", "Image uploaded for visual compliance review", now_iso)
        return {"submission_id": sub_id, "version_id": version_id, "status": status,
                "metrics": result["metrics"], "findings": findings}
    except Exception:
        logger.exception("visual_review failed")
        raise HTTPException(status_code=500, detail="Could not save the image review. Please try again.")


@app.post("/api/rules/import")
async def import_rules_csv(file: UploadFile = File(...), admin=Depends(require_admin)):
    """Imports Rules from a CSV file upload (admin only, max 1 MB / 500 rows)."""
    content = await file.read(1_000_001)
    if len(content) > 1_000_000:
        raise HTTPException(status_code=413, detail="CSV file is too large (max 1 MB).")
    try:
        text_data = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 text.")
    reader = csv.DictReader(StringIO(text_data))

    db = get_db()
    count = skipped = 0
    for n, row in enumerate(reader):
        if n >= 500:
            break
        rid = (row.get("id") or "").strip()
        text = (row.get("text") or "").strip()
        category = (row.get("category") or "").strip()
        severity = (row.get("severity") or "medium").strip().lower()
        if (not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", rid) or not text or len(text) > 1000
                or not category or len(category) > 60):
            skipped += 1
            continue
        if severity not in ("high", "medium", "low"):
            severity = "medium"
        try:
            db.table("rules").upsert({
                "id": rid,
                "category": category,
                "text": text,
                "severity": severity,
                "is_mandatory": str(row.get("is_mandatory", "false")).lower() == "true",
                "version": 1
            }).execute()
            count += 1
        except Exception:
            logger.exception("rule import row failed")
            skipped += 1

    clear_pipeline_cache()
    return {"status": "success", "imported": count, "skipped": skipped}  
    clear_pipeline_cache()
    return {"status": "success", "imported": count, "skipped": skipped}


# --- Contact Form & Resend Integration ---
from pydantic import BaseModel
import hashlib
import json
import urllib.request

class ContactForm(BaseModel):
    name: str
    email: str
    message: str

@app.post("/contact")
def submit_contact_form(req: ContactForm, request: Request):
    db = get_db()
    
    # 1. IP Tracking & Rate Limiting (Protects from spam)
    client_ip = request.client.host if request.client else "unknown"
    salt = os.getenv("IP_HASH_SALT", "mohar2026")
    ip_hash = hashlib.sha256((client_ip + salt).encode("utf-8")).hexdigest()
    
    # Check if this IP has sent too many messages
    recent = db.table("contact_messages").select("id").eq("ip_hash", ip_hash).execute()
    if recent.data and len(recent.data) >= 3:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    # 2. Save securely to Supabase
    db.table("contact_messages").insert({
        "name": req.name,
        "email": req.email,
        "message": req.message,
        "ip_hash": ip_hash
    }).execute()

    # 3. Send Email via Resend
    resend_key = os.getenv("RESEND_API_KEY")
   to_email = "xgjunaxd@gmail.com"
    from_email = "onboarding@resend.dev"
    
    if resend_key and to_email:
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json"
            }
            data = {
                "from": from_email,
                "to": to_email,
                "subject": f"New Message from {req.name}",
                "html": f"<p><strong>Name:</strong> {req.name}</p><p><strong>Email:</strong> {req.email}</p><p><strong>Message:</strong><br>{req.message}</p>"
            }
            req_obj = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            urllib.request.urlopen(req_obj)
        except Exception as e:
            logger.error(f"Resend API failed: {e}")
            # Graceful fallback: fails silently so the database still saves
    
    return {"status": "success", "message": "Message saved and sent!"}
