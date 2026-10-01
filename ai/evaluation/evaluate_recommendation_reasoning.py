from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# =========================================================
# PATH SETUP
# =========================================================

CURRENT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

AI_DIR = CURRENT_DIR.parent

if str(AI_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(AI_DIR),
    )


from ranking import rank_animals


# =========================================================
# FILES
# =========================================================

CHALLENGE_FILE = (
    CURRENT_DIR
    / "recommendation_challenge_25.json"
)

RESULTS_DIR = (
    CURRENT_DIR
    / "results"
)

RESULTS_FILE = (
    RESULTS_DIR
    / "recommendation_reasoning_results.json"
)

SUMMARY_FILE = (
    RESULTS_DIR
    / "recommendation_reasoning_summary.json"
)


# =========================================================
# LOAD CHALLENGE SET
# =========================================================

def load_challenge_set(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        raise FileNotFoundError(
            f"Challenge file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(
            file
        )

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            "Challenge file must contain a JSON list."
        )

    return data


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


def get_pet_type(
    animal: dict[str, Any],
) -> str:

    return normalize_text(
        animal.get(
            "pet_type",
            animal.get(
                "type",
                "",
            ),
        )
    )


# =========================================================
# EVALUATE ONE CASE
# =========================================================

def evaluate_case(
    case: dict[str, Any],
) -> dict[str, Any]:

    preferences = case[
        "preferences"
    ]

    animals = case[
        "animals"
    ]

    expected = case[
        "expected"
    ]

    result = rank_animals(
        animals=animals,
        preferences=preferences,
        recommendation_limit=4,
    )

    actual_mode = result.get(
        "mode"
    )

    best_match = result.get(
        "best_match"
    )

    actual_top1_id = (
        best_match.get(
            "id"
        )
        if isinstance(
            best_match,
            dict,
        )
        else None
    )

    expected_mode = (
        expected.get(
            "mode"
        )
    )

    expected_top1_id = (
        expected.get(
            "top1_id"
        )
    )

    allowed_pet_type = (
        normalize_text(
            expected.get(
                "allowed_pet_type"
            )
        )
    )

    # -----------------------------------------------------
    # MODE ACCURACY
    # -----------------------------------------------------

    mode_correct = (
        actual_mode
        == expected_mode
    )

    # -----------------------------------------------------
    # TOP-1 ACCURACY
    # -----------------------------------------------------

    top1_correct = (
        actual_top1_id
        == expected_top1_id
    )

    # -----------------------------------------------------
    # HARD-CONSTRAINT COMPLIANCE
    # -----------------------------------------------------

    hard_constraint_correct = True

    recommendations = result.get(
        "recommendations",
        [],
    )

    if allowed_pet_type:

        for animal in recommendations:

            if (
                get_pet_type(
                    animal
                )
                != allowed_pet_type
            ):

                hard_constraint_correct = False
                break

    # -----------------------------------------------------
    # NO-MATCH CORRECTNESS
    # -----------------------------------------------------

    if expected_mode == "no_match":

        no_match_correct = (
            actual_mode == "no_match"
            and best_match is None
            and len(
                recommendations
            ) == 0
        )

    else:
        no_match_correct = True

    # -----------------------------------------------------
    # FALLBACK CORRECTNESS
    # -----------------------------------------------------

    if expected_mode == "alternative":

        fallback_correct = (
            actual_mode == "alternative"
            and actual_top1_id
            == expected_top1_id
            and hard_constraint_correct
        )

    else:
        fallback_correct = True

    # -----------------------------------------------------
    # OVERALL CASE PASS
    # -----------------------------------------------------

    overall_pass = (
        mode_correct
        and top1_correct
        and hard_constraint_correct
        and no_match_correct
        and fallback_correct
    )

    return {
        "case_id":
            case.get(
                "id"
            ),

        "category":
            case.get(
                "category"
            ),

        "expected":
            expected,

        "actual_mode":
            actual_mode,

        "actual_top1_id":
            actual_top1_id,

        "mode_correct":
            mode_correct,

        "top1_correct":
            top1_correct,

        "hard_constraint_correct":
            hard_constraint_correct,

        "no_match_correct":
            no_match_correct,

        "fallback_correct":
            fallback_correct,

        "overall_pass":
            overall_pass,

        "recommendation_ids": [
            animal.get(
                "id"
            )
            for animal
            in recommendations
        ],

        "raw_result":
            result,
    }


# =========================================================
# SUMMARY
# =========================================================

def build_summary(
    results: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    total = len(
        results
    )

    top1_correct = sum(
        1
        for result in results
        if result[
            "top1_correct"
        ]
    )

    mode_correct = sum(
        1
        for result in results
        if result[
            "mode_correct"
        ]
    )

    hard_constraint_correct = sum(
        1
        for result in results
        if result[
            "hard_constraint_correct"
        ]
    )

    no_match_correct = sum(
        1
        for result in results
        if result[
            "no_match_correct"
        ]
    )

    fallback_correct = sum(
        1
        for result in results
        if result[
            "fallback_correct"
        ]
    )

    fully_correct = sum(
        1
        for result in results
        if result[
            "overall_pass"
        ]
    )

    # -----------------------------------------------------
    # CATEGORY ACCURACY
    # -----------------------------------------------------

    category_totals: dict[
        str,
        int,
    ] = {}

    category_correct: dict[
        str,
        int,
    ] = {}

    for result in results:

        category = result.get(
            "category",
            "unknown",
        )

        category_totals[
            category
        ] = (
            category_totals.get(
                category,
                0,
            )
            + 1
        )

        if result[
            "overall_pass"
        ]:

            category_correct[
                category
            ] = (
                category_correct.get(
                    category,
                    0,
                )
                + 1
            )

    category_accuracy = {}

    for category, count in (
        category_totals.items()
    ):

        correct = (
            category_correct.get(
                category,
                0,
            )
        )

        category_accuracy[
            category
        ] = round(
            correct / count,
            4,
        )

    return {
        "total_cases":
            total,

        "fully_correct_cases":
            fully_correct,

        "overall_accuracy":
            round(
                fully_correct / total,
                4,
            )
            if total
            else 0,

        "top1_accuracy":
            round(
                top1_correct / total,
                4,
            )
            if total
            else 0,

        "mode_accuracy":
            round(
                mode_correct / total,
                4,
            )
            if total
            else 0,

        "hard_constraint_compliance":
            round(
                hard_constraint_correct / total,
                4,
            )
            if total
            else 0,

        "no_match_accuracy":
            round(
                no_match_correct / total,
                4,
            )
            if total
            else 0,

        "fallback_accuracy":
            round(
                fallback_correct / total,
                4,
            )
            if total
            else 0,

        "category_accuracy":
            category_accuracy,
    }


# =========================================================
# MAIN
# =========================================================

def main():

    cases = load_challenge_set(
        CHALLENGE_FILE
    )

    print()
    print(
        "=" * 70
    )

    print(
        "PAWCONNECT RECOMMENDATION REASONING EVALUATION"
    )

    print(
        "=" * 70
    )

    print(
        "Challenge cases:",
        len(
            cases
        ),
    )

    results = []

    for index, case in enumerate(
        cases,
        start=1,
    ):

        result = evaluate_case(
            case
        )

        results.append(
            result
        )

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
            "CATEGORY:",
            result[
                "category"
            ],
        )

        print(
            "EXPECTED MODE:",
            result[
                "expected"
            ].get(
                "mode"
            ),
        )

        print(
            "ACTUAL MODE:",
            result[
                "actual_mode"
            ],
        )

        print(
            "EXPECTED TOP-1:",
            result[
                "expected"
            ].get(
                "top1_id"
            ),
        )

        print(
            "ACTUAL TOP-1:",
            result[
                "actual_top1_id"
            ],
        )

        print(
            "MODE CORRECT:",
            result[
                "mode_correct"
            ],
        )

        print(
            "TOP-1 CORRECT:",
            result[
                "top1_correct"
            ],
        )

        print(
            "HARD CONSTRAINT:",
            result[
                "hard_constraint_correct"
            ],
        )

        print(
            "FALLBACK:",
            result[
                "fallback_correct"
            ],
        )

        print(
            "CASE PASS:",
            result[
                "overall_pass"
            ],
        )

    summary = build_summary(
        results
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_FILE.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    SUMMARY_FILE.write_text(
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
        "RECOMMENDATION REASONING SUMMARY"
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
        "Fully correct:",
        (
            f"{summary['fully_correct_cases']}"
            f"/{summary['total_cases']}"
        ),
    )

    print(
        "Overall accuracy:",
        (
            f"{summary['overall_accuracy'] * 100:.2f}%"
        ),
    )

    print(
        "Top-1 recommendation accuracy:",
        (
            f"{summary['top1_accuracy'] * 100:.2f}%"
        ),
    )

    print(
        "Mode accuracy:",
        (
            f"{summary['mode_accuracy'] * 100:.2f}%"
        ),
    )

    print(
        "Hard-constraint compliance:",
        (
            f"{summary['hard_constraint_compliance'] * 100:.2f}%"
        ),
    )

    print(
        "No-match accuracy:",
        (
            f"{summary['no_match_accuracy'] * 100:.2f}%"
        ),
    )

    print(
        "Fallback accuracy:",
        (
            f"{summary['fallback_accuracy'] * 100:.2f}%"
        ),
    )

    print()

    print(
        "Category accuracy:"
    )

    for category, accuracy in (
        summary[
            "category_accuracy"
        ].items()
    ):

        print(
            f"  {category}: "
            f"{accuracy * 100:.2f}%"
        )

    print()

    print(
        "Detailed results saved:",
        RESULTS_FILE,
    )

    print(
        "Summary saved:",
        SUMMARY_FILE,
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()