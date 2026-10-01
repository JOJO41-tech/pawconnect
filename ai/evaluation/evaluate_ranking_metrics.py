"""
Standard ranking-metric evaluation of PawConnect's recommendation
logic (NDCG@k, MAP@k, Hit Rate@k, MRR) against baselines, on a
larger seeded set of generated scenarios.

Addresses reviewer requests for standard recommendation metrics,
larger scenario sets, stronger baselines, and significance testing.

Systems compared (all receive the same structured preferences, so
language-understanding errors do not affect this measurement):
  * PawConnect       - ranking.rank_animals (hard filter -> fallback -> soft scoring)
  * Aggregate score  - one weighted sum over required + preferred matches
  * Filter only      - hard-constraint filter, listing order, no preference ranking
  * Random           - random order over available animals

Relevance labels come from scenario_generator.relevance (graded 0-5).
Binary metrics (MAP, HR, MRR) treat the best-graded animals in the
pool as relevant. Because relevance is derived from the intended
recommendation policy, these numbers measure how faithfully each
ranker implements that policy, not real adopter satisfaction.

Run:
    python evaluation/evaluate_ranking_metrics.py [--scenarios 1000] [--pool 20] [--seed 20260930]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import wilcoxon


# =========================================================
# PATH SETUP
# =========================================================

CURRENT_DIR = Path(__file__).resolve().parent
AI_DIR = CURRENT_DIR.parent

for path in (AI_DIR, CURRENT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ranking import rank_animals  # noqa: E402
from scenario_generator import (  # noqa: E402
    aggregate_score_ranker,
    filter_only_ranker,
    generate_scenarios,
    make_random_ranker,
    relevance,
    violates_hard_constraint,
)


# =========================================================
# FILES & CONFIGURATION
# =========================================================

RESULTS_DIR = CURRENT_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "ranking_metrics_summary.json"
SCENARIO_FILE = CURRENT_DIR / "generated_ranking_scenarios.json"

CUTOFFS = (1, 3, 5, 10)
MAX_K = max(CUTOFFS)
BOOTSTRAP_RESAMPLES = 5_000


# =========================================================
# RANKERS
# =========================================================

def pawconnect_ranker(scenario: dict[str, Any], k: int) -> list[dict[str, Any]]:
    result = rank_animals(
        animals=scenario["animals"],
        preferences=scenario["preferences"],
        recommendation_limit=k,
    )
    return result.get("recommendations", [])


# =========================================================
# METRICS
# =========================================================

def dcg(grades: list[int]) -> float:
    return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(grades))


def ndcg_at(ranked_grades: list[int], pool_grades: list[int], k: int) -> float:
    ideal = dcg(sorted(pool_grades, reverse=True)[:k])
    return dcg(ranked_grades[:k]) / ideal if ideal else 0.0


def average_precision_at(hits: list[bool], relevant_count: int, k: int) -> float:
    if not relevant_count:
        return 0.0
    found, total = 0, 0.0
    for i, hit in enumerate(hits[:k], start=1):
        if hit:
            found += 1
            total += found / i
    return total / min(relevant_count, k)


def reciprocal_rank(hits: list[bool]) -> float:
    for i, hit in enumerate(hits, start=1):
        if hit:
            return 1.0 / i
    return 0.0


def score_scenario(scenario: dict[str, Any], ranked: list[dict[str, Any]]) -> dict[str, float] | None:
    preferences = scenario["preferences"]
    grade_by_id = {a["id"]: relevance(a, preferences) for a in scenario["animals"]}
    pool_grades = list(grade_by_id.values())
    best_grade = max(pool_grades)

    # No eligible animal of the requested type: nothing to rank.
    if best_grade == 0:
        return None

    ranked_ids = [a["id"] for a in ranked]
    ranked_grades = [grade_by_id.get(i, 0) for i in ranked_ids]
    hits = [g == best_grade for g in ranked_grades]
    relevant_count = sum(g == best_grade for g in pool_grades)

    metrics = {"mrr": reciprocal_rank(hits[:MAX_K])}

    for k in CUTOFFS:
        metrics[f"ndcg@{k}"] = ndcg_at(ranked_grades, pool_grades, k)
        metrics[f"hit_rate@{k}"] = float(any(hits[:k]))
        metrics[f"map@{k}"] = average_precision_at(hits, relevant_count, k)

    top = ranked[:5]
    metrics["hard_violation_rate@5"] = (
        sum(violates_hard_constraint(a, preferences) for a in top) / len(top) if top else 0.0
    )
    return metrics


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator) -> list[float]:
    idx = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    means = values[idx].mean(axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


# =========================================================
# MAIN
# =========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=int, default=1000)
    parser.add_argument("--pool", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260930)
    args = parser.parse_args()

    scenarios = generate_scenarios(args.scenarios, args.pool, args.seed)
    SCENARIO_FILE.write_text(json.dumps(scenarios, indent=1), encoding="utf-8")

    rankers = {
        "PawConnect": pawconnect_ranker,
        "Aggregate score": aggregate_score_ranker,
        "Filter only": filter_only_ranker,
        "Random": make_random_ranker(args.seed),
    }

    per_ranker: dict[str, list[dict[str, float]]] = {name: [] for name in rankers}
    skipped = 0
    modes: dict[str, int] = {}

    for scenario in scenarios:
        mode = rank_animals(scenario["animals"], scenario["preferences"], MAX_K).get("mode")
        modes[mode] = modes.get(mode, 0) + 1
        rows = {name: score_scenario(scenario, ranker(scenario, MAX_K)) for name, ranker in rankers.items()}
        if rows["PawConnect"] is None:
            skipped += 1
            continue
        for name, row in rows.items():
            per_ranker[name].append(row)

    evaluated = len(per_ranker["PawConnect"])
    metric_names = list(per_ranker["PawConnect"][0])
    rng = np.random.default_rng(args.seed)

    summary: dict[str, Any] = {}
    for name, rows in per_ranker.items():
        summary[name] = {}
        for metric in metric_names:
            values = np.array([r[metric] for r in rows])
            summary[name][metric] = {"mean": float(values.mean()), "ci_95": bootstrap_ci(values, rng)}

    significance = {}
    pawconnect_ndcg = np.array([r["ndcg@5"] for r in per_ranker["PawConnect"]])
    for name in rankers:
        if name == "PawConnect":
            continue
        other = np.array([r["ndcg@5"] for r in per_ranker[name]])
        if np.all(pawconnect_ndcg == other):
            p_value = 1.0
        else:
            p_value = float(wilcoxon(pawconnect_ndcg, other, zero_method="wilcox").pvalue)
        significance[f"PawConnect_vs_{name}"] = {
            "metric": "ndcg@5",
            "mean_difference": float((pawconnect_ndcg - other).mean()),
            "wilcoxon_p_value": p_value,
        }

    # ---------------------------------------------------------
    # Report
    # ---------------------------------------------------------

    shown = ["ndcg@5", "ndcg@10", "map@10", "hit_rate@1", "hit_rate@5", "mrr", "hard_violation_rate@5"]

    print("=" * 100)
    print("PAWCONNECT RANKING METRICS")
    print("=" * 100)
    print(f"Generated scenarios: {len(scenarios)}  (evaluated: {evaluated}, no eligible pet: {skipped})")
    print(f"Pool size: {args.pool}   Seed: {args.seed}   PawConnect modes: {modes}")
    print()
    widths = [max(12, len(m) + 2) for m in shown]
    print(f"{'System':<18}" + "".join(f"{m:>{w}}" for m, w in zip(shown, widths)))
    print("-" * (18 + sum(widths)))
    for name in rankers:
        print(f"{name:<18}" + "".join(f"{summary[name][m]['mean']:>{w}.4f}" for m, w in zip(shown, widths)))

    print()
    for key, value in significance.items():
        print(f"{key}: dNDCG@5 = {value['mean_difference']:+.4f}, Wilcoxon p = {value['wilcoxon_p_value']:.3g}")

    output = {
        "configuration": {
            "generated_scenarios": len(scenarios),
            "evaluated_scenarios": evaluated,
            "skipped_no_eligible_pet": skipped,
            "pawconnect_modes": modes,
            "pool_size": args.pool,
            "seed": args.seed,
            "cutoffs": list(CUTOFFS),
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "relevance": "graded 0-5 from scenario_generator.relevance; binary relevant = best grade in pool",
        },
        "systems": summary,
        "significance": significance,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print()
    print("Scenarios saved to:", SCENARIO_FILE)
    print("Results saved to:  ", OUTPUT_FILE)


if __name__ == "__main__":
    main()
