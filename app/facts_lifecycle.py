"""Fact lifecycle helpers for Mohar (pure functions, no database access).

- expiry state / days left for a fact
- conflict detection between two facts that talk about the same thing
- finding which approved posts rely on a fact that is expiring or expired
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

EXPIRING_WINDOW_DAYS = 30
_STOP = {
    "the", "a", "an", "is", "are", "on", "of", "for", "to", "in", "and", "or", "up", "at",
    "by", "has", "have", "be", "with", "new", "all", "any", "our", "your", "from", "as",
    "subject", "change", "per", "astrapay",
}


def parse_date(value: Any) -> Optional[date]:
    """'2026-11-30' -> date. Returns None for empty or invalid input."""
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def days_left(fact: Dict[str, Any], today: date) -> Optional[int]:
    exp = parse_date(fact.get("expires_on"))
    return None if exp is None else (exp - today).days


def fact_state(fact: Dict[str, Any], today: date, window: int = EXPIRING_WINDOW_DAYS) -> str:
    """'expired' | 'expiring' | 'active' (explicit status 'expired' always wins)."""
    if str(fact.get("status", "")).lower() == "expired":
        return "expired"
    left = days_left(fact, today)
    if left is None:
        return "active"
    if left < 0:
        return "expired"
    if left <= window:
        return "expiring"
    return "active"


def _figures(text: str) -> List[str]:
    """Numbers and quoted phrases that identify what a fact is about."""
    out: List[str] = []
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?%?", text or ""):
        tok = m.group(0).rstrip(",.")
        digits = re.sub(r"\D", "", tok)
        if "%" in tok or len(digits) >= 3:
            out.append(tok)
    for m in re.finditer(r"[\"“']([^\"”']{4,60})[\"”']", text or ""):
        out.append(m.group(1).strip())
    seen, uniq = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return uniq


def _contains_figure(body: str, token: str) -> bool:
    if token[0].isdigit():
        pat = r"(?<![\d,.])" + re.escape(token) + r"(?![\d,]|\.\d)"
    else:
        pat = re.escape(token)
    return re.search(pat, body, flags=re.IGNORECASE) is not None


def find_dependents(fact: Dict[str, Any], posts: Iterable[Dict[str, Any]],
                    cited_ids: Optional[Dict[str, set]] = None) -> List[Dict[str, Any]]:
    """Approved posts that rely on `fact`: their text repeats one of the fact's
    figures (e.g. 'Rs. 100', '6.5%', a quoted offer name) or a finding cited the fact."""
    tokens = _figures(fact.get("approved_text", ""))
    fid = str(fact.get("id", ""))
    out = []
    for p in posts:
        body = p.get("body") or ""
        hit = [t for t in tokens if _contains_figure(body, t)]
        cited = bool(cited_ids and fid in cited_ids.get(p.get("id"), set()))
        if hit or cited:
            out.append({"id": p.get("id"), "title": p.get("title"),
                        "matched": hit[:3] if hit else [f"cited {fid}"]})
    return out


def expiry_alerts(facts: List[Dict[str, Any]], posts: List[Dict[str, Any]], today: date,
                  window: int = EXPIRING_WINDOW_DAYS,
                  cited_ids: Optional[Dict[str, set]] = None) -> List[Dict[str, Any]]:
    alerts = []
    for f in facts:
        state = fact_state(f, today, window)
        if state == "active":
            continue
        alerts.append({
            "fact_id": f.get("id"),
            "approved_text": f.get("approved_text"),
            "owner": f.get("owner"),
            "expires_on": f.get("expires_on"),
            "state": state,
            "days_left": days_left(f, today),
            "dependent_posts": find_dependents(f, posts, cited_ids),
        })
    alerts.sort(key=lambda a: (a["days_left"] is None, a["days_left"] if a["days_left"] is not None else 0))
    return alerts


def _words(text: str) -> set:
    ws = re.findall(r"[a-z]+", (text or "").lower())
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in ws if w not in _STOP and len(w) > 2}


def _window(f: Dict[str, Any]):
    start = parse_date(f.get("valid_from")) or date.min
    end = parse_date(f.get("expires_on")) or date.max
    return start, end


def _same_subject(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    ta, tb = (a.get("topic") or "").strip().lower(), (b.get("topic") or "").strip().lower()
    if ta and tb:
        return ta == tb
    wa, wb = _words(a.get("approved_text")), _words(b.get("approved_text"))
    shared = wa & wb
    return len(shared) >= 3 and len(shared) / max(1, len(wa | wb)) >= 0.6


def detect_conflicts(facts: List[Dict[str, Any]], today: Optional[date] = None,
                     only_for: Optional[str] = None) -> List[Dict[str, Any]]:
    """Two live facts about the same subject, valid at the same time, saying different things."""
    today = today or date.today()
    live = [f for f in facts if fact_state(f, today) != "expired"]
    out = []
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if only_for and only_for not in (a.get("id"), b.get("id")):
                continue
            if (a.get("approved_text") or "").strip().lower() == (b.get("approved_text") or "").strip().lower():
                continue
            (s1, e1), (s2, e2) = _window(a), _window(b)
            if s1 > e2 or s2 > e1:
                continue
            if _same_subject(a, b):
                out.append({
                    "fact_a": a.get("id"), "fact_b": b.get("id"),
                    "text_a": a.get("approved_text"), "text_b": b.get("approved_text"),
                    "message": f"{a.get('id')} and {b.get('id')} describe the same thing differently while both are valid.",
                })
    return out
