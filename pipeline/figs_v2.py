"""Charts for the v2 findings, as static SVG. One mark colour per job: red for the finding, pink for its context,
stone for the rest. Values are labelled directly, so nothing depends on colour alone. Marks carry `grow` or `draw`
classes that the stylesheet animates once the chart is on screen."""
import html
import math

E = html.escape
W = 600


def _svg(h, label, body):
    cls = "chart" if W >= 600 else "chart chart-narrow"
    return (f'<svg class="{cls}" viewBox="0 0 {W} {h}" role="img" aria-label="{E(label)}" preserveAspectRatio="xMidYMid meet">'
            f'{body}</svg>')


def lorenz(points, value):
    """Cumulative share of reviews against cumulative share of cafés, fewest reviews first."""
    x0, y0, s = 60 if W >= 600 else 8, 20, 260
    k = (W - x0 - 40) / s if W >= 600 else (W - x0 - 8) / s
    P = lambda x, y: (x0 + s * x / 100 * k, y0 + s - s * y / 100)
    pts = [P(x, y) for x, y in points]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M{P(0, 0)[0]},{P(0, 0)[1]} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{P(100, 100)[0]},{P(100, 100)[1]} Z"
    ex, ey = P(90, 0)
    yv = next(y for x, y in points if x == 90)
    _, py = P(90, yv)
    eq0, eq1 = P(0, 0), P(100, 100)
    return _svg(300, f"Lorenz curve: the top tenth of cafés hold {value}% of reviews", f"""
<path class="fade" d="M{eq0[0]},{eq0[1]} L{eq1[0]},{eq1[1]} L{P(0, 100)[0]},{P(0, 100)[1]} Z" fill="var(--stone)"/>
<path class="fade" d="{area}" fill="var(--pink)"/>
<line x1="{eq0[0]}" y1="{eq0[1]}" x2="{eq1[0]}" y2="{eq1[1]}" stroke="var(--soft)" stroke-width="1.5"/>
<polyline class="draw" points="{line}" fill="none" stroke="var(--red)" stroke-width="3" stroke-linejoin="round" pathLength="1"/>
<line x1="{ex}" y1="{py}" x2="{ex}" y2="{P(90, 100)[1]}" stroke="var(--ink)" stroke-width="2"/>
<text x="{ex - 10}" y="{P(0, 46)[1]}" text-anchor="end" class="c-strong">{value}% of reviews</text>
<text x="{ex - 10}" y="{P(0, 46)[1] + 20}" text-anchor="end">with the top tenth</text>
<text x="{x0}" y="{y0 + s + 26}">Cafés, fewest reviews first</text>
<text x="{P(100, 0)[0]}" y="{y0 + s + 26}" text-anchor="end">all</text>
<text x="{P(8, 8)[0]}" y="{P(8, 8)[1] - 10}" class="c-soft" transform="rotate({-math.degrees(math.atan(1 / k)):.1f} {P(8, 8)[0]} {P(8, 8)[1] - 10})">if every café had an equal share</text>""")


# ---------- one chart system: every chart shares this frame, grid, ticks, axis titles and colours ----------

def _nice(mx):
    """Round tick steps (0, 25, 50, 75, 100 ...) that cover mx."""
    if mx <= 0:
        return [0, 1]
    raw = mx / 4
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    n = math.ceil(mx / step - 1e-9)
    return [round(i * step, 6) for i in range(n + 1)]


def _tick(v, unit):
    t = f"{v:,.0f}" if abs(v - round(v)) < 1e-9 else f"{v:,.1f}"
    t = t.replace("-", "−")
    return f"{t}{unit}" if unit in ("%", "×") else (f"{unit}{t}" if unit in ("₹", "$", "US$") else (f"{t} {unit}" if unit else t))


def _title(x, y, text, anchor="start", rotate=False):
    rot = f' transform="rotate(-90 {x} {y})"' if rotate else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="c-ax"{rot}>{E(text)}</text>'


def hbar(rows, x_title="", y_title="", hot=(0,), unit="%", label="", title="", lo=None):
    """Horizontal bars. rows: (category, value) or (category, value, value text). Categories down the left (the y axis,
    titled above them), a value axis along the bottom with light gridlines and a title, the value printed at each bar's end.
    Negative values run left of a zero line."""
    rows = [r if len(r) == 3 else (r[0], r[1], None) for r in rows]
    narrow = W < 600
    L = 0 if narrow else 196                         # the category column (on phones each name sits above its bar)
    R = 76 if narrow else 84                         # room for the value text
    T = (26 if title else 0) + (22 if y_title else 6)
    row = 56 if narrow else 38
    vmin = min(0, *(v for _, v, _ in rows)) if lo is None else lo
    vmax = max(0, *(v for _, v, _ in rows))
    if vmin >= 0:
        ticks = _nice(vmax)
    else:                                            # one step for both sides of zero
        st = _nice(max(vmax, -vmin))[1]
        ticks = [round(i * st, 6) for i in range(math.floor(vmin / st), math.ceil(vmax / st) + 1)]
    a, b = ticks[0], ticks[-1]
    X = lambda v: L + (W - L - R) * (v - a) / ((b - a) or 1)
    H = T + row * len(rows)
    out = []
    if title:
        out.append(f'<text x="0" y="16" class="c-title">{E(title)}</text>')
    if y_title:
        out.append(_title(0, T - 10, y_title))
    for t in ticks:                                  # gridlines and tick labels
        out.append(f'<line x1="{X(t):.1f}" y1="{T - 4}" x2="{X(t):.1f}" y2="{H}" class="c-grid{" c-zero" if t == 0 else ""}"/>'
                   f'<text x="{X(t):.1f}" y="{H + 20}" text-anchor="middle" class="c-tick">{E(_tick(t, unit))}</text>')
    for i, (cat, v, txt) in enumerate(rows):
        y = T + i * row
        x0, x1 = sorted((X(0), X(v)))
        txt = txt if txt is not None else _tick(v, unit) if unit in ("%", "×") else f"{v:,}"
        sign = "+" if (vmin < 0 and v > 0 and txt[0].isdigit()) else ""
        by = y + (26 if narrow else 8)               # bar top
        out.append(f'<text x="0" y="{y + (18 if narrow else 23)}" class="c-cat">{E(cat)}</text>'
                   f'<rect class="grow" x="{x0:.1f}" y="{by}" width="{max(x1 - x0, 2):.1f}" height="22" fill="var({"--red" if i in hot else "--pink"})"/>'
                   f'<text x="{(x1 if v >= 0 else x0) + (8 if v >= 0 else -8):.1f}" y="{by + 16}" text-anchor="{"start" if v >= 0 else "end"}" class="c-strong">{E(sign + txt)}</text>')
    if x_title:
        out.append(_title((L + W - R) / 2, H + 46, x_title, "middle"))
    return _svg(H + (56 if x_title else 30), label or title or x_title, "".join(out))


def vcol(rows, x_title="", y_title="", hot=(0,), unit="%", label="", title="", show=None, short=None):
    """Vertical columns. rows: (category, value). A value axis up the left with gridlines and a turned title;
    categories along the bottom with a title under them. `show` lists which columns print their value (default all)."""
    narrow = W < 600
    L = 56
    T = 26 if title else 12
    ch = 190
    ticks = _nice(max(v for _, v in rows))
    top = ticks[-1]
    Y = lambda v: T + ch - ch * v / top
    n = len(rows)
    cw = (W - L) / n
    out = [f'<text x="0" y="16" class="c-title">{E(title)}</text>'] if title else []
    for t in ticks:
        out.append(f'<line x1="{L}" y1="{Y(t):.1f}" x2="{W}" y2="{Y(t):.1f}" class="c-grid{" c-zero" if t == 0 else ""}"/>'
                   f'<text x="{L - 8}" y="{Y(t) + 4:.1f}" text-anchor="end" class="c-tick">{E(_tick(t, unit))}</text>')
    for i, (cat, v) in enumerate(rows):
        x = L + i * cw + cw * 0.18
        bw = cw * 0.64
        out.append(f'<rect class="grow-y" x="{x:.1f}" y="{Y(v):.1f}" width="{bw:.1f}" height="{max(T + ch - Y(v), 1):.1f}" fill="var({"--red" if i in hot else "--pink"})"><title>{E(cat)}: {E(_tick(v, unit))}</title></rect>')
        if show is None or i in show:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{Y(v) - 8:.1f}" text-anchor="middle" class="c-strong">{E(_tick(v, unit))}</text>')
        lab = (short or {}).get(cat, cat) if narrow else cat
        out.append(f'<text x="{x + bw / 2:.1f}" y="{T + ch + 22}" text-anchor="middle" class="c-cat">{E(lab)}</text>')
    if y_title:
        out.append(_title(14, T + ch / 2, y_title, "middle", rotate=True))
    if x_title:
        out.append(_title((L + W) / 2, T + ch + 50, x_title, "middle"))
    return _svg(T + ch + (60 if x_title else 34), label or title or x_title, "".join(out))


def hbars(bars, label, hot=(0,), unit="%", sign=False, note="", x_title="", y_title=""):
    """Kept for the findings' data shape: (label, value) pairs."""
    return hbar(bars, x_title or note, y_title, hot, unit, label)


def tbars(rows, label, hot=(0,), note="", x_title="", y_title="", unit=""):
    """Bars whose value labels are text (₹52, 84 tables): rows are (label, value, text). Tick units follow the text."""
    ts = [t for _, _, t in rows]
    if not unit:
        unit = "₹" if all(t.startswith("₹") for t in ts) else "%" if all(t.endswith("%") for t in ts) else ""
    return hbar(rows, x_title, y_title, hot, unit, label, title=note)


SHORT = {"Under 10": "<10", "10 to 49": "10–49", "50 to 199": "50–199", "200 to 999": "200–999", "1,000 or more": "1,000+"}


def columns(bands, label, x_title="Google reviews per café", y_title="Cafés rated 4.8 or more"):
    """The review-count bands, as columns on the shared frame."""
    return vcol([(b["band"], b["share48"]) for b in bands], x_title, y_title, (0,), "%", label, short=SHORT)


def split(parts, label, x_title=""):
    """One 100% bar, split into its parts, on a 0–100% axis with a title; a key with each part's value beneath."""
    fills = ["var(--red)", "var(--pink)", "var(--stone-2)"]
    L, R, T = 0, 8, 8
    X = lambda v: L + (W - L - R) * v / 100
    out = []
    for t in (0, 25, 50, 75, 100):
        out.append(f'<line x1="{X(t):.1f}" y1="{T - 4}" x2="{X(t):.1f}" y2="{T + 52}" class="c-grid"/>'
                   f'<text x="{X(t):.1f}" y="{T + 72}" text-anchor="{"start" if t == 0 else "end" if t == 100 else "middle"}" class="c-tick">{t}%</text>')
    x = 0.0
    for i, (lab, v) in enumerate(parts):
        out.append(f'<rect class="grow" x="{X(x):.1f}" y="{T}" width="{max(X(v) - X(0) - 2, 1):.1f}" height="44" fill="{fills[min(i, 2)]}"><title>{E(lab)}: {v}%</title></rect>')
        if v >= 9:
            out.append(f'<text x="{X(x) + 10:.1f}" y="{T + 28}" class="c-strong" fill="{"var(--paper)" if i == 0 else "var(--ink)"}">{v}%</text>')
        x += v
    y = T + 78
    if x_title:
        out.append(_title(W / 2, y + 16, x_title, "middle"))
        y += 26
    col = W / len(parts) if W >= 600 else W / min(len(parts), 2)
    for i, (lab, v) in enumerate(parts):
        lx, ly = (i % (len(parts) if W >= 600 else 2)) * col, y + 18 + (i // (len(parts) if W >= 600 else 2)) * 26
        out.append(f'<rect x="{lx:.1f}" y="{ly - 11}" width="12" height="12" fill="{fills[min(i, 2)]}"/>'
                   f'<text x="{lx + 20:.1f}" y="{ly}" class="c-cat"><tspan class="c-strong">{v}%</tspan> {E(lab)}</text>')
    rows_ = 1 if W >= 600 else math.ceil(len(parts) / 2)
    return _svg(y + 14 + 26 * rows_, label, "".join(out))


def spacing(areas, label, x_title="Average distance to the nearest café (metres)", y_title="Area"):
    """Actual distance to the nearest café against random scatter, per area, as paired bars on the shared frame."""
    rows, hot = [], []
    for a in areas:
        hot.append(len(rows))
        rows += [(f'{a["area"]}, actual', a["observed_m"], f'{a["observed_m"]} m'), (f'{a["area"]}, at random', a["random_m"], f'{a["random_m"]} m')]
    return hbar(rows, x_title, y_title, tuple(hot), "", label)


def both(fn, *a, **k):
    """The same chart at desktop and phone width; the stylesheet shows one."""
    global W
    W = 600
    wide = fn(*a, **k)
    W = 400
    narrow = fn(*a, **k)
    W = 600
    return f'<figure class="pb-chart reveal">{wide}{narrow}</figure>'


def _slog(v):
    return math.copysign(math.log1p(abs(v) / 100), v)


def forest(items, label):
    """Raw gap (open ring) against like-for-like effect (red dot) with its 90% interval, on a log scale of % change."""
    lo_v, hi_v = -80, 1200
    x0, x1 = (210, W - 15) if W >= 600 else (168, W - 12)
    X = lambda v: x0 + (x1 - x0) * (_slog(max(min(v, hi_v), lo_v)) - _slog(lo_v)) / (_slog(hi_v) - _slog(lo_v))
    row = 56 if narrow else 38
    top = 34
    out = [f'<line x1="{X(0):.1f}" y1="{top - 10}" x2="{X(0):.1f}" y2="{top + row * len(items)}" stroke="var(--ink)" stroke-width="1.5"/>']
    for t in ((-50, 0, 100, 400, 1000) if W >= 600 else (0, 100, 1000)):
        out.append(f'<text x="{X(t):.1f}" y="{top - 16}" text-anchor="middle" class="c-soft">{"+" if t > 0 else ""}{t}%</text>')
    for i, it in enumerate(items):
        y = top + i * row + row / 2
        bold = "c-strong" if it["holds"] else ""
        out.append(f'<text x="0" y="{y + 5}" class="{bold}">{E(it["label"])}</text>'
                   f'<line class="grow" x1="{X(it["lo"]):.1f}" y1="{y}" x2="{X(it["hi"]):.1f}" y2="{y}" stroke="var({"--red" if it["holds"] else "--pink"})" stroke-width="4" stroke-linecap="round"/>'
                   f'<circle cx="{X(it["raw"]):.1f}" cy="{y}" r="7" fill="var(--paper)" stroke="var(--ink)" stroke-width="2"/>'
                   f'<circle class="pop" cx="{X(it["adj"]):.1f}" cy="{y}" r="7" fill="var({"--red" if it["holds"] else "--soft"})"/>')
    ly = top + row * len(items) + 26
    out.append(f'<circle cx="8" cy="{ly - 5}" r="6" fill="var(--paper)" stroke="var(--ink)" stroke-width="2"/><text x="22" y="{ly}">Raw gap</text>'
               f'<circle cx="128" cy="{ly - 5}" r="6" fill="var(--red)"/><text x="142" y="{ly}">Like for like, with 90% interval</text>')
    return _svg(ly + 12, label, "".join(out))


def mix(rows, label):
    """Type mix by area: one stacked bar per area, values labelled inside."""
    fills = {"Coffee-led": "var(--red)", "Tea & chai": "var(--sky)", "Bakery": "var(--pink)", "All-day café": "var(--stone-2)"}
    ink = {"Coffee-led": "var(--paper)", "Tea & chai": "var(--paper)", "Bakery": "var(--ink)", "All-day café": "var(--ink)"}
    out, y = [], 8
    for area, parts in rows:
        out.append(f'<text x="0" y="{y + 16}" class="c-strong">{E(area)}</text>')
        y += 26
        x = 0.0
        for t, v in parts:
            w = W * v / 100
            out.append(f'<rect class="grow" x="{x:.1f}" y="{y}" width="{max(w - 3, 1):.1f}" height="40" fill="{fills[t]}"/>')
            if v >= 7:
                out.append(f'<text x="{x + 8:.1f}" y="{y + 26}" fill="{ink[t]}">{v}%</text>')
            x += w
        y += 58
    per = 4 if W >= 600 else 2
    for j, t in enumerate(fills):
        lx, ly = (j % per) * (W / per), y + (j // per) * 26
        out.append(f'<rect x="{lx:.0f}" y="{ly}" width="14" height="14" fill="{fills[t]}"/><text x="{lx + 20:.0f}" y="{ly + 12}">{E(t)}</text>')
    return _svg(y + 24 + 26 * (len(fills) // per - 1), label, "".join(out))


# axis titles for each finding's chart: (value axis, category axis)
AXES = {
    "attention": ("Share of all Google reviews", ""), "platforms_rate": ("Share of cafés rated on both platforms", ""),
    "delivery": ("Share of cafés that deliver through Zomato", ""), "swiggy_cost_for_two": ("Share of cafés on both apps", ""),
    "visibility": ("Share of cafés", ""), "survey_on_the_fence": ("Share of café-goers asked", ""),
    "amenities": ("Extra Google reviews for cafés with Wi-Fi", "Compared with"), "price": ("Share of cafés", "Cost for two"),
    "cs_price_premium": ("Cafés charging over ₹600 for two", "Area"), "listing_detail": ("Share of cafés on Zomato", "Features listed"),
    "menus": ("Share of cafés listing it", "Cuisine"), "survey_word_of_mouth": ("Share of café-goers asked", "Heard about it from"),
    "survey_the_place": ("Share of café-goers asked", "Chose it for"), "survey_long_stays": ("Share of café-goers asked", "Time stayed"),
    "survey_mornings": ("Share of café-goers asked", "First coffee or tea out"),
}


def chart(f, width=600):
    global W
    W = width
    c = f["chart"]
    lab = f"{f['value']}{f['unit']} {f['headline']}"
    xt, yt = AXES.get(f["id"], ("", ""))
    if c["kind"] == "lorenz":
        return lorenz(c["points"], f["value"])
    if c["kind"] == "bands":
        return columns(c["bands"], lab)
    if c["kind"] == "split":
        return split(c["parts"], lab, xt)
    if c["kind"] == "spacing":
        return spacing(c["areas"], lab)
    if c["kind"] == "forest":
        return forest(c["items"], lab)
    if c["kind"] == "bars":
        return hbar(c["bars"], xt or c.get("note", ""), yt, (0, 1) if f["id"] == "price" else (0,), c.get("unit", "%"), lab)
    if c["kind"] == "mix":
        return mix(c["rows"], lab)
    return ""
