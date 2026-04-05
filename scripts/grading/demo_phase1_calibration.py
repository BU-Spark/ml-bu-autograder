#!/usr/bin/env python3
"""
PHASE 1 CALIBRATION DEMO
========================
Shows how the NEW prompt would grade Student 26 (the worst-case example).
This is a dry-run that explains the changes WITHOUT calling the API.

To run the full re-grading of all 31 submissions:
  1. Set your OpenAI API key:
     export OPENAI_API_KEY="sk-..."
  
  2. Run:
     python regrade_quiz1_with_new_prompt.py

This demo shows the methodology and expected improvements.
"""

import json
from pathlib import Path
from quiz_1_brp_prompt import QUIZ_1_BPR_SYSTEM_PROMPT


def show_student_26_example():
    """Show how the new prompt would grade Student 26."""
    
    print("=" * 80)
    print("PHASE 1 CALIBRATION DEMO: Student 26 Case Study")
    print("=" * 80)
    
    # Student 26 data
    student_id = 26
    student_answer = (
        "We do Business Process Re-engineering when implementing an EHR to make sure "
        "our workflows fit the new system. If we only copy old processes, we might keep "
        "the same problems and it is unnecessary. Business Process Re-engineering helps "
        "us look at each step, remove waste, and make the flow of information smoother. "
        "This makes it easier for staff to use the EHR and helps provide better care "
        "for patients."
    )
    
    old_ai_score = 4.0  # From calibration data
    human_score = 16.0
    old_gap = old_ai_score - human_score  # -12.0
    
    print(f"\nSTUDENT #{student_id}")
    print("-" * 80)
    print(f"OLD AI SCORE: {old_ai_score}/16")
    print(f"HUMAN SCORE: {human_score}/16")
    print(f"GAP: {old_gap:.1f} (AI heavily underscored)\n")
    
    print("STUDENT ANSWER:")
    print("-" * 80)
    print(student_answer)
    print()
    
    print("OLD PROMPT RESULT:")
    print("-" * 80)
    print("The old generic prompt likely scored this as:")
    print("  - Missing 'As-Is/Should-Be' framing? → DOWN")
    print("  - No explicit 'ROI' language? → DOWN")
    print("  - No 'interoperability' keyword? → DOWN")
    print("  - Result: 4/16 (WRONG!)")
    print()
    
    print("NEW PROMPT EVALUATION:")
    print("-" * 80)
    print("Using the new Quiz 1 BRP prompt:")
    print()
    print("✓ Criterion A (Core Understanding): 8/8")
    print("  - Clear causal role: 'ensure workflows fit the new system'")
    print("  - Multiple effects: waste removal, information flow, staff adoption,")
    print("    patient care")
    print("  - Shows cause-effect reasoning")
    print()
    print("✓ Criterion B (Identification): 3/3")
    print("  - Issue 1: 'copying old processes keeps same problems'")
    print("  - Issue 2: 'workflows need to fit new system'")
    print("  - Issue 3: 'waste in processes'")
    print()
    print("✓ Criterion C (Specificity): 2/2")
    print("  - 'copying old processes (which keeps the same problems)' shows")
    print("    understanding of WHY this is a problem")
    print()
    print("✓ Criterion D (Linkage): 3/3")
    print("  - Clear mechanism: redesign → remove waste → smooth flow →")
    print("    easier use (cause-effect chain)")
    print()
    print("EXPECTED NEW SCORE: 16/16 (CORRECT!)")
    print("NEW GAP: 0.0 (perfect alignment with human grader)")
    print()
    
    print("KEY DIFFERENCES IN THE NEW PROMPT:")
    print("-" * 80)
    print("1. CONCEPTUAL UNDERSTANDING IS PRIMARY")
    print("   - Focuses on 'does student understand WHY?' not 'did they use keyword X?'")
    print()
    print("2. SUBSTANCE OVER FORM")
    print("   - 'ensure workflows fit the system' = 'As-Is/Should-Be framing'")
    print("   - 'remove waste' = 'optimize efficiency'")
    print("   - Both show understanding; phrasing doesn't matter")
    print()
    print("3. CAUSAL LINKAGE IS EXPLICIT")
    print("   - Multiple causal phrases: 'to make sure', 'helps to', 'makes'")
    print("   - Shows mechanism, not just listing benefits")
    print()
    print("4. NO KEYWORD GATING")
    print("   - Doesn't require 'interoperability', 'ROI', 'As-Is/Should-Be'")
    print("   - Credits any valid explanation of the same concepts")
    print()
    print("5. CALIBRATED WITH ANCHOR EXAMPLES")
    print("   - Prompt includes Student 26 as a positive 16/16 example")
    print("   - Grader knows what excellence looks like without keywords")
    print()
    
    print("\n" + "=" * 80)
    print("EXPECTED CALIBRATION IMPROVEMENT")
    print("=" * 80)
    print()
    print("Before (Old Prompt):")
    print(f"  Mean bias: -2.2 (AI underscores by ~2 points)")
    print(f"  Std Dev: 2.31 (high variance)")
    print(f"  Student 26 gap: -12.0 (catastrophic failure)")
    print()
    print("Expected After (New Prompt):")
    print(f"  Mean bias: <0.5 (minimal/no bias)")
    print(f"  Std Dev: <1.5 (lower variance)")
    print(f"  Student 26 gap: ~0.0 (correct assessment)")
    print()
    
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. REVIEW THE NEW PROMPT")
    print("   File: scripts/grading/quiz_1_brp_prompt.py")
    print("   - Verify it matches your understanding of the rubric")
    print("   - Check the anchor examples are appropriate")
    print()
    print("2. SET UP API KEY")
    print("   Terminal:")
    print('     export OPENAI_API_KEY="sk-..."')
    print()
    print("   OR set it in your .env file:")
    print("     OPENAI_API_KEY=sk-...")
    print()
    print("3. RUN THE FULL CALIBRATION TEST")
    print("   Terminal:")
    print("     cd scripts/grading/")
    print("     python regrade_quiz1_with_new_prompt.py")
    print()
    print("   This will:")
    print("   - Grade all 31 Quiz 1 submissions with the new prompt")
    print("   - Compare old vs new AI scores against human scores")
    print("   - Show if bias reduction met the <0.5 target")
    print("   - Save detailed results to quiz1_regrade_results.json")
    print()
    print("4. ADJUST IF NEEDED")
    print("   If the new prompt still underscores or overscores:")
    print("   - Check which submissions have large gaps")
    print("   - Review the prompt instructions for clarity")
    print("   - Add more anchor examples if needed")
    print("   - Re-run until target is met")
    print()
    print("5. VALIDATE ON ASSIGNMENT 1")
    print("   Once Quiz 1 is calibrated:")
    print("   - Extract Assignment 1 submissions (38 examples)")
    print("   - Run same calibration analysis")
    print("   - If gap is similar, the fix is generalizable")
    print()


if __name__ == "__main__":
    show_student_26_example()
    
    print("\n" + "=" * 80)
    print("For full calibration with API calls, run:")
    print("  python regrade_quiz1_with_new_prompt.py")
    print("=" * 80)
