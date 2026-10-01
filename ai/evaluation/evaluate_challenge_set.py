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


from ml_engine import predict_ml_only


# =========================================================
# FILES
# =========================================================

CHALLENGE_FILE = (
    CURRENT_DIR
    / "natural_language_challenge_60"
    ".jsonl"
)

RESULTS_DIR = (
    CURRENT_DIR
    / "results"
)

ML_RESULTS_FILE = (
    RESULTS_DIR
    / "ml_results.json"
)

ML_SUMMARY_FILE = (
    RESULTS_DIR
    / "ml_summary.json"
)


# =========================================================
# LABEL MAPPING
# =========================================================

LABEL_TO_VALUE = {
    # Pet type
    "prefers_dog": (
        "pet_type",
        "dog",
    ),
    "prefers_cat": (
        "pet_type",
        "cat",
    ),

    # Energy
    "active": (
        "energy_level",
        "high",
    ),
    "moderate_activity": (
        "energy_level",
        "medium",
    ),
    "low_energy": (
        "energy_level",
        "low",
    ),

    # Experience
    "beginner_owner": (
        "experience_level",
        "beginner",
    ),
    "experienced_owner": (
        "experience_level",
        "experienced",
    ),

    # Compatibility
    "good_with_children": (
        "child_friendly",
        True,
    ),
    "good_with_pets": (
        "pet_friendly",
        True,
    ),
    "apartment_friendly": (
        "apartment_friendly",
        True,
    ),

    # Time
    "limited_time": (
        "available_attention_hours",
        2,
    ),
    "plenty_time": (
        "available_attention_hours",
        8,
    ),
}


TEMPERAMENT_LABELS = {
    "calm",
    "quiet",
    "friendly",
    "playful",
    "gentle",
    "independent",
    "protective",
    "affectionate",
    "vocal",
}


# =========================================================
# LOAD CHALLENGE DATA
# =========================================================

def load_challenge_set(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        raise FileNotFoundError(
            f"Missing challenge file: {path}"
        )

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

            text = row.get(
                "text"
            )

            if not isinstance(
                text,
                str,
            ):
                raise ValueError(
                    "Missing or invalid "
                    f"'text' at line {line_number}"
                )

            expected = row.get(
                "expected",
                {},
            )

            if not isinstance(
                expected,
                dict,
            ):
                raise ValueError(
                    "Invalid 'expected' "
                    f"at line {line_number}"
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
                normalize_text(
                    item
                )
                for item in value
                if normalize_text(
                    item
                )
            }
        )

    return [
        normalize_text(
            value
        )
    ]


# =========================================================
# CONVERT ML LABELS TO STRUCTURED VALUES
# =========================================================

def extract_structured_ml_output(
    prediction: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert raw classifier labels into a structured
    preference dictionary for evaluation.

    IMPORTANT:
    This does NOT add hybrid rules or entity extraction.
    It only interprets what the ML labels themselves mean.
    """

    labels = prediction.get(
        "labels",
        [],
    )

    if not isinstance(
        labels,
        list,
    ):
        labels = []

    normalized_labels = {
        normalize_text(
            label
        )
        for label in labels
    }

    structured: dict[
        str,
        Any,
    ] = {}

    # -----------------------------------------------------
    # Direct label mappings
    # -----------------------------------------------------

    for label in normalized_labels:

        mapping = LABEL_TO_VALUE.get(
            label
        )

        if not mapping:
            continue

        field, value = mapping

        # If multiple contradictory labels occur,
        # preserve them separately for analysis later.
        if field not in structured:
            structured[
                field
            ] = value

        else:

            existing = structured[
                field
            ]

            if existing != value:

                conflict_key = (
                    f"{field}_conflict"
                )

                conflicts = structured.get(
                    conflict_key,
                    [],
                )

                if not isinstance(
                    conflicts,
                    list,
                ):
                    conflicts = []

                if existing not in conflicts:
                    conflicts.append(
                        existing
                    )

                if value not in conflicts:
                    conflicts.append(
                        value
                    )

                structured[
                    conflict_key
                ] = conflicts

    # -----------------------------------------------------
    # Temperament
    # -----------------------------------------------------

    temperament = sorted(
        label
        for label in normalized_labels
        if label in TEMPERAMENT_LABELS
    )

    if temperament:
        structured[
            "temperament"
        ] = temperament

    return structured


# =========================================================
# FIELD COMPARISON
# =========================================================

def values_match(
    field: str,
    expected: Any,
    predicted: Any,
) -> bool:

    if expected is None:
        return predicted is None

    if field == "temperament":

        expected_list = set(
            normalize_list(
                expected
            )
        )

        predicted_list = set(
            normalize_list(
                predicted
            )
        )

        return expected_list.issubset(
            predicted_list
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
            return float(
                expected
            ) == float(
                predicted
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

    return (
        normalize_text(
            expected
        )
        ==
        normalize_text(
            predicted
        )
    )


# =========================================================
# SCORE ONE CASE
# =========================================================

def score_case(
    *,
    expected: dict[str, Any],
    structured_output: dict[str, Any],
    raw_labels: list[str],
) -> dict[str, Any]:

    field_results: dict[
        str,
        bool,
    ] = {}

    correct_fields = 0

    for field, expected_value in expected.items():

        predicted_value = (
            structured_output.get(
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

    if total_expected_fields > 0:

        field_accuracy = round(
            correct_fields
            / total_expected_fields,
            4,
        )

    else:

        field_accuracy = 0.0

    overall_case_correct = (
        total_expected_fields > 0
        and correct_fields
        == total_expected_fields
    )

    # -----------------------------------------------------
    # Identify labels that do not correspond to any
    # expected category.
    # -----------------------------------------------------

    expected_categories = set(
        expected.keys()
    )

    false_positive_labels: list[
        str
    ] = []

    for label in raw_labels:

        normalized_label = (
            normalize_text(
                label
            )
        )

        # Temperament
        if (
            normalized_label
            in TEMPERAMENT_LABELS
        ):

            if (
                "temperament"
                not in expected_categories
            ):
                false_positive_labels.append(
                    normalized_label
                )

            continue

        mapping = LABEL_TO_VALUE.get(
            normalized_label
        )

        if not mapping:

            # Unknown / unmapped classifier labels
            # still count as extra model output.
            false_positive_labels.append(
                normalized_label
            )

            continue

        field, _ = mapping

        if field not in expected_categories:

            false_positive_labels.append(
                normalized_label
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

        "field_accuracy": (
            field_accuracy
        ),

        "overall_case_correct": (
            overall_case_correct
        ),

        "false_positive_labels": (
            sorted(
                false_positive_labels
            )
        ),

        "false_positive_count": len(
            false_positive_labels
        ),
    }


# =========================================================
# BUILD SUMMARY
# =========================================================

def build_summary(
    results: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    total_cases = len(
        results
    )

    if total_cases == 0:

        return {
            "system": "ml_only",
            "total_cases": 0,
        }

    total_expected_fields = 0
    total_correct_fields = 0

    fully_correct_cases = 0

    total_false_positives = 0

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

        total_false_positives += (
            evaluation[
                "false_positive_count"
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

    # -----------------------------------------------------
    # Overall field accuracy
    # -----------------------------------------------------

    if total_expected_fields > 0:

        field_accuracy = (
            total_correct_fields
            / total_expected_fields
        )

    else:

        field_accuracy = 0.0

    # -----------------------------------------------------
    # Exact case accuracy
    # -----------------------------------------------------

    exact_case_accuracy = (
        fully_correct_cases
        / total_cases
    )

    # -----------------------------------------------------
    # Average false positives
    # -----------------------------------------------------

    average_false_positives = (
        total_false_positives
        / total_cases
    )

    # -----------------------------------------------------
    # Per-field accuracy
    # -----------------------------------------------------

    per_field_accuracy: dict[
        str,
        float,
    ] = {}

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
        "system": "ml_only",

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
            field_accuracy,
            4,
        ),

        "fully_correct_cases": (
            fully_correct_cases
        ),

        "exact_case_accuracy": round(
            exact_case_accuracy,
            4,
        ),

        "total_false_positive_labels": (
            total_false_positives
        ),

        "average_false_positive_labels_per_case": round(
            average_false_positives,
            4,
        ),

        "per_field_accuracy": (
            per_field_accuracy
        ),
    }


# =========================================================
# RUN ML BASELINE
# =========================================================

def evaluate_ml():

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
        "PAWCONNECT ML-ONLY EVALUATION"
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

    results: list[
        dict[str, Any]
    ] = []

    # =====================================================
    # CASE LOOP
    # =====================================================

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

        prediction = (
            predict_ml_only(
                text
            )
        )

        structured_output = (
            extract_structured_ml_output(
                prediction
            )
        )

        evaluation = score_case(
            expected=expected,

            structured_output=(
                structured_output
            ),

            raw_labels=(
                prediction.get(
                    "labels",
                    [],
                )
            ),
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

            "ml_output": (
                prediction
            ),

            "structured_ml_output": (
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
        # Terminal display
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
            "FALSE POSITIVES:",
            evaluation[
                "false_positive_labels"
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

    # =====================================================
    # SAVE
    # =====================================================

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ML_RESULTS_FILE.write_text(

        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )

    ML_SUMMARY_FILE.write_text(

        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )

    # =====================================================
    # PRINT SUMMARY
    # =====================================================

    print()
    print(
        "=" * 70
    )

    print(
        "ML-ONLY SUMMARY"
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
        "Average false-positive labels:",
        summary[
            "average_false_positive_labels_per_case"
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
        ML_RESULTS_FILE,
    )

    print(
        "Summary saved:",
        ML_SUMMARY_FILE,
    )

    print(
        "=" * 70
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    evaluate_ml()