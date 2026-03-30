"""
generate_rubric.py — Generate or enhance a grading rubric from assignment instructions.

Usage (standalone test):
    python generate_rubric.py --assignment assignments/assignment1_instructions.txt
    python generate_rubric.py --assignment assignments/assignment1_instructions.txt \
        --existing-rubric path/to/rubric.txt \
        --instructions "Focus more on EHR terminology and HL7 standards"
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (two levels up: rubric_gen → scripts → project root)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are an expert course designer for a graduate-level Health Information Systems course.
Your task is to create a grading rubric for a given assignment.

RUBRIC REQUIREMENTS:
- Total points must equal exactly 100.
- Create 3-5 criteria that reflect the main evaluation dimensions of the assignment.
- Each criterion must have:
    - A clear, descriptive name
    - A max_points value (integer, >0, all criteria must sum to 100)
    - 4-8 specific, measurable checklist items that a grader can evaluate as YES/PARTIAL/NO
- Checklist items must be concrete and observable, evaluating SUBSTANCE and UNDERSTANDING — not format or presentation.
  GOOD: "Student identifies at least two bottlenecks in the current workflow"
  BAD:  "Swim lanes are correctly shown" / "Issues listed in bullet format" / "Diagram uses Visio"
- Do NOT create checklist items based on format requirements (diagram style, file type, software tool, layout, bullet vs paragraph, number of slides/pages). Those are submission mechanics, not learning outcomes.
- Do NOT reference specific tools (Visio, PowerPoint, Word) or visual conventions (swim lanes, arrows, boxes) in checklist items unless the assignment is explicitly about mastering that tool.
- Each item must be gradable YES/PARTIAL/NO based on the conceptual content alone, even if the student used a completely different visual format.
- Do NOT include grade bands, point deductions, or scoring instructions — just criteria and checklist items.
- Do NOT add a "Clarity and Quality" criterion unless the assignment explicitly mentions it.

OUTPUT: Return ONLY valid JSON, no markdown, no explanation:
{
  "criteria": [
    {
      "criterion_name": "<name>",
      "max_points": <integer>,
      "checklist_items": ["<item 1>", "<item 2>", ...]
    }
  ],
  "total_points": 100
}
"""

ENHANCE_SYSTEM_PROMPT = """\
You are an expert course designer for a graduate-level Health Information Systems course.
Your task is to enhance an existing grading rubric based on the assignment instructions.

ENHANCEMENT REQUIREMENTS:
- Keep the same overall structure and total points (must equal 100).
- Improve checklist items to be more specific and measurable, focusing on SUBSTANCE and UNDERSTANDING — not format or presentation.
- Remove any checklist items that test format requirements (diagram style, file type, software tool used, layout, bullet vs paragraph, slide/page count). These are submission mechanics, not learning outcomes.
- Do NOT reference specific tools (Visio, PowerPoint, Word) or visual conventions (swim lanes, arrows, boxes) unless the assignment is explicitly about mastering that tool.
- Add missing checklist items that the assignment clearly requires but the rubric omits (conceptual coverage only).
- Remove vague or duplicate checklist items.
- Each item must be gradable YES/PARTIAL/NO based on conceptual content alone, regardless of the visual format the student used.
- Adjust max_points per criterion if the current distribution doesn't match the assignment emphasis.
- Each criterion must have 4-8 checklist items.

OUTPUT: Return ONLY valid JSON, no markdown, no explanation:
{
  "criteria": [
    {
      "criterion_name": "<name>",
      "max_points": <integer>,
      "checklist_items": ["<item 1>", "<item 2>", ...]
    }
  ],
  "total_points": 100
}
"""


@dataclass
class RubricCriterion:
    criterion_name: str
    max_points: float
    checklist_items: list[str] = field(default_factory=list)


@dataclass
class Rubric:
    criteria: list[RubricCriterion]
    total_points: float


def _parse_json(raw: str) -> dict:
    """Extract JSON object from LLM response, stripping markdown fences if present."""
    # Strip ```json ... ``` fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    # Find first { ... } block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response:\n{raw[:500]}")
    return json.loads(raw[start:end])


def _validate_and_build(data: dict) -> Rubric:
    """Validate LLM JSON output and return a Rubric dataclass."""
    criteria_raw = data.get("criteria")
    if not criteria_raw or not isinstance(criteria_raw, list):
        raise ValueError("Response missing 'criteria' list")

    criteria = []
    for c in criteria_raw:
        name = str(c.get("criterion_name", "")).strip()
        pts = float(c.get("max_points", 0))
        items = [str(i).strip() for i in c.get("checklist_items", []) if str(i).strip()]
        if not name:
            raise ValueError(f"Criterion missing name: {c}")
        if pts <= 0:
            raise ValueError(f"Criterion '{name}' has invalid max_points: {pts}")
        if not items:
            raise ValueError(f"Criterion '{name}' has no checklist items")
        criteria.append(RubricCriterion(criterion_name=name, max_points=pts, checklist_items=items))

    total = sum(c.max_points for c in criteria)
    if abs(total - 100) > 0.5:
        raise ValueError(f"Criteria points sum to {total}, expected 100")

    return Rubric(criteria=criteria, total_points=total)


def _call_anthropic(system: str, user: str, model: str, api_key: str) -> dict:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = message.content[0].text.strip()
    in_tok = message.usage.input_tokens
    out_tok = message.usage.output_tokens
    cost = (in_tok * 3.00 + out_tok * 15.00) / 1_000_000
    print(f"[token usage] input={in_tok}  output={out_tok}  cost=${cost:.5f}")
    return _parse_json(raw)


def generate_rubric(
    assignment_text: str,
    *,
    instructions: str = "",
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> Rubric:
    """
    Generate a new rubric from assignment instructions.

    Args:
        assignment_text: Full text of the assignment instructions.
        instructions: Optional professor guidance (e.g. "emphasize HL7 standards").
        model: Anthropic model to use.
        api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var).
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    user_parts = [f"=== ASSIGNMENT INSTRUCTIONS ===\n{assignment_text.strip()}"]
    if instructions:
        user_parts.append(f"=== ADDITIONAL INSTRUCTIONS ===\n{instructions.strip()}")
    user_parts.append("Generate the rubric JSON now.")

    data = _call_anthropic(SYSTEM_PROMPT, "\n\n".join(user_parts), model, api_key)
    return _validate_and_build(data)


def enhance_rubric(
    assignment_text: str,
    existing_rubric_text: str,
    *,
    instructions: str = "",
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> Rubric:
    """
    Enhance an existing rubric given the assignment instructions.

    Args:
        assignment_text: Full text of the assignment instructions.
        existing_rubric_text: The current rubric (any text format — DOCX text, JSON, plain text).
        instructions: Optional professor guidance for the enhancement.
        model: Anthropic model to use.
        api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var).
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    user_parts = [
        f"=== ASSIGNMENT INSTRUCTIONS ===\n{assignment_text.strip()}",
        f"=== EXISTING RUBRIC ===\n{existing_rubric_text.strip()}",
    ]
    if instructions:
        user_parts.append(f"=== ADDITIONAL INSTRUCTIONS ===\n{instructions.strip()}")
    user_parts.append("Enhance the rubric JSON now.")

    data = _call_anthropic(ENHANCE_SYSTEM_PROMPT, "\n\n".join(user_parts), model, api_key)
    return _validate_and_build(data)


def rubric_to_dict(rubric: Rubric) -> dict:
    return {
        "total_points": rubric.total_points,
        "criteria": [
            {
                "criterion_name": c.criterion_name,
                "max_points": c.max_points,
                "checklist_items": c.checklist_items,
            }
            for c in rubric.criteria
        ],
    }


# ── CLI for standalone testing ────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or enhance a grading rubric")
    parser.add_argument("--assignment", required=True, help="Path to assignment instructions text file")
    parser.add_argument("--existing-rubric", default=None, help="Path to existing rubric text file (triggers enhance mode)")
    parser.add_argument("--instructions", default="", help="Additional professor instructions")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model to use")
    parser.add_argument("--output", default=None, help="Save JSON output to this file path")
    args = parser.parse_args()

    assignment_text = Path(args.assignment).read_text(encoding="utf-8")

    if args.existing_rubric:
        existing_text = Path(args.existing_rubric).read_text(encoding="utf-8")
        print(f"Mode: ENHANCE (existing rubric: {args.existing_rubric})")
        rubric = enhance_rubric(assignment_text, existing_text, instructions=args.instructions, model=args.model)
    else:
        print("Mode: GENERATE (from scratch)")
        rubric = generate_rubric(assignment_text, instructions=args.instructions, model=args.model)

    result = rubric_to_dict(rubric)
    print(json.dumps(result, indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
