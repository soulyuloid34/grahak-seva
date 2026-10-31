#!/usr/bin/env python3
"""Generate results/traces.md with 5 end-to-end agent traces.

Run from the project root:  python3 level1/make_traces.py
Traces: clean query, colloquial/noisy query, ambiguous query, a misclassified
validation query, and an out-of-scope query.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adapter  # noqa: E402

ROOT = adapter.ROOT
RESULTS = ROOT / "results"
SAMPLE = 400
AMBIGUOUS = "I have a problem with my stuff"
OUT_OF_SCOPE = "What is the weather like in Paris today?"


def find(name):
    for p in (ROOT / "data" / name, ROOT / name):
        if p.exists():
            return p
    sys.exit(f"Could not find {name}")


def safe_run(q):
    try:
        return adapter.run(q)
    except Exception as e:  # keep going so one failure doesn't lose all traces
        return {"intent": None, "category": None, "confidence": None,
                "action": None, "response": f"[pipeline error: {e}]",
                "evidence": [], "raw": {"error": str(e)}}


def fmt_conf(c):
    return f"{c:.2f}" if isinstance(c, (int, float)) else str(c)


def render(n, title, note, query, trace, truth=None):
    L = [f"## Trace {n}: {title}\n", f"*{note}*\n",
         f"**Customer query:** {query}\n"]
    if truth is not None:
        L.append(f"**Ground truth:** intent `{truth['intent']}`, "
                 f"category `{truth['category']}`\n")
    L += ["**A1 Intent Analyst output**\n",
          f"- intent: `{trace['intent']}`",
          f"- category: `{trace['category']}`",
          f"- confidence: {fmt_conf(trace['confidence'])}\n",
          "**Handoff to A2 Response Specialist** (A1's intent, category and "
          "confidence are passed on; A2 uses them to choose guidance)\n"]
    if trace["evidence"]:
        L.append("**Supporting examples retrieved**\n")
        for i, ev in enumerate(trace["evidence"][:3], 1):
            text = ev if isinstance(ev, str) else adapter.as_json(ev)
            L.append(f"{i}. {text[:300].replace(chr(10), ' ')}")
        L.append("")
    L += [f"**Action:** {trace['action'] or 'answer'}\n",
          "**Final response**\n", f"> {(trace['response'] or '').replace(chr(10), chr(10) + '> ')}\n"]
    if truth is not None and truth.get("response"):
        L += ["**Reference response (dataset)**\n",
              f"> {str(truth['response'])[:600].replace(chr(10), chr(10) + '> ')}\n"]
    L += ["<details><summary>Raw trace</summary>\n", "```json",
          adapter.as_json(trace["raw"])[:3000], "```", "</details>\n"]
    return "\n".join(L)


def main():
    val = pd.read_csv(find("validation.csv"))
    sample = val.sample(n=min(SAMPLE, len(val)), random_state=42).reset_index(drop=True)
    print(f"Scanning up to {len(sample)} validation rows for trace candidates...")

    clean = noisy = wrong = None
    for _, row in sample.iterrows():
        if clean and noisy and wrong:
            break
        flags = str(row["flags"])
        is_special = any(ch in flags for ch in "QZ")
        need_clean = clean is None and not is_special
        need_noisy = noisy is None and is_special
        if not (need_clean or need_noisy or wrong is None):
            continue
        t = safe_run(row["instruction"])
        right = str(t["intent"]) == str(row["intent"])
        item = (row, t)
        if right and need_clean:
            clean = item
        elif right and need_noisy:
            noisy = item
        elif not right and wrong is None:
            wrong = item

    parts = ["# Agent traces\n",
             "Five end-to-end examples from the A1 -> A2 pipeline. Validation "
             "queries are drawn from the held-out file with seed 42.\n"]

    def truth_of(r):
        return {"intent": r["intent"], "category": r["category"],
                "response": r["response"]}

    if clean:
        r, t = clean
        parts.append(render(1, "clean validation query, answered correctly",
                            "Shows the normal path: classify, hand off, retrieve, respond.",
                            r["instruction"], t, truth_of(r)))
    if noisy:
        r, t = noisy
        parts.append(render(2, "colloquial or noisy wording",
                            f"Query carries variation flags `{r['flags']}`.",
                            r["instruction"], t, truth_of(r)))
    parts.append(render(3, "ambiguous query",
                        "Expected to lower confidence and trigger clarification.",
                        AMBIGUOUS, safe_run(AMBIGUOUS)))
    if wrong:
        r, t = wrong
        parts.append(render(4, "misclassified validation query",
                            "A failure case, shown honestly with the reference answer.",
                            r["instruction"], t, truth_of(r)))
    else:
        parts.append(f"## Trace 4: misclassified query\n\nNo misclassification "
                     f"was found in the scanned sample of {len(sample)} rows.\n")
    parts.append(render(5, "out-of-scope query",
                        "Expected to escalate to a human rather than guess.",
                        OUT_OF_SCOPE, safe_run(OUT_OF_SCOPE)))

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / "traces.md"
    path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Saved {path}")
    print("Check traces 3 and 5: if they did not clarify or escalate, "
          "tell Claude what action/confidence they showed.")


if __name__ == "__main__":
    main()
