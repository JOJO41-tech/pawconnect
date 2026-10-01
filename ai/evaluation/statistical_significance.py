"""
Statistical significance and confidence intervals for the
60-request preference-understanding benchmark.

Addresses reviewer requests for statistical significance testing.
Uses the saved per-case outputs of the ML-only, Hybrid, and
Llama 3.3 70B evaluations (no model is re-run).

Reports:
  * micro precision / recall / F1, field accuracy and exact-case
    accuracy with 95% percentile-bootstrap confidence intervals
    (cases resampled with replacement);
  * paired comparisons between systems:
      - exact McNemar test on case-level exact correctness,
      - Wilcoxon signed-rank test on per-case field accuracy,
      - paired bootstrap CI and p-value for the micro-F1 difference.

Run:
    python evaluation/statistical_significance.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest, wilcoxon


# =========================================================
# PATH SETUP
# =========================================================

CURRENT_DIR = Path(__file__).resolve().parent
AI_DIR = CURRENT_DIR.parent

for path in (AI_DIR, CURRENT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evaluate_ablation import calculate_micro_counts  # noqa: E402


# =========================================================
# FILES & CONFIGURATION
# =========================================================

RESULTS_DIR = CURRENT_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "statistical_significance.json"

SYSTEMS = {
    "ml_only": (RESULTS_DIR / "ml_results.json", "structured_ml_output"),
    "hybrid_ai": (RESULTS_DIR / "hybrid_results.json", "structured_hybrid_output"),
    "llama_3_3_70b": (RESULTS_DIR / "llm_results_llama.json", "structured_llm_output"),
}

PAIRS = [
    ("hybrid_ai", "ml_only"),
    ("hybrid_ai", "llama_3_3_70b"),
    ("ml_only", "llama_3_3_70b"),
]

BOOTSTRAP_RESAMPLES = 10_000
RANDOM_SEED = 20260930
CONFIDENCE = 0.95


# =========================================================
# PER-CASE TABLE
# =========================================================

def load_cases(path: Path, output_key: str) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    cases = {}

    for row in rows:
        expected = row.get("expected", {})
        predicted = row.get(output_key) or {}
        tp, fp, fn = calculate_micro_counts(expected, predicted)
        evaluation = row.get("evaluation", {})
        total = evaluation.get("total_expected_fields") or len(expected)

        cases[row["case_id"]] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "correct_fields": evaluation.get("correct_fields", tp),
            "total_fields": total,
            "field_accuracy": (evaluation.get("correct_fields", tp) / total) if total else 0.0,
            "case_correct": bool(evaluation.get("overall_case_correct", False)),
        }

    return cases


def to_arrays(cases: dict[str, dict[str, Any]], case_ids: list[str]) -> dict[str, np.ndarray]:
    return {
        key: np.array([cases[case_id][key] for case_id in case_ids], dtype=float)
        for key in ("tp", "fp", "fn", "correct_fields", "total_fields", "field_accuracy", "case_correct")
    }


# =========================================================
# METRICS
# =========================================================

def micro_prf(tp: float, fp: float, fn: float) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def metrics_for(arrays: dict[str, np.ndarray], idx: np.ndarray) -> dict[str, float]:
    tp, fp, fn = (arrays[k][idx].sum() for k in ("tp", "fp", "fn"))
    precision, recall, f1 = micro_prf(tp, fp, fn)
    return {
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
        "field_accuracy": arrays["correct_fields"][idx].sum() / arrays["total_fields"][idx].sum(),
        "exact_case_accuracy": arrays["case_correct"][idx].mean(),
    }


def bootstrap_indices(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, n, size=(BOOTSTRAP_RESAMPLES, n))


def ci(values: np.ndarray) -> list[float]:
    alpha = (1 - CONFIDENCE) / 2
    return [float(np.quantile(values, alpha)), float(np.quantile(values, 1 - alpha))]


# =========================================================
# PAIRED TESTS
# =========================================================

def mcnemar_exact(a_correct: np.ndarray, b_correct: np.ndarray) -> dict[str, Any]:
    a_only = int(((a_correct == 1) & (b_correct == 0)).sum())
    b_only = int(((a_correct == 0) & (b_correct == 1)).sum())
    discordant = a_only + b_only
    p_value = binomtest(a_only, discordant, 0.5).pvalue if discordant else 1.0
    return {"a_correct_b_wrong": a_only, "a_wrong_b_correct": b_only, "p_value": float(p_value)}


def wilcoxon_field_accuracy(a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    differences = a - b
    non_zero = int((differences != 0).sum())

    if non_zero == 0:
        return {"non_zero_pairs": 0, "statistic": None, "p_value": 1.0}

    result = wilcoxon(a, b, zero_method="wilcox")
    return {"non_zero_pairs": non_zero, "statistic": float(result.statistic), "p_value": float(result.pvalue)}


def paired_bootstrap_f1(
    a: dict[str, np.ndarray],
    b: dict[str, np.ndarray],
    samples: np.ndarray,
) -> dict[str, Any]:
    all_idx = np.arange(len(a["tp"]))
    observed = metrics_for(a, all_idx)["micro_f1"] - metrics_for(b, all_idx)["micro_f1"]

    diffs = np.array([
        metrics_for(a, idx)["micro_f1"] - metrics_for(b, idx)["micro_f1"]
        for idx in samples
    ])

    # Two-sided p-value: how often the resampled difference
    # falls on the opposite side of zero from the observed one.
    if observed == 0:
        p_value = 1.0
    else:
        opposite = (diffs <= 0).mean() if observed > 0 else (diffs >= 0).mean()
        # Floor at 1/B: a zero count means p < 1/B, not p = 0.
        p_value = min(1.0, max(2 * opposite, 1 / BOOTSTRAP_RESAMPLES))

    return {"observed_difference": float(observed), "ci_95": ci(diffs), "p_value": float(p_value)}


# =========================================================
# MAIN
# =========================================================

def main():
    per_system = {name: load_cases(path, key) for name, (path, key) in SYSTEMS.items()}

    case_ids = sorted(set.intersection(*(set(cases) for cases in per_system.values())))
    n = len(case_ids)
    arrays = {name: to_arrays(cases, case_ids) for name, cases in per_system.items()}

    rng = np.random.default_rng(RANDOM_SEED)
    samples = bootstrap_indices(n, rng)
    all_idx = np.arange(n)

    print("=" * 78)
    print("PAWCONNECT STATISTICAL SIGNIFICANCE (60-request benchmark)")
    print("=" * 78)
    print(f"Paired cases: {n}   Bootstrap resamples: {BOOTSTRAP_RESAMPLES}   Seed: {RANDOM_SEED}")

    system_results = {}

    for name, data in arrays.items():
        point = metrics_for(data, all_idx)
        boot = [metrics_for(data, idx) for idx in samples]
        intervals = {metric: ci(np.array([b[metric] for b in boot])) for metric in point}

        system_results[name] = {
            metric: {"value": float(value), "ci_95": intervals[metric]}
            for metric, value in point.items()
        }

        print()
        print(name)
        for metric, value in point.items():
            low, high = intervals[metric]
            print(f"  {metric:<22}{value * 100:7.2f}%   95% CI [{low * 100:6.2f}, {high * 100:6.2f}]")

    pair_results = {}

    print()
    print("-" * 78)
    print("PAIRED COMPARISONS")
    print("-" * 78)

    for a_name, b_name in PAIRS:
        a, b = arrays[a_name], arrays[b_name]
        comparison = {
            "mcnemar_exact_case": mcnemar_exact(a["case_correct"], b["case_correct"]),
            "wilcoxon_field_accuracy": wilcoxon_field_accuracy(a["field_accuracy"], b["field_accuracy"]),
            "paired_bootstrap_micro_f1": paired_bootstrap_f1(a, b, samples),
        }
        pair_results[f"{a_name}_vs_{b_name}"] = comparison

        f1_diff = comparison["paired_bootstrap_micro_f1"]
        print()
        print(f"{a_name} vs {b_name}")
        print(
            f"  McNemar (exact-case):      "
            f"{comparison['mcnemar_exact_case']['a_correct_b_wrong']} vs "
            f"{comparison['mcnemar_exact_case']['a_wrong_b_correct']} discordant, "
            f"p = {comparison['mcnemar_exact_case']['p_value']:.4g}"
        )
        print(f"  Wilcoxon (field accuracy): p = {comparison['wilcoxon_field_accuracy']['p_value']:.4g}")
        print(
            f"  Micro-F1 difference:       {f1_diff['observed_difference'] * 100:+.2f} pp, "
            f"95% CI [{f1_diff['ci_95'][0] * 100:+.2f}, {f1_diff['ci_95'][1] * 100:+.2f}], "
            f"p {'<=' if f1_diff['p_value'] <= 1 / BOOTSTRAP_RESAMPLES else '='} {f1_diff['p_value']:.4g}"
        )

    output = {
        "benchmark": "natural_language_challenge_60",
        "paired_cases": n,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "random_seed": RANDOM_SEED,
        "confidence_level": CONFIDENCE,
        "systems": system_results,
        "paired_comparisons": pair_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print()
    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
