# app/gemini_client.py
"""
Gemini API client for Mohar.
- Makes ONE call per review using `google-genai` (with fallback support if `google-generativeai` is installed).
- Reads GEMINI_API_KEY from environment variables.
- Uses temperature 0.2 and JSON response mode.
- Validates output against Pydantic schema.
- Retries once on invalid JSON or validation error, then falls back cleanly.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

# Exact system prompt following MASTER CONTEXT & AI-2 specification
SYSTEM_PROMPT = """You are a senior brand governance reviewer for AstraPay (an Indian fintech and UPI app).
Your job is to review pre-publication marketing and customer communications for brand, tone, terminology, claim, disclaimer, and factual compliance.

STRICT OPERATING RULES:
1. Act as a brand reviewer for AstraPay.
2. Use ONLY the provided rules and facts in the prompt. Never invent a rule or fact.
3. Cite ONLY the exact IDs from the provided rules and facts lists (e.g., "CL-001", "CL-002", "CL-003", "TN-001", "TN-002", "TM-001", "TM-002", "TM-003", "FC-001", "FC-002", "DS-001", "AC-001", or "F-001" through "F-010").
4. Return a JSON array ONLY (no Markdown fences, no prose before or after). If there are no issues, return [].
5. For every finding, `excerpt` MUST be an exact, verbatim substring copied from the submitted content.
6. Include `confidence` honestly as a float between 0.0 and 1.0.
7. Provide 2 actionable replacement fixes (`fix_1` and `fix_2`) that preserve the creator's original meaning and keep numbers/promises unchanged UNLESS the fix removes an illegal claim or corrects a factual error against the approved fact ledger.
8. Set `needs_human` to true whenever a claim is ambiguous, borderline, relies on an external source not in the fact ledger, or you are unsure.

REQUIRED JSON ARRAY ITEM SHAPE:
{
  "category": "unsupported_claim|fact_error|expired_fact|terminology|tone|disclaimer|accessibility",
  "severity": "high|medium|low",
  "confidence": 0.85,
  "excerpt": "exact text from content",
  "rule_or_fact_id": "CL-001",
  "explanation": "plain-language reason citing the exact rule or fact",
  "fix_1": "first suggested replacement keeping meaning intact",
  "fix_2": "second suggested replacement keeping meaning intact",
  "needs_human": false
}"""


class FindingModel(BaseModel):
    """Pydantic schema for validating each finding returned by Gemini."""

    category: Literal[
        "unsupported_claim",
        "fact_error",
        "expired_fact",
        "terminology",
        "tone",
        "disclaimer",
        "accessibility",
    ]
    severity: Literal["high", "medium", "low"]
    confidence: float = Field(ge=0.0, le=1.0)
    excerpt: str = Field(min_length=1)
    rule_or_fact_id: str = Field(min_length=2)
    explanation: str = Field(min_length=3)
    fix_1: str = Field(min_length=1)
    fix_2: str = Field(min_length=1)
    needs_human: bool = False


FINDING_LIST_ADAPTER = TypeAdapter(List[FindingModel])


def _build_user_prompt(
    text: str,
    channel: str,
    audience: str,
    rules: List[Dict[str, Any]],
    facts: List[Dict[str, Any]],
) -> str:
    """Formats all rules, facts, metadata, and content for the single Gemini review call."""
    rules_lines = [
        f"- {r['id']} (category: {r.get('category', 'general')}, severity: {r.get('severity', 'medium')}): {r['text']}"
        for r in rules
    ]
    facts_lines = [
        f"- {f['id']}: {f['approved_text']} | expires_on: {f.get('expires_on') or 'none'} | status: {f.get('status', 'active')}"
        for f in facts
    ]
    return (
        "APPROVED ASTRAPAY RULES:\n"
        + "\n".join(rules_lines)
        + "\n\nAPPROVED ASTRAPAY FACTS LEDGER:\n"
        + "\n".join(facts_lines)
        + f"\n\nSUBMISSION METADATA:\nChannel: {channel}\nAudience: {audience}\n\n"
        + "CONTENT TO REVIEW:\n"
        + f'"""\n{text}\n"""\n\n'
        + "Return ONLY a valid JSON array of findings matching the required schema."
    )


def _strip_markdown_fences(raw_text: str) -> str:
    """Removes ```json ... ``` wrappers if a model includes them despite JSON mode."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _call_gemini_raw(user_prompt: str, api_key: str, model_name: str) -> str:
    """
    Executes a single Gemini API call with temperature=0.2 and JSON response mode.
    Supports `google-genai` (primary) and `google-generativeai` (fallback import).
    """
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        return response.text or "[]"
    except ImportError:
        import google.generativeai as genai_legacy  # type: ignore

        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        )
        response = model.generate_content(user_prompt)
        return response.text or "[]"


def analyze_with_gemini(
    text: str,
    rules: List[Dict[str, Any]],
    facts: List[Dict[str, Any]],
    channel: str = "social",
    audience: str = "general",
) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
    """
    Runs one Gemini API call to detect tone issues, implied claims, and fact mismatches.
    Retries once on bad JSON / Pydantic validation failure, then falls back cleanly.

    Returns:
        (findings_list, fallback_used, error_message)
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    if not api_key:
        return (
            [],
            True,
            "GEMINI_API_KEY is not set; falling back to deterministic rules-engine findings only.",
        )

    user_prompt = _build_user_prompt(
        text=text,
        channel=channel,
        audience=audience,
        rules=rules,
        facts=facts,
    )

    last_error: Optional[str] = None
    # Try up to 2 times (initial call + 1 retry on bad JSON / error)
    for attempt in range(2):
        try:
            prompt_to_send = user_prompt
            if attempt == 1 and last_error:
                prompt_to_send = (
                    user_prompt
                    + f"\n\nNOTE: Your previous response failed JSON validation ({last_error}). "
                    "Return ONLY a raw JSON array matching the exact schema."
                )

            raw_output = _call_gemini_raw(
                user_prompt=prompt_to_send,
                api_key=api_key,
                model_name=model_name,
            )
            cleaned_json = _strip_markdown_fences(raw_output)

            # Parse and validate with Pydantic
            parsed_data = json.loads(cleaned_json)
            # Handle case where model wraps list in {"findings": [...]}
            if isinstance(parsed_data, dict) and "findings" in parsed_data:
                parsed_data = parsed_data["findings"]

            validated_models = FINDING_LIST_ADAPTER.validate_python(parsed_data)
            findings = [item.model_dump() for item in validated_models]
            return findings, False, None

        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            last_error = f"{type(exc).__name__}: {exc}"

    return (
        [],
        True,
        f"Gemini review failed after 1 retry ({last_error}); showing deterministic rules-engine findings only.",
    )