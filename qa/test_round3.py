"""Round 3 tests: real sign-in roles, fact lifecycle, expiry alerts, visual checker.
Run from the repo root:   python -m pytest -q qa/test_round3.py
Uses an in-memory fake database; never touches Supabase or Gemini.
"""
import io
import itertools
import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy")

import app.main as main                       # noqa: E402
from app import facts_lifecycle as fl, visual  # noqa: E402
from fastapi.testclient import TestClient     # noqa: E402
from PIL import Image, ImageDraw              # noqa: E402

_ip = itertools.count(100)
TODAY = date.today()
USERS = {
    "tok-creator":  ("u-creator", "creator@mohar-demo.app", "creator"),
    "tok-creator2": ("u-creator2", "other@mohar-demo.app", "creator"),
    "tok-manager":  ("u-manager", "manager@mohar-demo.app", "manager"),
    "tok-reviewer": ("u-reviewer", "reviewer@mohar-demo.app", "reviewer"),
}


class Q:
    def __init__(s, rows): s.rows, s.f, s.mode, s.p = rows, [], "select", None
    def select(s, *a): s.mode = "select"; return s
    def eq(s, c, v): s.f.append((c, v)); return s
    def in_(s, c, vals): s.f.append((c, set(vals))); return s
    def order(s, *a, **k): return s
    def update(s, p): s.mode, s.p = "update", p; return s
    def insert(s, p): s.mode, s.p = "insert", p; return s
    def upsert(s, p): s.mode, s.p = "insert", p; return s
    def execute(s):
        ok = lambda r: all((r.get(c) in v) if isinstance(v, set) else r.get(c) == v for c, v in s.f)
        match = [r for r in s.rows if ok(r)]
        if s.mode == "update": [r.update(s.p) for r in match]
        if s.mode == "insert": s.rows.append(dict(s.p))
        return type("R", (), {"data": [dict(m) for m in match]})()


class FakeAuth:
    def get_user(self, token):
        if token not in USERS:
            raise RuntimeError("bad token")
        return type("R", (), {"user": type("U", (), {"id": USERS[token][0], "email": USERS[token][1]})()})()


class DB:
    def __init__(s):
        s.t, s.auth = {}, FakeAuth()
        s.t["user_roles"] = [{"user_id": u, "role": r} for u, _, r in USERS.values()]
    def table(s, n): return Q(s.t.setdefault(n, []))


def _png(bg, fg):
    im = Image.new("RGB", (400, 300), bg)
    ImageDraw.Draw(im).rectangle([40, 100, 360, 160], fill=fg)
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


@pytest.fixture()
def client(monkeypatch):
    db = DB()
    db.t["rules"] = [{"id": i, "category": "accessibility", "text": t, "severity": "medium"} for i, t in
                     [("AC-001", "alt text"), ("AC-002", "good alt"), ("AC-003", "contrast"), ("VC-001", "brand colours")]]
    db.t["facts"] = [
        {"id": "F-002", "approved_text": "Daily UPI transfer limit is Rs. 1,00,000.", "source": "s", "owner": "o",
         "valid_from": "2025-01-01", "expires_on": None, "status": "active", "version": 1},
        {"id": "F-003", "approved_text": "AstraPay Rewards: cashback up to Rs. 100 on first bill payment.", "source": "s",
         "owner": "o", "valid_from": "2026-01-01", "expires_on": (TODAY + timedelta(days=12)).isoformat(),
         "status": "active", "version": 1},
    ]
    db.t["submissions"] = [
        {"id": "s-own", "title": "mine", "channel": "social", "audience": "general", "creator": "c",
         "creator_id": "u-creator", "status": "ready_for_approval", "current_version": 1},
        {"id": "s-other", "title": "theirs", "channel": "social", "audience": "general", "creator": "o",
         "creator_id": "u-creator2", "status": "approved", "current_version": 1},
    ]
    db.t["versions"] = [
        {"id": "v1", "submission_id": "s-own", "version_no": 1, "body": "hello world"},
        {"id": "v2", "submission_id": "s-other", "version_no": 1, "body": "Get cashback up to Rs. 100 on your first bill."},
    ]
    monkeypatch.setattr(main, "get_db", lambda: db)
    monkeypatch.setattr(main, "run_review_pipeline", lambda **k: {"findings": [], "fallback_used": False})
    monkeypatch.setattr(main, "REQUIRE_AUTH", True)
    main._TOKEN_CACHE.clear()
    c = TestClient(main.app, headers={"x-forwarded-for": f"10.1.0.{next(_ip)}"})
    c.db = db
    return c


def H(tok): return {"Authorization": f"Bearer {tok}"}
def approve(c, tok, sub="s-own"):
    return c.post(f"/api/submissions/{sub}/approval", headers=H(tok), json={"decision": "approve", "comment": "ok"})


# ---- Sign-in and roles ------------------------------------------------------
def test_no_token_is_refused_everywhere(client):
    assert client.get("/api/submissions").status_code == 401
    assert approve(client, None) .status_code == 401
    assert client.post("/api/submissions", json={"title": "t", "text": "hello there", "channel": "social", "audience": "general"}).status_code == 401


def test_bad_token_is_refused(client):
    assert client.get("/api/submissions", headers=H("nope")).status_code == 401


def test_creator_cannot_approve_manager_can(client):
    assert approve(client, "tok-creator").status_code == 403
    assert approve(client, "tok-reviewer").status_code == 403
    assert approve(client, "tok-manager").status_code == 200


def test_audit_entry_names_the_real_user(client):
    approve(client, "tok-manager")
    row = [r for r in client.db.t["audit_log"] if r["action"].startswith("approve")][0]
    assert row["actor_email"] == "manager@mohar-demo.app" and row["actor_id"] == "u-manager"


def test_role_in_request_body_cannot_override_token(client):
    r = client.post("/api/submissions/s-own/approval", headers=H("tok-creator"),
                    json={"role": "Manager", "decision": "approve"})
    assert r.status_code == 403


def test_only_creators_submit(client):
    body = {"title": "t", "text": "A fine post for customers.", "channel": "social", "audience": "general"}
    assert client.post("/api/submissions", headers=H("tok-manager"), json=body).status_code == 403
    r = client.post("/api/submissions", headers=H("tok-creator"), json=body)
    assert r.status_code == 200
    saved = [s for s in client.db.t["submissions"] if s["id"] == r.json()["submission_id"]][0]
    assert saved["creator_id"] == "u-creator" and saved["creator"] == "creator@mohar-demo.app"


def test_creators_only_see_their_own_posts(client):
    ids = {s["id"] for s in client.get("/api/submissions", headers=H("tok-creator")).json()}
    assert ids == {"s-own"}
    assert {s["id"] for s in client.get("/api/submissions", headers=H("tok-manager")).json()} == {"s-own", "s-other"}
    assert client.get("/api/submissions/s-other", headers=H("tok-creator")).status_code == 403
    assert client.get("/api/submissions/s-other", headers=H("tok-manager")).status_code == 200


def test_demo_login_returns_role(client, monkeypatch):
    monkeypatch.setattr(main.auth_service, "demo_sign_in",
                        lambda role: {"access_token": "tok-manager", "expires_in": 3600, "user_id": "u-manager", "email": "manager@mohar-demo.app"})
    r = client.post("/api/auth/demo", json={"role": "Manager"})
    assert r.status_code == 200 and r.json()["role"] == "Manager" and r.json()["access_token"] == "tok-manager"
    assert client.post("/api/auth/demo", json={"role": "Boss"}).status_code == 422


def test_login_wrong_password_is_401(client, monkeypatch):
    def boom(e, p): raise main.auth_service.AuthError("Wrong email or password.")
    monkeypatch.setattr(main.auth_service, "sign_in_password", boom)
    assert client.post("/api/auth/login", json={"email": "a@b.c", "password": "x"}).status_code == 401


def test_login_is_rate_limited(client, monkeypatch):
    def boom(e, p): raise main.auth_service.AuthError("Wrong email or password.")
    monkeypatch.setattr(main.auth_service, "sign_in_password", boom)
    codes = [client.post("/api/auth/login", json={"email": "a@b.c", "password": "x"}).status_code for _ in range(12)]
    assert codes[:10] == [401] * 10 and 429 in codes[10:]


# ---- Reviewer workspace / fact lifecycle -------------------------------------
def test_only_reviewers_edit_facts(client):
    body = {"approved_text": "Daily UPI transfer limit is Rs. 1,50,000.", "change_note": "NPCI update"}
    assert client.put("/api/facts/F-002", headers=H("tok-creator"), json=body).status_code == 403
    assert client.put("/api/facts/F-002", headers=H("tok-manager"), json=body).status_code == 403
    assert client.put("/api/facts/F-002", headers=H("tok-reviewer"), json=body).status_code == 200


def test_old_fact_version_is_kept(client):
    client.put("/api/facts/F-002", headers=H("tok-reviewer"),
               json={"approved_text": "Daily UPI transfer limit is Rs. 1,50,000.", "change_note": "NPCI update"})
    cur = [f for f in client.db.t["facts"] if f["id"] == "F-002"][0]
    assert cur["version"] == 2 and "1,50,000" in cur["approved_text"] and cur["updated_by"] == "reviewer@mohar-demo.app"
    old = client.db.t["fact_versions"][0]
    assert old["version"] == 1 and "1,00,000" in old["approved_text"] and old["change_note"] == "NPCI update"
    hist = client.get("/api/facts/F-002/versions", headers=H("tok-reviewer")).json()
    assert hist["current"]["version"] == 2 and len(hist["history"]) == 1


def test_expiry_date_can_be_set_and_cleared(client):
    r = client.put("/api/facts/F-002", headers=H("tok-reviewer"), json={"expires_on": "2027-03-31"})
    assert r.status_code == 200
    assert [f for f in client.db.t["facts"] if f["id"] == "F-002"][0]["expires_on"] == "2027-03-31"
    client.put("/api/facts/F-002", headers=H("tok-reviewer"), json={"clear_expiry": True})
    assert [f for f in client.db.t["facts"] if f["id"] == "F-002"][0]["expires_on"] is None


def test_expiry_before_start_is_rejected(client):
    r = client.put("/api/facts/F-002", headers=H("tok-reviewer"), json={"expires_on": "2024-01-01"})
    assert r.status_code == 400
    assert client.put("/api/facts/F-002", headers=H("tok-reviewer"), json={"expires_on": "tomorrow"}).status_code == 422


def test_conflicting_fact_shows_a_warning(client):
    r = client.post("/api/facts", headers=H("tok-reviewer"), json={
        "id": "F-050", "approved_text": "Daily UPI transfer limit is Rs. 2,00,000.", "source": "s", "owner": "o",
        "valid_from": "2026-01-01"})
    assert r.status_code == 200 and r.json()["warnings"] and "F-002" in r.json()["warnings"][0]
    assert client.get("/api/facts/conflicts", headers=H("tok-reviewer")).json()["conflicts"]


def test_unrelated_fact_has_no_warning(client):
    r = client.post("/api/facts", headers=H("tok-reviewer"), json={
        "id": "F-051", "approved_text": "Customer support is available 8 AM to 10 PM IST.", "source": "s", "owner": "o"})
    assert r.json()["warnings"] == []


# ---- Expiry alerts -----------------------------------------------------------
def test_expiry_alert_lists_fact_and_dependent_approved_post(client):
    data = client.get("/api/alerts/expiring", headers=H("tok-manager")).json()
    alert = [a for a in data["alerts"] if a["fact_id"] == "F-003"][0]
    assert alert["state"] == "expiring" and alert["days_left"] == 12
    assert [p["id"] for p in alert["dependent_posts"]] == ["s-other"]
    assert all(a["fact_id"] != "F-002" for a in data["alerts"])


def test_lifecycle_states():
    t = date(2026, 11, 10)
    assert fl.fact_state({"expires_on": "2026-11-30", "status": "active"}, t) == "expiring"
    assert fl.fact_state({"expires_on": "2026-09-01", "status": "active"}, t) == "expired"
    assert fl.fact_state({"expires_on": None, "status": "active"}, t) == "active"
    assert fl.fact_state({"expires_on": None, "status": "expired"}, t) == "expired"


def test_figure_matching_is_exact():
    fact = {"id": "F-003", "approved_text": "cashback up to Rs. 100"}
    posts = [{"id": "a", "title": "a", "body": "Pay Rs. 1,00,000 daily"}, {"id": "b", "title": "b", "body": "Cashback Rs. 100 today"}]
    assert [p["id"] for p in fl.find_dependents(fact, posts)] == ["b"]


# ---- Visual checker ----------------------------------------------------------
def test_visual_missing_alt_and_low_contrast_flagged(client):
    r = client.post("/api/visual-review", headers=H("tok-creator"),
                    files={"file": ("poster.png", _png("#CDEFE1", "#BFE3D4"), "image/png")}, data={"alt_text": "", "title": "Poster"})
    assert r.status_code == 200
    ids = {f["rule_or_fact_id"] for f in r.json()["findings"]}
    assert {"AC-001", "AC-003"} <= ids
    assert all(f["evidence_valid"] for f in r.json()["findings"])
    assert all(f["fix_1"] and f["fix_2"] for f in r.json()["findings"])


def test_visual_good_image_is_clean(client):
    r = client.post("/api/visual-review", headers=H("tok-creator"),
                    files={"file": ("p.png", _png("#0B6E4F", "#FFFFFF"), "image/png")},
                    data={"alt_text": "AstraPay app screen confirming a UPI payment", "title": "Good"})
    assert r.status_code == 200 and r.json()["findings"] == [] and r.json()["status"] == "ready_for_approval"


def test_visual_off_brand_colour_flagged(client):
    r = client.post("/api/visual-review", headers=H("tok-creator"),
                    files={"file": ("p.png", _png("#8A2BE2", "#FFFFFF"), "image/png")},
                    data={"alt_text": "A purple promotional banner for AstraPay", "title": "Purple"})
    assert "VC-001" in {f["rule_or_fact_id"] for f in r.json()["findings"]}


def test_visual_rule_missing_from_db_needs_human(client):
    client.db.t["rules"] = []
    r = client.post("/api/visual-review", headers=H("tok-creator"),
                    files={"file": ("p.png", _png("#0B6E4F", "#FFFFFF"), "image/png")}, data={"alt_text": ""})
    f = r.json()["findings"][0]
    assert f["evidence_valid"] is False and f["needs_human"] is True


def test_visual_rejects_non_images_and_non_creators(client):
    bad = client.post("/api/visual-review", headers=H("tok-creator"), files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 400
    ok = client.post("/api/visual-review", headers=H("tok-manager"), files={"file": ("p.png", _png("#fff", "#000"), "image/png")})
    assert ok.status_code == 403


def test_alt_text_quality():
    assert visual.check_alt_text("")["rule"] == "AC-001"
    assert visual.check_alt_text("image")["rule"] == "AC-002"
    assert visual.check_alt_text("IMG_2041.jpg")["rule"] == "AC-002"
    assert visual.check_alt_text("AstraPay card shown next to a phone") is None


def test_contrast_math():
    assert round(visual.contrast_ratio((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert visual.contrast_ratio((255, 255, 255), (255, 255, 255)) == 1.0
