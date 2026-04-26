# Lessons Learned — GradeAI Pro

**Project:** GradeAI Pro — AI-Powered Automated Grading System  
**Semester:** Spring 2026  
**Team:** Sai Chava  
**Program:** Boston University MET CS / CDS  

---

## Table of Contents

1. [What Worked Well](#1-what-worked-well)
2. [What Did Not Work](#2-what-did-not-work)
3. [Surprising Findings](#3-surprising-findings)
4. [Technical Challenges & How We Solved Them](#4-technical-challenges--how-we-solved-them)
5. [LLM Grading Quality](#5-llm-grading-quality)
6. [Data & Infrastructure Lessons](#6-data--infrastructure-lessons)
7. [Recommendations for Future Teams](#7-recommendations-for-future-teams)
8. [What We Would Do Differently](#8-what-we-would-do-differently)
9. [Open Problems](#9-open-problems)

---

## 1. What Worked Well

### RAG Grounding Significantly Improves Grading Quality

Retrieving relevant lecture content before grading reduced hallucinated credit. Without RAG, the LLM would sometimes award points for vague mentions of concepts that weren't present. With lecture context retrieved from ChromaDB, the LLM could compare the student's explanation to the actual course material and identify gaps more precisely.

**Evidence:** Grading runs with RAG context consistently applied checklist items more strictly than runs without it — scoring 5–10 points lower on average for submissions that paraphrased without depth.

### Policy Caps Prevented Systematic Over-Grading

The LLM tends to be generous with PARTIAL credit for vague mentions. Policy caps (e.g., cap at 78% if no workflow diagram is present) acted as a safety net that caught the most common over-grading pattern.

Without policy caps, the average score in early testing was ~82/100. With caps enabled, it dropped to ~74/100 — which matched instructor expectations more closely.

### Vision AI Description Was the Key to Multimodal Grading

Before adding Vision AI, grading was based only on extracted text. Students who included diagrams and architecture figures but minimal text scored poorly because the LLM couldn't "see" the visual content. After adding image description:
- Submissions with strong diagrams but thin text scored 10–15 points higher
- Evidence references became richer and more specific
- The LLM could evaluate the quality of flowcharts and architecture diagrams

### Multi-Provider Architecture Enabled Cost Control

Supporting OpenAI, Gemini, and Anthropic in parallel was the right call. During development:
- We used Gemini for rapid testing (cheap, fast)
- We used Claude Sonnet for final grading runs (highest quality)
- We used gpt-4o-mini for prototype demos (reliable, well-documented)

Switching providers required changing only one dropdown — zero code changes for the instructor.

### Flask Blueprint Architecture Scaled Well

Splitting the web app into 5 blueprints (grading, lecture, rubric, library, reports) made the codebase maintainable. Adding the quiz batch grading feature in a later sprint required changes only in `blueprints/grading.py` — no risk of breaking other features.

### Subprocess-Based Pipeline (Web → CLI) Was the Right Isolation Strategy

Initially considered importing the grading module directly in the Flask blueprint. Switched to subprocess invocation of `run_pipeline.py` — this proved invaluable:
- When grading crashed (out of memory on a large PDF), it crashed in the subprocess, not the web server
- Logs from the subprocess could be streamed to the browser in real time
- CLI remained independently usable for automation

### AI Rubric Generation Was Well-Received

Instructors appreciated having a starting rubric generated from the assignment text. Even when they edited the result, having a structured starting point saved significant time compared to building a rubric from scratch.

---

## 2. What Did Not Work

### Automated Test Suite: Never Built

This is the single biggest gap. The grading algorithm has:
- Grade band mapping
- Policy cap logic
- Checklist percentage calculation
- Rubric parsing (3 methods)

All of this was tested manually. Manual testing caught issues but slowly. A regression introduced in one refactor (a PARTIAL weight change from 0.5 to 0.67) was not caught for several test runs.

**Impact:** Medium. Grading outputs may contain bugs that no test caught.  
**Fix:** Add pytest tests for `grade_submission.py` as the first task next semester.

### Batch Grading Performance (No Async Processing)

Grading 10+ students in batch blocks the Flask worker for 20–30 minutes. During testing, this caused browser timeouts and unclear error messages when grading a large batch.

**What happened:** Students would click "Grade All" for 15 submissions and see a blank progress log after 2 minutes — not because grading failed, but because the browser gave up waiting.

**Attempted fix:** Streaming logs via Server-Sent Events partially helped, but the fundamental issue (synchronous subprocess in Flask worker) remained.

**Proper fix:** Celery + Redis job queue. Each grading run becomes an async task. Progress is polled, not streamed from a blocking call.

### LLM Inconsistency on Short Text Submissions

Submissions with very little extracted text (e.g., a 3-slide deck with mostly images) were graded inconsistently. The LLM sometimes scored them 70/100, sometimes 45/100 on identical re-runs — 25-point variance is unacceptable.

**Root cause:** Small text samples give the LLM very little signal. The score is dominated by luck-of-the-draw prompt sampling at temperature > 0.

**Partial fix:** Added Vision AI description to convert images to text, reducing the variance. But the problem persists for truly sparse submissions.

**Better fix:** Detect low-evidence submissions and flag them for human review rather than auto-grading.

### DOCX Rubric Parsing Failed on Non-Standard Tables

Many professor-authored DOCX rubrics used merged cells, color formatting, and multi-column layouts that Camelot/python-docx couldn't parse reliably. The AI fallback (Claude Haiku) saved roughly 30% of these but still failed on heavily formatted rubrics.

**Impact:** High during initial deployment — instructors had to reformat rubrics manually.

**Fix applied:** Added plain-text regex parser as a middle tier. Instructors learned to use simpler table formats.

**Recommendation:** Build a rubric preview UI showing how the rubric was parsed before grading begins — catches parse failures early.

### Web UI Has No Authentication

The Flask app runs with no login. Anyone who can reach `localhost:5000` can upload student files, trigger expensive API calls, and download grade reports.

This was acceptable for local development but would be a serious problem if deployed on any shared network.

**Fix:** Flask-Login with a simple single-user credential (stored in `.env`) is a half-day implementation. Should be the first thing added before any network deployment.

---

## 3. Surprising Findings

### The LLM Grade Band System Works Better Than Raw Percentages

We initially tried a linear mapping: `checklist_pct × max_points`. The results felt wrong — a 74% and a 75% checklist score gave essentially the same points as a 74% and a 73%. Grade bands (snapping to 75%, 90%, 96.7%, etc.) were added to match how instructors actually think about grades. Once we added bands, instructors stopped arguing with specific point values.

### Lecture Context Sometimes Hurts Grading Quality

When retrieved lecture chunks were only loosely related to the question at hand, the LLM was distracted by irrelevant content and sometimes marked correct student work as wrong. Restricting the L2 distance threshold from 2.0 to 1.5 reduced this problem significantly.

**Lesson:** RAG context should be high-confidence or not included at all. Noisy retrieval is worse than no retrieval.

### Vision AI Cost Was Not a Bottleneck

Initial concern was that describing 10–15 images per student at ~$0.003 each would make grading expensive at scale. In practice, the total Vision AI cost for a 30-student batch was under $1.50 — negligible compared to time savings.

The real cost bottleneck was **Claude Sonnet for grading** — at ~$0.03 per student, 30 students costs ~$0.90. Still acceptable, but scales linearly.

### Students Include FAR More Images Than Expected

Early design assumed 2–3 diagrams per submission. The actual average for project submissions was 8–12 images per student (architecture diagrams, ERDs, process flows, screenshots, charts). Tiling was not originally planned — it became necessary after the first batch of PPTX files overwhelmed the vision API with 2000×1500px architecture diagrams.

### Gemini Embeddings Outperformed Local Sentence Transformers

For lecture retrieval quality, `gemini-embedding-001` (768-dim) produced noticeably better matches than `all-MiniLM-L6-v2` (384-dim) — especially for domain-specific course terminology. The difference was visible in retrieval.jsonl: Gemini matches were more often "on topic" while local embeddings sometimes matched by keyword rather than concept.

---

## 4. Technical Challenges & How We Solved Them

### Challenge: `light-dark()` CSS in draw.io SVG exports

Draw.io exports SVGs with `light-dark(lightValue, darkValue)` CSS function calls for dark/light mode support. GitHub's SVG renderer ignores the `color-scheme: light` hint and renders all colors as dark.

**Solution:** Wrote a Python script with a balanced-parenthesis parser to replace all 275 `light-dark(x, y)` occurrences with just `x` (the light-mode value). A naive regex would fail on `light-dark(rgb(r,g,b), rgb(r,g,b))` because of the nested commas.

### Challenge: Camelot Table Extraction Fails on Complex PDFs

Camelot's lattice method (bordered tables) worked well, but many student submissions used "stream" tables (aligned text without borders) that Camelot couldn't detect.

**Solution:** Added pdfplumber as a second-pass parser for pages where Camelot found 0 tables but the page had clearly tabular text layout. Combined output improved table coverage from ~60% to ~85%.

### Challenge: ChromaDB Collection Already Exists on Re-Index

When re-running the indexing pipeline, ChromaDB complained about duplicate chunk IDs.

**Solution:** Added a `reset_collection` flag (default: False). When True, the collection is deleted and rebuilt from scratch. When False, only new chunks (not already in the collection by ID) are added. Incremental indexing works correctly for adding new lectures.

### Challenge: Flask SSE (Server-Sent Events) Buffering

Browser SSE requires `Content-Type: text/event-stream` and disabling response buffering. On some systems, Flask's debug mode enabled buffering that swallowed SSE events for 30+ seconds.

**Solution:** Added `X-Accel-Buffering: no` response header and switched to `stream_with_context()` for all SSE routes.

### Challenge: Rubric JSON Validation with LLM-Generated Rubrics

LLMs occasionally generated rubrics where criterion points summed to 97 or 103 instead of exactly 100.

**Solution:** Added a post-generation validation step:
1. Check sum of `max_points` == 100
2. If off by ≤ 5%, auto-adjust the first criterion to compensate
3. If off by > 5%, regenerate with an explicit constraint reminder in the prompt

---

## 5. LLM Grading Quality

### Accuracy vs. Human Grader

Informal comparison with instructor-graded samples (Spring 2026, Assignment 1, n=8 students):

| Metric | Value |
|---|---|
| Mean absolute error vs. human grade | 4.2 points (out of 100) |
| Within ±5 points | 6/8 students (75%) |
| Over-graded by >10 points | 1/8 students |
| Under-graded by >10 points | 1/8 students |

The one over-graded student had a strong business analysis section but missing technical components — the LLM gave PARTIAL credit for vague mentions that the instructor marked NO. Policy caps caught the most egregious case.

### Consistency (Re-Run Same Student Twice)

| Model | Mean score difference (same input, 2 runs) |
|---|---|
| gpt-4o-mini | ±3.1 pts |
| gemini-2.5-flash | ±4.8 pts |
| claude-sonnet-4-6 | ±2.3 pts |

Claude Sonnet was most consistent. Temperature was set to 0.3 for all providers — lower temperature reduced variance but increased the risk of systematic bias.

### Best Provider for This Use Case

Based on Spring 2026 testing: **claude-sonnet-4-6 (Anthropic)** produced the most accurate and consistent rubric-based grading. It was also the most expensive. For high-stakes final submissions, use Anthropic. For rapid feedback or quiz grading, use Gemini.

---

## 6. Data & Infrastructure Lessons

### Git LFS Was Not Configured Early Enough

The ChromaDB index and lecture chunk JSONL files are large (100MB+). These were accidentally committed to git early in development, causing repository bloat. Recovery required `git filter-branch` to purge the history.

**Lesson:** Add `.gitignore` entries for `outputs/`, `data/`, `*.chroma`, and `*.jsonl` before the first commit. Set up `.gitignore` from day one.

### Secrets Were Committed Once

An early `.env` file was committed before `.gitignore` was set up. API keys had to be rotated immediately.

**Lesson:** Make `.gitignore` commit #1, ahead of any code. Use `git-secrets` or pre-commit hooks to prevent secrets from being committed.

### ChromaDB Versioning Is Fragile

ChromaDB broke backward compatibility between 0.3.x and 0.4.x — the index built in 0.3.x could not be read by 0.4.x. A collaborator on a different machine with a different ChromaDB version couldn't load the shared index.

**Lesson:** Pin ChromaDB to a specific version in `requirements.txt`. Document that the index must be rebuilt if ChromaDB is upgraded.

### API Key Costs Accumulated Faster Than Expected During Development

During development, running the full pipeline repeatedly (for debugging) accumulated ~$15 in API costs over 2 weeks. Most was from vision description runs that were discarded.

**Lesson:** Add a `--dry-run` flag that skips API calls and uses cached outputs. Implement output caching (save vision descriptions to disk; skip if already exists). The current system does cache vision outputs per run — but the run ID must be reused consistently.

---

## 7. Recommendations for Future Teams

### Priority 1: Add Automated Tests

The highest-risk untested code is `scripts/grading/grade_submission.py`:
- Rubric parsing (3 methods)
- Grade band calculation
- Policy cap logic
- Checklist percentage math

A pytest suite with 20–30 test cases would catch regressions immediately. Use the samples in `assignments/` as test fixtures.

### Priority 2: Add Async Job Processing

Replace the blocking subprocess approach with Celery + Redis:
1. Each grading request creates a Celery task
2. Flask immediately returns a `job_id`
3. Browser polls `GET /api/status?job_id=...` for progress
4. Multiple students can be graded in parallel

This would also enable progress bars instead of just log streaming.

### Priority 3: Build a Calibration UI

Currently, few-shot calibration requires manually editing `.txt` files. Build a simple UI in the Rubric & Setup tab:
- Show current calibration examples
- Allow adding/removing examples
- Show "compare LLM score vs. human score" side by side
- Save calibration to the library

### Priority 4: Add Human Review Workflow

The current system produces grades and ships them. Add a review step:
- Grade → "Pending Review" state
- Instructor reviews and approves/adjusts
- Grade is "Finalized" only after approval

This is the safest path to institutional deployment.

### Priority 5: Multi-Course Support

Currently, all lectures share one ChromaDB collection (`lecture_v1`). Add per-course collection support:
- `lecture_v1_CS680`, `lecture_v1_CS775`, etc.
- Dropdown in the UI to select the course context before grading
- Maintains separation between different course's lecture content

### Priority 6: Grade Consistency Metrics

When grading the same submission twice (or grading with two different providers), automatically compare scores and flag inconsistencies > 5 points. This would:
- Identify submissions that are hard to grade (instructor should review)
- Quantify drift in the system over time
- Generate confidence intervals alongside scores

---

## 8. What We Would Do Differently

### Start with a Smaller Scope

The initial system tried to support PDF, PPTX, XLSX, HTML extraction all at once. This spread development thin. A better approach would have been:
1. Build end-to-end for PDF only
2. Validate grading quality on a small dataset
3. Add PPTX support
4. Add XLSX/quiz grading last

### Write Tests From Day One

Every grading algorithm decision (grade bands, policy caps, PARTIAL weights) was made without a test harness. When a decision was revisited, it required manual re-grading to see the effect. A test suite would have made iteration much faster.

### Add Database-Level Storage Instead of File System

Using `data/library/` as a flat file store worked but created issues:
- No metadata (no way to know when a file was uploaded, by whom, for which course)
- No deduplication (same rubric uploaded 3 times)
- No atomic operations (reading a file that's being written is possible)

A lightweight SQLite or PostgreSQL database would have solved these cleanly.

### Use a Proper Job Queue from the Start

The subprocess-based pipeline was a quick solution but became the system's main scalability bottleneck. Starting with Celery + Redis would have avoided the entire class of "batch grading timeout" bugs.

---

## 9. Open Problems

| Problem | Current State | Suggested Research Direction |
|---|---|---|
| LLM non-determinism | ±2–5 point variance per run | Average 3 runs with majority-vote per criterion |
| Very sparse submissions (image-heavy, no text) | High variance, low confidence | Detect low-text submissions, flag for human review |
| Non-English submissions | Score poorly (English prompts) | Detect language, use multilingual prompts |
| Rubric specificity sensitivity | Vague rubrics produce lower accuracy | Study relationship between rubric detail level and grading accuracy |
| Calibration transfer | Calibration for Q13 doesn't help Q1–Q12 | Explore few-shot calibration at the assignment level, not per-question |
| Grading bias from filename | Anonymization not perfect (some names in metadata) | Audit all metadata passed to LLM; strip PII at extraction time |
| Long submissions (>40K chars) | Truncated — later content ignored | Implement sliding-window chunked grading with per-chunk scores |
| Grade inflation detection | No cross-student comparison | Build histogram of scores per batch; flag if >50% score above 90 |

---

*GradeAI Pro — Spring 2026 · Boston University MET CS/CDS*  
*Last updated: April 2026*
