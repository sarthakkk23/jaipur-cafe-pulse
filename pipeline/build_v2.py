"""Version 2: "The Instrument". The full record turned into graded, explained findings.

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
import figs_v2 as figs  # noqa: E402

E = html.escape
TYPES = ["Coffee-led", "Tea & chai", "Bakery", "All-day café"]

PHOTOS = {
    "hawa-mahal-sky": ("The Hawa Mahal's pink sandstone face against a pale morning sky, Jaipur", "Nikunj Mundra", "https://unsplash.com/photos/W3qWtMNwRf0", 3200, 3706),
    "jantar-dial": ("A sundial at Jantar Mantar, Jaipur", "Ravi Kumar Meena", "https://unsplash.com/photos/0k3ohtAd7DU", 3200, 4267),
    "patrika-gate-sky": ("Patrika Gate against a clear sky, Jaipur", "Swaroop Satheesh", "https://unsplash.com/photos/n8r8CLJUo2o", 3200, 5689),
    "jantar-field": ("The instruments of Jantar Mantar below Nahargarh, Jaipur", "Ibrahim Rifath", "https://unsplash.com/photos/ZCa9LzaG_9M", 3200, 2134),
    "hawa-horses": ("Decorated horses passing the Hawa Mahal, Jaipur", "Aditya Siva", "https://unsplash.com/photos/6rDbvXzIVpQ", 3200, 2133),
    "pink-haveli": ("A pink haveli seen through neem leaves, Jaipur", "Chirag Singhvi", "https://unsplash.com/photos/17tsb--Y72M", 3200, 4231),
    "kulhad-chai": ("Chai in clay kulhads beside a blue-pottery plate", "VD Photography", "https://unsplash.com/photos/HHM4Ejj0SCE", 3200, 4266),
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


def bar(site, prefix="", home=True, updates=True, here=""):
    h = "" if home else (prefix or "../../")
    links = [("Insights", f"{h}#insights"), ("Location check", f"{h}location/"), ("The best", f"{h}#best"), ("Method", f"{h}#method")]
    links += [("Free updates", f"{h}#updates")] if updates else []
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{u}"{cur if l == here else ""}>{E(l)}</a>' for l, u in links)
    return (f'<header class="bar"><a class="wordmark" href="{h}#top">{E(site["title"])}</a>'
            f'<nav class="bar-links" aria-label="Sections">{nav}</nav>'
            f'<a class="btn" href="{h}#contact">Coffee?</a></header>')


def credits_line(prefix=""):
    ph = "; ".join(f'<a href="{E(u)}" rel="noopener" target="_blank">{E(who)}</a>' for _, (_, who, u, _, _) in PHOTOS.items())
    return (f'Photographs on Unsplash by {ph}. Street plate © <a href="https://www.openstreetmap.org/copyright" rel="noopener" target="_blank">'
            f'OpenStreetMap contributors</a> (ODbL). Search interest from Google Trends. Independent research: not affiliated with or endorsed by '
            f'Google, Zomato, Swiggy or magicpin, whose names appear only to cite where public figures came from.')


def build(mode):
    cfg = yaml.safe_load(open(ROOT / "config.yaml"))
    ins = json.load(open(ROOT / "data/public/insights_latest.json"))
    T, meta, k = ins["tokens"], ins["meta"], ins["meta"]["min_group_size"]
    I = ins["insights"]
    site, au = cfg["site"], cfg["site"]["author"]
    ent = lambda t: "".join(f"&#{ord(c)};" for c in t)
    mailto = ent(f"mailto:{au['email']}?subject={quote('Coffee? ' + au.get('email_subject', site['title']))}") if au.get("email") else ""
    captured = nice(meta["captured_on"])
    core = T.get("scene.core_cafes", "")
    F = {f["id"]: f for f in I.get("findings") or []}
    lead_f = F.get("cluster") or next(iter(F.values()))

    # ---------- hero: the city's cafés as an object you can turn ----------
    terrain = json.dumps({"grid": I["terrain"]["grid"], "bbox": I["terrain"]["bbox"],
                          "all": I["terrain"]["frames"][meta["snapshot"]]["all"]}).replace("</", "<\\/")
    hero = f"""<section class="hero" id="top" aria-labelledby="hero-h">
  <figure class="hero-pic" aria-hidden="true">{pic("hawa-mahal-sky", "(max-width: 900px) 100vw, 55vw", eager=True)}</figure>
  <div class="hero-copy">
    <div class="hero-top">
      <h1 id="hero-h" class="hero-h">Jaipur's cafés, measured.</h1>
      <p class="hero-sub">What {E(core)} cafés reveal about being found, rated and chosen.</p>
    </div>
    <p class="hero-fig"><span class="hero-num">{lead_f['value']}<small>{E(lead_f['unit'])}</small></span>
      <span class="hero-cap">{E(lead_f['headline'])}</span></p>
    <div class="hero-foot"><p class="hero-act"><a class="btn" href="#insights">See what works</a><a class="btn btn-ghost" href="#benchmark">Check your café</a></p>
    <p class="hero-meta">C-Scheme and Malviya Nagar · updated {E(captured)} · <a href="#f-{E(lead_f['id'])}">How I know</a></p></div>
  </div>
  <div class="hero-obj">
    <canvas class="relief" aria-label="Café density across C-Scheme and Malviya Nagar, sculpted as a relief"></canvas>
    <div class="relief-labels" aria-hidden="true"></div>
    <figure class="relief-still">{pic("jantar-dial", "(max-width: 900px) 100vw, 55vw", eager=True)}</figure>
    <p class="relief-hint" aria-hidden="true">Drag to turn. The taller the ground, the more cafés stand close together.</p>
    <p class="relief-note">At the top: Jantar Mantar, the stone observatory Jaipur's founder built to measure the sky. This page measures its cafés.</p>
  </div>
  <script type="application/json" id="relief-data">{terrain}</script>
</section>"""

    # ---------- intro ----------
    intro = f"""<section class="intro" aria-label="About this record">
  <p class="lead reveal">I read every café listing in C-Scheme and Malviya Nagar, so you don't have to. Then I tell you, in plain words,
  what the data says and what it doesn't. It is updated often, so the trends are the latest ones.</p>
  <div class="cols">
    <p class="reveal"><b>Plain words.</b> Each finding is one sentence and one number: a share of cafés, and what it means for yours.</p>
    <p class="reveal"><b>What it doesn't say.</b> Every finding also says where it stops, so you never read more into it than is there.</p>
    <p class="reveal"><b>Serious statistics, simply.</b> Resampling, like-for-like models and clustering tests run behind every figure.
    You get the answer, not the jargon.</p>
    <p class="reveal"><b>Evidence.</b> <span class="ev" data-g="3"><i></i><i></i><i></i></span> strong,
    <span class="ev" data-g="2"><i></i><i></i><i></i></span> moderate, <span class="ev" data-g="1"><i></i><i></i><i></i></span> weak.
    How sure each finding is. Independent research by {E(au['name'])}; no platform or café pays to appear.</p>
  </div>
</section>"""

    # ---------- findings, in three chapters ----------
    G = {"Strong": 3, "Moderate": 2, "Weak": 1}

    def finding(f, flip):
        how = "".join(f"<li>{E(h)}</li>" for h in f["how"])
        g = G.get(f["grade"], 1)
        return f"""<article class="fd{' flip' if flip else ''}" id="f-{E(f['id'])}">
  <div class="fd-text reveal">
    <p class="fd-num">{f['value']}<small>{E(f['unit'])}</small></p>
    <h3 class="fd-head">{E(f['headline'])}</h3>
    <p class="fd-body">{E(f['body'])}</p>
    {f'<p class="fd-limit">{E(f["limit"])}</p>' if f.get("limit") else ""}
    <p class="fd-grade"><span class="ev" data-g="{g}"><i></i><i></i><i></i></span>{E(f['grade'])} evidence · {f['n']:,} cafés</p>
    <details class="fd-how"><summary>How I know</summary><ul>{how}</ul></details>
  </div>
  <figure class="fd-chart reveal">{figs.chart(f, 600)}{figs.chart(f, 400)}</figure>
</article>"""

    def chapter(cid, title, lede, ids, after=""):
        items = [F[i] for i in ids if i in F]
        if not items:
            return ""
        body = "".join(finding(f, n % 2 == 1) for n, f in enumerate(items))
        return f"""<section class="chapter" id="{cid}" aria-labelledby="{cid}-h">
  <header class="ch-head reveal"><h2 id="{cid}-h">{E(title)}</h2><p>{E(lede)}</p></header>
  {body}{after}
</section>"""

    ch1 = chapter("insights", "Where attention goes.", "Reviews and ratings decide who gets found. Here is how they really behave, in plain words.",
                  ["attention", "ratings", "platforms_rate", "delivery"])
    band = f"""<figure class="band reveal" data-drift>{pic("hawa-horses", "100vw")}<figcaption>Outside the Hawa Mahal, in the old city.</figcaption></figure>"""
    pair = f"""<section class="pair" aria-label="Mornings in Jaipur">
  <figure class="pair-a reveal" data-drift>{pic("kulhad-chai", "(max-width: 760px) 100vw, 40vw")}<figcaption>Chai in clay kulhads: the city's first order of the day.</figcaption></figure>
  <figure class="pair-b reveal" data-drift>{pic("pink-haveli", "(max-width: 760px) 100vw, 55vw")}<figcaption>A haveli in the Pink City, through neem leaves.</figcaption></figure>
</section>"""
    ch2 = chapter("offer", "What cafés offer.", "Menus, prices and features: what is common, what is rare, and what actually goes with being chosen.",
                  ["amenities", "price", "menus", "visibility"])

    # ---------- the sundial ----------
    curve = (I["hours"]["curve"].get("Both areas") or {}).get("points", [])
    areas_curve = {a: (I["hours"]["curve"].get(a) or {}).get("points", []) for a in meta["areas"]}
    dial_data = json.dumps({"all": curve, "areas": areas_curve}).replace("</", "<\\/")
    sundial = f"""<section class="sundial" id="day" aria-labelledby="day-h">
  <div class="sd-pin">
    <div class="sd-copy">
      <h2 id="day-h" class="reveal">When they open.</h2>
      <p class="reveal">Only {E(str(I['hours'].get('open_by_8', '')))}% of cafés are serving by 8am; the typical one opens at {E(T.get('hours.median_open', ''))}.
      The morning is open ground, especially for coffee: {E(T.get('hours.open_by_8.coffee', ''))} of coffee-led cafés open by 8am, against
      {E(T.get('hours.open_by_8.tea', ''))} of chai cafés. Scroll to move through the day.</p>
      <p class="sd-read" aria-live="polite"><span class="sd-time">8am</span><span class="sd-share">{E(str(I['hours'].get('open_by_8', '')))}% of cafés open</span>
      <span class="sd-areas"></span></p>
    </div>
    <svg class="dial" viewBox="-220 -220 440 440" role="img" aria-label="Share of cafés open at each hour of the day, drawn as a sundial">
      <g class="wedges"></g><g class="marks"></g><line class="gnomon" x1="0" y1="0" x2="0" y2="-196"/><circle class="hub" r="38"/>
    </svg>
  </div>
  <script type="application/json" id="dial-data">{dial_data}</script>
</section>"""

    # ---------- where they gather ----------
    loc_cta = """<a class="loc-cta reveal" href="location/"><span class="loc-cta-h">Check a location.</span>
  <span class="loc-cta-p">Pick any spot in C-Scheme or Malviya Nagar and read its five-minute walk: how many cafés, what kind, and where the gaps are.</span>
  <span class="btn">Open the location check</span></a>"""
    ch3 = chapter("place", "Where they gather.", "Cafés pull towards each other, and customers always have a neighbour to compare.",
                  ["cluster", "areas"], after=loc_cta)

    # ---------- the best right now ----------
    profs = ins.get("profiles") or []
    plist = "".join(f"""<li><a href="cafes/{E(p['slug'])}/">
      <span class="best-name">{E(p['name'])}</span>
      <span class="best-tag">{E(p['tagline'])}</span>
      <span class="best-where">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))}</span>
      <span class="best-go">What they did right</span></a></li>""" for p in profs)
    best = f"""<section class="best" id="best" aria-labelledby="best-h">
  <figure class="best-pic reveal">{pic("patrika-gate-sky", "(max-width: 900px) 100vw, 40vw")}</figure>
  <div class="best-copy">
    <h2 id="best-h">The best, right now.</h2>
    <p class="best-sub">What each one did right, from public facts and its neighbourhood.</p>
    <ul class="best-list">{plist}</ul>
    <p class="best-note">Chosen by {E(au['name'])}. Never ranked by ratings, reviews or prices.</p>
  </div>
</section>""" if profs else ""

    # ---------- where does your café stand ----------
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
  <div class="bench-copy"><h2 id="bench-h">Where does your café stand?</h2>
    <p>Set your area and type and add what you know. Everything is computed in your browser from the published figures;
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

    # ---------- free updates, twice a month ----------
    sub = cfg.get("subscribe") or {}
    live = sub.get("provider") in ("google_form", "formspree") and sub.get("action")
    if live or mode == "draft":
        fields = sub.get("fields") or {}
        name_field = (f'<label class="field"><span>Your name</span><input type="text" name="{E(fields["name"])}" '
                      f'autocomplete="name" required maxlength="80"></label>') if fields.get("name") else ""
        updates = f"""<section class="updates" id="updates" aria-labelledby="updates-h">
  <div class="up-copy reveal">
    <h2 id="updates-h">The latest café trends, twice a month. Free.</h2>
    <p>Each update brings the newest findings on Jaipur's cafés straight to your WhatsApp: what customers reward, what is changing,
    and where the openings are. Short, and only when there is something new.</p>
  </div>
  <form class="up-form reveal" data-ui data-provider="{E(sub.get('provider', 'none'))}" data-action="{E(sub.get('action', ''))}" novalidate>
    {name_field}
    <label class="field"><span>Your WhatsApp number</span><input type="tel" name="{E(fields.get('contact', 'contact'))}" autocomplete="tel" inputmode="tel" required maxlength="16" placeholder="98290 12345"></label>
    <button class="btn" type="submit">Send me the updates</button>
    <p class="up-note">Used only to send these updates on WhatsApp. Never shared, never sold. Reply "stop" any time and you are off the list.</p>
    <p class="up-status" role="status" aria-live="polite"></p>
  </form>
</section>"""
        if not live:
            updates = updates.replace('<p class="up-note">', '<p class="up-note"><b>Draft: not connected yet, nothing is sent.</b> ')
    else:
        updates = ""

    # ---------- method: the statistics in plain words ----------
    listings = (I.get("method") or {}).get("listings")
    gloss = [
        ("Median", "The middle café when all are lined up. Unlike an average, one very busy café can't drag it."),
        ("Share", "Every headline figure is a share of cafés: out of every hundred, how many. It reads the same whether the group is fifty cafés or five hundred."),
        ("Interval", "I resample the cafés thousands of times (the bootstrap) and report the range most results fall in. A narrow range means a firm figure."),
        ("Shuffle test", "To ask whether a pattern could be luck, I shuffle the labels many times and count how often chance alone produces something as strong."),
        ("Rank correlation", "From −1 to +1: do cafés that are higher on one measure tend to be higher on another? Zero means no link."),
        ("Like for like", "A regression compares cafés that differ in one listed feature but share area, type and price level, so a feature doesn't get credit for what comes with it."),
        ("Clustering", "The Clark-Evans test compares the distance to the nearest café with what random scatter over the same ground would give."),
        ("Gini", "From 0 to 1: how unevenly something is shared. Zero, every café has the same; one, a single café has everything."),
    ]
    gl = "".join(f"<div><dt>{E(a)}</dt><dd>{E(b)}</dd></div>" for a, b in gloss)
    method = f"""<section class="method" id="method" aria-labelledby="method-h">
  <figure class="method-pic reveal">{pic("jantar-field", "(max-width: 760px) 100vw, 60vw")}</figure>
  <div class="method-copy"><h2 id="method-h">The methods, in plain words.</h2>
    <p>Three platforms describe the same café three ways. I read them on the same searches at every update, match them into one record,
    and publish only what holds for a group. These are the tools behind every figure above.</p></div>
  <dl class="gloss">{gl}</dl>
  <svg class="many" viewBox="0 0 1200 270" role="img" aria-label="Scattered platform listings compressed into one ordered record"
       data-listings="{listings or 0}" data-venues="{(I.get('method') or {}).get('venues', 0)}"></svg>
  <div class="method-cols">
    <p><b>Gather.</b> {E(T.get('method.listings', '—'))} platform listings in the latest update, from identical searches of Google Maps, Zomato and
    Swiggy, collected slowly and never past a block.</p>
    <p><b>Match.</b> One record of {E(T.get('scene.venues_tracked', ''))} venues with permanent IDs, matched by name and distance.</p>
    <p><b>Publish.</b> Aggregates only. Any group under {k} cafés is withheld; a café is named only to credit it, never next to its
    ratings, reviews or prices. <a href="data/insights.json" download>Download the figures</a>.</p>
  </div>
</section>"""

    # ---------- coffee, and the footer ----------
    contact = f"""<section class="contact" id="contact" aria-labelledby="contact-h">
  <h2 id="contact-h" class="reveal">Over a cup of coffee?</h2>
  <div class="c-copy reveal"><p>If you run a café in Jaipur, are about to open one, or just like thinking about them, I'd like to meet.
    Tell me what you'd want measured next.</p>
    <p class="c-links"><a class="btn" href="{mailto}">Say hello</a>
    <a href="{E(au.get('linkedin', ''))}" rel="noopener" target="_blank">{E(au['name'])} on LinkedIn</a></p></div>
</section>"""
    footer = f"""<footer class="foot">
  <a class="foot-name" href="#top">{E(site['title'])}</a>
  <p>{credits_line()}</p>
  <p>Updated {E(captured)} · groups under {k} cafés withheld · built {E(date.today().strftime('%-d %B %Y'))}</p>
</footer>"""

    banner = '<p class="draft-note">Draft build. Not for publishing.</p>' if mode == "draft" else ""
    imap = ('<script type="importmap">{"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.min.js"'
            '}}</script>')
    page = (head(site["title"], site["tagline"])
            + "\n" + imap + '\n<script type="module" src="relief.js"></script>\n<script src="tool.js" defer></script>\n</head>\n<body>\n'
            + banner + bar(site, updates=bool(updates)) + "\n<main>\n" + "\n".join([hero, intro, ch1, band, ch2, bench, pair, sundial, ch3, best, updates, method, contact])
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
    if (ROOT / "data/public/location_latest.json").exists():
        shutil.copy(ROOT / "data/public/location_latest.json", out / "data/location.json")
        (out / "location").mkdir(exist_ok=True)
        (out / "location" / "index.html").write_text(location_page(site, au, captured, k, mailto, bool(updates), banner))
    for p in profs:
        d = out / "cafes" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(profile(p, site, au, captured, core, k, mailto, ent))
    return out / "index.html"



def location_page(site, au, captured, k, mailto, updates, banner):
    """The location check: pick a spot, read its five-minute walk. Everything is computed from published aggregates."""
    pre = "../"
    return (head(f"Location check · {site['title']}", "Pick a spot in C-Scheme or Malviya Nagar and see, in plain words, what is within a five-minute walk.", pre)
            + '\n<script src="../location.js" defer></script>\n</head>\n<body>\n' + banner
            + bar(site, pre, home=False, updates=updates, here="Location check") + f"""
<main class="loc">
  <section class="loc-head">
    <div class="loc-head-copy"><h1 class="reveal">Check a location.</h1>
    <p class="loc-lede reveal">Pick a spot in C-Scheme or Malviya Nagar. I'll tell you, in plain words, what is within a five-minute walk:
    how many cafés, what kind, when they open, what they charge, and where the gaps are.</p></div>
    <figure class="loc-head-pic reveal" data-drift>{pic("patrika-gate-sky", "(max-width: 900px) 100vw, 40vw", eager=True, prefix=pre)}</figure>
  </section>
  <section class="loc-tool">
    <div class="loc-map">
      <div class="loc-ctrl" data-ui>
        <div class="seg-group" role="group" aria-label="Area"><button type="button" class="seg" data-area="0" aria-pressed="true">C-Scheme</button><button type="button" class="seg" data-area="1" aria-pressed="false">Malviya Nagar</button></div>
        <div class="seg-group loc-places" role="group" aria-label="Start from"></div>
      </div>
      <canvas class="loc-canvas" aria-label="Map of the area. Click a spot to read its five-minute walk."></canvas>
      <p class="loc-key">Darker ground: more cafés within a five-minute walk. Click anywhere on the map.</p>
    </div>
    <article class="loc-report" aria-live="polite"><p class="lr-k">Pick a spot to begin.</p></article>
  </section>
  <figure class="band reveal" data-drift>{pic("hawa-horses", "100vw", prefix=pre)}<figcaption>Outside the Hawa Mahal, in the old city.</figcaption></figure>
  <section class="loc-notes">
    <div class="reveal"><h2>How I read a spot.</h2>
    <p>Every spot on a 150-metre grid gets the cafés within 500 metres, about a five-minute walk. Shares and typical values appear only
    where {k} or more cafés are counted, rounded so no single café can be picked out. Offices, colleges, coaching centres, schools,
    gyms, hospitals, hotels, malls and big stores come from the same Google Maps searches I run for cafés, sorted by each place's own category
    and counted, never named. Bus stops and metro stations come from OpenStreetMap.</p></div>
    <div class="reveal"><h2>What it doesn't say.</h2>
    <p>It doesn't say a café here will do well or badly. Rent, footfall and what you serve matter more than any count. A count of
    places is not a count of people: one large office and one small clinic each count once. Residents are not counted yet.</p></div>
  </section>
  <section class="pair" aria-label="Mornings in Jaipur">
    <figure class="pair-a reveal" data-drift>{pic("kulhad-chai", "(max-width: 760px) 100vw, 40vw", prefix=pre)}<figcaption>Chai in clay kulhads: the city's first order of the day.</figcaption></figure>
    <figure class="pair-b reveal" data-drift>{pic("pink-haveli", "(max-width: 760px) 100vw, 55vw", prefix=pre)}<figcaption>A haveli in the Pink City, through neem leaves.</figcaption></figure>
  </section>
  <section class="contact"><h2 class="reveal">A second opinion?</h2><div class="c-copy reveal"><p>Tell me where you're looking. I'd like to
    walk the spot with you, over a cup of coffee.</p>
    <p class="c-links"><a class="btn" href="{mailto}">Say hello</a><a href="../#insights">Read the findings</a></p></div></section>
</main>
<footer class="foot"><a class="foot-name" href="../">{E(site['title'])}</a><p>{credits_line()}</p>
<p>Updated {E(captured)} · groups under {k} cafés withheld</p></footer>
</body>
</html>
""")


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
            + "\n</head>\n<body>\n" + bar(site, pre, home=False, updates=False) + f"""
<main class="pf">
  <section class="pf-head"><h1 class="reveal">{E(p['name'])}</h1><p class="pf-tag reveal">{E(p['tagline'])}</p>
    <p class="pf-where reveal">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))} · {len(p['outlets'])} {'café' if len(p['outlets']) == 1 else 'cafés'}</p></section>
  <section class="pf-sec"><h2>What they did right.</h2><ul class="story">{story}</ul>{notes}</section>
  <section class="pf-sec field-stone"><h2>Against the {E(core)} cafés I read.</h2><ul class="bands">{sig}</ul>
    <p class="pf-note">Area figures are aggregates. I never show a café's own ratings, review counts or prices.</p></section>
  <section class="pf-sec"><h2>What they offer.</h2><ul class="rare">{feats or '<li><span>Not listed.</span></li>'}</ul>{also}
    <table class="outlets"><caption>Cafés I read</caption><thead><tr><th>Area</th><th>Locality</th><th>Hours, first listed day</th><th>Listed on</th><th>Delivery</th></tr></thead><tbody>{rows}</tbody></table></section>
  <section class="contact"><h2>Over a cup of coffee?</h2><div class="c-copy"><p>If you run a café in Jaipur or are about to open one, I'd like to meet.</p>
    <p class="c-links"><a class="btn" href="{mailto}">Say hello</a><a href="{pre}#insights">Read the findings</a></p></div></section>
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
