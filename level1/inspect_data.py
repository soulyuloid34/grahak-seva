#!/usr/bin/env python3
"""Day 1: inspect the Bitext data and document the split.

Run from the project root:  python3 level1/inspect_data.py
Writes results/data_report.md and prints the same report.
"""
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def find(name):
    for p in (ROOT / "data" / name, ROOT / name):
        if p.exists():
            return p
    sys.exit(f"Could not find {name} in {ROOT / 'data'} or {ROOT}")


def norm(s):
    return " ".join(str(s).lower().split())


def table(series, n=5):
    rows = ["| label | count | share |", "|---|---|---|"]
    total = series.sum()
    for label, c in series.head(n).items():
        rows.append(f"| {label} | {c} | {c / total:.1%} |")
    return "\n".join(rows)


def main():
    train = pd.read_csv(find("train.csv"))
    val = pd.read_csv(find("validation.csv"))
    out = []
    add = out.append

    add("# Data report\n")
    add("## Files\n")
    add(f"- train: {len(train)} rows | validation: {len(val)} rows")
    add(f"- columns (train): {list(train.columns)}")
    add(f"- columns (validation): {list(val.columns)}\n")

    add("## Missing values\n")
    add(f"- train: {train.isna().sum().to_dict()}")
    add(f"- validation: {val.isna().sum().to_dict()}\n")

    add("## Labels\n")
    for col in ("category", "intent"):
        add(f"- distinct {col} in train: {train[col].nunique()}, "
            f"in validation: {val[col].nunique()}")
    missing_i = sorted(set(val["intent"]) - set(train["intent"]))
    missing_c = sorted(set(val["category"]) - set(train["category"]))
    add(f"- intents in validation but not in train: {missing_i or 'none'}")
    add(f"- categories in validation but not in train: {missing_c or 'none'}")
    per_intent = train.groupby("intent")["category"].nunique()
    odd = per_intent[per_intent > 1]
    add(f"- intents mapped to more than one category: "
        f"{list(odd.index) if len(odd) else 'none (clean intent -> category map)'}\n")

    add("## Class balance\n")
    for col in ("intent", "category"):
        vc = train[col].value_counts()
        add(f"### {col} (train)\n")
        add(f"Largest class {vc.iloc[0]}, smallest {vc.iloc[-1]}, "
            f"imbalance ratio {vc.iloc[0] / vc.iloc[-1]:.2f}.\n")
        add("Top 5:\n")
        add(table(vc))
        add("\nBottom 5:\n")
        add(table(vc.sort_values().head(5)))
        add("")
    add("Validation intent counts (top 5):\n")
    add(table(val["intent"].value_counts()))
    add("")

    add("## Variation flags\n")
    add("Each flag letter marks a linguistic or style variation of the query "
        "(for example politeness, colloquial wording, noise or typos).\n")
    for name, df in (("train", train), ("validation", val)):
        counts = Counter(ch for f in df["flags"].dropna() for ch in str(f))
        add(f"- {name}: {dict(sorted(counts.items(), key=lambda kv: -kv[1]))}")
    add("")

    add("## Duplicates and leakage\n")
    tn = train["instruction"].map(norm)
    vn = val["instruction"].map(norm)
    add(f"- duplicate instructions inside train (normalised): "
        f"{int(tn.duplicated().sum())}")
    dup_labels = train.assign(n=tn).groupby("n")["intent"].nunique()
    add(f"- instructions with conflicting intent labels in train: "
        f"{int((dup_labels > 1).sum())}")
    exact = set(train["instruction"]) & set(val["instruction"])
    normed = set(tn) & set(vn)
    add(f"- exact instructions shared by train and validation: {len(exact)}")
    add(f"- shared after lowercasing/whitespace normalisation: {len(normed)}")
    add(f"- share of validation rows affected: "
        f"{vn.isin(set(tn)).mean():.2%}\n")

    ph = train["response"].astype(str).str.contains(r"\{\{", regex=True).mean()
    add("## Response notes\n")
    add(f"- share of train responses containing {{{{Placeholder}}}} tokens: {ph:.1%}")
    add(f"- mean response length (words): "
        f"{train['response'].astype(str).str.split().str.len().mean():.0f}\n")

    add("## Split used\n")
    add("The organizer-provided `train.csv` and `validation.csv` are used exactly "
        "as given; no rows are moved between them.\n")
    add("- **Train** is used to fit the intent model and as the retrieval pool "
        "for supporting examples.")
    add("- **Validation** is held out: it is never used for training, retrieval, "
        "threshold tuning or prompt examples. It is used only to report "
        "intent Macro-F1, category accuracy and sample outputs.")
    add("- The split is therefore reproducible by construction. Any sampling "
        "done later (for example 200 validation queries) uses a fixed random "
        "seed of 42.")
    if len(normed):
        add(f"- Caveat: {len(normed)} normalised instructions appear in both files, "
            "so scores may be slightly optimistic.")

    report = "\n".join(out)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "data_report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"\n[saved to {RESULTS / 'data_report.md'}]")


if __name__ == "__main__":
    main()
