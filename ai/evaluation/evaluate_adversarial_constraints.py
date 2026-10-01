"""
Adversarial hard-constraint evaluation.

Each scenario is built to tempt a ranker into violating a
non-relaxable constraint: "decoy" animals match every preferred
trait (and every other required field) but have the wrong pet type
or are no longer available, while the legitimate candidates match
few or none of the preferred traits.

Attack families:
  exact_decoy        right-type exact matches exist but score poorly;
                     wrong-type decoys score perfectly
  fallback_decoy     no right-type exact match exists (another required
                     field fails), so fallback is triggered; decoys
                     satisfy everything except pet type
  no_right_type      no animal of the requested type exists at all;
                     only perfect-scoring decoys are available
  unavailable_decoy  perfect right-type animals exist but are adopted

Metrics per system:
  violation rate     share of scenarios with >= 1 recommended animal
                     of the wrong type or not available
  expected outcome   top-1 is a legitimate candidate, or (for
                     no_right_type) nothing is recommended

Run:
    python evaluation/evaluate_adversarial_constraints.py [--per-family 250] [--seed 20260930]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


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
    BOOLEAN_FIELDS,
    ENERGY,
    PET_TYPES,
    TRAITS,
    aggregate_score_ranker,
    random_animal,
    violates_hard_constraint,
)


# =========================================================
# FILES & CONFIGURATION
# =========================================================

RESULTS_DIR = CURRENT_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "adversarial_constraints_summary.json"
SCENARIO_FILE = CURRENT_DIR / "adversarial_constraint_scenarios.json"

FAMILIES = ["exact_decoy", "fallback_decoy", "no_right_type", "unavailable_decoy"]
TOP_K = 5


# =========================================================
# SCENARIO CONSTRUCTION
# =========================================================

def _perfect(animal: dict[str, Any], preferred: dict[str, Any]) -> dict[str, Any]:
    animal["energy_level"] = preferred["energy_level"]
    animal["temperament"] = ", ".join(preferred["temperament"])
    for field in BOOLEAN_FIELDS:
        animal[field] = preferred[field]
    return animal


def _poor(animal: dict[str, Any], preferred: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    animal["energy_level"] = rng.choice([e for e in ENERGY if e != preferred["energy_level"]])
    animal["temperament"] = rng.choice([t for t in TRAITS if t not in preferred["temperament"]])
    for field in BOOLEAN_FIELDS:
        animal[field] = not preferred[field]
    return animal


def build_scenario(family: str, index: int, rng: random.Random) -> dict[str, Any]:
    wanted = rng.choice(PET_TYPES)
    other = next(t for t in PET_TYPES if t != wanted)

    required: dict[str, Any] = {"pet_type": wanted, "size": rng.choice(["small", "medium", "large"])}
    preferred = {
        "energy_level": rng.choice(ENERGY),
        "temperament": rng.sample(TRAITS, 2),
        **{field: True for field in BOOLEAN_FIELDS},
    }

    animals: list[dict[str, Any]] = []
    next_id = 1

    def add(pet_type: str, *, perfect: bool, size_ok: bool = True, status: str = "available"):
        nonlocal next_id
        animal = random_animal(rng, next_id, pet_type)
        animal["size"] = required["size"] if size_ok else rng.choice(
            [s for s in ("small", "medium", "large") if s != required["size"]]
        )
        animal["adoption_status"] = status
        animals.append(_perfect(animal, preferred) if perfect else _poor(animal, preferred, rng))
        next_id += 1

    decoys = rng.randint(4, 8)
    legit = rng.randint(1, 3)

    # Decoys get lower IDs so ID-based tie-breaking cannot help.
    if family == "unavailable_decoy":
        for _ in range(decoys):
            add(wanted, perfect=True, status="adopted")
    else:
        for _ in range(decoys):
            add(other, perfect=True)

    if family == "exact_decoy":
        for _ in range(legit):
            add(wanted, perfect=False)
    elif family == "fallback_decoy":
        for _ in range(legit):
            add(wanted, perfect=False, size_ok=False)
    elif family == "unavailable_decoy":
        for _ in range(legit):
            add(wanted, perfect=False)
    # no_right_type: decoys only

    return {
        "id": f"ADV-{family}-{index:03d}",
        "family": family,
        "preferences": {"required": required, "preferred": preferred},
        "animals": animals,
        "expected_empty": family == "no_right_type",
    }


# =========================================================
# EVALUATION
# =========================================================

def pawconnect(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    return rank_animals(scenario["animals"], scenario["preferences"], TOP_K).get("recommendations", [])


def aggregate(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    return aggregate_score_ranker(scenario, TOP_K)


def judge(scenario: dict[str, Any], recommendations: list[dict[str, Any]]) -> dict[str, bool]:
    preferences = scenario["preferences"]
    violated = any(violates_hard_constraint(a, preferences) for a in recommendations)

    if scenario["expected_empty"]:
        correct = not recommendations
    else:
        correct = bool(recommendations) and not violates_hard_constraint(recommendations[0], preferences)

    return {"violated": violated, "correct": correct}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-family", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20260930)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    scenarios = [
        build_scenario(family, index, rng)
        for family in FAMILIES
        for index in range(1, args.per_family + 1)
    ]
    SCENARIO_FILE.write_text(json.dumps(scenarios, indent=1), encoding="utf-8")

    systems = {"PawConnect": pawconnect, "Aggregate score": aggregate}
    summary: dict[str, dict[str, dict[str, float]]] = {name: {} for name in systems}

    for name, system in systems.items():
        for family in FAMILIES + ["all"]:
            subset = [s for s in scenarios if family in ("all", s["family"])]
            judged = [judge(s, system(s)) for s in subset]
            summary[name][family] = {
                "scenarios": len(subset),
                "violation_rate": sum(j["violated"] for j in judged) / len(subset),
                "expected_outcome_rate": sum(j["correct"] for j in judged) / len(subset),
            }

    print("=" * 84)
    print("PAWCONNECT ADVERSARIAL HARD-CONSTRAINT EVALUATION")
    print("=" * 84)
    print(f"Scenarios: {len(scenarios)} ({args.per_family} per family)   Top-k: {TOP_K}   Seed: {args.seed}")
    print()
    print(f"{'Family':<20}{'System':<18}{'Violation rate':>18}{'Expected outcome':>20}")
    print("-" * 76)
    for family in FAMILIES + ["all"]:
        for name in systems:
            row = summary[name][family]
            print(
                f"{family:<20}{name:<18}"
                f"{row['violation_rate'] * 100:>17.2f}%"
                f"{row['expected_outcome_rate'] * 100:>19.2f}%"
            )

    output = {
        "configuration": {
            "families": FAMILIES,
            "scenarios_per_family": args.per_family,
            "top_k": TOP_K,
            "seed": args.seed,
        },
        "systems": summary,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print()
    print("Scenarios saved to:", SCENARIO_FILE)
    print("Results saved to:  ", OUTPUT_FILE)


if __name__ == "__main__":
    main()
