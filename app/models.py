from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Core Finding Model ---
class FindingBase(BaseModel):
    category: Literal[
        "unsupported_claim",
        "fact_error",
        "expired_fact",
        "terminology",
        "tone",
        "disclaimer",
        "accessibility"
    ]
    severity: Literal["high", "medium", "low"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    excerpt: str
    rule_or_fact_id: str
    explanation: str
    fix_1: str
    fix_2: str
    needs_human: bool = False

class FindingRecord(FindingBase):
    id: str
    version_id: str
    source_ref: Optional[str] = None
    evidence_valid: bool = True
    decision: str = "pending"
    decision_reason: Optional[str] = None

# --- Workspace Models ---
class RuleModel(BaseModel):
    id: str
    category: str
    text: str
    severity: Literal["high", "medium", "low"]
    version: int = 1
    is_mandatory: bool = False

class FactModel(BaseModel):
    id: str
    approved_text: str
    source: str
    owner: str
    valid_from: Optional[str] = None
    expires_on: Optional[str] = None
    status: str

class SampleContentModel(BaseModel):
    title: str
    channel: str
    audience: str
    text: str

class WorkspaceResponse(BaseModel):
    workspace: dict
    rules: List[RuleModel]
    facts: List[FactModel]
    sample_content: List[SampleContentModel]

# --- Submission Request Models ---
class SubmissionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    channel: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    creator: str = Field(default="Creator")

class FindingDecisionRequest(BaseModel):
    action: Literal["accept", "reject", "edit"]
    reason: Optional[str] = None
    edited_text: Optional[str] = None

class ResubmitRequest(BaseModel):
    text: str = Field(..., min_length=1)

class ApprovalRequest(BaseModel):
    role: str = Field(default="Manager")
    decision: Literal["approve", "reject", "request_changes"]
    comment: Optional[str] = None

# --- M4: Rule & Fact Management Models ---
class RuleCreateRequest(BaseModel):
    id: str
    category: str
    text: str
    severity: Literal["high", "medium", "low"]
    is_mandatory: bool = False

class RuleUpdateRequest(BaseModel):
    text: Optional[str] = None
    severity: Optional[Literal["high", "medium", "low"]] = None
    is_mandatory: Optional[bool] = None

class FactCreateRequest(BaseModel):
    id: str
    approved_text: str
    source: str
    owner: str
    valid_from: Optional[str] = None
    expires_on: Optional[str] = None
    status: str = "active"

class FactUpdateRequest(BaseModel):
    approved_text: Optional[str] = None
    source: Optional[str] = None
    owner: Optional[str] = None
    valid_from: Optional[str] = None
    expires_on: Optional[str] = None
    status: Optional[str] = None
