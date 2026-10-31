# -*- coding: utf-8 -*-
"""Threshold sweep on the labelled validation set (needs val_labeled.csv from the earlier step).

Run from level1/:
    python sweep_threshold.py
    python sweep_threshold.py --thresholds 0.6,0.7,0.8,0.9

For each threshold it shows how many queries get answered, how accurate those answers are, and how many
wrong answers slip through. Writes sweep.csv.
"""
import argparse
import time

import pandas as pd

import agents_l2 as L2
from predict_eval import find, INTENT_KEYS, CATEGORY_KEYS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labeled", default="val_labeled.csv")
    ap.add_argument("--thresholds", default="0.5,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95")
    args = ap.parse_args()

    v = pd.read_csv(args.labeled)
    T = L2.load_trace_module()
    train, _val = T.load_data()
    system = T.build_system(train)

    out = []
    for th in [float(x) for x in args.thresholds.split(",")]:
        t0 = time.time()
        pi, pc, dec = [], [], []
        for text in v["instruction"]:
            r = L2.run_level2(system, str(text), T=T, threshold=th)
            pi.append(find(r, INTENT_KEYS)); pc.append(find(r, CATEGORY_KEYS)); dec.append(r.get("decision"))
        p = pd.DataFrame({"i": pi, "c": pc, "d": dec})
        ans, ok = p.d == "ANSWER", v["intent"] == p["i"]
        out.append({"threshold": th,
                    "answer_%": round(100 * ans.mean(), 1),
                    "clarify_%": round(100 * (p.d == "CLARIFY").mean(), 1),
                    "escalate_%": round(100 * (p.d == "ESCALATE").mean(), 1),
                    "intent_acc_all_%": round(100 * ok.mean(), 2),
                    "category_acc_all_%": round(100 * (v["category"] == p["c"]).mean(), 2),
                    "intent_acc_answered_%": round(100 * ok[ans].mean(), 2) if ans.any() else None,
                    "wrong_answers": int((ans & ~ok).sum()),
                    "correct_answers_%_of_all": round(100 * (ans & ok).mean(), 1)})
        print(f"  threshold {th} done ({time.time() - t0:.0f}s)", flush=True)

    res = pd.DataFrame(out)
    res.to_csv("sweep.csv", index=False)
    print("\n" + res.to_string(index=False))


if __name__ == "__main__":
    main()
