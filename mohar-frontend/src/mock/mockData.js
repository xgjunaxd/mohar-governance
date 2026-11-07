export const MOCK_WORKSPACE = {
  workspace: {
    name: "AstraPay Demo Workspace",
    brand: "AstraPay",
    industry: "Fintech / UPI Payments",
    tone: "Formal but friendly"
  },
  rules: [
    {
      id: "CL-001",
      category: "unsupported_claim",
      text: "Never promise guaranteed, assured or risk-free returns.",
      severity: "high",
      version: "1.0",
      is_mandatory: true
    },
    {
      id: "CL-002",
      category: "unsupported_claim",
      text: "Superlatives ('best', 'No.1', 'fastest') need an approved source.",
      severity: "medium",
      version: "1.0",
      is_mandatory: false
    },
    {
      id: "CL-003",
      category: "unsupported_claim",
      text: "Every offer must state its validity period and 'T&C apply'.",
      severity: "medium",
      version: "1.0",
      is_mandatory: true
    },
    {
      id: "TN-001",
      category: "tone",
      text: "Formal but friendly tone; no slang ('bro', 'lit', 'gonna'), no ALL CAPS shouting.",
      severity: "low",
      version: "1.0",
      is_mandatory: false
    },
    {
      id: "TN-002",
      category: "tone",
      text: "At most one exclamation mark per post.",
      severity: "low",
      version: "1.0",
      is_mandatory: false
    },
    {
      id: "TM-001",
      category: "terminology",
      text: "Write 'AstraPay' (one word), never 'Astra Pay' or 'ASTRAPAY'.",
      severity: "low",
      version: "1.0",
      is_mandatory: true
    },
    {
      id: "TM-002",
      category: "terminology",
      text: "Say 'customers' not 'users'; say 'UPI Lite wallet' not 'mini wallet'.",
      severity: "low",
      version: "1.0",
      is_mandatory: false
    },
    {
      id: "TM-003",
      category: "terminology",
      text: "Banned words: 'free money', 'guaranteed loan', 'cheat', 'instant rich'.",
      severity: "high",
      version: "1.0",
      is_mandatory: true
    },
    {
      id: "FC-001",
      category: "fact_error",
      text: "Fees, limits and rates must match the approved fact ledger.",
      severity: "high",
      version: "1.0",
      is_mandatory: true
    },
    {
      id: "FC-002",
      category: "expired_fact",
      text: "Expired offers must not be advertised.",
      severity: "high",
      version: "1.0",
      is_mandatory: true
    },
    {
      id: "DS-001",
      category: "disclaimer",
      text: "Investment-related posts must include 'Investments are subject to market risks.'",
      severity: "high",
      version: "1.0",
      is_mandatory: true
    },
    {
      id: "AC-001",
      category: "accessibility",
      text: "Every image must have alt text (checked in Round 3).",
      severity: "medium",
      version: "1.0",
      is_mandatory: false
    }
  ],
  facts: [
    {
      id: "F-001",
      approved_text: "UPI transfers on AstraPay have zero fees.",
      source: "Product Spec v2.1",
      owner: "Payments Product Team",
      valid_from: "2025-01-01",
      expires_on: null,
      status: "active"
    },
    {
      id: "F-002",
      approved_text: "Daily UPI transfer limit is Rs. 1,00,000.",
      source: "RBI Guidelines / Compliance",
      owner: "Risk & Compliance",
      valid_from: "2025-01-01",
      expires_on: null,
      status: "active"
    },
    {
      id: "F-003",
      approved_text: "AstraPay Rewards: cashback up to Rs. 100 on first bill payment.",
      source: "Q4 Growth Campaign Document",
      owner: "Growth Marketing",
      valid_from: "2026-09-01",
      expires_on: "2026-11-30",
      status: "active"
    },
    {
      id: "F-004",
      approved_text: "'Diwali Dhamaka' cashback offer.",
      source: "Diwali 2025 Marketing Campaign",
      owner: "Campaign Lead",
      valid_from: "2025-10-15",
      expires_on: "2025-11-15",
      status: "expired"
    },
    {
      id: "F-005",
      approved_text: "Merchant fee is 0% for new merchants.",
      source: "Merchant Partnership Program 2026",
      owner: "Merchant Operations",
      valid_from: "2026-01-01",
      expires_on: "2026-12-31",
      status: "active"
    },
    {
      id: "F-006",
      approved_text: "Customer support is available 8 AM to 10 PM IST.",
      source: "SLA Handbook 2026",
      owner: "Support Operations",
      valid_from: "2025-01-01",
      expires_on: null,
      status: "active"
    },
    {
      id: "F-007",
      approved_text: "AstraPay Card annual fee is Rs. 499.",
      source: "Card Pricing Schedule",
      owner: "Card Business Unit",
      valid_from: "2025-06-01",
      expires_on: null,
      status: "active"
    },
    {
      id: "F-008",
      approved_text: "AstraPay Savings interest rate is 6.5% p.a. (subject to change).",
      source: "Banking Partner Rate Sheet",
      owner: "Treasury & Banking",
      valid_from: "2026-01-01",
      expires_on: "2026-12-31",
      status: "active"
    },
    {
      id: "F-009",
      approved_text: "UPI Lite wallet limit is Rs. 10,000.",
      source: "NPCI Circular 2025/11",
      owner: "Compliance",
      valid_from: "2025-11-01",
      expires_on: null,
      status: "active"
    },
    {
      id: "F-010",
      approved_text: "AstraPay is a fictional demo brand used for testing.",
      source: "Hackathon Demo Architecture",
      owner: "Engineering Core",
      valid_from: "2026-01-01",
      expires_on: null,
      status: "active"
    }
  ]
};