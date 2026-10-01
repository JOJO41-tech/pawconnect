from __future__ import annotations

import json
import sys
import time
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


from llm_engine import (
    MODEL_NAME,
    predict_llm_only,
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

LLM_RESULTS_FILE = (
    RESULTS_DIR
    / "llm_results_llama.json"
)

LLM_SUMMARY_FILE = (
    RESULTS_DIR
    / "llm_summary_llama.json"
)


# =========================================================
# REQUEST SETTINGS
# =========================================================

# Groq can handle requests much faster than the previous
# Gemini free-tier setup, but a short pause is still useful
# to avoid unnecessary rate-limit bursts.
REQUEST_DELAY_SECONDS = 2

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10


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

            expected = row.get(
                "expected",
                {},
            )

            if not isinstance(
                text,
                str,
            ):
                raise ValueError(
                    f"Invalid text at line {line_number}"
                )

            if not isinstance(
                expected,
                dict,
            ):
                raise ValueError(
                    f"Invalid expected result at line {line_number}"
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
                float(
                    expected
                )
                ==
                float(
                    predicted
                )
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

    for field, expected_value in expected.items():

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

    if total_expected_fields > 0:

        field_accuracy = (
            correct_fields
            / total_expected_fields
        )

    else:
        field_accuracy = 0.0

    overall_case_correct = (
        total_expected_fields > 0
        and correct_fields
        == total_expected_fields
    )

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
        "field_results":
            field_results,

        "correct_fields":
            correct_fields,

        "total_expected_fields":
            total_expected_fields,

        "field_accuracy":
            round(
                field_accuracy,
                4,
            ),

        "overall_case_correct":
            overall_case_correct,

        "extra_fields":
            extra_fields,

        "extra_field_count":
            len(
                extra_fields
            ),
    }


# =========================================================
# LLM CALL WITH RETRY
# =========================================================

def run_llm_with_retry(
    text: str,
) -> tuple[
    dict[str, Any],
    float,
    int,
]:

    last_error: Exception | None = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            print(
                f"Llama attempt "
                f"{attempt}/{MAX_RETRIES}"
            )

            start_time = (
                time.perf_counter()
            )

            result = (
                predict_llm_only(
                    text
                )
            )

            latency = (
                time.perf_counter()
                - start_time
            )

            return (
                result,
                latency,
                attempt,
            )

        except Exception as exc:

            last_error = exc

            error_text = str(
                exc
            ).lower()

            is_rate_limit = (
                "429" in error_text
                or "rate limit" in error_text
                or "too many requests" in error_text
            )

            if (
                is_rate_limit
                and attempt < MAX_RETRIES
            ):

                print(
                    "Rate limit reached."
                )

                print(
                    f"Waiting "
                    f"{RETRY_DELAY_SECONDS} "
                    "seconds before retry..."
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )

                continue

            raise

    if last_error:
        raise last_error

    raise RuntimeError(
        "Unknown LLM evaluation error."
    )


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

    successful_calls = 0
    failed_calls = 0

    total_expected_fields = 0
    total_correct_fields = 0

    fully_correct_cases = 0
    total_extra_fields = 0

    total_latency = 0.0
    total_attempts = 0

    field_totals: dict[
        str,
        int,
    ] = {}

    field_correct: dict[
        str,
        int,
    ] = {}

    for result in results:

        if result.get(
            "error"
        ):

            failed_calls += 1
            continue

        successful_calls += 1

        total_latency += float(
            result.get(
                "latency_seconds",
                0,
            )
        )

        total_attempts += int(
            result.get(
                "attempts",
                1,
            )
        )

        evaluation = (
            result[
                "evaluation"
            ]
        )

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

    if total_expected_fields > 0:

        extraction_accuracy = (
            total_correct_fields
            / total_expected_fields
        )

    else:
        extraction_accuracy = 0.0

    if successful_calls > 0:

        successful_exact_accuracy = (
            fully_correct_cases
            / successful_calls
        )

        average_extra_fields = (
            total_extra_fields
            / successful_calls
        )

        average_latency = (
            total_latency
            / successful_calls
        )

        average_attempts = (
            total_attempts
            / successful_calls
        )

    else:

        successful_exact_accuracy = 0.0
        average_extra_fields = 0.0
        average_latency = 0.0
        average_attempts = 0.0

    if total_cases > 0:

        completion_rate = (
            successful_calls
            / total_cases
        )

        all_case_exact_accuracy = (
            fully_correct_cases
            / total_cases
        )

    else:

        completion_rate = 0.0
        all_case_exact_accuracy = 0.0

    per_field_accuracy: dict[
        str,
        float,
    ] = {}

    for field, total in (
        field_totals.items()
    ):

        correct = (
            field_correct.get(
                field,
                0,
            )
        )

        per_field_accuracy[
            field
        ] = round(
            correct / total,
            4,
        )

    return {
        "system":
            "llm_only",

        "model_name":
            MODEL_NAME,

        "total_cases":
            total_cases,

        "successful_calls":
            successful_calls,

        "failed_calls":
            failed_calls,

        "completion_rate":
            round(
                completion_rate,
                4,
            ),

        "total_expected_fields":
            total_expected_fields,

        "correct_fields":
            total_correct_fields,

        "preference_extraction_accuracy":
            round(
                extraction_accuracy,
                4,
            ),

        "fully_correct_cases":
            fully_correct_cases,

        "successful_case_accuracy":
            round(
                successful_exact_accuracy,
                4,
            ),

        "all_case_exact_accuracy":
            round(
                all_case_exact_accuracy,
                4,
            ),

        "average_extra_fields_per_case":
            round(
                average_extra_fields,
                4,
            ),

        "average_latency_seconds":
            round(
                average_latency,
                4,
            ),

        "average_attempts_per_successful_case":
            round(
                average_attempts,
                4,
            ),

        "per_field_accuracy":
            per_field_accuracy,
    }


# =========================================================
# MAIN EVALUATION
# =========================================================

def evaluate_llm():

    rows = (
        load_challenge_set(
            CHALLENGE_FILE
        )
    )

    print()
    print(
        "=" * 70
    )

    print(
        "PAWCONNECT LLM-ONLY EVALUATION"
    )

    print(
        "=" * 70
    )

    print(
        "Model:",
        MODEL_NAME,
    )

    print(
        "Challenge samples:",
        len(
            rows
        ),
    )

    print(
        "Delay between requests:",
        (
            f"{REQUEST_DELAY_SECONDS} "
            "seconds"
        ),
    )

    results: list[
        dict[str, Any]
    ] = []

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for index, row in enumerate(
        rows,
        start=1,
    ):

        if index > 1:

            print()
            print(
                f"Waiting "
                f"{REQUEST_DELAY_SECONDS} "
                "seconds before next request..."
            )

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

        text = row[
            "text"
        ]

        expected = row.get(
            "expected",
            {},
        )

        case_id = row.get(
            "id",
            index,
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
            case_id,
        )

        print(
            "TEXT:",
            text,
        )

        try:

            (
                llm_result,
                latency,
                attempts,
            ) = run_llm_with_retry(
                text
            )

            predicted = (
                llm_result[
                    "structured_output"
                ]
            )

            evaluation = score_case(
                expected,
                predicted,
            )

            result = {
                "case_id":
                    case_id,

                "text":
                    text,

                "expected":
                    expected,

                "llm_output":
                    llm_result,

                "structured_llm_output":
                    predicted,

                "latency_seconds":
                    round(
                        latency,
                        4,
                    ),

                "attempts":
                    attempts,

                "evaluation":
                    evaluation,
            }

            print(
                "EXPECTED:",
                expected,
            )

            print(
                "PREDICTED:",
                predicted,
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

            print(
                "LATENCY:",
                (
                    f"{latency:.2f}s"
                ),
            )

            print(
                "ATTEMPTS:",
                attempts,
            )

        except Exception as exc:

            result = {
                "case_id":
                    case_id,

                "text":
                    text,

                "expected":
                    expected,

                "error":
                    str(
                        exc
                    ),
            }

            print(
                "ERROR:",
                exc,
            )

        results.append(
            result
        )

        # -------------------------------------------------
        # CHECKPOINT AFTER EVERY CASE
        # -------------------------------------------------

        LLM_RESULTS_FILE.write_text(

            json.dumps(
                results,
                indent=2,
                ensure_ascii=False,
            ),

            encoding="utf-8",
        )

    # =====================================================
    # SUMMARY
    # =====================================================

    summary = build_summary(
        results
    )

    LLM_RESULTS_FILE.write_text(

        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )

    LLM_SUMMARY_FILE.write_text(

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
        "LLM-ONLY SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        "Model:",
        summary[
            "model_name"
        ],
    )

    print(
        "Cases:",
        summary[
            "total_cases"
        ],
    )

    print(
        "Successful calls:",
        summary[
            "successful_calls"
        ],
    )

    print(
        "Failed calls:",
        summary[
            "failed_calls"
        ],
    )

    print(
        "Completion rate:",
        (
            f"{summary['completion_rate'] * 100:.2f}%"
        ),
    )

    print(
        "Preference extraction accuracy:",
        (
            f"{summary['preference_extraction_accuracy'] * 100:.2f}%"
        ),
    )

    print(
        "Exact accuracy among successful calls:",
        (
            f"{summary['successful_case_accuracy'] * 100:.2f}%"
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

    print(
        "Average latency:",
        (
            f"{summary['average_latency_seconds']:.2f}s"
        ),
    )

    print(
        "Average attempts:",
        summary[
            "average_attempts_per_successful_case"
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
        LLM_RESULTS_FILE,
    )

    print(
        "Summary saved:",
        LLM_SUMMARY_FILE,
    )

    print(
        "=" * 70
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    evaluate_llm()