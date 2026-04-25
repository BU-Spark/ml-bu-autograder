# Anthropic Prompt Caching

Internal engineering reference for the BU MET Autograder.
Background on Anthropic's caching mechanism: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

---

## Why caching matters for grading runs

Every student in a grading run sees the same system prompt, rubric criteria, rubric text, and
assignment instructions. That static context is roughly 4,000–5,000 tokens. Without caching,
those tokens are billed at the full input rate for every student. With a single `cache_control`
breakpoint, Anthropic stores the static prefix after the first call and charges the 90%-discounted
read rate on all subsequent calls in the same run.

For a class of 30 students, the first call pays a one-time cache-write premium (+25%); the
remaining 29 calls pay the read rate instead of the input rate. The measured result over 31 real
submissions was **~65% total cost reduction** and 31/31 cache hits after the first call.

---

## Block architecture

`build_system_blocks()` (`scripts/grading/grade_submission.py`) returns a two-element list of text
blocks that are passed directly to the Anthropic `messages.create` `system` parameter.

| Block | Content | Cache breakpoint? |
| :--- | :--- | :--- |
| **block1** | `SYSTEM_PROMPT` — grading persona, methodology, JSON output schema | No |
| **block2** | Assignment instructions + assignment-derived section IDs + rubric criteria JSON + rubric text | Yes, when `enable_cache=True` |

A condensed view of the logic:

```python
block1: dict[str, Any] = {"type": "text", "text": SYSTEM_PROMPT}

block2: dict[str, Any] = {"type": "text", "text": context_text}
if enable_cache:
    block2["cache_control"] = {"type": "ephemeral"}

return [block1, block2]
```

---

## Breakpoint strategy

Anthropic's cache is **cumulative**: a breakpoint on block2 implicitly caches block1 + block2
together as one prefix. The single-breakpoint approach writes one cache entry per run; subsequent
calls within the 5-minute TTL hit that entry and pay the read rate on the entire prefix.

**Implication for maintainers:** for the cache to hit, block2 must be byte-identical across
students in the same run. The rubric text, rubric criteria JSON, and assignment text are read
once from disk and re-parsed deterministically per student, so they stay stable. The one
non-obvious cache-poisoning trap is `expected_sections`: if it is derived from each student's
submission text rather than the assignment, block2 differs per student and the cache never hits.
`run_grading()` only embeds **assignment-derived** section IDs in block2; student-derived
sections are kept out of the cached block and used only for downstream section-coverage
validation.

---

## Provider gating

Caching is enabled only when `grading_provider == "anthropic"`:

```python
system_blocks = build_system_blocks(
    ...
    enable_cache=(grading_provider == "anthropic"),
)
```

When `grading_provider` is `openai` or `gemini`, `call_openai()` and `call_gemini()` receive the
system argument via `flatten_system_blocks()`, which
collapses all text blocks to a plain `\n\n`-joined string. Any non-`text` block type raises
`ValueError` to prevent silent content loss.

---

## Model support and known limitations

Caching is gated on provider, not model. The code passes `cache_control` to any model string you
supply to the Anthropic provider.

| Model family | Minimum cached tokens |
| :--- | :--- |
| Sonnet / Opus | 1,024 |
| Haiku | 2,048 |

**Known limitation:** if you run with a Haiku model and a short rubric (under 2,048 tokens of
combined block1 + block2 content), Anthropic will silently return `cache_creation_input_tokens: 0`
and `cache_read_input_tokens: 0`. No error is raised. The grader will function correctly but
caching will not activate and you will pay full input rates. Verify with the tools described below.

---

## TTL and run length

The `ephemeral` cache type has a **5-minute TTL**. Each cache hit resets the timer. Within a
normal grading run the timer stays alive because calls are issued sequentially with little idle
time between students.

If a run is interrupted and resumes more than 5 minutes after the last API call, the next student
will pay a fresh cache-write premium before subsequent calls return to the read rate.

---

## Cost structure (Claude Sonnet 4.6)

| Token type | Cost per 1M tokens | vs. standard input |
| :--- | :--- | :--- |
| Standard input | $3.00 | baseline |
| Cache write | $3.75 | +25% (one-time per run) |
| Cache read | $0.30 | −90% (all subsequent calls) |
| Output | $15.00 | — |

Observed in production stress test: **~65% total cost savings** over 31 submissions with
`claude-sonnet-4-6`. This is an empirical data point, not a guarantee — savings scale with class
size and rubric token count.

---

## Production log format

`run_grading()` prints per-student token usage
after each API call:

```
Tokens used — input: 452  output: 890  cache_write: 4,821  cache_read: 0
```
(first student — cache written)

```
Tokens used — input: 452  output: 885  cache_write: 0  cache_read: 4,821
```
(subsequent students — cache hit)

The `cache_write` and `cache_read` fields appear only when at least one of them is non-zero.
Absence of those fields means no cache metadata was returned — either the provider is not
Anthropic, or the cached region fell below the token minimum.

---

## Verifying caching on a new environment

These scripts are **local dev tools only** — they are not committed to the repo.

### Basic verification (`scripts/tools/test_prompt_caching.py`)

Runs three sequential API calls (baseline → cache write → cache read) against a synthetic rubric
padded to realistic token counts. Asserts `cache_creation_input_tokens > 0` on call 2 and
`cache_read_input_tokens > 0` on call 3.

```bash
python scripts/tools/test_prompt_caching.py --model claude-sonnet-4-6
```

A passing run prints:

```
  PASS: cache_creation_input_tokens > 0
  PASS: cache_read_input_tokens > 0
```

and writes a bar chart to `cache_savings.png`.

### Stress test (`scripts/tools/stress_test_caching.py`)

Grades N real student submissions twice — once without caching and once with — then outputs a
cost-comparison JSON and chart.

```bash
python scripts/tools/stress_test_caching.py --n 31 --model claude-sonnet-4-6
```

Look for:
- `cache_hits` in the summary equal to `N - 1` (the first call is always a write)
- `Cost savings (%)` in the expected range (~60–70% for a class-sized run with `claude-sonnet-4-6`)

---

## Duplicate implementation note

`app/scripts/grading/grade_submission.py` is a near-duplicate of `scripts/grading/grade_submission.py`.
This PR ships caching only in the CLI grader (`scripts/grading/`); the web-app copy in
`app/scripts/grading/` is unchanged. Future work to bring caching to the web-app path will
need to mirror the same surface (`build_system_blocks`, `flatten_system_blocks`, the
`system: str | list[dict]` widening on `call_*`, and the `enable_cache` wiring in `run_grading`).
