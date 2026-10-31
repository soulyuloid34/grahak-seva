"""Grahak Seva - landing dashboard + live A1 -> A2 query UI (Streamlit).

Run from the project root:   streamlit run level1/ui.py
or from level1:              streamlit run ui.py

Routes (same app, switched with a query parameter):
    /                -> landing dashboard (home.html, same folder as this file)
    /?page=query     -> "New query" page (chat, agent workings, insights, history)

Needs level1/trace.py (A1 -> A2 pipeline with full trace) and level1/home.html.
Optional: drop Briston / Harlow Solid font files in level1/fonts/ (or next to this file) and
they are embedded automatically; otherwise the fonts installed on the machine are used.
Needed: put .streamlit/config.toml next to where you launch the app (see config.toml): it forces the light
theme so tables, sliders and the popover are not drawn dark.
"""
import base64
import functools
import html
import json
import re
import base64
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stores as S  # noqa: E402  (the six demo stores)
import lang as LG   # noqa: E402  (English + Indian-language layer)


def _t(text, **fmt):
    """UI text in the language chosen in the sidebar."""
    return LG.tr(text, st.session_state.get("lang", "en"), **fmt)


import importlib.util  # noqa: E402

BLUE, BUTTER, CHOCO = "#c4dae8", "#feefb8", "#432f2e"
# shown on the navbar "Copy email" button
SUPPORT_EMAIL = "support@grahakseva.example"

# Grahak Seva logo (smiling support-desk mark), embedded so no extra file is needed. Same image as logo.png.
LOGO_B64 = "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LvjzL/z+zzz52EOf27H12fWd+UOIuRfgRXbuaxUqoc/NTJ4xc8kC3L3J3FB3wagroo71XImj9rZhoPfKUOoVDoC/1cueme691sDxHl9c5kQxQ0W02YysWL2C9RvWfe/KG6/49Q/+0A9+SZb89T114+2iuFCvafA2bUI3b8YajSb3/OkffuS+e772k9tffOrjB/btXzN/+BDV/DxYykKCGvpDjkpJT2jQejpqDg2JWcPChRCcSjo1p0pP3smH+H2VzE6fDPOkkUAKogHVgGXRA2JQQhBGxsZYtnylr1u3Zttll1/yBzd//EO/Ixf95DP1aNU7FrC9YQDne31B48vdi0dv/+Nrn3/qiRv27973fbtf3nnloQP7z587MhtFFQl5RD3SzsLQgT5PmZLQqkvhKUs+SSLFRBDNqj+q9cTvm9gN6betvgsNMEFFYo8lsyYazBbiTWI55/4V88zMMz4xQWukWRrp+fElE4dXr1n1/Hnrz7vr4isvuX/80r//lEjeKutUlS+u03OiH/qYO8/dW52Xt5x//z13X3nw0FSELBjdLRMNzQFCgnogIZHa05Qz+2mFLiONREoJQn6OhkDQQHiDSQlXcRUZd1HzMs2JvPuK3Rrj+qBhgwYZc0ie/KBV9kxFNSX2Zj9vIISClDJV1uTKSZZNLinPXbf+ES56335477yItBd24k26efNmW4zn5/8HGG77/WM/G40AAAAASUVORK5CYII="
LOGO_HTML = f'<img src="data:image/png;base64,{LOGO_B64}" alt="Grahak Seva logo">'

try:   # browser-tab icon = the logo (falls back to the emoji if Pillow is missing)
    import io
    from PIL import Image
    _icon = Image.open(io.BytesIO(base64.b64decode(LOGO_B64)))
except Exception:
    _icon = "🛍️"

st.set_page_config(page_title="Grahak Seva", page_icon=_icon, layout="wide",
                   initial_sidebar_state="expanded")


# ---------- fonts: Briston (page heading) + Harlow Solid (sub-headings and body) ----------
_FONT_TYPES = {".woff2": "woff2", ".woff": "woff",
               ".ttf": "truetype", ".otf": "opentype"}
_FONT_MIME = {".woff2": "font/woff2", ".woff": "font/woff",
              ".ttf": "font/ttf", ".otf": "font/otf"}


def _find_font(prefix):
    for folder in (HERE / "fonts", HERE, HERE.parent / "fonts"):
        if folder.is_dir():
            for f in sorted(folder.iterdir()):
                key = re.sub(r"[\s_-]+", "", f.stem.lower())
                if f.suffix.lower() in _FONT_TYPES and key.startswith(prefix):
                    return f
    return None


@functools.lru_cache(maxsize=None)
def font_css():
    """@font-face rules: installed font first, then an embedded copy if a font file is found."""
    def face(family, local_names, prefix):
        src = [f'local("{n}")' for n in local_names]
        f = _find_font(prefix)
        if f:
            b64 = base64.b64encode(f.read_bytes()).decode()
            src.append(f'url(data:{_FONT_MIME[f.suffix.lower()]};base64,{b64}) '
                       f'format("{_FONT_TYPES[f.suffix.lower()]}")')
        return '@font-face{font-family:"%s";src:%s;font-display:swap}' % (family, ",".join(src))
    return (face("GS Display", ["Briston", "Briston Regular"], "briston") +
            face("GS Body", ["Harlow Solid Italic", "Harlow Solid", "HarlowSolid"], "harlow"))


def _load_json(name, default):
    """Read a JSON file that make_dashboard_data.py wrote next to ui.py."""
    try:
        return json.loads((HERE / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def _go(target):
    """Switch page inside the same Streamlit session (keeps chat + history)."""
    st.query_params["page"] = target


# ---------- stores: shared state, switching and the sidebar ----------
ss = st.session_state
ss.setdefault("history", [])   # every trace, newest first
ss.setdefault("chat", [])      # chat entries (user, text, trace), oldest first
# conversation waiting for the customer's answer
ss.setdefault("pending", None)
ss.setdefault("threshold", 0.8)
ss.setdefault("store", S.DEFAULT_STORE)
ss.setdefault("lang", "en")      # en / hi / bn / ta / te / mr
# store id -> its saved chat / history / pending conversation
ss.setdefault("store_state", {})

STORE_DATA = _load_json("stores.json", {}).get(
    "stores", {})   # made by make_store_data.py


def _set_store(new_id):
    """Save the current store's conversation, load the new store's (or an empty one)."""
    if new_id not in S.BY_ID or new_id == ss.store:
        return
    ss.store_state[ss.store] = {"chat": ss.chat,
                                "history": ss.history, "pending": ss.pending}
    saved = ss.store_state.get(new_id, {})
    ss.chat, ss.history, ss.pending = saved.get(
        "chat", []), saved.get("history", []), saved.get("pending")
    ss.store = new_id
    # makes store_refresh() show a short "connecting" moment
    ss.store_switching = True
    st.query_params["store"] = new_id


# a link like ?store=zepto selects that store too
_qs = st.query_params.get("store", None)
_qs = _qs[0] if isinstance(_qs, list) and _qs else _qs
if _qs in S.BY_ID and _qs != ss.store:
    _set_store(_qs)
STORE = S.BY_ID[ss.store]

SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"] { background:#432f2e !important; width:262px !important; min-width:262px !important; }
[data-testid="stSidebar"] * { color:#feefb8; }
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display:none !important; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top:1.2rem; }
[data-testid="stSidebar"] .gs-side-h { font-family:"GS Display",Briston,Georgia,serif; font-size:1.25rem; margin:0 0 .15rem; }
[data-testid="stSidebar"] .gs-side-s { font-size:.95rem; opacity:.8; margin:0 0 .9rem; line-height:1.35; }
[data-testid="stSidebar"] .stButton > button { width:100%; justify-content:flex-start; text-align:left; border-radius:14px;
  border:1.5px solid rgba(254,239,184,.22); background:transparent; color:#feefb8; padding:.55rem .9rem; min-height:2.8rem; }
[data-testid="stSidebar"] .stButton > button:hover { background:rgba(254,239,184,.14); border-color:rgba(254,239,184,.5); color:#feefb8; transform:none; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] { background:#feefb8; color:#432f2e; border-color:#feefb8; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] * { color:#432f2e !important; }
[data-testid="stSidebar"] .stButton > button p { font-size:1.08rem; margin:0; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.75rem !important; }   /* space between store buttons */
[data-testid="stSidebar"] .stButton { margin-bottom:.15rem; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background:#fff !important; border-radius:14px; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color:#432f2e !important; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] label p { font-size:.95rem; }
.gs-nav { left:262px !important; }
@media (max-width:1000px) { .gs-nav { left:0 !important; } }
.gs-contact { background:#fff; border:1px solid #eadfd0; border-left:6px solid var(--sc,#432f2e); border-radius:16px; padding:14px 18px; margin:.6rem 0 .2rem; color:#432f2e; }
.gs-contact h5 { margin:0 0 .5rem; font-size:1.08rem; font-weight:700; color:#432f2e; }
.gs-contact .row { display:flex; gap:10px; margin:.25rem 0; font-size:1.02rem; flex-wrap:wrap; }
.gs-contact .row b { min-width:92px; }
.gs-contact a { color:#432f2e !important; text-decoration:underline; }
.gs-contact .cap { font-size:.88rem; opacity:.7; margin-top:.5rem; }
a.gs-pill { display:inline-block; background:#432f2e; color:#feefb8 !important; border-radius:999px; padding:.55rem 1.3rem; text-decoration:none !important; font-size:1.02rem; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background:#fffbea !important; border-color:#eadfd0 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] input { color:#432f2e !important; -webkit-text-fill-color:#432f2e !important; caret-color:#432f2e !important; }
[data-testid="stSidebar"] [data-baseweb="select"] input::placeholder { color:#8a7776 !important; opacity:1 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill:#432f2e !important; }
[data-testid="stSidebar"] [data-baseweb="select"] * { -webkit-text-fill-color:#432f2e !important; }
[data-testid="stSidebar"] [data-baseweb="select"] input, [data-testid="stSidebar"] [data-baseweb="select"] [value], [data-testid="stSidebar"] [data-baseweb="select"] span { opacity:1 !important; }
[data-baseweb="popover"] ul[role="listbox"] { background:#64cfd9 !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color:#432f2e !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background:#feefb8 !important; }
html body [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] *,
html body [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] input { color:#432f2e !important; -webkit-text-fill-color:#432f2e !important; caret-color:#432f2e !important; opacity:1 !important; }
html body [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] svg { fill:#432f2e !important; }
</style>
"""


LOGO_DIR = HERE / "assets" / "logos"


def _logo_css():
    """Show each store's logo (assets/logos/<id>.png) on its sidebar button instead of text.
    A store with no logo file keeps a plain text button."""
    css, shown = [], False
    for stn in S.STORES:
        f = LOGO_DIR / f"{stn['id']}.png"
        if not f.exists():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode()
        css.append(f'[data-testid="stSidebar"] .st-key-store_{stn["id"]} button '
                   f'{{ background-image:url("data:image/png;base64,{b64}") !important; }}')
        css.append(f'[data-testid="stSidebar"] .st-key-store_{stn["id"]} button {{ '
                   f'background-color:#ffffff !important; background-repeat:no-repeat !important; '
                   f'background-position:center !important; background-size:contain !important; '
                   f'background-origin:content-box !important; padding:.6rem 1.4rem !important; '
                   f'min-height:3.3rem !important; border:2px solid rgba(254,239,184,.25) !important; }}')
        css.append(f'[data-testid="stSidebar"] .st-key-store_{stn["id"]} button p '
                   f'{{ font-size:0 !important; line-height:0 !important; color:transparent !important; }}')
        css.append(f'[data-testid="stSidebar"] .st-key-store_{stn["id"]} button:hover '
                   f'{{ border-color:#feefb8 !important; }}')
        # the selected store: full strength with a butter ring
        css.append(f'[data-testid="stSidebar"] .st-key-store_{stn["id"]} button[kind="primary"], '
                   f'[data-testid="stSidebar"] .st-key-store_{stn["id"]} button[data-testid="stBaseButton-primary"] '
                   f'{{ background-color:#ffffff !important; border:3px solid #feefb8 !important; '
                   f'box-shadow:0 0 0 4px rgba(254,239,184,.35); }}')
        shown = True
    return "<style>" + "\n".join(css) + "</style>" if shown else ""


HEADER_FIX_CSS = """
<style>
/* "Export traces" before the first query: visible but clearly inactive (was an invisible white box) */
.stDownloadButton > button:disabled, .stButton > button:disabled {
  opacity:1 !important; background:#f1e7d3 !important; color:#7b6660 !important;
  border:1.5px dashed #c9b9a6 !important; cursor:not-allowed; transform:none !important; }
.stDownloadButton > button:disabled * { color:#7b6660 !important; }
/* "Escalation threshold" popover trigger: it was unstyled (dark navy, grey text) */
[data-testid="stPopover"] button, button[data-testid="stPopoverButton"] {
  background:#ffffff !important; color:#432f2e !important; border:1.5px solid #e4d7c4 !important;
  border-radius:999px !important; font-size:1.05rem !important; min-height:2.9rem !important; box-shadow:none !important; }
[data-testid="stPopover"] button *, button[data-testid="stPopoverButton"] * { color:#432f2e !important; }
[data-testid="stPopover"] button:hover, button[data-testid="stPopoverButton"]:hover { background:#d6e4f0 !important; }
</style>
"""


def render_sidebar():
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    st.markdown(_logo_css(), unsafe_allow_html=True)
    with st.sidebar:
        st.selectbox("🌐 Language / भाषा", LG.ORDER, key="lang",
                     format_func=lambda c: LG.LANGS[c][0])
        st.markdown(f'<div class="gs-side-h">{html.escape(_t("Stores"))}</div><div class="gs-side-s">'
                    f'{html.escape(_t("Pick a store to see its support dashboard and chat with its assistant."))}</div>',
                    unsafe_allow_html=True)
        for stn in S.STORES:
            st.button(stn["name"], key=f"store_{stn['id']}", on_click=_set_store, args=(stn["id"],),
                      type="primary" if stn["id"] == ss.store else "secondary", use_container_width=True)
        st.markdown('<div class="gs-side-s" style="margin-top:.8rem;font-size:.82rem">' + html.escape(
            _t("Demo: all stores use the same five agents on their own slice of the Bitext data. No real store data or APIs."))
            + '</div>', unsafe_allow_html=True)


def store_refresh():
    """Mock refresh: a short 'connecting' moment each time the store changes (nothing is really reloaded)."""
    if ss.get("store_switching"):
        ss.store_switching = False
        with st.spinner(_t("Connecting to {store} support...", store=STORE["name"])):
            time.sleep(0.9)
        st.toast(_t("Connected to {store} support",
                 store=STORE["name"]), icon="✅")


def contact_card(stn):
    """Human-contact options shown after an ESCALATE decision (in the selected language)."""
    e = html.escape
    rows = []
    if stn.get("phone"):
        rows.append(
            f'<div class="row"><b>{e(_t("Phone"))}</b><span>{e(stn["phone"])}</span></div>')
    if stn.get("email"):
        rows.append(
            f'<div class="row"><b>{e(_t("Email"))}</b><a href="mailto:{e(stn["email"])}">{e(stn["email"])}</a></div>')
    if stn.get("hours"):
        rows.append(
            f'<div class="row"><b>{e(_t("Hours"))}</b><span>{e(stn["hours"])}</span></div>')
    rows.append(
        f'<div class="row"><b>{e(_t("In the app"))}</b><span>{e(_t(stn["in_app"]))}</span></div>')
    rows.append(f'<div class="row"><b>{e(_t("Help centre"))}</b><a href="{e(stn["help_url"])}" target="_blank" '
                f'rel="noopener">{e(_t("{store} customer support", store=stn["name"]))}</a></div>')
    demo_note = _t(
        "Demo build: confirm these contact options on {store}'s official website.", store=stn["name"])
    cap = "" if stn.get(
        "verified") else f'<div class="cap">{e(demo_note)}</div>'
    head = _t("Talk to a person at {store}", store=stn["name"])
    return (f'<div class="gs-contact" style="--sc:{stn["color"]}"><h5>{e(head)}</h5>' + "".join(rows) + cap + '</div>')


def _dash_payload(data):
    """Dashboard data for home.html in the selected language (numbers stay, words are translated)."""
    lang, m = ss.lang, (data.get("metrics") or {})
    if lang == "en" or not m:
        return data
    data = dict(data)
    nm = STORE["name"]
    data["subtitle"] = _t(
        "{store} support · {n} held-out customer queries handled by the five agents.", store=nm, n=f"{m['n']:,}")
    data["note"] = _t(
        "Simulated {store} slice of the Bitext validation split (threshold {th}). Not real {store} data.", store=nm, th=m["threshold"])
    labels = ["Queries handled", "Answered by agents",
              "Escalated to humans", "Avg. response time"]
    chips = [_t("held-out sample"), _t("{p}% needed a follow-up", p=f"{m['clarify_pct']:.1f}"),
             _t("{p}% of queries", p=f"{m['escalate_pct']:.1f}"), _t("A1 to A5 end to end")]
    data["kpis"] = [dict(k, label=_t(lb), chip=c)
                    for k, lb, c in zip(data["kpis"], labels, chips)]
    data["top_intents"] = [[_t(n), c] for n, c in data["top_intents"]]
    data["recent"] = [[_t(r[0])] + list(r[1:]) for r in data["recent"]]
    return data


DASH_KEYS = ["Dashboard", "New query", "Search", "Export", "Query volume", "weekly", "monthly", "yearly",
             "Resolved by agents", "Escalated", "Top intents", "Recent queries", "View all", "Customer query",
             "Intent", "Confidence", "Action", "When", "Answered", "Clarify", "All", "Validation replay"]


# ---------- route: landing page ----------
page = st.query_params.get("page", "home")
if isinstance(page, list):
    page = page[0] if page else "home"

if page != "query":
    render_sidebar()
    store_refresh()
    st.markdown("""
<style>
#MainMenu, footer, [data-testid="stHeader"] { visibility: hidden; }
.stApp { background: #fffbea; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
iframe { border: 0; display: block; }
.st-key-gs_go_query, .st-key-gs_go_home { display: none !important; }
</style>""", unsafe_allow_html=True)
    home_file = HERE / "home.html"
    if home_file.exists():
        logo_css = (".logo{width:48px;height:48px;padding:4px;border-radius:14px}"
                    ".logo img{display:block;width:100%;height:100%;object-fit:contain}")
        src = (home_file.read_text(encoding="utf-8")
               .replace('<span class="logo">GS</span>', '<span class="logo">' + LOGO_HTML + '</span>')
               .replace("</style>", font_css() + logo_css + "</style>", 1))
        # real numbers from the trained agents
        data = STORE_DATA.get(ss.store) or _load_json("dashboard.json", None)
        if data:
            data = _dash_payload(data)
            data = dict(data, labels={"brand": "Grahak Seva · " + STORE["name"],
                                      "title": _t("{store} support dashboard", store=STORE["name"]),
                                      "chat": _t("Chat with {store}", store=STORE["name"])})
            i18n = {k: _t(k) for k in DASH_KEYS} if ss.lang != "en" else {}
            src = src.replace("<script>", "<script>window.GS_DATA=" + json.dumps(data).replace("</", "<\\/")
                              + ";window.GS_I18N=" +
                              json.dumps(i18n, ensure_ascii=False).replace(
                                  "</", "<\\/")
                              + ";</script><script>", 1)
        # home.html resizes its own frame
        components.html(src, height=1250, scrolling=False)
    else:
        st.error("home.html not found next to ui.py.")
    # hidden helper buttons: home.html clicks "gs-go-query" when "+ New query" / "New query" is pressed
    st.button("gs-go-query", key="gs_go_query", on_click=_go, args=("query",))
    st.button("gs-go-home", key="gs_go_home", on_click=_go, args=("home",))
    st.stop()


# ---------- query page: load the A1 -> A2 pipeline ----------
# Load level1/trace.py by path: "trace" is also a Python standard-library module name.
_spec = importlib.util.spec_from_file_location(
    "grahak_trace", HERE / "trace.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)
# Level 2: A3 Router, A4 Auditor, A5 Coordinator (agents_l2.py sits next to this file)
_spec2 = importlib.util.spec_from_file_location(
    "grahak_agents_l2", HERE / "agents_l2.py")
L2 = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(L2)

QUERY_CSS = """
:root {
  --blue:__BLUE__; --butter:__BUTTER__; --choco:__CHOCO__;
  --bg:#fffbea; --card:#fff; --text:__CHOCO__; --muted:#6f5c5b; --border:#eadfd0; --top:__CHOCO__;
  --primary:__CHOCO__; --on-primary:__BUTTER__;
  --nav-h:68px; --gutter:24px;
  --shadow:0 1px 2px rgba(67,47,46,.06),0 8px 24px rgba(67,47,46,.06);
  --display:"GS Display",Briston,Georgia,serif;
  --body:"GS Body","Harlow Solid Italic","Avenir Next","Trebuchet MS","Kohinoor Devanagari","Kohinoor Bangla","Kohinoor Tamil","Kohinoor Telugu","Noto Sans Devanagari","Noto Sans Bengali","Noto Sans Tamil","Noto Sans Telugu",sans-serif;
  color-scheme: light;
}

/* ---- page shell: hide Streamlit chrome (NOT every <header>, the navbar must stay visible) ---- */
#MainMenu, footer, [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display:none !important; }
.stApp { background:var(--bg); color:var(--text); overflow-x:hidden; }
.block-container, [data-testid="stMainBlockContainer"] {
  padding:calc(var(--nav-h) + 36px) var(--gutter) 9rem !important; max-width:1200px !important; margin:0 auto; }
[data-testid="stVerticalBlock"] { gap:1.1rem; }
.stApp iframe[height="0"] { display:none; }
[data-testid="stElementContainer"]:has(iframe[height="0"]) { display:none; }
.st-key-gs_go_home, .st-key-gs_go_query { display:none !important; }

/* ---- type: Harlow Solid for body + sub-headings, Briston for the page heading ---- */
html, body, .stApp, button, input, textarea, label,
[data-testid="stMarkdownContainer"] *:not(i):not([data-testid="stIconMaterial"]),
[data-testid="stCaptionContainer"] *, [data-testid="stMetric"] *, [data-baseweb="tab"] *,
[data-testid="stExpander"] summary *:not([data-testid="stIconMaterial"]),
[data-testid="stPopover"] *:not([data-testid="stIconMaterial"]), [data-testid="stPopoverBody"] *:not([data-testid="stIconMaterial"]),
[data-testid="stAlert"] *:not([data-testid="stIconMaterial"]) {
  font-family:var(--body); font-synthesis:none; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
  font-size:1.12rem; line-height:1.65; letter-spacing:.01em; color:var(--text); }
[data-testid="stMarkdownContainer"] ol, [data-testid="stMarkdownContainer"] ul { padding-left:1.6rem; margin:.4rem 0 .7rem; }
[data-testid="stMarkdownContainer"] li { margin:.45rem 0; padding-left:.25rem; }
[data-testid="stMarkdownContainer"] strong { font-weight:700; }
.gs-hero h1, .big, [data-testid="stMetricValue"], [data-testid="stMetricValue"] * { font-family:var(--display) !important; }
.gs-hero { margin:0 0 .4rem; }
.gs-hero h1 { margin:0; padding:0; font-size:34px; line-height:1.15; font-weight:400; letter-spacing:-.02em; color:var(--text) !important; }
.gs-hero p { margin:10px 0 0; color:var(--muted) !important; font-size:1.15rem; max-width:64ch; }
.sec { font-size:1.35rem; color:var(--text); margin:.8rem 0 .2rem; scroll-margin-top:calc(var(--nav-h) + 16px); }
[data-testid="stCaptionContainer"] * { color:var(--muted) !important; font-size:1rem !important; }

/* ================= NAVBAR (dropdown + submenu, sliding links, copy-email button) ================= */
.gs-nav { position:fixed; top:0; left:0; right:0; z-index:1000; visibility:visible !important;
  background:var(--top); color:var(--butter);
  border-bottom:1px solid rgba(254,239,184,.14); box-shadow:0 8px 24px rgba(67,47,46,.18); }
.gs-nav, .gs-nav * { box-sizing:border-box; }
.gs-nav ul { list-style:none; margin:0; padding:0; }
.gs-nav .nav__list li, .gs-nav .dropdown__menu li, .gs-nav .dropdown__submenu li { margin:0; padding:0; font-size:inherit; line-height:inherit; color:inherit; }
.gs-nav a { color:var(--butter) !important; text-decoration:none !important; cursor:pointer; }
.gs-nav button { font:inherit; color:inherit; background:none; border:0; padding:0; margin:0; cursor:pointer; text-align:left; }
.gs-nav .nav { max-width:1200px; margin:0 auto; padding:0 var(--gutter); height:var(--nav-h); display:flex; align-items:center; gap:28px; }
.gs-nav .nav__logo { display:flex; align-items:center; gap:12px; font-family:var(--display) !important; font-size:22px; white-space:nowrap; }
.gs-nav .logo { display:grid; place-items:center; flex:none; width:52px; height:52px; padding:4px; border-radius:14px; background:var(--butter); }
.gs-nav .logo img { display:block; width:100%; height:100%; object-fit:contain; }
.gs-nav .nav__toggle { display:none; position:relative; width:42px; height:42px; border-radius:50%; border:1px solid rgba(254,239,184,.4) !important; place-items:center; color:var(--butter); font-size:22px; }
.gs-nav .nav__toggle i { position:absolute; transition:opacity .25s, transform .25s; }
.gs-nav .nav__close { opacity:0; transform:rotate(-90deg); }
.gs-nav .nav__toggle.show .nav__close { opacity:1; transform:none; }
.gs-nav .nav__toggle.show .nav__burger { opacity:0; transform:rotate(90deg); }
.gs-nav .nav__menu { flex:1; display:flex; align-items:center; }
.gs-nav .nav__list { display:flex; align-items:center; gap:6px; margin-left:auto !important; }
.gs-nav .nav__list > li { height:var(--nav-h); display:flex; align-items:center; }

/* top-level links: full-strength butter text, filled pill for the current page */
.gs-nav .nav__link { display:inline-flex; align-items:center; gap:6px; padding:9px 18px; border-radius:999px; font-size:17px; line-height:1.5; color:var(--butter); transition:background .2s; }
.gs-nav .nav__link:hover, .gs-nav .dropdown__item:hover > .nav__link, .gs-nav .dropdown__item.show-dropdown > .nav__link { background:rgba(254,239,184,.16); }
.gs-nav a.nav__link.on { background:var(--butter); color:var(--choco) !important; }
.gs-nav a.nav__link.on .slide b::after { color:var(--choco); }
.gs-nav .nav__link:focus-visible, .gs-nav .dropdown__link:focus-visible, .gs-nav .dropdown__sublink:focus-visible, .gs-nav .nav__copy:focus-visible { outline:2px solid var(--blue); outline-offset:2px; }

/* sliding label (hover reveals a second copy sliding up) */
.gs-nav .slide { display:block; overflow:hidden; height:1.5em; line-height:1.5em; }
.gs-nav .slide b { display:block; position:relative; font-weight:400; transition:transform .35s cubic-bezier(.6,.05,.2,1); }
.gs-nav .slide b::after { content:attr(data-t); position:absolute; left:0; top:100%; color:var(--blue); white-space:nowrap; }
.gs-nav a:hover .slide b, .gs-nav .nav__link:hover .slide b, .gs-nav .nav__copy:hover .slide b { transform:translateY(-100%); }

/* dropdown panel */
.gs-nav .dropdown__arrow, .gs-nav .dropdown__add { font-size:19px; transition:transform .3s; }
.gs-nav .dropdown__item { position:relative; }
.gs-nav .dropdown__menu { background:#352322; }
.gs-nav .dropdown__link, .gs-nav .dropdown__sublink { display:flex; align-items:center; gap:14px; width:100%; padding:10px 12px; border-radius:14px; color:var(--butter); transition:background .2s; }
.gs-nav .dropdown__link:hover, .gs-nav .dropdown__sublink:hover { background:rgba(254,239,184,.12); }
.gs-nav .dd-ico { display:grid; place-items:center; flex:none; width:40px; height:40px; border-radius:12px; background:rgba(196,218,232,.16); color:var(--blue); font-size:20px; transition:background .2s, color .2s; }
.gs-nav .dropdown__link:hover .dd-ico { background:var(--blue); color:var(--choco); }
.gs-nav .dd-txt { display:flex; flex-direction:column; min-width:0; }
.gs-nav .dd-title { font-size:17px; line-height:1.3; }
.gs-nav .dd-desc { font-size:14px; line-height:1.35; color:rgba(254,239,184,.78); white-space:nowrap; }
.gs-nav .dropdown__add { margin-left:auto; color:var(--blue); }
.gs-nav .dropdown__submenu { max-height:0; overflow:hidden; transition:max-height .35s ease; margin:0 0 0 31px !important; padding:0 0 0 12px !important; border-left:1px solid rgba(254,239,184,.22); }
.gs-nav .dropdown__sublink { padding:9px 12px; font-size:16px; gap:10px; }
.gs-nav .dropdown__sublink i { font-size:18px; color:var(--blue); }
.gs-nav .dropdown__subitem.show-submenu > .dropdown__submenu { max-height:240px; margin-bottom:6px !important; }
.gs-nav .dropdown__subitem.show-submenu > .dropdown__link .dropdown__add { transform:rotate(45deg); }
.gs-nav .dropdown__item.show-dropdown > .nav__link .dropdown__arrow { transform:rotate(180deg); }

/* copy-email button */
.gs-nav .nav__copy { margin-left:8px; display:inline-flex; align-items:center; gap:8px; border-radius:999px; padding:10px 20px; background:var(--butter); color:var(--choco); font-size:16px; white-space:nowrap; transition:background .2s, transform .12s; }
.gs-nav .nav__copy i { color:var(--choco); font-size:18px; }
.gs-nav .nav__copy:hover { transform:translateY(-1px); }
.gs-nav .nav__copy .slide b::after { color:var(--choco); }
.gs-nav .nav__copy.copied { background:var(--blue); }

@media (min-width:1001px) {
  .gs-nav .dropdown__menu { position:absolute; top:100%; left:0; min-width:310px; padding:10px; border:1px solid rgba(254,239,184,.18); border-radius:20px; box-shadow:0 22px 44px rgba(0,0,0,.32); opacity:0; visibility:hidden; transform:translateY(8px); transition:opacity .25s, transform .25s, visibility .25s; }
  .gs-nav .dropdown__item:hover > .dropdown__menu, .gs-nav .dropdown__item.show-dropdown > .dropdown__menu, .gs-nav .dropdown__item:has(:focus-visible) > .dropdown__menu { opacity:1; visibility:visible; transform:none; }
  .gs-nav .dropdown__item--end > .dropdown__menu { left:auto; right:0; }
  .gs-nav .dropdown__item:hover .dropdown__arrow { transform:rotate(180deg); }
  .gs-nav .dropdown__subitem:hover > .dropdown__submenu { max-height:240px; margin-bottom:6px !important; }
}
@media (max-width:1000px) {
  :root { --nav-h:64px; }
  .gs-nav .nav { flex-wrap:wrap; height:auto; gap:0; padding:0 16px; }
  .gs-nav .nav__data { width:100%; height:var(--nav-h); display:flex; align-items:center; justify-content:space-between; }
  .gs-nav .nav__toggle { display:grid; }
  .gs-nav .nav__menu { width:100%; flex:none; display:block; max-height:0; overflow:hidden; transition:max-height .4s ease; }
  .gs-nav .nav__menu.show { max-height:calc(100vh - var(--nav-h)); overflow-y:auto; }
  .gs-nav .nav__list { flex-direction:column; align-items:stretch; gap:4px; padding:6px 0 20px !important; }
  .gs-nav .nav__list > li { height:auto; display:block; }
  .gs-nav .nav__link { display:flex; width:100%; justify-content:space-between; border-radius:14px; padding:13px 14px; }
  .gs-nav .dropdown__menu { max-height:0; overflow:hidden; transition:max-height .35s ease; padding:0 0 0 8px !important; }
  .gs-nav .dropdown__item.show-dropdown > .dropdown__menu { max-height:560px; padding-top:4px !important; }
  .gs-nav .nav__copy { margin:12px 0 0; width:100%; justify-content:center; }
  .block-container, [data-testid="stMainBlockContainer"] { padding-left:16px !important; padding-right:16px !important; }
}

/* ---- cards, pills, bars (same tokens as the dashboard) ---- */
.card { background:var(--card); border:1px solid var(--border); border-radius:20px; padding:22px 24px; height:100%; box-shadow:var(--shadow); color:var(--text); }
.card.butter { background:var(--butter); color:var(--choco); border-color:transparent; }
.card.blue { background:var(--blue); color:var(--choco); border-color:transparent; }
.card h4 { margin:0 0 .6rem; font-size:1.08rem; font-weight:400; text-transform:none; letter-spacing:0; opacity:.8; color:inherit !important; }
.big { font-size:2.1rem; line-height:1.15; letter-spacing:-.02em; }
.pill { display:inline-block; background:var(--choco); color:var(--butter) !important; border-radius:999px; padding:.2rem .9rem; font-size:.98rem; margin:.5rem .4rem 0 0; }
.pill.light { background:var(--blue); color:var(--choco) !important; }
.flow { display:flex; gap:.6rem; align-items:center; flex-wrap:wrap; margin:.4rem 0 1.1rem; }
.step { background:var(--card); border:1px solid var(--border); border-radius:999px; padding:.45rem 1.1rem; font-size:1.02rem; }
.step.on { background:var(--butter); color:var(--choco); border-color:#e6d48f; }
.arrow { color:var(--muted); }
.bar { background:var(--border); border-radius:99px; height:8px; margin:.25rem 0 .8rem; overflow:hidden; }
.bar > div { background:var(--choco); height:8px; border-radius:99px; }
.card.blue .bar { background:#a9c3d4; } .card.blue .bar > div { background:var(--choco); }
.resp { background:var(--card); border-left:4px solid var(--butter); border-radius:10px; padding:.9rem 1.1rem; white-space:pre-wrap; }
.esc { background:var(--blue); color:var(--choco); border-radius:12px; padding:.7rem 1rem; margin-bottom:.8rem; }

/* ---- buttons: primary = chocolate pill with butter text, others = white outlined pill ---- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] > button {
  background:#fff; color:var(--text); border:1.5px solid var(--border); border-radius:999px;
  font-size:1.05rem; line-height:1.25; padding:.55rem 1.4rem; min-height:2.9rem; box-shadow:none; white-space:normal;
  transition:transform .12s ease, background .15s ease, border-color .15s ease; }
.stButton > button *, .stDownloadButton > button *, [data-testid="stPopover"] > button * { color:inherit !important; }
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stPopover"] > button:hover {
  background:var(--blue); border-color:var(--blue); color:var(--choco); transform:translateY(-1px); }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] { background:var(--choco); color:var(--butter); border-color:var(--choco); }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { background:#5a403e; border-color:#5a403e; color:var(--butter); }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible, [data-testid="stPopover"] > button:focus-visible { outline:3px solid var(--blue); outline-offset:2px; }
.stButton > button:disabled, .stDownloadButton > button:disabled { opacity:.5; transform:none; background:#fff; }
.stButton > button p, .stDownloadButton > button p { margin:0; line-height:1.25; font-size:1.05rem; color:inherit; white-space:normal !important; overflow:visible !important; text-overflow:clip !important; }
.stButton > button > div, .stButton > button [data-testid="stMarkdownContainer"] { width:100%; max-width:none; overflow:visible; }

/* ---- tabs as pills (no red underline, real padding between pills) ---- */
[role="tablist"] { gap:10px; border:0 !important; padding:2px 0 6px; flex-wrap:wrap; }
[role="tablist"] [data-baseweb="tab-highlight"], [role="tablist"] [data-baseweb="tab-border"] { display:none !important; }
[role="tablist"] button[role="tab"] { height:auto !important; margin:0 !important; padding:9px 22px !important; border:1.5px solid var(--border) !important; border-radius:999px !important; background:#fff !important; color:var(--text) !important; transition:background .15s, border-color .15s; }
[role="tablist"] button[role="tab"] p { margin:0; font-size:1.1rem; color:inherit !important; }
[role="tablist"] button[role="tab"]:hover { background:var(--blue) !important; border-color:var(--blue) !important; }
[role="tablist"] button[role="tab"][aria-selected="true"] { background:var(--choco) !important; border-color:var(--choco) !important; color:var(--butter) !important; }
[role="tablist"] button[role="tab"][aria-selected="true"] p { color:var(--butter) !important; }
[role="tabpanel"] { padding-top:1.2rem !important; }

/* ---- inputs ---- */
.stTextInput [data-baseweb="input"] { background:#fff !important; border:1.5px solid var(--border) !important; border-radius:999px !important; overflow:hidden; }
.stTextInput [data-baseweb="input"]:focus-within { border-color:var(--choco) !important; box-shadow:0 0 0 3px rgba(196,218,232,.7); }
.stTextInput [data-baseweb="base-input"], .stTextInput input { background:transparent !important; border:0 !important; color:var(--text) !important; -webkit-text-fill-color:var(--text); padding:.7rem 1.3rem; font-size:1.08rem; }
.stTextInput input::placeholder { color:var(--muted) !important; -webkit-text-fill-color:var(--muted); opacity:1; }

/* ---- chat composer: dark chocolate box, light butter text, aligned to the content column ---- */
[data-testid="stBottom"], [data-testid="stBottom"] > div { background:linear-gradient(to top, var(--bg) 72%, rgba(255,251,234,0)) !important; }
[data-testid="stBottomBlockContainer"] { max-width:1200px !important; width:100%; margin:0 auto; padding:14px var(--gutter) 26px !important; }
[data-testid="stChatInput"] { background:var(--choco) !important; border:1.5px solid var(--choco) !important; border-radius:999px !important; box-shadow:var(--shadow); padding:4px 8px 4px 14px; }
[data-testid="stChatInput"]:focus-within { box-shadow:0 0 0 3px var(--blue); }
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] [data-baseweb="textarea"], [data-testid="stChatInput"] [data-baseweb="base-input"] { background:transparent !important; border:0 !important; }
[data-testid="stChatInput"] textarea { background:transparent !important; color:var(--butter) !important; -webkit-text-fill-color:var(--butter); caret-color:var(--butter); font-size:1.12rem; padding:.75rem .9rem; }
[data-testid="stChatInput"] textarea::placeholder { color:rgba(254,239,184,.78) !important; -webkit-text-fill-color:rgba(254,239,184,.78); opacity:1; }
[data-testid="stChatInput"] button { background:var(--butter) !important; color:var(--choco) !important; border-radius:50% !important; }
[data-testid="stChatInput"] button svg { fill:var(--choco); color:var(--choco); }
[data-testid="stChatInput"] button:disabled { opacity:.55; }

/* ---- chat messages: even padding, avatar gap, readable text ---- */
[data-testid="stChatMessage"] { background:var(--card); border:1px solid var(--border); border-radius:22px; padding:1.15rem 1.5rem; margin-bottom:.2rem; box-shadow:var(--shadow); display:flex; align-items:flex-start; gap:1.1rem; }
[data-testid="stChatMessageContent"] { min-width:0; color:var(--text); }
[data-testid^="stChatMessageAvatar"] { flex:none; width:42px; height:42px; border-radius:12px; background:var(--butter); border:1px solid #e6d48f; color:var(--choco); }
[data-testid="stChatMessageAvatarUser"] { background:var(--blue); border-color:#a9c3d4; }

/* ---- expanders, alerts, popover panel, metrics, tables ---- */
[data-testid="stExpander"] details, details { background:var(--card) !important; border:1px solid var(--border) !important; border-radius:16px !important; overflow:hidden; }
[data-testid="stExpander"] summary { color:var(--text); padding:.85rem 1.2rem; }
[data-testid="stExpander"] summary:hover { background:rgba(196,218,232,.28); }
[data-testid="stExpanderDetails"] { padding:.5rem 1.2rem 1.2rem; }
[data-testid="stAlert"] { background:var(--blue) !important; color:var(--choco) !important; border:0 !important; border-radius:16px !important; padding:.9rem 1.2rem; }
[data-testid="stAlert"] * { color:var(--choco) !important; }
[data-testid="stPopoverBody"] { background:var(--card) !important; border:1px solid var(--border) !important; border-radius:18px !important; padding:1.2rem 1.4rem !important; min-width:340px; box-shadow:0 18px 40px rgba(67,47,46,.18); }
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] label { color:var(--text) !important; font-size:1.05rem; }
[data-testid="stMetric"] { background:var(--card); border:1px solid var(--border); border-radius:20px; padding:16px 20px; box-shadow:var(--shadow); }
[data-testid="stMetricLabel"] * { color:var(--muted); font-size:1.02rem; }
[data-testid="stMetricValue"] { color:var(--text); }
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:16px; overflow:hidden; }
"""

st.markdown(
    '<style>@import url("https://cdn.jsdelivr.net/npm/remixicon@3.2.0/fonts/remixicon.css");'
    + font_css()
    + QUERY_CSS.replace("__BLUE__", BLUE).replace("__BUTTER__",
                                                  BUTTER).replace("__CHOCO__", CHOCO)
    + "</style>", unsafe_allow_html=True)


# ---------- navbar ----------
# Patterns from bedimcode/responsive-dropdown-menu-2 (dropdown + submenu, mobile-first) and
# bedimcode/responsive-navbar-interaction (sliding links, copy-email button).
def _slide(text):
    return f'<span class="slide"><b data-t="{text}">{text}</b></span>'


def _item(label, icon, desc, tab, scroll=None):
    """Dropdown row: icon tile + sliding title + one-line description."""
    sc = f' data-scroll="{scroll}"' if scroll else ""
    return (f'<li><a class="dropdown__link" href="#" data-tab="{tab}"{sc}>'
            f'<span class="dd-ico"><i class="{icon}"></i></span>'
            f'<span class="dd-txt"><span class="dd-title">{_slide(label)}</span>'
            f'<span class="dd-desc">{desc}</span></span></a></li>')


def _subitem(label, icon, tab, scroll):
    return (f'<li><a class="dropdown__sublink" href="#" data-tab="{tab}" data-scroll="{scroll}">'
            f'<i class="{icon}"></i>{_slide(label)}</a></li>')


def _dropdown(label, items_html, end=False):
    """end=True opens the panel right-aligned so it never runs off the right edge of the screen."""
    return ('<li class="dropdown__item' + (' dropdown__item--end' if end else '') +
            '"><button class="nav__link" type="button">' + _slide(label) +
            '<i class="ri-arrow-down-s-line dropdown__arrow"></i></button>'
            '<ul class="dropdown__menu">' + items_html + '</ul></li>')


NAV_HTML = (
    # a <div>, not <header>: the page CSS hides Streamlit's own <header>
    '<div class="gs-nav" role="banner"><nav class="nav" aria-label="Main">'
    '<div class="nav__data">'
    '<a class="nav__logo" href="?page=home" target="_self" data-go="home"><span class="logo">' +
    LOGO_HTML + '</span>Grahak Seva</a>'
    '<button class="nav__toggle" id="gs-toggle" type="button" aria-label="Menu">'
    '<i class="ri-menu-line nav__burger"></i><i class="ri-close-line nav__close"></i></button></div>'
    '<div class="nav__menu" id="gs-menu"><ul class="nav__list">'
    f'<li><a class="nav__link" href="?page=home" target="_self" data-go="home">{_slide(_t("Dashboard"))}</a></li>'
    f'<li><a class="nav__link on" href="?page=query" target="_self">{_slide(_t("New query"))}</a></li>'
    + _dropdown(_t("Workspace"),
                _item(_t("Chat"), "ri-chat-3-line",
                      _t("Ask a question, get an answer"), _t("Chat"))
                + _item(_t("Agent workings"), "ri-flow-chart",
                        _t("See how the five agents handled it"), _t("Agent workings"))
                + _item(_t("History"), "ri-history-line", _t("Search every past query"), _t("History")))
    + _dropdown(_t("Insights"),
                _item(_t("Overview"), "ri-pie-chart-line",
                      _t("Live metrics and charts"), _t("Insights"))
                + '<li class="dropdown__subitem"><button class="dropdown__link" type="button">'
                  '<span class="dd-ico"><i class="ri-bar-chart-line"></i></span>'
                  '<span class="dd-txt"><span class="dd-title">' +
                _slide(_t("Reports")) + '</span>'
                  '<span class="dd-desc">' +
                _t("Jump to a section") + '</span></span>'
                  '<i class="ri-add-line dropdown__add"></i></button><ul class="dropdown__submenu">'
                + _subitem(_t("Confidence over time"),
                           "ri-line-chart-line", _t("Insights"), "gs-over-time")
                + _subitem(_t("Threshold table"), "ri-table-line",
                           _t("Insights"), "gs-threshold")
                + _subitem(_t("Weakest intents"), "ri-focus-3-line",
                           _t("Insights"), "gs-weak")
                + '</ul></li>', end=True)
    + f'<li><button class="nav__copy" type="button" data-copy="{SUPPORT_EMAIL}"><i class="ri-mail-line"></i>'
    + _slide(_t("Copy email")) + '</button></li>'
    '</ul></div></nav></div>'
)

NAV_JS = """
<script>
(function () {
  var P = window.parent; if (!P) return;
  // re-running replaces the previous listeners instead of stacking a second set
  if (P.__gsNavOff) { try { P.__gsNavOff(); } catch (e) {} }
  var D = P.document;
  function closeAll() {
    var m = D.getElementById('gs-menu'), t = D.getElementById('gs-toggle');
    if (m) m.classList.remove('show'); if (t) t.classList.remove('show');
    D.querySelectorAll('.dropdown__item.show-dropdown').forEach(function (x) { x.classList.remove('show-dropdown'); });
  }
  function copyText(text) {
    if (P.navigator.clipboard && P.isSecureContext) return P.navigator.clipboard.writeText(text);
    return new Promise(function (res, rej) {
      var ta = D.createElement('textarea'); ta.value = text; D.body.appendChild(ta); ta.select();
      try { D.execCommand('copy') ? res() : rej(); } catch (e) { rej(e); }
      D.body.removeChild(ta);
    });
  }
  function openTab(name, scrollId) {
    var tabs = D.querySelectorAll('button[role="tab"]');
    for (var i = 0; i < tabs.length; i++) {
      if (tabs[i].textContent.trim() === name) { tabs[i].click(); break; }
    }
    setTimeout(function () {
      var el = scrollId && D.getElementById(scrollId);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      else P.scrollTo({ top: 0, behavior: 'smooth' });
    }, 220);
  }
  function onClick(e) {
    var t = e.target;
    var tg = t.closest('#gs-toggle');
    if (tg) { var m = D.getElementById('gs-menu'); tg.classList.toggle('show', m.classList.toggle('show')); return; }
    var cp = t.closest('.nav__copy');
    if (cp) {
      copyText(cp.getAttribute('data-copy')).then(function () {
        var b = cp.querySelector('b'), old = b.textContent;
        cp.classList.add('copied'); b.textContent = 'Copied!'; b.setAttribute('data-t', 'Copied!');
        setTimeout(function () { cp.classList.remove('copied'); b.textContent = old; b.setAttribute('data-t', old); }, 1800);
      }, function () {});
      return;
    }
    var sub = t.closest('.dropdown__subitem > .dropdown__link');
    if (sub) { sub.parentElement.classList.toggle('show-submenu'); return; }
    var dd = t.closest('.dropdown__item > .nav__link');
    if (dd) {
      var it = dd.parentElement, was = it.classList.contains('show-dropdown');
      D.querySelectorAll('.dropdown__item.show-dropdown').forEach(function (x) { x.classList.remove('show-dropdown'); });
      if (!was) it.classList.add('show-dropdown');
      return;
    }
    var go = t.closest('.gs-nav [data-go]');
    if (go) {
      var hb = findBtn('gs-go-' + go.getAttribute('data-go'));
      if (hb) { e.preventDefault(); hb.click(); closeAll(); return; }
    }
    var a = t.closest('.gs-nav [data-tab]');
    if (a) { e.preventDefault(); openTab(a.getAttribute('data-tab'), a.getAttribute('data-scroll')); closeAll(); return; }
    if (!t.closest('.gs-nav')) closeAll();
  }
  function findBtn(name) {
    var bs = D.querySelectorAll('button');
    for (var i = 0; i < bs.length; i++) { if (bs[i].textContent.trim() === name) return bs[i]; }
    return null;
  }
  function hideHelpers() {
    ['gs-go-home', 'gs-go-query'].forEach(function (n) {
      var b = findBtn(n);
      if (b) { var c = b.closest('[data-testid="stElementContainer"]') || b; c.style.display = 'none'; }
    });
  }
  hideHelpers(); setTimeout(hideHelpers, 300); setTimeout(hideHelpers, 1200);
  function onKey(e) { if (e.key === 'Escape') closeAll(); }
  D.addEventListener('click', onClick, true);
  D.addEventListener('keydown', onKey, true);
  P.__gsNavOff = function () {
    D.removeEventListener('click', onClick, true);
    D.removeEventListener('keydown', onKey, true);
  };
})();
</script>
"""

render_sidebar()
store_refresh()
st.markdown(HEADER_FIX_CSS, unsafe_allow_html=True)
st.markdown(NAV_HTML, unsafe_allow_html=True)
components.html(NAV_JS, height=0)
st.button("gs-go-home", key="gs_go_home", on_click=_go, args=("home",))


# ---------- area / line chart (same look as the dashboard's Query volume chart) ----------
CHART_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="utf-8"><style>
__FONTS__
:root{--blue:#c4dae8;--butter:#feefb8;--choco:#432f2e;--card:#fff;--text:#432f2e;--muted:#8a7776;--border:#eadfd0;
--primary:#432f2e;--on-primary:#feefb8;--s1:#432f2e;--f1:#c4dae8;--s2:#9b8583;
--shadow:0 1px 2px rgba(67,47,46,.06),0 8px 24px rgba(67,47,46,.06)}
*{box-sizing:border-box}
html,body{margin:0;background:transparent;font-family:"GS Body","Harlow Solid Italic","Avenir Next","Trebuchet MS",sans-serif;font-synthesis:none;color:var(--text)}
.card{margin:2px;background:var(--card);border:1px solid var(--border);border-radius:20px;padding:20px 22px;box-shadow:var(--shadow)}
.head h2{margin:0 0 6px;font-size:20px;font-weight:400}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:15px;color:var(--muted);margin-bottom:4px}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px}
#chart{position:relative;width:100%;height:260px;touch-action:pan-y}
#chart svg{display:block;overflow:visible}
.tl{font-size:14px;fill:var(--muted)}.tl.on{fill:var(--text)}
#tip{position:absolute;pointer-events:none;opacity:0;transition:opacity .1s;background:var(--primary);color:var(--on-primary);border-radius:10px;padding:8px 10px;min-width:170px;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.2);z-index:2}
#tip .r{display:flex;justify-content:space-between;gap:16px;margin-top:4px}
#tip .r i{display:inline-block;width:7px;height:7px;border-radius:2px;margin-right:6px}
.cap{margin:8px 0 0;font-size:14px;color:var(--muted)}
</style></head><body>
<div class="card"><div class="head"><h2 id="t"></h2></div>
<div class="legend" id="lg"></div><div id="chart"><div id="tip"></div></div><p class="cap" id="cp"></p></div>
<script>
const CFG=__CFG__;
const $=s=>document.querySelector(s);
$("#t").textContent=CFG.title;$("#cp").textContent=CFG.caption||"";
$("#lg").innerHTML=CFG.series.map((s,i)=>`<span><i style="background:var(--s${i+1})"></i>${s.name}</span>`).join("");
const n=CFG.labels.length;
function fit(){try{const f=window.frameElement;if(f)f.style.height=Math.ceil(document.body.getBoundingClientRect().height+6)+"px"}catch(e){}}
function draw(){
  const wrap=$("#chart"),w=wrap.clientWidth||600,h=260,pl=8,pr=8,pt=14,pb=30;
  const max=CFG.ymax,min=CFG.ymin,X=i=>n>1?pl+i*(w-pl-pr)/(n-1):w/2,Y=v=>pt+(1-(v-min)/(max-min))*(h-pt-pb);
  const path=s=>s.values.map((v,i)=>(i?"L":"M")+X(i).toFixed(1)+" "+Y(v).toFixed(1)).join("");
  let g="";
  for(let i=0;i<n;i++)g+=`<line x1="${X(i)}" x2="${X(i)}" y1="${pt}" y2="${h-pb}" stroke="var(--border)"/>`;
  for(let i=0;i<n-1;i++){const m=(X(i)+X(i+1))/2;g+=`<line x1="${m}" x2="${m}" y1="${pt}" y2="${h-pb}" stroke="var(--border)" stroke-dasharray="5 5"/>`}
  const labels=CFG.labels.map((l,i)=>`<text class="tl" data-i="${i}" x="${X(i)}" y="${h-8}" text-anchor="middle">${l}</text>`).join("");
  const lines=CFG.series.map((s,i)=>`<path d="${path(s)}" fill="none" stroke="var(--s${i+1})" stroke-width="${i?1.75:2}"${s.dash?' stroke-dasharray="6 5"':''}/>`).join("");
  const dots=CFG.series.map((s,i)=>`<circle id="d${i}" r="4.5" fill="var(--card)" stroke="var(--s${i+1})" stroke-width="2" opacity="0"/>`).join("");
  wrap.querySelector("svg")?.remove();
  wrap.insertAdjacentHTML("afterbegin",`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <defs><linearGradient id="gr" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" style="stop-color:var(--f1);stop-opacity:.75"/><stop offset="95%" style="stop-color:var(--f1);stop-opacity:.08"/></linearGradient></defs>
    ${g}<path d="${path(CFG.series[0])}L${X(n-1)} ${h-pb}L${X(0)} ${h-pb}Z" fill="url(#gr)"/>${lines}
    <line id="cur" y1="${pt}" y2="${h-pb}" stroke="var(--s1)" stroke-width="1.5" opacity="0"/>${dots}${labels}</svg>`);
  const tip=$("#tip"),cur=$("#cur"),ds=CFG.series.map((_,i)=>$("#d"+i));
  const off=()=>{[cur,...ds].forEach(e=>e.setAttribute("opacity",0));tip.style.opacity=0;wrap.querySelectorAll(".tl").forEach(t=>t.classList.remove("on"))};
  wrap.onpointerleave=off;
  wrap.onpointermove=e=>{
    const x=e.clientX-wrap.getBoundingClientRect().left;
    const i=n>1?Math.max(0,Math.min(n-1,Math.round((x-pl)/((w-pl-pr)/(n-1))))):0;
    cur.setAttribute("x1",X(i));cur.setAttribute("x2",X(i));cur.setAttribute("opacity",1);
    ds.forEach((d,k)=>{d.setAttribute("cx",X(i));d.setAttribute("cy",Y(CFG.series[k].values[i]));d.setAttribute("opacity",1)});
    tip.innerHTML=`<div style="opacity:.85">${CFG.tips[i]}</div>`+CFG.series.map((s,k)=>`<div class="r"><span><i style="background:${k?'var(--butter)':'var(--blue)'}"></i>${s.name}</span><b>${s.fmt[i]}</b></div>`).join("");
    tip.style.left=Math.max(0,Math.min(w-190,X(i)+14))+"px";tip.style.top="8px";tip.style.opacity=1;
    wrap.querySelectorAll(".tl").forEach(t=>t.classList.toggle("on",+t.dataset.i===i));
  };
  fit();
}
addEventListener("resize",draw);draw();
</script></body></html>
"""


def area_chart(title, labels, tips, series, ymin=0.0, ymax=1.0, caption=""):
    """Render the dashboard-style area/line chart. series = [{name, values, fmt, dash?}, ...]."""
    cfg = {"title": title, "labels": labels, "tips": tips, "series": series,
           "ymin": ymin, "ymax": ymax, "caption": caption}
    page_html = (CHART_TEMPLATE.replace("__FONTS__", font_css())
                 .replace("__CFG__", json.dumps(cfg).replace("</", "<\\/")))
    components.html(page_html, height=400, scrolling=False)


# ---------- cached system + data ----------
@st.cache_resource(show_spinner="Training A1 and A2 on the train split (A3-A5 run on top of them)...")
def load_system():
    train, val = T.load_data()
    system = T.build_system(train)
    ev = T.evaluate_a1(system, val) if val is not None else None
    return system, ev, len(train)


system, ev, n_train = load_system()

ss = st.session_state
ss.setdefault("history", [])   # every trace, newest first
ss.setdefault("chat", [])      # chat entries (user, text, trace), oldest first
# conversation waiting for the customer's answer
ss.setdefault("pending", None)
ss.setdefault("threshold", 0.8)

# sample-question chips: picked from validation.csv and checked against the agents by make_dashboard_data.py
EXAMPLES = ([e["text"] for e in STORE_DATA.get(ss.store, {}).get("examples", [])[:5]]
            or [e["text"] for e in _load_json("examples.json", [])[:4]] or [
    "How can I request a refund for my purchase?", "Where is my order?",
    "I want to cancel my order", "I forgot my password"])


# ---------- conversation flow (follow-up questions) ----------
# ss.pending holds a half-finished conversation: the original question, the details the
# customer has given so far, and how many times we already asked for more.
MAX_VAGUE_ASKS = 1   # "I'm not sure what you need" questions per conversation
MAX_ORDER_ASKS = 2   # 1st: order number, 2nd: email / phone / item + date

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)\+?\d[\d\s-]{8,13}\d(?!\d)")
ORDER_RE = re.compile(r"#\s?[A-Za-z0-9-]{4,}|\b[A-Za-z]{0,3}-?\d{5,9}\b")
# "I don't know / can't find it / no"
NOIDEA_RE = re.compile(
    r"^\s*(no|nope|nah|none|not sure|no idea|can'?t find|cannot find|"
    r"i (do not|don'?t|dont|can'?t|cant|cannot) (know|have|remember|find))\b", re.I)
# "... can't find my order number" inside the first question
LACKS_RE = re.compile(
    r"(can'?t|cant|cannot|couldn'?t|could not|don'?t|do not|didn'?t|did not|lost|forgot|"
    r"unable|missing|no)\b[^.?!]{0,40}\b(order\s*(number|id|no)|confirmation|receipt)", re.I)


def extract(text):
    """Pull an order number, email or phone out of free text."""
    found = {}
    m = EMAIL_RE.search(text)
    if m:
        found["email"] = m.group()
        text = text.replace(m.group(), " ")
    for m in PHONE_RE.finditer(text):
        if len(re.sub(r"\D", "", m.group())) >= 10:
            found["phone"] = m.group().strip()
            text = text.replace(m.group(), " ")
            break
    m = ORDER_RE.search(text)
    if m:
        found["order"] = m.group().strip()
    return found


def needs_order(intent):
    """Intents that cannot be handled without knowing which order we are talking about."""
    i = intent.lower()
    if any(k in i for k in ("policy", "fee", "place_order", "method")):
        return False
    return any(k in i for k in ("refund", "order", "invoice"))


def nice(intent):
    return str(intent).replace("_", " ")


def bot(text, tag=None, quick=None):
    ss.chat.append({"role": "assistant", "kind": "text",
                   "text": text, "tag": tag, "quick": quick})


def _localize(res, p):
    """Translate the agents' reply into the customer's language and record both translation steps in the trace."""
    local, info = LG.localize_response(res, ss.lang)
    LG.add_language_steps(
        res, ss.lang, p["orig"], p["en_last"], p["in_info"], local, info)
    return local


def finish(res, lead=None, note=None):
    ss.history.insert(0, res)
    ss.chat.append({"role": "assistant", "kind": "trace",
                   "trace": res, "lead": lead, "note": note})
    ss.pending = None


def advance(p):
    """Run all five agents on everything said so far, then answer, ask a follow-up, or escalate."""
    full = " ".join([p["query"]] + p["details"])
    have_ref = bool(extract(full)) or p["has_ref"]
    res = L2.run_level2(system, full, T=T,
                        threshold=ss.threshold, has_ref=have_ref)
    dec, reason = res["decision"], res["a5"]["reason"]
    # remembered so a change of topic can be spotted later
    p["intent"] = res["a1"]["intent"]

    if dec == L2.CLARIFY:
        kind = "order" if reason == "missing_info" else "vague"
        key, limit = ("order_asks", MAX_ORDER_ASKS) if kind == "order" else (
            "vague_asks", MAX_VAGUE_ASKS)
        if p[key] < limit:
            p[key] += 1
            p["kind"] = kind
            ss.pending = p
            local = _localize(res, p)
            # the clarify turn has a full trace too
            ss.history.insert(0, res)
            quick = (["I can't find it" if p[key] == 1 else "I don't have any of these"]
                     if kind == "order" else None)
            return bot(local, tag="Needs a few details", quick=quick)
        # asked as many times as allowed: hand over to a person (A5 override, recorded in the trace)
        L2.force_escalate(res, "no_order_reference" if kind ==
                          "order" else "still_unclear")
        _localize(res, p)
        return finish(res)

    lead = "Thanks, that helps. Here is what to do:" if (
        p["details"] and dec == L2.ANSWER) else None
    _localize(res, p)
    return finish(res, lead=lead)


def is_new_question(text, p):
    """While waiting for an answer, decide if the customer changed topic instead."""
    if p["kind"] != "order" or extract(text) or NOIDEA_RE.match(text) or len(text.split()) < 4:
        return False
    r = T.run_trace(system, text, threshold=ss.threshold)
    return r["decision"] == L2.ANSWER and r["a1"]["intent"] != p["intent"]


def handle_message(text, english=None):
    """text = what the customer typed (any supported language); english = a ready English version (chips, quick replies)."""
    text = (text or "").strip()
    if not text:
        return
    if english is None:
        # translate in: the five agents work in English
        en, in_info = LG.to_english(text, ss.lang)
    else:
        en, in_info = english, {"how": "preset", "ms": 0.0}
    # the customer sees their own words
    ss.chat.append({"role": "user", "kind": "text", "text": text})
    p = ss.pending
    if p and not is_new_question(en, p):
        p["details"].append(en)
        p["orig"], p["en_last"], p["in_info"] = text, en, in_info
        if p["kind"] == "order" and (extract(en) or
                                     (not NOIDEA_RE.match(en) and len(en.split()) >= 3)):
            p["has_ref"] = True   # they gave us something to look the order up with
        advance(p)
    else:
        ss.pending = None
        advance({"query": en, "details": [], "kind": None, "intent": None,
                 "vague_asks": 0, "order_asks": 0, "has_ref": False,
                 "orig": text, "en_last": en, "in_info": in_info})


def new_chat():
    ss.chat = []
    ss.pending = None


def esc(x):
    return html.escape(str(x))


def reply_text(r):
    """What the customer reads: A5's reply, in the customer's language when a translation step ran."""
    lg = r.get("language")
    return None, (lg["reply_local"] if lg else r["final_response"])


def render_trace(r, nested=False):
    """A1 -> A2 -> A3 -> A4 -> A5 cards + the raw step table. nested=True avoids expanders."""
    dec = r["decision"]
    steps = ["1 · Query", "2 · A1 Intent Analyst", "3 · A2 Response Specialist", "4 · A3 Router",
             "5 · A4 Auditor", "6 · A5 Coordinator", f"7 · {dec}"]
    lg = r.get("language")
    if lg and lg["selected"] != "en":
        sel = lg["selected"]
        steps = [f"0 · Translate {sel}→en"] + \
            steps + [f"8 · Translate en→{sel}"]
        st.markdown(
            f'<div class="card"><h4>Language layer · {esc(LG.LANGS[sel][1])}</h4>'
            f'<div><b>Customer wrote:</b> {esc(lg["original_query"])}</div>'
            f'<div style="margin-top:.4rem"><b>English for the agents:</b> {esc(lg["english_query"])}</div>'
            f'<span class="pill light">translate in: {esc(lg["translate_in"]["how"])}</span>'
            f'<span class="pill light">translate out: {esc(lg["translate_out"]["how"])}</span></div>',
            unsafe_allow_html=True)
    st.markdown('<div class="flow">' + '<span class="arrow">→</span>'.join(
        f'<span class="step on">{x}</span>' for x in steps) + '</div>', unsafe_allow_html=True)
    a1, ho, a2 = st.columns([1.1, 0.9, 1.4], gap="medium")
    cand = "".join(
        f'<div style="display:flex;justify-content:space-between"><span>{esc(c["intent"])}'
        f' <small>({esc(c["category"])})</small></span><b>{c["prob"]:.0%}</b></div>'
        f'<div class="bar"><div style="width:{max(c["prob"], 0.01) * 100:.0f}%"></div></div>'
        for c in r["a1"]["candidates"])
    a1.markdown(
        f'<div class="card blue"><h4>A1 · Intent Analyst</h4>'
        f'<div class="big">{esc(r["a1"]["intent"])}</div>'
        f'<span class="pill">category: {esc(r["a1"]["category"])}</span>'
        f'<span class="pill">confidence {r["a1"]["confidence"]:.0%}</span>'
        f'<div style="margin-top:1rem"><b>Top candidate intents</b></div>{cand}</div>',
        unsafe_allow_html=True)
    ho.markdown(
        f'<div class="card"><h4>Handoff · what A1 passes to A2</h4>'
        f'<pre style="background:{CHOCO};color:{BUTTER};border-radius:12px;padding:.7rem;'
        f'white-space:pre-wrap;font-size:.85rem">{esc(json.dumps(r["handoff"], indent=2, ensure_ascii=False))}</pre>'
        f'<span class="pill light">threshold {r["threshold"]:.2f}</span>'
        f'<span class="pill light">{r["latency_ms"]:.0f} ms total</span></div>',
        unsafe_allow_html=True)
    a2.markdown(
        f'<div class="card butter"><h4>A2 · Response Specialist</h4>'
        f'<div class="big">Draft response</div>'
        f'<span class="pill">similarity {r["a2"]["similarity"]:.0%}</span>'
        f'<div style="margin-top:.8rem"><b>Matched training instruction</b><br>'
        f'{esc(r["a2"]["matched_instruction"])}</div></div>', unsafe_allow_html=True)

    # ---- Level 2 agents
    a3c, a4c, a5c = st.columns([1, 1, 1], gap="medium")
    sig = r["a3"]["signals"]
    agree = "n/a" if sig["evidence_agreement"] is None else f'{sig["evidence_agreement"]:.0%}'
    a3c.markdown(
        f'<div class="card blue"><h4>A3 · Router</h4><div class="big">{esc(r["a3"]["route"])}</div>'
        f'<span class="pill">reason: {esc(r["a3"]["reason"].replace("_", " "))}</span>'
        f'<span class="pill">margin {sig["margin"]:.2f}</span>'
        f'<span class="pill">evidence agreement {agree}</span>'
        f'<div style="margin-top:.8rem"><b>Next steps</b><br>{esc(" → ".join(r["a3"]["next_steps"]))}</div></div>',
        unsafe_allow_html=True)
    a4 = r["a4"]
    first = a4.get("first_pass") or {}
    issues = first.get("issues") or []
    if a4["skipped"]:
        a4_body = "<div style='margin-top:.8rem'>Skipped: A3 routed away from a direct answer.</div>"
    else:
        a4_body = (f'<span class="pill">intent aligned: {"yes" if first.get("intent_aligned") else "no"}</span>'
                   f'<span class="pill">grounding {first.get("grounding", 0):.0%}</span>'
                   f'<div style="margin-top:.8rem"><b>First-pass issues</b><br>'
                   f'{esc("; ".join(issues)) if issues else "none"}</div>'
                   + (f'<div style="margin-top:.6rem"><b>Revision</b><br>{esc(a4["revision_note"])}</div>'
                      if a4["revision_count"] else ""))
    a4c.markdown(
        f'<div class="card"><h4>A4 · Response Auditor</h4>'
        f'<div class="big">{esc(str(a4["verdict"]).upper())}</div>{a4_body}</div>', unsafe_allow_html=True)
    a5c.markdown(
        f'<div class="card butter"><h4>A5 · Coordinator</h4><div class="big">{esc(dec)}</div>'
        f'<span class="pill">reason: {esc(r["a5"]["reason"].replace("_", " "))}</span>'
        f'<span class="pill">revisions {a4["revision_count"]}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">Agent trace (roles, outputs, decisions)</div>',
                unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"agent": s_["agent"], "role": s_["role"], "decision": s_["decision"],
                                "ms": s_["ms"]} for s_ in r["trace"]]),
                 hide_index=True, use_container_width=True)
    if nested:
        st.code(json.dumps(r["trace"], indent=2,
                ensure_ascii=False), language="json")
    else:
        with st.expander("Full trace JSON (inputs, outputs, evidence for every agent)"):
            st.code(json.dumps(r["trace"], indent=2,
                    ensure_ascii=False), language="json")
    st.markdown('<div class="sec">Supporting examples (A2 evidence)</div>',
                unsafe_allow_html=True)
    for i, e in enumerate(r["a2"]["evidence"], 1):
        if nested:
            st.markdown(f"{i}. *{esc(e['instruction'])}* · similarity {e['similarity']:.0%}",
                        unsafe_allow_html=True)
        else:
            with st.expander(f"Example {i} · similarity {e['similarity']:.0%} · {e['instruction'][:70]}"):
                st.markdown(f"**Customer said:** {e['instruction']}")
                st.markdown(f"**Reference response:** {e['response']}")


# chat_input is pinned to the bottom of the page whichever tab is open
prompt = st.chat_input(_t("Ask a question, e.g. How can I request a refund?"))
if prompt:
    handle_message(prompt)

# ---------- header ----------
st.markdown(f'<div class="gs-hero"><h1>{esc(_t("{store} support", store=STORE["name"]))}</h1>'
            f'<p>{esc(_t(STORE["tagline"]))}. '
            f'{esc(_t("Ask a question and get an answer. Open any reply to see how the five agents worked it out."))}</p></div>',
            unsafe_allow_html=True)

hc = st.columns([1, 1, 1.3, 1.6, 0.6], gap="small")
hc[0].button(_t("+ New chat"), on_click=new_chat,
             use_container_width=True, type="primary")
hc[1].download_button(_t("Export traces"), data=json.dumps(ss.history, indent=2, ensure_ascii=False),
                      file_name="grahak_seva_traces.json", mime="application/json",
                      disabled=not ss.history, use_container_width=True)
with hc[2].popover(_t("Escalation threshold"), use_container_width=True):
    ss.threshold = st.slider(
        _t("Confidence below this goes to a human"), 0.1, 0.9, ss.threshold, 0.05)

hc[3].markdown(f'<a class="gs-pill" href="{esc(STORE["help_url"])}" target="_blank" rel="noopener">'
               f'{esc(_t("{store} help centre ↗", store=STORE["name"]))}</a>', unsafe_allow_html=True)

tab_chat, tab_work, tab_dash, tab_hist = st.tabs(
    [_t("Chat"), _t("Agent workings"), _t("Insights"), _t("History")])

# ---------- CHAT ----------
with tab_chat:
    with st.chat_message("assistant", avatar="🛍️"):
        st.write(_t("Hi, I'm the {store} support assistant (powered by Grahak Seva). Ask me about orders, refunds, "
                    "shipping, payments or your account.", store=STORE["name"]))
    _warn = LG.language_notice(ss.lang)
    if _warn:
        st.warning(_warn)
    if not ss.chat:
        cols = st.columns(len(EXAMPLES), gap="small")
        for i, ex in enumerate(EXAMPLES):
            # chip shown in the customer's language
            label = LG.mt(ex, ss.lang)[0] if ss.lang != "en" else ex
            cols[i].button(label, key=f"ex{i}", on_click=handle_message, args=(label, ex),
                           use_container_width=True)
    for e in ss.chat:
        if e["role"] == "user":
            with st.chat_message("user"):
                st.write(e["text"])
        elif e["kind"] == "text":
            with st.chat_message("assistant", avatar="🛍️"):
                if e.get("tag"):
                    st.markdown(
                        f'<span class="pill">{esc(_t(e["tag"]))}</span>', unsafe_allow_html=True)
                st.markdown(e["text"])
        else:
            turn = e["trace"]
            with st.chat_message("assistant", avatar="🛍️"):
                note, text = reply_text(turn)
                note = e.get("note") or note
                if turn["decision"] == L2.ESCALATE:
                    st.markdown(f'<span class="pill">{esc(_t("Recommended for human review"))}</span>',
                                unsafe_allow_html=True)
                if note:
                    st.markdown(
                        f'<div class="esc">{note}</div>', unsafe_allow_html=True)
                elif e.get("lead"):
                    st.write(_t(e["lead"]))
                st.write(text)
                if turn["decision"] == L2.ESCALATE:
                    st.markdown(contact_card(STORE), unsafe_allow_html=True)
                with st.expander(f"{_t('How the agents handled this')} · {turn['a1']['intent']} · "
                                 f"{turn['a1']['confidence']:.0%} confident · {turn['decision']}"):
                    render_trace(turn, nested=True)
    # quick-reply buttons for the latest follow-up question
    if ss.chat and ss.chat[-1].get("quick"):
        qcols = st.columns(len(ss.chat[-1]["quick"]) + 2, gap="small")
        for i, label in enumerate(ss.chat[-1]["quick"]):
            qcols[i].button(_t(label), key=f"quick{len(ss.chat)}_{i}", on_click=handle_message,
                            args=(_t(label), label), use_container_width=True)

# ---------- AGENT WORKINGS ----------
with tab_work:
    if not ss.history:
        st.info("Ask something in the Chat tab to see A1 and A2 work.")
    else:
        r = ss.history[0]
        st.markdown(
            f"**Latest query:** {esc(r['query'])}", unsafe_allow_html=True)
        render_trace(r)

# ---------- INSIGHTS ----------
with tab_dash:
    h = ss.history
    n = len(h)
    auto = sum(1 for r in h if r["decision"] == L2.ANSWER)
    clar = sum(1 for r in h if r["decision"] == L2.CLARIFY)
    esc_n = sum(1 for r in h if r["decision"] == L2.ESCALATE)
    avg_lat = sum(r["latency_ms"] for r in h) / n if n else 0
    t1, t2, t3, t4 = st.columns(4, gap="medium")
    t1.markdown(f'<div class="card butter"><h4>Queries this session</h4><div class="big">{n}</div>'
                f'<span class="pill">live</span></div>', unsafe_allow_html=True)
    t2.markdown(f'<div class="card blue"><h4>Answered</h4><div class="big">'
                f'{(auto / n * 100 if n else 0):.0f}%</div><span class="pill">{auto} of {n}</span></div>',
                unsafe_allow_html=True)
    t3.markdown(f'<div class="card"><h4>Escalated to humans</h4><div class="big">{esc_n}</div>'
                f'<span class="pill light">{clar} clarifications asked</span></div>', unsafe_allow_html=True)
    mf = f"{ev['macro_f1']:.3f}" if ev else "n/a"
    t4.markdown(f'<div class="card"><h4>A1 Macro-F1 (held-out)</h4><div class="big">{mf}</div>'
                f'<span class="pill light">avg latency {avg_lat:.0f} ms</span></div>',
                unsafe_allow_html=True)
    st.write("")
    st.markdown('<div class="sec" id="gs-over-time">Your queries over time</div>',
                unsafe_allow_html=True)
    if not h:
        st.caption(
            "Ask a question in the Chat tab and the line graph will build up here.")
    else:
        # ss.history is newest first, so reverse it: query 1 on the left, newest on the right
        ordered = list(reversed(h))
        line_df = pd.DataFrame({
            "A1 confidence": [r["a1"]["confidence"] for r in ordered],
            "A2 similarity": [r["a2"]["similarity"] for r in ordered],
            "Escalation threshold": [r["threshold"] for r in ordered],
        }, index=pd.Index([f"Q{i}" for i in range(1, len(ordered) + 1)], name="Query"))
        st.line_chart(line_df, color=[CHOCO, "#7ba3be", "#e08a7a"], y_label="Score (0 to 1)",
                      x_label="Query number (oldest to newest)", height=300)
        st.caption(
            "Confidence below the red line is not answered directly: A3 asks a follow-up or escalates. Each new question adds a point.")
    st.write("")
    if not ev:
        st.warning(
            "validation.csv not found, so held-out metrics can't be shown.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Intent Macro-F1", f"{ev['macro_f1']:.3f}")
        m2.metric("Intent accuracy", f"{ev['intent_accuracy']:.1%}")
        m3.metric("Category accuracy",
                  f"{ev['category_accuracy']:.1%}" if ev["category_accuracy"] is not None else "n/a")
        m4.metric("Validation / train rows", f"{ev['n']:,} / {n_train:,}")
        st.markdown('<div class="sec" id="gs-threshold">Confidence threshold: auto-resolve vs accuracy</div>',
                    unsafe_allow_html=True)
        tt = pd.DataFrame(T.threshold_table(ev))
        tt["auto_resolved"] = (tt["auto_resolved"] *
                               100).round(1).astype(str) + "%"
        tt["accuracy_on_auto"] = tt["accuracy_on_auto"].apply(
            lambda v: "n/a" if v is None or pd.isna(v) else f"{v * 100:.1f}%")
        st.dataframe(tt, hide_index=True, use_container_width=True)
        st.markdown(
            '<div class="sec" id="gs-weak">Weakest intents (lowest F1)</div>', unsafe_allow_html=True)
        weak = pd.DataFrame(ev["per_intent"][:10], columns=["intent", "f1"])
        if len(weak):
            f1s = [float(v) for v in weak["f1"]]
            area_chart(
                "Weakest intents",
                labels=[str(i) for i in range(1, len(weak) + 1)],
                tips=[f"#{i} · {nice(x)}" for i,
                      x in enumerate(weak["intent"], 1)],
                series=[{"name": "Intent F1", "values": f1s, "fmt": [f"{v:.3f}" for v in f1s]},
                        {"name": "Macro-F1 (all intents)", "values": [float(ev["macro_f1"])] * len(f1s),
                         "fmt": [f"{ev['macro_f1']:.3f}"] * len(f1s), "dash": True}],
                ymin=0.0, ymax=1.0,
                caption="Rank 1 is the weakest intent. Hover the chart for intent names and scores.")

# ---------- HISTORY ----------
with tab_hist:
    flt = st.text_input("Search past queries or intents", key="flt",
                        placeholder="e.g. refund, cancel_order")
    rows = [{"query": x["query"], "intent": x["a1"]["intent"], "category": x["a1"]["category"],
             "confidence": round(x["a1"]["confidence"], 3),
             "similarity": round(x["a2"]["similarity"], 3), "decision": x["decision"],
             "latency_ms": round(x["latency_ms"])} for x in ss.history]
    if flt:
        f = flt.lower()
        rows = [x for x in rows if f in x["query"].lower() or f in x["intent"].lower()
                or f in x["category"].lower()]
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True,
                     use_container_width=True)
    else:
        st.caption("No queries yet." if not ss.history else "No matches.")
