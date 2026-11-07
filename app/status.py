from typing import List, Dict, Any

def calculate_status(findings: List[Dict[str, Any]], fallback_used: bool = False) -> str:
    """
    Calculates submission status based on findings:
    - 'blocked': any unresolved high-severity finding with valid evidence.
    - 'needs_review': invalid evidence, needs_human, low confidence, or AI fallback used.
    - 'ready_for_approval': otherwise.
    """
    has_unresolved = False
    needs_review = fallback_used

    for f in findings:
        decision = str(f.get("decision", "pending")).lower()
        if decision in ("accept", "edit"):
            continue  # This finding is resolved
            
        has_unresolved = True
        severity = str(f.get("severity", "")).lower()
        evidence_valid = bool(f.get("evidence_valid", True))
        needs_human = bool(f.get("needs_human", False))
        confidence = float(f.get("confidence", 1.0))

        if severity == "high" and evidence_valid:
            return "blocked"
            
        if not evidence_valid or needs_human or confidence < 0.75:
            needs_review = True

    if needs_review or has_unresolved:
        return "needs_review"
        
    return "ready_for_approval"
