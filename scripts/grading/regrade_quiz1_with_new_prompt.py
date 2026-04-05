#!/usr/bin/env python3
"""
Test Quiz 1 BPR Grading with New Prompt
========================================
Re-grades all 31 Quiz 1 submissions using the new specialized prompt that
prioritizes conceptual understanding and includes the instructor's calibration.

Before running:
1. Set OPENAI_API_KEY env var or update get_api_key() below
2. Ensure openpyxl is installed: pip install openpyxl
3. Run: python regrade_quiz1_with_new_prompt.py

Output:
- Prints side-by-side comparison: old AI score | new AI score | human score
- Calculates mean gap reduction
- Saves detailed results to quiz1_regrade_results.json
"""

import os
import sys
import json
import statistics
from pathlib import Path
from typing import Any

import openpyxl

# For calling OpenAI API
try:
    import openai
except ImportError:
    print("ERROR: openai not installed. Run: pip install openai")
    sys.exit(1)


MODEL_ONLY = "gpt-4o-2024-11-20"


def is_nonrecoverable_api_error(exception: Exception) -> bool:
    # Treat invalid API key as non-recoverable so one call attempt is enough.
    text = str(exception).lower()
    return "invalid_api_key" in text or "permission_denied" in text or "authorization" in text



# The specialized Quiz 1 BPR grading prompt (inlined to avoid import issues)
QUIZ_1_BPR_SYSTEM_PROMPT = """\
You are an expert graduate-level grader for a healthcare informatics course.
You are grading Quiz 1, Question 13 ("Why do we need to do Business Process 
Re-engineering as a part of implementing an EHR?") using the course's official 
rubric.

You are an expert graduate-level grader for a healthcare informatics course.
You are grading Quiz 1, Question 13 ("Why do we need to do Business Process 
Re-engineering as a part of implementing an EHR?") using the course's official 
rubric.

=== CRITICAL GRADING PRINCIPLE ===
CONCEPTUAL UNDERSTANDING IS PRIMARY. Focus on whether the student understands 
the core WHY of BPR for EHR, NOT on exact terminology or rubric keyword 
matching. Graduate students may use different words but still demonstrate the 
same deep understanding. Give credit for substance, not for checkbox words.

=== OFFICIAL RUBRIC (16 points total) ===

CRITERION A — CORE CONCEPTUAL UNDERSTANDING (8 points)
------------------------------------------------------
Measures: Does the student state the causal/functional role of BPR for EHR 
implementation? (e.g., redesigning workflows and data flows so the EHR can be 
used effectively; enabling interoperability; improving decision-making/adoption; 
addressing regulatory and business-model drivers).

SCORING:
• 8 points (Excellent): Clear, accurate causal role AND 2+ distinct effects 
  (interoperability, decision support, reduced redundancy, ROI, cost savings, 
  workflow efficiency). Shows cause-effect reasoning.
  
• 6 points (Good): Correct causal role AND at least one clear effect/benefit. 
  
• 4 points (Adequate): Partial/mostly-correct statement capturing BPR importance 
  but vague on mechanism or with minor inaccuracy.
  
• 2 points (Minimal): "BPR is important" with only generic justification, no 
  clear causal linkage.
  
• 0-1 points (Poor): Incorrect, irrelevant, or missing explanation.

*GATE RULE*: If score < 2, cap total at 6/16.

---

CRITERION B — IDENTIFICATION (3 points)
----------------------------------------
Number of distinct, relevant issues/problems named:
• 3 points: 3+ relevant issues (workflow inefficiencies, redundancy, lack of 
  interoperability, misalignment with mission, regulatory constraints, etc.)
• 2 points: 2 relevant issues
• 1 point: 1 relevant issue
• 0 points: None

---

CRITERION C — SPECIFICITY (2 points)
--------------------------------------
Does at least one issue include a specific qualifier showing understanding of 
WHY it matters?

• 2 points: Yes, one+ issue has a specific qualifier (e.g., "workflow 
  inefficiency [which leads to] duplicate data entry")
• 1 point: Issues named but explanations are generic
• 0 points: Purely list-like labels with no context

---

CRITERION D — LINKAGE (3 points)
---------------------------------
Clear causal/mechanistic connection between issues and how BPR addresses them:

• 3 points: Clear mechanistic linkage for 2+ issues OR strong linkage for 1 
  issue
• 2 points: Clear linkage for 1 issue
• 1 point: Vague/partial linkage
• 0 points: No linkage

---

=== CRITICAL GRADING RULES ===

1. SUBSTANCE OVER FORM
   - Student uses different terminology? Give credit if concept is present
   - "ensure workflows fit new system" = "As-Is/Should-Be framing" ✓
   - "remove waste" = "optimize efficiency" ✓
   - Graduate students earn credit for substance, not checkbox wording

2. AVOID KEYWORD GATING
   - Do NOT penalize for missing "ROI", "interoperability", "As-Is/Should-Be"
   - DO credit equivalent concepts in any form

3. ADDRESSING COMMON ERRORS
   - ERROR: "No term 'interoperability', so NO" → WRONG
     CORRECT: Give partial/YES if equivalent concept present
   
   - ERROR: "Only 3 sentences; should be 4-5. Low score" → WRONG
     CORRECT: Evaluate IDEAS only, ignore length
   
   - ERROR: "Didn't say As-Is/Should-Be, so 0 understanding" → WRONG
     CORRECT: Accept "redesign workflows" as equivalent

4. GRADUATE STANDARD
   Different phrasing ≠ different understanding. Judge substance.

---

=== ANCHOR EXAMPLES ===

EXAMPLE 1 — EXCELLENT (16/16)
"We do Business Process Re-engineering when implementing an EHR to make sure 
our workflows fit the new system. If we only copy old processes, we might keep 
the same problems. BPR helps us remove waste and smooth information flow. This 
makes it easier for staff to use the EHR and provides better care for patients."

Grading:
✓ Criterion A: "ensure workflows fit" (causal) + 4 effects = 8/8
✓ Criterion B: copying problems (1) + workflows need fit (2) + waste (3) = 3/3
✓ Criterion C: "keeps same problems" qualifier = 2/2
✓ Criterion D: redesign → waste removal → flow → adoption = 3/3
TOTAL: 16/16 (No As-Is/Should-Be, no ROI, but excellent understanding)

EXAMPLE 2 — GOOD (~13/16)
"BPR ensures workflows fit the EHR system. New processes improve data accuracy,
enable interoperability, and reduce costs. Staff adapt better to the system."

Grading: ~13/16 (clear causal role, multiple benefits, some linkage)

EXAMPLE 3 — POOR (~4/16)
"BPR is needed because it improves the EHR implementation."

Grading: 2/8 (Minimal, generic) + 0/3 + 0/2 + 0/3 = 2/16 initially, 
capped at 6 due to gate rule

---

=== OUTPUT FORMAT ===

Return ONLY valid JSON:
{
  "student_file": "<filename>",
  "criterion_scores": [
    {"criterion_id": "A", "awarded_points": <0-8>, "justification": "<30 words>"},
    {"criterion_id": "B", "awarded_points": <0-3>, "justification": "<30 words>"},
    {"criterion_id": "C", "awarded_points": <0-2>, "justification": "<30 words>"},
    {"criterion_id": "D", "awarded_points": <0-3>, "justification": "<30 words>"}
  ],
  "total_points": <sum>,
  "overall_feedback": "<2 sentences>"
}
"""


def get_api_key() -> str:
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        print("ERROR: OPENAI_API_KEY not set. Please export it first:")
        print('  export OPENAI_API_KEY="sk-..."')
        sys.exit(1)
    return key


def load_quiz1_data() -> list[dict[str, Any]]:
    """Load all Quiz 1 data from the comparison Excel file."""
    excel_path = Path(
        "/Users/dereklee/Desktop/DS549/BU MET/fall 2025 cs 581 quiz and assignment data"
        "/Quiz 1/CS 581 Quiz 1 AI vs Human Anonymized.xlsx"
    )
    
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}")
        sys.exit(1)
    
    wb = openpyxl.load_workbook(str(excel_path))
    ws = wb["Quiz 1 Anonymized Results"]
    
    submissions = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        try:
            student_num = float(row[0]) if row[0] is not None else None
            ai_score_old = float(row[1]) if row[1] is not None else None
            human_score = float(row[2]) if row[2] is not None else None
            student_answer = str(row[6]).strip() if row[6] is not None else ""
            
            if student_num and ai_score_old and human_score and student_answer:
                submissions.append({
                    "student_id": int(student_num),
                    "ai_score_old": ai_score_old,
                    "human_score": human_score,
                    "student_answer": student_answer,
                    "row_idx": row_idx,
                })
        except (ValueError, TypeError, IndexError):
            pass
    
    return submissions


def grade_submission_with_new_prompt(
    student_answer: str,
    api_key: str,
) -> dict[str, Any] | None:
    """
    Call OpenAI API with the new Quiz 1 BRP prompt.
    Returns the parsed grade JSON or None if error.
    """
    client = openai.OpenAI(api_key=api_key)

    user_message = (
        "Grade the student's response to the question: "
        '"Why do we need to do Business Process Re-engineering '
        'as a part of implementing an EHR?"\n\n'
        f"STUDENT ANSWER:\n{student_answer}"
    )

    model_name = MODEL_ONLY
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": QUIZ_1_BPR_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=800,
        )
    except Exception as e:
        if is_nonrecoverable_api_error(e):
            print(f"\nNonrecoverable API error with model {model_name}: {e}")
            return None
        print(f"\nAPI Error: {e}")
        return None

    raw_response = response.choices[0].message.content.strip()

    # Try to parse JSON from response
    try:
        # Try direct JSON parse
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    
    print(f"\nFailed to parse JSON from response:\n{raw_response[:200]}")
    return None


def extract_new_ai_score(grade_result: dict[str, Any]) -> float | None:
    """Extract the final score from the grading result."""
    if not grade_result:
        return None
    
    if "total_points" in grade_result:
        return float(grade_result["total_points"])
    
    # Fallback: sum criterion scores
    if "criterion_scores" in grade_result:
        total = sum(
            float(c.get("awarded_points", 0))
            for c in grade_result["criterion_scores"]
        )
        return total if total > 0 else None
    
    return None


def compute_confidence(grade_result: dict[str, Any]) -> float:
    """Estimate model confidence from criterion scores (0.0-1.0)."""
    if not grade_result or "criterion_scores" not in grade_result:
        return 0.0

    scores = {c["criterion_id"]: float(c.get("awarded_points", 0)) for c in grade_result["criterion_scores"]}

    # Normalize each criterion to 0..1 weight
    a_score = min(scores.get("A", 0) / 8.0, 1.0)
    b_score = min(scores.get("B", 0) / 3.0, 1.0)
    c_score = min(scores.get("C", 0) / 2.0, 1.0)
    d_score = min(scores.get("D", 0) / 3.0, 1.0)

    # Weighted average emphasizing core reasoning
    confidence = a_score * 0.4 + b_score * 0.2 + c_score * 0.2 + d_score * 0.2

    # penalize very low total points further to reflect uncertainty
    total_points = scores.get("A", 0) + scores.get("B", 0) + scores.get("C", 0) + scores.get("D", 0)
    if total_points <= 6:
        confidence = min(confidence, 0.4)

    return max(0.0, min(confidence, 1.0))


def compute_review_risk(
    grade_result: dict[str, Any],
    old_ai: float | None = None,
    new_ai: float | None = None,
    human_score: float | None = None,
) -> float:
    """
    Compute a risk score for whether human review is needed.
    
    Signals:
      - Confidence: Strength of criterion scoring (50%)
      - Completeness: How well rubric coverage (30%)
      - Edge penalty: Extreme scores (<= 4 or >= 15) (flat +0.2)
    
    Note: Drift signal (old_ai vs new_ai) omitted for deployment compatibility.
    """
    if not grade_result:
        return 1.0

    confidence = compute_confidence(grade_result)

    scores = {c["criterion_id"]: float(c.get("awarded_points", 0)) for c in grade_result.get("criterion_scores", [])}
    total_points = scores.get("A", 0) + scores.get("B", 0) + scores.get("C", 0) + scores.get("D", 0)
    normalized_total = min(total_points / 16.0, 1.0)

    edge_risk = 0.0
    if new_ai is not None and (new_ai <= 4 or new_ai >= 15):
        edge_risk = 0.2

    # Mix signals: weak confidence + low completeness + edge extremes
    # (Drift omitted for production deployment where old_ai unavailable)
    risk = (1.0 - confidence) * 0.50 + (1.0 - normalized_total) * 0.30 + edge_risk
    return max(0.0, min(risk, 1.0))


def needs_human_review(risk: float) -> bool:
    """Rule to determine if example goes for human review."""
    return risk >= 0.45


def main():
    print("=" * 80)
    print("QUIZ 1 BPR GRADING RECALIBRATION")
    print("=" * 80)
    print("\nLoading Quiz 1 data...")
    
    submissions = load_quiz1_data()
    print(f"Loaded {len(submissions)} submissions\n")
    
    api_key = get_api_key()
    
    print("Grading with new prompt (this may take a minute)...\n")
    print(f"{'Student':<8} {'Old AI':<8} {'New AI':<8} {'Human':<8} {'Gap (Old)':<12} {'Gap (New)':<12} {'Risk':<6} {'Conf':<6} {'Review':<6}")
    print("-" * 110)
    
    results = []
    old_gaps = []
    new_gaps = []
    
    for i, sub in enumerate(submissions, 1):
        student_id = sub["student_id"]
        old_ai = sub["ai_score_old"]
        human = sub["human_score"]
        answer = sub["student_answer"]
        
        # Grade with new prompt
        grade_result = grade_submission_with_new_prompt(answer, api_key)
        new_ai = extract_new_ai_score(grade_result) or old_ai  # fallback if parse fails

        risk = compute_review_risk(grade_result, old_ai, new_ai)
        confidence = compute_confidence(grade_result) if grade_result else 0.0
        audit_flag = needs_human_review(risk)

        old_gap = old_ai - human
        new_gap = new_ai - human
        old_gaps.append(old_gap)
        new_gaps.append(new_gap)

        # Store result
        results.append({
            "student_id": student_id,
            "ai_score_old": old_ai,
            "ai_score_new": new_ai,
            "human_score": human,
            "gap_old": old_gap,
            "gap_new": new_gap,
            "risk": risk,
            "confidence": confidence,
            "needs_human_review": audit_flag,
            "grade_result": grade_result,
        })
        
        # Print row
        old_gap_str = f"{old_gap:+.1f}" if old_gap != 0 else "0.0"
        new_gap_str = f"{new_gap:+.1f}" if new_gap != 0 else "0.0"
        review_str = 'YES' if audit_flag else 'NO'
        print(
            f"{student_id:<8.0f} {old_ai:<8.0f} {new_ai:<8.1f} {human:<8.0f} "
            f"{old_gap_str:<12} {new_gap_str:<12} {risk:<6.2f} {confidence:<6.2f} {review_str:<6}"
        )
        
        # Print progress
        if i % 5 == 0:
            print(f"  ... progress: {i}/{len(submissions)}")
    
    # Calculate statistics
    print("\n" + "=" * 80)
    print("CALIBRATION RESULTS")
    print("=" * 80)
    
    mean_old_gap = statistics.mean(old_gaps)
    mean_new_gap = statistics.mean(new_gaps)
    stdev_old_gap = statistics.stdev(old_gaps) if len(old_gaps) > 1 else 0
    stdev_new_gap = statistics.stdev(new_gaps) if len(new_gaps) > 1 else 0
    
    improvement = abs(mean_old_gap) - abs(mean_new_gap)
    improvement_pct = 100 * improvement / abs(mean_old_gap) if mean_old_gap != 0 else 0
    
    print(f"\nOLD PROMPT (AI vs Human):")
    print(f"  Mean gap: {mean_old_gap:.2f} (AI tends to {'underscore' if mean_old_gap < 0 else 'overscore'})")
    print(f"  Std dev:  {stdev_old_gap:.2f}")
    print(f"  Range:    {min(old_gaps):.1f} to {max(old_gaps):.1f}")
    
    print(f"\nNEW PROMPT (AI vs Human):")
    print(f"  Mean gap: {mean_new_gap:.2f} (AI tends to {'underscore' if mean_new_gap < 0 else 'overscore'})")
    print(f"  Std dev:  {stdev_new_gap:.2f}")
    print(f"  Range:    {min(new_gaps):.1f} to {max(new_gaps):.1f}")
    
    print(f"\nIMPROVEMENT:")
    print(f"  Bias reduced by:     {improvement:.2f} points ({improvement_pct:.1f}%)")
    print(f"  Variance reduced by: {stdev_old_gap - stdev_new_gap:.2f} points")
    
    # Check if we met the goal
    if abs(mean_new_gap) < 0.5:
        print(f"\n✅ SUCCESS: New gap ({abs(mean_new_gap):.2f}) < target (0.5)")
    else:
        print(f"\n⚠️  Gap still high: {abs(mean_new_gap):.2f} (target: <0.5)")
    
    # Save detailed results
    output_file = Path(__file__).parent / "quiz1_regrade_results.json"
    with output_file.open("w") as f:
        json.dump({
            "summary": {
                "total_submissions": len(submissions),
                "mean_gap_old": mean_old_gap,
                "mean_gap_new": mean_new_gap,
                "improvement": improvement,
                "improvement_pct": improvement_pct,
            },
            "results": results,
        }, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
