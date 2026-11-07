from app.db import get_db

WORKSPACE_DATA = {
    "id": "astrapay-demo",
    "name": "AstraPay (Demo Brand)",
    "description": "Fictional Indian fintech/UPI app used for pre-publication brand governance demo.",
    "tone": "Formal but friendly"
}

RULES_SEED = [
    {
        "id": "CL-001",
        "category": "unsupported_claim",
        "text": "Never promise guaranteed, assured or risk-free returns",
        "severity": "high",
        "version": 1,
        "is_mandatory": True,
    },
    {
        "id": "CL-002",
        "category": "unsupported_claim",
        "text": 'Superlatives ("best", "No.1", "fastest") need an approved source',
        "severity": "medium",
        "version": 1,
        "is_mandatory": False,
    },
    {
        "id": "CL-003",
        "category": "disclaimer",
        "text": 'Every offer must state its validity period and "T&C apply"',
        "severity": "medium",
        "version": 1,
        "is_mandatory": False,
    },
    {
        "id": "TN-001",
        "category": "tone",
        "text": 'Formal but friendly tone; no slang ("bro", "lit", "gonna"), no ALL CAPS shouting',
        "severity": "low",
        "version": 1,
        "is_mandatory": False,
    },
    {
        "id": "TN-002",
        "category": "tone",
        "text": "At most one exclamation mark per post",
        "severity": "low",
        "version": 1,
        "is_mandatory": False,
    },
    {
        "id": "TM-001",
        "category": "terminology",
        "text": 'Write "AstraPay" (one word), never "Astra Pay" or "ASTRAPAY"',
        "severity": "low",
        "version": 1,
        "is_mandatory": False,
    },
    {
        "id": "TM-002",
        "category": "terminology",
        "text": 'Say "customers" not "users"; say "UPI Lite wallet" not "mini wallet"',
        "severity": "low",
        "version": 1,
        "is_mandatory": False,
    },
    {
        "id": "TM-003",
        "category": "terminology",
        "text": 'Banned words: "free money", "guaranteed loan", "cheat", "instant rich"',
        "severity": "high",
        "version": 1,
        "is_mandatory": True,
    },
    {
        "id": "FC-001",
        "category": "fact_error",
        "text": "Fees, limits and rates must match the approved fact ledger",
        "severity": "high",
        "version": 1,
        "is_mandatory": True,
    },
    {
        "id": "FC-002",
        "category": "expired_fact",
        "text": "Expired offers must not be advertised",
        "severity": "high",
        "version": 1,
        "is_mandatory": True,
    },
    {
        "id": "DS-001",
        "category": "disclaimer",
        "text": 'Investment-related posts must include "Investments are subject to market risks."',
        "severity": "high",
        "version": 1,
        "is_mandatory": True,
    },
    {
        "id": "AC-001",
        "category": "accessibility",
        "text": "Every image must have alt text (checked in Round 3)",
        "severity": "medium",
        "version": 1,
        "is_mandatory": False,
    },
]

FACTS_SEED = [
    {
        "id": "F-001",
        "approved_text": "UPI transfers on AstraPay have zero fees.",
        "source": "AstraPay Pricing Policy v2.1",
        "owner": "Payments Product Team",
        "valid_from": "2025-01-01",
        "expires_on": None,
        "status": "active",
    },
    {
        "id": "F-002",
        "approved_text": "Daily UPI transfer limit is Rs. 1,00,000.",
        "source": "NPCI & AstraPay Compliance Guidelines",
        "owner": "Compliance Team",
        "valid_from": "2025-01-01",
        "expires_on": None,
        "status": "active",
    },
    {
        "id": "F-003",
        "approved_text": "AstraPay Rewards: cashback up to Rs. 100 on first bill payment.",
        "source": "Q4 Marketing Campaign Brief",
        "owner": "Growth Marketing",
        "valid_from": "2026-01-01",
        "expires_on": "2026-11-30",
        "status": "active",
    },
    {
        "id": "F-004",
        "approved_text": '"Diwali Dhamaka" cashback offer.',
        "source": "Festive Campaign 2025 Archive",
        "owner": "Growth Marketing",
        "valid_from": "2025-10-01",
        "expires_on": "2025-11-15",
        "status": "expired",
    },
    {
        "id": "F-005",
        "approved_text": "Merchant fee is 0% for new merchants.",
        "source": "Merchant Onboarding Terms 2026",
        "owner": "B2B Team",
        "valid_from": "2026-01-01",
        "expires_on": "2026-12-31",
        "status": "active",
    },
    {
        "id": "F-006",
        "approved_text": "Customer support is available 8 AM to 10 PM IST.",
        "source": "Operations SLA Doc",
        "owner": "Customer Success",
        "valid_from": "2025-01-01",
        "expires_on": None,
        "status": "active",
    },
    {
        "id": "F-007",
        "approved_text": "AstraPay Card annual fee is Rs. 499.",
        "source": "Card Member Agreement",
        "owner": "Cards Team",
        "valid_from": "2025-01-01",
        "expires_on": None,
        "status": "active",
    },
    {
        "id": "F-008",
        "approved_text": "AstraPay Savings interest rate is 6.5% p.a. (subject to change).",
        "source": "Treasury Rate Sheet 2026",
        "owner": "Wealth & Savings Team",
        "valid_from": "2026-01-01",
        "expires_on": "2026-12-31",
        "status": "active",
    },
    {
        "id": "F-009",
        "approved_text": "UPI Lite wallet limit is Rs. 10,000.",
        "source": "Product Spec v1.4",
        "owner": "Payments Product Team",
        "valid_from": "2025-01-01",
        "expires_on": None,
        "status": "active",
    },
    {
        "id": "F-009",  # Kept consistent via upsert below
        "id": "F-010",
        "approved_text": "AstraPay is a fictional demo brand used for testing.",
        "source": "Mohar Demo Governance Notice",
        "owner": "Mohar System",
        "valid_from": "2026-01-01",
        "expires_on": None,
        "status": "active",
    },
]

SAMPLE_CONTENT_SEED = [
    {
        "title": "Festive Savings & Cashback Post (With Planted Issues)",
        "channel": "LinkedIn",
        "audience": "Retail Customers",
        "text": (
            "Hey bro!! Welcome to Astra Pay, India's No.1 payments app! "
            "All our users can still grab the Diwali Dhamaka cashback offer and get free money today! "
            "Plus, invest in AstraPay Savings for a guaranteed 8% risk-free return and enjoy our "
            "mini wallet limit of Rs. 25,000!!"
        ),
    },
    {
        "title": "Clean Bill Payment Rewards Post",
        "channel": "Email",
        "audience": "New Customers",
        "text": (
            "Hello! Make your everyday transactions seamless with AstraPay. "
            "UPI transfers on AstraPay have zero fees, and our customers can enjoy "
            "AstraPay Rewards with cashback up to Rs. 100 on their first bill payment. "
            "Offer valid until 30 Nov 2026. T&C apply."
        ),
    },
]

def run_seed():
    """Seeds workspace, rules, and facts into Supabase using upsert (safe to run multiple times)."""
    db = get_db()
    print("Seeding workspace...")
    db.table("workspaces").upsert(WORKSPACE_DATA).execute()

    print(f"Seeding {len(RULES_SEED)} AstraPay rules...")
    db.table("rules").upsert(RULES_SEED).execute()

    print(f"Seeding {len(FACTS_SEED)} AstraPay facts...")
    db.table("facts").upsert(FACTS_SEED).execute()

    print("Seed completed successfully!")

if __name__ == "__main__":
    run_seed()