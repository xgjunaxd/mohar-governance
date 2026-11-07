# tests/test_pipeline_samples.py
"""
5 Sample AstraPay posts with expected findings and unit tests for:
- app/rules_engine.py
- app/validator.py
- app/pipeline.py (deduplication, caching, status calculation)
"""

from datetime import date
from app.pipeline import clear_pipeline_cache, run_review_pipeline
from app.validator import validate_findings

SAMPLE_POSTS = [
    {
        "id": "SAMPLE-1",
        "channel": "social",
        "audience": "general",
        "text": "Hey bro! Astra Pay users can now load their mini wallet in seconds!!",
        "expected_rule_or_fact_ids": {"TN-001", "TM-001", "TM-002", "TN-002"},
        "expected_status": "needs_review",
    },
    {
        "id": "SAMPLE-2",
        "channel": "social",
        "audience": "investors",
        "text": "Want free money? Invest with AstraPay Wealth today for guaranteed returns of 12% p.a. on your portfolio.",
        "expected_rule_or_fact_ids": {"TM-003", "CL-001", "DS-001"},
        "expected_status": "blocked",
    },
    {
        "id": "SAMPLE-3",
        "channel": "email",
        "audience": "existing_customers",
        "text": 'Celebrate with the "Diwali Dhamaka" cashback offer on AstraPay and get exciting rewards on your bill payments.',
        "expected_rule_or_fact_ids": {"F-004", "CL-003"},
        "expected_status": "blocked",
    },
    {
        "id": "SAMPLE-4",
        "channel": "web_copy",
        "audience": "general",
        "text": "AstraPay is India's No.1 fastest payment app where customers can transfer up to Rs. 5,00,000 daily via UPI and earn 9% p.a. on AstraPay Savings.",
        # Note: CL-002, F-002/FC-001, and F-008/FC-001 are detected when Gemini is enabled
        "expected_gemini_ids": {"CL-002", "F-002", "F-008", "FC-001"},
        "expected_status_with_gemini": "blocked",
    },
    {
        "id": "SAMPLE-5",
        "channel": "social",
        "audience": "general",
        "text": "AstraPay customers can enjoy zero fees on UPI transfers and get cashback up to Rs. 100 on their first bill payment with AstraPay Rewards. Valid till 30 Nov 2026. T&C apply.",
        "expected_rule_or_fact_ids": set(),
        "expected_status": "ready_for_approval",
    },
]


def test_deterministic_samples_1_2_3_5():
    """Verifies deterministic rules engine + validator + pipeline on Samples 1, 2, 3, and 5."""
    clear_pipeline_cache()
    ref_date = date(2026, 11, 4)

    for sample in SAMPLE_POSTS:
        if "expected_rule_or_fact_ids" not in sample:
            continue

        result = run_review_pipeline(
            text=sample["text"],
            channel=sample["channel"],
            audience=sample["audience"],
            use_gemini=False,
            reference_date=ref_date,
        )
        found_ids = {f["rule_or_fact_id"] for f in result["findings"]}
        assert sample["expected_rule_or_fact_ids"].issubset(found_ids), (
            f"{sample['id']} missing expected IDs. Expected {sample['expected_rule_or_fact_ids']}, got {found_ids}"
        )
        assert result["status"] == sample["expected_status"], (
            f"{sample['id']} status mismatch. Expected {sample['expected_status']}, got {result['status']}"
        )


def test_validator_flags_hallucinated_id_and_excerpt():
    """Ensures validator sets evidence_valid=False and needs_human=True on bad AI output."""
    content = "Send money easily to any bank account with AstraPay."
    fake_ai_findings = [
        {
            "category": "unsupported_claim",
            "severity": "high",
            "confidence": 0.92,
            "excerpt": "Send money easily",
            "rule_or_fact_id": "FAKE-999",  # Non-existent rule ID
            "explanation": "Hallucinated rule ID.",
            "fix_1": "Transfer money",
            "fix_2": "Pay contacts",
            "needs_human": False,
        },
        {
            "category": "tone",
            "severity": "low",
            "confidence": 0.88,
            "excerpt": "text that is not in the post at all",  # Non-existent excerpt
            "rule_or_fact_id": "TN-001",
            "explanation": "Hallucinated excerpt.",
            "fix_1": "Fix A",
            "fix_2": "Fix B",
            "needs_human": False,
        },
    ]

    validated = validate_findings(fake_ai_findings, content=content)
    assert len(validated) == 2
    assert validated[0]["evidence_valid"] is False
    assert validated[0]["needs_human"] is True
    assert validated[1]["evidence_valid"] is False
    assert validated[1]["needs_human"] is True


def test_pipeline_cache_and_deduplication():
    """Verifies that identical (text, channel, audience) hits the cache on the second call."""
    clear_pipeline_cache()
    post = "Hey bro, Astra Pay is live!"
    first = run_review_pipeline(post, channel="social", audience="general", use_gemini=False)
    second = run_review_pipeline(post, channel="social", audience="general", use_gemini=False)

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert len(first["findings"]) == len(second["findings"])


if __name__ == "__main__":
    test_deterministic_samples_1_2_3_5()
    test_validator_flags_hallucinated_id_and_excerpt()
    test_pipeline_cache_and_deduplication()
    print("All deterministic pipeline and validator tests passed successfully!")