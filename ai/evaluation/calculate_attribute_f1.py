from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# =========================================================
# PATHS
# =========================================================

CURRENT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = CURRENT_DIR / "results"


ML_FILE = RESULTS_DIR / "ml_results.json"
HYBRID_FILE = RESULTS_DIR / "hybrid_results.json"
LLM_FILE = RESULTS_DIR / "llm_results_llama.json"


# =========================================================
# ATTRIBUTES EVALUATED IN THE 60-CASE BENCHMARK
# =========================================================

ATTRIBUTES = [
    "pet_type",
    "gender",
    "size",
    "age_years",
    "age_months",
    "breed",
    "location",
    "energy_level",
    "temperament",
    "experience_level",
    "apartment_friendly",
    "child_friendly",
    "pet_friendly",
    "available_attention_hours",
]


# =========================================================
# LOAD JSON
# =========================================================

def load_json(path: Path) -> list[dict[str, Any]]:

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"{path.name} must contain a JSON list."
        )

    return data


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_value(value: Any) -> Any:
    """
    Normalize values so harmless formatting differences
    do not count as prediction errors.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        return value.strip().lower()

    if isinstance(value, list):
        normalized = [
            normalize_value(item)
            for item in value
        ]

        return tuple(
            sorted(normalized)
        )

    return value


# =========================================================
# EXTRACT STRUCTURED OUTPUT
# =========================================================

def get_prediction(
    result: dict[str, Any],
    system: str,
) -> dict[str, Any]:

    if system == "ml":
        value = result.get(
            "structured_ml_output",
            {},
        )

    elif system == "hybrid":
        value = result.get(
            "structured_hybrid_output",
            {},
        )

    elif system == "llm":
        value = result.get(
            "structured_llm_output",
            {},
        )

    else:
        raise ValueError(
            f"Unknown system: {system}"
        )

    if not isinstance(value, dict):
        return {}

    return value


# =========================================================
# ATTRIBUTE METRICS
# =========================================================

def calculate_attribute_metrics(
    results: list[dict[str, Any]],
    system: str,
) -> dict[str, dict[str, Any]]:

    metrics = {}

    for attribute in ATTRIBUTES:

        tp = 0
        fp = 0
        fn = 0
        support = 0

        for result in results:

            expected = result.get(
                "expected",
                {},
            )

            predicted = get_prediction(
                result,
                system,
            )

            expected_has_attribute = (
                attribute in expected
                and expected.get(attribute) is not None
            )

            predicted_has_attribute = (
                attribute in predicted
                and predicted.get(attribute) is not None
            )

            expected_value = normalize_value(
                expected.get(attribute)
            )

            predicted_value = normalize_value(
                predicted.get(attribute)
            )

            # -------------------------------------------------
            # POSITIVE EXPECTED ATTRIBUTE
            # -------------------------------------------------

            if expected_has_attribute:

                support += 1

                if (
                    predicted_has_attribute
                    and predicted_value == expected_value
                ):
                    # Correct field AND correct value
                    tp += 1

                elif predicted_has_attribute:
                    # Wrong value:
                    # expected value was missed -> FN
                    # wrong value was predicted -> FP
                    fn += 1
                    fp += 1

                else:
                    # Expected field completely missing
                    fn += 1

            # -------------------------------------------------
            # ATTRIBUTE WAS NOT EXPECTED
            # -------------------------------------------------

            else:

                if predicted_has_attribute:
                    # System invented an unexpected field
                    fp += 1

        precision = (
            tp / (tp + fp)
            if (tp + fp) > 0
            else 0.0
        )

        recall = (
            tp / (tp + fn)
            if (tp + fn) > 0
            else 0.0
        )

        f1 = (
            2 * precision * recall
            / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        metrics[attribute] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return metrics


# =========================================================
# PRINT TABLE
# =========================================================

def pretty_name(attribute: str) -> str:

    names = {
        "pet_type": "Pet type",
        "gender": "Gender",
        "size": "Size",
        "age_years": "Age (years)",
        "age_months": "Age (months)",
        "breed": "Breed",
        "location": "Location",
        "energy_level": "Energy level",
        "temperament": "Temperament",
        "experience_level": "Experience level",
        "apartment_friendly": "Apartment suitability",
        "child_friendly": "Child compatibility",
        "pet_friendly": "Pet compatibility",
        "available_attention_hours": "Available attention time",
    }

    return names.get(
        attribute,
        attribute,
    )


def main():

    ml_results = load_json(
        ML_FILE
    )

    hybrid_results = load_json(
        HYBRID_FILE
    )

    llm_results = load_json(
        LLM_FILE
    )

    print()
    print("=" * 82)
    print(
        "PAWCONNECT ATTRIBUTE-LEVEL F1 EVALUATION"
    )
    print("=" * 82)

    print(
        f"ML cases:     {len(ml_results)}"
    )
    print(
        f"Hybrid cases: {len(hybrid_results)}"
    )
    print(
        f"LLM cases:    {len(llm_results)}"
    )

    if not (
        len(ml_results)
        == len(hybrid_results)
        == len(llm_results)
        == 60
    ):
        print()
        print(
            "WARNING: Expected 60 cases "
            "for all three approaches."
        )

    ml_metrics = calculate_attribute_metrics(
        ml_results,
        "ml",
    )

    hybrid_metrics = calculate_attribute_metrics(
        hybrid_results,
        "hybrid",
    )

    llm_metrics = calculate_attribute_metrics(
        llm_results,
        "llm",
    )

    print()
    print(
        f"{'Attribute':<28}"
        f"{'ML F1':>12}"
        f"{'Hybrid F1':>14}"
        f"{'Llama F1':>14}"
        f"{'Support':>10}"
    )

    print("-" * 82)

    for attribute in ATTRIBUTES:

        ml_f1 = (
            ml_metrics[
                attribute
            ]["f1"] * 100
        )

        hybrid_f1 = (
            hybrid_metrics[
                attribute
            ]["f1"] * 100
        )

        llm_f1 = (
            llm_metrics[
                attribute
            ]["f1"] * 100
        )

        support = (
            ml_metrics[
                attribute
            ]["support"]
        )

        print(
            f"{pretty_name(attribute):<28}"
            f"{ml_f1:>11.2f}%"
            f"{hybrid_f1:>13.2f}%"
            f"{llm_f1:>13.2f}%"
            f"{support:>10}"
        )

    # -----------------------------------------------------
    # DETAILED TP / FP / FN
    # -----------------------------------------------------

    print()
    print("=" * 82)
    print("DETAILED COUNTS")
    print("=" * 82)

    for attribute in ATTRIBUTES:

        print()
        print(
            pretty_name(attribute)
        )

        for name, metric_set in [
            ("ML", ml_metrics),
            ("Hybrid", hybrid_metrics),
            ("Llama", llm_metrics),
        ]:

            metric = metric_set[
                attribute
            ]

            print(
                f"  {name:<7}"
                f"TP={metric['tp']:<4}"
                f"FP={metric['fp']:<4}"
                f"FN={metric['fn']:<4}"
                f"F1={metric['f1'] * 100:.2f}%"
            )

    print()
    print("=" * 82)


if __name__ == "__main__":
    main()