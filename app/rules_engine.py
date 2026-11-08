# app/rules_engine.py
"""
Deterministic rules engine for Mohar (AstraPay demo workspace).
Checks:
- TM-001: Brand spelling ("AstraPay" only, never "Astra Pay" or "ASTRAPAY")
- TM-002: Preferred terms ("customers" not "users"; "UPI Lite wallet" not "mini wallet")
- TM-003: Banned words ("free money", "guaranteed loan", "cheat", "instant rich")
- TN-001: Slang ("bro", "lit", "gonna") and ALL CAPS shouting
- TN-002: At most one exclamation mark per post
- CL-001: Guaranteed, assured, or risk-free returns claims
- CL-002: Unsubstantiated superlatives ("best", "No.1", "fastest") without source
- CL-003: Offer posts must include validity period and "T&C apply"
- DS-001: Investment posts must include "Investments are subject to market risks."
- FC-001: Deterministic fee/limit/rate number checks against AstraPay facts
- FC-002 / Expired facts: Checks expired facts (e.g. F-004 Diwali Dhamaka) by date
"""

from __future__ import annotations

import re
from app.fact_checks import run_fact_checks, check_superlatives
from datetime import date, datetime
from typing import Any, Dict, List, Optional

# Default seed rules (used if DB rules are not passed in)
DEFAULT_RULES: List[Dict[str, Any]] = [
    {"id": "CL-001", "category": "unsupported_claim", "text": "Never promise guaranteed, assured or risk-free returns", "severity": "high", "version": 1, "is_mandatory": True},
    {"id": "CL-002", "category": "unsupported_claim", "text": 'Superlatives ("best", "No.1", "fastest") need an approved source', "severity": "medium", "version": 1, "is_mandatory": False},
    {"id": "CL-003", "category": "disclaimer", "text": 'Every offer must state its validity period and "T&C apply"', "severity": "medium", "version": 1, "is_mandatory": False},
    {"id": "TN-001", "category": "tone", "text": 'Formal but friendly tone; no slang ("bro", "lit", "gonna"), no ALL CAPS shouting', "severity": "low", "version": 1, "is_mandatory": False},
    {"id": "TN-002", "category": "tone", "text": "At most one exclamation mark per post", "severity": "low", "version": 1, "is_mandatory": False},
    {"id": "TM-001", "category": "terminology", "text": 'Write "AstraPay" (one word), never "Astra Pay" or "ASTRAPAY"', "severity": "low", "version": 1, "is_mandatory": False},
    {"id": "TM-002", "category": "terminology", "text": 'Say "customers" not "users"; say "UPI Lite wallet" not "mini wallet"', "severity": "low", "version": 1, "is_mandatory": False},
    {"id": "TM-003", "category": "terminology", "text": 'Banned words: "free money", "guaranteed loan", "cheat", "instant rich"', "severity": "high", "version": 1, "is_mandatory": True},
    {"id": "FC-001", "category": "fact_error", "text": "Fees, limits and rates must match the approved fact ledger", "severity": "high", "version": 1, "is_mandatory": True},
    {"id": "FC-002", "category": "expired_fact", "text": "Expired offers must not be advertised", "severity": "high", "version": 1, "is_mandatory": True},
    {"id": "DS-001", "category": "disclaimer", "text": 'Investment-related posts must include "Investments are subject to market risks."', "severity": "high", "version": 1, "is_mandatory": True},
    {"id": "AC-001", "category": "accessibility", "text": "Every image must have alt text", "severity": "medium", "version": 1, "is_mandatory": False},
]

# Default seed facts (used if DB facts are not passed in)
DEFAULT_FACTS: List[Dict[str, Any]] = [
    {"id": "F-001", "approved_text": "UPI transfers on AstraPay have zero fees.", "source": "Product Policy v2", "owner": "Payments Team", "valid_from": "2025-01-01", "expires_on": None, "status": "active"},
    {"id": "F-002", "approved_text": "Daily UPI transfer limit is Rs. 1,00,000.", "source": "NPCI & AstraPay Policy", "owner": "Compliance", "valid_from": "2025-01-01", "expires_on": None, "status": "active"},
    {"id": "F-003", "approved_text": "AstraPay Rewards: cashback up to Rs. 100 on first bill payment.", "source": "Marketing Campaign Q4", "owner": "Growth Team", "valid_from": "2026-01-01", "expires_on": "2026-11-30", "status": "active"},
    {"id": "F-004", "approved_text": '"Diwali Dhamaka" cashback offer.', "source": "Festive Promo 2025", "owner": "Growth Team", "valid_from": "2025-10-01", "expires_on": "2025-11-15", "status": "expired"},
    {"id": "F-005", "approved_text": "Merchant fee is 0% for new merchants.", "source": "Merchant Tariff 2026", "owner": "Merchant Team", "valid_from": "2026-01-01", "expires_on": "2026-12-31", "status": "active"},
    {"id": "F-006", "approved_text": "Customer support is available 8 AM to 10 PM IST.", "source": "Support SLA", "owner": "Support Ops", "valid_from": "2025-01-01", "expires_on": None, "status": "active"},
    {"id": "F-007", "approved_text": "AstraPay Card annual fee is Rs. 499.", "source": "Card MITC", "owner": "Cards Team", "valid_from": "2025-01-01", "expires_on": None, "status": "active"},
    {"id": "F-008", "approved_text": "AstraPay Savings interest rate is 6.5% p.a. (subject to change).", "source": "Treasury Rate Sheet", "owner": "Banking Team", "valid_from": "2026-01-01", "expires_on": "2026-12-31", "status": "active"},
    {"id": "F-009", "approved_text": "UPI Lite wallet limit is Rs. 10,000.", "source": "UPI Lite Product Spec", "owner": "Payments Team", "valid_from": "2025-01-01", "expires_on": None, "status": "active"},
    {"id": "F-010", "approved_text": "AstraPay is a fictional demo brand used for testing.", "source": "Mohar Demo Spec", "owner": "Mohar Team", "valid_from": "2026-01-01", "expires_on": None, "status": "active"},
]

# Allowed uppercase acronyms so we do not false-flag normal financial terms under TN-001
ALLOWED_ACRONYMS = {
    "UPI", "IST", "INR", "KYC", "OTP", "PIN", "EMI", "PDF", "SMS",
    "URL", "API", "FAQ", "GST", "RBI", "NPCI", "NEFT", "RTGS", "IMPS",
    "PAN", "ATM", "BHIM", "QR", "ASTRAPAY", "FREE",
}


def _make_finding(
    category: str,
    severity: str,
    excerpt: str,
    rule_or_fact_id: str,
    explanation: str,
    fix_1: str,
    fix_2: str,
) -> Dict[str, Any]:
    """Helper to build a deterministic finding in the exact required JSON shape."""
    return {
        "category": category,
        "severity": severity,
        "confidence": 1.0,
        "excerpt": excerpt,
        "rule_or_fact_id": rule_or_fact_id,
        "explanation": explanation,
        "fix_1": fix_1,
        "fix_2": fix_2,
        "needs_human": False,
        "evidence_valid": True,
    }


def _find_sentence_containing(text: str, match_span: tuple[int, int]) -> str:
    """Returns the sentence or clause containing the character span (start, end)."""
    start, end = match_span
    # Split boundaries on sentence punctuation or newlines
    left_bound = 0
    for idx in range(start - 1, -1, -1):
        if text[idx] in ".!?\n":
            left_bound = idx + 1
            break
    right_bound = len(text)
    for idx in range(end, len(text)):
        if text[idx] in ".!?\n":
            right_bound = idx + 1
            break
    sentence = text[left_bound:right_bound].strip()
    return sentence if sentence else text[start:end]


def _parse_date(date_val: Any) -> Optional[date]:
    """Parses ISO dates ('2025-11-15') or human dates ('15 Nov 2025', 'EXPIRED 15 Nov 2025')."""
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val

    raw = str(date_val).strip()
    if not raw or raw.lower() == "none":
        return None

    # Strip leading 'EXPIRED' prefix if present
    cleaned = re.sub(r"(?i)^expired\s*", "", raw).strip()

    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _is_fact_expired(fact: Dict[str, Any], ref_date: date) -> bool:
    """Checks whether a fact record is expired relative to ref_date."""
    status = str(fact.get("status", "")).lower()
    expires_raw = str(fact.get("expires_on", "") or "")
    if status == "expired" or "expired" in expires_raw.lower():
        return True
    exp_date = _parse_date(fact.get("expires_on"))
    if exp_date and exp_date < ref_date:
        return True
    return False


def run_rules_engine(
    text: str,
    rules: Optional[List[Dict[str, Any]]] = None,
    facts: Optional[List[Dict[str, Any]]] = None,
    reference_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Runs all deterministic checks on `text` and returns a list of FINDING dicts
    with confidence=1.0 and evidence_valid=True.
    """
    if not text or not text.strip():
        return []

    active_facts = facts if facts is not None else DEFAULT_FACTS
    today = reference_date or date.today()
    findings: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 1. TM-001: Brand spelling ("AstraPay" one word, never "Astra Pay" or "ASTRAPAY")
    # -------------------------------------------------------------------------
    for match in re.finditer(r"Astra\s+Pay|ASTRAPAY", text, flags=re.IGNORECASE):
        excerpt = match.group(0)
        # Only flag if it is not literally "AstraPay"
        if excerpt != "AstraPay":
            findings.append(
                _make_finding(
                    category="terminology",
                    severity="low",
                    excerpt=excerpt,
                    rule_or_fact_id="TM-001",
                    explanation='Brand name must always be written as "AstraPay" (one word, camelCase), never with a space or in ALL CAPS.',
                    fix_1="AstraPay",
                    fix_2="the AstraPay app",
                )
            )

    # -------------------------------------------------------------------------
    # 2. TM-002: "customers" not "users"; "UPI Lite wallet" not "mini wallet"
    # -------------------------------------------------------------------------
    for match in re.finditer(r"\busers?\b", text, flags=re.IGNORECASE):
        excerpt = match.group(0)
        is_plural = excerpt.lower().endswith("s")
        replacement = "customers" if is_plural else "customer"
        if excerpt[0].isupper():
            replacement = replacement.capitalize()
        findings.append(
            _make_finding(
                category="terminology",
                severity="low",
                excerpt=excerpt,
                rule_or_fact_id="TM-002",
                explanation=f'AstraPay terminology requires saying "{replacement}" instead of "{excerpt}".',
                fix_1=replacement,
                fix_2=f"AstraPay {replacement.lower()}",
            )
        )

    for match in re.finditer(r"\bmini[\s-]wallets?\b", text, flags=re.IGNORECASE):
        excerpt = match.group(0)
        findings.append(
            _make_finding(
                category="terminology",
                severity="low",
                excerpt=excerpt,
                rule_or_fact_id="TM-002",
                explanation='Use the approved product term "UPI Lite wallet" instead of "mini wallet".',
                fix_1="UPI Lite wallet",
                fix_2="AstraPay UPI Lite wallet",
            )
        )

    # -------------------------------------------------------------------------
    # 3. TM-003: Banned words ("free money", "guaranteed loan", "cheat", "instant rich")
    # -------------------------------------------------------------------------
    banned_map = {
        r"\bfree\s+money\b": ("cashback rewards", "promotional benefits"),
        r"\bguaranteed\s+loans?\b": ("quick loan eligibility check", "streamlined loan application"),
        r"\bcheats?\b": ("smart tips", "helpful features"),
        r"\binstant\s+rich\b": ("long-term savings habits", "disciplined financial planning"),
    }
    for pattern, (fix1, fix2) in banned_map.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            excerpt = match.group(0)
            findings.append(
                _make_finding(
                    category="terminology",
                    severity="high",
                    excerpt=excerpt,
                    rule_or_fact_id="TM-003",
                    explanation=f'"{excerpt}" is a strictly banned phrase under AstraPay brand policy.',
                    fix_1=fix1,
                    fix_2=fix2,
                )
            )

    # -------------------------------------------------------------------------
    # 4. TN-001: Slang ("bro", "lit", "gonna") and ALL CAPS shouting
    # -------------------------------------------------------------------------
    slang_map = {
        r"\bbro\b": ("everyone", "friends"),
        r"\blit\b": ("great", "exciting"),
        r"\bgonna\b": ("going to", "set to"),
    }
    for pattern, (fix1, fix2) in slang_map.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            excerpt = match.group(0)
            findings.append(
                _make_finding(
                    category="tone",
                    severity="low",
                    excerpt=excerpt,
                    rule_or_fact_id="TN-001",
                    explanation=f'Slang term "{excerpt}" violates AstraPay\'s formal-but-friendly tone guideline.',
                    fix_1=fix1,
                    fix_2=fix2,
                )
            )

    # Check for ALL CAPS shouting (words of 4+ uppercase letters not in ALLOWED_ACRONYMS)
    for match in re.finditer(r"\b[A-Z]{4,}(?:\s+[A-Z]{2,})*\b", text):
        excerpt = match.group(0)
        words_in_match = excerpt.split()
        if all(w in ALLOWED_ACRONYMS for w in words_in_match):
            continue
        findings.append(
            _make_finding(
                category="tone",
                severity="low",
                excerpt=excerpt,
                rule_or_fact_id="TN-001",
                explanation="Avoid ALL CAPS shouting; keep the tone formal and friendly.",
                fix_1=excerpt.lower(),
                fix_2=excerpt.capitalize(),
            )
        )

    # -------------------------------------------------------------------------
    # 5. TN-002: At most one exclamation mark per post
    # -------------------------------------------------------------------------
    exclamation_count = text.count("!")
    if exclamation_count > 1:
        multi_bang = re.search(r"!{2,}", text)
        if multi_bang:
            sentence_excerpt = _find_sentence_containing(text, multi_bang.span())
            cleaned_once = re.sub(r"!{2,}", "!", sentence_excerpt)
            cleaned_period = re.sub(r"!+", ".", sentence_excerpt)
        else:
            sentence_excerpt = text.strip()
            # Keep only the first exclamation mark, turn the rest into periods
            parts = sentence_excerpt.split("!")
            cleaned_once = parts[0] + "!" + ".".join(parts[1:])
            cleaned_period = sentence_excerpt.replace("!", ".")

        findings.append(
            _make_finding(
                category="tone",
                severity="low",
                excerpt=sentence_excerpt,
                rule_or_fact_id="TN-002",
                explanation=f"Post contains {exclamation_count} exclamation marks; AstraPay allows at most one per post.",
                fix_1=cleaned_once,
                fix_2=cleaned_period,
            )
        )

    # -------------------------------------------------------------------------
    # 6. CL-001: Never promise guaranteed, assured or risk-free returns
    # -------------------------------------------------------------------------
    cl001_patterns = [
        r"\b(?:guaranteed|assured|risk[\s-]?free|100%\s+safe)\s+(?:returns?|profits?|income|interest|gains?|wealth)\b",
        r"\b(?:returns?|profits?|interest|gains?)\s+(?:are\s+|is\s+)?(?:100%\s+)?(?:guaranteed|assured|risk[\s-]?free)\b",
        r"\b(?:guaranteed|assured|risk[\s-]?free)\s+\d+(?:\.\d+)?%\s*(?:returns?|interest|p\.a\.)?\b",
    ]
    seen_cl001_spans: List[tuple[int, int]] = []
    for pat in cl001_patterns:
        for match in re.finditer(pat, text, flags=re.IGNORECASE):
            span = match.span()
            if any( not (span[1] <= s[0] or span[0] >= s[1]) for s in seen_cl001_spans ):
                continue
            seen_cl001_spans.append(span)
            excerpt = _find_sentence_containing(text, span)
            fix_a = re.sub(
                r"\b(guaranteed|assured|risk[\s-]?free|100%\s+safe)\s+",
                "",
                excerpt,
                flags=re.IGNORECASE,
            )
            findings.append(
                _make_finding(
                    category="unsupported_claim",
                    severity="high",
                    excerpt=excerpt,
                    rule_or_fact_id="CL-001",
                    explanation="Financial communications must never promise guaranteed, assured, or risk-free returns.",
                    fix_1=fix_a.strip(),
                    fix_2="Earn competitive returns with AstraPay Savings (rates subject to change).",
                )
            )

    # -------------------------------------------------------------------------
    # 7. CL-003: Every offer must state its validity period and "T&C apply"
    # -------------------------------------------------------------------------
    offer_match = re.search(
        r"\b(offer|cashback|discount|reward|rewards|promo|deal|voucher|bonus)\b",
        text,
        flags=re.IGNORECASE,
    )
    if offer_match:
        has_tnc = bool(
            re.search(r"\b(t\s*&\s*c(\s+apply)?|terms\s+and\s+conditions(\s+apply)?)\b", text, flags=re.IGNORECASE)
        )
        has_validity = bool(
            re.search(
                r"\b(valid\s+(till|until|up\s+to|through)|expires?\s+on|offer\s+ends|till\s+\d{1,2}\s+[A-Za-z]+|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
                text,
                flags=re.IGNORECASE,
            )
        )
        if not (has_tnc and has_validity):
            excerpt = _find_sentence_containing(text, offer_match.span())
            missing_parts = []
            if not has_validity:
                missing_parts.append("a validity date/period")
            if not has_tnc:
                missing_parts.append('"T&C apply"')
            missing_str = " and ".join(missing_parts)

            base_sentence = excerpt.rstrip(".!")
            findings.append(
                _make_finding(
                    category="disclaimer",
                    severity="medium",
                    excerpt=excerpt,
                    rule_or_fact_id="CL-003",
                    explanation=f"This promotional offer is missing {missing_str}.",
                    fix_1=f"{base_sentence}. Valid till 30 Nov 2026. T&C apply.",
                    fix_2=f"{base_sentence} (Offer valid till 30 Nov 2026; T&C apply).",
                )
            )

       # -------------------------------------------------------------------------
    # 8. DS-001: Investment posts must include "Investments are subject to market risks."
    #    Strong signals (invest*, mutual fund, portfolio, SIP...) always trigger.
    #    Weak words ("return(s)", "wealth") trigger ONLY together with a financial
    #    signal (%, p.a., interest, savings, Rs./₹). This stops false positives such as
    #    "you could return to Earth" in a physics post.
    # -------------------------------------------------------------------------
    strong_invest = re.search(
        r"\b(invest(?:ing|ment|ments|or|ors|ed|s)?|mutual\s+funds?|portfolio|stock\s+market|equity|equities)\b",
        text,
        flags=re.IGNORECASE,
    ) or re.search(r"\bSIPs?\b", text)  # case-sensitive, so "sip of tea" never matches
    invest_match = strong_invest
    if invest_match is None:
        weak = re.search(r"\b(wealth|returns?)\b", text, flags=re.IGNORECASE)
        has_fin_signal = re.search(
            r"%|p\.a\.|\binterest\b|\bsavings?\b|\bdeposits?\b|\bRs\.?\s*\d|₹",
            text,
            flags=re.IGNORECASE,
        )
        if weak and has_fin_signal:
            invest_match = weak
    if invest_match:
        has_disclaimer = "investments are subject to market risks" in text.lower()
        if not has_disclaimer:
            excerpt = _find_sentence_containing(text, invest_match.span())
            base_excerpt = excerpt.rstrip()
            if not base_excerpt.endswith((".", "!", "?")):
                base_excerpt += "."
            findings.append(
                _make_finding(
                    category="disclaimer",
                    severity="high",
                    excerpt=excerpt,
                    rule_or_fact_id="DS-001",
                    explanation='Investment-related content must include the mandatory disclaimer: "Investments are subject to market risks."',
                    fix_1=f"{base_excerpt} Investments are subject to market risks.",
                    fix_2=f"{base_excerpt} Please note: Investments are subject to market risks.",
                )
            )

    # -------------------------------------------------------------------------
    # 9. FC-002 / Expired facts by date (e.g. F-004 "Diwali Dhamaka" expired 15 Nov 2025)
    # -------------------------------------------------------------------------
    for fact in active_facts:
        if not _is_fact_expired(fact, today):
            continue

        fact_id = fact.get("id", "FC-002")
        approved_text = fact.get("approved_text", "")
        expires_on = fact.get("expires_on", "in the past")

        # Extract quoted campaign name (e.g. "Diwali Dhamaka") or fallback phrase
        quoted_names = re.findall(r'"([^"]+)"', approved_text)
        search_terms = quoted_names if quoted_names else [approved_text]

        for term in search_terms:
            if not term:
                continue
            term_match = re.search(re.escape(term), text, flags=re.IGNORECASE)
            if term_match:
                excerpt = _find_sentence_containing(text, term_match.span())
                findings.append(
                    _make_finding(
                        category="expired_fact",
                        severity="high",
                        excerpt=excerpt,
                        rule_or_fact_id=fact_id,
                        explanation=f'The "{term}" offer ({fact_id}) expired on {expires_on} and violates rule FC-002 (Expired offers must not be advertised).',
                        fix_1="Enjoy AstraPay Rewards: get cashback up to Rs. 100 on your first bill payment. Valid till 30 Nov 2026. T&C apply.",
                        fix_2="Pay bills seamlessly on AstraPay with zero UPI transfer fees.",
                    )
                )

    # -------------------------------------------------------------------------
    # 10. Backup checks that work without Gemini: FC-001 numbers vs approved facts,
    #     and CL-002 superlatives (see app/fact_checks.py)
    # -------------------------------------------------------------------------
    findings.extend(run_fact_checks(text, active_facts))
    if rules is None or any(str(r.get("id", "")).upper() == "CL-002" for r in rules):
        findings.extend(check_superlatives(text))

    return findings
