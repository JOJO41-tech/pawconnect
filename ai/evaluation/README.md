# PawConnect evaluation

All scripts are run from the `ai/` directory and write their outputs to `evaluation/results/`.

## Benchmarks

| File | Contents |
|---|---|
| `natural_language_challenge_60.jsonl` | 60 author-written requests, 150 expected fields (preference understanding) |
| `recommendation_challenge_25.json` | 25 controlled scenarios with expected mode and top-1 animal (recommendation logic) |
| `generated_ranking_scenarios.json` | 1,000 seeded scenarios, 20 animals each (created by `evaluate_ranking_metrics.py`) |
| `adversarial_constraint_scenarios.json` | 1,000 seeded adversarial scenarios (created by `evaluate_adversarial_constraints.py`) |

JSONL format for a preference benchmark (one request per line):

```json
{"id": "R001", "category": "free_form", "text": "<request as written by the adopter>", "expected": {"pet_type": "cat", "apartment_friendly": true}}
```

## Scripts

| Script | Purpose |
|---|---|
| `evaluate_hybrid_set.py [--input FILE]` | Hybrid pipeline on the 60-request set, or on another JSONL set in the format above |
| `evaluate_challenge_set.py`, `evaluate_llm_set.py` | ML-only and Llama 3.3 70B baselines (Llama needs `GROQ_API_KEY`) |
| `evaluate_ablation.py`, `calculate_attribute_f1.py` | Component ablation and attribute-level F1 |
| `statistical_significance.py` | Bootstrap 95% CIs; McNemar, Wilcoxon and paired-bootstrap tests between systems |
| `cross_validate_model.py` | 5-fold cross-validation of the TF-IDF + OvR LR classifier (thresholds tuned inside each fold) |
| `evaluate_recommendation_reasoning.py` | 25 controlled recommendation scenarios |
| `evaluate_ranking_metrics.py` | NDCG@k, MAP@k, Hit Rate@k, MRR against aggregate-score, filter-only and random baselines |
| `evaluate_adversarial_constraints.py` | Tests whether high soft-preference scores can override hard constraints (pet type, availability) |
| `benchmark_inference_time.py [--live-llm]` | Latency with warm-up excluded, 10 repeats per case, and the compute environment recorded |
| `dataset_statistics.py` | Data card: split sizes, label and entity frequencies, sentence diversity, train/benchmark overlap |

## Collecting real adopter requests

To evaluate on language the system was not designed around:

1. Collect 20–30 free-form requests from people who did not build the system, such as shelter inquiry emails or a short survey.
2. Have two annotators label the `expected` fields independently and resolve disagreements.
3. Save the labeled requests as `real_requests.jsonl` in the format above.
4. Run `python evaluation/evaluate_hybrid_set.py --input evaluation/real_requests.jsonl`.

## Note on relevance labels

Relevance in the generated ranking and adversarial scenarios comes from the intended recommendation policy (`scenario_generator.relevance`). These results therefore measure how faithfully each ranker implements that policy. They do not measure adopter satisfaction.
