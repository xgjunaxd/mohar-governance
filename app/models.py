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
    title: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1, max_length=5000)
    channel: str = Field(..., min_length=1, max_length=100)
    audience: str = Field(..., min_length=1, max_length=100)
    creator: str = Field(default="Creator", max_length=100)

class FindingDecisionRequest(BaseModel):
    action: Literal["accept", "reject", "edit"]
    reason: Optional[str] = Field(default=None, max_length=1000)
    edited_text: Optional[str] = Field(default=None, max_length=5000)

class ResubmitRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

class ApprovalRequest(BaseModel):
    role: str = Field(default="Manager", max_length=50)
    decision: Literal["approve", "reject", "request_changes"]
    comment: Optional[str] = Field(default=None, max_length=1000)

# --- M4: Rule & Fact Management Models ---
class RuleCreateRequest(BaseModel):
    id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{1,40}$")
    category: str = Field(..., min_length=1, max_length=60)
    text: str = Field(..., min_length=1, max_length=1000)
    severity: Literal["high", "medium", "low"]
    is_mandatory: bool = False

class RuleUpdateRequest(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    severity: Optional[Literal["high", "medium", "low"]] = None
    is_mandatory: Optional[bool] = None

class FactCreateRequest(BaseModel):
    id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{1,40}$")
    approved_text: str = Field(..., min_length=1, max_length=1000)
    source: str = Field(..., min_length=1, max_length=300)
    owner: str = Field(..., min_length=1, max_length=100)
    valid_from: Optional[str] = Field(default=None, max_length=10)
    expires_on: Optional[str] = Field(default=None, max_length=10)
    status: str = Field(default="active", max_length=30)

class FactUpdateRequest(BaseModel):
    approved_text: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    source: Optional[str] = Field(default=None, max_length=300)
    owner: Optional[str] = Field(default=None, max_length=100)
    valid_from: Optional[str] = Field(default=None, max_length=10)
    expires_on: Optional[str] = Field(default=None, max_length=10)
    status: Optional[str] = Field(default=None, max_length=30)
