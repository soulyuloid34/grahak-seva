# -*- coding: utf-8 -*-
"""How well does the five-agent system cope with Hindi, Bengali, Tamil, Telugu and Marathi customers?

    python evaluate_multilingual.py                    # 300 held-out queries per language
    python evaluate_multilingual.py --n 500 --langs hi,ta

For every held-out English query we (1) translate it into the language (a stand-in for a customer typing
in that language), (2) run the real customer path: translate back to English, then agents A1-A5, and
(3) compare with the dataset's true intent / category. English is the baseline.

Honest caveat for the demo: the "customer" text is machine-translated from English, so this measures how the
system copes with translation noise, not how real native speakers write (they use slang, mixed English, Hinglish).

Needs internet + `pip install deep-translator` (first run); translations are cached in translations_cache.json.
Writes outputs/multilingual_results.csv (summary) and outputs/predictions_multilingual.csv (every query).
"""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

import agents_l2 as L2
import lang as LG

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--langs", default=",".join(c for c in LG.ORDER if c != "en"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)

    T = L2.load_trace_module()
    train, val = T.load_data()
    if val is None:
        raise SystemExit("validation.csv not found")
    val = val[val["flags"].astype(str).str.fullmatch(r"B[A-Z]*")] if "flags" in val else val   # clean phrasing only
    val = val.sample(min(args.n, len(val)), random_state=args.seed).reset_index(drop=True)
    print(f"Training agents; evaluating {len(val)} held-out queries x {args.langs} ...")
    system = T.build_system(train)

    rows, summary = [], []
    for code in ["en"] + [c for c in args.langs.split(",") if c in LG.LANGS and c != "en"]:
        recs, failed = [], 0
        for i, (q, intent, cat) in enumerate(zip(val["instruction"], val["intent"], val["category"])):
            if code == "en":
                local, en = q, q
            else:
                local, how = LG._translate(q, "en", code)          # the "customer" writes in this language
                if how == "unavailable":
                    failed += 1
                en, _info = LG.to_english(local, code)             # the real customer path starts here
            r = L2.run_level2(system, en, T=T, threshold=args.threshold)
            recs.append({"query_id": f"Q{i + 1:04d}", "language": code, "original": local, "english_for_agents": en,
                         "true_intent": intent, "true_category": cat, "predicted_intent": r["a1"]["intent"],
                         "predicted_category": r["a1"]["category"], "decision": r["decision"]})
        df = pd.DataFrame(recs)
        rows.append(df)
        ans = df[df["decision"] == L2.ANSWER]
        summary.append({
            "language": LG.LANGS[code][1], "n": len(df),
            "intent_macro_f1": round(float(f1_score(df.true_intent, df.predicted_intent, average="macro", zero_division=0)), 3),
            "intent_acc": round(float(accuracy_score(df.true_intent, df.predicted_intent)), 3),
            "category_acc": round(float(accuracy_score(df.true_category, df.predicted_category)), 3),
            "ANSWER_%": round(100 * (df.decision == L2.ANSWER).mean(), 1),
            "CLARIFY_%": round(100 * (df.decision == L2.CLARIFY).mean(), 1),
            "ESCALATE_%": round(100 * (df.decision == L2.ESCALATE).mean(), 1),
            "acc_when_ANSWER": round(float((ans.predicted_intent == ans.true_intent).mean()), 3) if len(ans) else None,
            "translation_failed": failed})
        print(f"  {LG.LANGS[code][1]:8} intent acc {summary[-1]['intent_acc']:.3f}  ESCALATE {summary[-1]['ESCALATE_%']}%"
              + (f"  ({failed} translations failed)" if failed else ""))

    pd.concat(rows).to_csv(OUT / "predictions_multilingual.csv", index=False)
    res = pd.DataFrame(summary)
    res.to_csv(OUT / "multilingual_results.csv", index=False)
    print("\n", res.to_string(index=False))
    if res["translation_failed"].sum():
        print("\nSome translations failed (offline / deep-translator missing): those rows were evaluated on the "
              "untranslated text and the numbers for that language are NOT meaningful. Fix the connection and re-run.")
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
