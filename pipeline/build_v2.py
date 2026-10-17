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


SEO = {"base": "", "name": "", "author": {}}     # filled from config.yaml at build time


def asset(name):
    """name?v=<content hash>: a new deploy changes the address, so no browser keeps an old copy."""
    import hashlib
    src = ROOT / "web" / ("assets" if name == "tool.js" else "v2") / name
    return f"{name}?v={hashlib.sha1(src.read_bytes()).hexdigest()[:10]}" if src.exists() else name


def head(title, desc, prefix="", path="", ld=None):
    """Everything a search engine or a link preview reads: title, description, canonical address, Open Graph and
    Twitter cards, icons, and structured data (JSON-LD) describing the page."""
    guard = 'document.documentElement.classList.add("js");setTimeout(function(){if(!window.__pulse)document.documentElement.classList.remove("js","motion")},3000)'
    url = f"{SEO['base']}/{path}"
    image = f"{SEO['base']}/og.jpg"
    ld_tag = f'\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(url)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="author" content="{E(SEO['author'].get('name', ''))}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(SEO['name'])}">
<meta property="og:locale" content="en_IN">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{E(url)}">
<meta property="og:image" content="{E(image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{E(SEO['name'])}: Jaipur's cafés, measured. The Hawa Mahal's pink facade.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{E(image)}">
<link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{prefix}favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="{prefix}apple-touch-icon.png">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#f5f5f2">{ld_tag}
<script>{guard}</script>
<link rel="preload" href="{prefix}fonts/literata.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}{asset("v2.css")}">
<script src="{prefix}{asset("v2.js")}" defer></script>"""


CTX = {}   # site, author, mailto, dates and switches, filled at build time

# every page, in reading order: (path, label in the menu)
PAGES = [("insights/", "Insights"), ("location/", "Location check"), ("your-cafe/", "Your café"), ("best/", "The best"),
         ("method/", "Method"), ("updates/", "Free updates"), ("about/", "About")]


def pages_live():
    return [(u, l) for u, l in PAGES if u != "updates/" or CTX.get("updates")]


def bar(pre="", here=""):
    """The same menu on every page; on phones it folds into a menu button."""
    cur = ' aria-current="page"'
    links = "".join(f'<a href="{pre}{u}"{cur if l == here else ""}>{E(l)}</a>' for u, l in pages_live() if u != "about/")
    site = CTX["site"]
    return (f'<header class="bar"><a class="wordmark" href="{pre or "./"}">{E(site["title"])}</a>'
            f'<nav class="bar-links" aria-label="Main">{links}</nav>'
            f'<details class="menu"><summary aria-label="Open the menu">Menu</summary><nav class="menu-panel" aria-label="Main">'
            + "".join(f'<a href="{pre}{u}"{cur if l == here else ""}>{E(l)}</a>' for u, l in [("", "Home")] + pages_live())
            + f'</nav></details>'
            f'<a class="btn" href="{pre}about/#contact">Contact</a></header>')


def footer(pre=""):
    site, au = CTX["site"], CTX["au"]
    col = lambda title, items: f'<div><p class="ft-h">{E(title)}</p>' + "".join(f'<a href="{u}">{E(l)}</a>' for l, u in items) + "</div>"
    live = dict((l, u) for u, l in pages_live())
    explore = [(l, pre + live[l]) for l in ("Insights", "Location check", "Your café", "The best") if l in live]
    learn = [("Method", pre + "method/"), ("About", pre + "about/"), ("Download the figures", pre + "data/insights.json")]
    touch = ([("Free updates", pre + "updates/")] if "Free updates" in live else []) + [("Contact", pre + "about/#contact"), ("Email", CTX["mailto"]), ("LinkedIn", au.get("linkedin", ""))]
    return f"""<footer class="foot">
  <a class="foot-name" href="{pre or './'}">{E(site['title'])}</a>
  <div class="ft-cols">{col("Explore", explore)}{col("Learn", learn)}{col("Stay in touch", touch)}</div>
  <p>{credits_line()}</p>
  <p>Updated {E(CTX['captured'])} · groups under {CTX['k']} cafés withheld · built {E(date.today().strftime('%-d %B %Y'))}</p>
</footer>"""


def shell(path, title, desc, body, ld=None, here="", scripts="", main_cls="", crumb=None):
    """One page: head, menu, the page's own content, a breadcrumb with the next page, and the footer."""
    pre = "../" * path.count("/")
    site = CTX["site"]
    trail = [("Home", "", f"{SEO['base']}/")] + (crumb or ([(here, path, f"{SEO['base']}/{path}")] if here else []))
    graph = [{"@type": "WebPage", "@id": f"{SEO['base']}/{path}#page", "name": title, "url": f"{SEO['base']}/{path}", "inLanguage": "en-IN",
              "isPartOf": {"@id": f"{SEO['base']}/#site"}, "author": {"@id": f"{SEO['base']}/#author"}}]
    if len(trail) > 1:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                                                     for i, (n, _, u) in enumerate(trail)]})
    ld = ld or {"@context": "https://schema.org", "@graph": graph}
    order = [("", "Home")] + pages_live()
    paths = [u for u, _ in order]
    nxt = order[(paths.index(path) + 1) % len(order)] if path in paths else ("", "Home")
    where = " › ".join(f'<a href="{pre}{u}">{E(n)}</a>' for n, u, _ in trail[:-1]) + (f" › <span>{E(trail[-1][0])}</span>" if len(trail) > 1 else "")
    nav_end = (f'<nav class="trail" aria-label="Breadcrumb and next page"><p class="tr-where">{where}</p>'
               f'<a class="tr-next" href="{pre}{nxt[0]}"><span>Next</span>{E(nxt[1] if nxt[0] else "Back to the start")}</a></nav>') if path else ""
    return (head(title, desc, pre, path, ld) + scripts + "\n</head>\n<body>\n" + CTX["banner"] + bar(pre, here)
            + f'\n<main class="{main_cls}">\n' + body + "\n" + nav_end + "\n</main>\n" + footer(pre) + "\n</body>\n</html>\n")


def bio_lines(key):
    """Sarthak's own words from config.yaml, with the live café count filled in. 'Most with ten rivals' is only
    kept while the clustering finding still says most cafés have ten or more within a five-minute walk."""
    lines = [l.replace("{cafes}", CTX.get("core", "")) for l in (CTX["au"].get(key) or [])]
    if CTX.get("cluster_share") is not None and CTX["cluster_share"] < 50:
        lines = [l.replace("most with ten rivals a short walk away", "many with ten rivals a short walk away") for l in lines]
    return lines


def contact(pre="", title="Get in touch.", lead=None, bio=True):
    """The way to reach Sarthak, the same everywhere: a short introduction, then email and LinkedIn in plain view."""
    au = CTX["au"]
    intro = ("".join(f"<p>{E(line)}</p>" for line in bio_lines("bio_short"))
             + f'<p><a class="c-more" href="{pre}about/#who">More about me</a></p>') if bio else ""
    lead = lead or ("If something here is useful for your café, or you have a question about the data, you're welcome to get in touch. "
                    "Entirely your call.")
    email = au.get("email", "")
    return f"""<section class="contact" id="contact" aria-labelledby="contact-h">
  <div class="c-intro reveal"><h2 id="contact-h">{E(title)}</h2>{intro}<p>{E(lead)}</p></div>
  <div class="c-card reveal" data-ui>
    <p class="c-k">Email</p>
    <p class="c-email"><a href="{CTX['mailto']}">{CTX['ent'](email)}</a></p>
    <p class="c-acts"><a class="btn" href="{CTX['mailto']}">Write an email</a><button type="button" class="c-copy-btn" data-copy="{CTX['ent'](email)}">Copy address</button></p>
    <p class="c-k">LinkedIn</p>
    <p class="c-acts"><a class="btn btn-ln" href="{E(au.get('linkedin', ''))}" rel="noopener" target="_blank">{E(au['name'])} on LinkedIn</a></p>
    <p class="c-copied" role="status" aria-live="polite"></p>
  </div>
</section>"""


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
    SEO.update(base=site["base_url"].rstrip("/"), name=site["title"], author=au)
    ent = lambda t: "".join(f"&#{ord(c)};" for c in t)
    mailto = ent(f"mailto:{au['email']}?subject={quote(au.get('email_subject', site['title']))}") if au.get("email") else ""
    captured = nice(meta["captured_on"])
    core = T.get("scene.core_cafes", "")
    F = {f["id"]: f for f in I.get("findings") or []}
    lead_f = F.get("cluster") or next(iter(F.values()))
    sub = cfg.get("subscribe") or {}
    live = sub.get("provider") in ("google_form", "formspree") and sub.get("action")
    banner = '<p class="draft-note">Draft build. Not for publishing.</p>' if mode == "draft" else ""
    CTX.update(site=site, au=au, mailto=mailto, ent=ent, core=core, cluster_share=(F.get("cluster") or {}).get("value"), captured=captured, k=k, updates=bool(live or mode == "draft"), banner=banner)
    P = "../"                                   # every page except home sits one folder down

    # every finding, for the hero to rotate through (the headline numbers only; the page itself carries the rest)
    rot_data = json.dumps([{"id": f["id"], "value": f["value"], "unit": f["unit"], "headline": f["headline"]} for f in F.values()],
                          ensure_ascii=False).replace("</", "<\\/")

    # ---------- hero: the city's cafés as an object you can turn ----------
    terrain = json.dumps({"grid": I["terrain"]["grid"], "bbox": I["terrain"]["bbox"],
                          "all": I["terrain"]["frames"][meta["snapshot"]]["all"]}).replace("</", "<\\/")
    hero = f"""<section class="hero" id="top" aria-labelledby="hero-h">
  <figure class="hero-pic" aria-hidden="true">{pic("hawa-mahal-sky", "(max-width: 900px) 100vw, 55vw", eager=True)}</figure>
  <div class="hero-copy">
    <div class="hero-top">
      <h1 id="hero-h" class="hero-h">Jaipur's cafés, measured.</h1>
      <p class="hero-sub">I take my coffee seriously.<br>The data, more so.</p>
    </div>
    <div class="hero-fig" data-rot>
      <a class="rot-link" href="insights/#f-{E(lead_f['id'])}"><span class="hero-num">{lead_f['value']}<small>{E(lead_f['unit'])}</small></span>
      <span class="hero-cap">{E(lead_f['headline'])}</span></a>
      <div class="rot-ctrl" data-ui hidden><span class="rot-bar" aria-hidden="true"><i></i></span>
        <button type="button" class="rot-btn">Pause</button><span class="rot-count" aria-hidden="true"></span></div>
    </div>
    <script type="application/json" id="rot-data">{rot_data}</script>
    <div class="hero-foot"><p class="hero-act"><a class="btn" href="insights/">Read the {len(F)} insights</a>{'<a class="btn btn-ghost" href="updates/">Get them free on WhatsApp</a>' if CTX["updates"] else ""}</p>
    <p class="hero-meta">C-Scheme and Malviya Nagar · updated {E(captured)} · <a class="rot-how" href="insights/#f-{E(lead_f['id'])}">How I know</a></p></div>
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
  <p class="lead reveal">I read every café listing in Jaipur's C-Scheme and Malviya Nagar, {E(core)} cafés in all, so you don't have to.
  Then I tell you, in plain words, what the data says and what it doesn't: what customers reward, where the gaps are, and what a
  rating really means. It is updated often, so the trends are the latest ones.</p>
  <div class="cols">
    <p class="reveal"><b>Plain words.</b> Each finding is one sentence and one number: a share of cafés, and what it means for yours.</p>
    <p class="reveal"><b>What it doesn't say.</b> Every finding also says where it stops, so you never read more into it than is there.</p>
    <p class="reveal"><b>Strong coffee. Stronger evidence.</b> Resampling, like-for-like models and clustering tests run behind every
    figure, and each is graded <span class="ev" data-g="3"><i></i><i></i><i></i></span> strong, <span class="ev" data-g="2"><i></i><i></i><i></i></span> moderate
    or <span class="ev" data-g="1"><i></i><i></i><i></i></span> weak. You get the answer, not the jargon.</p>
    <p class="reveal"><b>Caffeinated, not biased.</b> Independent research by {E(au['name'])}. No platform or café pays to appear,
    and no café is ever criticised.</p>
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

    ch1 = chapter("insights", "Where attention goes.", "Reviews and ratings decide who gets found. Here is how they really behave, no sugar added.",
                  ["attention", "ratings", "platforms_rate", "delivery"])
    band = f"""<figure class="band reveal" data-drift>{pic("hawa-horses", "100vw", prefix=P)}<figcaption>Outside the Hawa Mahal, in the old city.</figcaption></figure>"""
    pair = f"""<section class="pair" aria-label="Mornings in Jaipur">
  <figure class="pair-a reveal" data-drift>{pic("kulhad-chai", "(max-width: 760px) 100vw, 40vw", prefix=P)}<figcaption>Chai in clay kulhads: the city's first order of the day.</figcaption></figure>
  <figure class="pair-b reveal" data-drift>{pic("pink-haveli", "(max-width: 760px) 100vw, 55vw", prefix=P)}<figcaption>A haveli in the Pink City, through neem leaves.</figcaption></figure>
</section>"""
    ch2 = chapter("offer", "What cafés offer.", "Good coffee. Bad assumptions. Let's fix that: what is common, what is rare, and what actually goes with being chosen.",
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
    loc_cta = """<a class="loc-cta reveal" href="../location/"><span class="loc-cta-h">Check a location.</span>
  <span class="loc-cta-p">Pick any spot in C-Scheme or Malviya Nagar and read its five-minute walk: how many cafés, what kind, and where the gaps are.</span>
  <span class="btn">Open the location check</span></a>"""
    ch3 = chapter("place", "Where they gather.", "Cafés pull towards each other, so choose your grounds carefully.",
                  ["cluster", "areas"], after=loc_cta)

    # ---------- the best right now ----------
    profs = ins.get("profiles") or []
    plist = "".join(f"""<li class="reveal"><a href="../cafes/{E(p['slug'])}/">
      <span class="best-name">{E(p['name'])}</span>
      <span class="best-tag">{E(p['tagline'])}</span>
      <span class="best-where">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))}</span>
      <span class="best-go">What they did right</span></a></li>""" for p in profs)
    best = f"""<section class="best" id="best" aria-labelledby="best-h">
  <figure class="best-pic reveal">{pic("patrika-gate-sky", "(max-width: 900px) 100vw, 40vw", eager=True, prefix=P)}</figure>
  <div class="best-copy">
    <h1 id="best-h" class="reveal">The best, right now.</h1>
    <p class="best-sub reveal">The cafés I would point a friend to right now. Each profile says what the café did right, from public facts and
    how it stands in its neighbourhood, never from its ratings, reviews or prices.</p>
    <ul class="best-list">{plist}</ul>
    <p class="best-note reveal">Chosen by {E(au['name'])}. Never ranked by ratings, reviews or prices.</p>
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
  <div class="bench-copy reveal"><h1 id="bench-h">Where does your café stand?</h1>
    <p>Set your area and type and add what you know. Everything is computed in your browser from the published figures;
    nothing you type leaves this page.</p>
    <div class="seg-row" role="group" aria-label="Mode" data-ui><button type="button" class="seg-btn" data-mode="owner" aria-pressed="true">I run a café</button>
    <button type="button" class="seg-btn" data-mode="planner" aria-pressed="false">I'm opening one</button></div>
  </div>
  <form class="tool-form reveal" autocomplete="off" data-ui>
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
    if live or mode == "draft":
        fields = sub.get("fields") or {}
        name_field = (f'<label class="field"><span>Your name</span><input type="text" name="{E(fields["name"])}" '
                      f'autocomplete="name" required maxlength="80"></label>') if fields.get("name") else ""
        updates = f"""<section class="updates" id="updates" aria-labelledby="updates-h">
  <div class="up-copy reveal">
    <h1 id="updates-h">Fresh findings, twice a month.</h1>
    <p>Free. Each update brings the newest findings on Jaipur's cafés straight to your WhatsApp: what customers reward, what is changing,
    and where the openings are. Short, and only when there is something new. No stale beans.</p>
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
  <figure class="method-pic reveal">{pic("jantar-field", "(max-width: 760px) 100vw, 60vw", eager=True, prefix=P)}</figure>
  <div class="method-copy"><h1 id="method-h">The methods, in plain words.</h1>
    <p>How the beans get counted. Three platforms describe the same café three ways. I read them on the same searches at every update, match them into one record,
    and publish only what holds for a group. These are the tools behind every figure on this site.</p></div>
  <dl class="gloss">{gl}</dl>
  <svg class="many" viewBox="0 0 1200 270" role="img" aria-label="Scattered platform listings compressed into one ordered record"
       data-listings="{listings or 0}" data-venues="{(I.get('method') or {}).get('venues', 0)}"></svg>
  <div class="method-cols method-cols-4">
    <p><b>Gather.</b> {E(T.get('method.listings', '—'))} platform listings in the latest update, from identical searches of Google Maps, Zomato and
    Swiggy, collected slowly and never past a block.</p>
    <p><b>Match.</b> One record of {E(T.get('scene.venues_tracked', ''))} venues with permanent IDs, matched by name and distance.</p>
    <p><b>Publish.</b> Aggregates only. Any group under {k} cafés is withheld; a café is named only to credit it, never next to its
    ratings, reviews or prices. <a href="../data/insights.json" download>Download the figures</a>.</p>
    <p><b>Check.</b> Before anything is published, every figure is re-counted from the source data by separate code. Each
    finding names its evidence grade and the number of cafés behind it.</p>
  </div>
</section>"""


    # ---------- home: what you'll find, and three findings to start with ----------
    cards = [("insights/", "Insights", f"{len(F)} findings on {core} cafés, each in one sentence, with what it means for yours."),
             ("location/", "Location check", "Pick any spot and read its five-minute walk: cafés, gaps, and who is around to buy coffee."),
             ("your-cafe/", "Your café", "Set your area, type and numbers; see where you stand. Nothing you type leaves the page."),
             ("best/", "The best", "The cafés doing it best right now, and what each one did right."),
             ("method/", "Method", "How the beans get counted: the statistics in plain words, and the data to download.")]
    if CTX["updates"]:
        cards.append(("updates/", "Free updates", "Fresh findings on WhatsApp, twice a month. No stale beans."))
    explore = f"""<section class="explore" aria-labelledby="explore-h">
  <header class="ch-head reveal"><h2 id="explore-h">Find what you came for.</h2><p>Every part of the record, one click away. Start with the findings, or go straight to your street.</p></header>
  <ul class="best-list ex-list">{"".join(f'<li class="reveal"><a href="{u}"><span class="best-name">{E(t)}</span><span class="ex-p">{E(d)}</span><span class="best-go">Open</span></a></li>' for u, t, d in cards)}</ul>
</section>"""
    picks = [F[x] for x in ("attention", "platforms_rate", "delivery") if x in F]
    teasers = f"""<section class="teasers" aria-labelledby="teasers-h">
  <h2 id="teasers-h" class="reveal">Three findings to start with.</h2>
  <div class="tz-grid">{"".join(f'<a class="tz reveal" href="insights/#f-{E(f["id"])}"><span class="tz-num">{f["value"]}<small>{E(f["unit"])}</small></span><span class="tz-head">{E(f["headline"])}</span></a>' for f in picks)}</div>
</section>"""

    # ---------- insights: the findings, with a jump bar ----------
    chapters = [("insights-attention", "Where attention goes"), ("offer", "What cafés offer"), ("day", "When they open"), ("place", "Where they gather")]
    ins_head = f"""<section class="page-head">
  <h1 class="reveal">What the data says.</h1>
  <p class="page-lede reveal">{len(F)} findings on {E(core)} cafés in C-Scheme and Malviya Nagar. Each is one sentence and one number,
  with what it means for you, what it doesn't say, and how I know.</p>
  <nav class="jump reveal" aria-label="On this page">{"".join(f'<a href="#{a}">{E(t)}</a>' for a, t in chapters)}</nav>
</section>"""
    ch1 = ch1.replace('id="insights"', 'id="insights-attention"').replace('aria-labelledby="insights-h"', 'aria-labelledby="insights-attention-h"').replace('id="insights-h"', 'id="insights-attention-h"')

    # ---------- about ----------
    about = f"""<section class="page-head about-head">
  <h1 class="reveal">Caffeinated, not biased.</h1>
  <p class="page-lede reveal">Jaipur Café Index is independent research by {E(au['name'])}, based in Jaipur. I read every café listing in
  C-Scheme and Malviya Nagar, match them into one record, and publish what the data says in plain words, updated twice a month.</p>
</section>
<section class="who" id="who" aria-labelledby="who-h">
  <div class="who-side">
    <h2 id="who-h" class="reveal">Who's behind it.</h2>
    <picture class="who-photo reveal"><source type="image/webp" srcset="{P}img/sarthak-street-400.webp 400w, {P}img/sarthak-street-800.webp 800w" sizes="(max-width: 900px) 240px, 380px">
    <img src="{P}img/sarthak-street-800.jpg" srcset="{P}img/sarthak-street-400.jpg 400w, {P}img/sarthak-street-800.jpg 800w" sizes="(max-width: 900px) 240px, 380px" width="800" height="1542" alt="{E(au['name'])}" loading="lazy" decoding="async"></picture>
  </div>
  <div class="who-text">{"".join(f'<p class="reveal">{E(l)}</p>' for l in bio_lines("bio_long"))}</div>
</section>
<section class="rules">
  <h2 class="reveal">The house rules.</h2>
  <ul class="best-list rule-list">
    <li class="reveal"><div class="rule-row"><span class="best-name">Aggregates only.</span><span class="ex-p">Figures describe groups of cafés, never one café. Any group under {k} is withheld.</span></div></li>
    <li class="reveal"><div class="rule-row"><span class="best-name">Praise, never criticism.</span><span class="ex-p">A café is named only to credit it. No café's ratings, reviews or prices appear here.</span></div></li>
    <li class="reveal"><div class="rule-row"><span class="best-name">Nobody pays.</span><span class="ex-p">No platform or café pays for this record or to appear in it.</span></div></li>
    <li class="reveal"><div class="rule-row"><span class="best-name">Every number checked.</span><span class="ex-p">Each figure is re-counted from the source data by separate code before it is published.</span></div></li>
  </ul>
</section>
{contact(P, bio=False)}"""

    # ---------- the pages ----------
    imap = ('<script type="importmap">{"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.min.js"'
            '}}</script>')
    person = {"@type": "Person", "@id": f"{SEO['base']}/#author", "name": au["name"], "description": (bio_lines("bio_short") or [""])[0], "url": au.get("linkedin", ""),
              "email": f"mailto:{au.get('email', '')}", "image": f"{SEO['base']}/img/sarthak-street-800.jpg",
              "sameAs": [au.get("linkedin", "")], "knowsAbout": ["Café market research", "Data analysis", "Jaipur"]}
    first = (ins.get("insights", {}).get("history") or [{}])[0].get("captured_on") or meta["captured_on"]
    dataset = {"@type": "Dataset", "name": f"{site['title']}: cafés in C-Scheme and Malviya Nagar, Jaipur",
         "description": (f"Independent, aggregate data on {core} operating cafés in C-Scheme and Malviya Nagar, Jaipur: opening hours, "
                         "cost for two, review concentration, ratings by platform, menus, platform reach and clustering. "
                         f"Groups under {k} cafés are withheld; no café's own ratings, reviews or prices are published."),
         "url": f"{SEO['base']}/insights/", "creator": {"@id": f"{SEO['base']}/#author"}, "isAccessibleForFree": True,
         "keywords": ["cafés in Jaipur", "C-Scheme cafés", "Malviya Nagar cafés", "Jaipur café market", "opening a café in Jaipur", "coffee shops Jaipur"],
         "temporalCoverage": f"{first}/{meta['captured_on']}", "dateModified": meta["captured_on"],
         "spatialCoverage": {"@type": "Place", "name": "C-Scheme and Malviya Nagar, Jaipur, Rajasthan, India",
                             "geo": {"@type": "GeoShape", "box": "26.836 75.7915 26.9185 75.839"}},
         "variableMeasured": ["Share of cafés open by 8am", "Typical cost for two", "Share of Google reviews held by the top tenth of cafés",
                              "Share of cafés rated 4.8 or more by review count", "Google against Zomato rating", "Delivery against dine-in reviews",
                              "Cuisines per menu", "Platforms per café", "Cafés within a five-minute walk"],
         "distribution": {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SEO['base']}/data/insights.json"}}
    ld_home = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f"{SEO['base']}/#site", "name": site["title"], "url": f"{SEO['base']}/", "inLanguage": "en-IN",
         "description": site["tagline"], "publisher": {"@id": f"{SEO['base']}/#author"}}, person, dataset]}
    # old one-page links (#insights, #best …) still land somewhere sensible
    legacy = ('<script>(function(){var m={"#insights":"insights/","#offer":"insights/#offer","#day":"insights/#day","#place":"insights/#place",'
              '"#best":"best/","#benchmark":"your-cafe/","#method":"method/","#updates":"updates/","#contact":"about/#contact"};'
              'var h=location.hash;if(m[h])location.replace(m[h]);else if(/^#f-/.test(h))location.replace("insights/"+h);})();</script>')

    out = ROOT / "dist"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web" / "v2", out)
    shutil.copy(ROOT / "web" / "assets" / "tool.js", out / "tool.js")
    (out / "data").mkdir(exist_ok=True)
    shutil.copy(ROOT / "data/public/insights_latest.json", out / "data/insights.json")
    (out / ".nojekyll").write_text("")

    def write(path, html):
        d = out / path
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html)

    write("", shell("", site.get("seo_title", site["title"]), site["tagline"],
                    "\n".join([hero, intro, explore, teasers, contact("")]), ld=ld_home,
                    scripts="\n" + imap + '\n<script type="module" src="' + asset("relief.js") + '"></script>\n' + legacy))
    ins_ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": f"{SEO['base']}/insights/#page", "name": "What the data says about Jaipur's cafés", "url": f"{SEO['base']}/insights/",
         "inLanguage": "en-IN", "isPartOf": {"@id": f"{SEO['base']}/#site"}, "author": {"@id": f"{SEO['base']}/#author"}},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SEO['base']}/"},
                                                         {"@type": "ListItem", "position": 2, "name": "Insights", "item": f"{SEO['base']}/insights/"}]},
        dataset]}
    write("insights/", shell("insights/", f"What the data says about Jaipur's cafés · {site['title']}",
                             f"{len(F)} findings on {core} cafés in C-Scheme and Malviya Nagar, Jaipur: reviews, ratings, delivery, prices, menus, hours and clustering, in plain words.",
                             "\n".join([ins_head, ch1, band, ch2, pair, sundial, ch3]), ld=ins_ld, here="Insights"))
    write("your-cafe/", shell("your-cafe/", f"Compare your café with Jaipur's · {site['title']}",
                              "Set your area, type and numbers and see where your café stands among cafés in C-Scheme and Malviya Nagar, Jaipur. Computed in your browser.",
                              bench,
                              here="Your café", scripts=f'\n<script src="../{asset("tool.js")}" defer></script>', main_cls="main-bench"))
    if best:
        write("best/", shell("best/", f"The best cafés in Jaipur right now · {site['title']}",
                             "The cafés in C-Scheme and Malviya Nagar doing it best right now, and what each one did right, from public facts.",
                             best, here="The best"))
    write("method/", shell("method/", f"How the numbers are made · {site['title']}",
                           "The statistics behind Jaipur Café Index in plain words: medians, intervals, shuffle tests, like-for-like models and clustering. Data to download.",
                           method, here="Method"))
    if updates:
        write("updates/", shell("updates/", f"Free café insights on WhatsApp · {site['title']}",
                                "Fresh findings on Jaipur's cafés, twice a month, free on WhatsApp. Short, and only when there is something new.",
                                updates, here="Free updates", main_cls="main-updates"))
    write("about/", shell("about/", f"About · {site['title']}",
                          f"Who is behind Jaipur Café Index: {au['name']}, who grew up in Jaipur and studies how businesses win and lose in its markets. How to get in touch.",
                          about, here="About"))
    if (ROOT / "data/public/location_latest.json").exists():
        shutil.copy(ROOT / "data/public/location_latest.json", out / "data/location.json")
        write("location/", location_page(site, au, captured, k, mailto))
    for p in profs:
        write(f"cafes/{p['slug']}/", profile(p, site, au, captured, core, k, mailto, ent))

    urls = ["", "insights/", "location/", "your-cafe/"] + (["best/"] if best else []) + ["method/"] + (["updates/"] if updates else []) + ["about/"]
    urls += [f"cafes/{p['slug']}/" for p in profs]
    prio = {"": "1.0", "insights/": "0.9", "location/": "0.9", "your-cafe/": "0.8", "best/": "0.8"}
    (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SEO['base']}/{u}</loc><lastmod>{meta['captured_on']}</lastmod><changefreq>weekly</changefreq>"
                  f"<priority>{prio.get(u, '0.6')}</priority></url>\n" for u in urls) + "</urlset>\n")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SEO['base']}/sitemap.xml\n")
    root = "/" + SEO["base"].split("/", 3)[-1] + "/" if SEO["base"].count("/") > 2 else "/"
    (out / "404.html").write_text(head(f"Page not found · {site['title']}", "This page wandered off for a coffee.", root)
        .replace('content="index, follow, max-image-preview:large"', 'content="noindex"')
        + '\n</head>\n<body>\n<main class="nf"><h1>This page wandered off for a coffee.</h1>'
        + f'<p>It isn\'t here, but the findings are. <a href="{root}insights/">Read the insights</a> or <a href="{root}">go home</a>.</p></main>\n</body>\n</html>\n')
    return out / "index.html"


def location_page(site, au, captured, k, mailto):
    """The location check: pick a spot, read its five-minute walk. Everything is computed from published aggregates."""
    pre = "../"
    body = f"""
  <section class="loc-head">
    <div class="loc-head-copy"><h1 class="reveal">Check a location.</h1>
    <p class="loc-lede reveal">Know your grounds before you grind. Pick a spot in C-Scheme or Malviya Nagar, Jaipur, and I'll tell you,
    in plain words, what is within a five-minute walk: how many cafés, what kind, who is around to buy coffee, and where the gaps are.</p></div>
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
""" + contact(pre, "Questions about a spot?", "If you're weighing a location and want to talk it through, you're welcome to get in touch.", bio=False)
    return shell("location/", f"Where to open a café in Jaipur · {site['title']}",
                 "Opening a café in Jaipur? Pick any spot in C-Scheme or Malviya Nagar: see the cafés, the gaps and who is around to buy coffee.",
                 body, here="Location check", scripts=f'\n<script src="../{asset("location.js")}" defer></script>', main_cls="loc")


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
    slug_url = f"{SEO['base']}/cafes/{p['slug']}/"
    body = f"""
  <section class="pf-head"><h1 class="reveal">{E(p['name'])}</h1><p class="pf-tag reveal">{E(p['tagline'])}</p>
    <p class="pf-where reveal">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))} · {len(p['outlets'])} {'café' if len(p['outlets']) == 1 else 'cafés'}</p></section>
  <section class="pf-sec"><h2>What they did right.</h2><ul class="story">{story}</ul>{notes}</section>
  <section class="pf-sec field-stone"><h2>Against the {E(core)} cafés I read.</h2><ul class="bands">{sig}</ul>
    <p class="pf-note">Area figures are aggregates. I never show a café's own ratings, review counts or prices.</p></section>
  <section class="pf-sec"><h2>What they offer.</h2><ul class="rare">{feats or '<li><span>Not listed.</span></li>'}</ul>{also}
    <table class="outlets"><caption>Cafés I read</caption><thead><tr><th>Area</th><th>Locality</th><th>Hours, first listed day</th><th>Listed on</th><th>Delivery</th></tr></thead><tbody>{rows}</tbody></table></section>
""" + contact(pre, bio=False) + f"""
  <p class="pf-src">Facts from the sources linked and from public listings read on {E(captured)}.</p>"""
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "name": f"{p['name']}: what they did right", "url": slug_url, "inLanguage": "en-IN",
         "isPartOf": {"@id": f"{SEO['base']}/#site"}, "author": {"@id": f"{SEO['base']}/#author"},
         "about": {"@type": "CafeOrCoffeeShop", "name": p["name"],
                   "address": {"@type": "PostalAddress", "addressLocality": "Jaipur", "addressRegion": "Rajasthan", "addressCountry": "IN"}}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SEO['base']}/"},
            {"@type": "ListItem", "position": 2, "name": "The best", "item": f"{SEO['base']}/best/"},
            {"@type": "ListItem", "position": 3, "name": p["name"], "item": slug_url}]}]}
    return shell(f"cafes/{p['slug']}/", f"{p['name']}, Jaipur: what they did right · {site['title']}",
                 f"{p['tagline']} What {p['name']} did right, from public facts and its neighbourhood in Jaipur.",
                 body, ld=ld, here="The best", main_cls="pf",
                 crumb=[("The best", "best/", f"{SEO['base']}/best/"), (p["name"], f"cafes/{p['slug']}/", slug_url)])


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
