"""Build stores.json: one simulated dashboard + sample questions per store.

Run from the level1 folder after any change to the agents or to the thresholds:
    python make_store_data.py                  # uses the validation split, threshold 0.8
    python make_store_data.py --threshold 0.6

How the six stores are simulated (say this in the demo): every validation row is given to ONE store at random,
with each store favouring the categories listed in stores.py (e.g. Blinkit and Zepto get more DELIVERY/ORDER,
Amazon gets more SUBSCRIPTION/INVOICE).  Each store's slice is then run through the full A1-A5 pipeline, so the
numbers on its dashboard are real agent outputs on held-out data - just not real company data.
"""
import argparse
import json
import random
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

import agents_l2 as L2
import stores as S

HERE = Path(__file__).resolve().parent


def nice(x):
    return str(x).replace("_", " ").capitalize()


def showable(r):
    """Safe to show on a dashboard: not rude (flag W), no unfilled {{template}}, short enough."""
    return "W" not in r["flags"] and "{{" not in r["query"] and len(r["query"]) < 90


def pick_examples(rows, rng):
    """Up to 5 chips: 3 clear ANSWER questions (different intents), 1 CLARIFY, 1 ESCALATE (from this store's slice)."""
    out, seen = [], set()
    by = {d: [r for r in rows if r["decision"] == d] for d in L2.DECISIONS}
    for d in by:
        rng.shuffle(by[d])
    for r in by[L2.ANSWER]:
        if r["intent"] not in seen and showable(r):
            seen.add(r["intent"])
            out.append({"text": r["query"], "expected": L2.ANSWER})
        if len(out) == 3:
            break
    for d in (L2.CLARIFY, L2.ESCALATE):
        for r in by[d]:
            if showable(r):
                out.append({"text": r["query"], "expected": d})
                break
    # a slice may not contain a showable CLARIFY / ESCALATE row: fall back to a generic one
    have = {e["expected"] for e in out}
    if L2.CLARIFY not in have:
        out.append({"text": "I need a refund but cannot find my order number", "expected": L2.CLARIFY})
    if L2.ESCALATE not in have:
        out.append({"text": "What is the weather in Paris today?", "expected": L2.ESCALATE})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    T = L2.load_trace_module()
    train, val = T.load_data()
    if val is None:
        raise SystemExit("validation.csv not found")
    val = val.reset_index(drop=True)
    print(f"Training agents on {len(train):,} rows; splitting {len(val):,} held-out rows across {len(S.STORES)} stores ...")
    system = T.build_system(train)

    # ---- assign each held-out row to one store, favouring that store's categories
    assign = {s["id"]: [] for s in S.STORES}
    for i, cat in enumerate(val["category"]):
        w = [float(s["weights"].get(cat, 1.0)) for s in S.STORES]
        sid = rng.choices([s["id"] for s in S.STORES], weights=w)[0]
        assign[sid].append(i)

    out = {}
    for s in S.STORES:
        idx = assign[s["id"]]
        sub = val.iloc[idx].reset_index(drop=True)
        t0 = time.time()
        res = [L2.run_level2(system, q, T=T, threshold=args.threshold) for q in sub["instruction"]]
        rows = [{"flags": fl, "query": q, "intent": r["a1"]["intent"], "true_intent": ti, "category": r["a1"]["category"],
                 "true_category": tc, "conf": r["a1"]["confidence"], "decision": r["decision"],
                 "reason": r["a5"]["reason"], "ms": r["latency_ms"]}
                for fl, q, ti, tc, r in zip(sub["flags"].astype(str), sub["instruction"], sub["intent"], sub["category"], res)]
        n = len(rows)
        cnt = {d: sum(r["decision"] == d for r in rows) for d in L2.DECISIONS}
        pct = {d: (100 * cnt[d] / n if n else 0) for d in cnt}
        ans = [r for r in rows if r["decision"] == L2.ANSWER]
        acc_ans = sum(r["intent"] == r["true_intent"] for r in ans) / len(ans) if ans else None
        top = pd.Series([r["intent"] for r in rows]).value_counts().head(6)
        # recent table: mix of statuses, newest first
        status = {L2.ANSWER: "answered", L2.CLARIFY: "clarify", L2.ESCALATE: "escalated"}
        pool = [r for r in rows if showable(r)]
        rng.shuffle(pool)
        recent = [r for r in pool if r["decision"] != L2.ANSWER][:4] + [r for r in pool if r["decision"] == L2.ANSWER][:6]
        rng.shuffle(recent)
        order = recent[:9]
        replay = [1 if r["decision"] == L2.ANSWER else 0 for r in rows]
        rng.shuffle(replay)
        data = {
            "store": {"id": s["id"], "name": s["name"], "initials": s["initials"], "color": s["color"],
                      "tint": s["tint"], "tagline": s["tagline"]},
            "subtitle": f"{s['name']} support · {n:,} held-out customer queries handled by the five agents.",
            "kpis": [
                {"label": "Queries handled", "value": f"{n:,}", "chip": "held-out sample", "style": "b"},
                {"label": "Answered by agents", "value": f"{pct[L2.ANSWER]:.0f}%",
                 "chip": f"{pct[L2.CLARIFY]:.1f}% needed a follow-up", "style": "u"},
                {"label": "Escalated to humans", "value": f"{cnt[L2.ESCALATE]:,}", "chip": f"{pct[L2.ESCALATE]:.1f}% of queries"},
                {"label": "Avg. response time", "value": f"{(sum(r['ms'] for r in rows) / n if n else 0):.0f} ms",
                 "chip": "A1 to A5 end to end"},
            ],
            "note": f"Simulated {s['name']} slice of the Bitext validation split (threshold {args.threshold}). "
                    f"Not real {s['name']} data.",
            "replay": replay,
            "top_intents": [[nice(k), int(v)] for k, v in top.items()],
            "recent": [[r["query"], r["intent"], round(r["conf"], 2), status[r["decision"]], f"sample {i + 1}"]
                       for i, r in enumerate(order)],
            "examples": pick_examples(rows, rng),
            "metrics": {
                "n": n, "threshold": args.threshold,
                "macro_f1": round(float(f1_score([r["true_intent"] for r in rows], [r["intent"] for r in rows],
                                                 average="macro", zero_division=0)), 3) if n else None,
                "intent_acc": round(float(accuracy_score([r["true_intent"] for r in rows], [r["intent"] for r in rows])), 3) if n else None,
                "category_acc": round(float(accuracy_score([r["true_category"] for r in rows], [r["category"] for r in rows])), 3) if n else None,
                "acc_when_answered": None if acc_ans is None else round(acc_ans, 3),
                "answer_pct": round(pct[L2.ANSWER], 1), "clarify_pct": round(pct[L2.CLARIFY], 1),
                "escalate_pct": round(pct[L2.ESCALATE], 1),
                "category_mix": {k: int(v) for k, v in sub["category"].value_counts().items()},
            },
        }
        out[s["id"]] = data
        print(f"  {s['name']:9} {n:5} rows  ANSWER {pct[L2.ANSWER]:5.1f}%  CLARIFY {pct[L2.CLARIFY]:4.1f}%  "
              f"ESCALATE {pct[L2.ESCALATE]:4.1f}%   ({time.time() - t0:.0f}s)")

    (HERE / "stores.json").write_text(json.dumps({"threshold": args.threshold, "stores": out}, indent=1), encoding="utf-8")
    print("Wrote stores.json")


if __name__ == "__main__":
    main()
