"""Version 2: "The Instrument". Same data, copy and gate as v1; a quieter page.

Jaipur was founded by an astronomer who built instruments to measure the sky. This page
measures the city's cafés, and every figure is set as a reading from an instrument.

Usage: python pipeline/build_v2.py [--mode draft|publish]
"""
import argparse, html, json, re, shutil, sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
import check_publish  # noqa: E402

E = html.escape
TYPES = ["Coffee-led", "Tea & chai", "Bakery", "All-day café"]

PHOTOS = {
    "hawa-mahal-sky": ("The Hawa Mahal against a pale morning sky, Jaipur", "Nikunj Mundra", "https://unsplash.com/photos/W3qWtMNwRf0", 3200, 3706),
    "jantar-dial": ("A sundial at Jantar Mantar, Jaipur", "Ravi Kumar Meena", "https://unsplash.com/photos/0k3ohtAd7DU", 3200, 4267),
    "patrika-gate-sky": ("Patrika Gate against a clear sky, Jaipur", "Swaroop Satheesh", "https://unsplash.com/photos/n8r8CLJUo2o", 3200, 5689),
    "jantar-field": ("The instruments of Jantar Mantar below Nahargarh, Jaipur", "Ibrahim Rifath", "https://unsplash.com/photos/ZCa9LzaG_9M", 3200, 2134),
    "morning-cup": ("A cup of coffee steaming in low morning light", "Barney Goodman", "https://unsplash.com/photos/Di2oDZKW2es", 3200, 2209),
}


def fill(text, T):
    """Escape copy, swap {{token}} for its value, drop the v1 accent marks (no styled accent words here)."""
    out = E(text.replace("*", ""))
    return re.sub(r"{{\s*([\w.]+)\s*}}", lambda m: f'<span class="n">{E(str(T.get(m.group(1), "—")))}</span>', out)


def pic(name, sizes, cls="", eager=False, prefix=""):
    alt, who, _, w, h = PHOTOS[name]
    srcset = lambda ext: ", ".join(f"{prefix}img/{name}-{s}.{ext} {s}w" for s in (900, 1600, 2400))
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<picture class="{cls}"><source type="image/webp" srcset="{srcset("webp")}" sizes="{sizes}">'
            f'<img src="{prefix}img/{name}-1600.jpg" srcset="{srcset("jpg")}" sizes="{sizes}" width="{w}" height="{h}" alt="{E(alt)}" {load}></picture>')


def nice(iso):
    return date.fromisoformat(iso).strftime("%-d %B %Y")


def short(iso):
    return date.fromisoformat(iso).strftime("%-d %b %Y")


def head(title, desc, prefix=""):
    guard = 'document.documentElement.classList.add("js");setTimeout(function(){if(!window.__pulse)document.documentElement.classList.remove("js","motion")},3000)'
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#f5f5f2">
<script>{guard}</script>
<link rel="preload" href="{prefix}fonts/literata.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}v2.css">
<script src="{prefix}v2.js" defer></script>"""


def bar(site, prefix="", home=True):
    h = "" if home else "../../"
    links = [("Readings", "readings"), ("Map", "map"), ("The best", "best"), ("Method", "method")]
    nav = "".join(f'<a href="{h}#{i}">{E(l)}</a>' for l, i in links)
    return (f'<header class="bar"><a class="wordmark" href="{h}#top">{E(site["title"])}</a>'
            f'<nav class="bar-links" aria-label="Sections">{nav}</nav>'
            f'<a class="btn" href="{h}#benchmark">Take a reading</a></header>')


def credits_line(prefix=""):
    ph = "; ".join(f'<a href="{E(u)}" rel="noopener" target="_blank">{E(who)}</a>' for _, (_, who, u, _, _) in PHOTOS.items())
    return (f'Photographs on Unsplash by {ph}. Street plate © <a href="https://www.openstreetmap.org/copyright" rel="noopener" target="_blank">'
            f'OpenStreetMap contributors</a> (ODbL). Search interest from Google Trends. Independent research: not affiliated with or endorsed by '
            f'Google, Zomato, Swiggy or magicpin, whose names appear only to cite where public figures came from.')


def build(mode):
    cfg = yaml.safe_load(open(ROOT / "config.yaml"))
    ins = json.load(open(ROOT / "data/public/insights_latest.json"))
    nar = yaml.safe_load(open(ROOT / "content/narrative.yaml"))
    T, meta, k = ins["tokens"], ins["meta"], ins["meta"]["min_group_size"]
    I = ins["insights"]
    site, au = cfg["site"], cfg["site"]["author"]
    ent = lambda t: "".join(f"&#{ord(c)};" for c in t)
    mailto = ent(f"mailto:{au['email']}?subject={quote(au.get('email_subject', site['title']))}") if au.get("email") else ""
    captured = nice(meta["captured_on"])
    hist = I.get("history") or []
    ch = I.get("changes")
    core = T.get("scene.core_cafes", "")

    # ---------- hero: a two-by-two board ----------
    hero = f"""<section class="board" id="top" aria-labelledby="hero-h">
  <div class="tile t-name"><h1 id="hero-h"><span class="name">Jaipur</span><span class="name-sub">Café Pulse</span></h1></div>
  <figure class="tile t-photo t-a">{pic("hawa-mahal-sky", "(max-width: 760px) 100vw, 50vw", eager=True)}</figure>
  <figure class="tile t-photo t-b">{pic("jantar-dial", "(max-width: 760px) 100vw, 50vw")}</figure>
  <div class="tile t-dark"><p>{E(core)} cafés, read every two weeks like an instrument.</p></div>
  <div class="tile t-pink"><p>Latest reading<br><strong>{E(captured)}</strong></p></div>
</section>"""

    # ---------- intro: lead over four columns ----------
    intro = f"""<section class="intro" aria-label="About this record">
  <p class="lead reveal">An independent, dated record of the cafés of C-Scheme and Malviya Nagar. Every two weeks we re-read
  them on the same searches and publish what moved, as aggregates, never as anyone's scorecard.</p>
  <div class="cols">
    <p class="reveal"><b>Who.</b> Independent research by {E(au['name'])}, based in Jaipur. No platform pays for it, no café pays to
    appear in it, and no café is ranked by its ratings.</p>
    <p class="reveal"><b>What.</b> {E(T.get('scene.venues_tracked', ''))} venues read from Zomato, Google Maps and Swiggy, matched into one
    record with permanent IDs. Figures appear only for groups of {k} cafés or more.</p>
    <p class="reveal"><b>Where.</b> C-Scheme with Ashok Nagar, and Malviya Nagar from World Trade Park to the sectors: two
    of the city's densest café districts, and the two we can measure honestly today.</p>
    <p class="reveal"><b>Reach.</b> If you run a café, or are about to open one, write to <a href="{mailto}">{ent(au.get('email', ''))}</a>
    or find {E(au['name'].split()[0])} on <a href="{E(au.get('linkedin', ''))}" rel="noopener" target="_blank">LinkedIn</a>. A private reading of your own café is free.</p>
  </div>
</section>"""

    # ---------- one figure owns the screen ----------
    figure = f"""<section class="figure-page field-pink" aria-labelledby="fig-h">
  <h2 id="fig-h" class="reveal">Mornings are open.</h2>
  <div class="fig-block">
    <p class="fig reveal">{E(str(I['hours'].get('open_by_8', '—')))}<sup>%</sup></p>
    <p class="fig-cap reveal">of cafés with listed hours are serving by 8am. Read across {E(T.get('hours.n', ''))} cafés on {E(captured)}.</p>
  </div>
  <p class="fig-src">Source: Zomato listed hours</p>
</section>"""

    # ---------- the sundial: the day as an instrument reads it ----------
    curve = (I["hours"]["curve"].get("Both areas") or {}).get("points", [])
    areas_curve = {a: (I["hours"]["curve"].get(a) or {}).get("points", []) for a in meta["areas"]}
    dial_data = json.dumps({"all": curve, "areas": areas_curve}).replace("</", "<\\/")
    sundial = f"""<section class="sundial" id="day" data-pin aria-labelledby="day-h">
  <div class="sd-pin">
    <div class="sd-copy">
      <h2 id="day-h" class="reveal">The day, on a dial.</h2>
      <p class="reveal">Each of the twenty-four wedges is an hour. Its fill is the share of cafés open then. The typical café opens at
      {E(T.get('hours.median_open', ''))}; chai cafés rise earliest, {E(T.get('hours.open_by_8.tea', ''))} open by 8am against
      {E(T.get('hours.open_by_8.coffee', ''))} of coffee-led cafés.</p>
      <p class="sd-read" aria-live="polite"><span class="sd-time">8am</span><span class="sd-share">{E(str(I['hours'].get('open_by_8', '')))}% of cafés open</span>
      <span class="sd-areas"></span></p>
    </div>
    <svg class="dial" viewBox="-220 -220 440 440" role="img" aria-label="Share of cafés open at each hour of the day, drawn as a sundial">
      <g class="wedges"></g><g class="marks"></g><line class="gnomon" x1="0" y1="0" x2="0" y2="-196"/><circle class="hub" r="38"/>
    </svg>
  </div>
  <script type="application/json" id="dial-data">{dial_data}</script>
</section>"""

    # ---------- the survey plate ----------
    snaps = "".join(f'<button type="button" class="seg" data-snap="{E(h["label"])}" aria-pressed="{str(i == len(hist) - 1).lower()}">{E(short(h["captured_on"]))}</button>'
                    for i, h in enumerate(hist))
    by_area = {h["label"]: h["by_area"] for h in hist}
    terrain = json.dumps(I["terrain"]).replace("</", "<\\/")
    mp = f"""<section class="plate" id="map" data-pin aria-labelledby="map-h">
  <div class="plate-pin">
    <canvas class="plate-canvas" aria-hidden="true"></canvas>
    <div class="plate-labels" aria-hidden="true"></div>
    <div class="plate-copy">
      <h2 id="map-h">Where the cafés gather.</h2>
      <ol class="stops">
        <li data-stop="0" class="on"><b>Jantar Mantar.</b> Built by the founder of Jaipur to measure the sky; the city has been measuring itself since.</li>
        <li data-stop="1"><b>C-Scheme.</b> {E(T.get('scene.core.cs', ''))} cafés in the planned neighbourhood south of the old city.</li>
        <li data-stop="2"><b>Malviya Nagar.</b> {E(T.get('scene.core.mn', ''))} cafés, from World Trade Park to the sectors.</li>
      </ol>
      <div class="plate-ctrl"><span>Reading of</span>{snaps}</div>
      <p class="plate-note">Contours rise where cafés stand close together. Counts only, smoothed over about 200 metres.</p>
    </div>
  </div>
  <script type="application/json" id="terrain-data">{terrain}</script>
</section>"""

    # ---------- what moved: snapshot tabs over banded readings ----------
    def bands_latest():
        if not ch:
            return []
        mom = ch.get("momentum") or {}
        rows = [(T.get("changes.newly_listed", "—"), "Newly listed", f"Confirmed on Zomato or on two platforms. Another {T.get('changes.churn_in', '—')} appeared in a single search."),
                (T.get("changes.share_gaining", "—"), "Gained reviews", f"Share of cafés with at least one new Google review in {T.get('changes.days', '')} days."),
                (T.get("changes.share_gaining.cs", "—"), "C-Scheme", f"gained reviews, against {T.get('changes.share_gaining.mn', '—')} in Malviya Nagar."),
                (T.get("changes.busiest_type_share", "—"), "Broadest momentum", f"of {T.get('changes.busiest_type', '')} cafés gained reviews, more than any other type."),
                (T.get("changes.closed", "—"), "Now listed as closed", f"and {T.get('changes.not_found', '—')} confirmed café could not be found. They stay on the record.")]
        return [r for r in rows if r[0] not in ("—", None)]

    def bands_for(h, prev):
        rows = [(f"{h.get('core_confirmed', h['core']):,}", "Confirmed cafés", "On Zomato or on two platforms.")]
        for a, v in h["by_area"].items():
            d = "" if not prev else f" ({v - prev['by_area'][a]:+d} since the last reading)"
            rows.append((f"{v:,}", a, "confirmed cafés" + d))
        for a, v in (h.get("median_price") or {}).items():
            if v:
                rows.append((f"₹{v:,.0f}", f"Cost for two, {a}", "the typical café, as listed on Zomato"))
        return rows

    tabs, panels = [], []
    for i, h in enumerate(hist):
        latest = i == len(hist) - 1
        rows = (bands_latest() if latest and ch else []) + bands_for(h, hist[i - 1] if i else None)
        body = "".join(f'<li><span class="b-v">{E(str(v))}</span><span class="b-t">{E(t)}</span><span class="b-n">{E(n)}</span></li>' for v, t, n in rows)
        tabs.append(f'<button type="button" class="tab" role="tab" id="tab-{i}" aria-controls="pan-{i}" aria-selected="{str(latest).lower()}">'
                    f'<span>{E(date.fromisoformat(h["captured_on"]).strftime("%a"))}</span><b>{E(short(h["captured_on"]))}</b></button>')
        panels.append(f'<ul class="bands" role="tabpanel" id="pan-{i}" aria-labelledby="tab-{i}"{"" if latest else " hidden"}>{body}</ul>')
    moved = f"""<section class="moved" id="readings" aria-labelledby="moved-h">
  <div class="moved-head"><h2 id="moved-h"><span class="soft">What moved</span><br>between readings.</h2>
    <a class="btn btn-ghost" href="data/insights.json" download>Download the figures</a></div>
  <div class="moved-body"><div class="tabs" role="tablist" aria-label="Readings">{"".join(tabs)}</div><div>{"".join(panels)}</div></div>
</section>"""

    # ---------- what the readings say: a mosaic of unlike tiles ----------
    att = I["attention"]["by_area"]["Both areas"]
    dec = att["deciles"]
    segs = "".join(f'<i style="--w:{max(v, 0.6):.2f}" class="{"hot" if j == 0 else ""}"></i>' for j, v in enumerate(dec))
    am = {a["key"]: a for a in I["amenities"]["items"]}
    rare = sorted([a for a in I["amenities"]["items"]], key=lambda a: (a["share"] is not None, a["share"] or 0))[:4]
    rare_li = "".join(f'<li><span>{E(a["label"])}</span><b>{"fewer than " + str(k) if a["share"] is None else str(a["share"]) + "%"}</b></li>' for a in rare)
    mosaic = f"""<section class="mosaic" id="findings" aria-labelledby="mos-h">
  <div class="m m-head"><h2 id="mos-h">What the readings say.</h2></div>
  <figure class="m m-photo">{pic("patrika-gate-sky", "(max-width: 760px) 100vw, 50vw")}</figure>
  <div class="m m-fig"><p class="m-big">{E(T.get('attention.top10_share.all', ''))}</p><p>of all Google reviews sit with the top tenth of cafés.</p>
    <div class="deciles" role="img" aria-label="Share of reviews by tenth of cafés">{segs}</div></div>
  <div class="m m-list"><p class="m-k">Rarely offered</p><ul>{rare_li}</ul><p class="m-foot">Share of {E(T.get('amenities.n', ''))} cafés on Zomato.</p></div>
  <div class="m m-sent field-pink"><p>A coffee-led café costs {E(T.get('price.coffee.cs', ''))} for two in C-Scheme and {E(T.get('price.coffee.mn', ''))} in Malviya Nagar.</p>
    <p class="m-foot">Same cup, different street. Zomato's listed cost for two.</p></div>
  <div class="m m-sent2"><p>Under ten reviews, {E(T.get('ratings.share48.newest', ''))} rate 4.8 or above. Past a thousand, {E(T.get('ratings.share48.established', ''))}.</p>
    <p class="m-foot">A rating that settles is usually a café that is growing.</p></div>
  <div class="m m-fig2"><p class="m-big">{E(T.get('demand.matcha.multiple', ''))}</p><p>Rajasthan's searches for matcha, 2025 against 2019. Coffee: {E(T.get('demand.coffee.multiple', ''))}.</p></div>
  <div class="m m-wide"><p>Only {E(T.get('amenities.share.wifi', ''))} of cafés list Wi-Fi and {E(T.get('amenities.share.work_friendly', ''))} call themselves work-friendly, yet those that do carry far more reviews.</p></div>
  <div class="m m-wide2"><p>Half the cafés we read have {E(T.get('attention.median_reviews.all', ''))} Google reviews or fewer: most cafés compete in the long tail, where every review counts for more.</p></div>
</section>"""

    # ---------- the best right now ----------
    profs = ins.get("profiles") or []
    rows = "".join(f"""<li><a href="cafes/{E(p['slug'])}/">
      <span class="best-name">{E(p['name'])}</span>
      <span class="best-tag">{E(p['tagline'])}</span>
      <span class="best-where">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))}</span>
      <span class="best-go">What they did right</span></a></li>""" for p in profs)
    band = f"""<figure class="band reveal">{pic("morning-cup", "100vw")}</figure>"""
    best = band + f"""<section class="best" id="best" aria-labelledby="best-h">
  <h2 id="best-h">The best, right now.</h2>
  <p class="best-sub">What each one did right, from public facts and its neighbourhood.</p>
  <ul class="best-list">{rows}</ul>
  <p class="best-note">Chosen by {E(au['name'])}. Never ranked by ratings, reviews or prices.</p>
</section>""" if profs else ""

    # ---------- the live thing: take a reading of your café ----------
    tool_data = json.dumps({
        "areas": meta["areas"], "types": TYPES, "k": k, "captured_on": captured,
        "price": I["price"], "attention": I["attention"]["by_area"], "ratings": I["ratings"]["buckets"], "open_cdf": I["hours"]["open_cdf"],
        "amenities": [{"key": a["key"], "label": a["label"], "share": a["share"]} for a in I["amenities"]["items"]],
        "counts": I["scene"]["by_type"], "demand": {s["term"]: s["x2025_vs_2019"] for q in I["demand"]["sets"] for s in q["series"]},
        "email": au.get("email", ""), "subject": au.get("email_subject", site["title"]),
    }, ensure_ascii=False).replace("</", "<\\/")
    fmt_clock = lambda m: (f"{12 if (m // 60) % 12 == 0 else (m // 60) % 12}{':' + str(m % 60).zfill(2) if m % 60 else ''}{'am' if m // 60 < 12 else 'pm'}")
    opts = "".join(f'<option value="{m}">{fmt_clock(m)}</option>' for m in range(360, 781, 30))
    radios = lambda name, vals: "".join(f'<label class="opt"><input type="radio" name="{name}" value="{E(v)}"{" checked" if i == 0 else ""}><span>{E(v)}</span></label>'
                                        for i, v in enumerate(vals))
    am_opts = "".join(f'<label class="opt"><input type="checkbox" name="am" value="{a["key"]}"><span>{E(a["label"])}</span></label>' for a in I["amenities"]["items"])
    bench = f"""<section class="bench" id="benchmark" aria-labelledby="bench-h">
  <div class="bench-copy"><h2 id="bench-h">Take a reading of your café.</h2>
    <p>Set your area and type and add what you know. The reading is computed in your browser from the same published figures;
    nothing you type leaves this page.</p>
    <div class="seg-row" role="group" aria-label="Mode" data-ui><button type="button" class="seg-btn" data-mode="owner" aria-pressed="true">I run a café</button>
    <button type="button" class="seg-btn" data-mode="planner" aria-pressed="false">I'm opening one</button></div>
  </div>
  <form class="tool-form" autocomplete="off" data-ui>
    <fieldset><legend>Area</legend><div class="opts">{radios("area", meta["areas"])}</div></fieldset>
    <fieldset><legend>Type</legend><div class="opts">{radios("type", TYPES)}</div></fieldset>
    <div class="owner-only fields">
      <label class="field"><span>Cost for two (₹)</span><input type="number" name="price" min="50" max="20000" step="10" inputmode="numeric" placeholder="700"></label>
      <label class="field"><span>Google reviews</span><input type="number" name="reviews" min="0" max="100000" step="1" inputmode="numeric" placeholder="120"></label>
      <label class="field"><span>Google rating</span><input type="number" name="rating" min="1" max="5" step="0.1" inputmode="decimal" placeholder="4.5"></label>
      <label class="field"><span>Opens at</span><select name="open"><option value="">Choose</option>{opts}</select></label>
    </div>
    <fieldset class="owner-only"><legend>What you offer</legend><div class="opts">{am_opts}</div></fieldset>
  </form>
  <div class="tool-results" aria-live="polite"></div>
  <script type="application/json" id="pulse-data">{tool_data}</script>
</section>"""

    # ---------- method: many into one ----------
    listings = (I.get("method") or {}).get("listings")
    method = f"""<section class="method" id="method" aria-labelledby="method-h">
  <figure class="method-pic reveal">{pic("jantar-field", "(max-width: 760px) 100vw, 60vw")}</figure>
  <div class="method-copy"><h2 id="method-h">Many listings, one record.</h2>
    <p>Three platforms describe the same café three ways. We read them all on the same searches every run, match them into one record,
    and publish only what holds for a group.</p></div>
  <svg class="many" viewBox="0 0 1200 270" role="img" aria-label="Scattered platform listings compressed into one ordered record"
       data-listings="{listings or 0}" data-venues="{(I.get('method') or {}).get('venues', 0)}"></svg>
  <div class="method-cols">
    <p><b>Gather.</b> {E(T.get('method.listings', '—'))} platform listings this run: 25 Google Maps searches, 8 Zomato searches and 30 Swiggy
    queries, identical every run, collected slowly and never past a block.</p>
    <p><b>Match.</b> One record of {E(T.get('scene.venues_tracked', ''))} venues with permanent IDs, matched by name and distance.
    A café counts as new or gone only when Zomato lists it or two platforms agree.</p>
    <p><b>Publish.</b> Aggregates only. Any group under {k} cafés is withheld; a café is named only to credit it, never next to its
    ratings, reviews or prices.</p>
  </div>
</section>"""

    # ---------- contact + footer ----------
    contact = f"""<section class="contact" id="contact" aria-label="Contact">
  <p class="c-say reveal">Run a café in Jaipur, or about to open one? Tell me what you would want measured.</p>
  <div class="c-links reveal"><p class="c-q">Want a private reading?</p>
    <a href="{mailto}">{ent(au.get('email', ''))}</a>
    <a href="{E(au.get('linkedin', ''))}" rel="noopener" target="_blank">{E(au['name'])} on LinkedIn</a>
    <p class="c-where">Jaipur, India. Readings are free for owners.</p></div>
</section>"""
    footer = f"""<footer class="foot">
  <a class="foot-name" href="{mailto}">Write to {E(au['name'].split()[0])}</a>
  <p>{credits_line()}</p>
  <p>Reading of {E(captured)} · groups under {k} cafés withheld · built {E(date.today().strftime('%-d %B %Y'))}</p>
</footer>"""

    banner = '<p class="draft-note">Draft build. Not for publishing.</p>' if mode == "draft" else ""
    page = (head(site["title"], site["tagline"])
            + '\n<script type="importmap">{"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.min.js"}}</script>'
            + '\n<script type="module" src="plate.js"></script>\n<script src="tool.js" defer></script>\n</head>\n<body>\n'
            + banner + bar(site) + "\n<main>\n" + "\n".join([hero, intro, figure, sundial, mp, moved, mosaic, best, bench, method, contact])
            + "\n</main>\n" + footer + "\n</body>\n</html>\n")

    out = ROOT / "dist"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web" / "v2", out)
    shutil.copy(ROOT / "web" / "assets" / "tool.js", out / "tool.js")
    (out / "data").mkdir(exist_ok=True)
    shutil.copy(ROOT / "data/public/insights_latest.json", out / "data/insights.json")
    (out / ".nojekyll").write_text("")
    (out / "index.html").write_text(page)
    for p in profs:
        d = out / "cafes" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(profile(p, site, au, captured, core, k, mailto, ent))
    return out / "index.html"


def profile(p, site, au, captured, core, k, mailto, ent):
    pre = "../../"
    def src(s):
        if not s.get("url"):
            return f'<span class="src">{E(s["publication"])}, {E(s["date"])}</span>'
        return f'<a class="src" href="{E(s["url"])}" rel="noopener" target="_blank">{E(s["publication"])}, {E(s["date"])}</a>'
    story = "".join(f'<li class="reveal"><p>{E(x["text"])}</p>{src(x["source"])}</li>' for x in p["story"])
    sig = "".join(f'<li class="reveal"><span class="b-v">{E(s["v"])}</span><span class="b-t">{E(s["k"])}</span><span class="b-n">{E(s["t"])}</span></li>' for s in p["signals"])
    measured = sorted((f for f in p["features"] if f["share"] is not None), key=lambda f: f["share"])
    feats = "".join(f'<li><span>{E(f["f"])}</span><b>{f["share"]}% of cafés</b></li>' for f in measured)
    also = sorted(f["f"] for f in p["features"] if f["share"] is None)
    also = f'<p class="pf-also">Also lists {E(", ".join(also[:-1]).lower())} and {E(also[-1].lower())}.</p>' if len(also) > 1 else ""
    rows = "".join(f'<tr><td>{E(o["area"])}</td><td>{E(o["locality"] or "")}</td><td>{E(o["opens"] + "–" + o["closes"]) if o["opens"] and o["closes"] else "Not listed"}</td>'
                   f'<td>{E(", ".join(o["on"]))}</td><td>{"Yes" if o["delivers"] else "Dine-in"}</td></tr>' for o in p["outlets"])
    notes = f'<blockquote class="notes">{E(p["notes"])}</blockquote>' if p.get("notes") else ""
    return (head(f"{p['name']} · {site['title']}", f"{p['tagline']} What {p['name']} did right.", pre)
            + "\n</head>\n<body>\n" + bar(site, pre, home=False) + f"""
<main class="pf">
  <section class="pf-head"><h1 class="reveal">{E(p['name'])}</h1><p class="pf-tag reveal">{E(p['tagline'])}</p>
    <p class="pf-where reveal">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))} · {len(p['outlets'])} {'café' if len(p['outlets']) == 1 else 'cafés'}</p></section>
  <section class="pf-sec"><h2>What they did right.</h2><ul class="story">{story}</ul>{notes}</section>
  <section class="pf-sec field-stone"><h2>Against the {E(core)} cafés we read.</h2><ul class="bands">{sig}</ul>
    <p class="pf-note">Area figures are aggregates. We never show a café's own ratings, review counts or prices.</p></section>
  <section class="pf-sec"><h2>What they offer.</h2><ul class="rare">{feats or '<li><span>Not listed.</span></li>'}</ul>{also}
    <table class="outlets"><caption>Cafés we read</caption><thead><tr><th>Area</th><th>Locality</th><th>Hours, first listed day</th><th>Listed on</th><th>Delivery</th></tr></thead><tbody>{rows}</tbody></table></section>
  <section class="contact"><p class="c-say">Run a café? A private reading of your own is free.</p><div class="c-links"><a href="{mailto}">{ent(au.get('email', ''))}</a>
    <a href="{pre}#benchmark">Take a reading now</a></div></section>
</main>
<footer class="foot"><a class="foot-name" href="{pre}">{E(site['title'])}</a><p>{credits_line()}</p>
<p>Facts from the sources linked and from public listings read on {E(captured)}. Groups under {k} cafés withheld.</p></footer>
</body>
</html>
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["draft", "publish"], default="draft")
    a = ap.parse_args()
    errors, _ = check_publish.check(a.mode)
    if errors and a.mode == "publish":
        for e in errors:
            print("ERROR", e)
        return 1
    path = build(a.mode)
    errors, warnings = check_publish.check(a.mode, path)
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors and a.mode == "publish":
        path.unlink()
        return 1
    print(f"built {path.relative_to(ROOT)} (v2, {a.mode}); {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
