# -*- coding: utf-8 -*-
"""Pre-translate every dashboard and page string so switching language is instant (and works offline).

Why: the first time a language is selected, the app translates every dashboard string (top intents, recent
queries, labels, notes) one by one on the CPU while the page waits. Results are cached in
translations_cache.json, so this only has to happen once. This script does it ahead of time by running the real
app headlessly for every store, language and page.

Run from the level1 folder (stop `streamlit run` first, it competes for the CPU):
    python warm_translations.py hi              # Hindi only (about the demo language), do this first
    python warm_translations.py hi bn ta te mr  # several
    python warm_translations.py                 # all five Indian languages
    python warm_translations.py hi --quality    # slower, better translations (beam search)

Tip: afterwards run each demo query once per language in the app so the chat replies are cached too.
"""
import json
import sys
import time
from pathlib import Path

import lang as LG
import stores as S

if "--quality" not in sys.argv:
    # greedy decoding is roughly 3x faster than beam search and fine for short UI labels
    def _fast_line(line, src, dst):
        import torch
        tok, model = LG._nllb_load()
        m = LG._PREFIX.match(line)
        prefix, body = (m.group(1), line[m.end():]) if m else (
            "", line.strip())
        sents = [x.strip() for x in LG._SENT.split(body) if x.strip()]
        if not sents:
            return line
        tok.src_lang = LG.NLLB_CODE[src]
        outs = []
        for i in range(0, len(sents), 8):
            enc = tok(sents[i:i + 8], return_tensors="pt",
                      padding=True, truncation=True, max_length=256)
            with torch.no_grad():
                gen = model.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids(LG.NLLB_CODE[dst]),
                                     num_beams=1, max_new_tokens=256)
            outs += tok.batch_decode(gen, skip_special_tokens=True)
        return prefix + " ".join(outs)
    LG._nllb_line = _fast_line

try:
    from transformers.utils import logging as _hf_logging
    _hf_logging.set_verbosity_error()
except Exception:
    pass

from streamlit.testing.v1 import AppTest  # noqa: E402

wanted = [a for a in sys.argv[1:] if not a.startswith(
    "--")] or [c for c in LG.ORDER if c != "en"]
ui = str(Path(__file__).with_name("ui.py"))


def cache_size():
    try:
        return len(json.loads(LG.CACHE_FILE.read_text(encoding="utf-8")))
    except Exception:
        return 0


t0 = time.time()
print(f"cache starts with {cache_size()} translations", flush=True)
for lg in wanted:
    for stn in S.STORES:
        for page in ("home", "query"):
            at = AppTest.from_file(ui, default_timeout=3600)
            at.query_params["page"] = page
            at.session_state["lang"] = lg
            at.session_state["store"] = stn["id"]
            at.run()
            err = "  ERROR: " + \
                str(at.exception[0].value)[:150] if at.exception else ""
            print(f"{lg} | {stn['id']:9} | {page:5} | cache {cache_size():5} | {time.time() - t0:5.0f}s{err}",
                  flush=True)
print("done. Start the app with:  HF_HUB_OFFLINE=1 streamlit run ui.py")
