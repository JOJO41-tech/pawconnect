"""
Descriptive statistics ("data card") for the synthetic v4 training
corpus and the two evaluation benchmarks.

Addresses reviewer requests to fully specify the synthetic data and
benchmarks so others can reproduce and extend them. Reports split
sizes, label frequencies, entity coverage, request length, sentence
(template) diversity, and cross-split sentence overlap.

Run:
    python evaluation/dataset_statistics.py
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
DATA_DIR = CURRENT_DIR.parent / "data"
RESULTS_DIR = CURRENT_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "dataset_statistics.json"

SPLITS = {
    "train": DATA_DIR / "pawconnect_v4_train.jsonl",
    "validation": DATA_DIR / "pawconnect_v4_validation.jsonl",
    "test": DATA_DIR / "pawconnect_v4_test.jsonl",
}
NL_BENCHMARK = CURRENT_DIR / "natural_language_challenge_60.jsonl"
REC_BENCHMARK = CURRENT_DIR / "recommendation_challenge_25.json"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [re.sub(r"\s+", " ", p.lower()).strip() for p in parts if p.strip()]


def describe_split(rows: list[dict]) -> dict:
    words = [len(r["text"].split()) for r in rows]
    label_counts = Counter(label for r in rows for label in r["labels"])
    entity_counts = Counter(
        key for r in rows for key, value in (r.get("entities") or {}).items() if value is not None
    )
    sentence_counts = Counter(s for r in rows for s in sentences(r["text"]))

    return {
        "samples": len(rows),
        "source_types": dict(Counter(r.get("source_type") for r in rows)),
        "words_per_request": {
            "mean": round(statistics.mean(words), 2),
            "median": statistics.median(words),
            "min": min(words),
            "max": max(words),
        },
        "labels_per_request_mean": round(statistics.mean(len(r["labels"]) for r in rows), 2),
        "label_frequency": dict(label_counts.most_common()),
        "entity_coverage": {k: round(v / len(rows), 4) for k, v in entity_counts.most_common()},
        "distinct_sentences": len(sentence_counts),
        "total_sentences": sum(sentence_counts.values()),
        "unique_request_texts": len({r["text"] for r in rows}),
    }


def main():
    splits = {name: load_jsonl(path) for name, path in SPLITS.items()}
    stats = {name: describe_split(rows) for name, rows in splits.items()}

    train_sentences = {s for r in splits["train"] for s in sentences(r["text"])}
    for name in ("validation", "test"):
        split_sentences = [s for r in splits[name] for s in sentences(r["text"])]
        stats[name]["sentence_overlap_with_train"] = round(
            sum(s in train_sentences for s in split_sentences) / len(split_sentences), 4
        )

    nl_rows = load_jsonl(NL_BENCHMARK)
    nl_sentences = [s for r in nl_rows for s in sentences(r["text"])]
    nl_stats = {
        "requests": len(nl_rows),
        "expected_fields": sum(len(r["expected"]) for r in nl_rows),
        "categories": dict(Counter(r.get("category") for r in nl_rows)),
        "field_frequency": dict(Counter(f for r in nl_rows for f in r["expected"]).most_common()),
        "sentence_overlap_with_train": round(
            sum(s in train_sentences for s in nl_sentences) / len(nl_sentences), 4
        ),
    }

    rec_rows = json.loads(REC_BENCHMARK.read_text(encoding="utf-8"))
    rec_stats = {
        "scenarios": len(rec_rows),
        "categories": dict(Counter(r.get("category") for r in rec_rows)),
        "animals_per_scenario_mean": round(statistics.mean(len(r["animals"]) for r in rec_rows), 2),
        "expected_modes": dict(Counter(r["expected"].get("mode") for r in rec_rows)),
    }

    output = {
        "training_corpus": stats,
        "natural_language_benchmark_60": nl_stats,
        "recommendation_benchmark_25": rec_stats,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=" * 72)
    print("PAWCONNECT DATASET STATISTICS")
    print("=" * 72)
    for name, s in stats.items():
        print(
            f"{name:<11} n={s['samples']:<5} words/request={s['words_per_request']['mean']:<6} "
            f"labels/request={s['labels_per_request_mean']:<5} distinct sentences={s['distinct_sentences']}"
            + (f"  overlap w/ train={s['sentence_overlap_with_train'] * 100:.1f}%"
               if "sentence_overlap_with_train" in s else "")
        )
    print(
        f"NL benchmark: {nl_stats['requests']} requests, {nl_stats['expected_fields']} fields, "
        f"sentence overlap with train = {nl_stats['sentence_overlap_with_train'] * 100:.1f}%"
    )
    print(f"Recommendation benchmark: {rec_stats['scenarios']} scenarios, modes {rec_stats['expected_modes']}")
    print()
    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
