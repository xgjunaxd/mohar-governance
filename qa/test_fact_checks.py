"""Tests for the rule-based backup checks (no Gemini needed).
Run from the repo root:  python -m pytest -q qa/test_fact_checks.py
"""
import csv
import os
import pathlib

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy")

import pytest  # noqa: E402
from app.rules_engine import run_rules_engine, DEFAULT_FACTS  # noqa: E402
from app.pipeline import run_review_pipeline  # noqa: E402

NEW = {"F-001", "F-002", "F-003", "F-005", "F-006", "F-007", "F-008", "F-009", "CL-002"}


def ids(text, **kw):
    return {f["rule_or_fact_id"] for f in run_rules_engine(text, **kw) if f["rule_or_fact_id"] in NEW}


@pytest.mark.parametrize("text,expected", [
    ("Daily UPI transfer limit is Rs. 5,00,000.", {"F-002"}),
    ("Daily UPI transfer limit is Rs. 1,00,000.", set()),
    ("You can transfer up to Rs. 2,50,000 daily via UPI.", {"F-002"}),
    ("Your UPI Lite wallet holds up to Rs. 25,000 at a time.", {"F-009"}),
    ("UPI Lite wallet limit is Rs. 10,000.", set()),
    ("The AstraPay Card annual fee is Rs. 999.", {"F-007"}),
    ("The AstraPay Card annual fee is Rs. 499.", set()),
    ("Earn 9% p.a. on AstraPay Savings.", {"F-008"}),
    ("Earn 6.5% p.a. on AstraPay Savings.", set()),
    ("Pay a small fee on every UPI transfer.", {"F-001"}),
    ("Enjoy zero fees on every UPI transfer.", set()),
    ("There are no charges on transfers.", set()),
    ("Our support is available 24x7.", {"F-006"}),
    ("Support is available from 8 AM to 10 PM IST.", set()),
    ("Support is available from 9 AM to 6 PM.", {"F-006"}),
    ("Merchants pay a 2% merchant fee.", {"F-005"}),
    ("Merchants pay a 0% merchant fee.", set()),
    ("Get cashback up to Rs. 500 on your first bill.", {"F-003"}),
    ("Get cashback up to Rs. 100 on your first bill.", set()),
    ("This is the best savings account.", {"CL-002"}),
    ("AstraPay is India's No.1 payment app.", {"CL-002"}),
    ("We offer the fastest transfers.", {"CL-002"}),
    ("Best wishes for the festive season.", set()),
    ("According to a 2026 survey, AstraPay is the best app.", set()),
])
def test_single_claims(text, expected):
    assert ids(text) == expected


def test_clean_post_has_no_new_flags():
    t = ("Dear Customer, AstraPay now lets you pay your utility bills in a few taps. "
         "Offer valid until 30 November 2026. T&C apply.")
    assert ids(t) == set()


def test_rs_abbreviation_does_not_break_sentences():
    r = [f for f in run_rules_engine("Daily UPI transfer limit is Rs. 5,00,000. Thanks.") if f["rule_or_fact_id"] == "F-002"]
    assert r and r[0]["excerpt"] == "Daily UPI transfer limit is Rs. 5,00,000."


def test_excerpts_are_exact_text_from_the_post():
    t = "Hi! The AstraPay Card annual fee is Rs. 999. This is the best app."
    for f in run_rules_engine(t):
        assert f["excerpt"] in t


def test_fix_replaces_wrong_number_with_approved_one():
    f = [x for x in run_rules_engine("The AstraPay Card annual fee is Rs. 999.") if x["rule_or_fact_id"] == "F-007"][0]
    assert "999" not in f["fix_1"] and "499" in f["fix_1"]


def test_uses_live_facts_not_hardcoded_numbers():
    facts = [dict(f) for f in DEFAULT_FACTS]
    for f in facts:
        if f["id"] == "F-007":
            f["approved_text"] = "AstraPay Card annual fee is Rs. 999."
    assert "F-007" not in ids("The AstraPay Card annual fee is Rs. 999.", facts=facts)


def test_missing_fact_is_never_checked():
    facts = [f for f in DEFAULT_FACTS if f["id"] != "F-002"]
    assert "F-002" not in ids("Daily UPI transfer limit is Rs. 5,00,000.", facts=facts)


def test_superlative_check_respects_rule_list():
    rules = [{"id": "TM-001"}]
    assert "CL-002" not in ids("This is the best app.", rules=rules)


def test_pipeline_catches_everything_without_gemini():
    t = ("Hi users! Astra Pay gives you guaranteed 10% interest on savings. "
         "We also offer the fastest UPI transfers in India. "
         "Daily transfer limit is Rs. 2,00,000 with zero fees. Invest today. "
         "Offer valid till 31 December 2026. T&C apply.")
    r = run_review_pipeline(text=t, use_gemini=False, use_cache=False)
    got = {f["rule_or_fact_id"] for f in r["findings"]}
    assert {"TM-001", "TM-002", "CL-001", "DS-001", "F-008", "F-002", "CL-002"} <= got


# Samples whose planted problem is a WRONG number or an unproven superlative.
MUST_FIND = {"S-003": {"CL-002"}, "S-005": {"F-001", "F-006"}, "S-008": {"F-005"}, "S-010": {"F-007", "F-009"},
             "S-011": {"F-008"}, "S-012": {"F-003"}, "S-015": {"CL-002"}, "S-017": {"F-006"},
             "S-018": {"F-002"}, "S-019": {"CL-002"}, "S-023": {"F-007"}}


def test_qa_samples_no_false_alarms_and_wrong_numbers_found():
    path = pathlib.Path(__file__).parent / "test_samples.csv"
    rows = {r["id"]: r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    for sid, r in rows.items():
        got = ids(r["text"])
        planted = set(r["planted_issues"].split(";"))
        if r["type"] != "violation":
            assert got == set(), (sid, got)          # clean posts are never flagged
        assert got <= planted, (sid, got, planted)   # no flag outside the planted problems
    for sid, must in MUST_FIND.items():
        assert must <= ids(rows[sid]["text"]), (sid, must, ids(rows[sid]["text"]))
