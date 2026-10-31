"""Grahak Seva - the six demo stores shown in the sidebar.

Edit this file to change a store's look or its human-contact options.  Nothing here talks to the real
companies: every store runs the same A1-A5 agents, with its own slice of the Bitext data
(see make_store_data.py).  Colours are text-only brand tints, no company logos are used.

TO FILL IN (search each company's OFFICIAL help / contact page, not third-party "customer care number"
sites - those are full of scam numbers):
    phone, email, hours   -> leave as None to hide that row in the escalation card
    help_url              -> deep link to the store's own help centre
Set verified=True once you have checked a store's details against its official site.
Run `python stores.py` to list what is still missing.
"""

STORES = [
    dict(id="amazon", name="Amazon", initials="A", color="#232f3e", tint="#ffe2b3",
         tagline="Orders, returns, Prime and payments",
         # help page confirmed from Amazon India's own site (aboutamazon.in "How to contact Amazon Customer Service")
         help_url="https://www.amazon.in/gp/help/customer/display.html?nodeId=508510",
         in_app="Amazon app → Menu → Customer Service → Contact Us (you can choose a callback or chat)",
         phone=None, email=None, hours=None, verified=False,
         # share of each Bitext category this store gets in the demo slice (higher = more of that category)
         weights=dict(SUBSCRIPTION=3, INVOICE=2, ACCOUNT=1.5, PAYMENT=1.5)),
    dict(id="flipkart", name="Flipkart", initials="F", color="#2874f0", tint="#cfe0ff",
         tagline="Orders, delivery, refunds and replacements",
         help_url="https://www.flipkart.com/helpcentre",   # TODO verify on the site
         in_app="Flipkart app → Account → 24x7 Customer Support",   # TODO verify wording
         phone=None, email=None, hours=None, verified=False,
         weights=dict(ORDER=2, REFUND=2, DELIVERY=1.5)),
    dict(id="meesho", name="Meesho", initials="M", color="#9f2089", tint="#f6d3ef",
         tagline="Orders, returns and shipping",
         help_url="https://www.meesho.com",                # TODO: deep link to the help page
         in_app="Meesho app → Profile → Help & Support",   # TODO verify wording
         phone=None, email=None, hours=None, verified=False,
         weights=dict(ORDER=2, REFUND=2.5, SHIPPING=2, DELIVERY=1.5, CANCEL=1.5, SUBSCRIPTION=.3, INVOICE=.5)),
    dict(id="nykaa", name="Nykaa", initials="N", color="#e80071", tint="#ffd0e6",
         tagline="Beauty orders, returns and your account",
         help_url="https://www.nykaa.com",                 # TODO: deep link to the help page
         in_app="Nykaa app → Account → Help / Contact Us",  # TODO verify wording
         phone=None, email=None, hours=None, verified=False,
         weights=dict(ORDER=2, REFUND=2, SHIPPING=1.5, ACCOUNT=1.5, FEEDBACK=2, SUBSCRIPTION=.5)),
    dict(id="blinkit", name="Blinkit", initials="B", color="#0c831f", tint="#fbe869",
         tagline="Quick delivery, missing items and refunds",
         help_url="https://blinkit.com",                   # TODO: deep link to the help page
         in_app="Blinkit app → Profile → Help & Support",  # TODO verify wording
         phone=None, email=None, hours=None, verified=False,
         weights=dict(DELIVERY=3, ORDER=2.5, REFUND=2, PAYMENT=2, CANCEL=1.5, SUBSCRIPTION=.2, INVOICE=.4, SHIPPING=.3)),
    dict(id="zepto", name="Zepto", initials="Z", color="#5a189a", tint="#e7d2fb",
         tagline="10-minute delivery, payments and refunds",
         help_url="https://www.zeptonow.com",             # TODO: deep link to the help page
         in_app="Zepto app → Profile → Help & Support",    # TODO verify wording
         phone=None, email=None, hours=None, verified=False,
         weights=dict(DELIVERY=3, ORDER=2.5, PAYMENT=2.5, REFUND=1.5, CANCEL=2, SUBSCRIPTION=.2, INVOICE=.4, SHIPPING=.3)),
]

BY_ID = {s["id"]: s for s in STORES}
DEFAULT_STORE = "amazon"


if __name__ == "__main__":
    for s in STORES:
        missing = [k for k in ("phone", "email", "hours") if not s[k]]
        print(f"{s['name']:9} verified={s['verified']!s:5}  help_url={s['help_url']}\n"
              f"{'':9} still empty: {', '.join(missing) or 'nothing'}")
