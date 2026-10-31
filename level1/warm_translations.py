# -*- coding: utf-8 -*-
"""Fill translations_cache.json so the multilingual demo also works with a weak or missing internet connection.

Run once, with internet, from the level1 folder (after make_store_data.py):
    pip install deep-translator
    python warm_translations.py                  # all five Indian languages
    python warm_translations.py --langs hi,mr    # only some
    python warm_translations.py --delay 1.5      # slower = safer against Google's rate limit

It translates everything the UI cannot take from the hand-written tables in lang.py:
  - each store's tagline and "in the app" route, the sample-question chips, top intents, recent queries
  - the 27 intent names (used in "Is this about X or Y?" follow-ups)
  - the English answer the agents give to each store's sample questions, so those answers show in Hindi etc.
Re-running is cheap: anything already in the cache is skipped, and every new translation is saved straight away,
so you can stop (Ctrl+C) or get blocked and simply run it again later.
Google's free endpoint blocks bursts of requests: the script paces itself, retries with backoff, and stops
cleanly after repeated blocks instead of hammering the server.
"""
import argparse
import json
import random
import time
from pathlib import Path

import lang as LG
import stores as S

HERE = Path(__file__).resolve().parent


def translate_one(t, lg, is_answer, backoff, retries):
    """One string -> (how, waited). Retries only when Google is rate-limiting us."""
    for attempt in range(retries + 1):
        _out, how = LG.mt(t, lg) if is_answer else LG._translate(t, "en", lg)
        if how != "unavailable":
            return how
        if attempt == retries or not LG.is_rate_limited():
            return how                               # not a rate limit (offline / library missing): retrying will not help
        wait = backoff * (2 ** attempt) + random.random()
        print(f"    rate-limited, waiting {wait:.0f}s (retry {attempt + 1}/{retries})...", flush=True)
        time.sleep(wait)
        LG.reset_backoff()                           # lang.py skips the network for 60s after a failure; undo that
    return "unavailable"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default=",".join(c for c in LG.ORDER if c != "en"))
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--delay", type=float, default=0.8, help="seconds to pause after each live translation")
    ap.add_argument("--backoff", type=float, default=8.0, help="first wait (s) after a rate-limit; doubles each retry")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--max-fail", type=int, default=2, help="stop after this many strings in a row fail")
    args = ap.parse_args(argv)
    langs = [c for c in args.langs.split(",") if c in LG.LANGS and c != "en"]

    data = json.loads((HERE / "stores.json").read_text(encoding="utf-8"))["stores"] if (HERE / "stores.json").exists() else {}
    texts = set()                                   # plain UI-style strings
    for st in S.STORES:
        texts.update([st["tagline"], st["in_app"]])
        d = data.get(st["id"], {})
        texts.update(e["text"] for e in d.get("examples", []))
        texts.update(n for n, _ in d.get("top_intents", []))
        texts.update(r[0] for r in d.get("recent", []))

    # intent names + the answers the agents give to each store's sample questions (needs the trained agents)
    answers = set()
    try:
        import agents_l2 as L2
        T = L2.load_trace_module()
        train, _val = T.load_data()
        system = T.build_system(train)
        texts.update(i.replace("_", " ") for i in system.agent_specs)
        for d in data.values():
            for e in d.get("examples", []):
                r = L2.run_level2(system, e["text"], T=T, threshold=args.threshold)
                if r["decision"] == L2.ANSWER:
                    answers.add(r["final_response"])
    except Exception as ex:                          # agents not available: still warm the plain strings
        print(f"(skipping agent answers: {type(ex).__name__}: {ex})")

    todo = sorted(texts) + sorted(answers)
    print(f"{len(texts)} UI strings + {len(answers)} agent answers x {len(langs)} languages", flush=True)
    tally = {"cache": 0, "live": 0, "unavailable": 0, "same": 0}
    fails_in_row, stopped = 0, False
    try:
        for lg in langs:
            for i, t in enumerate(todo, 1):
                how = translate_one(t, lg, t in answers, args.backoff, args.retries)
                tally[how] = tally.get(how, 0) + 1
                if how == "unavailable":
                    fails_in_row += 1
                    if fails_in_row >= args.max_fail:
                        stopped = True
                        break
                else:
                    fails_in_row = 0
                if how == "live" and LG.status().get("backend") != "nllb":   # the offline model has no rate limit
                    time.sleep(args.delay + 0.4 * random.random())
                    if tally["live"] % 25 == 0:
                        print(f"    {LG.LANGS[lg][1]}: {i}/{len(todo)} ({tally['live']} new so far)", flush=True)
            if stopped:
                break
            print(f"  {LG.LANGS[lg][1]:8} done", flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted. Everything translated so far is saved; run again to continue.")

    print("\nnew translations:", tally.get("live", 0), "| already cached:", tally.get("cache", 0),
          "| failed:", tally.get("unavailable", 0))
    if stopped:
        print("Stopped early:", LG.status().get("last_error") or "translator unavailable",
              "\n-> Progress is saved. Wait 20-30 minutes or switch to a phone hotspot, then run the same command again.")
    elif tally.get("unavailable"):
        print("Some translations failed:", LG.status().get("last_error") or "translator unavailable",
              "\n-> check your internet connection and `pip install deep-translator`, then run this again.")
    else:
        print("Cache saved to translations_cache.json")


if __name__ == "__main__":
    main()
