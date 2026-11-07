# app/validator.py
"""
Evidence validator for Mohar.
Core promise: "No source, no flag. No silent changes. No automatic approvals."
Checks every finding to ensure:
1) `rule_or_fact_id` exists in the workspace's `rules` or `facts` tables.
2) `excerpt` is an actual substring of the submitted content (case-insensitive).
If either check fails, sets `evidence_valid = False` and `needs_human = True`.
Also populates `source_ref` with the authoritative rule/fact text for the UI and DB.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.rules_engine import DEFAULT_FACTS, DEFAULT_RULES

LOW_CONFIDENCE_THRESHOLD = 0.75


def build_source_lookup(
    rules: Optional[List[Dict[str, Any]]] = None,
    facts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    Builds a dictionary mapping valid rule/fact IDs (e.g. 'CL-001', 'F-002')
    to their human-readable description for `source_ref`.
    """
    active_rules = rules if rules is not None else DEFAULT_RULES
    active_facts = facts if facts is not None else DEFAULT_FACTS

    lookup: Dict[str, str] = {}
    for r in active_rules:
        rid = str(r.get("id", "")).strip()
        if rid:
            lookup[rid.upper()] = str(r.get("text", "")).strip()

    for f in active_facts:
        fid = str(f.get("id", "")).strip()
        if fid:
            exp = f.get("expires_on")
            exp_suffix = f" (Expires: {exp})" if exp else ""
            lookup[fid.upper()] = f"{str(f.get('approved_text', '')).strip()}{exp_suffix}"

    return lookup


def _find_exact_excerpt_in_content(content: str, candidate_excerpt: str) -> Optional[str]:
    """
    Checks if `candidate_excerpt` is a substring of `content` (case-insensitive).
    If found, returns the exact slice from `content` so frontend highlighting matches.
    """
    if not candidate_excerpt or not candidate_excerpt.strip():
        return None

    needle = candidate_excerpt.strip()
    idx = content.lower().find(needle.lower())
    if idx == -1:
        return None
    return content[idx : idx + len(needle)]


def validate_findings(
    findings: List[Dict[str, Any]],
    content: str,
    rules: Optional[List[Dict[str, Any]]] = None,
    facts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Validates each finding's cited `rule_or_fact_id` and `excerpt` against DB lists and `content`.
    Sets `evidence_valid`, `needs_human`, and `source_ref` accordingly.
    """
    source_lookup = build_source_lookup(rules=rules, facts=facts)
    validated: List[Dict[str, Any]] = []

    for item in findings:
        finding = dict(item)
        cited_id = str(finding.get("rule_or_fact_id", "")).strip().upper()
        raw_excerpt = str(finding.get("excerpt", ""))
        confidence = float(finding.get("confidence", 0.0))

        # 1. Check if rule_or_fact_id exists in DB rules or facts
        id_exists = cited_id in source_lookup

        # 2. Check if excerpt appears in content (case-insensitive)
        matched_slice = _find_exact_excerpt_in_content(content, raw_excerpt)
        excerpt_exists = matched_slice is not None

        if id_exists and excerpt_exists:
            finding["rule_or_fact_id"] = cited_id
            finding["excerpt"] = matched_slice
            finding["evidence_valid"] = True
            finding["source_ref"] = f"{cited_id}: {source_lookup[cited_id]}"
            # Low confidence findings still require human verification
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                finding["needs_human"] = True
            else:
                finding["needs_human"] = bool(finding.get("needs_human", False))
        else:
            # Never trust AI blindly: flag as invalid evidence and require human verification
            finding["evidence_valid"] = False
            finding["needs_human"] = True
            reasons = []
            if not id_exists:
                reasons.append(f'cited ID "{cited_id}" is not in approved rules/facts')
            if not excerpt_exists:
                reasons.append("excerpt does not match exact text in submission")

            reason_note = f" [Needs human verification: {'; '.join(reasons)}]"
            finding["explanation"] = str(finding.get("explanation", "")).strip() + reason_note
            finding["source_ref"] = (
                f"{cited_id}: {source_lookup[cited_id]}"
                if id_exists
                else f"Unverified source ({cited_id or 'none'}) - needs human verification"
            )

        validated.append(finding)

    return validated