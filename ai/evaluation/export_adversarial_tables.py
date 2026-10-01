"""Teacher item 5: per-case adversarial tables (test cases, expected vs actual, pass rate, violation rate).

Collects three adversarial suites into CSV files under results/adversarial_tables/:
  1. adversarial_1000_cases.csv   - 1,000 seeded scenarios (evaluate_adversarial_constraints.py, seed 20260930)
  2. structured_traps_20_cases.csv - 20 hand-built soft-preference traps (evaluate_adversarial_traps.py)
  3. language_traps_16_cases.csv   - 16 adversarial phrasings through the parser (evaluate_language_traps.py)
  4. adversarial_summary.csv       - pass rate and violation rate per family and system, with exact 95% CIs
Run from ai/:  python evaluation/export_adversarial_tables.py
(runs the three suites first if their result files are missing)
"""
import csv, json, random, subprocess, sys
from pathlib import Path
from scipy.stats import binomtest
EV = Path(__file__).resolve().parent; AI = EV.parent; sys.path[:0] = [str(AI), str(EV)]
OUT = EV / "results" / "adversarial_tables"; OUT.mkdir(parents=True, exist_ok=True)
import evaluate_adversarial_constraints as adv
from scenario_generator import violates_hard_constraint

def ci(k, n):
    c = binomtest(k, n).proportion_ci(method="exact"); return f"[{100*c.low:.1f}%, {100*c.high:.1f}%]"
def short(a): return f'{a["id"]}:{a.get("type")}/{a.get("size")}/{a.get("adoption_status","available")}'

summary = []
# ---------- 1. 1,000 seeded scenarios ----------
rng = random.Random(20260930)
scen = [adv.build_scenario(f, i, rng) for f in adv.FAMILIES for i in range(1, 251)]
rows = []
for s in scen:
    req = s["preferences"]["required"]
    exp = "no recommendation (requested species absent)" if s["expected_empty"] else \
          f'top-1 is an available {req["pet_type"]}; no {("adopted animal" if s["family"]=="unavailable_decoy" else "other-species animal")} in top-5'
    row = {"case_id": s["id"], "family": s["family"], "required": json.dumps(req), "preferred": json.dumps(s["preferences"]["preferred"]),
           "n_animals": len(s["animals"]), "n_decoys": sum(violates_hard_constraint(a, s["preferences"]) for a in s["animals"]), "expected": exp}
    for name, fn in (("pawconnect", adv.pawconnect), ("aggregate", adv.aggregate)):
        recs = fn(s); j = adv.judge(s, recs)
        row[f"{name}_actual_top5"] = " | ".join(short(a) for a in recs) or "(empty)"
        row[f"{name}_pass"] = int(j["correct"]); row[f"{name}_violation"] = int(j["violated"])
    rows.append(row)
with open(OUT / "adversarial_1000_cases.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for fam in adv.FAMILIES + ["all"]:
    sub = [r for r in rows if fam in ("all", r["family"])]
    for name, label in (("pawconnect", "PawConnect"), ("aggregate", "Aggregate-score baseline")):
        p = sum(r[f"{name}_pass"] for r in sub); v = sum(r[f"{name}_violation"] for r in sub); n = len(sub)
        summary.append({"suite": "1,000 seeded scenarios", "family": fam, "system": label, "cases": n, "passed": p,
                        "pass_rate": f"{100*p/n:.1f}%", "pass_rate_95CI": ci(p, n), "violating_cases": v,
                        "violation_rate": f"{100*v/n:.1f}%", "violation_rate_95CI": ci(v, n)})

# ---------- 2. structured traps ----------
f2 = EV / "results" / "adversarial_results.json"
if not f2.exists(): subprocess.run([sys.executable, str(EV / "evaluate_adversarial_traps.py")], check=True, cwd=AI)
d = json.load(open(f2))
EXPECT = {"E": "exact mode; trap never in top-k; every item satisfies all required constraints",
          "F": "alternative mode; species never violated; every relaxed constraint disclosed",
          "N": "no recommendation (requested species absent)",
          "O": "alternative that fails fewer required constraints ranks first"}
rows2 = [{"case_id": r["id"], "family": r["family"], "expected": EXPECT[r["family"]], "actual_mode": r["mode"],
          "pawconnect_actual_top": " ".join(map(str, r["pawconnect_top"])) or "(empty)", "pawconnect_pass": int(r["pass"]),
          "pawconnect_hard_violating_items": r["pc_hard_violations_topk"], "pawconnect_species_violating_items": r["pc_species_violations"],
          "undisclosed_violations": r["undisclosed_violations"], "baseline_actual_top": " ".join(map(str, r["baseline_top"])),
          "baseline_trap_rank1": int(r["bl_trap_rank1"]), "baseline_hard_violating_items": r["bl_hard_violations_topk"],
          "MR_deterministic_100_runs": int(r["MR_determinism_100runs"]), "MR_order_invariant_20_shuffles": int(r["MR_order_invariance_20shuffles"]),
          "MR_trap_removal_invariant": "" if "MR_trap_removal_invariance" not in r else int(r["MR_trap_removal_invariance"])} for r in d["rows"]]
with open(OUT / "structured_traps_20_cases.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows2[0])); w.writeheader(); w.writerows(rows2)
raw = {r["id"]: r for r in d["rows"]}
def must_not_violate(r, who):  # family-specific: what may never be violated
    if r["family"] == "E": return r[f"{who}_hard_violations_topk"]          # any required constraint
    if r["family"] in ("F", "N"): return r[f"{who}_species_violations"]       # species (other constraints may be relaxed, disclosed)
    return None                                                               # O: relaxation by design, ordering only
def baseline_pass(r):
    if r["family"] == "E": return not r["bl_trap_in_topk"]
    if r["family"] in ("F", "N"): return r["bl_species_violations"] == 0 and (r["family"] != "N" or not r["baseline_top"])
    return r["baseline_top"][:1] == [1]
for fam in ["E", "F", "N", "O", "E+F+N"]:
    sub = [raw[r["case_id"]] for r in rows2 if r["family"] in fam.split("+")]
    n = len(sub)
    for who, label, passf in (("pc", "PawConnect", lambda r: r["pass"]), ("bl", "Aggregate-score baseline", baseline_pass)):
        p = sum(bool(passf(r)) for r in sub)
        vs = [must_not_violate(r, who) for r in sub]
        if any(v is None for v in vs): v_txt, v_ci, v_n = "n/a (relaxation by design)", "", ""
        else: v_n = sum(v > 0 for v in vs); v_txt, v_ci = f"{100*v_n/n:.1f}%", ci(v_n, n)
        summary.append({"suite": "20 structured traps", "family": fam, "system": label, "cases": n, "passed": p, "pass_rate": f"{100*p/n:.1f}%",
                        "pass_rate_95CI": ci(p, n), "violating_cases": v_n, "violation_rate": v_txt, "violation_rate_95CI": v_ci})

# ---------- 3. language traps ----------
f3 = EV / "results" / "language_trap_results.json"
if not f3.exists(): subprocess.run([sys.executable, str(EV / "evaluate_language_traps.py")], check=True, cwd=AI)
d3 = json.load(open(f3))
rows3 = [{"case_id": r["id"], "category": r["category"], "text": r["text"], "expected_hard_constraints": json.dumps(r["gold"]),
          "hybrid_actual": json.dumps(r["Hybrid"]["pred_hard"]), "hybrid_species_pass": int(r["Hybrid"]["species_ok"]), "hybrid_all_hard_pass": int(r["Hybrid"]["all_hard_ok"]),
          "ml_only_actual": json.dumps(r["ML-only"]["pred_hard"]), "ml_only_species_pass": int(r["ML-only"]["species_ok"]), "ml_only_all_hard_pass": int(r["ML-only"]["all_hard_ok"])} for r in d3["rows"]]
with open(OUT / "language_traps_16_cases.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows3[0])); w.writeheader(); w.writerows(rows3)
for sysname, key in (("Hybrid", "hybrid"), ("ML-only", "ml_only")):
    n = len(rows3)
    for what in ("species", "all_hard"):
        p = sum(r[f"{key}_{what}_pass"] for r in rows3)
        summary.append({"suite": "16 language traps (parser)", "family": f"{what.replace('_', ' ')} extraction", "system": sysname, "cases": n, "passed": p,
                        "pass_rate": f"{100*p/n:.1f}%", "pass_rate_95CI": ci(p, n), "violating_cases": n - p,
                        "violation_rate": f"{100*(n-p)/n:.1f}% (wrong/missing)", "violation_rate_95CI": ci(n - p, n)})
with open(OUT / "adversarial_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
for s in summary: print(f'{s["suite"]:<28}{s["family"]:<24}{s["system"]:<26}{s["passed"]:>5}/{s["cases"]:<5} pass {s["pass_rate"]:>7} {s["pass_rate_95CI"]:<18} viol {s["violation_rate"]}')
