"""Teacher item 1: re-run latency with per-run records, several independent rounds, and full environment details.

For each round: gc.collect(), warm-up runs (excluded), then every one of the 60 benchmark requests is timed
REPEATS times per system. System order alternates between rounds so slow drift cannot favour one system.

Outputs (results/latency/):
  latency_runs.csv          one row per timed run: round, system, case_id, repeat, latency_ms
  latency_summary.csv       per system: mean, SD, median, P95, min, max over all runs; mean of round means +/- SD across rounds
  latency_rounds.csv        per system and round: mean, SD, median
  latency_environment.json  machine, OS, CPU, RAM, power source, Python/packages, timer, warm-up/repeat settings, Llama/API settings

Run from ai/ (plug the laptop into AC power and close other apps first):
  python evaluation/benchmark_latency_rounds.py                      # ML-only + Hybrid, 5 rounds x 10 repeats x 60 cases
  python evaluation/benchmark_latency_rounds.py --live-llm           # also re-measure Llama 3.3 70B via Groq (needs GROQ_API_KEY)
  python evaluation/benchmark_latency_rounds.py --live-llm --llm-repeats 1   # fits the Groq free tier (~63 calls, ~60k tokens, ~7 min)
Without --live-llm the Llama rows come from the saved single-call-per-case run (llm_results_llama.json) and are labelled as such.
"""
import argparse, csv, gc, json, os, random, statistics, subprocess, sys, time
from pathlib import Path
EV = Path(__file__).resolve().parent; AI = EV.parent; sys.path[:0] = [str(AI), str(EV)]
import benchmark_inference_time as bit
ap0 = argparse.ArgumentParser(add_help=False); ap0.add_argument("--out", default=str(EV / "results" / "latency")); OUT = Path(ap0.parse_known_args()[0].out); OUT.mkdir(parents=True, exist_ok=True)

def power_source():
    try:
        import psutil; b = psutil.sensors_battery()
        if b is not None: return {"on_ac_power": bool(b.power_plugged), "battery_percent": b.percent}
    except Exception: pass
    if sys.platform == "win32":
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery).BatteryStatus"], capture_output=True, text=True, timeout=15).stdout.strip()
            return {"win32_battery_status": out, "note": "2 = on AC power, 1 = discharging (on battery)"}
        except Exception as e: return {"unknown": str(e)}
    return {"unknown": "no battery information (desktop/server/container)"}

def pct(v, q):
    s = sorted(v); k = (len(s) - 1) * q; f = int(k); c = min(f + 1, len(s) - 1); return s[f] + (s[c] - s[f]) * (k - f)
def stats(v): return {"n": len(v), "mean_ms": statistics.mean(v), "sd_ms": statistics.stdev(v) if len(v) > 1 else 0.0, "median_ms": statistics.median(v),
                      "p95_ms": pct(v, .95), "min_ms": min(v), "max_ms": max(v)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--rounds", type=int, default=5); ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--warmup", type=int, default=10); ap.add_argument("--live-llm", action="store_true")
    ap.add_argument("--llm-repeats", type=int, default=3); ap.add_argument("--llm-rounds", type=int, default=1); ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--llm-warmup", type=int, default=3, help="Llama warm-up calls excluded from timing")
    ap.add_argument("--llm-pause", type=float, default=6.0, help="seconds to wait between Llama calls (outside the timer) to stay under API rate limits")
    a = ap.parse_args()
    cases = bit.load_challenge_set(EV / "natural_language_challenge_60.jsonl")
    systems = {"ML-only": bit.run_ml_only_pipeline, "Hybrid": bit.run_hybrid_pipeline}
    runs = []
    for rnd in range(1, a.rounds + 1):
        order = list(systems) if rnd % 2 else list(reversed(systems))
        for name in order:
            fn = systems[name]; gc.collect()
            for _ in range(a.warmup): fn(cases[0]["text"])
            for rep in range(1, a.repeats + 1):
                for c in cases:
                    t0 = time.perf_counter(); fn(c["text"]); dt = (time.perf_counter() - t0) * 1000
                    runs.append({"round": rnd, "system": name, "case_id": c["id"], "repeat": rep, "latency_ms": round(dt, 6), "source": "measured"})
        print(f"round {rnd} done")
    llm_cfg = {"provider": "Groq Cloud API (groq Python SDK)", "model": "llama-3.3-70b-versatile", "temperature": 0, "response_format": "json_object",
               "measurement": "end-to-end client-side latency per request (includes network transfer and API queueing)"}
    if a.live_llm:
        if not os.environ.get("GROQ_API_KEY"): sys.exit("GROQ_API_KEY is not set; run without --live-llm or set the key first.")
        import llm_engine
        # Disable the SDK's automatic retries so a rate-limited (HTTP 429) call is logged as an error
        # instead of silently adding back-off time to the measured latency.
        llm_engine.client = llm_engine.client.with_options(max_retries=0)
        for rnd in range(1, a.llm_rounds + 1):
            for _ in range(a.llm_warmup):
                try: bit.run_llm_pipeline(cases[0]["text"])
                except Exception as e: print("warm-up call failed:", type(e).__name__)
                time.sleep(a.llm_pause)
            for rep in range(1, a.llm_repeats + 1):
                for i, c in enumerate(cases, 1):
                    t0 = time.perf_counter()
                    try: bit.run_llm_pipeline(c["text"]); ok = "measured"
                    except Exception as e: ok = f"error: {type(e).__name__}: {str(e)[:120]}"
                    runs.append({"round": rnd, "system": "Llama 3.3 70B", "case_id": c["id"], "repeat": rep, "latency_ms": round((time.perf_counter() - t0) * 1000, 3), "source": ok})
                    if i % 10 == 0: print(f"Llama round {rnd} repeat {rep}: {i}/{len(cases)} calls")
                    time.sleep(a.llm_pause)
        llm_cfg.update({"warmup_calls_excluded": a.llm_warmup, "repeats_per_case": a.llm_repeats, "rounds": a.llm_rounds,
                        "pause_between_calls_s": a.llm_pause, "sdk_automatic_retries": 0,
                        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": "live re-measurement"})
        n_err = sum(1 for r in runs if r["system"] == "Llama 3.3 70B" and r["source"].startswith("error"))
        print(f"Llama timed calls: {a.llm_rounds * a.llm_repeats * len(cases)}, with errors: {n_err}" + ("  <-- check GROQ_API_KEY / rate limits" if n_err else ""))
    else:
        for r in json.load(open(EV / "results" / "llm_results_llama.json")):
            runs.append({"round": 0, "system": "Llama 3.3 70B", "case_id": r["case_id"], "repeat": 1, "latency_ms": round(r["latency_seconds"] * 1000, 3),
                         "source": "saved original run (1 call per case, no warm-up)"})
        llm_cfg.update({"warmup_calls_excluded": 0, "repeats_per_case": 1, "source": "saved original evaluation run (llm_results_llama.json)"})
    with open(OUT / "latency_runs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(runs[0])); w.writeheader(); w.writerows(runs)
    summary, per_round = [], []
    for name in ["ML-only", "Hybrid", "Llama 3.3 70B"]:
        v = [r["latency_ms"] for r in runs if r["system"] == name and r["source"] != "" and not r["source"].startswith("error")]
        if not v: continue
        rounds = sorted({r["round"] for r in runs if r["system"] == name})
        rmeans = []
        for rd in rounds:
            rv = [r["latency_ms"] for r in runs if r["system"] == name and r["round"] == rd and not r["source"].startswith("error")]
            s = stats(rv); rmeans.append(s["mean_ms"]); per_round.append({"system": name, "round": rd, **{k: round(x, 4) if isinstance(x, float) else x for k, x in s.items()}})
        s = stats(v)
        summary.append({"system": name, "rounds": len(rounds), "timed_runs": len(v), **{k: round(x, 4) for k, x in s.items() if k != "n"},
                        "mean_of_round_means_ms": round(statistics.mean(rmeans), 4), "sd_across_rounds_ms": round(statistics.stdev(rmeans), 4) if len(rmeans) > 1 else "",
                        "errors": sum(1 for r in runs if r["system"] == name and r["source"].startswith("error")),
                        "source": next(r["source"] for r in runs if r["system"] == name)})
    for fn, rows in (("latency_summary.csv", summary), ("latency_rounds.csv", per_round)):
        with open(OUT / fn, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    env = bit.collect_environment(); env.update({"power": power_source(), "benchmark": {"cases": len(cases), "rounds": a.rounds, "warmup_runs_excluded_per_system_per_round": a.warmup,
               "repeats_per_case": a.repeats, "timed_runs_per_local_system": a.rounds * a.repeats * len(cases), "system_order": "alternates each round",
               "scope": "preference understanding only (text -> structured preferences); ranking excluded"}, "llama": llm_cfg})
    json.dump(env, open(OUT / "latency_environment.json", "w"), indent=1)
    for s in summary: print(s)

if __name__ == "__main__": main()
