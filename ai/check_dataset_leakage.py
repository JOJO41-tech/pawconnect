from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TRAIN_FILE = DATA_DIR / "pawconnect_v4_train.jsonl"
VAL_FILE = DATA_DIR / "pawconnect_v4_validation.jsonl"
TEST_FILE = DATA_DIR / "pawconnect_v4_test.jsonl"


def normalize_text(text: str) -> str:
    text = text.lower().strip()

    text = re.sub(
        r"[^\w\s]",
        "",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def load_dataset(path: Path):
    rows = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:

            if not line.strip():
                continue

            row = json.loads(line)

            rows.append(
                {
                    "text": row["text"],
                    "normalized_text": normalize_text(
                        row["text"]
                    ),
                    "labels": sorted(
                        row["labels"]
                    ),
                }
            )

    return rows


def duplicate_count(rows):
    texts = [
        row["normalized_text"]
        for row in rows
    ]

    counts = Counter(texts)

    duplicates = {
        text: count
        for text, count in counts.items()
        if count > 1
    }

    return duplicates


def find_overlap(
    first,
    second,
):
    first_texts = {
        row["normalized_text"]
        for row in first
    }

    second_texts = {
        row["normalized_text"]
        for row in second
    }

    return (
        first_texts
        & second_texts
    )


def print_overlap(
    title,
    overlap,
):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    print(
        "Overlapping texts:",
        len(overlap),
    )

    for text in list(overlap)[:20]:
        print(
            "-",
            text,
        )


def main():

    train = load_dataset(
        TRAIN_FILE
    )

    validation = load_dataset(
        VAL_FILE
    )

    test = load_dataset(
        TEST_FILE
    )

    print(
        "Train samples:",
        len(train),
    )

    print(
        "Validation samples:",
        len(validation),
    )

    print(
        "Test samples:",
        len(test),
    )

    print()
    print("=" * 60)
    print("DUPLICATES INSIDE EACH SPLIT")
    print("=" * 60)

    train_duplicates = duplicate_count(
        train
    )

    validation_duplicates = duplicate_count(
        validation
    )

    test_duplicates = duplicate_count(
        test
    )

    print(
        "Train duplicate texts:",
        len(train_duplicates),
    )

    print(
        "Validation duplicate texts:",
        len(validation_duplicates),
    )

    print(
        "Test duplicate texts:",
        len(test_duplicates),
    )

    train_val_overlap = find_overlap(
        train,
        validation,
    )

    train_test_overlap = find_overlap(
        train,
        test,
    )

    val_test_overlap = find_overlap(
        validation,
        test,
    )

    print_overlap(
        "TRAIN ↔ VALIDATION",
        train_val_overlap,
    )

    print_overlap(
        "TRAIN ↔ TEST",
        train_test_overlap,
    )

    print_overlap(
        "VALIDATION ↔ TEST",
        val_test_overlap,
    )

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_cross_split_overlap = (
        len(train_val_overlap)
        + len(train_test_overlap)
        + len(val_test_overlap)
    )

    if total_cross_split_overlap == 0:
        print(
            "✓ No exact text overlap found "
            "between dataset splits."
        )
    else:
        print(
            "⚠ Cross-split overlap detected."
        )

        print(
            "This may artificially inflate "
            "evaluation performance."
        )


if __name__ == "__main__":
    main()