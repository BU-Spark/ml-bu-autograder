# Calibration Analysis: Quiz 1 AI vs Human Grading

**Date**: March 26, 2026  
**Data Source**: Fall 2025 Quiz 1 submissions (31 students)

---

## Key Finding: AI SYSTEMATICALLY UNDERSCORE

### Score Statistics
| Metric | AI Scores | Human Scores | Gap |
|--------|-----------|--------------|-----|
| **Mean** | 12.9 | 15.1 | **-2.2** ⚠️ |
| **Median** | 14.0 | 16.0 | **-2.0** |
| **Std Dev** | 2.31 | 1.15 | |
| **Range** | 4–15 | 12–16 | |

### Distribution Buckets
```
AI Scores:              Human Scores:
 0- 3: 0                 0- 3: 0
 4- 7: 1                 4- 7: 0
 8-11: 3                 8-11: 0
12-15: 27               12-15: 15 (includes some 16s)
```

---

## Problem Analysis

### 1. **Systematic Underscoring (-2.2 point bias)**
- AI averages 12.9/16, humans average 15.1/16
- This is a **~15% underestimate** across the board
- Likely causes:
  - ✗ Rubric threshold misinterpretation (AI setting bar too high)
  - ✗ Overly strict evaluation of "specificity" or "examples"
  - ✗ Missing context from instructor notes that humans use

### 2. **High Variance in AI Scoring (StdDev 2.31 vs 1.15)**
- AI is more volatile (poor calibration)
- Humans cluster tightly in 12-16 range (well-calibrated)
- 13% of submissions have gaps >3 points (outliers)

### 3. **Ceiling Effect Missing**
- Humans award full score (16) for excellent work
- AI maxes out at 15, suggesting it's conservative on the "perfect" criterion

---

## Files to Use for Calibration

### ✅ **HIGH PRIORITY - Use These**

1. **Quiz 1 Data (31 submissions)**
   - Location: `fall 2025 cs 581 quiz and assignment data/Quiz 1/`
   - Files:
     - `CS 581 Quiz 1 AI vs Human Anonymized.xlsx` — Ground truth comparison
     - `24fallmetcs581_m1 Quiz 1.xlsx` — Spring 2025 submissions (additional 40+ samples)
   - **Action**: Use all responses (both semesters) to fix the -2.2 point bias

2. **Assignment 1: Workflow & BPR (38 submissions)**
   - Location: `pre- fall 2025 cs581_quiz_and_assignment_data/Assignment 1 - Workflow & BPR/`
   - Subdirectory: `24fallmetcs581_m1 submissions and rubrics/`
   - **Status**: 38 graded submissions (Fall 2024) + rubric
   - **Action**: Extract and analyze score distribution

3. **Spring 2026 Curated Examples**
   - Location: `Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/`
   - Status: Manually tagged (Good/Bad) with grades
   - **Action**: Use as anchor points for boundary testing

### ⚠️ **MEDIUM PRIORITY - Leverage as Context**

4. **Fall 2025 Refined Rubrics (JSON)**
   - Location: `fall 2025 cs 581 quiz and assignment data/New Refined Rubrics/`
   - Files: `quiz_1/rubric_refined.txt`, `quiz_2/rubric_refined.txt`, `quiz_4/rubric_refined.txt`
   - **Action**: Cross-check your rubric interpretation against these

5. **Spring 2025 Submission Data**
   - Location: `pre- fall 2025 cs581_quiz_and_assignment_data/Spring 2025/`
   - Quiz 1, 2, 3 with sample answers
   - **Action**: Validate that your fix applies across semesters

---

## Recommended Calibration Strategy

### Phase 1: Fix the Systematic Bias (This Week)
1. **Root cause analysis**: 
   - Review 5 submissions where AI gave 4-7 (why so low?)
   - Review 5 submissions where AI gave 12-13 and humans gave 15-16 (what's missing?)
   
2. **Adjust promptry/rubric thresholds** to reduce the -2.2 bias:
   - If due to overly strict criteria → relax boundaries
   - If due to missing context → add rubric notes to the grader prompt

3. **Retest** on all 31 Quiz 1 submissions

### Phase 2: Validate Across Assignments (Next Step)
- Extract Assignment 1 AI vs Human if available
- Check if -2.2 bias exists across different assignment types
- Synthesize new data only if discovered gaps (e.g., no submissions in 4-8 range)

### Phase 3: Build Training Set
- Combine best Quiz 1 + Assignment 1 data (~70+ examples)
- Use good/bad examples from Spring 2026 as anchor points
- Freeze rubrics once bias is <0.5 points

---

## Don't Need to Synthesize Yet

**Reason**: You have 31+ real submissions with human ground truth already. Synthesizing now would:
- ❌ Add noise before you understand the systematic bias
- ❌ Dilute the leverage of real rubric feedback
- ❌ Miss the specific misconceptions your AI is making

**Only synthesize IF**:
- After fixing the -2.2 bias, you discover gaps (e.g., need examples of score 0-3, 9-11 range)
- You need coverage of specific scenarios not in your historical data

---

## Next Steps

1. ✅ **Review underscored submissions** (4 cases with gap >3)
2. ✅ **Adjust grader prompt/thresholds** to target -0.5 bias
3. ✅ **Retest on all 31 Quiz 1 submissions**
4. ✅ **Extract Assignment 1 scores** and run same analysis
5. ⏭️ **Synthesize only if needed** (after Phase 1 validation)

