# Root Cause Analysis: Why AI Underscore

## Critical Finding: Student 26 is a Case Study

**Student 26**: AI=4/16 | Human=16/16 | **Gap: -12 (catastrophic failure)**

### The Answer (Student 26):
```
We do Business Process Re-engineering when implementing an EHR to make sure 
our workflows fit the new system. If we only copy old processes, we might keep 
the same problems and it is unnecessary. Business Process Re-engineering helps 
us look at each step, remove waste, and make the flow of information smoother. 
This makes it easier for staff to use the EHR and helps provide better care 
for patients.
```

### Human's Evaluation:
> "Your answer is **excellent** and thoroughly explains the necessity of Business 
> Process Re-engineering (BPR) during Electronic Health Record (EHR) implementation.
>
> - ✅ Identifies the **core reason**: BPR is needed to make sure workflows fit 
>   the new system and avoids copying old processes
> - ✅ Covers the **operational benefits**: Remove waste, smooth information flow
> - ✅ Addresses the **human element**: Easier for staff to use EHR
> - ✅ Covers the **strategic outcome**: Better care for patients"

### What This Tells Us
This answer **hits all 4 rubric dimensions**:
1. ✅ Issues/problems identified (copying old processes = bad)
2. ✅ Breadth of benefits (workflow fit, waste reduction, information flow, staff adoption, patient care)
3. ✅ Depth/mechanism (redesign → removes waste → smoother flow → easier use)
4. ✅ Originality (clearly own words, not verbatim from materials)

**Yet the AI gave 4/16.** This suggests:

---

## Hypothesis 1: The AI Grader is Looking for Specific Keywords

The rubric mentions these key terms:
- "As-Is" and "Should-Be" states
- "ROI" (return on investment)
- "Interoperability"
- "Standardization"

**Student 26's answer doesn't use these exact terms**, so the AI might be pattern-matching keywords rather than evaluating conceptual understanding.

**Evidence**: 
- Student 12 uses "research, population health analytics, billing, inventory, communications, privacy, accountability, AI, clinical care, cost effective, interfaces"
- Human still rated it 14/16 (noted it was "strong" but lacked explicit As-Is/Should-Be framing)
- AI gave it 8/16 (punished for not being "perfect")

---

## Hypothesis 2: The AI Grader is Too Strict on the "Originality" Criterion

The rubric says:
```
2 points (Full): Response is clearly in the student's own words. 
  Overall exact-match similarity <=20% AND no contiguous verbatim phrase 
  >8 words from source material
```

**Possible misinterpretation**: 
- AI might be flagging common healthcare terms ("workflow," "EHR," "standardization") 
  as plagiarism when they're just domain vocabulary
- AI might be overly penalizing grammar/spelling (Student 27 has "low effective" 
  and "flow the regulation" but still got 12/16 from AI, 16/16 from human)

---

## Hypothesis 3: The AI Doesn't Follow the Rubric's Own Guidance

From the rubric's global notes:
> "When in doubt between two adjacent point totals, **prefer awarding the higher 
> value** if the student's conceptual understanding is correct but phrased concisely. 
> Do not penalize minor wording similarity."

**Student 26's answer is:**
- ✅ Conceptually correct
- ✅ Concise (4 sentences as requested)
- ✅ Addresses all criteria

**By the rubric's own guidance, this should score HIGH (14-16), not 4.**

---

## Pattern Across Problem Submissions

| Student | AI Score | Human Score | Issue | Gap |
|---------|----------|--------------|-------|-----|
| **26** | 4 | 16 | Answer is excellent; AI doesn't recognize it | -12 |
| **12** | 8 | 14 | Good answer, lacks As-Is/Should-Be; AI undervalues partial credit | -6 |
| **24** | 10 | 14 | Good answer, lacks strategic framing; AI is too rigid | -4 |
| **27** | 12 | 16 | Good answer with grammar quirks; AI penalizes form over substance | -4 |

**Common Thread**: AI is either:
1. Not reading the answer carefully (keyword matching fallacy)
2. Being overly rigid about what "good" looks like
3. Not following the rubric's own guidance on holistic scoring

---

## What the AI Feedback Shows

Looking at the AI feedback for Student 26 would reveal its reasoning. But based on 
the pattern, we can infer:

**Likely AI Approach**:
```
1. Check for As-Is/Should-Be language → NOT FOUND → Flag as incomplete
2. Check for ROI language → NOT FOUND → Downgrade further
3. Check for "business processes" discussion → NOT FOUND → More downgrade
4. Final score: Fails too many keyword checks → 4/16
```

**What It Should Do**:
```
1. Evaluate core intent: Does student understand why BPR is needed? → YES
2. Count distinct issues identified: At least 1 (copying old processes = bad) → PASS
3. Map to benefit categories: 
   - Operational efficiency (waste removal)
   - Staff adoption (easier to use)
   - Patient care (better outcomes)
   → 3+ categories identified → Full credit on breadth
4. Check mechanism: Does redesign → remove waste → smoother process explain itself? → YES
5. Evaluate originality: Own words, clear phrasing → YES
6. Final: All criteria met → 16/16
```

---

## Implications for Your Grader

**Your current AI grader likely has:**
1. ❌ Overly strict keyword matching (not evaluating intent)
2. ❌ Poor handling of acceptable paraphrasing vs. plagiarism
3. ❌ Ignores the rubric's guidance to "prefer higher scores when conceptually correct"
4. ❌ Treats formatting/grammar as scoring criteria (it's not per the rubric)

**Fix needed**: 
- Rewrite the prompt/rubric interpretation to focus on **conceptual understanding** first
- Apply keywords as **supporting evidence**, not **gatekeeping criteria**
- Explicitly instruct the grader to follow the rubric's guidance on holistic scoring
- Add examples: "Student 26's answer is a 16/16 example—no As-Is/Should-Be framing, but conceptually excellent"

