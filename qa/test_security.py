"""Security regression tests for the Mohar API.
Run from the repo root:   python -m pytest -q qa/test_security.py
Uses an in-memory fake database, so it never touches Supabase or Gemini.
"""
import os
import itertools
import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy")

import app.main as main                      # noqa: E402
from fastapi.testclient import TestClient    # noqa: E402

EVIL = "https://evil.example"
GOOD = "https://mohar-governance-snowy.vercel.app"
_ip = itertools.count(1)


class Q:
    def __init__(s, rows, boom=False):
        s.rows, s.f, s.mode, s.p, s.boom = rows, [], "select", None, boom
    def select(s, *a): s.mode = "select"; return s
    def eq(s, c, v): s.f.append((c, v)); return s
    def in_(s, c, vals): s.f.append((c, set(vals))); return s
    def order(s, *a, **k): return s
    def update(s, p): s.mode, s.p = "update", p; return s
    def insert(s, p): s.mode, s.p = "insert", p; return s
    def upsert(s, p): s.mode, s.p = "insert", p; return s
    def execute(s):
        if s.boom and s.mode == "insert":
            raise RuntimeError("SECRET-DB-DETAIL host=db.internal password=hunter2")
        ok = lambda r: all((r.get(c) in v) if isinstance(v, set) else r.get(c) == v for c, v in s.f)
        match = [r for r in s.rows if ok(r)]
        if s.mode == "update": [r.update(s.p) for r in match]
        if s.mode == "insert": s.rows.append(s.p)
        return type("R", (), {"data": match})()


class DB:
    def __init__(s, boom=False): s.t, s.boom = {}, boom
    def table(s, n): return Q(s.t.setdefault(n, []), s.boom)


@pytest.fixture()
def client(monkeypatch):
    db = DB()
    db.t["submissions"] = [{"id": "s1", "title": "t", "channel": "social", "audience": "general",
                            "creator": "c", "status": "ready_for_approval", "current_version": 1}]
    monkeypatch.setattr(main, "get_db", lambda: db)
    monkeypatch.setattr(main, "run_review_pipeline",
                        lambda **k: {"findings": [], "fallback_used": False})
    monkeypatch.setattr(main, "REQUIRE_AUTH", False)
    c = TestClient(main.app, headers={"x-forwarded-for": f"10.0.0.{next(_ip)}"})
    c.db = db
    return c


NEW_RULE = {"id": "T-1", "category": "tone", "text": "x", "severity": "low"}
NEW_FACT = {"id": "F-T1", "approved_text": "x", "source": "s", "owner": "o"}


# ---- Admin routes ---------------------------------------------------------
def test_admin_routes_refuse_anonymous(client):
    assert client.post("/api/rules", json=NEW_RULE).status_code == 401
    assert client.put("/api/rules/CL-001", json={"text": "hacked"}).status_code == 401
    assert client.post("/api/facts", json=NEW_FACT).status_code == 401
    assert client.put("/api/facts/F-001", json={"approved_text": "hacked"}).status_code == 401
    assert client.post("/api/rules/import", files={"file": ("r.csv", b"id,text\n")}).status_code == 401


def test_admin_wrong_key_refused_right_key_allowed(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key-123")
    assert client.post("/api/rules", json=NEW_RULE, headers={"x-admin-key": "nope"}).status_code == 401
    assert client.post("/api/rules", json=NEW_RULE, headers={"x-admin-key": "test-admin-key-123"}).status_code == 200


def test_admin_disabled_when_no_key_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    assert client.post("/api/rules", json=NEW_RULE, headers={"x-admin-key": ""}).status_code == 401


def test_csv_import_limits(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "k")
    h = {"x-admin-key": "k"}
    big = b"id,category,text,severity\n" + b"A,b,c,low\n" * 200000
    assert client.post("/api/rules/import", headers=h, files={"file": ("r.csv", big)}).status_code == 413
    assert client.post("/api/rules/import", headers=h, files={"file": ("r.csv", b"\xff\xfe\x00bad")}).status_code == 400
    ok = b"id,category,text,severity\nR-1,tone,Be kind,low\n../bad id,tone,x,low\n"
    r = client.post("/api/rules/import", headers=h, files={"file": ("r.csv", ok)})
    assert r.status_code == 200 and r.json() == {"status": "success", "imported": 1, "skipped": 1}


# ---- CORS + headers -------------------------------------------------------
def test_cors_blocks_unknown_origin_allows_ours(client):
    pre = lambda o: client.options("/api/submissions", headers={
        "Origin": o, "Access-Control-Request-Method": "POST"})
    assert pre(EVIL).headers.get("access-control-allow-origin") is None
    assert pre(GOOD).headers.get("access-control-allow-origin") == GOOD
    assert pre(GOOD).headers.get("access-control-allow-credentials") is None


def test_security_headers_present(client):
    h = client.get("/health").headers
    for name in ("x-content-type-options", "x-frame-options", "strict-transport-security",
                 "content-security-policy", "referrer-policy", "permissions-policy"):
        assert name in h, name
    assert h["x-content-type-options"] == "nosniff"


# ---- Validation -----------------------------------------------------------
def _post(client, **over):
    body = {"title": "T", "text": "Hello customers, this is a fine post.", "channel": "social",
            "audience": "general", "creator": "Creator"}
    body.update(over)
    return client.post("/api/submissions", json=body)


def test_input_limits(client):
    assert _post(client, text="A" * 5001).status_code == 422
    assert _post(client, title="T" * 201).status_code == 422
    assert _post(client, creator="C" * 101).status_code == 422
    assert _post(client, text="").status_code == 422
    assert client.post("/api/submissions/s1/resubmit", json={"text": "A" * 5001}).status_code == 422


# ---- Rate limiting --------------------------------------------------------
def test_ai_rate_limit_per_ip(client):
    codes = [_post(client).status_code for _ in range(13)]
    assert codes[:10] == [200] * 10
    assert 429 in codes[10:]
    r = _post(client)
    assert r.status_code == 429 and "retry-after" in r.headers


def test_rate_limit_is_per_ip(client):
    for _ in range(12):
        _post(client)
    other = _post(client)  # same IP -> limited
    assert other.status_code == 429
    client.headers["x-forwarded-for"] = "10.9.9.9"
    assert _post(client).status_code == 200  # a different visitor is unaffected


def test_health_never_rate_limited(client):
    assert {client.get("/health").status_code for _ in range(300)} == {200}


# ---- Error leakage --------------------------------------------------------
def test_database_errors_are_not_leaked(client):
    client.db.boom = True
    r = _post(client)
    assert r.status_code == 500
    assert "SECRET-DB-DETAIL" not in r.text and "hunter2" not in r.text


# ---- Existing behaviour still works (regression) --------------------------
def test_normal_submission_flow_still_works(client):
    r = _post(client)
    assert r.status_code == 200
    assert {"submission_id", "status", "findings"} <= set(r.json())


def test_approval_rules_unchanged(client):
    ap = lambda role: client.post("/api/submissions/s1/approval",
                                  json={"role": role, "decision": "approve", "comment": "ok"})
    assert ap("Creator").status_code == 403
    assert ap("Manager").status_code == 200
    client.db.t["submissions"][0]["status"] = "ready_for_approval"
    main.REQUIRE_AUTH = True
    try:
        assert ap("Manager").status_code == 401
    finally:
        main.REQUIRE_AUTH = False


def test_workspace_and_dashboard_endpoints_still_respond(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/workspace").status_code == 200
