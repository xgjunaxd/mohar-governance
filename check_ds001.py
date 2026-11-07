from app.rules_engine import run_rules_engine

def ids(text):
    return [f["rule_or_fact_id"] for f in run_rules_engine(text)]

investing = ids("Get guaranteed returns of 12% p.a. on your savings.")
science = ids("Imagine travelling at light speed... you could return to Earth much later.")

print("Investment post :", investing)
print("Science post    :", science)
print()
print("CHECK 1 (investment post gets DS-001):", "PASS" if "DS-001" in investing else "FAIL")
print("CHECK 2 (science post has NO DS-001) :", "PASS" if "DS-001" not in science else "FAIL")
