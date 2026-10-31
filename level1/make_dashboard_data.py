"""Grahak Seva - build the JSON files the UI reads, from the trained agents.

Run from the project root (same place you run streamlit from):
    python level1/make_dashboard_data.py              # replay 400 validation queries
    python level1/make_dashboard_data.py --n 1000     # bigger replay, slower, smoother charts

Writes next to this file:
    dashboard.json   KPIs, top intents, recent queries and the replay series for the dashboard (home.html)
    examples.json    sample questions for the chat chips (picked from validation.csv, checked against the agents)

It uses the same level1/trace.py functions as ui.py:
    T.load_data() -> (train, val)      T.build_system(train)      T.evaluate_a1(system, val)
    T.run_trace(system, text, threshold=...)
The agents are trained on train.csv only. Everything replayed or suggested comes from validation.csv,
so the agents have never seen those questions.
"""
import argparse
import importlib.util
import json
import random
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=400, help="validation queries to replay through A1 -> A2")
ap.add_argument("--threshold", type=float, default=0.8, help="confidence below this is escalated")
ap.add_argument("--examples", type=int, default=8, help="sample questions to keep (the UI shows 4)")
ap.add_argument("--seed", type=int, default=7)
args = ap.parse_args()

# trace.py is loaded by path because "trace" is also a Python standard-library module name
spec = importlib.util.spec_from_file_location("grahak_trace", HERE / "trace.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

t0 = time.time()
train, val = T.load_data()
if val is None:
    raise SystemExit("validation.csv not found - nothing to replay.")
print(f"Training A1 and A2 on {len(train):,} rows (train.csv)...")
system = T.build_system(train)
ev = T.evaluate_a1(system, val)
print(f"  done in {time.time() - t0:.1f}s | held-out Macro-F1 {ev['macro_f1']:.3f} on {ev['n']:,} validation rows")

rng = random.Random(args.seed)


def nice(intent):
    return str(intent).replace("_", " ")


def clean(text):
    """The Bitext questions contain {{Order Number}}-style slots; fill them so they read like real messages."""
    return re.sub(r"\{\{(.*?)\}\}",
                  lambda m: "#85632" if "number" in m.group(1).lower() else m.group(1).lower(), text)


# NOTE: use val["flags"], not val.flags (DataFrame.flags is a pandas attribute, not your column)
# ---------- 1) replay validation queries through the real pipeline ----------
idx = list(range(len(val)))
rng.shuffle(idx)
idx = idx[:min(args.n, len(val))]
print(f"Replaying {len(idx)} validation queries through A1 -> A2...")
replay, rows, lat = [], [], []
for k, i in enumerate(idx, 1):
    row = val.iloc[i]
    res = T.run_trace(system, row["instruction"], threshold=args.threshold)
    ok = res["decision"] == "auto_resolved"
    replay.append(1 if ok else 0)
    lat.append(res["latency_ms"])
    # "tidy" = no {{slots}}, no swearing / typos / slang, so it looks fine in the Recent queries table
    tidy = "{{" not in row["instruction"] and not re.search(r"[WZKQE]", row["flags"])
    rows.append({"i": int(i), "query": clean(row["instruction"]), "true": row["intent"], "pred": res["a1"]["intent"],
                 "conf": float(res["a1"]["confidence"]), "ok": ok, "tidy": tidy})
    if k % 100 == 0:
        print(f"  {k}/{len(idx)}")

n = len(rows)
auto = sum(replay)
pred_counts = Counter(r["pred"] for r in rows).most_common(6)
answered = [r for r in rows if r["ok"] and r["tidy"]] or [r for r in rows if r["ok"]]
escalated = [r for r in rows if not r["ok"] and r["tidy"]] or [r for r in rows if not r["ok"]]
recent = answered[:5] + escalated[:2]
rng.shuffle(recent)

dashboard = {
    "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "subtitle": "How the two agents did on held-out validation questions they were never trained on.",
    "note": (f"Live results: trained on {len(train):,} rows from train.csv, replayed {n:,} questions from "
             f"validation.csv at a {args.threshold:.0%} escalation threshold."),
    "kpis": [
        {"label": "Questions replayed", "value": f"{n:,}", "chip": f"of {len(val):,} validation rows", "style": "b"},
        {"label": "Auto-resolved", "value": f"{auto / n:.0%}", "chip": f"{auto:,} of {n:,}", "style": "u"},
        {"label": "Escalated to humans", "value": f"{n - auto:,}", "chip": f"below {args.threshold:.0%} confidence", "style": ""},
        {"label": "Avg. response time", "value": f"{sum(lat) / n / 1000:.2f} s" if sum(lat) / n >= 1000
                                                    else f"{sum(lat) / n:.0f} ms",
         "chip": f"A1 Macro-F1 {ev['macro_f1']:.3f}", "style": ""},
    ],
    "top_intents": [[nice(k), v] for k, v in pred_counts],
    "recent": [[r["query"], r["pred"], round(r["conf"], 2), "answered" if r["ok"] else "escalated",
                f"validation row {r['i']}"] for r in recent],
    "replay": replay,            # 1 = auto-resolved, 0 = escalated, in replay order (the chart buckets this)
    "metrics": {"macro_f1": ev["macro_f1"], "intent_accuracy": ev["intent_accuracy"],
                "category_accuracy": ev.get("category_accuracy"), "train_rows": len(train), "val_rows": len(val)},
}
(HERE / "dashboard.json").write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")
print("Wrote dashboard.json")

# ---------- 2) sample questions for the chat chips ----------
# Preferred intents first (the everyday shop questions), then any others.
PREFERRED = ["get_refund", "track_order", "cancel_order", "recover_password", "get_invoice",
             "change_shipping_address", "delivery_period", "payment_issue", "check_refund_policy",
             "contact_human_agent"]
ordered = PREFERRED + [i for i in sorted(val["intent"].unique()) if i not in PREFERRED]
no_slot = ~val["instruction"].str.contains(r"\{\{", regex=True)
plain = ~val["flags"].str.contains(r"[WZKQE]", regex=True)   # drop swearing, typos, keyword-only, slang, abbreviations
TIERS = [(15, 45), (15, 60), (15, 80)]                       # short enough to fit a chip; relax if an intent has none

examples = []
for intent in ordered:
    if len(examples) >= args.examples:
        break
    found = None
    for lo, hi in TIERS:
        pool = val[(val["intent"] == intent) & no_slot & plain & val["instruction"].str.len().between(lo, hi)]
        texts = list(pool["instruction"])
        rng.shuffle(texts)
        texts.sort(key=lambda s: not s.strip().endswith("?"))   # real questions first
        for text in texts[:15]:
            res = T.run_trace(system, text, threshold=args.threshold)
            # keep it only if the agents get it right, so the demo chips always work
            if res["a1"]["intent"] == intent and res["decision"] == "auto_resolved":
                found = {"text": text.strip()[0].upper() + text.strip()[1:], "intent": intent,
                         "category": res["a1"]["category"], "confidence": round(float(res["a1"]["confidence"]), 2)}
                break
        if found:
            break
    if found:
        examples.append(found)

(HERE / "examples.json").write_text(json.dumps(examples, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote examples.json ({len(examples)} questions)")
for e in examples:
    print(f"  [{e['intent']}] {e['text']}")
print(f"All done in {time.time() - t0:.0f}s.")
