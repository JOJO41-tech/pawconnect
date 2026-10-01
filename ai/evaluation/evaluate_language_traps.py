"""Stage-1 adversarial phrasings: does the parser extract the right HARD constraints when the text contains distractors?
(The Stage-2 filter enforces whatever is extracted, so a species extraction error becomes a faithfully enforced wrong constraint.)"""
import json, sys
from pathlib import Path
AI = Path(__file__).resolve().parents[1]; EV = AI / "evaluation"; sys.path[:0] = [str(AI), str(EV)]
import evaluate_ablation as ab

CASES = [
 # (id, category, text, gold hard constraints)
 ("A01", "other-pet mention", "I want a calm cat that gets along with my dog.", {"pet_type": "cat"}),
 ("A02", "other-pet mention", "Looking for a dog that is good with my two cats.", {"pet_type": "dog"}),
 ("A03", "other-pet mention", "We already have a cat at home, so we want a friendly dog that likes cats.", {"pet_type": "dog"}),
 ("A04", "other-pet mention", "My dog needs a companion, and a relaxed cat would be perfect.", {"pet_type": "cat"}),
 ("A05", "negation", "I want a cat, not a dog.", {"pet_type": "cat"}),
 ("A06", "negation", "No cats please, I would like a dog.", {"pet_type": "dog"}),
 ("A07", "negation", "I don't want a dog. I want a cat.", {"pet_type": "cat"}),
 ("A08", "negation", "Please do not recommend any cats; I am only interested in dogs.", {"pet_type": "dog"}),
 ("A09", "past pet / contrast", "I grew up with dogs but now I want to adopt a cat.", {"pet_type": "cat"}),
 ("A10", "past pet / contrast", "I had a cat before; this time I would like a dog.", {"pet_type": "dog"}),
 ("A11", "family preference", "My kids love cats, but we have decided to adopt a dog.", {"pet_type": "dog"}),
 ("A12", "gender distractor", "I want a female cat because our male cat needs a friend.", {"pet_type": "cat", "gender": "female"}),
 ("A13", "size distractor", "I live in a large house but I want a small dog.", {"pet_type": "dog", "size": "small"}),
 ("A14", "location distractor", "I am originally from Chiang Mai but now live in Bangkok and want a cat in Bangkok.", {"pet_type": "cat", "location": "Bangkok"}),
 ("A15", "soft-preference pressure", "It must be a cat, even if it is not calm or apartment friendly.", {"pet_type": "cat"}),
 ("A16", "soft-preference pressure", "Any dog is fine even if it is very energetic; I just do not want a cat.", {"pet_type": "dog"}),
]
HARD = ["pet_type", "gender", "size", "location", "breed", "age_years", "age_months"]
def norm(v): return v.strip().lower() if isinstance(v, str) else v

rows = []
for cid, cat, text, gold in CASES:
    out = {}
    for name, fn in (("ML-only", ab.ml_only), ("Hybrid", ab.full_hybrid)):
        pred = fn(text) or {}
        species_ok = norm(pred.get("pet_type")) == gold["pet_type"]
        hard_ok = all(norm(pred.get(k)) == norm(gold.get(k)) for k in HARD if k in gold) and \
                  all(pred.get(k) in (None, "") for k in HARD if k not in gold)
        out[name] = dict(pet_type=pred.get("pet_type"), species_ok=species_ok, all_hard_ok=hard_ok,
                         pred_hard={k: pred.get(k) for k in HARD if pred.get(k) not in (None, "")})
    rows.append(dict(id=cid, category=cat, text=text, gold=gold, **out))

summ = {}
for name in ("ML-only", "Hybrid"):
    summ[name] = dict(species_correct=sum(r[name]["species_ok"] for r in rows), all_hard_correct=sum(r[name]["all_hard_ok"] for r in rows), n=len(rows),
                      species_missing=sum(r[name]["pet_type"] in (None, "") for r in rows),
                      species_wrong=sum(r[name]["pet_type"] not in (None, "") and not r[name]["species_ok"] for r in rows))
json.dump({"summary": summ, "rows": rows}, open("" + str(Path(__file__).resolve().parent / "results" / "language_trap_results.json") + "", "w"), indent=1)
print(json.dumps(summ, indent=1))
for r in rows:
    print(f'{r["id"]} {r["category"]:<22} gold={r["gold"]}  Hybrid={r["Hybrid"]["pred_hard"]}  ML={r["ML-only"]["pred_hard"]}')
