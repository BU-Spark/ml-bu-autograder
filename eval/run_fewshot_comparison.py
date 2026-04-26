"""
Few-shot calibration comparison across all quizzes.
Runs grading WITH and WITHOUT few-shot examples for Quiz 1-4,
then prints a combined before/after table.

Usage:
    python3 run_fewshot_comparison.py            # all quizzes
    python3 run_fewshot_comparison.py --quiz 1   # single quiz
    python3 run_fewshot_comparison.py --max-eval 20
"""

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "fall 2025 cs 581 quiz and assignment data"

QUIZ_CONFIGS = {
    "quiz_1": {
        "label": "Quiz 1 (BPR/EHR, /16)",
        "excel": DATA_DIR / "Quiz 1" / "CS 581 Quiz 1 AI vs Human Anonymized.xlsx",
        "rubric": DATA_DIR / "New Refined Rubrics" / "quiz_1" / "quiz_1.json",
        "sheet": "Quiz 1 Anonymized Results",
        "answer_col": "student answer",
        "prof_col": "Human Score",
        "filter_module": "module1",
    },
    "quiz_2": {
        "label": "Quiz 2 (RCM, /15)",
        "excel": DATA_DIR / "Quiz 2" / "CS 581 Quiz 2.xlsx",
        "rubric": DATA_DIR / "New Refined Rubrics" / "quiz_2" / "quiz_2.json",
        "sheet": "results",
        "answer_col": "student answer",
        "prof_col": "[human] grade for question in course",
        "filter_module": None,
    },
    "quiz_3": {
        "label": "Quiz 3 (PI Requirements, /16)",
        "excel": DATA_DIR / "Quiz 3" / "CS 581 Quiz 3.xlsx",
        "rubric": DATA_DIR / "New Refined Rubrics" / "quiz_3" / "quiz_3.json",
        "sheet": "results",
        "answer_col": "student answer",
        "prof_col": "[human] grade for question in course",
        "filter_module": None,
    },
    "quiz_4": {
        "label": "Quiz 4 (HIS Infrastructure, /16)",
        "excel": DATA_DIR / "Quiz 4" / "[new prompt used] cs581_quiz4 - Anonymized.xlsx",
        "rubric": DATA_DIR / "New Refined Rubrics" / "quiz_4" / "quiz_4.json",
        "sheet": "new prompt used cs581_quiz4 - A",
        "answer_col": "Student answer",
        "prof_col": "[human] grade for question in course",
        "filter_module": None,
    },
}


def run_condition(label, use_fewshot, aid, cfg, models, max_eval, k):
    """Run eval for one condition; return {key: {mae, n}} dict."""
    import eval_chunking_grading as e

    original_build = e.build_few_shot_block
    if not use_fewshot:
        e.build_few_shot_block = lambda _aid: ""

    print(f"\n  -- {label} --")
    results = e.run_eval(
        excel_path=cfg["excel"],
        rubric_path=cfg["rubric"],
        lectures_root=BASE_DIR,
        models=models,
        max_eval=max_eval,
        k_retrieve=k,
        sheet_name=cfg["sheet"],
        answer_col=cfg["answer_col"],
        prof_col=cfg["prof_col"],
        filter_module=cfg.get("filter_module"),
        assignment_id=aid if use_fewshot else None,
    )

    e.build_few_shot_block = original_build
    return results or {}


def print_combined_table(all_results):
    """Print a single combined before/after table across all quizzes."""
    print("\n")
    print("=" * 78)
    print("FEW-SHOT CALIBRATION RESULTS — ALL QUIZZES (model: gpt-4o-mini, TF-IDF retrieval)")
    print("=" * 78)
    print(f"{'Quiz':<32} {'Baseline MAE':>12} {'Few-shot MAE':>13} {'Δ MAE':>8} {'% Change':>10} {'Winner':>8}")
    print("-" * 78)

    for aid, row in all_results.items():
        label = QUIZ_CONFIGS[aid]["label"]
        b = row.get("baseline_mae")
        f = row.get("fewshot_mae")
        n = row.get("n", "?")
        if b is None or f is None:
            print(f"  {label:<30} {'ERROR':>12} {'ERROR':>13}")
            continue
        delta = f - b
        pct = (b - f) / b * 100 if b else 0
        winner = "few-shot" if delta < -0.01 else ("baseline" if delta > 0.01 else "tie")
        print(f"  {label:<30} {b:>12.2f} {f:>13.2f} {delta:>+8.2f} {pct:>+9.1f}%  {winner:>8}   (n={n})")

    # Average row
    valid = [(r["baseline_mae"], r["fewshot_mae"]) for r in all_results.values()
             if r.get("baseline_mae") is not None and r.get("fewshot_mae") is not None]
    if valid:
        avg_b = sum(b for b, _ in valid) / len(valid)
        avg_f = sum(f for _, f in valid) / len(valid)
        avg_d = avg_f - avg_b
        avg_pct = (avg_b - avg_f) / avg_b * 100 if avg_b else 0
        print("-" * 78)
        print(f"  {'AVERAGE':<30} {avg_b:>12.2f} {avg_f:>13.2f} {avg_d:>+8.2f} {avg_pct:>+9.1f}%")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiz", default=None, choices=list(QUIZ_CONFIGS),
                        help="Run a single quiz instead of all (default: all)")
    parser.add_argument("--models", nargs="+", default=["openai"])
    parser.add_argument("--max-eval", type=int, default=15)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--out", default="fewshot_comparison_results.json")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    quizzes = {args.quiz: QUIZ_CONFIGS[args.quiz]} if args.quiz else QUIZ_CONFIGS

    print(f"\nRunning few-shot calibration comparison")
    print(f"Quizzes : {list(quizzes.keys())}")
    print(f"Models  : {args.models}  |  Max rows: {args.max_eval}  |  Top-k: {args.k}")

    all_results = {}
    full_data = {}

    for aid, cfg in quizzes.items():
        print(f"\n{'='*60}")
        print(f"QUIZ: {cfg['label']}")
        print(f"{'='*60}")

        baseline = run_condition("BASELINE (no few-shot)", False, aid, cfg, args.models, args.max_eval, args.k)
        fewshot  = run_condition("FEW-SHOT calibration",  True,  aid, cfg, args.models, args.max_eval, args.k)

        # Extract MAE for the single model key (hybrid+openai)
        b_key = "hybrid+openai"
        b_mae = baseline.get(b_key, {}).get("mae")
        f_mae = fewshot.get(b_key, {}).get("mae")
        n     = baseline.get(b_key, {}).get("n") or fewshot.get(b_key, {}).get("n")

        all_results[aid] = {"baseline_mae": b_mae, "fewshot_mae": f_mae, "n": n}
        full_data[aid] = {"baseline": baseline, "fewshot": fewshot}

    print_combined_table(all_results)

    out_path = BASE_DIR / args.out
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"config": {"max_eval": args.max_eval, "k": args.k, "models": args.models},
                   "per_quiz": full_data, "summary": all_results},
                  f, ensure_ascii=False, indent=2)
    print(f"\nFull results saved to: {out_path}")


if __name__ == "__main__":
    main()
