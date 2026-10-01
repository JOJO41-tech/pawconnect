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


from app import (
    run_prediction,
    build_ranking_preferences,
)
from preference_standardizer import (
    standardize_preferences,
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

HYBRID_RESULTS_FILE = (
    RESULTS_DIR
    / "hybrid_results.json"
)

HYBRID_SUMMARY_FILE = (
    RESULTS_DIR
    / "hybrid_summary.json"
)


# =========================================================
# LOAD CHALLENGE SET
# =========================================================

def load_challenge_set(
    path: Path,
) -> list[dict[str, Any]]:

    rows: list[
        dict[str, Any]
    ] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):

            if not line.strip():
                continue

            row = json.loads(
                line
            )

            if not isinstance(
                row.get("text"),
                str,
            ):
                raise ValueError(
                    f"Invalid text at line {line_number}"
                )

            rows.append(
                row
            )

    return rows


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip().lower()


def normalize_list(
    value: Any,
) -> list[str]:

    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):

        return sorted(
            {
                normalize_text(item)
                for item in value
                if normalize_text(item)
            }
        )

    return [
        normalize_text(
            value
        )
    ]


# =========================================================
# BUILD STRUCTURED HYBRID OUTPUT
# =========================================================

def build_structured_output(
    standardized: dict[str, Any],
) -> dict[str, Any]:

    required = standardized.get(
        "required",
        {},
    )

    preferred = standardized.get(
        "preferred",
        {},
    )

    if not isinstance(
        required,
        dict,
    ):
        required = {}

    if not isinstance(
        preferred,
        dict,
    ):
        preferred = {}

    output: dict[
        str,
        Any,
    ] = {}

    # -----------------------------------------------------
    # Required
    # -----------------------------------------------------

    for field in (
        "pet_type",
        "breed",
        "gender",
        "size",
        "location",
        "age_years",
        "age_months",
    ):

        if field in required:
            output[
                field
            ] = required[
                field
            ]

    # -----------------------------------------------------
    # Preferred
    # -----------------------------------------------------

    for field in (
        "energy_level",
        "apartment_friendly",
        "child_friendly",
        "pet_friendly",
        "experience_level",
        "available_attention_hours",
    ):

        if field in preferred:
            output[
                field
            ] = preferred[
                field
            ]

    if "temperament" in preferred:

        output[
            "temperament"
        ] = preferred[
            "temperament"
        ]

    return output


# =========================================================
# VALUE COMPARISON
# =========================================================

def values_match(
    field: str,
    expected: Any,
    predicted: Any,
) -> bool:

    if expected is None:
        return predicted is None

    if field == "temperament":

        expected_set = set(
            normalize_list(
                expected
            )
        )

        predicted_set = set(
            normalize_list(
                predicted
            )
        )

        return expected_set.issubset(
            predicted_set
        )

    if isinstance(
        expected,
        bool,
    ):

        return predicted is expected

    if isinstance(
        expected,
        (
            int,
            float,
        ),
    ):

        try:

            return (
                float(expected)
                == float(predicted)
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

    return (
        normalize_text(expected)
        ==
        normalize_text(predicted)
    )


# =========================================================
# SCORE CASE
# =========================================================

def score_case(
    expected: dict[str, Any],
    predicted: dict[str, Any],
) -> dict[str, Any]:

    field_results: dict[
        str,
        bool,
    ] = {}

    correct_fields = 0

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

    total_expected_fields = len(
        expected
    )

    field_accuracy = (
        correct_fields
        / total_expected_fields
        if total_expected_fields
        else 0.0
    )

    overall_case_correct = (
        total_expected_fields > 0
        and correct_fields
        == total_expected_fields
    )

    # -----------------------------------------------------
    # Extra structured fields
    # -----------------------------------------------------

    expected_fields = set(
        expected.keys()
    )

    predicted_fields = set(
        predicted.keys()
    )

    extra_fields = sorted(
        predicted_fields
        - expected_fields
    )

    return {
        "field_results": (
            field_results
        ),

        "correct_fields": (
            correct_fields
        ),

        "total_expected_fields": (
            total_expected_fields
        ),

        "field_accuracy": round(
            field_accuracy,
            4,
        ),

        "overall_case_correct": (
            overall_case_correct
        ),

        "extra_fields": (
            extra_fields
        ),

        "extra_field_count": len(
            extra_fields
        ),
    }


# =========================================================
# SUMMARY
# =========================================================

def build_summary(
    results: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    total_cases = len(
        results
    )

    total_expected_fields = 0
    total_correct_fields = 0

    fully_correct_cases = 0

    total_extra_fields = 0

    field_totals: dict[
        str,
        int,
    ] = {}

    field_correct: dict[
        str,
        int,
    ] = {}

    for result in results:

        evaluation = result[
            "evaluation"
        ]

        total_expected_fields += (
            evaluation[
                "total_expected_fields"
            ]
        )

        total_correct_fields += (
            evaluation[
                "correct_fields"
            ]
        )

        total_extra_fields += (
            evaluation[
                "extra_field_count"
            ]
        )

        if evaluation[
            "overall_case_correct"
        ]:
            fully_correct_cases += 1

        for field, correct in (
            evaluation[
                "field_results"
            ].items()
        ):

            field_totals[
                field
            ] = (
                field_totals.get(
                    field,
                    0,
                )
                + 1
            )

            if correct:

                field_correct[
                    field
                ] = (
                    field_correct.get(
                        field,
                        0,
                    )
                    + 1
                )

    preference_extraction_accuracy = (
        total_correct_fields
        / total_expected_fields
        if total_expected_fields
        else 0.0
    )

    exact_case_accuracy = (
        fully_correct_cases
        / total_cases
        if total_cases
        else 0.0
    )

    average_extra_fields = (
        total_extra_fields
        / total_cases
        if total_cases
        else 0.0
    )

    per_field_accuracy = {}

    for field, total in (
        field_totals.items()
    ):

        correct = field_correct.get(
            field,
            0,
        )

        per_field_accuracy[
            field
        ] = round(
            correct / total,
            4,
        )

    return {
        "system": (
            "hybrid_ai"
        ),

        "total_cases": (
            total_cases
        ),

        "total_expected_fields": (
            total_expected_fields
        ),

        "correct_fields": (
            total_correct_fields
        ),

        "preference_extraction_accuracy": round(
            preference_extraction_accuracy,
            4,
        ),

        "fully_correct_cases": (
            fully_correct_cases
        ),

        "exact_case_accuracy": round(
            exact_case_accuracy,
            4,
        ),

        "total_extra_fields": (
            total_extra_fields
        ),

        "average_extra_fields_per_case": round(
            average_extra_fields,
            4,
        ),

        "per_field_accuracy": (
            per_field_accuracy
        ),
    }


# =========================================================
# HYBRID EVALUATION
# =========================================================

def evaluate_hybrid():

    challenge_rows = (
        load_challenge_set(
            CHALLENGE_FILE
        )
    )

    print()
    print(
        "=" * 70
    )

    print(
        "PAWCONNECT HYBRID AI EVALUATION"
    )

    print(
        "=" * 70
    )

    print(
        "Challenge samples:",
        len(
            challenge_rows
        ),
    )

    results = []

    for index, row in enumerate(
        challenge_rows,
        start=1,
    ):

        text = row[
            "text"
        ]

        expected = row.get(
            "expected",
            {},
        )

        # -------------------------------------------------
        # Hybrid prediction
        # -------------------------------------------------

        prediction = (
            run_prediction(
                text
            )
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

        structured_output = (
            build_structured_output(
                standardized
            )
        )

        evaluation = (
            score_case(
                expected,
                structured_output,
            )
        )

        result = {

            "case_id": row.get(
                "id",
                index,
            ),

            "text": text,

            "expected": (
                expected
            ),

            "hybrid_prediction": (
                prediction
            ),

            "hybrid_preferences": (
                standardized
            ),

            "structured_hybrid_output": (
                structured_output
            ),

            "evaluation": (
                evaluation
            ),
        }

        results.append(
            result
        )

        # -------------------------------------------------
        # Terminal
        # -------------------------------------------------

        print()
        print(
            "-" * 70
        )

        print(
            f"CASE {index}"
        )

        print(
            "ID:",
            result[
                "case_id"
            ],
        )

        print(
            "TEXT:",
            text,
        )

        print(
            "EXPECTED:",
            expected,
        )

        print(
            "PREDICTED:",
            structured_output,
        )

        print(
            "FIELD ACCURACY:",
            (
                f"{evaluation['field_accuracy'] * 100:.2f}%"
            ),
        )

        print(
            "CASE PASS:",
            evaluation[
                "overall_case_correct"
            ],
        )

        print(
            "EXTRA FIELDS:",
            evaluation[
                "extra_fields"
            ],
        )

    # =====================================================
    # SUMMARY
    # =====================================================

    summary = (
        build_summary(
            results
        )
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    HYBRID_RESULTS_FILE.write_text(

        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )

    HYBRID_SUMMARY_FILE.write_text(

        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )

    print()
    print(
        "=" * 70
    )

    print(
        "HYBRID AI SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        "Cases:",
        summary[
            "total_cases"
        ],
    )

    print(
        "Preference extraction accuracy:",
        (
            f"{summary['preference_extraction_accuracy'] * 100:.2f}%"
        ),
    )

    print(
        "Exact case accuracy:",
        (
            f"{summary['exact_case_accuracy'] * 100:.2f}%"
        ),
    )

    print(
        "Fully correct cases:",
        (
            f"{summary['fully_correct_cases']}"
            f"/{summary['total_cases']}"
        ),
    )

    print(
        "Average extra fields:",
        summary[
            "average_extra_fields_per_case"
        ],
    )

    print()
    print(
        "Per-field accuracy:"
    )

    for field, accuracy in (
        summary[
            "per_field_accuracy"
        ].items()
    ):

        print(
            f"  {field}: "
            f"{accuracy * 100:.2f}%"
        )

    print()
    print(
        "Detailed results saved:",
        HYBRID_RESULTS_FILE,
    )

    print(
        "Summary saved:",
        HYBRID_SUMMARY_FILE,
    )

    print(
        "=" * 70
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "Alternative JSONL benchmark in the same format "
            "(e.g. hand-labeled real adopter requests). "
            "Results are saved as hybrid_results_<stem>.json."
        ),
    )

    cli_args = parser.parse_args()

    if cli_args.input is not None:

        CHALLENGE_FILE = cli_args.input.resolve()

        HYBRID_RESULTS_FILE = (
            RESULTS_DIR
            / f"hybrid_results_{CHALLENGE_FILE.stem}.json"
        )

        HYBRID_SUMMARY_FILE = (
            RESULTS_DIR
            / f"hybrid_summary_{CHALLENGE_FILE.stem}.json"
        )

    evaluate_hybrid()