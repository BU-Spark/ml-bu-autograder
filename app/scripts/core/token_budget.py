"""
Token tracking and cost estimation for grading LLM calls.

``MODEL_PRICING`` maps model name → per-token rates (USD per 1 M tokens) for
input, output, cache_creation_input, and cache_read_input.  Models that omit a
cache key (e.g. GPT-4o) simply don't charge for it.

To add a new model: copy any existing entry, set the correct model ID as the
key, fill in the rates from the provider's pricing page, and update the
``# Last updated`` comment with today's date.
"""
from __future__ import annotations

import warnings
from typing import Any

# Last updated: 2026-04-06
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "cache_creation_input": 3.75,
        "cache_read_input": 0.30,
    },
    "claude-haiku-3-5-20241022": {
        "input": 1.00,
        "output": 4.00,
        "cache_creation_input": 1.25,
        "cache_read_input": 0.10,
    },
    "gpt-4o-2024-11-20": {
        "input": 2.50,
        "output": 10.00,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
    # VERIFY: pricing confirmed as of 2026-04-06; check https://ai.google.dev/pricing
    "gemini-2.5-flash": {
        "input": 0.15,
        "output": 0.60,
    },
}


def _estimate_cost(model: str, usage: dict[str, int]) -> float:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        warnings.warn(
            f"No pricing entry for model '{model}' — cost will be reported as $0.00. "
            "Add it to MODEL_PRICING in core/token_budget.py.",
            stacklevel=2,
        )
        return 0.0
    cost = (
        usage.get("input_tokens", 0) * pricing.get("input", 0.0)
        + usage.get("output_tokens", 0) * pricing.get("output", 0.0)
        + usage.get("cache_creation_input_tokens", 0) * pricing.get("cache_creation_input", 0.0)
        + usage.get("cache_read_input_tokens", 0) * pricing.get("cache_read_input", 0.0)
    ) / 1_000_000
    return round(cost, 6)


class TokenTracker:
    """Accumulates per-call token usage and estimates USD cost across a grading run."""

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []

    def record(self, call_type: str, model: str, usage: dict[str, int]) -> None:
        """Append one LLM call's token counts and estimated cost to the internal log."""
        self._calls.append({
            "call_type": call_type,
            "model": model,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
            "estimated_cost_usd": _estimate_cost(model, usage),
        })

    def summary_by_type(self) -> dict[str, Any]:
        """Return token totals and cost grouped by ``call_type`` label."""
        buckets: dict[str, Any] = {}
        for call in self._calls:
            ct = call["call_type"]
            if ct not in buckets:
                buckets[ct] = {
                    "count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "estimated_cost_usd": 0.0,
                }
            b = buckets[ct]
            b["count"] += 1
            for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                        "cache_read_input_tokens", "estimated_cost_usd"):
                b[key] += call[key]
        # Round once per bucket after all accumulation to avoid per-step float drift.
        for b in buckets.values():
            b["estimated_cost_usd"] = round(b["estimated_cost_usd"], 6)
        return buckets

    def total_summary(self) -> dict[str, Any]:
        """Return aggregate token counts and total estimated cost across all recorded calls."""
        total_calls = len(self._calls)
        total_input = sum(c["input_tokens"] for c in self._calls)
        total_output = sum(c["output_tokens"] for c in self._calls)
        total_cache_creation = sum(c["cache_creation_input_tokens"] for c in self._calls)
        total_cache_read = sum(c["cache_read_input_tokens"] for c in self._calls)
        total_cost = round(sum(c["estimated_cost_usd"] for c in self._calls), 6)
        return {
            "total_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cache_creation_tokens": total_cache_creation,
            "total_cache_read_tokens": total_cache_read,
            "total_estimated_cost_usd": total_cost,
        }

    def human_summary(self) -> str:
        """Return a formatted multi-line string suitable for printing to stdout."""
        t = self.total_summary()
        lines = [
            "── Token Usage ──────────────────────────────",
            f"  Calls            : {t['total_calls']}",
            f"  Input tokens     : {t['total_input_tokens']:,}",
            f"  Output tokens    : {t['total_output_tokens']:,}",
            f"  Cache creation   : {t['total_cache_creation_tokens']:,}",
            f"  Cache read       : {t['total_cache_read_tokens']:,}",
            f"  Estimated cost   : ${t['total_estimated_cost_usd']:.4f} USD",
            "─────────────────────────────────────────────",
        ]
        by_type = self.summary_by_type()
        if len(by_type) > 1:
            for ct, b in by_type.items():
                lines.append(f"  [{ct}] {b['count']} call(s)  in={b['input_tokens']:,}  out={b['output_tokens']:,}  ${b['estimated_cost_usd']:.4f}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Return ``total_summary()`` merged with ``summary_by_type()`` for JSON serialization."""
        return {**self.total_summary(), "by_type": self.summary_by_type()}
