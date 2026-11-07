# app/pipeline.py
"""
Unified review pipeline for Mohar:
1) Deterministic rules engine (plain Python)
2) Gemini analysis (single call, JSON array validated with Pydantic, retry once, fallback)
3) Evidence validator (verifies cited rule/fact ID and excerpt substring)
4) Normaliser / De-duplicator (merges overlapping findings on same excerpt/category;
   keeps severity and confidence SEPARATE)
5) Status calculator ('blocked' | 'needs_review' | 'ready_for_approval')
6) In-memory cache keyed by SHA-256 hash of (text, channel, audience)
"""

from __future__ import annotations

import copy
import hashlib
from datetime import date
from typing import Any, Dict, List, Optional

from app.gemini_client import analyze_with_gemini
from app.rules_engine import DEFAULT_FACTS, DEFAULT_RULES, run_rules_engine
from app.validator import validate_findings

# Simple in-memory cache keyed by SHA-256 hash of (text, channel, audience)
_PIPELINE_CACHE: Dict[str, Dict[str, Any]] = {}

SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


def make_cache_key(text: str, channel: str = "social", audience: str = "general") -> str:
    """Computes a deterministic SHA-256 hash for (text, channel, audience)."""
    normalized = f"{text.strip()}|{channel.strip().lower()}|{audience.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def clear_pipeline_cache() -> None:
    """Clears the in-memory review cache (useful for tests or when rules/facts change)."""
    _PIPELINE_CACHE.clear()


def _excerpts_overlap(excerpt_a: str, excerpt_b: str) -> bool:
    """Returns True if two excerpts are identical or one is a substring of the other (case-insensitive)."""
    a = excerpt_a.strip().lower()
    b = excerpt_b.strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normaliser: merges overlapping findings that share the same (excerpt, category)
    or (excerpt, rule_or_fact_id).
    Prefers valid evidence and higher confidence (rules engine = 1.0) while keeping
    severity and confidence strictly SEPARATE.
    """
    # Sort so valid evidence and deterministic findings (confidence 1.0) come first
    sorted_findings = sorted(
        findings,
        key=lambda f: (
            bool(f.get("evidence_valid", False)),
            float(f.get("confidence", 0.0)),
            SEVERITY_RANK.get(str(f.get("severity", "low")), 1),
        ),
        reverse=True,
    )

    deduped: List[Dict[str, Any]] = []
    for candidate in sorted_findings:
        c_excerpt = str(candidate.get("excerpt", ""))
        c_cat = str(candidate.get("category", "")).lower()
        c_id = str(candidate.get("rule_or_fact_id", "")).upper()

        is_duplicate = False
        for existing in deduped:
            e_excerpt = str(existing.get("excerpt", ""))
            e_cat = str(existing.get("category", "")).lower()
            e_id = str(existing.get("rule_or_fact_id", "")).upper()

            if _excerpts_overlap(c_excerpt, e_excerpt) and (c_cat == e_cat or c_id == e_id):
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(candidate)

    return deduped


def compute_submission_status(
    findings: List[Dict[str, Any]],
    fallback_used: bool = False,
) -> str:
    """
    Computes submission status according to MASTER CONTEXT:
    - 'blocked': at least one unresolved high-severity finding with valid evidence
    - 'needs_review': invalid/uncertain evidence, low confidence (< 0.75), needs_human=True,
      unresolved medium/low findings, or when Gemini failed and fallback was used
    - 'ready_for_approval': no unresolved findings and full pipeline succeeded
    """
    unresolved = [
        f for f in findings if str(f.get("decision", "pending")).lower() not in ("accept", "edit")
    ]

    if not unresolved:
        return "needs_review" if fallback_used else "ready_for_approval"

    for f in unresolved:
        if str(f.get("severity", "")).lower() == "high" and bool(f.get("evidence_valid", False)):
            return "blocked"

    return "needs_review"


def run_review_pipeline(
    text: str,
    channel: str = "social",
    audience: str = "general",
    rules: Optional[List[Dict[str, Any]]] = None,
    facts: Optional[List[Dict[str, Any]]] = None,
    use_cache: bool = True,
    use_gemini: bool = True,
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Runs the complete Mohar review pipeline:
    1. Check cache
    2. Run deterministic rules engine
    3. Run Gemini analysis (unless disabled or fallback triggered)
    4. Validate all findings through evidence validator
    5. De-duplicate overlapping findings
    6. Compute submission status
    """
    active_rules = rules if rules is not None else DEFAULT_RULES
    active_facts = facts if facts is not None else DEFAULT_FACTS

    cache_key = make_cache_key(text=text, channel=channel, audience=audience)
    if use_cache and cache_key in _PIPELINE_CACHE:
        cached_result = copy.deepcopy(_PIPELINE_CACHE[cache_key])
        cached_result["cache_hit"] = True
        return cached_result

    # Step 1: Deterministic rules engine
    rule_findings = run_rules_engine(
        text=text,
        rules=active_rules,
        facts=active_facts,
        reference_date=reference_date,
    )

    # Step 2: Gemini AI analysis (one call per review)
    gemini_findings: List[Dict[str, Any]] = []
    fallback_used = False
    notice: Optional[str] = None

    if use_gemini:
        gemini_findings, fallback_used, notice = analyze_with_gemini(
            text=text,
            rules=active_rules,
            facts=active_facts,
            channel=channel,
            audience=audience,
        )

    # Step 3: Evidence validator (validates both rules engine and Gemini outputs)
    combined_raw = rule_findings + gemini_findings
    validated_findings = validate_findings(
        findings=combined_raw,
        content=text,
        rules=active_rules,
        facts=active_facts,
    )

    # Step 4: Normaliser / De-duplicator
    final_findings = deduplicate_findings(validated_findings)

    # Step 5: Compute status
    status = compute_submission_status(
        findings=final_findings,
        fallback_used=fallback_used,
    )

    result = {
        "status": status,
        "findings": final_findings,
        "fallback_used": fallback_used,
        "notice": notice,
        "cache_hit": False,
    }

    # Only cache when Gemini succeeded or when Gemini was intentionally disabled
    if use_cache and (not fallback_used or not use_gemini):
        _PIPELINE_CACHE[cache_key] = copy.deepcopy(result)

    return result