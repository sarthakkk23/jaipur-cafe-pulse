"""Layer 2 (public aggregates) + copy + kudos + web/ -> dist/ (the deployable site).

Reads only data/public/insights_latest.json, content/narrative.yaml,
content/kudos.yaml and config.yaml. Never touches raw data.

Usage: python pipeline/build_site.py [--mode draft|publish]
  draft   : pending kudos shown with a badge, draft banner on the page
  publish : pending kudos left out; refuses to build if the publish gate fails
"""
import argparse, html, json, re, shutil, sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
import check_publish  # noqa: E402

E = html.escape
AREA_CLASS = {"C-Scheme": "s1", "Malviya Nagar": "s2"}
TYPES = ["Coffee-led", "Tea & chai", "Bakery", "All-day café"]


def fill(text, tokens):
    """Escape copy, then swap {{token}} for its value."""
    out = E(text)
    return re.sub(r"{{\s*([\w.]+)\s*}}", lambda m: f'<span class="fig">{E(str(tokens.get(m.group(1), "—")))}</span>', out)


def fmt_min(m):
    h = (m // 60) % 24
    if h == 0:
        return "midnight"
    if h == 12:
        return "noon"
    return f"{h % 12}{'am' if h < 12 else 'pm'}"


def words(text):
    """Headline split into masked words for the staggered reveal (plain text without JS)."""
    return " ".join(f'<span class="w"><span style="--d:{i}">{E(w)}</span></span>' for i, w in enumerate(text.split()))


def sec_head(eyebrow, idx):
    return (f'<div class="sec-head"><p class="eyebrow">{E(eyebrow)}</p><span class="idx">({idx:02d})</span>'
            f'<span class="rule" data-scene="enter" aria-hidden="true"></span></div>')


def nice_date(iso):
    return date.fromisoformat(iso).strftime("%-d %B %Y")


# ---------------- charts (inline SVG) ----------------
def svg_open(w, h, label, cls=""):
    return (f'<svg class="viz {cls}" viewBox="0 0 {w} {h}" role="img" aria-label="{E(label)}" '
            f'preserveAspectRatio="xMidYMid meet">')


def legend(areas):
    items = "".join(f'<span class="key"><i class="sw {AREA_CLASS[a]}"></i>{E(a)}</span>' for a in areas)
    return f'<div class="legend">{items}</div>'


def table(head, rows, caption):
    th = "".join(f"<th scope='col'>{E(h)}</th>" for h in head)
    trs = "".join("<tr>" + "".join(f"<td>{E(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<details class="table-view"><summary>View as table</summary>'
            f'<table><caption>{E(caption)}</caption><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></details>')


def chart_hours(ins, areas):
    h = ins["insights"]["hours"]
    W, H, L, R, T, B = 880, 340, 48, 20, 16, 40
    x0, x1 = 360, 1560
    sx = lambda m: L + (m - x0) / (x1 - x0) * (W - L - R)
    sy = lambda p: T + (1 - p / 100) * (H - T - B)
    out = [svg_open(W, H, "Share of cafés open at each time of day, by area", "line")]
    # breakfast window
    out.append(f'<rect class="band" x="{sx(360):.1f}" y="{T}" width="{sx(540) - sx(360):.1f}" height="{H - T - B}" rx="6"/>')
    out.append(f'<text class="band-label" x="{sx(450):.1f}" y="{T + 18}" text-anchor="middle">Before 9am</text>')
    for p in (0, 25, 50, 75, 100):
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{sy(p):.1f}" y2="{sy(p):.1f}"/>')
        out.append(f'<text class="tick" x="{L - 10}" y="{sy(p) + 4:.1f}" text-anchor="end">{p}%</text>')
    for m in range(360, 1561, 120):
        out.append(f'<text class="tick" x="{sx(m):.1f}" y="{H - 12}" text-anchor="middle">{fmt_min(m)}</text>')
    series, rows = [], {}
    for a in areas:
        c = h["curve"].get(a)
        if not c:
            continue
        pts = c["points"]
        d = " ".join(f"{'M' if i == 0 else 'L'}{sx(m):.1f},{sy(p):.1f}" for i, (m, p) in enumerate(pts))
        out.append(f'<path class="ln {AREA_CLASS[a]}" d="{d}"/>')
        series.append({"name": a, "cls": AREA_CLASS[a], "values": [p for _, p in pts]})
        for m, p in pts:
            rows.setdefault(m, {})[a] = p
    xs = sorted(rows)
    out.append(f'<line class="cross" x1="0" x2="0" y1="{T}" y2="{H - B}"/>')
    out.append(f'<rect class="hit" x="{L}" y="{T}" width="{W - L - R}" height="{H - T - B}" fill="transparent" '
               f'data-line=\'{E(json.dumps({"x": [sx(m) for m in xs], "labels": [fmt_clock(m) for m in xs], "y": {s["name"]: [sy(v) for v in s["values"]] for s in series}, "series": series}))}\' '
               f'tabindex="0" aria-label="Explore values by time of day"/>')
    out.append("</svg>")
    tbl = table(["Time"] + areas, [[fmt_clock(m)] + [f"{rows[m].get(a, '—')}%" for a in areas] for m in xs],
                "Share of cafés open, by time of day")
    return legend(areas) + "".join(out) + tbl


def fmt_clock(m):
    h, mi = divmod(m % 1440, 60)
    if h == 0 and mi == 0:
        return "midnight"
    if h == 12 and mi == 0:
        return "noon"
    h12 = 12 if h % 12 == 0 else h % 12
    return f"{h12}{':' + str(mi).zfill(2) if mi else ''}{'am' if h < 12 else 'pm'}"


def chart_prices(ins, areas, k):
    cells = {(c["type"], c["area"]): c for c in ins["insights"]["price"]["cells"]}
    W, rowh, L, R, T = 880, 64, 150, 70, 10
    H = T + rowh * len(TYPES) + 34
    vmax = 1500
    sx = lambda v: L + v / vmax * (W - L - R)
    out = [svg_open(W, H, "Cost for two by café type and area: median and middle half", "dots")]
    for v in range(0, vmax + 1, 250):
        out.append(f'<line class="grid" x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{T}" y2="{H - 30}"/>')
        out.append(f'<text class="tick" x="{sx(v):.1f}" y="{H - 10}" text-anchor="middle">₹{v:,}</text>')
    rows = []
    for i, t in enumerate(TYPES):
        yc = T + i * rowh + rowh / 2
        out.append(f'<text class="cat" x="{L - 16}" y="{yc + 5:.1f}" text-anchor="end">{E(t)}</text>')
        for j, a in enumerate(areas):
            y = yc + (-11 if j == 0 else 11)
            c = cells.get((t, a), {})
            if c.get("median") is None:
                out.append(f'<text class="muted-note" x="{sx(0) + 6:.1f}" y="{y + 4:.1f}">{E(a)}: fewer than {k} listings</text>')
                rows.append([t, a, f"fewer than {k}", "", ""])
                continue
            tip = f"{t} · {a}: median ₹{c['median']:,.0f}, middle half ₹{c['p25']:,.0f}–₹{c['p75']:,.0f} ({c['n']} cafés)"
            out.append(f'<line class="rng {AREA_CLASS[a]}" x1="{sx(c["p25"]):.1f}" x2="{sx(c["p75"]):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>')
            out.append(f'<circle class="dot {AREA_CLASS[a]}" cx="{sx(c["median"]):.1f}" cy="{y:.1f}" r="6" data-tip="{E(tip)}" tabindex="0"/>')
            out.append(f'<text class="val" x="{sx(c["p75"]) + 10:.1f}" y="{y + 4:.1f}">₹{c["median"]:,.0f}</text>')
            rows.append([t, a, f"₹{c['median']:,.0f}", f"₹{c['p25']:,.0f}–₹{c['p75']:,.0f}", c["n"]])
    out.append("</svg>")
    return legend(areas) + "".join(out) + table(["Type", "Area", "Median", "Middle half", "Cafés"], rows,
                                                 "Zomato cost for two, by type and area")


def chart_deciles(ins):
    a = ins["insights"]["attention"]["by_area"]["Both areas"]
    dec = a["deciles"]
    W, H, L, R, T, B = 880, 300, 48, 10, 20, 44
    slot = (W - L - R) / 10
    bw = 24
    sy = lambda p: T + (1 - p / 70) * (H - T - B)
    labels = ["Top 10%", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "Bottom 10%"]
    out = [svg_open(W, H, "Share of all Google reviews held by each tenth of cafés", "cols")]
    for p in (0, 20, 40, 60):
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{sy(p):.1f}" y2="{sy(p):.1f}"/>')
        out.append(f'<text class="tick" x="{L - 10}" y="{sy(p) + 4:.1f}" text-anchor="end">{p}%</text>')
    for i, v in enumerate(dec):
        cx = L + slot * i + slot / 2
        y = sy(v)
        hgt = max(sy(0) - y, 0.5)
        out.append(bar_up(cx - bw / 2, y, bw, hgt, "v1", f"{labels[i]} of cafés: {v}% of reviews"))
        out.append(f'<text class="tick" x="{cx:.1f}" y="{H - 18}" text-anchor="middle">{labels[i]}</text>')
        if i in (0, 1, 9):
            lab = "<0.1%" if v < 0.1 else f"{v:g}%"
            out.append(f'<text class="val" x="{cx:.1f}" y="{y - 8:.1f}" text-anchor="middle">{lab}</text>')
    out.append(f'<text class="axis-note" x="{L + slot * 5:.1f}" y="{H - 2}" text-anchor="middle">Cafés ranked by Google review count, in tenths</text>')
    out.append("</svg>")
    return "".join(out) + table(["Tenth of cafés", "Share of reviews"], [[labels[i], f"{v}%"] for i, v in enumerate(dec)],
                                "Share of all Google reviews by tenth of cafés")


def bar_up(x, y, w, h, cls, tip):
    r = min(4, h)
    d = (f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
         f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} L{x + w:.1f},{y + h:.1f} Z")
    return f'<path class="bar {cls}" d="{d}" data-tip="{E(tip)}" tabindex="0"/>'


def bar_right(x, y, w, h, cls, tip):
    r = min(4, w)
    d = (f"M{x:.1f},{y:.1f} L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
         f"L{x + w:.1f},{y + h - r:.1f} Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f} L{x:.1f},{y + h:.1f} Z")
    return f'<path class="bar {cls}" d="{d}" data-tip="{E(tip)}" tabindex="0"/>'


def chart_ratings(ins, k):
    bks = ins["insights"]["ratings"]["buckets"]
    W, H, L, R, T, B = 880, 280, 48, 10, 24, 44
    slot = (W - L - R) / len(bks)
    bw = 24
    sy = lambda p: T + (1 - p / 100) * (H - T - B)
    out = [svg_open(W, H, "Share of cafés rated 4.8 or higher, by number of Google reviews", "cols")]
    for p in (0, 25, 50, 75, 100):
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{sy(p):.1f}" y2="{sy(p):.1f}"/>')
        out.append(f'<text class="tick" x="{L - 10}" y="{sy(p) + 4:.1f}" text-anchor="end">{p}%</text>')
    rows = []
    for i, b in enumerate(bks):
        cx = L + slot * i + slot / 2
        out.append(f'<text class="tick" x="{cx:.1f}" y="{H - 18}" text-anchor="middle">{E(b["label"])}</text>')
        v = b.get("share_48_plus")
        if v is None:
            out.append(f'<text class="muted-note" x="{cx:.1f}" y="{sy(0) - 8:.1f}" text-anchor="middle">fewer than {k}</text>')
            rows.append([b["label"], f"fewer than {k}", ""])
            continue
        y = sy(v)
        out.append(bar_up(cx - bw / 2, y, bw, max(sy(0) - y, 0.5), "v1", f"{b['label']} reviews: {v}% rated 4.8+ ({b['n']} cafés)"))
        out.append(f'<text class="val" x="{cx:.1f}" y="{y - 8:.1f}" text-anchor="middle">{v}%</text>')
        rows.append([b["label"], f"{v}%", b["n"]])
    out.append(f'<text class="axis-note" x="{L + (W - L - R) / 2:.1f}" y="{H - 2}" text-anchor="middle">Number of Google reviews</text>')
    out.append("</svg>")
    return "".join(out) + table(["Google reviews", "Rated 4.8+", "Cafés"], rows, "Share rated 4.8 or higher by review count")


def chart_amenities(ins, k):
    items = ins["insights"]["amenities"]["items"]
    shown = sorted([i for i in items if i["share"] is not None], key=lambda i: -i["share"])
    hidden = [i for i in items if i["share"] is None]
    W, rowh, L, R, T = 880, 34, 190, 60, 8
    H = T + rowh * (len(shown) + (1 if hidden else 0)) + 8
    vmax = 50
    sx = lambda v: L + v / vmax * (W - L - R)
    out = [svg_open(W, H, "Share of cafés on Zomato listing each feature", "bars")]
    rows = []
    for i, it in enumerate(shown):
        y = T + i * rowh
        out.append(f'<text class="cat" x="{L - 14}" y="{y + 17}" text-anchor="end">{E(it["label"])}</text>')
        w = max(sx(it["share"]) - L, 0.5)
        tip = f"{it['label']}: listed by {it['share']}% of cafés on Zomato"
        if it.get("median_reviews_yes") is not None:
            tip += f" · median Zomato reviews {it['median_reviews_yes']:,.0f} with vs {it['median_reviews_no']:,.0f} without"
        out.append(bar_right(L, y + 5, w, 18, "v1", tip))
        out.append(f'<text class="val" x="{L + w + 8:.1f}" y="{y + 18}">{it["share"]}%</text>')
        rows.append([it["label"], f"{it['share']}%"])
    if hidden:
        y = T + len(shown) * rowh
        names = ", ".join(i["label"] for i in hidden)
        out.append(f'<text class="muted-note" x="0" y="{y + 18}">{E(names)}: each listed by fewer than {k} cafés</text>')
        rows += [[i["label"], f"fewer than {k} cafés"] for i in hidden]
    out.append("</svg>")
    return "".join(out) + table(["Feature", "Share of cafés on Zomato"], rows, "Features cafés list on Zomato")


def chart_demand(ins):
    panels = []
    rows = []
    for s in ins["insights"]["demand"]["sets"]:
        for ser in s["series"]:
            pts = ser["points"]
            W, H, L, R, T, B = 420, 210, 36, 14, 16, 30
            xs = [p[0] for p in pts]
            sx = lambda y: L + (y - xs[0]) / (xs[-1] - xs[0]) * (W - L - R)
            sy = lambda v: T + (1 - v / 100) * (H - T - B)
            o = [svg_open(W, H, f"Google search interest in '{ser['term']}', Rajasthan, yearly average", "mini")]
            for p in (0, 50, 100):
                o.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{sy(p):.1f}" y2="{sy(p):.1f}"/>')
                o.append(f'<text class="tick" x="{L - 8}" y="{sy(p) + 4:.1f}" text-anchor="end">{p}</text>')
            for y in (xs[0], 2019, xs[-1]):
                o.append(f'<text class="tick" x="{sx(y):.1f}" y="{H - 8}" text-anchor="middle">{y}</text>')
            line = " ".join(f"{'M' if i == 0 else 'L'}{sx(y):.1f},{sy(v):.1f}" for i, (y, v) in enumerate(pts))
            area = line + f" L{sx(xs[-1]):.1f},{sy(0):.1f} L{sx(xs[0]):.1f},{sy(0):.1f} Z"
            o.append(f'<path class="wash v1" d="{area}"/>')
            o.append(f'<path class="ln v1" d="{line}"/>')
            for y, v in pts:
                o.append(f'<circle class="pt v1" cx="{sx(y):.1f}" cy="{sy(v):.1f}" r="4" data-tip="{y}: index {v:g}" tabindex="0"/>')
            o.append("</svg>")
            mult = f"{ser['x2025_vs_2019']}× since 2019" if ser["x2025_vs_2019"] else "rising from a very small base"
            panels.append(f'<div class="panel"><div class="panel-head"><span class="term">“{E(ser["term"])}”</span>'
                          f'<span class="mult">{E(mult)}</span></div>{"".join(o)}</div>')
            rows += [[ser["term"], y, f"{v:g}"] for y, v in pts]
    return (f'<div class="panels">{"".join(panels)}</div>'
            + table(["Term", "Year", "Index (yearly average)"], rows, "Google Trends, Rajasthan, yearly averages"))


# ---------------- page ----------------
def section_html(sec, tokens, chart_html, meta, source, n_note, alt, idx):
    body = "".join(f"<p>{fill(p, tokens)}</p>" for p in sec["body"])
    tk = sec["takeaways"]
    return f"""
<section id="{sec['id']}" class="insight alt{' first' if alt == 'first' else ''}" aria-labelledby="{sec['id']}-h">
  <div class="wrap">
    {sec_head(sec['eyebrow'], idx)}
    <h2 id="{sec['id']}-h" class="headline split">{words(sec['headline'])}</h2>
    <div class="copy reveal">{body}</div>
    <figure class="card chart draw reveal">
      {chart_html}
      <figcaption>Source: {E(source)} · {E(n_note)} · captured {E(nice_date(meta['captured_on']))}</figcaption>
    </figure>
    <div class="takeaways">
      <article class="card take reveal"><p class="take-label">(If you run a café)</p><p>{fill(tk['owner'], tokens)}</p></article>
      <article class="card take reveal"><p class="take-label">(If you're opening one)</p><p>{fill(tk['planner'], tokens)}</p></article>
    </div>
  </div>
</section>"""


def build(mode):
    cfg = yaml.safe_load(open(ROOT / "config.yaml"))
    ins = json.load(open(ROOT / "data/public/insights_latest.json"))
    nar = yaml.safe_load(open(ROOT / "content/narrative.yaml"))
    kud = yaml.safe_load(open(ROOT / "content/kudos.yaml"))["entries"]
    T, meta, k = ins["tokens"], ins["meta"], ins["meta"]["min_group_size"]
    areas = meta["areas"]
    site = cfg["site"]

    charts = {
        "hours_curve": (lambda: chart_hours(ins, areas), "Zomato listed hours",
                        f"{ins['insights']['hours']['n']} cafés with listed hours"),
        "price_ranges": (lambda: chart_prices(ins, areas, k), "Zomato cost for two", "cafés with a listed price"),
        "attention_deciles": (lambda: chart_deciles(ins), "Google Maps review counts",
                              f"{ins['insights']['attention']['by_area']['Both areas']['n']} cafés on Google Maps"),
        "ratings_maturity": (lambda: chart_ratings(ins, k), "Google Maps ratings and review counts", "cafés with a Google rating"),
        "amenities_bars": (lambda: chart_amenities(ins, k), "Zomato highlights",
                           f"{ins['insights']['amenities']['n']} cafés on Zomato"),
        "demand_lines": (lambda: chart_demand(ins), "Google Trends, Rajasthan", "index 0–100 within each query set"),
    }

    nav = [("overview", "Overview")] + [(s["id"], s["nav"]) for s in nar["sections"]] + [("makers", "Makers"), ("method", "Method")]
    nav_html = "".join(f'<a class="chip" href="#{i}">{E(l)}</a>' for i, l in nav)

    cards = "".join(f"""
      <div class="hl-slot">
        <span class="hl-frame" aria-hidden="true"><span>({i + 1:02d})</span></span>
        <a class="hl-card" href="{E(h['link'])}">
          <span class="hl-glow" aria-hidden="true"></span>
          <span class="hl-value">{fill(h['value'], T)}</span>
          <span class="hl-caption">{fill(h['caption'], T)}</span>
          <span class="hl-more">See the detail <span aria-hidden="true">›</span></span>
        </a>
      </div>""" for i, h in enumerate(nar["highlights"]))

    secs = "".join(section_html(s, T, charts[s["chart"]][0](), meta, charts[s["chart"]][1], charts[s["chart"]][2], "first" if i == 0 else "", i + 1)
                   for i, s in enumerate(nar["sections"]))

    shown = [x for x in kud if x.get("approved") or mode == "draft"]
    makers = "".join(f"""
      <article class="card maker reveal">
        {'<span class="badge-draft">Draft · awaiting approval</span>' if not x.get('approved') else ''}
        <p class="maker-area">{E(x['area'])}</p>
        <h3>{E(x['name'])}</h3>
        <p>{E(x['praise'])}</p>
        <p class="maker-src">{' · '.join(f'<a href="{E(s["url"])}" rel="noopener" target="_blank">{E(s["publication"])}, {E(s["date"])}</a>' for s in x['sources'])}</p>
      </article>""" for x in shown)
    if not shown:
        makers = '<p class="muted">Entries appear here once approved.</p>'

    method = "".join(f'<article class="card point reveal"><h3>{E(p["title"])}</h3><p>{fill(p["text"], T)}</p></article>'
                     for p in nar["method"]["points"])

    au = site["author"]
    contact = []
    if au.get("linkedin"):
        contact.append(f'<a class="pill" href="{E(au["linkedin"])}" rel="noopener" target="_blank">Connect on LinkedIn</a>')
    if au.get("email"):
        contact.append(f'<a class="pill ghost" href="mailto:{E(au["email"])}">Email</a>')
    if not contact and mode == "draft":
        contact.append('<span class="badge-draft">Add your LinkedIn and email in config.yaml</span>')

    banner = ('<div class="draft-banner" role="status">Draft build. Not for publishing. Pending kudos are shown with a badge.</div>'
              if mode == "draft" else "")
    hero = nar["hero"]
    page = f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(site['title'])}</title>
<meta name="description" content="{E(site['tagline'])}">
<meta name="color-scheme" content="light dark">
<script>document.documentElement.classList.add("js")</script>
<link rel="stylesheet" href="assets/styles.css">
<script src="assets/app.js" defer></script>
</head>
<body>
{banner}
<header class="localnav">
  <div class="localnav-inner">
    <a class="brand" href="#overview">{E(site['title'])}</a>
    <span class="asof">C-Scheme / Malviya Nagar · Snapshot {E(nice_date(meta['captured_on']))}</span>
    <button class="grid-toggle" type="button" aria-pressed="false">Grid <span class="sw-on">On</span><span class="sw-off">Off</span></button>
  </div>
  <nav class="chips" aria-label="Sections">{nav_html}</nav>
</header>

<main>
<section id="overview" class="hero" aria-labelledby="hero-h">
  <div class="hero-glow" aria-hidden="true"></div>
  <div class="wrap">
    <p class="eyebrow reveal">{E(hero['eyebrow'])}</p>
    <h1 id="hero-h" class="hero-title rise"><span class="glow-text">{E(hero['headline'])}</span></h1>
    <p class="lede reveal">{fill(hero['lede'], T)}</p>
    <p class="badge reveal">C-Scheme · Malviya Nagar · refreshed every two weeks</p>
  </div>
</section>

<section class="highlights" data-scene="pin" aria-labelledby="hl-h" style="--n:{len(nar['highlights'])}">
  <div class="pin">
    <div class="wrap hl-head">
      <h2 id="hl-h" class="headline split">{words("The scene at a glance.")}</h2>
      <span class="hl-hint" aria-hidden="true">Scroll ¬</span>
    </div>
    <div class="gallery" tabindex="0" aria-label="Highlights">{cards}
    </div>
    <div class="wrap hl-foot"><span class="hl-progress" aria-hidden="true"><i></i></span>
      <span class="hl-count" aria-hidden="true">{len(nar['highlights']):02d} figures</span></div>
  </div>
</section>

<div class="curtain" data-scene="through" aria-hidden="true">
  {"".join(f'<span style="--i:{i}"></span>' for i in range(8))}
</div>
{secs}

<section id="makers" class="makers" data-invert aria-labelledby="makers-h">
  <div class="wrap">
    {sec_head(nar['makers']['eyebrow'], len(nar['sections']) + 1)}
    <h2 id="makers-h" class="headline split">{words(nar['makers']['headline'])}</h2>
    <p class="lede-sm reveal">{fill(nar['makers']['lede'], T)}</p>
    <div class="maker-grid">{makers}</div>
  </div>
</section>

<section id="method" class="method alt" aria-labelledby="method-h">
  <div class="wrap">
    {sec_head(nar['method']['eyebrow'], len(nar['sections']) + 2)}
    <h2 id="method-h" class="headline split">{words(nar['method']['headline'])}</h2>
    <div class="point-grid">{method}</div>
    <p class="download reveal"><a href="data/insights.json" download>Download this snapshot's aggregates (JSON)</a></p>
  </div>
</section>

<section class="about" aria-labelledby="about-h">
  <div class="wrap">
    <h2 id="about-h" class="headline split">{words("Made in Jaipur.")}</h2>
    <p class="lede-sm reveal">An independent research project by {E(au['name'])}, building a dated, honest record of
    how Jaipur's cafés change. If you run a café, or are about to open one, I'd like to hear from you.</p>
    <div class="contact reveal">{''.join(contact)}</div>
  </div>
</section>
</main>

<footer class="foot">
  <div class="wrap">
    <p>Independent research. Not affiliated with or endorsed by Google, Zomato, Swiggy or magicpin; platform names
    appear only to cite where public figures came from. Figures are aggregates of public listings captured on
    {E(nice_date(meta['captured_on']))}; groups smaller than {k} cafés are not shown.</p>
    <p>Built {E(date.today().strftime('%-d %B %Y'))} · Snapshot {E(meta['snapshot'])}</p>
  </div>
</footer>
<div class="tip" role="tooltip" hidden></div>
<div class="grid-overlay" aria-hidden="true"><div class="wrap">{"".join("<span></span>" for _ in range(12))}</div></div>
</body>
</html>
"""
    out = ROOT / "dist"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web", out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page)
    (out / ".nojekyll").write_text("")
    shutil.copy(ROOT / "data/public/insights_latest.json", out / "data/insights.json")
    return out / "index.html"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["draft", "publish"], default="draft")
    a = ap.parse_args()
    errors, warnings = check_publish.check(a.mode)
    if errors and a.mode == "publish":
        for e in errors:
            print("ERROR", e)
        print("refusing to build a publish version")
        return 1
    path = build(a.mode)
    errors, warnings = check_publish.check(a.mode, path)
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors and a.mode == "publish":
        path.unlink()
        print("built page failed the gate; removed")
        return 1
    print(f"built {path.relative_to(ROOT)} ({a.mode}); {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
