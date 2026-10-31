"""A1 -> A2 pipeline with a full, inspectable trace.

Wraps support_agents.MultiAgentSystem without changing it. Used by ui.py, and
handy on its own for the README / submission traces:

    python3 level1/trace.py "How can I request a refund for my purchase?"
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.metrics.pairwise import cosine_similarity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from support_agents.multi_agent_system import MultiAgentSystem  # noqa: E402


def find_csv(*names):
    for name in names:
        for p in (ROOT / "data" / name, ROOT / name, HERE / name):
            if p.exists():
                return p
    raise FileNotFoundError(f"None of {names} found in {ROOT / 'data'} or {ROOT}")


def load_data():
    """Return (train_df, validation_df). Validation is None if the file is missing."""
    train = pd.read_csv(find_csv("training.csv", "train.csv"))
    try:
        val = pd.read_csv(find_csv("validation.csv", "val.csv"))
    except FileNotFoundError:
        val = None
    return train, val


def build_system(train_df):
    """Fit A1 + A2 on the TRAIN split only."""
    return MultiAgentSystem().fit(train_df)


def run_trace(system, query, threshold=0.3, top_k=3):
    """Run one query through A1 -> A2 and return every intermediate output."""
    t0 = time.perf_counter()
    clf, gen = system.intent_classifier, system.response_generator

    # Official pipeline result (A1 classify -> A2 retrieve)
    out = system.process_query(query, confidence_threshold=threshold)
    intent = str(out["predicted_intent"])

    # A1 detail: top candidate intents
    probs = clf.predict_proba([query])[0]
    order = np.argsort(probs)[::-1][:3]
    category_of = lambda name: str(system.agent_specs.get(name, {}).get("category", "unknown"))
    candidates = [
        {"intent": str(clf.intent_names[i]),
         "category": category_of(str(clf.intent_names[i])),
         "prob": float(probs[i])}
        for i in order
    ]

    # A2 detail: closest training examples among those A1 labelled with the same intent
    raw_sims = cosine_similarity(gen.instruction_vectorizer.transform([query]),
                                 gen.instruction_vectors)[0]
    sims = raw_sims * (gen.intents == intent)
    evidence = [
        {"instruction": str(gen.instructions.iloc[i]),
         "response": str(gen.responses.iloc[i]),
         "similarity": float(sims[i]),
         "intent": str(gen.intents[i])}
        for i in np.argsort(sims)[::-1][:top_k]
    ]
    # Level 2: nearest examples over ALL intents (A3 uses them to spot contradictory evidence)
    neighbors = [
        {"instruction": str(gen.instructions.iloc[i]),
         "similarity": float(raw_sims[i]),
         "intent": str(gen.intents[i])}
        for i in np.argsort(raw_sims)[::-1][:5]
    ]

    return {
        "query": query,
        "a1": {
            "intent": intent,
            "category": category_of(intent),
            "confidence": float(out["intent_confidence"]),
            "candidates": candidates,
        },
        "handoff": {  # exactly what A1 passes to A2
            "query": query,
            "intent": intent,
            "category": category_of(intent),
            "confidence": round(float(out["intent_confidence"]), 4),
        },
        "a2": {
            "response": str(out["response"]),
            "similarity": float(out["response_confidence"]),
            "matched_instruction": str(out["matched_instruction"]),
            "evidence": evidence,
            "neighbors": neighbors,
        },
        "threshold": threshold,
        "decision": "auto_resolved" if out["above_threshold"] else "escalate",
        "latency_ms": (time.perf_counter() - t0) * 1000,
    }


def evaluate_a1(system, val_df):
    """Held-out A1 metrics (vectorised, runs in about a second)."""
    clf = system.intent_classifier
    texts = val_df["instruction"].values
    true = val_df["intent"].values
    pred = clf.predict(texts)
    conf = clf.get_confidence_scores(texts)

    cat_of = {k: v["category"] for k, v in system.agent_specs.items()}
    cat_acc = None
    if "category" in val_df.columns:
        pred_cat = np.array([cat_of.get(p, "unknown") for p in pred])
        cat_acc = float(accuracy_score(val_df["category"].values, pred_cat))

    labels = sorted(set(true))
    per_intent = sorted(
        zip(labels, f1_score(true, pred, labels=labels, average=None, zero_division=0)),
        key=lambda kv: kv[1])
    return {
        "n": int(len(val_df)),
        "macro_f1": float(f1_score(true, pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(true, pred, average="weighted", zero_division=0)),
        "intent_accuracy": float(accuracy_score(true, pred)),
        "category_accuracy": cat_acc,
        "per_intent": [(str(k), float(v)) for k, v in per_intent],
        "conf": conf,
        "correct": pred == true,
    }


def threshold_table(ev, thresholds=(0.3, 0.5, 0.6, 0.7, 0.8, 0.9)):
    """For each escalation threshold: share auto-resolved and accuracy on those."""
    rows = []
    for t in thresholds:
        keep = ev["conf"] >= t
        rows.append({
            "threshold": t,
            "auto_resolved": float(keep.mean()),
            "accuracy_on_auto": float(ev["correct"][keep].mean()) if keep.any() else None,
        })
    return rows


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How can I request a refund for my purchase?"
    train_df, _ = load_data()
    print(json.dumps(run_trace(build_system(train_df), q), indent=2, ensure_ascii=False))
