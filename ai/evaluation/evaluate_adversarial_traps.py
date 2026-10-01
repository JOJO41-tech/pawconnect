"""Adversarial 'soft-preference trap' suite for PawConnect's ranking logic (Stage 2, structured input).

Each trap animal violates exactly the hard constraint(s) under test but matches EVERY soft preference,
while compliant animals match few or none. A ranker that lets soft scores compensate for hard constraints
will surface the trap; PawConnect should not (except by-design relaxations in Alternative mode, which must be disclosed).
"""
import copy, json, random, sys, hashlib
from pathlib import Path
AI = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(AI))
from ranking import rank_animals
from filter_engine import evaluate_required_constraints
from scoring_engine import WEIGHTS, calculate_preferred_score

K = 4
SOFT = {"energy_level": "low", "temperament": ["calm", "friendly"], "apartment_friendly": True,
        "child_friendly": True, "pet_friendly": True, "experience_level": "beginner", "available_attention_hours": 2}
PERFECT = dict(energy_level="low", temperament="calm, friendly", apartment_friendly=True, child_friendly=True,
               pet_friendly=True, experience_required="beginner", daily_attention_hours=2)
POOR = dict(energy_level="high", temperament="independent", apartment_friendly=False, child_friendly=False,
            pet_friendly=False, experience_required="experienced", daily_attention_hours=6)
FAIR = dict(POOR, energy_level="low")  # matches 1 of 7 soft prefs
BASE = {"dog": dict(type="dog", breed="Poodle", gender="female", size="small", location="Bangkok", age="2 years"),
        "cat": dict(type="cat", breed="Persian", gender="female", size="small", location="Bangkok", age="2 years")}
OTHER = {"dog": "cat", "cat": "dog"}
VIOLATE = {"gender": ("gender", "male"), "size": ("size", "large"), "breed": None, "location": ("location", "Chiang Mai"),
           "age": ("age", "7 years")}
REQ_KEY = {"gender": "gender", "size": "size", "breed": "breed", "location": "location", "age": "age_years"}

def animal(i, name, attrs, soft):
    return dict(id=i, name=name, adoption_status="available", **attrs, **soft)

def violate(s, x, attrs):
    a = dict(attrs)
    if x == "pet_type": a["type"] = OTHER[s]; a["breed"] = BASE[OTHER[s]]["breed"]
    elif x == "breed": a["breed"] = "Beagle" if s == "dog" else "Siamese"
    else: k, v = VIOLATE[x]; a[k] = v
    return a

def req_for(s, x):
    r = {"pet_type": s}
    if x not in ("pet_type",):
        r[REQ_KEY[x]] = 2.0 if x == "age" else BASE[s][{"age_years": "age"}.get(REQ_KEY[x], REQ_KEY[x])]
    return r

# ---------------- baseline: single aggregate (compensatory) score, no filtering ----------------
def aggregate_baseline(animals, prefs):
    req = prefs["required"]
    out = []
    for a in animals:
        ev = evaluate_required_constraints(a, req)
        hard_pts = 20.0 * len(ev["matched_constraints"]); hard_max = 20.0 * len(req)
        ps = calculate_preferred_score(a, prefs["preferred"], {})
        earned = hard_pts + ps.get("earned_weight", ps.get("earned", 0)); possible = hard_max + ps.get("possible_weight", ps.get("possible", 0))
        out.append((earned / possible if possible else 0, -int(a["id"]), a))
    out.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [t[2] for t in out[:K]]

def violates(a, req): return not evaluate_required_constraints(a, req)["is_match"]
def species_ok(a, req): return a["type"] == req["pet_type"]
def sig(res): return hashlib.sha256(json.dumps([(r["id"], r["compatibility_score"]) for r in res["recommendations"]] + [res["mode"]]).encode()).hexdigest()

scenarios = []
# Family E: exact-mode traps (a compliant animal exists)
for s in ("dog", "cat"):
    for x in ("pet_type", "gender", "size", "breed", "location", "age"):
        req = req_for(s, x)
        cat = [animal(1, "TRAP", violate(s, x, BASE[s]), PERFECT),
               animal(2, "Compliant-A", BASE[s], FAIR), animal(3, "Compliant-B", BASE[s], POOR),
               animal(4, "Decoy-1", violate(s, "pet_type", BASE[s]), PERFECT),
               animal(5, "TRAP-2", violate(s, x, dict(BASE[s], size="medium") if x != "size" else BASE[s]), PERFECT)]
        scenarios.append(dict(id=f"E-{s}-{x}", family="E", species=s, violated=x, prefs={"required": req, "preferred": SOFT}, animals=cat, trap_ids=None))
# Family F: fallback with species trap (no fully compliant animal)
for s in ("dog", "cat"):
    req = {"pet_type": s, "gender": "female", "location": "Bangkok"}
    for variant, same_species_attrs in (("fails-gender", dict(BASE[s], gender="male")), ("fails-both", dict(BASE[s], gender="male", location="Chiang Mai"))):
        trap_attrs = dict(BASE[OTHER[s]])
        cat = [animal(1, "TRAP-other-species", trap_attrs, PERFECT), animal(2, "Same-species", same_species_attrs, POOR),
               animal(3, "Other-species-2", dict(trap_attrs, size="large"), PERFECT)]
        scenarios.append(dict(id=f"F-{s}-{variant}", family="F", species=s, violated="pet_type", prefs={"required": req, "preferred": SOFT}, animals=cat, trap_ids={1, 3}))
# Family N: requested species absent from catalogue
for s in ("dog", "cat"):
    cat = [animal(i, f"Other-{i}", dict(BASE[OTHER[s]]), PERFECT) for i in (1, 2, 3)]
    scenarios.append(dict(id=f"N-{s}", family="N", species=s, violated="pet_type", prefs={"required": {"pet_type": s}, "preferred": SOFT}, animals=cat, trap_ids={1, 2, 3}))
# Family O: fallback ordering - fewer failed relaxable constraints vs perfect soft score
for s in ("dog", "cat"):
    req = {"pet_type": s, "gender": "female", "location": "Bangkok"}
    cat = [animal(1, "Fails-1-constraint(soft 0%)", dict(BASE[s], gender="male"), POOR),
           animal(2, "Fails-2-constraints(soft 100%)", dict(BASE[s], gender="male", location="Chiang Mai"), PERFECT)]
    scenarios.append(dict(id=f"O-{s}", family="O", species=s, violated="relaxable", prefs={"required": req, "preferred": SOFT}, animals=cat, trap_ids={2}))

rows = []
for sc in scenarios:
    req = sc["prefs"]["required"]
    if sc["trap_ids"] is None:
        sc["trap_ids"] = {a["id"] for a in sc["animals"] if violates(a, req)}
    assert sc["trap_ids"] and all(violates(a, req) for a in sc["animals"] if a["id"] in sc["trap_ids"]) or sc["family"] == "O", sc["id"]
    res = rank_animals(copy.deepcopy(sc["animals"]), copy.deepcopy(sc["prefs"]), K)
    recs = res["recommendations"]; ids = [r["id"] for r in recs]
    base = aggregate_baseline(copy.deepcopy(sc["animals"]), sc["prefs"]); bids = [a["id"] for a in base]
    row = dict(id=sc["id"], family=sc["family"], mode=res["mode"], pawconnect_top=ids, baseline_top=bids)
    row["pc_species_violations"] = sum(not species_ok(r, req) for r in recs)
    row["bl_species_violations"] = sum(not species_ok(a, req) for a in base)
    row["pc_trap_rank1"] = bool(ids) and ids[0] in sc["trap_ids"]
    row["bl_trap_rank1"] = bool(bids) and bids[0] in sc["trap_ids"]
    row["pc_trap_in_topk"] = any(i in sc["trap_ids"] for i in ids)
    row["bl_trap_in_topk"] = any(i in sc["trap_ids"] for i in bids)
    row["pc_hard_violations_topk"] = sum(violates(r, req) for r in recs)
    row["bl_hard_violations_topk"] = sum(violates(a, req) for a in base)
    # disclosure: every returned item that fails a required constraint must list it
    row["undisclosed_violations"] = sum(1 for r in recs if violates(r, req) and not set(evaluate_required_constraints(r, req)["failed_constraints"]) <= set(r.get("failed_required_constraints", [])))
    if sc["family"] == "E":
        row["pass"] = res["mode"] == "exact" and not row["pc_trap_in_topk"] and row["pc_hard_violations_topk"] == 0
    elif sc["family"] == "F":
        row["pass"] = res["mode"] == "alternative" and row["pc_species_violations"] == 0 and row["undisclosed_violations"] == 0 and len(recs) > 0
    elif sc["family"] == "N":
        row["pass"] = len(recs) == 0
    else:  # O: strict expectation = fewer failed relaxable constraints ranks first
        row["pass"] = ids[:1] == [1]
        row["scores"] = {r["id"]: r["compatibility_score"] for r in recs}
    # metamorphic relations
    sig0 = sig(res)
    mr_det = all(sig(rank_animals(copy.deepcopy(sc["animals"]), copy.deepcopy(sc["prefs"]), K)) == sig0 for _ in range(100))
    rng = random.Random(hash(sc["id"]) & 0xffff)
    mr_shuffle = True
    for _ in range(20):
        a2 = copy.deepcopy(sc["animals"]); rng.shuffle(a2)
        mr_shuffle &= sig(rank_animals(a2, copy.deepcopy(sc["prefs"]), K)) == sig0
    row["MR_determinism_100runs"] = mr_det; row["MR_order_invariance_20shuffles"] = mr_shuffle
    if sc["family"] == "E":
        no_trap = [a for a in sc["animals"] if a["id"] not in sc["trap_ids"]]
        r2 = rank_animals(copy.deepcopy(no_trap), copy.deepcopy(sc["prefs"]), K)
        row["MR_trap_removal_invariance"] = [r["id"] for r in r2["recommendations"]] == ids
        # amplification: make compliant animals' competitor trap even stronger -> no change (already perfect); instead degrade compliant soft further
        worse = [dict(a, **POOR) if a["id"] not in sc["trap_ids"] else a for a in sc["animals"]]
        r3 = rank_animals(copy.deepcopy(worse), copy.deepcopy(sc["prefs"]), K)
        row["MR_trap_still_excluded_when_compliant_worsen"] = not any(r["id"] in sc["trap_ids"] for r in r3["recommendations"])
    rows.append(row)

def summ(fam):
    R = [r for r in rows if r["family"] in fam]
    return dict(n=len(R), pawconnect_pass=sum(r["pass"] for r in R),
                pc_trap_rank1=sum(r["pc_trap_rank1"] for r in R), bl_trap_rank1=sum(r["bl_trap_rank1"] for r in R),
                pc_trap_in_topk=sum(r["pc_trap_in_topk"] for r in R), bl_trap_in_topk=sum(r["bl_trap_in_topk"] for r in R),
                pc_species_viol_items=sum(r["pc_species_violations"] for r in R), bl_species_viol_items=sum(r["bl_species_violations"] for r in R),
                pc_hard_viol_items=sum(r["pc_hard_violations_topk"] for r in R), bl_hard_viol_items=sum(r["bl_hard_violations_topk"] for r in R),
                undisclosed=sum(r["undisclosed_violations"] for r in R),
                MR_det=sum(r["MR_determinism_100runs"] for r in R), MR_shuffle=sum(r["MR_order_invariance_20shuffles"] for r in R))
summary = {"E_exact_traps": summ("E"), "F_fallback_species_traps": summ("F"), "N_species_absent": summ("N"), "O_fallback_ordering": summ("O"),
           "E_MR_trap_removal": sum(r.get("MR_trap_removal_invariance", False) for r in rows if r["family"] == "E"),
           "E_MR_compliant_worsen": sum(r.get("MR_trap_still_excluded_when_compliant_worsen", False) for r in rows if r["family"] == "E")}
json.dump({"summary": summary, "rows": rows}, open("" + str(Path(__file__).resolve().parent / "results" / "adversarial_results.json") + "", "w"), indent=1, default=list)
print(json.dumps(summary, indent=1))
for r in rows:
    if not r["pass"] or r["family"] == "O": print("NOTE", r["id"], r["mode"], r["pawconnect_top"], r.get("scores"))
