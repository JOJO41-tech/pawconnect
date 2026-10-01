from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
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
# IMPORT REAL PAWCONNECT PIPELINES
# =========================================================

from ml_engine import predict_ml_only

from app import (
    run_prediction,
    build_ranking_preferences,
)

from preference_standardizer import (
    standardize_preferences,
)

# Import the SAME structured-output function
# used by your 60-case Hybrid evaluation.
from evaluate_hybrid_set import (
    build_structured_output,
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
    / "inference_time_comparison.json"
)


# =========================================================
# BENCHMARK CONFIGURATION
# =========================================================

WARMUP_RUNS = 10

# 60 cases × 10 runs = 600 timed executions per system.
REPEATS_PER_CASE = 10


# Per-case Llama latencies saved by evaluate_llm_set.py
# (one end-to-end Groq API call per case, including network time).
LLAMA_RESULTS_FILE = (
    RESULTS_DIR
    / "llm_results_llama.json"
)

# Live Llama re-measurement (--live-llm): fewer repeats than the
# local systems to limit API cost and rate-limit pressure.
LLM_WARMUP_RUNS = 3
LLM_REPEATS_PER_CASE = 3


# =========================================================
# COMPUTE ENVIRONMENT
# =========================================================

def cpu_name() -> str:

    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                return str(
                    winreg.QueryValueEx(key, "ProcessorNameString")[0]
                ).strip()
        except OSError:
            pass

    cpuinfo = Path("/proc/cpuinfo")

    if cpuinfo.exists():
        for line in cpuinfo.read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()

    return platform.processor() or "unknown"


def total_memory_gb() -> float | None:

    try:
        if sys.platform == "win32":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / 1024 ** 3, 1)

        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / 1024 ** 3, 1)

    except (AttributeError, OSError, ValueError):
        return None


def package_version(name: str) -> str | None:

    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def collect_environment() -> dict[str, Any]:

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "cpu": cpu_name(),
        "logical_cpus": os.cpu_count(),
        "memory_gb": total_memory_gb(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "packages": {
            name: package_version(name)
            for name in ("scikit-learn", "numpy", "scipy", "joblib", "groq")
        },
        "timer": "time.perf_counter (single process, single thread, no GPU)",
    }


# =========================================================
# LOAD 60-CASE CHALLENGE
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

            text = row.get(
                "text"
            )

            if not isinstance(
                text,
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
# ML-ONLY PIPELINE
# =========================================================

def run_ml_only_pipeline(
    text: str,
) -> dict[str, Any]:

    return predict_ml_only(
        text
    )


# =========================================================
# FULL HYBRID PREFERENCE-UNDERSTANDING PIPELINE
# =========================================================

def run_hybrid_pipeline(
    text: str,
) -> dict[str, Any]:

    # -----------------------------------------------------
    # 1. TF-IDF + OvR Logistic Regression
    #    + semantic rules + entity extraction
    # -----------------------------------------------------

    prediction = (
        run_prediction(
            text
        )
    )

    # -----------------------------------------------------
    # 2. Convert prediction to ranking preferences
    # -----------------------------------------------------

    legacy_preferences = (
        build_ranking_preferences(
            prediction
        )
    )

    # -----------------------------------------------------
    # 3. Standardize preferences
    # -----------------------------------------------------

    standardized = (
        standardize_preferences(
            legacy_preferences,
            model_name="hybrid",
            original_prompt=text,
        )
    )

    # -----------------------------------------------------
    # 4. Produce same structured output
    #    used in 60-case experiment
    # -----------------------------------------------------

    structured_output = (
        build_structured_output(
            standardized
        )
    )

    return structured_output


# =========================================================
# LLAMA PIPELINE (live re-measurement only)
# =========================================================

def run_llm_pipeline(
    text: str,
) -> dict[str, Any]:

    # Imported lazily: llm_engine requires GROQ_API_KEY at import.
    from llm_engine import predict_llm_only

    return predict_llm_only(
        text
    )


# =========================================================
# SAVED LLAMA LATENCY
# =========================================================

def saved_llama_latency() -> dict[str, Any]:

    rows = json.loads(
        LLAMA_RESULTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    latencies = [
        row["latency_seconds"]
        for row in rows
        if row.get("latency_seconds") is not None
    ]

    attempts = [
        row.get("attempts", 1)
        for row in rows
    ]

    mean_latency = statistics.mean(
        latencies
    )

    return {
        "system": "Llama 3.3 70B Versatile (saved evaluation run)",
        "cases": len(latencies),
        "warmup_runs_excluded": 0,
        "repeats_per_case": 1,
        "total_timed_runs": len(latencies),
        "mean_seconds": mean_latency,
        "mean_ms": mean_latency * 1000,
        "median_ms": statistics.median(latencies) * 1000,
        "p95_ms": percentile(latencies, 95) * 1000,
        "minimum_ms": min(latencies) * 1000,
        "maximum_ms": max(latencies) * 1000,
        "std_ms": (
            statistics.stdev(latencies) * 1000
            if len(latencies) > 1
            else 0.0
        ),
        "mean_attempts_per_case": statistics.mean(attempts),
        "statistics_over": "single call per case",
        "source_file": LLAMA_RESULTS_FILE.name,
    }


# =========================================================
# PERCENTILE
# =========================================================

def percentile(
    values: list[float],
    percentile_value: float,
) -> float:

    if not values:
        return 0.0

    sorted_values = sorted(
        values
    )

    index = (
        percentile_value
        / 100
        * (
            len(sorted_values)
            - 1
        )
    )

    lower = int(
        index
    )

    upper = min(
        lower + 1,
        len(sorted_values) - 1,
    )

    fraction = (
        index - lower
    )

    return (
        sorted_values[lower]
        * (1 - fraction)
        +
        sorted_values[upper]
        * fraction
    )


# =========================================================
# BENCHMARK FUNCTION
# =========================================================

def benchmark_system(
    name: str,
    function,
    cases: list[
        dict[str, Any]
    ],
    warmup_runs: int = WARMUP_RUNS,
    repeats_per_case: int = REPEATS_PER_CASE,
) -> dict[str, Any]:

    print()
    print(
        "=" * 72
    )

    print(
        f"BENCHMARKING {name}"
    )

    print(
        "=" * 72
    )

    # -----------------------------------------------------
    # Warm-up
    # -----------------------------------------------------

    warmup_text = (
        cases[0][
            "text"
        ]
    )

    print(
        f"Warm-up runs (excluded from timing): {warmup_runs}"
    )

    for _ in range(
        warmup_runs
    ):

        function(
            warmup_text
        )

    # -----------------------------------------------------
    # Timed runs
    # -----------------------------------------------------

    case_latencies: list[
        float
    ] = []

    all_run_latencies: list[
        float
    ] = []

    for case_number, case in enumerate(
        cases,
        start=1,
    ):

        text = case[
            "text"
        ]

        repeated_times: list[
            float
        ] = []

        for _ in range(
            repeats_per_case
        ):

            start = (
                time.perf_counter()
            )

            function(
                text
            )

            end = (
                time.perf_counter()
            )

            elapsed = (
                end - start
            )

            repeated_times.append(
                elapsed
            )

            all_run_latencies.append(
                elapsed
            )

        case_mean = (
            statistics.mean(
                repeated_times
            )
        )

        case_latencies.append(
            case_mean
        )

        print(
            f"Case {case_number:02d}/"
            f"{len(cases)}: "
            f"{case_mean * 1000:.3f} ms"
        )

    # -----------------------------------------------------
    # Statistics
    # -----------------------------------------------------

    mean_latency = (
        statistics.mean(
            case_latencies
        )
    )

    median_latency = (
        statistics.median(
            case_latencies
        )
    )

    minimum_latency = min(
        case_latencies
    )

    maximum_latency = max(
        case_latencies
    )

    std_latency = (
        statistics.stdev(
            case_latencies
        )
        if len(
            case_latencies
        ) > 1
        else 0.0
    )

    p95_latency = percentile(
        case_latencies,
        95,
    )

    total_runs = (
        len(cases)
        * repeats_per_case
    )

    throughput = (
        1 / mean_latency
        if mean_latency > 0
        else 0.0
    )

    result = {

        "system": name,

        "cases": len(
            cases
        ),

        "warmup_runs_excluded": (
            warmup_runs
        ),

        "repeats_per_case": (
            repeats_per_case
        ),

        "total_timed_runs": (
            total_runs
        ),

        "mean_seconds": (
            mean_latency
        ),

        "mean_ms": (
            mean_latency
            * 1000
        ),

        "median_ms": (
            median_latency
            * 1000
        ),

        "p95_ms": (
            p95_latency
            * 1000
        ),

        "minimum_ms": (
            minimum_latency
            * 1000
        ),

        "maximum_ms": (
            maximum_latency
            * 1000
        ),

        "std_ms": (
            std_latency
            * 1000
        ),

        "statistics_over":
            "per-case mean latency",

        "requests_per_second": (
            throughput
        ),
    }

    print()
    print(
        f"Mean:       "
        f"{result['mean_ms']:.3f} ms"
    )

    print(
        f"Median:     "
        f"{result['median_ms']:.3f} ms"
    )

    print(
        f"P95:        "
        f"{result['p95_ms']:.3f} ms"
    )

    print(
        f"Minimum:    "
        f"{result['minimum_ms']:.3f} ms"
    )

    print(
        f"Maximum:    "
        f"{result['maximum_ms']:.3f} ms"
    )

    print(
        f"Std. dev.:  "
        f"{result['std_ms']:.3f} ms"
    )

    print(
        f"Throughput: "
        f"{result['requests_per_second']:.2f} "
        f"requests/sec"
    )

    return result


# =========================================================
# MAIN
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--live-llm",
        action="store_true",
        help=(
            "Re-measure Llama 3.3 70B through the Groq API with "
            "warm-up and repeats (requires GROQ_API_KEY). "
            "Default: summarize the saved evaluation latencies."
        ),
    )

    args = parser.parse_args()

    environment = collect_environment()

    cases = (
        load_challenge_set(
            CHALLENGE_FILE
        )
    )

    print()
    print(
        "=" * 72
    )

    print(
        "PAWCONNECT INFERENCE-TIME COMPARISON"
    )

    print(
        "=" * 72
    )

    print(
        "Challenge cases:",
        len(
            cases
        ),
    )

    print(
        "Repeats per case:",
        REPEATS_PER_CASE,
    )

    print(
        "Timed local runs per system:",
        (
            len(cases)
            * REPEATS_PER_CASE
        ),
    )

    print(
        "Warm-up runs (excluded):",
        WARMUP_RUNS,
    )

    print(
        f"CPU: {environment['cpu']} "
        f"({environment['logical_cpus']} logical), "
        f"RAM: {environment['memory_gb']} GB"
    )

    print(
        f"OS: {environment['os']}, "
        f"Python {environment['python']}"
    )

    # =====================================================
    # ML-ONLY
    # =====================================================

    ml_result = (
        benchmark_system(
            "ML-only",
            run_ml_only_pipeline,
            cases,
        )
    )

    # =====================================================
    # FULL HYBRID
    # =====================================================

    hybrid_result = (
        benchmark_system(
            "Hybrid AI",
            run_hybrid_pipeline,
            cases,
        )
    )

    # =====================================================
    # LLAMA
    # =====================================================

    llm_settings = {
        "provider": "Groq Cloud API (groq Python SDK)",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0,
        "response_format": "json_object",
        "measurement": (
            "end-to-end client-side latency per request, "
            "including network and API queueing time"
        ),
    }

    if args.live_llm:

        llama_result = benchmark_system(
            "Llama 3.3 70B Versatile (live)",
            run_llm_pipeline,
            cases,
            warmup_runs=LLM_WARMUP_RUNS,
            repeats_per_case=LLM_REPEATS_PER_CASE,
        )

        llama_result.update(llm_settings)

    else:

        llama_result = saved_llama_latency()
        llama_result.update(llm_settings)


    # =====================================================
    # SPEEDUP
    # =====================================================

    llama_vs_ml = (
        llama_result[
            "mean_ms"
        ]
        / ml_result[
            "mean_ms"
        ]
    )

    llama_vs_hybrid = (
        llama_result[
            "mean_ms"
        ]
        / hybrid_result[
            "mean_ms"
        ]
    )

    hybrid_vs_ml = (
        hybrid_result[
            "mean_ms"
        ]
        / ml_result[
            "mean_ms"
        ]
    )


    # =====================================================
    # FINAL TABLE
    # =====================================================

    print()
    print(
        "=" * 72
    )

    print(
        "FINAL INFERENCE-TIME COMPARISON"
    )

    print(
        "=" * 72
    )

    print(
        f"{'Approach':<28}"
        f"{'Mean Latency':>18}"
        f"{'Relative':>18}"
    )

    print(
        "-" * 64
    )

    print(
        f"{'ML-only':<28}"
        f"{ml_result['mean_ms']:>15.3f} ms"
        f"{'1.00x':>18}"
    )

    print(
        f"{'Hybrid AI':<28}"
        f"{hybrid_result['mean_ms']:>15.3f} ms"
        f"{hybrid_vs_ml:>17.2f}x"
    )

    print(
        f"{'Llama 3.3 70B':<28}"
        f"{llama_result['mean_ms']:>15.3f} ms"
        f"{llama_vs_ml:>17.2f}x"
    )

    print()
    print(
        f"Llama / Hybrid latency ratio: "
        f"{llama_vs_hybrid:.2f}x"
    )

    print(
        f"Llama / ML latency ratio: "
        f"{llama_vs_ml:.2f}x"
    )

    print(
        f"Hybrid / ML latency ratio: "
        f"{hybrid_vs_ml:.2f}x"
    )


    # =====================================================
    # SAVE RESULTS
    # =====================================================

    comparison = {

        "benchmark": {
            "challenge_cases":
                len(
                    cases
                ),

            "warmup_runs":
                WARMUP_RUNS,

            "repeats_per_case":
                REPEATS_PER_CASE,

            "scope":
                (
                    "Preference-understanding "
                    "inference"
                ),

            "llama_measurement":
                (
                    "live re-measurement"
                    if args.live_llm
                    else "saved evaluation run"
                ),
        },

        "environment":
            environment,

        "ml_only":
            ml_result,

        "hybrid_ai":
            hybrid_result,

        "llama_3_3_70b":
            llama_result,

        "latency_ratios": {

            "llama_vs_ml":
                llama_vs_ml,

            "llama_vs_hybrid":
                llama_vs_hybrid,

            "hybrid_vs_ml":
                hybrid_vs_ml,
        },
    }

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(

        json.dumps(
            comparison,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )

    print()
    print(
        "Results saved to:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "=" * 72
    )


if __name__ == "__main__":

    main()