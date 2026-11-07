import app.main as main
from fastapi.testclient import TestClient

class Q:
    def __init__(s, rows): s.rows, s.f, s.mode, s.p = rows, [], "select", None
    def select(s, *a): s.mode = "select"; return s
    def eq(s, c, v): s.f.append((c, v)); return s
    def order(s, *a, **k): return s
    def update(s, p): s.mode, s.p = "update", p; return s
    def insert(s, p): s.mode, s.p = "insert", p; return s
    def execute(s):
        match = [r for r in s.rows if all(r.get(c) == v for c, v in s.f)]
        if s.mode == "update": [r.update(s.p) for r in match]
        if s.mode == "insert": s.rows.append(s.p)
        return type("R", (), {"data": match})()

class DB:
    def __init__(s): s.t = {}
    def table(s, n): return Q(s.t.setdefault(n, []))

db = DB()
db.t["submissions"] = [{"id": "s1", "title": "t", "channel": "social", "audience": "general",
                        "creator": "c", "status": "ready_for_approval", "current_version": 1}]
main.get_db = lambda: db
client = TestClient(main.app)

def approve(role):
    return client.post("/api/submissions/s1/approval",
                       json={"role": role, "decision": "approve", "comment": "ok"})

a = approve("Creator").status_code
b = approve("Manager").status_code
db.t["submissions"][0]["status"] = "ready_for_approval"
main.REQUIRE_AUTH = True
c = approve("Manager").status_code
main.REQUIRE_AUTH = False

print("Creator tries to approve        :", a, "PASS" if a == 403 else "FAIL (want 403)")
print("Manager approves (no login)     :", b, "PASS" if b == 200 else "FAIL (want 200)")
print("REQUIRE_AUTH on, no login token :", c, "PASS" if c == 401 else "FAIL (want 401)")
