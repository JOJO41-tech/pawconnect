"""Weight-sensitivity analysis for PawConnect's preferred-score weights.
Uses the 1,000 generated ranking scenarios and their weight-INDEPENDENT relevance labels
(scenario_generator.relevance counts matched preferences, unweighted)."""
import copy, json, math, random, sys
from pathlib import Path
import numpy as np
from scipy.stats import kendalltau
AI = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(AI))
GEN = Path(__file__).resolve().parent; sys.path.insert(0, str(GEN))
import scoring_engine
from ranking import rank_animals
from scenario_generator import relevance

SC = json.load(open(GEN / "generated_ranking_scenarios.json"))
KEYS = ["energy_level", "temperament", "apartment_friendly", "experience_level", "available_attention_hours", "child_friendly", "pet_friendly"]
CURRENT = dict(scoring_engine.WEIGHTS)
roc = [sum(1 / j for j in range(i, 8)) / 7 for i in range(1, 8)]
SETS = {"current (20/20/15/15/10/10/10)": CURRENT,
        "equal": {k: 1.0 for k in KEYS},
        "rank-order centroid": dict(zip(KEYS, roc))}
rng = random.Random(2026)
RANDOM = [{k: CURRENT[k] * rng.uniform(0.5, 1.5) for k in KEYS} for _ in range(100)]
K = 5

def dcg(g): return sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(g))

def run(weights):
    scoring_engine.WEIGHTS.clear(); scoring_engine.WEIGHTS.update(weights)
    rankings, nd = [], []
    for sc in SC:
        res = rank_animals(copy.deepcopy(sc["animals"]), copy.deepcopy(sc["preferences"]), 20)
        ids = [r["id"] for r in res["recommendations"]]
        grade = {a["id"]: relevance(a, sc["preferences"]) for a in sc["animals"]}
        ideal = dcg(sorted(grade.values(), reverse=True)[:K])
        nd.append(dcg([grade[i] for i in ids[:K]]) / ideal if ideal else np.nan)
        rankings.append(ids)
    return rankings, np.array(nd)

base_rank, base_nd = run(CURRENT)
out = {"n_scenarios": len(SC), "k": K, "sets": {}}
def compare(name, w):
    rk, nd = run(w)
    taus, top1, jac = [], [], []
    for a, b in zip(base_rank, rk):
        if len(a) >= 2 and set(a) == set(b):
            pos = {x: i for i, x in enumerate(b)}; t = kendalltau(range(len(a)), [pos[x] for x in a]).statistic
            if not np.isnan(t): taus.append(t)
        if a and b: top1.append(a[0] == b[0])
        A, B = set(a[:K]), set(b[:K])
        if A | B: jac.append(len(A & B) / len(A | B))
    return dict(ndcg5=float(np.nanmean(nd)), delta_ndcg5_vs_current=float(np.nanmean(nd - base_nd)),
                kendall_tau_mean=float(np.mean(taus)), top1_agreement=float(np.mean(top1)), top5_jaccard=float(np.mean(jac)))
for name, w in SETS.items():
    out["sets"][name] = compare(name, w)
R = [compare(f"rand{i}", w) for i, w in enumerate(RANDOM)]
out["random_perturbation_x0.5_to_1.5_100draws"] = {m: {"mean": float(np.mean([r[m] for r in R])), "min": float(np.min([r[m] for r in R])), "max": float(np.max([r[m] for r in R]))} for m in R[0]}
scoring_engine.WEIGHTS.clear(); scoring_engine.WEIGHTS.update(CURRENT)
out["roc_weights"] = dict(zip(KEYS, [round(x, 4) for x in roc]))
out["pref_fields_used_in_scenarios"] = sorted({k for s in SC for k in s["preferences"]["preferred"]})
json.dump(out, open("" + str(Path(__file__).resolve().parent / "results" / "weight_sensitivity.json") + "", "w"), indent=1)
print(json.dumps(out, indent=1))
