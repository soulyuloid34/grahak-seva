# -*- coding: utf-8 -*-
"""Run the five agents on evaluation_queries.csv and write predictions.csv.

Run from the level1 folder:
    python predict_eval.py evaluation_queries.csv --threshold 0.8
    python predict_eval.py evaluation_queries.csv --limit 20      # quick test on the first 20 rows

Output (predictions.csv): query_id, predicted_intent, predicted_category, decision
The evaluation file has no labels, so there is no accuracy to compute from it: this file is what you submit.
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

import agents_l2 as L2

INTENT_KEYS = ("predicted_intent", "intent", "final_intent", "routed_intent", "a2_intent", "label")
CATEGORY_KEYS = ("predicted_category", "category", "final_category", "routed_category", "a1_category")


def find(r, names):
    for n in names:
        if n in r and r[n] is not None:
            return r[n]
    for v in r.values():                              # one level of nesting, e.g. r["router"]["intent"]
        if isinstance(v, dict):
            for n in names:
                if n in v and v[n] is not None:
                    return v[n]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default="evaluation_queries.csv")
    ap.add_argument("--out", default="predictions.csv")
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    if args.limit:
        df = df.head(args.limit)
    print(f"{len(df)} queries from {args.csv}", flush=True)

    T = L2.load_trace_module()
    train, _val = T.load_data()
    system = T.build_system(train)

    rows, t0 = [], time.time()
    for n, (qid, text) in enumerate(zip(df["query_id"], df["instruction"]), 1):
        r = L2.run_level2(system, str(text), T=T, threshold=args.threshold)
        if n == 1:
            print("result keys:", sorted(r.keys()), flush=True)
            if find(r, INTENT_KEYS) is None:
                sys.exit("Could not find the intent in the result (see keys above). "
                         "Tell me the key names and I will adjust INTENT_KEYS / CATEGORY_KEYS.")
        rows.append({"query_id": qid,
                     "predicted_intent": find(r, INTENT_KEYS),
                     "predicted_category": find(r, CATEGORY_KEYS),
                     "decision": r.get("decision")})
        if n % 250 == 0:
            print(f"  {n}/{len(df)}  ({time.time() - t0:.0f}s)", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False)
    print(f"\nWrote {args.out}: {len(out)} rows")
    print(out["decision"].value_counts(normalize=True).round(3).to_string())


if __name__ == "__main__":
    main()
