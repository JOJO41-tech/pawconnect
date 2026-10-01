from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TRAIN_FILE = DATA_DIR / "pawconnect_v4_train.jsonl"
VAL_FILE = DATA_DIR / "pawconnect_v4_validation.jsonl"
TEST_FILE = DATA_DIR / "pawconnect_v4_test.jsonl"


def load_texts(path: Path) -> list[str]:
    texts = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            row = json.loads(line)

            text = row.get("text")

            if isinstance(text, str) and text.strip():
                texts.append(text.strip())

    return texts


def analyze_similarity(
    train_texts: list[str],
    target_texts: list[str],
    target_name: str,
):
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )

    all_texts = train_texts + target_texts

    matrix = vectorizer.fit_transform(all_texts)

    train_matrix = matrix[: len(train_texts)]
    target_matrix = matrix[len(train_texts):]

    similarities = cosine_similarity(
        target_matrix,
        train_matrix,
    )

    max_scores = similarities.max(axis=1)

    print()
    print("=" * 60)
    print(f"{target_name} → TRAIN SIMILARITY")
    print("=" * 60)

    print(
        "Average nearest-train similarity:",
        round(float(np.mean(max_scores)), 4),
    )

    print(
        "Median nearest-train similarity:",
        round(float(np.median(max_scores)), 4),
    )

    print(
        "Maximum similarity:",
        round(float(np.max(max_scores)), 4),
    )

    print(
        "Samples >= 0.90:",
        int(np.sum(max_scores >= 0.90)),
    )

    print(
        "Samples >= 0.80:",
        int(np.sum(max_scores >= 0.80)),
    )

    print(
        "Samples >= 0.70:",
        int(np.sum(max_scores >= 0.70)),
    )

    print()
    print("Top 10 most similar examples:")

    top_indices = np.argsort(
        max_scores
    )[-10:][::-1]

    for index in top_indices:
        best_train_index = int(
            np.argmax(
                similarities[index]
            )
        )

        print()
        print(
            "Similarity:",
            round(
                float(
                    max_scores[index]
                ),
                4,
            ),
        )

        print(
            "Target:",
            target_texts[index],
        )

        print(
            "Train:",
            train_texts[
                best_train_index
            ],
        )


def main():
    train_texts = load_texts(
        TRAIN_FILE
    )

    val_texts = load_texts(
        VAL_FILE
    )

    test_texts = load_texts(
        TEST_FILE
    )

    print(
        "Train:",
        len(train_texts),
    )

    print(
        "Validation:",
        len(val_texts),
    )

    print(
        "Test:",
        len(test_texts),
    )

    analyze_similarity(
        train_texts,
        val_texts,
        "VALIDATION",
    )

    analyze_similarity(
        train_texts,
        test_texts,
        "TEST",
    )


if __name__ == "__main__":
    main()