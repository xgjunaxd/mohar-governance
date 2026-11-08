"""Rule-based backup checks that do NOT need Gemini.

1) run_fact_checks : compares fees / limits / rates in a post with the approved
   fact ledger (FC-001) - e.g. "limit Rs. 5,00,000" vs approved "Rs. 1,00,000".
   It reads the numbers from the live facts passed in, so editing a fact in the
   database changes what is checked. A fact that does not exist is never checked.
2) check_superlatives : "best", "fastest", "No.1" ... need an approved source (CL-002).
"""
import re
from typing import Any, Dict, List, Optional, Tuple

AMOUNT_RE = re.compile(r"(?:\brs\.?|\binr|₹)\s*([\d][\d,]*(?:\.\d+)?)", re.IGNORECASE)
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
TIME_RE = re.compile(r"\b(\d{1,2})(?::\d{2})?\s*(am|pm)\b", re.IGNORECASE)
ZERO_WORDS = re.compile(r"\b(zero|no|nil|0|without|waived|free)\b", re.IGNORECASE)


def _finding(category, severity, excerpt, rule_or_fact_id, explanation, fix_1, fix_2):
    return {
        "category": category, "severity": severity, "confidence": 1.0, "excerpt": excerpt,
        "rule_or_fact_id": rule_or_fact_id, "explanation": explanation,
        "fix_1": fix_1, "fix_2": fix_2, "needs_human": False, "evidence_valid": True,
    }


def _sentences(text: str) -> List[Tuple[int, int]]:
    """(start, end) of each sentence in the ORIGINAL text. Does not split on
    'Rs.', 'p.a.', 'No.1' or decimals."""
    spans, start, n, i = [], 0, len(text), 0
    while i < n:
        ch = text[i]
        if ch == "\n":
            spans.append((start, i)); start = i + 1
        elif ch in "!?":
            j = i + 1
            while j < n and text[j] in "!?":
                j += 1
            spans.append((start, j)); start = j; i = j - 1
        elif ch == ".":
            abbrev = re.search(r"(?:\brs|\bno|\bp\.a|\bapprox|\bvs)$", text[:i].lower())
            nxt = text[i + 1:i + 2]
            if not abbrev and not nxt.isdigit() and (i + 1 >= n or nxt.isspace()):
                spans.append((start, i + 1)); start = i + 1
        i += 1
    spans.append((start, n))
    out = []
    for s, e in spans:
        seg = text[s:e]
        lead = len(seg) - len(seg.lstrip())
        seg = seg.strip()
        if seg:
            out.append((s + lead, s + lead + len(seg)))
    return out


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _fact_value(fact: Dict[str, Any], kind: str):
    """Returns (number, exact text such as 'Rs. 1,00,000' or '6.5%') from a fact."""
    t = str(fact.get("approved_text", ""))
    m = (AMOUNT_RE if kind == "amount" else PCT_RE).search(t)
    if not m:
        return None, None
    return _num(m.group(1)), m.group(0)


def _hours_24(sentence: str) -> List[int]:
    hrs = []
    for h, ap in TIME_RE.findall(sentence):
        h = int(h) % 12
        hrs.append(h + (12 if ap.lower() == "pm" else 0))
    return hrs


def run_fact_checks(text: str, facts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    by_id = {str(f.get("id", "")).upper(): f for f in (facts or [])}
    findings: List[Dict[str, Any]] = []

    def numeric(fid, kind, topic, sentence, low, text_, mode="ne"):
        fact = by_id.get(fid)
        if not fact or not topic(low):
            return
        approved, approved_txt = _fact_value(fact, kind)
        if approved is None:
            return
        found = [(_num(m.group(1)), m) for m in (AMOUNT_RE if kind == "amount" else PCT_RE).finditer(sentence)]
        if not found:
            return
        if mode == "gt":
            bad = [(v, m) for v, m in found if v > approved]
        else:
            bad = [] if any(abs(v - approved) < 1e-9 for v, _ in found) else found
        if not bad:
            return
        v, m = bad[0]
        fixed = sentence[:m.start()] + approved_txt + sentence[m.end():]
        findings.append(_finding(
            "fact_error", "high", sentence, fid,
            f'The post says "{m.group(0).strip()}", but the approved fact {fid} says: "{fact.get("approved_text")}" (rule FC-001: fees, limits and rates must match the approved fact ledger).',
            fixed, str(fact.get("approved_text", "")),
        ))

    for s, e in _sentences(text):
        sent = text[s:e]
        low = sent.lower()

        numeric("F-009", "amount", lambda l: "lite" in l and ("limit" in l or "up to" in l or "holds" in l or "wallet" in l), sent, low, text)
        numeric("F-002", "amount", lambda l: ("limit" in l or "daily" in l or "per day" in l) and "lite" not in l and ("upi" in l or "transfer" in l), sent, low, text)
        numeric("F-007", "amount", lambda l: "annual" in l and "fee" in l, sent, low, text)
        numeric("F-003", "amount", lambda l: "cashback" in l, sent, low, text, mode="gt")
        numeric("F-008", "pct", lambda l: "saving" in l and ("interest" in l or "rate" in l or "p.a" in l or "return" in l), sent, low, text)
        numeric("F-005", "pct", lambda l: "merchant" in l and "fee" in l, sent, low, text)

        # F-001: UPI transfers have zero fees
        f1 = by_id.get("F-001")
        if f1 and "transfer" in low and re.search(r"\b(fee|fees|charge|charges)\b", low) and not ZERO_WORDS.search(low):
            findings.append(_finding(
                "fact_error", "high", sent, "F-001",
                f'The post mentions a fee on transfers, but the approved fact F-001 says: "{f1.get("approved_text")}" (rule FC-001).',
                str(f1.get("approved_text", "")), "Enjoy zero-fee UPI transfers on AstraPay.",
            ))

        # F-006: support hours
        f6 = by_id.get("F-006")
        if f6 and "support" in low:
            around_clock = re.search(r"24\s*[x/*]\s*7|24\s*hours?|round[\s-]the[\s-]clock|all\s+day|anytime", low)
            hrs = _hours_24(sent)
            wrong_times = bool(hrs) and not (8 in hrs and 22 in hrs)
            if around_clock or wrong_times:
                findings.append(_finding(
                    "fact_error", "high", sent, "F-006",
                    f'The post gives different support hours, but the approved fact F-006 says: "{f6.get("approved_text")}" (rule FC-001).',
                    str(f6.get("approved_text", "")), "Our customer support team is available from 8 AM to 10 PM IST.",
                ))
    return findings


SUPERLATIVE_RE = re.compile(
    r"\b(best(?!\s+(?:wishes|regards|of\s+luck|practices?))|fastest|cheapest|safest|biggest|largest|"
    r"most\s+(?:trusted|secure|popular|reliable)|top[\s-]rated|number\s+(?:one|1)|no\.?\s*1)\b|\B#\s*1\b",
    re.IGNORECASE,
)
SOURCED_RE = re.compile(r"according\s+to|as\s+per|source\s*:|ranked|survey|award|\*", re.IGNORECASE)
_NEUTRAL = {"best": "great", "fastest": "fast", "cheapest": "affordable", "safest": "secure",
            "biggest": "large", "largest": "large"}


def check_superlatives(text: str) -> List[Dict[str, Any]]:
    findings = []
    for s, e in _sentences(text):
        sent = text[s:e]
        m = SUPERLATIVE_RE.search(sent)
        if not m or SOURCED_RE.search(sent):
            continue
        word = m.group(0)
        neutral = _NEUTRAL.get(word.lower(), "trusted")
        fix_1 = sent[:m.start()] + neutral + sent[m.end():]
        fix_2 = re.sub(r"\s{2,}", " ", (sent[:m.start()].rstrip() + " " + sent[m.end():].lstrip())).strip()
        findings.append(_finding(
            "unsupported_claim", "medium", sent, "CL-002",
            f'"{word}" is a superlative claim with no approved source (rule CL-002). Remove it or add an approved source.',
            fix_1, fix_2,
        ))
    return findings
