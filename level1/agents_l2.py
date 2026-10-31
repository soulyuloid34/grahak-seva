"""Grahak Seva - Level 2: A3 Router, A4 Response Auditor, A5 Coordinator.

Put this file in the same folder as trace.py (level1/). No API key and no network:
every agent runs locally on top of the A1 -> A2 output that trace.run_trace already produces.

Pipeline (one shared record, every step appended to res["trace"]):
    A1 Intent Analyst -> A2 retrieval (both from trace.run_trace)
      -> A3 Router      : picks the next step from intent, uncertainty and evidence
      -> A4 Auditor     : intent alignment, grounding, unsupported claims  (accept / revise / flag)
      -> A2 revise      : at most ONE revision, picked from the retrieved evidence
      -> A5 Coordinator : final response + ANSWER / CLARIFY / ESCALATE

Quick test:   python agents_l2.py "I need a refund but cannot find my order number"
"""
import importlib.util
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

ANSWER, CLARIFY, ESCALATE = "ANSWER", "CLARIFY", "ESCALATE"
DECISIONS = (ANSWER, CLARIFY, ESCALATE)

# Tune these on the validation split (evaluate_l2.py prints the decision mix for the current values).
CFG = dict(
    esc_conf=0.35,   # A1 confidence below this -> ESCALATE (A1 has no idea)
    esc_sim=0.25,    # best retrieved example less similar than this -> no usable evidence -> ESCALATE
    margin=0.15,     # top-1 minus top-2 intent probability below this -> ambiguous -> CLARIFY
    agree=0.50,      # share of retrieved examples that must carry A1's intent (when they have labels)
    align_sim=0.30,  # intent-alignment fallback when the evidence has no intent labels
    ground=0.60,     # every sentence needs this share of its content words found in the evidence
)


def load_trace_module():
    """Load level1/trace.py by path ("trace" is also a standard-library module name)."""
    spec = importlib.util.spec_from_file_location("grahak_trace", HERE / "trace.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- text helpers
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)\+?\d[\d\s-]{8,13}\d(?!\d)")
ORDER_RE = re.compile(r"#\s?[A-Za-z0-9-]{4,}|\b[A-Za-z]{0,3}-?\d{5,9}\b")
# "... can't find my order number" / "lost the receipt"
LACKS_RE = re.compile(
    r"(can'?t|cant|cannot|couldn'?t|could not|don'?t|do not|didn'?t|did not|lost|forgot|"
    r"unable|missing|no)\b[^.?!]{0,40}\b(order\s*(number|id|no)|confirmation|receipt)", re.I)

PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
SENT_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"[a-z]{3,}")
STOP = set("""the and for you your are was were will can with that this from have has had not but all any
 our out get let its too also then than them they their there here what when where which who whom how
 please would could should may might just into onto over under about once been being very more most
 some such only own same few other each both""".split())

# Claims that an action has ALREADY happened. A support bot with no database access must never say these.
CLAIM_RES = [re.compile(p, re.I) for p in (
    r"\b(?:has|have|had|was|were|is|are)\s+(?:now\s+|already\s+|successfully\s+|just\s+)?(?:been\s+)?"
    r"(?:processed|refunded|cancel{1,2}ed|issued|credited|reversed|shipped|dispatched|delivered|approved|"
    r"completed|updated|changed|reset|resolved)\b",
    r"\b(?:i|we)(?:'ve|\s+have|\s+just|\s+already)\s+(?:processed|refunded|cancel{1,2}ed|issued|credited|"
    r"reversed|updated|changed|reset|escalated|placed)\b",
    r"\b(?:i|we)\s+(?:processed|refunded|cancel{1,2}ed|issued|credited|reversed|updated|changed|reset)\b",
)]
CONDITIONAL_RE = re.compile(r"\b(once|when|after|until|if|as soon as|before|whenever|unless)\b[^.!?]*$", re.I)


def extract_ref(text):
    """True if the text carries an order number, email or phone (something to look the order up with)."""
    return bool(EMAIL_RE.search(text) or ORDER_RE.search(text) or
                any(len(re.sub(r"\D", "", m.group())) >= 10 for m in PHONE_RE.finditer(text)))


def content_words(text):
    return {w for w in WORD_RE.findall(text.lower()) if w not in STOP}


def find_claims(text):
    """Sentences that claim an order/payment/refund/account change was already made.
    'Once your refund has been processed, you will...' is guidance, not a claim, so it is skipped."""
    hits = []
    for sent in SENT_RE.split(text):
        for rx in CLAIM_RES:
            m = rx.search(sent)
            if m and not CONDITIONAL_RE.search(sent[:m.start()]):
                hits.append(sent.strip())
                break
    return hits


def sanitize(text):
    """'{{Order Number}}' -> 'the order number' (unfilled dataset template fields must not reach a customer)."""
    return PLACEHOLDER_RE.sub(lambda m: "the " + m.group(1).lower(), text)


def _plain(x):
    """Make numpy scalars / tuples JSON-friendly so ss.history can still be exported."""
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if hasattr(x, "item") and not isinstance(x, (str, bytes)):
        try:
            return x.item()
        except Exception:
            return str(x)
    return x


def _step(trace, agent, role, inputs, outputs, t0, decision=None, evidence=None):
    trace.append({"agent": agent, "role": role, "inputs": inputs, "outputs": outputs,
                  "decision": decision, "evidence": evidence or [],
                  "ms": round((time.perf_counter() - t0) * 1000, 2)})


# ---------------------------------------------------------------- A3 Routing / Planning
def _margin(cands):
    p = sorted((float(c["prob"]) for c in cands), reverse=True)
    return p[0] - (p[1] if len(p) > 1 else 0.0) if p else 0.0


def _agreement(evidence, intent):
    labelled = [e for e in evidence if e.get("intent")]
    if not labelled:
        return None
    return sum(e["intent"] == intent for e in labelled) / len(labelled)


def a3_route(base, has_ref, threshold, cfg):
    """Select the next step from predicted intent, uncertainty and the available evidence."""
    a1, a2 = base["a1"], base["a2"]
    conf, sim = float(a1["confidence"]), float(a2["similarity"])
    margin = _margin(a1["candidates"])
    agree = _agreement(a2.get("neighbors") or a2["evidence"], a1["intent"])
    lacks = bool(LACKS_RE.search(base["query"])) and not has_ref
    sig = {"confidence": round(conf, 4), "margin": round(margin, 4), "similarity": round(sim, 4),
           "evidence_agreement": None if agree is None else round(agree, 4),
           "missing_order_reference": lacks, "threshold": threshold}

    if conf < cfg["esc_conf"] or sim < cfg["esc_sim"]:
        route, reason = "escalate", "low_confidence" if conf < cfg["esc_conf"] else "weak_evidence"
        steps = ["skip A4 (nothing reliable to audit)", "A5 recommends human review"]
    elif lacks:
        route, reason = "clarify", "missing_info"
        steps = ["skip A4 (no answer yet)", "A5 asks for the order reference"]
    elif conf < threshold or margin < cfg["margin"]:
        route, reason = "clarify", "ambiguous_intent"
        steps = ["skip A4 (no answer yet)", "A5 asks a focused follow-up"]
    else:
        conflict = agree is not None and agree < cfg["agree"]
        route, reason = "answer", "evidence_conflict" if conflict else "confident"
        steps = ["A4 audits the draft", "revise once from the evidence if A4 objects", "A5 finalises"]
    return {"route": route, "reason": reason, "signals": sig, "next_steps": steps}


# ---------------------------------------------------------------- A4 Response Auditor
def a4_audit(text, source, base, cfg, conflict=False):
    """Check one candidate response. source = the retrieved example the text came from (or None)."""
    a1, evidence = base["a1"], base["a2"]["evidence"]
    # 1) intent alignment
    if source is not None and source.get("intent"):
        aligned = source["intent"] == a1["intent"]
    else:
        aligned = float(base["a2"]["similarity"]) >= cfg["align_sim"]
    # 2) grounding: every sentence must be covered by the retrieved evidence
    pool = set()
    for e in evidence:
        pool |= content_words(e.get("response", ""))
    weak = []
    for s in SENT_RE.split(sanitize(text)):
        cw = content_words(s)
        if cw and len(cw & pool) / len(cw) < cfg["ground"]:
            weak.append(s.strip())
    n_sent = max(1, len([s for s in SENT_RE.split(text) if content_words(s)]))
    grounding = 1.0 - len(weak) / n_sent
    # 3) unsupported claims: completed actions, or ids/amounts that appear nowhere in the evidence or query
    claims = find_claims(text)
    evid_text = " ".join(e.get("response", "") for e in evidence) + " " + base["query"]
    invented = [n for n in re.findall(r"\b\d{4,}\b", text) if n not in evid_text]
    claims += [f"number not in evidence: {n}" for n in invented]
    placeholders = PLACEHOLDER_RE.findall(text)

    issues = []
    if not aligned:
        issues.append("response is not about the predicted intent")
    if weak:
        issues.append(f"{len(weak)} sentence(s) not supported by the evidence")
    if claims:
        issues.append("claims an action was already completed or states unsupported facts")
    if placeholders:
        issues.append("unfilled template fields")
    if conflict:
        issues.append("retrieved examples disagree with the predicted intent")
    verdict = "accept" if not issues else "revise"
    return {"intent_aligned": aligned, "grounding": round(grounding, 3), "ungrounded": weak,
            "unsupported_claims": claims, "placeholders": placeholders,
            "evidence_conflict": conflict, "issues": issues, "verdict": verdict}


def a2_revise(draft, base, cfg):
    """A2 second attempt: clean the draft, else take the next-best retrieved example that passes A4."""
    clean = sanitize(draft)
    if clean != draft:
        audit = a4_audit(clean, None, base, cfg)
        if audit["verdict"] == "accept":
            return clean, None, audit, "filled template fields"
    for e in sorted(base["a2"]["evidence"], key=lambda e: -float(e.get("similarity", 0))):
        if e.get("response", "").strip() == draft.strip():
            continue
        if e.get("intent") and e["intent"] != base["a1"]["intent"]:
            continue
        text = sanitize(e["response"])
        audit = a4_audit(text, e, base, cfg)
        if audit["verdict"] == "accept":
            return text, e, audit, "switched to the next-best evidence example"
    return None, None, None, "no retrieved example passes the audit"


# ---------------------------------------------------------------- A5 Coordinator
def _q_missing():
    return ("No problem, that happens a lot. Your order number is usually in the confirmation email or under "
            "*My Orders* in your account. If you can't find it, tell me the **email or phone number** you used "
            "at checkout, or the **item name and roughly when you bought it**, and I'll work from that.")


def _q_ambiguous(a1):
    names = [str(c["intent"]).replace("_", " ") for c in a1["candidates"][:2] if float(c["prob"]) >= 0.1]
    guess = (f" Is this about **{names[0]}**" + (f" or **{names[1]}**" if len(names) > 1 else "") + "?"
             if names else "")
    return ("I want to be sure I give you the right help, and I'm not fully sure what you need yet." + guess +
            " Could you tell me a bit more, for example what you ordered and what went wrong?")


ESC_TEXT = {
    "low_confidence": "I couldn't work out what you need with enough confidence",
    "weak_evidence": "I don't have reliable guidance for this request",
    "unresolved_conflict": "the guidance I found was contradictory and I couldn't resolve it",
    "unsupported_claim": "I couldn't produce a response I can fully stand behind",
    "still_unclear": "your request is still unclear after a follow-up question",
    "no_order_reference": "I couldn't match this to an order",
}


def escalation_message(reason_key):
    why = ESC_TEXT.get(reason_key, "this needs a closer look")
    return (f"I want to be sure you get the right help, so I'm recommending this for **human review**, because "
            f"{why}. A support agent can verify your details and look into it. Nothing on your order, payment, "
            f"refund or account has been changed.")


def a5_coordinate(base, plan, final_text, audit, cfg):
    """Combine agent outputs into the final decision, response and reason."""
    if plan["route"] == "clarify":
        text = _q_missing() if plan["reason"] == "missing_info" else _q_ambiguous(base["a1"])
        return {"decision": CLARIFY, "final_response": text, "reason": plan["reason"]}
    if plan["route"] == "escalate":
        return {"decision": ESCALATE, "final_response": escalation_message(plan["reason"]),
                "reason": plan["reason"]}
    # answer route: A4 verdict decides
    if final_text is None:
        second = [c for c in base["a1"]["candidates"][1:2] if float(c["prob"]) >= 0.1]
        if audit and not audit["intent_aligned"] and second:
            return {"decision": CLARIFY, "final_response": _q_ambiguous(base["a1"]),
                    "reason": "ambiguous_intent"}
        key = "unresolved_conflict" if audit and audit["evidence_conflict"] else "unsupported_claim"
        return {"decision": ESCALATE, "final_response": escalation_message(key), "reason": key}
    if find_claims(final_text):          # last guard: never tell a customer something was already done
        return {"decision": ESCALATE, "final_response": escalation_message("unsupported_claim"),
                "reason": "unsupported_claim"}
    return {"decision": ANSWER, "final_response": final_text, "reason": plan["reason"]}


def force_escalate(res, reason_key, t0=None):
    """Used by the UI when follow-up questions are exhausted. Keeps decision, response and trace consistent."""
    t0 = t0 or time.perf_counter()
    res["decision"] = ESCALATE
    res["a5"] = {"decision": ESCALATE, "final_response": escalation_message(reason_key), "reason": reason_key}
    res["final_response"] = res["a5"]["final_response"]
    _step(res["trace"], "A5", "Coordinator", {"override": reason_key}, res["a5"], t0, decision=ESCALATE)
    return res


# ---------------------------------------------------------------- pipeline
def run_level2(system, query, T=None, threshold=0.8, has_ref=False, cfg=None):
    """Full five-agent run. Returns the Level 1 trace dict plus a3 / a4 / a5 / trace / final_response,
    with res["decision"] now one of ANSWER / CLARIFY / ESCALATE (Level 1's value is kept in res["l1_decision"])."""
    cfg = {**CFG, **(cfg or {})}
    T = T or load_trace_module()
    t_all = time.perf_counter()
    trace = []

    t0 = time.perf_counter()
    base = T.run_trace(system, query, threshold=threshold)
    a1, a2 = base["a1"], base["a2"]
    _step(trace, "A1", "Intent Analyst", {"query": query},
          {"intent": a1["intent"], "category": a1["category"], "confidence": a1["confidence"],
           "top_candidates": [(c["intent"], round(float(c["prob"]), 4)) for c in a1["candidates"][:3]]},
          t0, decision=None)
    _step(trace, "A2", "Response Specialist", {"intent": a1["intent"], "handoff": base.get("handoff")},
          {"draft_response": a2["response"], "similarity": a2["similarity"],
           "matched_instruction": a2["matched_instruction"]},
          t0, evidence=[{"instruction": e.get("instruction"), "similarity": e.get("similarity")}
                        for e in a2["evidence"]])

    has_ref = has_ref or extract_ref(query)
    t0 = time.perf_counter()
    plan = a3_route(base, has_ref, threshold, cfg)
    _step(trace, "A3", "Routing / Planning", {"signals": plan["signals"]},
          {"route": plan["route"], "reason": plan["reason"], "next_steps": plan["next_steps"]},
          t0, decision=plan["route"].upper())

    audit0 = audit1 = None
    final_text, revised, note = None, 0, None
    if plan["route"] == "answer":
        draft = a2["response"]
        source = next((e for e in a2["evidence"] if e.get("response", "").strip() == draft.strip()), None)
        t0 = time.perf_counter()
        audit0 = a4_audit(draft, source, base, cfg, conflict=plan["reason"] == "evidence_conflict")
        _step(trace, "A4", "Response Auditor", {"draft_response": draft}, audit0, t0,
              decision=audit0["verdict"].upper(),
              evidence=[{"issue": i} for i in audit0["issues"]])
        if audit0["verdict"] == "accept":
            final_text, audit1 = draft, audit0
        else:
            t0 = time.perf_counter()
            new, src, a_new, note = a2_revise(draft, base, cfg)
            revised = 1
            audit1 = a_new or {**audit0, "verdict": "flag"}
            final_text = new
            _step(trace, "A2", "Response Specialist (revision)", {"issues": audit0["issues"]},
                  {"revised_response": new, "how": note}, t0,
                  decision="REVISED" if new else "NO_REVISION",
                  evidence=[{"instruction": src.get("instruction"), "similarity": src.get("similarity")}]
                  if src else [])
            t0 = time.perf_counter()
            _step(trace, "A4", "Response Auditor (re-check)", {"revised_response": new},
                  audit1, t0, decision=audit1["verdict"].upper())
    else:
        _step(trace, "A4", "Response Auditor", {"route": plan["route"]},
              {"skipped": True, "why": "A3 routed away from a direct answer"}, time.perf_counter(),
              decision="SKIPPED")

    t0 = time.perf_counter()
    a5 = a5_coordinate(base, plan, final_text, audit1 or audit0, cfg)
    _step(trace, "A5", "Coordinator",
          {"route": plan["route"], "a4_verdict": (audit1 or audit0 or {}).get("verdict"), "revisions": revised},
          {"final_response": a5["final_response"], "reason": a5["reason"]}, t0, decision=a5["decision"])

    res = dict(base)
    res["l1_decision"] = base.get("decision")
    res.update({
        "a3": plan,
        "a4": {"skipped": plan["route"] != "answer", "first_pass": audit0, "final": audit1,
               "revision_count": revised, "revision_note": note,
               "verdict": (audit1 or {}).get("verdict", "skipped")},
        "a5": a5, "decision": a5["decision"], "final_response": a5["final_response"],
        "trace": trace,
        "latency_ms": float(base.get("latency_ms", 0)) + (time.perf_counter() - t_all) * 1000,
    })
    return _plain(res)


if __name__ == "__main__":
    import json
    T = load_trace_module()
    train, _val = T.load_data()
    system = T.build_system(train)
    q = " ".join(sys.argv[1:]) or "I need a refund but cannot find my order number"
    r = run_level2(system, q, T=T)
    for s in r["trace"]:
        print(f'{s["agent"]:3} {s["role"]:34} {str(s["decision"]):12} {s["ms"]:7.1f} ms')
    print("\nDECISION:", r["decision"], "|", r["a5"]["reason"])
    print(r["final_response"])
    print("\n", json.dumps(r["a3"]["signals"], indent=2))
