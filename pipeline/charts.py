"""Inline-SVG charts. Each leads with its headline number, highlights the story and greys the rest.

Colour rules (dataviz method): two-area charts use the validated blue/orange pair with a legend;
single-series charts use one accent (a same-hue gradient, not an encoding) with emphasis on the
bar the copy talks about and neutral grey for the rest. Text always wears ink, never series colour.
"""
import html
import json

E = html.escape
W = 720                                   # drawing width; ~1:1 with the page at desktop, readable on phones
AREA_CLASS = {"C-Scheme": "s1", "Malviya Nagar": "s2"}
TYPES = ["Coffee-led", "Tea & chai", "Bakery", "All-day café"]
_uid = [0]


def uid(p):
    _uid[0] += 1
    return f"{p}{_uid[0]}"


def head(big, text):
    return f'<div class="chart-head"><span class="ch-big">{big}</span><span class="ch-text">{E(text)}</span></div>'


def svg(h, label, cls, defs=""):
    return (f'<svg class="viz {cls}" viewBox="0 0 {W} {h}" role="img" aria-label="{E(label)}" preserveAspectRatio="xMidYMid meet">'
            f'<defs>{defs}</defs>')


def accent_grad(gid, vertical=True):
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" class="ga"/><stop offset="1" class="gb"/></linearGradient>')


def legend(areas):
    return '<div class="legend">' + "".join(f'<span class="key"><i class="sw {AREA_CLASS[a]}"></i>{E(a)}</span>' for a in areas) + "</div>"


def table(head_, rows, caption):
    th = "".join(f"<th scope='col'>{E(h)}</th>" for h in head_)
    trs = "".join("<tr>" + "".join(f"<td>{E(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<details class="table-view"><summary>View as table</summary>'
            f'<table><caption>{E(caption)}</caption><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></details>')


def monotone(pts):
    """Smooth path through points without overshoot (Fritsch–Carlson monotone cubic)."""
    n = len(pts)
    if n < 3:
        return " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    dx = [pts[i + 1][0] - pts[i][0] for i in range(n - 1)]
    s = [(pts[i + 1][1] - pts[i][1]) / dx[i] for i in range(n - 1)]
    m = [s[0]] + [0 if s[i - 1] * s[i] <= 0 else (s[i - 1] + s[i]) / 2 for i in range(1, n - 1)] + [s[-1]]
    for i in range(n - 1):
        if s[i] == 0:
            m[i] = m[i + 1] = 0
        else:
            a, b = m[i] / s[i], m[i + 1] / s[i]
            h = a * a + b * b
            if h > 9:
                t = 3 / h ** 0.5
                m[i], m[i + 1] = t * a * s[i], t * b * s[i]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(n - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        c = dx[i] / 3
        d += f" C{x0 + c:.1f},{y0 + m[i] * c:.1f} {x1 - c:.1f},{y1 - m[i + 1] * c:.1f} {x1:.1f},{y1:.1f}"
    return d


def capsule_up(x, y, w, base, cls, tip, fill=None):
    """Column with a rounded data-end and a square foot on the baseline."""
    h = max(base - y, 0.5)
    r = min(12, w / 2, h)
    d = (f"M{x:.1f},{base:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} L{x + w - r:.1f},{y:.1f} "
         f"Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} L{x + w:.1f},{base:.1f} Z")
    f = f' fill="url(#{fill})"' if fill else ""
    return f'<path class="bar {cls}" d="{d}"{f} data-tip="{E(tip)}" tabindex="0"/>'


def fmt_clock(m):
    h, mi = divmod(m % 1440, 60)
    if h == 0 and mi == 0:
        return "midnight"
    if h == 12 and mi == 0:
        return "noon"
    return f"{12 if h % 12 == 0 else h % 12}{':' + str(mi).zfill(2) if mi else ''}{'am' if h < 12 else 'pm'}"


# ---------------- opening hours ----------------
def hours(ins, areas):
    h = ins["insights"]["hours"]
    H, L, R, T, B = 330, 40, 16, 24, 34
    x0, x1 = 360, 1560
    sx = lambda m: L + (m - x0) / (x1 - x0) * (W - L - R)
    sy = lambda p: T + (1 - p / 100) * (H - T - B)
    defs = ""
    gids = {}
    for a in areas:
        g = uid("wash"); gids[a] = g
        defs += (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="w0 {AREA_CLASS[a]}"/>'
                 f'<stop offset="1" class="w1 {AREA_CLASS[a]}"/></linearGradient>')
    band = uid("band")
    defs += f'<linearGradient id="{band}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" class="b0"/><stop offset="1" class="b1"/></linearGradient>'
    o = [svg(H, "Share of cafés open at each time of day, by area", "line", defs)]
    o.append(f'<rect x="{sx(360):.1f}" y="{T}" width="{sx(540) - sx(360):.1f}" height="{H - T - B}" rx="10" fill="url(#{band})"/>')
    for p in (0, 50, 100):
        o.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{sy(p):.1f}" y2="{sy(p):.1f}"/>')
        o.append(f'<text class="tick" x="{L - 8}" y="{sy(p) + 4:.1f}" text-anchor="end">{p}%</text>')
    for m in range(360, 1561, 180):
        o.append(f'<text class="tick" x="{sx(m):.1f}" y="{H - 10}" text-anchor="middle">{fmt_clock(m)}</text>')
    series, rows = [], {}
    for a in areas:
        c = h["curve"].get(a)
        if not c:
            continue
        pts = [(sx(m), sy(p)) for m, p in c["points"]]
        line = monotone(pts)
        o.append(f'<path d="{line} L{pts[-1][0]:.1f},{sy(0):.1f} L{pts[0][0]:.1f},{sy(0):.1f} Z" fill="url(#{gids[a]})"/>')
        o.append(f'<path class="ln {AREA_CLASS[a]}" d="{line}"/>')
        series.append({"name": a, "cls": AREA_CLASS[a], "values": [p for _, p in c["points"]]})
        for m, p in c["points"]:
            rows.setdefault(m, {})[a] = p
    # the 8am marker the copy talks about: a short stem up to the dots, label in the free space above
    if 480 in rows:
        x = sx(480)
        vals = [(a, rows[480][a]) for a in areas if rows[480].get(a) is not None]
        top_v = max(v for _, v in vals)
        o.append(f'<line class="marker" x1="{x:.1f}" x2="{x:.1f}" y1="{sy(top_v) - 14:.1f}" y2="{H - B}"/>')
        for a, v in vals:
            o.append(f'<circle class="dot {AREA_CLASS[a]}" cx="{x:.1f}" cy="{sy(v):.1f}" r="6"/>')
        lx, ly = L + 10, sy(86)
        o.append(f'<text class="mk-label" x="{lx:.1f}" y="{ly:.1f}">Open at 8am</text>')
        for j, (a, v) in enumerate(vals):
            yy = ly + 24 + j * 20
            o.append(f'<circle class="key-dot {AREA_CLASS[a]}" cx="{lx + 4:.1f}" cy="{yy - 4:.1f}" r="4"/>')
            o.append(f'<text class="mk-sub" x="{lx + 14:.1f}" y="{yy:.1f}">{v}% {E(a)}</text>')
    xs = sorted(rows)
    o.append(f'<line class="cross" x1="0" x2="0" y1="{T}" y2="{H - B}"/>')
    o.append(f'<rect class="hit" x="{L}" y="{T}" width="{W - L - R}" height="{H - T - B}" fill="transparent" '
             f'data-line=\'{E(json.dumps({"x": [sx(m) for m in xs], "labels": [fmt_clock(m) for m in xs], "series": series}))}\' '
             f'tabindex="0" aria-label="Explore values by time of day"/>')
    o.append("</svg>")
    big = f'{h.get("open_by_8", "—")}%'
    return (head(big, "of cafés are serving by 8am") + legend(areas) + "".join(o)
            + table(["Time"] + areas, [[fmt_clock(m)] + [f"{rows[m].get(a, '—')}%" for a in areas] for m in xs],
                    "Share of cafés open, by time of day"))


# ---------------- prices ----------------
def prices(ins, areas, k):
    cells = {(c["type"], c["area"]): c for c in ins["insights"]["price"]["cells"]}
    rowh, L, R, T = 78, 128, 64, 8
    H = T + rowh * len(TYPES) + 30
    vmax = 1500
    sx = lambda v: L + v / vmax * (W - L - R)
    o = [svg(H, "Cost for two by café type and area: median and middle half", "dots")]
    for v in range(0, vmax + 1, 500):
        o.append(f'<line class="grid" x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{T}" y2="{H - 26}"/>')
        o.append(f'<text class="tick" x="{sx(v):.1f}" y="{H - 8}" text-anchor="middle">₹{v:,}</text>')
    rows = []
    for i, t in enumerate(TYPES):
        yc = T + i * rowh + rowh / 2
        o.append(f'<text class="cat" x="0" y="{yc + 5:.1f}">{E(t)}</text>')
        for j, a in enumerate(areas):
            y = yc + (-13 if j == 0 else 13)
            c = cells.get((t, a), {})
            if c.get("median") is None:
                o.append(f'<text class="muted-note" x="{sx(0) + 4:.1f}" y="{y + 4:.1f}">{E(a)}: fewer than {k} listings</text>')
                rows.append([t, a, f"fewer than {k}", "", ""])
                continue
            tip = f"{t} · {a}: median ₹{c['median']:,.0f}, middle half ₹{c['p25']:,.0f}–₹{c['p75']:,.0f} ({c['n']} cafés)"
            x1, x2 = sx(c["p25"]), sx(c["p75"])
            o.append(f'<rect class="rng {AREA_CLASS[a]}" x="{x1:.1f}" y="{y - 6:.1f}" width="{max(x2 - x1, 12):.1f}" height="12" rx="6"/>')
            o.append(f'<circle class="dot {AREA_CLASS[a]}" cx="{sx(c["median"]):.1f}" cy="{y:.1f}" r="8" data-tip="{E(tip)}" tabindex="0"/>')
            o.append(f'<text class="val" x="{max(x2, sx(c["median"]) + 8) + 10:.1f}" y="{y + 5:.1f}">₹{c["median"]:,.0f}</text>')
            rows.append([t, a, f"₹{c['median']:,.0f}", f"₹{c['p25']:,.0f}–₹{c['p75']:,.0f}", c["n"]])
    o.append("</svg>")
    cs, mn = cells.get(("Coffee-led", areas[0]), {}), cells.get(("Coffee-led", areas[1]), {})
    big = (f'₹{cs["median"]:,.0f}<small> · </small>₹{mn["median"]:,.0f}' if cs.get("median") and mn.get("median") else "—")
    return (head(big, f"typical cost for two at a coffee-led café, {areas[0]} · {areas[1]}") + legend(areas) + "".join(o)
            + table(["Type", "Area", "Median", "Middle half", "Cafés"], rows, "Zomato cost for two, by type and area"))


# ---------------- attention ----------------
def deciles(ins):
    a = ins["insights"]["attention"]["by_area"]["Both areas"]
    dec = a["deciles"]
    H, L, R, T, B = 300, 8, 8, 34, 38
    slot = (W - L - R) / 10
    bw = min(46, slot * 0.62)
    top = max(dec) * 1.08
    sy = lambda p: T + (1 - p / top) * (H - T - B)
    g = uid("acc")
    o = [svg(H, "Share of all Google reviews held by each tenth of cafés", "cols", accent_grad(g))]
    labels = ["Top 10%", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "Bottom"]
    o.append(f'<line class="base" x1="{L}" x2="{W - R}" y1="{sy(0):.1f}" y2="{sy(0):.1f}"/>')
    for i, v in enumerate(dec):
        cx = L + slot * i + slot / 2
        hero = i == 0
        o.append(capsule_up(cx - bw / 2, sy(v), bw, sy(0), "hero" if hero else "mute", f"{labels[i]} of cafés: {v}% of reviews", g if hero else None))
        o.append(f'<text class="tick" x="{cx:.1f}" y="{H - 12}" text-anchor="middle">{labels[i]}</text>')
        if i in (0, 1, 9):
            lab = "<0.1%" if v < 0.1 else f"{v:g}%"
            o.append(f'<text class="{"val-hero" if hero else "val"}" x="{cx:.1f}" y="{sy(v) - 10:.1f}" text-anchor="middle">{lab}</text>')
    o.append("</svg>")
    return (head(f'{a["top10_share"]}%', "of all Google reviews sit with the top tenth of cafés") + "".join(o)
            + table(["Tenth of cafés", "Share of reviews"], [[labels[i], f"{v}%"] for i, v in enumerate(dec)],
                    "Share of all Google reviews by tenth of cafés"))


# ---------------- ratings ----------------
def ratings(ins, k):
    bks = ins["insights"]["ratings"]["buckets"]
    H, L, R, T, B = 300, 8, 8, 34, 38
    slot = (W - L - R) / len(bks)
    bw = min(64, slot * 0.5)
    sy = lambda p: T + (1 - p / 100) * (H - T - B)
    g = uid("acc")
    o = [svg(H, "Share of cafés rated 4.8 or higher, by number of Google reviews", "cols", accent_grad(g))]
    o.append(f'<line class="base" x1="{L}" x2="{W - R}" y1="{sy(0):.1f}" y2="{sy(0):.1f}"/>')
    rows = []
    for i, b in enumerate(bks):
        cx = L + slot * i + slot / 2
        o.append(f'<text class="tick" x="{cx:.1f}" y="{H - 12}" text-anchor="middle">{E(b["label"])} reviews</text>')
        v = b.get("share_48_plus")
        if v is None:
            o.append(f'<text class="muted-note" x="{cx:.1f}" y="{sy(0) - 8:.1f}" text-anchor="middle">fewer than {k}</text>')
            rows.append([b["label"], f"fewer than {k}", ""])
            continue
        hero = i in (0, len(bks) - 1)
        o.append(capsule_up(cx - bw / 2, sy(v), bw, sy(0), "hero" if hero else "mute", f"{b['label']} reviews: {v}% rated 4.8+ ({b['n']} cafés)", g if hero else None))
        o.append(f'<text class="{"val-hero" if hero else "val"}" x="{cx:.1f}" y="{sy(v) - 10:.1f}" text-anchor="middle">{v}%</text>')
        rows.append([b["label"], f"{v}%", b["n"]])
    o.append("</svg>")
    first, last = bks[0].get("share_48_plus"), bks[-1].get("share_48_plus")
    big = f"{first}%<small> → </small>{last}%" if first is not None and last is not None else "—"
    return (head(big, "rated 4.8 or above: cafés with under ten reviews vs a thousand or more") + "".join(o)
            + table(["Google reviews", "Rated 4.8+", "Cafés"], rows, "Share rated 4.8 or higher by review count"))


# ---------------- amenities ----------------
def amenities(ins, k, highlight=("wifi", "work_friendly")):
    items = ins["insights"]["amenities"]["items"]
    shown = sorted([i for i in items if i["share"] is not None], key=lambda i: -i["share"])
    hidden = [i for i in items if i["share"] is None]
    rowh, L, R, T = 40, 196, 56, 6
    H = T + rowh * len(shown) + (30 if hidden else 6)
    vmax = max(50, max((i["share"] for i in shown), default=50))
    sx = lambda v: L + v / vmax * (W - L - R)
    g = uid("acc")
    o = [svg(H, "Share of cafés on Zomato listing each feature", "bars", accent_grad(g, vertical=False))]
    rows = []
    for i, it in enumerate(shown):
        y = T + i * rowh
        hero = it["key"] in highlight
        o.append(f'<text class="cat{" cat-hero" if hero else ""}" x="0" y="{y + 21}">{E(it["label"])}</text>')
        o.append(f'<rect class="track" x="{L}" y="{y + 8}" width="{W - L - R}" height="18" rx="9"/>')
        w = max(sx(it["share"]) - L, 18)
        tip = f"{it['label']}: listed by {it['share']}% of cafés on Zomato"
        if it.get("median_reviews_yes") is not None:
            tip += f" · median Zomato reviews {it['median_reviews_yes']:,.0f} with vs {it['median_reviews_no']:,.0f} without"
        f = f' fill="url(#{g})"' if hero else ""
        o.append(f'<rect class="bar {"hero" if hero else "mute-strong"}" x="{L}" y="{y + 8}" width="{w:.1f}" height="18" rx="9"{f} data-tip="{E(tip)}" tabindex="0"/>')
        o.append(f'<text class="{"val-hero" if hero else "val"}" x="{W - R + 10}" y="{y + 22}">{it["share"]}%</text>')
        rows.append([it["label"], f"{it['share']}%"])
    if hidden:
        y = T + len(shown) * rowh
        o.append(f'<text class="muted-note" x="0" y="{y + 18}">{E(", ".join(i["label"] for i in hidden))}: each listed by fewer than {k} cafés</text>')
        rows += [[i["label"], f"fewer than {k} cafés"] for i in hidden]
    o.append("</svg>")
    wifi = next((i for i in items if i["key"] == "wifi"), None)
    big = f'{wifi["share"]}%' if wifi and wifi["share"] is not None else "—"
    return (head(big, "of cafés on Zomato list Wi-Fi") + "".join(o)
            + table(["Feature", "Share of cafés on Zomato"], rows, "Features cafés list on Zomato"))


# ---------------- demand ----------------
def demand(ins):
    panels, rows = [], []
    for s in ins["insights"]["demand"]["sets"]:
        for ser in s["series"]:
            pts = ser["points"]
            PW, H, L, R, T, B = 360, 190, 8, 40, 16, 26
            xs = [p[0] for p in pts]
            sx = lambda y: L + (y - xs[0]) / (xs[-1] - xs[0]) * (PW - L - R)
            sy = lambda v: T + (1 - v / 100) * (H - T - B)
            g = uid("dw")
            defs = f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="dw0"/><stop offset="1" class="dw1"/></linearGradient>'
            o = [f'<svg class="viz mini" viewBox="0 0 {PW} {H}" role="img" aria-label="{E("Google search interest in " + ser["term"] + ", Rajasthan, yearly average")}"><defs>{defs}</defs>']
            o.append(f'<line class="base" x1="{L}" x2="{PW - R}" y1="{sy(0):.1f}" y2="{sy(0):.1f}"/>')
            for y in (xs[0], 2019, xs[-1]):
                o.append(f'<text class="tick" x="{sx(y):.1f}" y="{H - 6}" text-anchor="middle">{y}</text>')
            pp = [(sx(y), sy(v)) for y, v in pts]
            line = monotone(pp)
            o.append(f'<path d="{line} L{pp[-1][0]:.1f},{sy(0):.1f} L{pp[0][0]:.1f},{sy(0):.1f} Z" fill="url(#{g})"/>')
            o.append(f'<path class="ln v1" d="{line}"/>')
            for (y, v), (px, py) in zip(pts, pp):
                o.append(f'<circle class="pt-hit" cx="{px:.1f}" cy="{py:.1f}" r="10" data-tip="{y}: index {v:g}" tabindex="0"/>')
            ex, ey = pp[-1]
            o.append(f'<circle class="end v1" cx="{ex:.1f}" cy="{ey:.1f}" r="5"/>')
            o.append(f'<text class="val" x="{ex + 9:.1f}" y="{ey + 4:.1f}">{pts[-1][1]:g}</text>')
            o.append("</svg>")
            mult = f"{ser['x2025_vs_2019']}×" if ser["x2025_vs_2019"] else "rising"
            sub = "since 2019" if ser["x2025_vs_2019"] else "from a small base"
            panels.append(f'<div class="panel"><div class="panel-head"><span class="term">“{E(ser["term"])}”</span>'
                          f'<span class="mult"><b>{E(mult)}</b> {E(sub)}</span></div>{"".join(o)}</div>')
            rows += [[ser["term"], y, f"{v:g}"] for y, v in pts]
    mult = {ser["term"]: ser["x2025_vs_2019"] for st in ins["insights"]["demand"]["sets"] for ser in st["series"]}
    top = max(((t, m) for t, m in mult.items() if m), key=lambda tm: tm[1], default=None)
    hd = head(f"{top[1]}×", f"Rajasthan's search interest in {top[0]}, 2025 against 2019") if top else ""
    return (hd + f'<div class="panels">{"".join(panels)}</div>'
            + table(["Term", "Year", "Index (yearly average)"], rows, "Google Trends, Rajasthan, yearly averages"))
