"""Teacher item 6: human-readable ground truth for the two author-built benchmarks.
Writes results/ground_truth/benchmark60_ground_truth.csv (one row per expected field; null = must NOT be predicted)
and results/ground_truth/scenarios25_ground_truth.csv. Run from ai/: python evaluation/export_ground_truth.py"""
import csv, json
from pathlib import Path
EV = Path(__file__).resolve().parent; OUT = EV / "results" / "ground_truth"; OUT.mkdir(parents=True, exist_ok=True)
b60 = [json.loads(l) for l in open(EV / "natural_language_challenge_60.jsonl", encoding="utf-8") if l.strip()]
with open(OUT / "benchmark60_ground_truth.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["request_id", "category", "text", "field", "expected_value", "positive_field (null = the 1 negative expectation; 149 positive + 1 negative = 150 fields)"])
    n = 0
    for r in b60:
        for k, v in r["expected"].items():
            w.writerow([r["id"], r.get("category", ""), r["text"], k, "null (must not be predicted)" if v is None else json.dumps(v), v is not None]); n += v is not None
s25 = json.load(open(EV / "recommendation_challenge_25.json", encoding="utf-8"))
with open(OUT / "scenarios25_ground_truth.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["scenario_id", "category", "required", "preferred", "n_animals", "animal_ids", "expected_mode", "expected_top1_id", "allowed_pet_type"])
    for s in s25:
        e = s["expected"]
        w.writerow([s["id"], s.get("category", ""), json.dumps(s["preferences"].get("required", {})), json.dumps(s["preferences"].get("preferred", {})),
                    len(s["animals"]), " ".join(str(a["id"]) for a in s["animals"]), e.get("mode"), e.get("top1_id"), e.get("allowed_pet_type")])
print(f"60-request benchmark: {len(b60)} requests, {n} expected non-null fields; 25 scenarios -> {OUT}")
