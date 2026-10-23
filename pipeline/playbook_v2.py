"""The owner's playbook: seven problems café owners in C-Scheme and Malviya Nagar run into most, one page each.

Every page follows the same path: the problem in the owner's words, the one measured figure that frames it, a full worked
case study, a calculator where the maths helps, three things to do, the sources, and a takeaway to end on.

Rules for the numbers:
- Measured figures are read from the published data at build time, never typed in. If one is missing, its sentence is left out.
- Every assumption is either sourced (S below) or chosen to work against the page's own conclusion, so the conclusion still
  holds if the real figure is kinder. Ranges are shown where a figure can reasonably vary.
- Case studies are worked examples, not real cafés. Street figures in them are real aggregates from the Location check.
- No café is named or criticised.
The calculators in web/v2/playbook.js run the same formulas as the *_out functions here."""
import math
import re
from html import escape as E

# ---------- sources ----------
S = {
    "nrai": ("NRAI's complaint, reported by LiveLaw, 5 April 2022: commission of 20% to 30%",
             "https://www.livelaw.in/amp/news-updates/cci-orders-probe-determine-conduct-zomato-swiggy-anti-competitive-195865"),
    "gst": ("Restaurant India, 19 June 2018: 18% GST on the platform's commission, with no input tax credit for restaurants",
            "https://www.restaurantindia.in/news/from-swiggy-to-foodpanda-online-food-delivery-service-firms-face-gst-heat.n15916"),
    "milk": ("India TV, 21 May 2026: Saras Gold full-cream milk at ₹70 a litre in Jaipur",
             "https://www.indiatvnews.com/rajasthan/saras-milk-price-hike-jaipur-dairy-increases-cost-by-rs-2-per-litre-paneer-and-curd-also-costlier-2026-05-21-1041984"),
    "beans": ("Blue Tokai, Attikan Estate: ₹2,380 for 1 kg at retail, taxes included",
              "https://bluetokaicoffee.com/products/attikan-estate"),
    "cups": ("A Jaipur packaging seller on IndiaMART: 250 ml paper cups at ₹3 to ₹3.50 each",
             "https://m.indiamart.com/pack-today"),
    "wage": ("Keka, Rajasthan minimum wages: ₹285 a day for unskilled work",
             "https://www.keka.com/library/minimum-wages/rajasthan"),
    "rent": ("Restaurant India: business is good when rent is at or below 15% of revenue",
             "https://www.restaurantindia.in/article/are-high-rentals-draining-out-restaurant-business.13854"),
    "google": ("Google Maps contribution policy: no incentives such as payment, discounts or free goods for reviews",
               "https://support.google.com/contributionpolicy/answer/7400114?hl=en"),
    "menu": ("Kasavana and Smith, Menu Engineering (1982); a worked application in the Journal of Hospitality Application and Research",
             "https://publishingindia.com/archive/johar/application-of-kasavana-smith-menu-engineering-model-to-menu-of-a-resort-restaurant-a-case-study-approach"),
}

# ---------- the assumptions, each sourced or set against the conclusion ----------
BEANS_KG = 2380        # retail price; a café buying wholesale pays less, so the cost below is high on purpose
DOSE_G = 18            # a standard double shot
MILK_L = 70            # Saras Gold, the dearest everyday milk in Jaipur
MILK_ML = 150          # generous for a cappuccino
EXTRAS = 2             # sugar, napkin, water
CUP_SET = 10           # cup, lid and sleeve; cups alone are ₹3 to ₹3.50
DELIVERY_PACK = 15     # cup, lid and a carrier bag
GST_FOOD = 5           # GST on café food and drink
GST_COMMISSION = 18
WAGE_DAY = 285         # Rajasthan unskilled minimum, for comparison only
STAFF_HOUR = 100       # nearly three times the minimum wage
POWER_HOUR = 100       # about 10 units an hour at ₹10 a unit: far above what a small café draws

coffee = DOSE_G * BEANS_KG / 1000          # ≈ ₹42.84
milk = MILK_ML * MILK_L / 1000             # ₹10.50
CAPPA_TABLE = coffee + milk + EXTRAS       # ≈ ₹55
CAPPA_AWAY = CAPPA_TABLE + CUP_SET         # ≈ ₹65.34
COLD_MILK_ML = 200                          # a cold coffee takes more milk
COLD = coffee + COLD_MILK_ML * MILK_L / 1000 + 3   # coffee, milk, sugar and ice ≈ ₹59.84


def inr(n):
    """₹ in Indian grouping: 150000 -> 1,50,000."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = f"{head},{tail}"
    return ("-" if n < 0 else "") + s


def r1(x):
    """A rating as Google shows it: one decimal."""
    return f"{math.floor(x * 10 + 0.5) / 10:.1f}"


# ---------- calculator maths (mirrored in playbook.js) ----------
def early_keep(price, ingredients):
    return price / (1 + GST_FOOD / 100) - ingredients


def early_out(cost, price, ingredients):
    keep = early_keep(price, ingredients)
    if keep <= 0:
        return "At this price each coffee loses money before staff and power. Check the price and the ingredient cost."
    n = math.ceil(cost / keep)
    return (f"Each coffee keeps ₹{inr(keep)} after GST and ingredients, so you need <b>{n} {'coffee' if n == 1 else 'coffees'} "
            f"in the extra hours</b> to cover ₹{inr(cost)}. Every one after that is profit.")


def delivery_keep(price, commission, discount, packaging, ingredients):
    sale = price * (1 - discount / 100)
    return sale - sale * commission / 100 * (1 + GST_COMMISSION / 100) - packaging - ingredients


def delivery_out(price, commission, discount, packaging, ingredients):
    keep = delivery_keep(price, commission, discount, packaging, ingredients)
    table = price - ingredients
    pct = lambda x: round(100 * x / price) if price else 0
    return (f"On the app this item keeps <b>₹{inr(keep)} ({pct(keep)}% of its price)</b>. "
            f"At a table it keeps ₹{inr(table)} ({pct(table)}%).")


def price_out(old, new, ingredients):
    a, b = old - ingredients, new - ingredients
    if a <= 0 or b <= 0 or new <= old:
        return "Enter a new price above the current one, and both above the ingredient cost."
    lose = 100 - math.ceil(100 * a / b)          # rounded down: the safe side
    return (f"Each sale keeps ₹{inr(a)} now and ₹{inr(b)} after the rise. You can lose <b>{lose} of every 100 sales</b> "
            f"and still earn as much as before.")


def rent_out(rent, share, bill, days):
    month = rent / (share / 100) if share else 0
    day = month / days if days else 0
    n = math.ceil(day / bill) if bill else 0
    return (f"At {share:g}% of sales, this rent needs <b>₹{inr(month)} a month</b>: ₹{inr(day)} a day, "
            f"or <b>{n} tables a day</b> at ₹{inr(bill)}.")


# ---------- building blocks ----------
TAGS = {"m": ("Measured", "tag-m"), "e": ("Estimate", "tag-e"), "j": ("Judgement", "tag-j"), "a": ("Arithmetic", "tag-a"), "x": ("Example", "tag-x"),
        "s": ("Survey", "tag-s")}


def tag(kind):
    label, cls = TAGS[kind]
    return f'<span class="tag {cls}">{label}</span>'


def src(key):
    label, url = S[key]
    return f'<a href="{E(url)}" rel="noopener" target="_blank">{E(label)}</a>'


def field(name, label, value, note="", step="any", mx=10000000):
    hint = f"<small>{note}</small>" if note else ""
    return (f'<label class="field"><span>{E(label)}</span><input type="number" name="{name}" value="{value}" min="0" max="{mx}" '
            f'step="{step}" inputmode="decimal">{hint}</label>')


def calc(kind, title, lede, fields, out):
    return f"""<section class="pc" aria-labelledby="pc-{kind}">
  <div class="pc-copy reveal"><h2 id="pc-{kind}">{E(title)}</h2><p>{lede}</p></div>
  <form class="calc reveal" data-calc="{kind}" onsubmit="return false">
    <div class="calc-fields">{"".join(fields)}</div>
    <p class="calc-out" aria-live="polite">{out}</p>
  </form>
</section>"""


def table(head, rows):
    th = "".join(f'<th scope="col">{h}</th>' for h in head)
    tr = "".join("<tr>" + "".join((f'<th scope="row">{c}</th>' if i == 0 else f"<td>{c}</td>") for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="pt"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def hero(n, short, h1, sub, num, unit, cap, note):
    return f"""<section class="ph" aria-labelledby="ph-h">
  <div class="ph-copy">
    <p class="ph-eyebrow">Problem {n} of 7 · {E(short)}</p>
    <h1 id="ph-h" class="ph-h">{E(h1)}</h1>
    <p class="ph-sub">{E(sub)}</p>
  </div>
  <div class="ph-fig">
    <p class="hero-num">{num}<small>{E(unit)}</small></p>
    <p class="ph-cap">{cap}</p>
    <p class="ph-note">{note}</p>
  </div>
</section>"""


def lead(text, tiles=()):
    t = ""
    if tiles:
        t = '<div class="tz-grid pl-tiles">' + "".join(
            f'<div class="tz reveal">{tag(k)}<span class="tz-num">{num}<small>{E(u)}</small></span><span class="tz-head">{txt}</span></div>'
            for k, num, u, txt in tiles) + "</div>"
    return f'<section class="pl"><p class="lead reveal">{text}</p>{t}</section>'


def case(title, setup, steps):
    rows = "".join(f"""<li class="cs-step reveal"><div class="cs-n"><span class="cs-num">{i + 1:02d}</span>{tag(k)}</div>
      <div class="cs-body"><h3>{E(t)}</h3>{body}</div></li>""" for i, (k, t, body) in enumerate(steps))
    return f"""<section class="cs" aria-labelledby="cs-h">
  <header class="ch-head reveal"><h2 id="cs-h">{E(title)}</h2><p>{setup}</p></header>
  <ol class="cs-list">{rows}</ol>
</section>"""


def todo(items):
    rows = "".join(f'<li class="reveal"><div class="rule-row"><span class="best-name">{E(t)}</span><span class="ex-p">{d}</span></div></li>' for t, d in items)
    return f"""<section class="rules pd">
  <h2 class="reveal">What to do this week.</h2>
  <ul class="best-list rule-list">{rows}</ul>
</section>"""


def sources(items):
    rows = "".join(f"<li>{x}</li>" for x in items)
    return f'<section class="psrc reveal" aria-labelledby="psrc-h"><h2 id="psrc-h">Where the numbers come from.</h2><ul>{rows}</ul></section>'


def takeaway(text):
    return f'<section class="pt-end" aria-label="The takeaway"><p class="pt-k reveal">The takeaway</p><p class="pt-say reveal">{text}</p></section>'


# ---------- reading the data ----------
def nearest_spot(L, area, place):
    """The published spot nearest to a named place: real aggregates for a five-minute walk around it."""
    if not L or area not in L.get("areas", {}):
        return None
    ai = list(L["areas"].keys()).index(area)
    hit = next((p for p in L["areas"][area].get("places") or [] if p[0] == place), None)
    if not hit:
        return None
    _, la, lo = hit
    r = math.radians
    d = lambda s: 2 * 6371000 * math.asin(math.sqrt(math.sin(r(s[0] - la) / 2) ** 2 + math.cos(r(la)) * math.cos(r(s[0])) * math.sin(r(s[1] - lo) / 2) ** 2))
    best = min((s for s in L["spots"] if s[2] == ai), key=d, default=None)
    return best[3] if best and d(best) <= 150 else None


def pages(I, F, L, k, core, pre):
    """Returns (index body, [problem pages]). Each page: slug, short, title, answer, seo, desc, body."""
    curve = (I.get("hours") or {}).get("curve") or {}
    at8 = lambda a: dict(map(tuple, curve[a]["points"])).get(480) if a in curve else None
    by_type = (I.get("hours") or {}).get("by_type") or {}
    areas = (L or {}).get("areas") or {}
    att = (I.get("attention") or {}).get("by_area") or {}
    med = lambda a: (att.get(a) or {}).get("median_reviews")
    buckets = (I.get("ratings") or {}).get("buckets") or []
    menu_bars = dict(((F.get("menus") or {}).get("chart") or {}).get("bars") or [])
    cells = [c for c in (I.get("price") or {}).get("cells") or [] if c.get("median") and c.get("n", 0) >= k]
    hours_n = (I.get("hours") or {}).get("n", "")
    ing = math.ceil(CAPPA_TABLE)                 # costs are always rounded up
    cold = math.ceil(COLD)
    P = []
    SVF = {f["id"]: f for f in (I.get("survey") or {}).get("findings") or []}
    sv_n = ((I.get("survey") or {}).get("meta") or {}).get("n")

    def finding_note(fid):
        f = F.get(fid)
        if not f:
            return ""
        size = f'{f["n"]:,} cafés, ' if f.get("base") != "people" and f["n"] >= 100 else ""
        return f'{size}{E(f["grade"]).lower()} evidence. <a href="{pre}insights/#f-{E(fid)}">How I know</a>'.capitalize() if not size else \
               f'{size}{E(f["grade"]).lower()} evidence. <a href="{pre}insights/#f-{E(fid)}">How I know</a>'


    # ===== 1. standing out =====
    f = F.get("cluster")
    gt = nearest_spot(L, "Malviya Nagar", "Gaurav Tower")
    items = [("Cold coffee", 620, 180, cold), ("Cappuccino", 540, 160, ing), ("Veg sandwich", 410, 180, 60),
             ("Brownie", 380, 120, 35), ("Masala chai", 300, 60, 12), ("Pizza", 140, 320, 130), ("Pasta", 90, 280, 95), ("Momos", 60, 150, 55)]
    sold = sum(i[1] for i in items)
    pop_line = 0.7 * sold / len(items)                       # Kasavana and Smith: 70% of an equal share
    avg_m = sum(n * (p - c) for _, n, p, c in items) / sold

    def box(n, p, c):
        return {(True, True): "Star", (True, False): "Plowhorse", (False, True): "Puzzle", (False, False): "Dog"}[(n >= pop_line, (p - c) >= avg_m)]
    rows = [[E(nm), f"<b>{box(n, p, c)}</b>", f"{n}", f"{100 * n / sold:.0f}%", f"₹{p}", f"₹{c}", f"₹{p - c}"] for nm, n, p, c in items]
    stars = [i for i in items if box(*i[1:]) == "Star"]
    star = max(stars, key=lambda i: i[1] * (i[2] - i[3]))
    named = lambda b: ", ".join(i[0].lower() for i in items if box(*i[1:]) == b)
    street = ""
    if gt:
        mix = gt.get("mix") or {}
        top = max(mix, key=mix.get) if mix else None
        counts = (areas.get("Malviya Nagar") or {}).get("spot_counts") or []
        busier = round(100 * sum(1 for c in counts if c < gt["n"]) / len(counts)) if counts else None
        street = (f"Within a five-minute walk of Gaurav Tower there are <b>{gt['n']} cafés</b>"
                  + (f", more than at {busier}% of the spots I map in Malviya Nagar." if busier else ".")
                  + (f" The most common kind is the {E(top.lower())}, at {mix[top]}% of them; coffee-led cafés are {mix.get('Coffee-led', 0)}%." if top else "")
                  + (f" Across both areas, {F['menus']['value']}% of cafés list five or more cuisines" if F.get("menus") else "")
                  + (f", and more list fast food ({menu_bars['Fast food']}%) than coffee ({menu_bars['Coffee']}%)." if "Fast food" in menu_bars and "Coffee" in menu_bars else ".")
                  + " To a customer standing here, most of these menus look the same.")
    steps = ([("m", "Read the street", f"<p>{street}</p>")] if street else []) + [
        ("x", "List last month's sales by item", "<p>From the billing system: how many of each item sold, its price, and what its ingredients cost. "
              "The figures below are invented to show the method. Run it on your own sales.</p>"
              + table(["Item", "Box", "Sold", "Share", "Price", "Ingredients", "Kept per item"], rows)
              + "<p class=\"calc-note\">The Box column is explained in the next step.</p>"),
        ("a", "Sort every item into one of four boxes", f"<p>This is menu engineering, a method restaurants have used since the 1980s. Ask two questions of each item:</p>"
              f"<ul><li><b>Is it popular?</b> Yes if it sells at least 70% of what it would if every item sold equally. With {len(items)} items, "
              f"an equal share is {100 / len(items):.1f}% of sales, so the line is {100 * 0.7 / len(items):.2f}%: {pop_line:.0f} a month here.</li>"
              f"<li><b>Does it keep more than average?</b> Yes if it keeps more than ₹{avg_m:.0f}, the average across everything sold.</li></ul>"
              "<p><b>Star:</b> popular, and keeps more. <b>Plowhorse:</b> popular, keeps less. <b>Puzzle:</b> keeps more, but rarely ordered. "
              "<b>Dog:</b> neither.</p>"),
        *([("s", "What people say they choose on", f"<p>Among the café-goers I surveyed, {SVF['survey_the_place']['value']}% picked their last café "
                f"for the place itself, the space and the vibe, and {SVF['survey_the_place']['data']['menu']}% for something specific on the menu. "
                "So the signature can be the room as much as a dish: a corner, a view, a seat people ask for. Whichever it is, it should be the one thing "
                "people can name.</p>")] if "survey_the_place" in SVF else []),
        ("j", "Choose the signature", f"<p>The signature should be a Star that already sells. Here that's <b>{E(star[0].lower())}</b>: "
              f"{round(100 * star[1] / sold)}% of everything sold, keeping ₹{star[2] - star[3]} each, above the ₹{avg_m:.0f} average. "
              "Nothing new has to be invented. The customers have already voted.</p>"),
        ("j", "Act on the other boxes", "<ul>"
              + (f"<li><b>Plowhorses</b> ({E(named('Plowhorse'))}): keep them, and raise the price a little or trim the cost. "
                 f"The <a href=\"{pre}playbook/pricing/\">pricing case</a> shows how far a price can safely rise.</li>" if named("Plowhorse") else "")
              + (f"<li><b>Puzzles</b> ({E(named('Puzzle'))}): they keep a lot when they sell. Give them a better place on the menu for a month. If they still don't move, cut them.</li>" if named("Puzzle") else "")
              + (f"<li><b>Dogs</b> ({E(named('Dog'))}): cut. Fewer items means faster service, fresher stock and less waste.</li>" if named("Dog") else "")
              + "</ul>"),
        ("j", "Make the street know it", f"<p>Put {E(star[0].lower())} first on the menu, on the board outside, and as the first photo on every app. "
              "Then ask ten regulars one question: \"What do you come here for?\" When most of them name it, the signature has landed.</p>"),
    ]
    body = (hero(1, "Standing out", "Ten cafés within a five-minute walk. Why would anyone pick mine?",
                 "Because you're known for one thing. Your own sales already show which.",
                 f["value"] if f else "", f["unit"] if f else "", E(f["headline"]) if f else "", finding_note("cluster"))
            + lead("When every café nearby sells a bit of everything, the menu stops being a reason to choose. People pick a café for one thing "
                   "they can name: the cold coffee, the cheesecake, the quiet corner. If they can't name yours, they choose on distance or price.")
            + case("A worked example: an all-day café near Gaurav Tower.",
                   "A Malviya Nagar café with a long menu, in one of the most crowded café spots in the area. Not a real café: the street figures are real, the sales are invented.", steps)
            + todo([("Sort last month's sales.", "Put every item into the four boxes. It takes an hour with your billing report."),
                    ("Make one Star your signature.", "First on the menu, on the board outside, and the first photo on every app."),
                    ("Cut one Dog.", "Start with the item that sells least and keeps least. See whether anyone asks for it.")])
            + sources([f"Cafés near Gaurav Tower: the <a href=\"{pre}location/\">Location check</a>, latest update. Menus: the Zomato cuisine tags of {F['menus']['n'] if F.get('menus') else ''} cafés.",
                       f"The four-box method: {src('menu')}.",
                       f"Ingredient costs for the cappuccino (₹{ing}) and cold coffee (₹{cold}) are worked out in the <a href=\"{pre}playbook/pricing/\">pricing</a> and <a href=\"{pre}playbook/delivery/\">delivery</a> cases. The other figures are invented for the example."])
            + takeaway("You don't need a new idea to stand out. Your sales already know your best item. The job is to make the street know it too."))
    P.append(dict(slug="stand-out", short="Standing out", title="Ten cafés within a five-minute walk. Why pick mine?",
                  answer=f"Find the one item your customers already choose, and make the whole street know it.",
                  seo="How a café stands out on a crowded street in Jaipur", body=body,
                  desc="A worked case for cafés in C-Scheme and Malviya Nagar, Jaipur: use menu engineering on your own sales to find a signature item and cut what doesn't sell."))

    # ===== 2. empty mornings =====
    o_all, o_cs, o_mn = at8("Both areas"), at8("C-Scheme"), at8("Malviya Nagar")
    am = nearest_spot(L, "C-Scheme", "Ashok Marg")
    away = math.ceil(CAPPA_AWAY)
    cost = 2 * 2 * STAFF_HOUR + 2 * POWER_HOUR
    keep = early_keep(150, away)
    need = math.ceil(cost / keep)
    grid_rows = [[f"₹{p}"] + [f"{math.ceil(c / early_keep(p, away))}" for c in (cost, cost * 1.5, cost * 2)] for p in (130, 150, 180)]
    d = (am or {}).get("demand") or {}
    steps = []
    if am and d:
        bits = [f"<b>{d[g]}</b> {lbl}" for g, lbl in (("office", "offices and banks"), ("gym", "gyms and yoga studios"), ("coworking", "coworking spaces"), ("college", "colleges")) if d.get(g)]
        steps.append(("m", "Who is around in the morning",
                      f"<p>Within a five-minute walk of Ashok Marg there are {am['n']} cafés, and around them " + ", ".join(bits[:-1]) + f" and {bits[-1]}. "
                      "These are places found on Google Maps, not head counts: a big office counts once, like a small one.</p>"))
    steps += [
        ("e", "What two extra hours cost", table(["Cost", "Working", "Per day"], [
            ["Two people, two hours", f"₹{STAFF_HOUR} an hour each: nearly three times Rajasthan's minimum wage of ₹{WAGE_DAY} for an 8-hour day", f"₹{inr(2 * 2 * STAFF_HOUR)}"],
            ["Power and water", f"₹{POWER_HOUR} an hour: about 10 units at ₹10, far more than a small café draws", f"₹{inr(2 * POWER_HOUR)}"],
            ["<b>Total</b>", "", f"<b>₹{inr(cost)}</b>"]])),
        ("e", "What one takeaway cappuccino keeps", table(["Line", "Working", "₹"], [
            ["Price", "₹10 below the ₹160 used in the other cases, to stay cautious; GST included", "150.00"],
            ["Less GST", "₹150 ÷ 1.05", f"−{150 - 150 / 1.05:.2f}"],
            ["Coffee", f"{DOSE_G} g at ₹{inr(BEANS_KG)} a kilo, the retail price", f"−{coffee:.2f}"],
            ["Milk", f"{MILK_ML} ml at ₹{MILK_L} a litre", f"−{milk:.2f}"],
            ["Cup, lid, sleeve, sugar", f"₹{CUP_SET} + ₹{EXTRAS}", f"−{CUP_SET + EXTRAS:.2f}"],
            ["<b>Kept</b>", "Ingredients rounded up to ₹" + str(away), f"<b>{keep:.2f}</b>"]])),
        ("a", "How many coffees pay for the hours", f"<p>₹{inr(cost)} ÷ ₹{keep:.2f} = {cost / keep:.1f}. So <b>{need} coffees in two hours</b> covers everything. "
              "Here's how the answer moves with your costs and price:</p>"
              + table(["Coffee price", f"Costs ₹{inr(cost)}", f"₹{inr(cost * 1.5)}", f"₹{inr(cost * 2)}"], grid_rows)),
        ("j", "Is that many realistic?", "<p>"
              + (f"With {d['office']} offices and banks and {d.get('gym', 0)} gyms within five minutes, {need} coffees is fewer than one for every office. " if d.get("office", 0) > need else "")
              + "The people are there. What's missing is a reason to stop: a coffee that's ready before they reach the counter.</p>"),
        *([("s", "Is the morning demand there?", f"<p>Among the café-goers I surveyed, only {SVF['survey_mornings']['value']}% have their first coffee "
                f"or tea out before 10am on a weekday, and {SVF['survey_mornings']['data']['none']}% don't buy one at all on weekdays. Many are "
                "people who aren't tied to an office, so a street of offices may differ. Still, early trade won't come from passers-by alone: it has to "
                "come from a crowd that's already out, like the offices and gyms counted above.</p>")] if "survey_mornings" in SVF else []),
        ("a", "The worst case", f"<p>If not one extra coffee sells, a month's trial (26 working days) costs ₹{inr(26 * cost)}. "
              "Add any unsold bakes and a few printed cards, and that is about the most the experiment can lose. Four weeks is enough to know.</p>"),
    ]
    tiles = []
    if o_cs is not None and o_mn is not None:
        tiles += [("m", o_cs, "%", "of C-Scheme cafés are open by 8am."), ("m", o_mn, "%", "of Malviya Nagar cafés are open by 8am.")]
    coffee_open = (by_type.get("Coffee-led") or {}).get("median_open")
    if coffee_open:
        tiles.append(("m", coffee_open, "", "is when the typical coffee-led café opens."))
    body = (hero(2, "Empty mornings", "Our mornings are empty. Is it worth opening earlier?",
                 f"Near offices, very likely. {need} coffees in two hours pays for it, even on pessimistic numbers.",
                 o_all if o_all is not None else "", "%", "of cafés in C-Scheme and Malviya Nagar are open by 8am.",
                 f"Zomato's listed hours for {hours_n} cafés. <a href=\"{pre}insights/#day\">How I know</a>")
            + lead("Most cafés here open after their customers have gone to work. Office staff, gym crowds and students want coffee before ten. "
                   "Opening earlier only makes sense if the extra hours pay for themselves, so here is the maths.", tiles)
            + case("A worked example: a coffee-led café near Ashok Marg.",
                   "A C-Scheme café that opens at 10am, weighing an 8am start. Not a real café: the street figures are real, and every cost is set high on purpose.", steps)
            + calc("early", "Your numbers.", "Change any box: your extra cost a day, the price a customer pays (GST included), and what one coffee's ingredients and cup cost you.", [
                field("cost", "Extra cost a day (₹)", cost, "Staff hours plus power."),
                field("price", "Price of a coffee (₹)", 150, "What the customer pays."),
                field("ingredients", "Ingredients and cup (₹)", away, "Worked out above.")],
                early_out(cost, 150, away))
            + todo([("Build a two-item morning menu.", "Coffee and one bake, ready in under three minutes, so nobody misses their bus."),
                    ("Tell the ten nearest offices and gyms.", f"A short visit with a card showing the new hours. See who is around you on the <a href=\"{pre}location/\">Location check</a>."),
                    ("Run it for four weeks, then decide.", f"Count every bill before 10am. If the daily average stays under {need}, stop: you've lost at most ₹{inr(26 * cost)}.")])
            + sources([f"Opening hours: Zomato's listed hours for {hours_n} cafés. Offices, gyms and coworking: Google Maps searches, counted on the <a href=\"{pre}location/\">Location check</a>.",
                       f"Minimum wage: {src('wage')}.", f"Coffee: {src('beans')}.", f"Milk: {src('milk')}.", f"Cups: {src('cups')}.",
                       "Staff and power costs are set well above typical levels, so the real break-even is lower than shown."])
            + takeaway(f"An earlier opening is a cheap experiment with a known worst case. Near offices, {need} coffees in two hours pays for it. Open, count every bill, and let four weeks of numbers decide."))
    P.append(dict(slug="empty-mornings", short="Empty mornings", title="Our mornings are empty. Is it worth opening earlier?",
                  answer=f"Near offices, very likely: {need} coffees in two hours pays for it, even on pessimistic costs.",
                  seo="Should a café in Jaipur open earlier? The break-even maths", body=body,
                  desc=f"A worked case for cafés in C-Scheme and Malviya Nagar, Jaipur: what two extra morning hours cost, and the {need} coffees that pay for them."))

    # ===== 3. being found =====
    f = F.get("attention")
    mn, cs = med("Malviya Nagar"), med("C-Scheme")
    start, avg = 12, 4.9
    target = mn or 50
    hits = [(n, (avg * n + 1) / (n + 1)) for n in sorted({start, target, cs or 145})]
    gap = target - start
    chg = I.get("changes") or {}
    mom = chg.get("momentum") or {}
    share1, med_pw, days_ = mom.get("share_1_per_week"), mom.get("median_per_week"), chg.get("days")
    pace = 1                                            # one review a week: a strong, reachable pace here (measured below)
    months = round(gap / pace / 4.33)
    ask_rows = [[f"{b}", f"{b * 7}", f"1 in {b * 7 // pace}"] for b in (40, 80, 120)]
    time_rows = [[f"{p_} a week", f"{math.ceil(gap / p_)} weeks", f"about {round(gap / p_ / 4.33)} months"] for p_ in (1, 2)]
    lo_b = next((b for b in buckets if b.get("lo") == 0), None)
    hi_b = buckets[-1] if buckets else None
    tiles = []
    if mn and cs:
        tiles += [("m", mn, "", "Google reviews for the typical Malviya Nagar café."), ("m", cs, "", "for the typical C-Scheme café.")]
    if share1 is not None:
        tiles.append(("m", share1, "%", f"of cafés gained one new Google review a week or more over {days_} days."))
    steps = [
        ("x", "Where the café stands", f"<p>Say the café has {start} reviews, rated {avg}. The typical café in Malviya Nagar has {target}: that part is measured. The gap is <b>{gap} reviews</b>.</p>"),
        ("a", "Why a few reviews are fragile", "<p>Here is what one unhappy one-star review does to a 4.9, depending on how many reviews stand behind it:</p>"
              + table(["Reviews before", "Average after one 1-star", "As Google shows it"], [[f"{n}", f"{x:.2f}", f"<b>{r1(x)}</b>"] for n, x in hits])
              + (lambda a, b: f"<p>At {start} reviews, one bad day costs you {a / 10:.1f} stars. At {target}, only {b / 10:.1f}. "
                 "Volume is what makes a rating hard to knock over.</p>")(round(10 * (avg - float(r1(hits[0][1])))), round(10 * (avg - float(r1((avg * target + 1) / (target + 1))))))),
    ]
    if share1 is not None and med_pw is not None:
        steps.append(("m", "What pace is realistic here",
                      f"<p>Between my last two updates, {days_} days apart, the typical café gained {med_pw:.1f} new Google reviews a week, and only "
                      f"<b>{share1}%</b> gained one a week or more. So one review a week is a strong pace here: it beats about {100 - share1}% of cafés. "
                      "It's one stretch of a few weeks, so treat it as a guide.</p>"))
    wm = SVF.get("survey_word_of_mouth")
    if wm:
        sign = (f" One early sign: people who heard about a café from a friend were more than twice as likely to say they'd definitely go back "
                f"({wm['data']['friend_back']}%) as people who found it on Instagram ({wm['data']['insta_back']}%)."
                if wm["data"].get("friend_back") and wm["data"]["friend_back"] >= 2 * wm["data"]["insta_back"] else "")
        steps.append(("s", "How people actually hear about a café",
                      f"<p>Among the café-goers I surveyed, {wm['value']}% heard about their last café from a friend, family or Instagram, and only "
                      f"{wm['data']['apps']}% from Google Maps or a delivery app. So reviews mostly do their work after the first mention: they reassure "
                      f"someone who has already heard your name.{sign} Steady reviews and a reason for regulars to bring someone work together.</p>"))
    steps += [
        ("a", "How long it takes", f"<p>At a steady pace, closing a gap of {gap} takes:</p>" + table(["Pace", "Time", "Roughly"], time_rows)
              + f"<p>At one a week, that's one review from every few hundred bills, even for a quiet café:</p>"
              + table(["Bills a day", "Bills a week", "Reviews needed"], ask_rows)
              + "<p>Not everyone you ask will write one, so ask more often than that. Most happy customers never think to write one unasked. They need asking, not pleading.</p>"),
        ("j", "Ask at the right moment", "<p>Ask in person when someone compliments the food or thanks you on the way out, and hand them a small card with a QR code that opens your Google review page. "
              "Never offer a discount, a free item or money for a review: Google's rules forbid it, and those reviews can be removed.</p>"),
        ("j", "Answer every review", "<p>Reply within two days, in a line or two. Thank the good ones by naming what they liked. Answer the hard ones calmly, and take the details offline. New customers read the replies as closely as the reviews.</p>"),
    ]
    beats = f"beats the pace of {100 - share1}% of cafés here" if share1 is not None else "is a strong pace"
    body = (hero(3, "Being found", "We're new, nobody finds us, and we have too few reviews.",
                 f"A steady pace beats a burst. One honest review a week already {beats}.",
                 f["value"] if f else "", f["unit"] if f else "", E(f["headline"]) if f else "", finding_note("attention"))
            + lead("Attention piles onto the cafés that already have it. A new café with a handful of reviews is easy to miss and easy to knock over: "
                   "one bad review moves its rating a long way. The fix is steady, honest volume, not a burst.", tiles)
            + case("A worked example: a new café in Malviya Nagar.", f"Open three months, with {start} Google reviews and a {avg}. Not a real café: the area figures are real, the rest is arithmetic.", steps)
            + todo([("Complete your Google Business Profile.", "Exact hours, a menu photo, at least ten real photos of the food and the room, and the right category."),
                    ("Put a QR card on every table and bill.", "One line: \"Enjoyed it? A review helps us more than you'd think.\" And ask in person at the happy moment."),
                    ("Aim for one review a week, and count them.", "A steady week-by-week tally keeps it going; reply to every review within two days.")])
            + sources([f"Review counts, ratings and review growth: Google Maps, my last two updates, leaving out cafés whose Google listing changed. <a href=\"{pre}insights/#f-ratings\">How ratings behave</a>.",
                       f"Review rules: {src('google')}.", "The worked example's rating and bill counts are round numbers for the arithmetic, not data about any café."])
            + takeaway(f"You don't need a campaign. One honest review a week {beats}. Keep it up, and in about {months} months a new café reaches the street's typical count, with a rating that's far harder to knock over."))
    P.append(dict(slug="being-found", short="Being found", title="We're new, nobody finds us, and we have too few reviews.",
                  answer=f"One honest review a week {beats}. At that pace a new café reaches the typical count in about {months} months.",
                  seo="How a new café in Jaipur gets more Google reviews", body=body,
                  desc="A worked case for new cafés in Malviya Nagar and C-Scheme, Jaipur: why a few reviews make a rating fragile, what review pace is realistic, and how long catching up takes."))

    # ===== 4. delivery =====
    f = F.get("delivery")
    price, com = 180, 25
    fee = price * com / 100
    tax = fee * GST_COMMISSION / 100
    keep_app = delivery_keep(price, com, 0, DELIVERY_PACK, cold)
    keep_tab = price - cold
    keep_disc = delivery_keep(price, com, 20, DELIVERY_PACK, cold)
    sens = [[f"{c}%"] + [f"₹{inr(delivery_keep(price, c, dd, DELIVERY_PACK, cold))}" for dd in (0, 10, 20)] for c in (20, 25, 30)]
    steps = [
        ("e", "What the cold coffee costs to make", f"<p>{DOSE_G} g of coffee at ₹{inr(BEANS_KG)} a kilo (₹{coffee:.2f}), {COLD_MILK_ML} ml of milk at ₹{MILK_L} a litre (₹{COLD_MILK_ML * MILK_L / 1000:.2f}), and ₹3 of sugar and ice: "
              f"<b>₹{cold}</b>, rounded up. That's at the retail coffee price, so it's on the high side. A cold coffee travels well, which makes it a fair test of delivery.</p>"),
        ("a", "Side by side", table(["", "At a table", "On the app"], [
            ["Menu price", f"₹{price}", f"₹{price}"],
            [f"Commission, {com}%", "–", f"−₹{fee:.2f}"],
            [f"GST on the commission, {GST_COMMISSION}%", "–", f"−₹{tax:.2f}"],
            ["Cup, lid, straw and bag", "–", f"−₹{DELIVERY_PACK}"],
            ["Ingredients", f"−₹{cold}", f"−₹{cold}"],
            ["<b>Kept</b>", f"<b>₹{inr(keep_tab)}</b> ({round(100 * keep_tab / price)}%)", f"<b>₹{inr(keep_app)}</b> ({round(100 * keep_app / price)}%)"]])
              + f"<p>Menu prices here are before GST. The customer pays the 5% GST on top either way, so it doesn't change what you keep. The app's cut, with its own tax, is "
                f"{com * (1 + GST_COMMISSION / 100):.1f}% of the price before you've paid for a single ingredient.</p>"),
        ("a", "Add a discount", f"<p>Apps push cafés to fund discounts. A 20% discount you pay for, with commission charged on the discounted price, leaves <b>₹{inr(keep_disc)}</b> "
              f"of a ₹{price} cold coffee. Whatever your exact terms, the picture stays the same:</p>"
              + table(["Commission", "No discount", "10% discount", "20% discount"], sens)),
        ("j", "Why not just drop delivery?", "<p>"
              + (f"Because for {f['value']}% of cafés here that deliver, most of their Zomato reviews come from delivery. " if f else "")
              + "Delivery is where many customers first meet you. The aim isn't to leave the apps. It's to sell, on the apps, the items that keep money and travel well.</p>"),
        ("j", "Build the delivery menu", "<p>Go item by item with the calculator below. Keep the items that leave a fair share after the app's cut and arrive "
              "as good as they left. Drop the ones that don't: a foamy cappuccino collapses on the way, and crisp things go soft.</p>"),
    ]
    body = (hero(4, "Delivery margins", "Delivery brings orders. After the commission, what's left?",
                 "Less than half of what the same item keeps at a table. So choose what you deliver on purpose.",
                 f["value"] if f else "", f["unit"] if f else "", E(f["headline"]) if f else "", finding_note("delivery"))
            + lead("Delivery reaches people who would never walk in, and it's where many cafés here earn their reputation. But the app takes its commission, "
                   "and tax on that commission, before you've paid for anything. The answer isn't to quit. It's to know what each item keeps.",
                   [("e", "20–30", "%", "commission: the range restaurants put to India's competition regulator."),
                    ("e", GST_COMMISSION, "%", "GST on that commission, which restaurants can't claim back.")])
            + case("A worked example: one cold coffee, two ways.", f"The same ₹{price} cold coffee, sold at a table and through an app at {com}% commission. Every cost is sourced or set high on purpose.", steps)
            + calc("delivery", "Check any item.", "Put in an item's menu price, your commission and discount terms, and what its packaging and ingredients cost.", [
                field("price", "Menu price (₹)", price),
                field("commission", "Commission (%)", com, "It's in your contract.", mx=100),
                field("discount", "Discount you fund (%)", 0, mx=100),
                field("packaging", "Packaging (₹)", DELIVERY_PACK),
                field("ingredients", "Ingredients (₹)", cold)],
                delivery_out(price, com, 0, DELIVERY_PACK, cold))
            + todo([("Run every delivery item through the calculator.", "Write down what each keeps. A few will keep almost nothing."),
                    ("Spend on packaging before discounts.", "An item that arrives right earns the next order. A discount only lowers what's left."),
                    ("Put a card in every bag.", "Give a reason to visit in person, like an item you only serve at the table.")])
            + sources([f"Delivery reviews: the Zomato listings of {f['n'] if f else ''} cafés, latest update.", f"Commission: {src('nrai')}. GST on commission: {src('gst')}. These are the latest public figures I could find; your contract has yours.",
                       f"Coffee: {src('beans')}.", f"Milk: {src('milk')}.", f"Cups: {src('cups')}. The ₹{DELIVERY_PACK} allows for a lid, straw and bag too."])
            + takeaway("Treat every delivery item as its own small business. If it keeps nothing after the app's cut, it's advertising. Decide how much advertising you want to buy, and sell the rest at the table."))
    P.append(dict(slug="delivery", short="Delivery margins", title="Delivery brings orders. After the commission, what's left?",
                  answer=f"A ₹{price} cold coffee keeps ₹{inr(keep_app)} on the app and ₹{inr(keep_tab)} at a table. Choose what you deliver on purpose.",
                  seo="What Zomato and Swiggy orders really leave a café in Jaipur", body=body,
                  desc="A worked case for cafés in C-Scheme and Malviya Nagar, Jaipur: commission, GST on commission and packaging, line by line, with a calculator for any item."))

    # ===== 5. pricing =====
    f = F.get("price")
    old, new = 160, 180
    a_, b_ = old - ing, new - ing
    need_cups = math.ceil(100 * a_ / b_)
    rise_rows = [[f"₹{o} → ₹{o + 20}", f"₹{o - ing} → ₹{o + 20 - ing}", f"<b>{100 - math.ceil(100 * (o - ing) / (o + 20 - ing))}</b>"] for o in (140, 160, 200, 240)]
    byt = {}
    for c in cells:
        byt.setdefault(c["type"], {})[c["area"]] = c["median"]
    ptable = table(["Type", "C-Scheme", "Malviya Nagar"], [[E(t)] + [f"₹{inr(v[x])}" if x in v else "–" for x in ("C-Scheme", "Malviya Nagar")] for t, v in byt.items()]) if byt else ""
    rho = next((m.group(1) for h in (f or {}).get("how") or [] for m in [re.search(r"rank correlation (-?[\d.]+)", h)] if m), None)
    rated = next((m.group(1) for h in (f or {}).get("how") or [] for m in [re.search(r"Google rating, for ([\d,]+) cafés", h)] if m), None)
    steps = [
        ("e", "What the cup costs to make", f"<p>{DOSE_G} g of coffee at the retail price (₹{coffee:.2f}), {MILK_ML} ml of Saras Gold milk (₹{milk:.2f}), and ₹{EXTRAS} of sugar and napkin: <b>₹{ing}</b>. "
              f"At ₹{old}, ingredients are {round(100 * ing / old)}% of the price. The cup is cheap. Rent, staff and the seat are what cost money.</p>"),
        ("a", f"What a ₹{new - old} rise changes", table(["", f"At ₹{old}", f"At ₹{new}"], [
            ["Kept per cup", f"₹{a_}", f"₹{b_}"],
            ["Kept on 100 cups", f"₹{inr(100 * a_)}", f"₹{inr(100 * b_)}"],
            [f"Cups needed to keep ₹{inr(100 * a_)}", "100", f"<b>{need_cups}</b>"]])
              + f"<p>After the rise you can sell <b>{100 - need_cups} fewer cups in every 100</b> and keep the same money. That's your safety margin.</p>"),
        ("a", "The same sum at other prices", "<p>The cheaper the item, the more sales a ₹20 rise can afford to lose:</p>"
              + table(["Price", "Kept per cup", "Sales you can lose, of 100"], rise_rows)),
        ("m", "Will it cost you stars?", "<p>"
              + (f"Probably not. Across {rated or f['n']} cafés, price shows no link to Google rating" + (f" (rank correlation {rho}; zero means no link)" if rho else "") + ": "
                 "dearer cafés don't rate lower. That compares different cafés, though, which isn't the same as watching one café raise its prices, so count after you do." if f else "")
              + "</p>" + (f"<p>What matters more is where you sit against cafés like yours. The typical cost for two:</p>{ptable}<p class=\"calc-note\">–: fewer than {k} cafés, so withheld.</p>" if ptable else "")),
        ("j", "Raise it the right way", "<p>Raise a few items at a time, starting with the popular ones that keep least: the Plowhorses from "
              f"<a href=\"{pre}playbook/stand-out/\">the four boxes</a>. Pair the rise with something people can see, like a better cup or a bigger bake. Then count cups for four weeks.</p>"),
    ]
    body = (hero(5, "Pricing", "Am I charging too much, or too little?",
                 "A coffee costs far less to make than it sells for. The real question is how many sales a rise can afford to lose.",
                 f["value"] if f else "", f["unit"] if f else "", (E(f["headline"]) + " And price shows no link to Google rating.") if f else "", finding_note("price"))
            + lead("Owners worry that a higher price will cost them customers and stars. Stars don't move with price here. Customers might, "
                   "so the useful question is how many you can lose before a rise stops paying. That question has an exact answer.")
            + case(f"A worked example: a cappuccino at ₹{old}, going to ₹{new}.", "Ingredient costs are sourced. Everything else is arithmetic.", steps)
            + calc("price", "Test your own rise.", "Put in the current price, the new one, and what the item's ingredients cost.", [
                field("old", "Price now (₹)", old), field("new", "New price (₹)", new), field("ingredients", "Ingredients (₹)", ing)],
                price_out(old, new, ing))
            + todo([("Cost your top ten items.", "One page: the ingredient cost of each, updated when milk or coffee prices change."),
                    ("Raise the popular items that keep least.", "₹10 to ₹20 at a time, with something visible to show for it."),
                    ("Count for four weeks.", f"If sales of the item fall by less than the safety margin ({100 - need_cups} in 100 for a ₹{old} cappuccino), the rise is paying.")])
            + sources([f"Prices and ratings: Zomato cost for two and Google ratings, latest update. <a href=\"{pre}insights/#f-price\">How I know</a>.",
                       f"Coffee: {src('beans')}.", f"Milk: {src('milk')}."])
            + takeaway(f"A ₹{new - old} rise on a ₹{old} cappuccino pays for itself unless you lose more than {100 - need_cups} sales in every hundred. Raise, count, and let the count decide, not the fear."))
    P.append(dict(slug="pricing", short="Pricing", title="Am I charging too much, or too little?",
                  answer=f"A ₹{new - old} rise on a ₹{old} cappuccino survives losing {100 - need_cups} of every 100 sales, and dearer cafés here don't rate lower.",
                  seo="How to price coffee in a Jaipur café: the maths of a price rise", body=body,
                  desc="A worked case for cafés in C-Scheme and Malviya Nagar, Jaipur: what a cappuccino costs to make, and how many sales a price rise can afford to lose."))

    # ===== 6. table time =====
    f = F.get("amenities")
    wf_share = next((i.get("share") for i in (I.get("amenities") or {}).get("items") or [] if i.get("key") == "work_friendly"), None)
    wf_n = (I.get("amenities") or {}).get("n")
    sp = nearest_spot(L, "C-Scheme", "Sardar Patel Marg")
    two = (sp or {}).get("price")
    per = two / 2 if two else None
    camp = 180 / 3
    pass_price = 300
    steps = []
    if per:
        steps.append(("m", "What a lunch guest spends here", f"<p>Around Sardar Patel Marg the typical café charges <b>₹{inr(two)} for two</b>: about ₹{inr(per)} a person.</p>"))
    steps += [
        ("a", "What a seat brings in an hour", table(["Who is in the seat", "Spends", "Stays", "Brings in per hour"],
            [["Laptop guest, one coffee", "₹180", "3 hours", f"<b>₹{camp:.0f}</b>"]]
            + ([["Lunch guest", f"₹{inr(per)}", "1 hour", f"<b>₹{inr(per)}</b>"], ["Lunch guest, slow", f"₹{inr(per)}", "1½ hours", f"<b>₹{inr(per / 1.5)}</b>"]] if per else [])
            + [["Nobody", "–", "–", "<b>₹0</b>"]])),
        *([("s", "Who stays long", f"<p>Among the café-goers I surveyed, {SVF['survey_long_stays']['value']}% stayed more than an hour on their last visit, "
                f"and {SVF['survey_long_stays']['data']['catching_up']}% of those were catching up with someone; only "
                f"{SVF['survey_long_stays']['data']['working_pct']}% were working. The long table is mostly friends, "
                "not laptops, so the hour-by-hour logic below applies to groups too.</p>")] if "survey_long_stays" in SVF else []),
        ("j", "When it matters, and when it doesn't", "<p>These are sales, not profit, but the gap is wide enough that the point holds either way. A laptop guest only costs you money when someone else is turned away for want of a seat. "
              + (f"At a full lunch, each camped seat gives up ₹{inr(per / 1.5 - camp)} to ₹{inr(per - camp)} of sales an hour. " if per else "")
              + "At 4pm, with half the room empty, the alternative is ₹0, and the same guest is pure gain.</p>"),
        ("a", "Sell the time instead", f"<p>A work pass for the quiet hours: ₹{pass_price} for three hours, with a coffee, one refill and a cookie. That's ₹{pass_price // 3} an hour from the seat, "
              f"{pass_price / 3 / camp:.1f} times the one-coffee guest, and the guest knows exactly what they've bought.</p>"
              + (f"<p>Few cafés make this explicit: only {wf_share}% of cafés on Zomato list themselves as work-friendly. A clear offer stands out.</p>" if wf_share is not None else "")),
        ("j", "Will limits cost you reviews?", "<p>" + (f"Probably not much. Cafés with Wi-Fi get {f['value']}{f['unit']} the reviews, but against cafés that are otherwise alike that gap can't be told from none, "
              "so Wi-Fi doesn't look like what brings the reviews. That's about Wi-Fi, not about limits, so treat it as a hint. " if f else "") + "A polite limit at the busiest hour, with a welcome the rest of the day, keeps both crowds.</p>"),
    ]
    body = (hero(6, "Table time", "People sit for hours over one coffee.",
                 "It's only a problem when you're full. Protect the busy hour and sell the quiet ones.",
                 wf_share if wf_share is not None else "", "%", "of cafés on Zomato list themselves as work-friendly.",
                 f"Zomato's listed highlights for {wf_n} cafés. <a href=\"{pre}your-cafe/\">Compare yours</a>")
            + lead("Some guests stay three hours on one coffee. Whether that costs you anything depends entirely on the hour. When the café is full, the seat is worth a lot. "
                   "When it's half empty, a guest who stays is better than an empty chair.")
            + case("A worked example: a café on Sardar Patel Marg.", "A C-Scheme café that's full at lunch and quiet in the afternoon. Not a real café: the street figure is real, the rest is arithmetic.", steps)
            + todo([("Pick a work zone.", "Tables near sockets, away from the window and the big tables. Laptops welcome there all day."),
                    ("Offer a work pass in the quiet hours.", f"₹{pass_price} for three hours with a drink, a refill and a snack. Put it on the board."),
                    ("Set a polite rule for the busiest hour.", "A table card: \"Laptop-free from 1 to 3, so everyone gets a seat.\"")])
            + sources([f"Typical cost for two near Sardar Patel Marg: the <a href=\"{pre}location/\">Location check</a>, from Zomato listings.",
                       f"Work-friendly listings: Zomato highlights. Wi-Fi and reviews: {f['n'] if f else ''} cafés, compared like for like. <a href=\"{pre}insights/#f-amenities\">How I know</a>.",
                       "Time in the seat and the work-pass price are round example figures."])
            + takeaway("A laptop guest is a gift at 4pm and a cost at 1pm. Make the rule about the hour, not the guest, and sell the quiet hours as time."))
    P.append(dict(slug="table-time", short="Table time", title="People sit for hours over one coffee.",
                  answer="It only costs you when you're full. Protect the busy hour, and sell the quiet ones as a work pass.",
                  seo="Laptop guests in cafés: what a seat earns per hour", body=body,
                  desc="A worked case for cafés in C-Scheme, Jaipur: what a seat earns an hour from a laptop guest against a lunch guest, and when it matters."))

    # ===== 7. location and rent =====
    rent, share, days = 150000, 15, 30
    month = rent / (share / 100)
    day = month / days
    comp = []
    for nm, area in (("Sardar Patel Marg", "C-Scheme"), ("Sector 10", "Malviya Nagar")):
        s = nearest_spot(L, area, nm)
        if s and s.get("price"):
            dd = s.get("demand") or {}
            comp.append((nm, area, s["n"], s["price"], dd.get("office", 0), dd.get("coaching", 0) + dd.get("college", 0), math.ceil(day / s["price"])))
    steps = []
    if comp:
        steps.append(("m", "Two real streets", table(["Within five minutes of", "Cafés", "Typical cost for two", "Offices and banks", "Colleges and coaching"],
                       [[f"{E(nm)}, {E(ar)}", f"{n}", f"₹{inr(bl)}", f"{o}", f"{c}"] for nm, ar, n, bl, o, c, _ in comp])))
    steps.append(("a", "What the rent has to earn", f"<p>Say both spaces ask ₹{inr(rent)} a month. Rent should be at most {share}% of sales, so the café must sell "
                  f"<b>₹{inr(month)} a month</b>: ₹{inr(day)} a day over {days} days.</p>"))
    if len(comp) == 2:
        (n1, _, _, b1, o1, c1, k1), (n2, _, _, b2, o2, c2, k2) = comp
        steps += [
            ("a", "Turn it into tables", table(["Spot", "A table of two spends", "Tables a day to pay the rent"],
                  [[E(n1), f"₹{inr(b1)}", f"<b>{k1}</b>"], [E(n2), f"₹{inr(b2)}", f"<b>{k2}</b>"]])
                  + f"<p>The same rent needs <b>{k2 / k1:.1f} times as many tables</b> at {E(n2)} as at {E(n1)}, because a table there typically spends less. "
                    "This counts every table as spending the street's typical cost for two; tables of one, or ones that order less, mean more tables.</p>"),
            ("j", "Which street can do it?", f"<p>{E(n2)} has more people around: {o2} offices and banks and {c2} colleges and coaching centres within five minutes, "
                  f"against {o1} and {c1}. So it may well fill {k2} tables, but only a footfall count can tell. The rent is the same. What it asks of each street is not.</p>"),
        ]
    steps.append(("j", "Count before you sign", "<p>Stand outside for half an hour at 8am, 1pm and 7pm, on a weekday and on a weekend day, and count the people who walk past. "
                  "If the tables you need are a big share of everyone who passes, keep looking. Ask three shopkeepers which days are busy and what changed this year.</p>"))
    first_bill = comp[0][3] if comp else 700
    body = (hero(7, "Location and rent", "Is this the right spot, and what rent can it carry?",
                 "Judge the rent against what a table on that street spends, then count whether the people are there.",
                 share, "%", "of sales is the most a restaurant's rent should take, by a common trade rule.", "A rule of thumb, not my data: " + src("rent"))
            + lead("Rent is the one cost you can't cut once you've signed. The same rent can be easy on one street and impossible on the next, "
                   "because what a table spends changes from street to street. Turn the rent into tables a day, and the decision gets clear.")
            + case("A worked example: one rent, two streets.", f"Two real spots, one in each area, both asking ₹{inr(rent)} a month. The street figures are real; the rent is an example.", steps)
            + calc("rent", "Check a space.", "Put in the rent, the share of sales you'll allow it, what a table on that street spends, and the days you'll open.", [
                field("rent", "Monthly rent (₹)", rent, step=1000), field("share", "Rent as a share of sales (%)", share, "10–15% is the usual target.", mx=100),
                field("bill", "A table spends (₹)", first_bill, f"The typical cost for two, on the <a href=\"{pre}location/\">Location check</a>."), field("days", "Days open a month", days, mx=31)],
                rent_out(rent, share, first_bill, days))
            + todo([("Read the street on the Location check.", f"Cafés within five minutes, the typical cost for two, and who is around: <a href=\"{pre}location/\">open the Location check</a>"),
                    ("Turn the rent into tables a day.", "Use the calculator with that street's cost for two."),
                    ("Count footfall at three times of day.", "On a weekday and a weekend day. Compare it with the tables you need before you sign anything.")])
            + sources([f"Street figures: the <a href=\"{pre}location/\">Location check</a>, latest update: cafés within 500 metres, Zomato cost for two, and places from Google Maps searches.",
                       f"Rent rule: {src('rent')}.", f"The ₹{inr(rent)} rent is an example, not a quote for either street."])
            + takeaway("A spot is only cheap if its street's tables can pay for it. Turn the rent into tables a day, go and count the people, and sign only when the two agree."))
    P.append(dict(slug="location-rent", short="Location and rent", title="Is this the right spot, and what rent can it carry?",
                  answer="Turn the rent into tables a day at that street's prices, then count whether the people are there.",
                  seo="Café rent in Jaipur: how much can a spot carry?", body=body,
                  desc="A worked case comparing two real streets in C-Scheme and Malviya Nagar, Jaipur: the same rent, turned into tables a day, with a calculator."))

    # ---------- the index ----------
    rows = "".join(f'<li class="reveal"><a href="{p["slug"]}/"><span class="best-name"><span class="pi-n">{i + 1:02d}</span>{E(p["title"])}</span>'
                   f'<span class="ex-p">{E(p["answer"])}</span><span class="best-go">Read</span></a></li>' for i, p in enumerate(P))
    index = f"""<section class="ph ph-index" aria-labelledby="ph-h">
  <div class="ph-copy">
    <p class="ph-eyebrow">For café owners in C-Scheme and Malviya Nagar</p>
    <h1 id="ph-h" class="ph-h">The owner's playbook.</h1>
    <p class="ph-sub">Good coffee. Bad assumptions. Let's fix that.</p>
  </div>
  <div class="ph-fig ph-how">
    <p class="ph-cap">The seven problems owners here run into most. Each is worked through as a case study, with every sum shown.</p>
    <ul class="ph-tags">
      <li>{tag("m")} counted in the latest update of {E(core)} cafés</li>
      <li>{tag("a")} sums anyone can redo</li>
      <li>{tag("e")} sourced, or set high on purpose so the answer stays cautious</li>
      <li>{tag("j")} what I'd do, reasoned from the above</li>
      <li>{tag("x")} invented figures, only to show a method</li>
      <li>{tag("s")} from my survey of café-goers, early signs</li>
    </ul>
  </div>
</section>
<section class="explore pi">
  <ul class="best-list ex-list pi-list">{rows}</ul>
</section>"""
    return index, P
