"""The owner's playbook: the problems café owners in C-Scheme and Malviya Nagar run into most, and a fix for each.

Every block is labelled for what it is. Measured: a figure from the latest update, read from the published data, never typed in.
Estimate: rough maths on assumptions stated next to it, which the owner can change (the calculators run the same formulas in
playbook.js). Judgement: what I'd try, reasoned from the two. Nothing names or criticises a café."""
import math
from html import escape as E


def inr(n):
    """₹ in Indian grouping: 120000 -> 1,20,000."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = f"{head},{tail}"
    return ("-" if n < 0 else "") + s


# ---------- the three calculators: defaults and formulas (playbook.js mirrors these) ----------
EARLY = {"cost": 600, "bill": 250, "keep": 65}
DELIVERY = {"order": 400, "commission": 25, "discount": 40, "packaging": 25, "food": 30}
RENT = {"rent": 120000, "share": 15, "bill": 500, "days": 30}
GST_ON_COMMISSION = 18


def early_out(cost, bill, keep):
    per = bill * keep / 100
    n = math.ceil(cost / per) if per > 0 else 0
    return (f"You'd need about <b>{n} extra {'bill' if n == 1 else 'bills'} a day</b> in those hours to cover the cost. "
            f"Every bill after that is profit.")


def delivery_out(order, commission, discount, packaging, food):
    base = order - discount
    fee = base * commission / 100 * (1 + GST_ON_COMMISSION / 100)
    food_cost = order * food / 100
    left = base - fee - packaging - food_cost
    dine = order - food_cost
    pct = lambda x: round(100 * x / order) if order else 0
    return (f"A ₹{inr(order)} order leaves you <b>₹{inr(left)} ({pct(left)}%)</b> after commission, its GST, your discount, packaging "
            f"and ingredients. The same order eaten in leaves ₹{inr(dine)} ({pct(dine)}%), before rent and staff in both cases.")


def rent_out(rent, share, bill, days):
    month = rent / (share / 100) if share else 0
    day = month / days if days else 0
    bills = math.ceil(day / bill) if bill else 0
    return (f"To keep rent at {share:g}% of sales, the spot has to sell <b>₹{inr(month)} a month</b>: about ₹{inr(day)} a day, "
            f"or {bills} bills a day at ₹{inr(bill)}.")


def field(name, label, value, note="", step=1, mn=0, mx=10000000):
    hint = f'<small>{E(note)}</small>' if note else ""
    return (f'<label class="field"><span>{E(label)}</span><input type="number" name="{name}" value="{value}" min="{mn}" max="{mx}" '
            f'step="{step}" inputmode="decimal">{hint}</label>')


def calc(kind, title, fields, out):
    return (f'<form class="calc" data-calc="{kind}" onsubmit="return false"><p class="calc-h">{E(title)}</p>'
            f'<div class="calc-fields">{"".join(fields)}</div><p class="calc-out" aria-live="polite">{out}</p></form>')


# ---------- page parts ----------
TAGS = {"m": ("Measured", "tag-m"), "e": ("Estimate", "tag-e"), "j": ("Judgement", "tag-j")}


def block(kind, title, inner):
    label, cls = TAGS[kind]
    return f'<div class="pb-block reveal"><p class="pb-k"><span class="tag {cls}">{label}</span>{E(title)}</p>{inner}</div>'


def ul(items):
    """A list of facts; a table among them is set below the list rather than inside it."""
    rows = [x for x in items if x and not x.startswith("<table")]
    return "<ul>" + "".join(f"<li>{x}</li>" for x in rows) + "</ul>" + "".join(x for x in items if x and x.startswith("<table"))


def ol(items):
    return "<ol>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>"


def problem(n, pid, short, q, measured, why, estimate, tries, know):
    return f"""<article class="pb" id="{pid}" aria-labelledby="{pid}-h">
  <header class="pb-head reveal"><p class="pb-n">{n:02d} · {E(short)}</p><h2 id="{pid}-h">{E(q)}</h2></header>
  <div class="pb-body">
    {block("m", "What the data shows", ul(measured)) if measured else ""}
    {block("j", "Why it happens", f"<p>{why}</p>")}
    {block("e", estimate[0], estimate[1]) if estimate else ""}
    {block("j", "What I'd try", ol(tries))}
    <p class="pb-know reveal"><b>How you'll know it worked.</b> {know}</p>
  </div>
</article>"""


def page(I, F, L, k, core, pre):
    """The playbook's body. I, F: the insights and findings by id; L: the location data (or None)."""
    def fact(fid):
        f = F.get(fid)
        return f"<b>{f['value']}{E(f['unit'])}</b> {E(f['headline'])}" if f else ""

    # hours: share of cafés open by 8am, from the published opening curve
    curve = (I.get("hours") or {}).get("curve") or {}
    at8 = lambda a: dict(map(tuple, curve[a]["points"])).get(480) if a in curve else None
    o_all, o_cs, o_mn = at8("Both areas"), at8("C-Scheme"), at8("Malviya Nagar")
    areas = (L or {}).get("areas") or {}
    dm = lambda a, g: (areas.get(a) or {}).get("demand", {}).get(g)
    att = ((I.get("attention") or {}).get("by_area") or {})
    med = lambda a: (att.get(a) or {}).get("median_reviews")
    am = {i["key"]: i for i in (I.get("amenities") or {}).get("items") or []}
    shares = ((I.get("platforms") or {}).get("shares") or {})

    probs = []

    # 01 standing out
    probs.append(problem(1, "stand-out", "Standing out", "There are ten cafés within a five-minute walk. Why would anyone pick mine?",
        [fact("cluster"), fact("menus")],
        "When every café nearby offers a bit of everything, the menu stops being a reason to choose. People remember one thing per "
        "place: the cold coffee, the cheesecake, the quiet corner. Be the café for one thing before you try to be the café for everyone.",
        None,
        ["<b>Pick one signature,</b> something people can name. Put it first on the menu, on the board outside, and as the first photo on every app.",
         "<b>Trim the menu.</b> Look at last month's sales and cut the items that sell least. A shorter menu means a faster kitchen, fresher stock and less waste.",
         "<b>Ask ten regulars one question:</b> \"What do you come here for?\" If the answers scatter, the signature isn't landing yet."],
        "The share of bills that include your signature item, week by week. It should climb."))

    # 02 quiet hours
    meas = []
    if o_all is not None:
        meas.append(f"Only <b>{o_all}%</b> of cafés are open by 8am"
                    + (f" ({o_cs}% in C-Scheme, {o_mn}% in Malviya Nagar)." if o_cs is not None and o_mn is not None else "."))
    if dm("C-Scheme", "office") and dm("Malviya Nagar", "coaching"):
        meas.append(f"Around them: <b>{dm('C-Scheme', 'office')}</b> offices and banks in C-Scheme; <b>{dm('Malviya Nagar', 'coaching')}</b> "
                    f"coaching centres and <b>{dm('Malviya Nagar', 'gym')}</b> gyms and yoga studios in Malviya Nagar. Places found on "
                    f"Google Maps, not people: one big office counts once.")
    e = EARLY
    probs.append(problem(2, "quiet-hours", "Empty hours", "Mornings are empty and afternoons are slow.",
        meas,
        "Most cafés here open after their customers are already at work. Office staff, gym crowds and students want coffee before ten, "
        "and students are often free mid-afternoon. A quiet hour isn't a lost hour if it serves a different crowd.",
        ("Is opening two hours earlier worth it?", calc("early", "Put in your own numbers", [
            field("cost", "Extra cost per day (₹)", e["cost"], "My guess: one person's extra hours plus power."),
            field("bill", "Average bill (₹)", e["bill"], "A coffee and a bake."),
            field("keep", "Kept after ingredients (%)", e["keep"], "My guess for coffee and bakes.", mx=100)],
            early_out(**e))),
        ["<b>A grab-and-go morning menu:</b> coffee and one or two bakes, ready in under three minutes.",
         f"<b>Tell the neighbours directly.</b> A short visit or a WhatsApp note to the offices, gyms and coaching centres within five minutes. "
         f"Find yours on the <a href=\"{pre}location/\">Location check</a>.",
         "<b>For the 3 to 6pm slump,</b> a simple fixed-price combo for students or the after-gym crowd. Give any new hour four weeks before you judge it: habits take time."],
        "Bills before 10am, and between 3 and 6pm, counted every day for four weeks."))

    # 03 being found
    meas = [fact("attention")]
    if med("Both areas"):
        meas.append(f"The typical café here has <b>{med('Both areas')}</b> Google reviews"
                    + (f" ({med('C-Scheme')} in C-Scheme, {med('Malviya Nagar')} in Malviya Nagar)." if med("C-Scheme") and med("Malviya Nagar") else "."))
    meas.append(fact("ratings"))
    est = None
    if med("Both areas"):
        m = med("Both areas")
        est = ("How long to reach the typical count?",
               f"<p>Arithmetic, not a forecast: starting from zero, a café that gets two new reviews a week reaches the typical {m} in about "
               f"<b>{math.ceil(m / 2)} weeks</b>. At five a week, about <b>{math.ceil(m / 5)} weeks</b>. Count your own last month to see your pace.</p>")
    probs.append(problem(3, "found", "Being found", "New customers don't find us online, and we have too few reviews.",
        meas,
        "Attention piles onto the cafés that already have it, so the first fifty reviews are the hardest and count the most. "
        "Most happy customers simply never think to write one. They need asking.",
        est,
        ["<b>Complete your Google Business Profile:</b> exact hours (including any early opening), a menu photo, at least ten real photos, and the right category.",
         "<b>Ask in person at the happy moment,</b> when someone compliments the food, with a small QR card that opens your review page. "
         "Never pay or give discounts for reviews: Google's rules forbid it, and such reviews can be removed.",
         "<b>Reply to every review within two days,</b> briefly. Thank the good ones; answer the hard ones calmly, and take the details offline."],
        "New Google reviews per week."))

    # 04 delivery
    meas = [fact("delivery"), fact("visibility")]
    if shares.get("Zomato") is not None and shares.get("Swiggy") is not None:
        meas.append(f"<b>{shares['Zomato']}%</b> of cafés are on Zomato and <b>{shares['Swiggy']}%</b> on Swiggy.")
    d = DELIVERY
    probs.append(problem(4, "delivery", "Delivery margins", "Delivery brings orders. After the commission, what's left?",
        meas,
        "For most cafés here, delivery shapes the reputation more than the table does, so it can't be an afterthought. But it pays very "
        "differently from a table, so it has to be designed on purpose.",
        ("What a delivery order leaves you", calc("delivery", "Put in your own numbers", [
            field("order", "Order value (₹)", d["order"]),
            field("commission", "Commission (%)", d["commission"], "Often reported at about 15–30%. Yours is in your contract.", mx=100),
            field("discount", "Discount you fund (₹)", d["discount"]),
            field("packaging", "Packaging (₹)", d["packaging"]),
            field("food", "Ingredients (% of price)", d["food"], "My guess.", mx=100)],
            delivery_out(**d)) + f'<p class="calc-note">Includes {GST_ON_COMMISSION}% GST on the commission. Payment fees and ads, if you pay for them, come on top.</p>'),
        ["<b>A delivery menu of things that travel well.</b> Leave off what arrives soggy or flat, and pick items whose margin survives the commission.",
         "<b>Spend on packaging before discounts.</b> A dish that arrives right earns the next order; a discount only lowers what's left.",
         "<b>Put a small card in every bag</b> with a reason to visit in person, such as an item you only serve at the table."],
        "Money left per order, not the number of orders."))

    # 05 pricing
    cells = [c for c in (I.get("price") or {}).get("cells") or [] if c.get("median") and c.get("n", 0) >= k]
    rows = {}
    for c in cells:
        rows.setdefault(c["type"], {})[c["area"]] = c["median"]
    table = ""
    if rows:
        table = ('<table class="pb-table"><caption>Typical cost for two on Zomato</caption><thead><tr><th scope="col">Type</th>'
                 '<th scope="col">C-Scheme</th><th scope="col">Malviya Nagar</th></tr></thead><tbody>'
                 + "".join(f'<tr><th scope="row">{E(t)}</th>' + "".join(f"<td>{'₹' + inr(v[a]) if a in v else '–'}</td>" for a in ("C-Scheme", "Malviya Nagar")) + "</tr>"
                           for t, v in rows.items())
                 + f"</tbody></table><p class=\"calc-note\">– : fewer than {k} cafés listed, so withheld.</p>")
    beans, milk, extras, cup, menu = 18 * 1400 / 1000, 150 * 65 / 1000, 3, 10, 180
    table_cost, away_cost = beans + milk + extras, beans + milk + extras + cup
    est = ("What a cappuccino costs to make",
           ul([f"18 g of coffee at ₹1,400 a kilo: about ₹{inr(beans)}",
               f"150 ml of milk at ₹65 a litre: about ₹{inr(milk)}",
               f"Sugar, napkin and water: about ₹{extras}",
               f"A takeaway cup and lid: about ₹{cup} more"])
           + f"<p>About <b>₹{inr(table_cost)} at a table</b> and ₹{inr(away_cost)} to take away. At ₹{menu} on the menu, ingredients are about "
             f"{round(100 * table_cost / menu)}% of the price. These are my assumptions; your supplier prices will differ.</p>")
    probs.append(problem(5, "pricing", "Pricing", "Am I charging too much, or too little?",
        [fact("price")] + ([table] if table else []),
        "The cup is cheap. The rent, the staff and the seat are what cost money. So price for what your customer values: the place, the "
        "speed, the signature. A lower price won't buy a higher rating.",
        est,
        ["<b>Write down the cost of your top ten items</b> on one page, and update it when milk or beans change price.",
         "<b>Build a price ladder:</b> one item that's easy to say yes to, your signature in the middle, one premium choice above it. The premium makes the middle feel fair.",
         "<b>Raise prices a few items at a time,</b> alongside something people can see: a better cup, a bigger bake, a new item."],
        "Average bill and items per bill, month on month."))

    # 06 table time
    meas = [fact("amenities")]
    if am.get("wifi", {}).get("share") is not None and am.get("work_friendly", {}).get("share") is not None:
        meas.append(f"<b>{am['wifi']['share']}%</b> of cafés on Zomato list Wi-Fi and <b>{am['work_friendly']['share']}%</b> list themselves as work-friendly.")
    if dm("C-Scheme", "coworking") and dm("Malviya Nagar", "coworking"):
        meas.append(f"There are <b>{dm('C-Scheme', 'coworking')}</b> coworking spaces in C-Scheme and <b>{dm('Malviya Nagar', 'coworking')}</b> in Malviya Nagar: people who work away from an office are already here.")
    probs.append(problem(6, "tables", "Table time", "People sit for hours over one coffee.",
        meas,
        "Laptop guests aren't the problem. Laptop guests at the best tables in the busiest hour are. Off-peak, they fill seats that would sit empty.",
        ("What a seat earns in an hour",
         f"<p>One ₹180 coffee over three hours earns that seat <b>₹60 an hour</b>. The same seat at lunch, with one ₹250 bill an hour, earns "
         f"<b>₹250</b>. My example numbers; the point is the gap, and it only matters when the café is full.</p>"),
        ["<b>Choose a work zone:</b> tables near sockets, away from the window and the big tables. Welcome laptops there, all day.",
         "<b>Sell the time, not just the coffee:</b> a fixed-price work pass for slow hours, such as a drink, a refill and a snack for three hours.",
         "<b>At peak hours, a polite table card:</b> \"Laptop-free from 1 to 3, so everyone gets a seat.\""],
        "Sales per table per hour, for the work zone and for the rest of the room."))

    # 07 location and rent
    meas = []
    for a in ("C-Scheme", "Malviya Nagar"):
        c = (areas.get(a) or {}).get("cafes") or {}
        if c.get("n") and c.get("price"):
            meas.append(f"{a}: <b>{c['n']}</b> operating cafés; the typical one charges <b>₹{inr(c['price'])}</b> for two.")
    meas.append(f"For any single spot, the cafés within a five-minute walk and who is around: <a href=\"{pre}location/\">Location check</a>.")
    r = RENT
    probs.append(problem(7, "location", "Location and rent", "Is this the right spot, and what rent can it carry?",
        meas,
        "Rent is the one cost you can't cut once you've signed. A spot is only cheap if it brings enough people through the door to pay for it.",
        ("What rent does a spot need to earn?", calc("rent", "Put in your own numbers", [
            field("rent", "Monthly rent (₹)", r["rent"], step=1000),
            field("share", "Rent as a share of sales (%)", r["share"], "A common rule of thumb in food service: about 10–15%.", mx=100),
            field("bill", "Average bill (₹)", r["bill"]),
            field("days", "Days open a month", r["days"], mx=31)],
            rent_out(**r))),
        ["<b>Count footfall yourself:</b> half an hour at 8am, 1pm and 7pm, on a weekday and on a weekend day.",
         f"<b>Read the spot on the <a href=\"{pre}location/\">Location check</a>:</b> how many cafés within five minutes, what kind, and which offices, colleges and gyms are near.",
         "<b>Talk to three shopkeepers on the street</b> about its weekly rhythm: which days and hours are busy, and what changed in the last year."],
        "Before you sign: compare the bills a day you'd need (above) with the people you counted walking past. If you'd need a large share of them to walk in, keep looking."))

    jump = "".join(f'<a href="#{pid}">{E(s)}</a>' for pid, s in [("stand-out", "Standing out"), ("quiet-hours", "Empty hours"), ("found", "Being found"),
                                                                ("delivery", "Delivery margins"), ("pricing", "Pricing"), ("tables", "Table time"),
                                                                ("location", "Location and rent")])
    head = f"""<section class="page-head pb-top">
  <h1 class="reveal">The owner's playbook.</h1>
  <p class="page-lede reveal">The problems café owners in C-Scheme and Malviya Nagar run into most, and how I'd tackle each one. Some of it is measured,
  some is rough maths, and some is plain judgement. Each part says which it is, and every estimate shows its working, so you can put in your own numbers.</p>
  <div class="pb-legend reveal">
    <p><span class="tag tag-m">Measured</span>Counted in the latest update of {E(core)} cafés.</p>
    <p><span class="tag tag-e">Estimate</span>Rough maths on stated assumptions. Swap in yours.</p>
    <p><span class="tag tag-j">Judgement</span>What I'd try, reasoned from the above. Test it before you trust it.</p>
  </div>
  <nav class="jump reveal" aria-label="Problems on this page">{jump}</nav>
</section>"""
    return head + '\n<div class="pb-list">\n' + "\n".join(probs) + "\n</div>"
