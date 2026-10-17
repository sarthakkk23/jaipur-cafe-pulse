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


def hbars(bars, label, hot=(0,), unit="%", sign=False, note=""):
    """Horizontal bars, labels left, values right. The `hot` bar is red, the rest pink. An optional note names the measure."""
    row = 40
    top = 34 if note else 0
    h = row * len(bars) + 10 + top
    mx = max(v for _, v in bars) or 1
    L = 200 if W >= 600 else 140
    out = []
    if note:
        out.append(f'<text x="0" y="18" class="c-soft">{E(note)}</text>')
    for i, (lab, v) in enumerate(bars):
        y = 6 + top + i * row
        w = (W - L - 60) * v / mx
        out.append(f'<text x="0" y="{y + 21}">{E(lab)}</text>'
                   f'<rect class="grow" x="{L}" y="{y + 6}" width="{max(w, 2):.1f}" height="22" fill="var({"--red" if i in hot else "--pink"})"/>'
                   f'<text x="{L + w + 8:.1f}" y="{y + 23}" class="c-strong">{"+" if sign and v > 0 else ""}{v:,}{unit}</text>')
    return _svg(h, label, "".join(out))


SHORT = {"Under 10": "<10", "10 to 49": "10–49", "50 to 199": "50–199", "200 to 999": "200–999", "1,000 or more": "1,000+"}


def columns(bands, label):
    """Vertical bars for the review-count bands."""
    n = len(bands)
    cw = W / n
    out = []
    for i, b in enumerate(bands):
        x = i * cw + cw * 0.18
        bw = cw * 0.64
        hgt = 190 * b["share48"] / 100
        y = 220 - hgt
        out.append(f'<rect class="grow-y" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(hgt, 2):.1f}" fill="var({"--red" if i == 0 else "--pink"})"/>'
                   f'<text x="{x + bw / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle" class="c-strong">{b["share48"]}%</text>'
                   f'<text x="{x + bw / 2:.1f}" y="246" text-anchor="middle">{E(b["band"] if W >= 600 else SHORT.get(b["band"], b["band"]))}</text>'
                   f'<text x="{x + bw / 2:.1f}" y="266" text-anchor="middle" class="c-soft">{b["n"]}{" cafés" if W >= 600 else ""}</text>')
    out.append('<text x="0" y="292" class="c-soft">Google reviews per café</text>')
    return _svg(300, label, f'<line x1="0" y1="220" x2="{W}" y2="220" stroke="var(--ink)" stroke-width="1.5"/>' + "".join(out))


def split(parts, label):
    """One 100% bar, first part red, then pink, then stone; a keyed row of values beneath."""
    fills = ["var(--red)", "var(--pink)", "var(--stone-2)"]
    x, out = 0.0, []
    col = W / len(parts)
    for i, (lab, v) in enumerate(parts):
        w = W * v / 100
        out.append(f'<rect class="grow" x="{x:.1f}" y="10" width="{max(w - 3, 1):.1f}" height="56" fill="{fills[min(i, 2)]}"/>')
        lx = i * col
        out.append(f'<rect x="{lx:.1f}" y="88" width="12" height="12" fill="{fills[min(i, 2)]}"/>'
                   f'<text x="{lx + 20:.1f}" y="99" class="c-strong">{v}%</text><text x="{lx + 20:.1f}" y="121">{E(lab)}</text>')
        x += w
    return _svg(132, label, "".join(out))


def spacing(areas, label):
    """Average distance to the nearest café: observed against random scatter, per area."""
    mx = max(a["random_m"] for a in areas)
    L = 150 if W >= 600 else 96
    out, y = [], 6
    for a in areas:
        out.append(f'<text x="0" y="{y + 18}" class="c-strong">{E(a["area"])}</text>')
        for kind, v, fill in (("observed", a["observed_m"], "var(--red)"), ("random", a["random_m"], "var(--stone-2)")):
            y += 30
            w = (W - L - 70) * v / mx
            out.append(f'<rect class="grow" x="{L}" y="{y}" width="{w:.1f}" height="20" fill="{fill}"/>'
                       f'<text x="{L - 10}" y="{y + 15}" text-anchor="end" class="c-soft">{"Actual" if kind == "observed" else "At random"}</text>'
                       f'<text x="{L + w + 8:.1f}" y="{y + 16}">{v} m</text>')
        y += 46
    out.append(f'<text x="0" y="{y + 4}" class="c-soft">Average distance to the nearest café</text>')
    return _svg(y + 12, label, "".join(out))


def _slog(v):
    return math.copysign(math.log1p(abs(v) / 100), v)


def forest(items, label):
    """Raw gap (open ring) against like-for-like effect (red dot) with its 90% interval, on a log scale of % change."""
    lo_v, hi_v = -80, 1200
    x0, x1 = (210, W - 15) if W >= 600 else (168, W - 12)
    X = lambda v: x0 + (x1 - x0) * (_slog(max(min(v, hi_v), lo_v)) - _slog(lo_v)) / (_slog(hi_v) - _slog(lo_v))
    row = 38
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


def chart(f, width=600):
    global W
    W = width
    c = f["chart"]
    lab = f"{f['value']}{f['unit']} {f['headline']}"
    if c["kind"] == "lorenz":
        return lorenz(c["points"], f["value"])
    if c["kind"] == "bands":
        return columns(c["bands"], lab)
    if c["kind"] == "split":
        return split(c["parts"], lab)
    if c["kind"] == "spacing":
        return spacing(c["areas"], lab)
    if c["kind"] == "forest":
        return forest(c["items"], lab)
    if c["kind"] == "bars":
        return hbars(c["bars"], lab, hot=(0, 1) if f["id"] == "price" else (0,), sign=c.get("sign", False), note=c.get("note", ""))
    if c["kind"] == "mix":
        return mix(c["rows"], lab)
    return ""
