"""Adapter between the Level 1 tooling and the existing support_agents code.

This is the ONLY file that needs to know how support_agents/multi_agent_system.py
is called. It tries common entry-point names and normalises whatever comes back
into one dict:

    intent, category, confidence, action, response, evidence, raw

Test the connection from the project root:
    python3 level1/adapter.py "How can I request a refund for my purchase?"

If auto-detection fails it lists the public names it found. Fix it by setting
ENTRY below, for example ENTRY = ("support_agents.multi_agent_system", "MultiAgentSystem", "process")
"""
import importlib
import inspect
import json
import sys
from collections import deque
from dataclasses import asdict, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Optional manual override: (module, class_or_None, method_or_function)
ENTRY = None

MODULE = "support_agents.multi_agent_system"
NAMES = ("resolve", "process_query", "run_pipeline", "handle_query",
         "process", "run", "answer", "respond", "predict", "__call__")

_fn = None


def _public(mod):
    return [n for n in dir(mod) if not n.startswith("_")]


def _find_csv(name):
    for p in (ROOT / "data" / name, ROOT / name):
        if p.exists():
            return p
    raise FileNotFoundError(f"{name} not found in {ROOT / 'data'} or {ROOT}")


def _build(mod):
    """Explicit wiring: MultiAgentSystem() -> fit(train_df) -> process_query.

    Fits on the TRAIN file only. Validation is never touched here.
    Errors are deliberately not swallowed so you see the real traceback.
    """
    import pandas as pd
    system = mod.MultiAgentSystem()
    if callable(getattr(system, "fit", None)):
        system.fit(pd.read_csv(_find_csv("train.csv")))
    return system.process_query


def _load():
    global _fn
    if _fn:
        return _fn
    if ENTRY:
        mod = importlib.import_module(ENTRY[0])
        target = getattr(mod, ENTRY[1]) if ENTRY[1] else mod
        if ENTRY[1] and inspect.isclass(target):
            target = target()
        _fn = getattr(target, ENTRY[2])
        return _fn

    mod = importlib.import_module(MODULE)
    cls = getattr(mod, "MultiAgentSystem", None)
    if cls is not None and hasattr(cls, "process_query"):
        _fn = _build(mod)
        return _fn
    for n in NAMES:
        f = getattr(mod, n, None)
        if callable(f) and not inspect.isclass(f):
            _fn = f
            return _fn
    for cname, cls in inspect.getmembers(mod, inspect.isclass):
        if cls.__module__ != mod.__name__:
            continue
        for n in NAMES:
            if hasattr(cls, n):
                try:
                    obj = cls()
                except TypeError:
                    continue
                _fn = getattr(obj, n)
                return _fn
    raise RuntimeError(
        f"Could not find an entry point in {MODULE}.\n"
        f"Public names found: {_public(mod)}\n"
        "Set ENTRY at the top of level1/adapter.py.")


def _walk(obj):
    """Breadth-first (key, value) pairs through nested dicts/lists/objects."""
    q = deque([(obj, 0)])
    while q:
        cur, depth = q.popleft()
        if depth > 5:
            continue
        if is_dataclass(cur) and not isinstance(cur, type):
            cur = asdict(cur)
        elif (hasattr(cur, "__dict__")
              and not isinstance(cur, (str, bytes, int, float, dict, list, tuple))):
            cur = vars(cur)
        if isinstance(cur, dict):
            for k, v in cur.items():
                yield str(k).lower(), v
                q.append((v, depth + 1))
        elif isinstance(cur, (list, tuple)):
            for v in cur:
                q.append((v, depth + 1))


def _dig(obj, exact, contains=(), types=(str,), skip=("true", "gold", "expected")):
    pairs = list(_walk(obj))
    ok = lambda v: isinstance(v, types) and not isinstance(v, bool) and v != ""
    for name in exact:
        for k, v in pairs:
            if k == name and ok(v):
                return v
    for sub in contains:
        for k, v in pairs:
            if sub in k and not any(s in k for s in skip) and ok(v):
                return v
    return None


def normalize(raw):
    if isinstance(raw, str):
        return {"intent": None, "category": None, "confidence": None,
                "action": None, "response": raw, "evidence": [], "raw": raw}
    evidence = _dig(raw, ("supporting_examples", "evidence", "examples",
                          "retrieved", "retrieved_examples", "supporting"),
                    ("example", "retriev", "support"), types=(list, tuple)) or []
    return {
        "intent": _dig(raw, ("intent", "predicted_intent"), ("intent",)),
        "category": _dig(raw, ("category", "predicted_category"), ("category",)),
        "confidence": _dig(raw, ("confidence", "intent_confidence", "score"),
                           ("confid", "prob"), types=(int, float)),
        "action": _dig(raw, ("action", "decision", "route")),
        "response": _dig(raw, ("final_response", "response", "answer", "reply",
                               "candidate_answer"),
                         ("response", "answer", "reply")),
        "evidence": list(evidence),
        "raw": raw,
    }


def run(query, threshold=None):
    """Run the full A1 -> A2 pipeline and return a normalised trace dict.

    If a threshold is given and process_query accepts `confidence_threshold`,
    it is passed through; otherwise the system's own default is used.
    """
    fn = _load()
    kwargs = {}
    if threshold is not None:
        try:
            if "confidence_threshold" in inspect.signature(fn).parameters:
                kwargs["confidence_threshold"] = threshold
        except (TypeError, ValueError):
            pass
    return normalize(fn(query, **kwargs))


def as_json(obj):
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How can I request a refund for my purchase?"
    t = run(q)
    print("query     :", q)
    for k in ("intent", "category", "confidence", "action"):
        print(f"{k:10}:", t[k])
    print("response  :", (t["response"] or "")[:400])
    print("evidence  :", len(t["evidence"]), "item(s)")
    missing = [k for k in ("intent", "category", "confidence", "response")
               if t[k] in (None, "")]
    if missing:
        print("\nNOT FOUND in output:", missing)
        print("Raw output follows, paste it to Claude so the adapter can be fixed:\n")
        print(as_json(t["raw"]))
