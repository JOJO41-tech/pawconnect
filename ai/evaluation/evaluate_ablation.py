from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# =========================================================
# PATH SETUP
# =========================================================

CURRENT_DIR = Path(__file__).resolve().parent
AI_DIR = CURRENT_DIR.parent

if str(AI_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(AI_DIR),
    )


# =========================================================
# IMPORT EXISTING PAWCONNECT COMPONENTS
# =========================================================

from ml_engine import predict_ml_only

from app import (
    run_prediction,
    build_ranking_preferences,
)

from entity_extractor import extract_entities

from preference_standardizer import (
    standardize_preferences,
)

# ML-only conversion
from evaluate_challenge_set import (
    extract_structured_ml_output,
)

# Same evaluation/output functions as Hybrid test
from evaluate_hybrid_set import (
    load_challenge_set,
    build_structured_output,
    values_match,
)


# =========================================================
# FILES
# =========================================================

CHALLENGE_FILE = (
    CURRENT_DIR
    / "natural_language_challenge_60.jsonl"
)

RESULTS_DIR = (
    CURRENT_DIR
    / "results"
)

OUTPUT_FILE = (
    RESULTS_DIR
    / "ablation_component_results.json"
)


# =========================================================
# ENTITY FIELDS
# =========================================================

ENTITY_FIELDS = (
    "pet_type",
    "breed",
    "gender",
    "size",
    "location",
    "age_years",
    "age_months",
)


# =========================================================
# 1. ML-ONLY
# =========================================================

def ml_only(
    text: str,
) -> dict[str, Any]:

    prediction = predict_ml_only(
        text
    )

    return extract_structured_ml_output(
        prediction
    )


# =========================================================
# 2. ML + SEMANTIC RULES
#
# Entity contribution is deliberately removed.
# Everything else in the Hybrid semantic processing
# remains active.
# =========================================================

def ml_plus_semantic_rules(
    text: str,
) -> dict[str, Any]:

    # Full Hybrid prediction includes:
    # ML probabilities + semantic prediction rules
    prediction = run_prediction(
        text
    )

    # IMPORTANT:
    # remove extracted entities so that this configuration
    # measures semantic/rule processing without entities.
    prediction = dict(
        prediction
    )

    prediction[
        "entities"
    ] = {}

    legacy_preferences = (
        build_ranking_preferences(
            prediction
        )
    )

    standardized = (
        standardize_preferences(
            legacy_preferences,
            model_name="hybrid",
            original_prompt=text,
        )
    )

    return build_structured_output(
        standardized
    )


# =========================================================
# 3. ML + ENTITY EXTRACTION
#
# No Hybrid semantic/rule pipeline is used.
# Start with pure ML structured output and add ONLY
# explicit entity extraction.
# =========================================================

def ml_plus_entity_extraction(
    text: str,
) -> dict[str, Any]:

    # Pure ML baseline
    prediction = predict_ml_only(
        text
    )

    structured = (
        extract_structured_ml_output(
            prediction
        )
    )

    # Make a copy so original ML output is untouched.
    output = dict(
        structured
    )

    # Explicit entity extraction only.
    entities = extract_entities(
        text
    )

    if not isinstance(
        entities,
        dict,
    ):
        entities = {}

    for field in ENTITY_FIELDS:

        value = entities.get(
            field
        )

        if value is not None:

            # Exact entity information takes precedence
            # over statistical ML interpretation.
            output[
                field
            ] = value

    return output


# =========================================================
# 4. FULL HYBRID
# =========================================================

def full_hybrid(
    text: str,
) -> dict[str, Any]:

    prediction = run_prediction(
        text
    )

    legacy_preferences = (
        build_ranking_preferences(
            prediction
        )
    )

    standardized = (
        standardize_preferences(
            legacy_preferences,
            model_name="hybrid",
            original_prompt=text,
        )
    )

    return build_structured_output(
        standardized
    )


# =========================================================
# MICRO PRECISION / RECALL / F1
# =========================================================

def calculate_micro_counts(
    expected: dict[str, Any],
    predicted: dict[str, Any],
) -> tuple[int, int, int]:

    tp = 0
    fp = 0
    fn = 0

    expected_fields = set(
        expected.keys()
    )

    predicted_fields = set(
        predicted.keys()
    )

    # -----------------------------------------------------
    # Expected fields
    # -----------------------------------------------------

    for field, expected_value in (
        expected.items()
    ):

        predicted_value = predicted.get(
            field
        )

        # Explicit null = negative expectation
        if expected_value is None:

            if (
                field in predicted
                and predicted_value is not None
            ):
                fp += 1

            continue

        correct = values_match(
            field,
            expected_value,
            predicted_value,
        )

        if correct:

            tp += 1

        else:

            fn += 1

            # Wrong non-null value:
            # expected value missed + wrong value produced.
            if (
                field in predicted
                and predicted_value is not None
            ):
                fp += 1

    # -----------------------------------------------------
    # Completely unexpected fields
    # -----------------------------------------------------

    for field in (
        predicted_fields
        - expected_fields
    ):

        value = predicted.get(
            field
        )

        # Ignore internal conflict-analysis keys.
        if field.endswith(
            "_conflict"
        ):
            continue

        if value is not None:

            fp += 1

    return (
        tp,
        fp,
        fn,
    )


# =========================================================
# EVALUATE ONE CONFIGURATION
# =========================================================

def evaluate_configuration(
    name: str,
    function,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:

    total_expected_fields = 0
    correct_fields_total = 0
    exact_cases = 0

    total_tp = 0
    total_fp = 0
    total_fn = 0

    detailed_results = []

    for index, row in enumerate(
        cases,
        start=1,
    ):

        text = row[
            "text"
        ]

        expected = row.get(
            "expected",
            {},
        )

        predicted = function(
            text
        )

        # -------------------------------------------------
        # Existing field-accuracy definition
        # -------------------------------------------------

        correct_fields = 0
        field_results = {}

        for field, expected_value in (
            expected.items()
        ):

            predicted_value = (
                predicted.get(
                    field
                )
            )

            correct = values_match(
                field,
                expected_value,
                predicted_value,
            )

            field_results[
                field
            ] = correct

            if correct:
                correct_fields += 1

        total_fields_case = len(
            expected
        )

        total_expected_fields += (
            total_fields_case
        )

        correct_fields_total += (
            correct_fields
        )

        exact = (
            total_fields_case > 0
            and correct_fields
            == total_fields_case
        )

        if exact:
            exact_cases += 1

        # -------------------------------------------------
        # Micro P/R/F1
        # -------------------------------------------------

        tp, fp, fn = (
            calculate_micro_counts(
                expected,
                predicted,
            )
        )

        total_tp += tp
        total_fp += fp
        total_fn += fn

        detailed_results.append(
            {
                "case_id": row.get(
                    "id",
                    index,
                ),
                "text": text,
                "expected": expected,
                "predicted": predicted,
                "field_results": field_results,
                "correct_fields": (
                    correct_fields
                ),
                "total_expected_fields": (
                    total_fields_case
                ),
                "exact_case": exact,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )

    # =====================================================
    # AGGREGATE METRICS
    # =====================================================

    precision = (
        total_tp
        / (
            total_tp
            + total_fp
        )
        if (
            total_tp
            + total_fp
        ) > 0
        else 0.0
    )

    recall = (
        total_tp
        / (
            total_tp
            + total_fn
        )
        if (
            total_tp
            + total_fn
        ) > 0
        else 0.0
    )

    f1 = (
        (
            2
            * precision
            * recall
        )
        / (
            precision
            + recall
        )
        if (
            precision
            + recall
        ) > 0
        else 0.0
    )

    field_accuracy = (
        correct_fields_total
        / total_expected_fields
        if total_expected_fields
        else 0.0
    )

    exact_accuracy = (
        exact_cases
        / len(
            cases
        )
        if cases
        else 0.0
    )

    return {
        "configuration": name,
        "cases": len(
            cases
        ),
        "tp": total_tp,
        "fp": total_fp,
        "fn": total_fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "correct_fields": (
            correct_fields_total
        ),
        "total_expected_fields": (
            total_expected_fields
        ),
        "field_accuracy": (
            field_accuracy
        ),
        "exact_cases": (
            exact_cases
        ),
        "exact_case_accuracy": (
            exact_accuracy
        ),
        "details": (
            detailed_results
        ),
    }


# =========================================================
# PRINT INDIVIDUAL RESULTS
# =========================================================

def print_result(
    result: dict[str, Any],
):

    print()
    print(
        result[
            "configuration"
        ]
    )

    print(
        "-" * 65
    )

    print(
        "TP / FP / FN:",
        result[
            "tp"
        ],
        "/",
        result[
            "fp"
        ],
        "/",
        result[
            "fn"
        ],
    )

    print(
        "Precision:     "
        f"{result['precision'] * 100:.2f}%"
    )

    print(
        "Recall:        "
        f"{result['recall'] * 100:.2f}%"
    )

    print(
        "F1-score:      "
        f"{result['f1'] * 100:.2f}%"
    )

    print(
        "Field accuracy:"
        f" {result['field_accuracy'] * 100:.2f}%"
    )

    print(
        "Exact-case acc:"
        f" {result['exact_case_accuracy'] * 100:.2f}%"
    )

    print(
        "Correct fields:"
        f" {result['correct_fields']}"
        f"/{result['total_expected_fields']}"
    )

    print(
        "Exact cases:   "
        f"{result['exact_cases']}"
        f"/{result['cases']}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    cases = load_challenge_set(
        CHALLENGE_FILE
    )

    print()
    print(
        "=" * 94
    )

    print(
        "PAWCONNECT COMPONENT-ADDITION ABLATION STUDY"
    )

    print(
        "=" * 94
    )

    print(
        "Benchmark cases:",
        len(
            cases
        ),
    )

    configurations = [

        (
            "ML-only",
            ml_only,
        ),

        (
            "ML + Semantic Rules",
            ml_plus_semantic_rules,
        ),

        (
            "ML + Entity Extraction",
            ml_plus_entity_extraction,
        ),

        (
            "Full Hybrid",
            full_hybrid,
        ),
    ]

    results = []

    for name, function in configurations:

        result = (
            evaluate_configuration(
                name,
                function,
                cases,
            )
        )

        results.append(
            result
        )

        print_result(
            result
        )

    # =====================================================
    # FINAL TABLE
    # =====================================================

    print()
    print(
        "=" * 104
    )

    print(
        "ABLATION SUMMARY"
    )

    print(
        "=" * 104
    )

    print(
        f"{'Configuration':<28}"
        f"{'Precision':>12}"
        f"{'Recall':>11}"
        f"{'F1':>11}"
        f"{'Field Acc.':>14}"
        f"{'Exact Acc.':>14}"
    )

    print(
        "-" * 104
    )

    for result in results:

        print(
            f"{result['configuration']:<28}"
            f"{result['precision'] * 100:>11.2f}%"
            f"{result['recall'] * 100:>10.2f}%"
            f"{result['f1'] * 100:>10.2f}%"
            f"{result['field_accuracy'] * 100:>13.2f}%"
            f"{result['exact_case_accuracy'] * 100:>13.2f}%"
        )

    # =====================================================
    # SAVE
    # =====================================================

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "Detailed results saved to:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "=" * 104
    )


if __name__ == "__main__":

    main()