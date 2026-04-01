# Calibration Data Inventory & Recommendations

**Generated**: March 26, 2026  
**Status**: Ready to use (do NOT synthesize new data yet)

---

## Tier 1: USE IMMEDIATELY (Gold Standard)

### 📊 Fall 2025 Quiz 1 Comparison (AI vs Human)
- **Location**: `fall 2025 cs 581 quiz and assignment data/Quiz 1/`
- **File**: `CS 581 Quiz 1 AI vs Human Anonymized.xlsx`
- **Sample Size**: 31 graded submissions
- **Ground Truth**: Yes (human instructor grades available)
- **Issue Found**: AI systematically underscores by -2.2 points
- **Priority**: 🔴 **CRITICAL** — Use to fix the -12 to -4 point gaps immediately
- **Action**: 
  - [ ] Review Student 26 (AI=4, Human=16) to understand keyword-matching fallacy
  - [ ] Review Student 12, 24, 27 to calibrate partial credit scoring
  - [ ] Update prompt to prioritize **conceptual understanding** over keyword matching
  - [ ] Re-evaluate all 31 Quiz 1 responses after fix

**Files in this folder**:
```
CS 581 Autograder Quiz 1 - Semantic Search.xlsx
  → Contains semantic retrieval results (useful for validation)
CS 581 Quiz 1 AI vs Human Anonymized - Prompt Engineering Tests.xlsx
  → Shows different prompt variations (reference for your prompts)
CS 581 Quiz 1 AI vs Human Anonymized.xlsx
  → THE MAIN FILE - Use this
```

---

### 📚 Assignment 1: Workflow & BPR (Pre-Fall 2025)
- **Location**: `pre- fall 2025 cs581_quiz_and_assignment_data/Assignment 1 - Workflow & BPR/`
- **Subdirectory**: `24fallmetcs581_m1 submissions and rubrics/`
- **Sample Size**: 38 student submissions (student 1–38 folders)
- **Available**: 
  - [ ] Student PDFs/PPTs with grades
  - [ ] Detailed feedback (in `all student scores and feedback log.xlsx`)
  - [ ] Rubric (see `CS581 Assignment1_Description.pdf`)
- **Ground Truth**: Yes (instructor scores + feedback)
- **Priority**: 🟡 **HIGH** — Extract and analyze after Quiz 1 fix
- **Action**:
  - [ ] Extract A1 submission grades from the feedback log
  - [ ] Run same calibration analysis (AI vs Human on assignments)
  - [ ] Check if -2.2 bias exists across assignment format (visual + text) or is Quiz-specific

---

## Tier 2: USE FOR VALIDATION (Good Calibration Anchors)

### ✅ Spring 2026 Curated Examples
- **Location**: `Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/`
- **Structure**:
  ```
  Assignment 1_ Diagram & Text/
    ├── Student 1 - Good Example/     → grades.xlsx
    ├── Student 2 - Good Example/     → grades.xlsx
    └── Student 3 - Bad Example/      → grades.xlsx
  ```
- **Sample Size**: 3 curated examples (intentionally diverse quality)
- **Ground Truth**: Instructor-tagged labels + grades
- **Priority**: 🟢 **MEDIUM** — Use after Phase 1 to anchor score boundaries
- **Action**:
  - [ ] Grade these 3 examples with your fixed grader
  - [ ] Verify AI scores align with tags (Good→14-16, Bad→4-8)
  - [ ] If mismatch, feed back to rubric/prompt refinement

---

### 📋 Fall 2025 Refined Rubrics (JSON)
- **Location**: `fall 2025 cs 581 quiz and assignment data/New Refined Rubrics/`
- **Files**: 
  ```
  quiz_1/rubric_refined.txt      ← Reference rubric used for Fall 2025 grading
  quiz_2/rubric_refined.txt      ← Additional quiz data
  quiz_4/rubric_refined.txt      ← Additional quiz data
  ```
- **Content**: Detailed operational scoring mapping (e.g., "6 points: Student names 3+ distinct issues")
- **Ground Truth**: Used by instructors for Fall 2025 calibration
- **Priority**: 🟢 **MEDIUM** — Cross-check your rubric interpretation
- **Action**:
  - [ ] Verify your grader prompt aligns with these operational thresholds
  - [ ] Use as reference to prevent overly strict or loose scoring boundaries

---

## Tier 3: REFERENCE MATERIALS (Context Only)

### 📚 Spring 2025 Quiz & Assignment Data
- **Location**: `pre- fall 2025 cs581_quiz_and_assignment_data/`
- **Sample Size**: ~30-40 per quiz/assignment
- **Priority**: 🔵 **LOW** — Use only after Tier 1 is fixed
- **Action**:
  - [ ] Extract Spring 2025 Quiz 1 scores if available
  - [ ] Verify fix applies across semesters

### 📖 Lecture Materials & Sample Answers
- **Location**: `pre- fall 2025 cs581_quiz_and_assignment_data/Quiz_1/Quiz 1 Short Answer Questions and Sample Answers.docx`
- **Content**: Instructor's model answers for context
- **Priority**: 🔵 **LOW** — Reference to understand what "good" should sound like

---

## 🚫 DO NOT DO THIS YET

❌ **Synthesize (generate) new student submissions**

**Why**: 
- You have 31+ real submissions with ground truth
- Synthesized data will introduce noise before you understand the systematic bias
- Better to fix the -2.2 point bias on real data first

**When to synthesize** (if needed):
- After Phase 1 validation, if you discover score distribution gaps
- E.g., "Do we have enough examples in the 0-5 range? In the 9-11 range?"
- Only synthesize those specific gaps, not wholesale replacement

---

## Recommended Work Plan

### Phase 1: Fix the Bias (This Week)
**Goal**: Reduce AI underscore from -2.2 to <+0.5

1. **Analysis** (done ✅)
   - Identified -2.2 systematic bias
   - Found 7 submissions with large gaps
   - Root cause: AI uses keyword-matching, not conceptual eval

2. **Intervention** (next)
   - Revise grader prompt/rubric to prioritize **understanding** over keywords
   - Add explicit instruction: "Prefer higher scores when conceptually correct"
   - Include Student 26 as an anchor example (16/16, no As-Is/Should-Be language)
   
3. **Validation** (next)
   - Re-grade all 31 Quiz 1 submissions with new prompt
   - Measure: Is gap now < ±1.0?

### Phase 2: Validate Across Assignments (End of Week)
**Goal**: Confirm fix generalizes to different assignment formats

1. Extract A1 grades from feedback log
2. Run same calibration analysis
3. If gap consistent, use same fix
4. If different, investigate format-specific issues

### Phase 3: Build Training Set (Next Week)
**Goal**: Freeze rubrics and create final calibration dataset

1. Combine Quiz 1 (31) + Assignment 1 (38) = 69 real examples
2. Add Spring 2026 curated examples as anchors (3)
3. Use refined rubrics as reference
4. Only synthesize if distribution gaps discovered

---

## File Summary Table

| File | Location | Samples | Ground Truth | Status | Use |
|------|----------|---------|--------------|--------|-----|
| **Quiz 1 AI vs Human** | Q1 folder | 31 | Yes | Ready | Phase 1 |
| **Assignment 1 Submissions** | Pre-F25/A1/24fall | 38 | Yes | Ready | Phase 2 |
| **Spring 2026 Examples** | S26/Assignment Examples | 3 | Yes | Ready | Phase 1 validation |
| **Refined Rubrics** | F25/New Refined | 3 | Yes | Ready | Reference |
| **Spring 2025 Quizzes** | Pre-F25 | ~40 | Yes | Ready | Stretch goal |

---

## Success Metrics

- [ ] **Quiz 1**: Mean AI-Human difference < ±0.5 (was -2.2)
- [ ] **Assignment 1**: Mean AI-Human difference < ±0.5 (to be measured)
- [ ] **Spring 2026 Examples**: AI classifies Good/Bad correctly
- [ ] **Robustness**: Same fix works across quiz and assignment questions

---

