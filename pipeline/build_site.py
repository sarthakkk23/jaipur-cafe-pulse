"""Layer 2 (public aggregates) + copy + kudos + web/ -> dist/ (the deployable site).

Reads only data/public/insights_latest.json, content/narrative.yaml,
content/kudos.yaml and config.yaml. Never touches raw data.

Usage: python pipeline/build_site.py [--mode draft|publish]
  draft   : pending kudos shown with a badge, draft banner on the page
  publish : pending kudos left out; refuses to build if the publish gate fails
"""
import argparse, html, json, re, shutil, sys
from urllib.parse import quote
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
import check_publish  # noqa: E402
import site_extra as SX  # noqa: E402
import charts as C  # noqa: E402
from charts import fmt_clock  # noqa: E402

E = html.escape
TYPES = ["Coffee-led", "Tea & chai", "Bakery", "All-day café"]


def fill(text, tokens):
    """Escape copy, then swap {{token}} for its value."""
    out = E(text)
    return re.sub(r"{{\s*([\w.]+)\s*}}", lambda m: f'<span class="fig">{E(str(tokens.get(m.group(1), "—")))}</span>', out)


ACCENT = re.compile(r"^\*(.+?)\*([.,!?:;]*)$")


def accent(word):
    """*word* in copy -> the serif italic accent."""
    m = ACCENT.match(word)
    return f'<em class="acc">{E(m.group(1))}</em>{E(m.group(2))}' if m else E(word)


def plain(text):
    return text.replace("*", "")


def spread_accents(text):
    """'*right now*.' -> '*right* *now*.' so each word can be accented on its own."""
    return re.sub(r"\*([^*]+)\*", lambda m: " ".join(f"*{w}*" for w in m.group(1).split()), text)


def words(text):
    """Headline split into masked words for the staggered reveal (plain text without JS)."""
    text = spread_accents(text)
    return " ".join(f'<span class="w"><span style="--d:{i}">{accent(w)}</span></span>' for i, w in enumerate(text.split()))


def sec_head(eyebrow, idx, sid=None):
    share = (f'<button class="share" type="button" data-share="#{sid}" aria-label="Copy a link to this section">'
             f'Share</button>') if sid else ""
    return (f'<div class="sec-head"><p class="eyebrow">{E(eyebrow)}</p><span class="idx">{share}({idx:02d})</span>'
            f'<span class="rule" data-scene="enter" aria-hidden="true"></span></div>')


def nice_date(iso):
    return date.fromisoformat(iso).strftime("%-d %B %Y")


# ---------------- page ----------------
def section_html(sec, tokens, chart_html, meta, source, n_note, alt, idx):
    body = "".join(f"<p>{fill(p, tokens)}</p>" for p in sec["body"])
    tk = sec["takeaways"]
    return f"""
<section id="{sec['id']}" class="insight alt{' first' if alt == 'first' else ''}" aria-labelledby="{sec['id']}-h">
  <div class="wrap">
    {sec_head(sec['eyebrow'], idx, sec['id'])}
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
        "hours_curve": (lambda: C.hours(ins, areas), "Zomato listed hours",
                        f"{ins['insights']['hours']['n']} cafés with listed hours"),
        "price_ranges": (lambda: C.prices(ins, areas, k), "Zomato cost for two", "cafés with a listed price"),
        "attention_deciles": (lambda: C.deciles(ins), "Google Maps review counts",
                              f"{ins['insights']['attention']['by_area']['Both areas']['n']} cafés on Google Maps"),
        "ratings_maturity": (lambda: C.ratings(ins, k), "Google Maps ratings and review counts", "cafés with a Google rating"),
        "amenities_bars": (lambda: C.amenities(ins, k), "Zomato highlights",
                           f"{ins['insights']['amenities']['n']} cafés on Zomato"),
        "demand_lines": (lambda: C.demand(ins), "Google Trends, Rajasthan", "index 0–100 within each query set"),
    }

    nav = ([("overview", "Overview"), ("timemachine", "What moved"), ("map", "Map")]
           + ([("top", "Top cafés")] if ins.get("profiles") else []) + [(s["id"], s["nav"]) for s in nar["sections"]]
           + [("benchmark", "Benchmark"), ("makers", "Makers"), ("method", "Method"), ("contact", "Contact")])
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

    ticker = "".join(f'<span class="tk"><b>{fill(h["value"], T)}</b> {E(h.get("short", ""))}</span><span class="tk-dot">✦</span>'
                     for h in nar["highlights"])
    n_pre = 2 + (1 if ins.get("profiles") else 0)      # time machine, map, top cafés come first
    extra_html = (SX.timemachine(ins, nar, fill, words, sec_head, 1, T) + SX.terrain(ins, nar, fill, words, sec_head, 2, T)
                  + SX.top_cards(ins, nar, fill, words, sec_head, 3, T))
    secs = "".join(section_html(s, T, charts[s["chart"]][0](), meta, charts[s["chart"]][1], charts[s["chart"]][2], "", n_pre + i + 1)
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
    ent = lambda t: "".join(f"&#{ord(c)};" for c in t)          # keeps the address out of naive scrapers
    mailto = ent(f"mailto:{au['email']}?subject={quote(au.get('email_subject', site['title']))}") if au.get("email") else ""
    li_icon = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.8 0 0 .77 0 1.73v20.54C0 23.23.8 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>')
    mail_icon = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" '
                 'd="M3 5.5h18v13H3zM3.5 6l8.5 7 8.5-7"/></svg>')
    contact = []
    if au.get("email"):
        contact.append(f'<a class="cta" href="{mailto}">{mail_icon}<span>Email me</span></a>')
    if au.get("linkedin"):
        contact.append(f'<a class="cta ghost" href="{E(au["linkedin"])}" rel="noopener" target="_blank">{li_icon}<span>Connect on LinkedIn</span></a>')
    copy_row = (f'<p class="copy-row reveal"><span class="addr">{ent(au["email"])}</span>'
                f'<button class="copy-btn" type="button" data-copy="{ent(au["email"])}">Copy address</button></p>') if au.get("email") else ""
    nav_cta = f'<a class="nav-cta" href="#contact">Get in touch</a>' if contact else ""
    foot_contact = " · ".join(x for x in [
        f'<a href="{mailto}">{ent(au["email"])}</a>' if au.get("email") else "",
        f'<a href="{E(au["linkedin"])}" rel="noopener" target="_blank">LinkedIn</a>' if au.get("linkedin") else ""] if x)
    if not contact and mode == "draft":
        contact.append('<span class="badge-draft">Add your LinkedIn and email in config.yaml</span>')

    tool_data = json.dumps({
        "areas": areas, "types": TYPES, "k": k, "captured_on": nice_date(meta["captured_on"]),
        "price": ins["insights"]["price"], "attention": ins["insights"]["attention"]["by_area"],
        "ratings": ins["insights"]["ratings"]["buckets"], "open_cdf": ins["insights"]["hours"]["open_cdf"],
        "amenities": [{"key": a["key"], "label": a["label"], "share": a["share"]} for a in ins["insights"]["amenities"]["items"]],
        "counts": ins["insights"]["scene"]["by_type"],
        "demand": {s["term"]: s["x2025_vs_2019"] for q in ins["insights"]["demand"]["sets"] for s in q["series"]},
        "email": au.get("email", ""), "subject": au.get("email_subject", site["title"]),
    }, ensure_ascii=False).replace("</", "<\\/")
    bm = nar["benchmark"]
    opts = "".join(f'<option value="{m}">{fmt_clock(m)}</option>' for m in range(360, 781, 30))
    chips = lambda name, vals: "".join(
        f'<label class="chip-in"><input type="radio" name="{name}" value="{E(v)}"{" checked" if i == 0 else ""}><span>{E(v)}</span></label>'
        for i, v in enumerate(vals))
    am_chips = "".join(f'<label class="chip-in"><input type="checkbox" name="am" value="{a["key"]}"><span>{E(a["label"])}</span></label>'
                       for a in ins["insights"]["amenities"]["items"])
    tool_html = f"""<section id="benchmark" class="tool" aria-labelledby="benchmark-h">
  <div class="wrap">
    {sec_head(bm['eyebrow'], n_pre + len(nar['sections']) + 1, 'benchmark')}
    <h2 id="benchmark-h" class="headline split">{words(bm['headline'])}</h2>
    <p class="lede-sm reveal">{fill(bm['lede'], T)}</p>
    <div class="tool-card reveal">
      <div class="seg" role="group" aria-label="Mode">
        <button type="button" class="seg-btn" data-mode="owner" aria-pressed="true">I run a café</button>
        <button type="button" class="seg-btn" data-mode="planner" aria-pressed="false">I'm opening one</button>
      </div>
      <form class="tool-form" autocomplete="off">
        <fieldset><legend>Area</legend><div class="chip-row">{chips("area", areas)}</div></fieldset>
        <fieldset><legend>Type</legend><div class="chip-row">{chips("type", TYPES)}</div></fieldset>
        <div class="owner-only field-grid">
          <label class="field"><span>Cost for two (₹)</span><input type="number" name="price" min="50" max="20000" step="10" inputmode="numeric" placeholder="700"></label>
          <label class="field"><span>Google reviews</span><input type="number" name="reviews" min="0" max="100000" step="1" inputmode="numeric" placeholder="120"></label>
          <label class="field"><span>Google rating</span><input type="number" name="rating" min="1" max="5" step="0.1" inputmode="decimal" placeholder="4.5"></label>
          <label class="field"><span>Opens at</span><select name="open"><option value="">Choose</option>{opts}</select></label>
        </div>
        <fieldset class="owner-only"><legend>What you offer</legend><div class="chip-row">{am_chips}</div></fieldset>
      </form>
      <div class="tool-results" aria-live="polite"></div>
      <p class="tool-note">Approximate positions from rounded group distributions (groups of {k}+ cafés; finer detail only for 20+).
      Snapshot of {nice_date(meta['captured_on'])}. Nothing you enter leaves this page.</p>
    </div>
  </div>
</section>"""

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
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#ffffff">
<script>document.documentElement.classList.add("js");setTimeout(function(){{if(!window.__pulse)document.documentElement.classList.remove("js","motion")}},3000)</script>
<link rel="stylesheet" href="assets/styles.css">
<script src="assets/app.js" defer></script>
<script type="importmap">{{"imports": {{"three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.min.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/"}}}}</script>
<script type="module" src="assets/scene3d.js"></script>
<script type="module" src="assets/terrain.js"></script>
<script src="assets/tool.js" defer></script>
<link rel="preload" href="assets/fonts/geist.woff2" as="font" type="font/woff2" crossorigin>
</head>
<body>
{banner}
<header class="localnav">
  <div class="localnav-inner">
    <a class="brand" href="#overview">{E(site['title'])}</a>
    <span class="asof">C-Scheme / Malviya Nagar · Snapshot {E(nice_date(meta['captured_on']))}</span>
    <div class="nav-right">
      <button class="grid-toggle" type="button" aria-pressed="false">Grid <span class="sw-on">On</span><span class="sw-off">Off</span></button>
      {nav_cta}
    </div>
  </div>
  <nav class="chips" aria-label="Sections">{nav_html}</nav>
</header>

<main>
<section id="overview" class="hero" aria-labelledby="hero-h">
  <div class="hero-glow" aria-hidden="true"></div>
  <canvas class="scene3d" data-scene3d="hero" aria-hidden="true"></canvas>
  <div class="wrap">
    <p class="eyebrow reveal">{E(hero['eyebrow'])}</p>
    <h1 id="hero-h" class="hero-title rise"><span class="glow-text">{" ".join(accent(w) for w in spread_accents(hero['headline']).split())}</span></h1>
    <p class="lede reveal">{fill(hero['lede'], T)}</p>
    <div class="hero-ctas reveal">
      <a class="cta" href="#benchmark">Benchmark your café</a>
      <a class="cta ghost" href="#mornings">Read the findings</a>
    </div>
    <p class="badge reveal">C-Scheme · Malviya Nagar · refreshed every two weeks</p>
  </div>
</section>

<div class="ticker" aria-hidden="true"><div class="ticker-track">{ticker}{ticker}</div></div>

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
{extra_html}
{secs}

{tool_html}

<section id="makers" class="makers" aria-labelledby="makers-h">
  <div class="wrap">
    {sec_head(nar['makers']['eyebrow'], n_pre + len(nar['sections']) + 2, 'makers')}
    <h2 id="makers-h" class="headline split">{words(nar['makers']['headline'])}</h2>
    <p class="lede-sm reveal">{fill(nar['makers']['lede'], T)}</p>
    <div class="maker-grid">{makers}</div>
  </div>
</section>

<section id="method" class="method alt" aria-labelledby="method-h">
  <div class="wrap">
    {sec_head(nar['method']['eyebrow'], n_pre + len(nar['sections']) + 3, 'method')}
    <h2 id="method-h" class="headline split">{words(nar['method']['headline'])}</h2>
    <div class="point-grid">{method}</div>
    <p class="download reveal"><a href="data/insights.json" download>Download this snapshot's aggregates (JSON)</a></p>
  </div>
</section>

<section id="contact" class="about" aria-labelledby="about-h">
  <div class="wrap about-grid">
    <div class="about-copy">
      {sec_head("Made in Jaipur", n_pre + len(nar['sections']) + 4)}
      <h2 id="about-h" class="headline split">{words("Let's talk over coffee.")}</h2>
      <p class="lede-sm reveal">I'm {E(au['name'])}. I'm building a dated, honest record of how Jaipur's cafés change.
      If you run a café, or you're about to open one, I'd love to hear what you'd want measured.</p>
      <div class="contact reveal">{''.join(contact)}</div>
      {copy_row}
    </div>
    <canvas class="scene3d about-3d" data-scene3d="coffee" aria-hidden="true"></canvas>
  </div>
</section>
</main>

<footer class="foot">
  <div class="wrap">
    <p>Independent research. Not affiliated with or endorsed by Google, Zomato, Swiggy or magicpin; platform names
    appear only to cite where public figures came from. Figures are aggregates of public listings captured on
    {E(nice_date(meta['captured_on']))}; groups smaller than {k} cafés are not shown.</p>
    <p class="foot-contact">{E(au['name'])}{' · ' + foot_contact if foot_contact else ''}</p>
    <p>Built {E(date.today().strftime('%-d %B %Y'))} · Snapshot {E(meta['snapshot'])}</p>
  </div>
</footer>
<div class="tip" role="tooltip" hidden></div>
<script type="application/json" id="pulse-data">{tool_data}</script>
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
    head_extra = ('<script type="importmap">{"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.min.js",'
                  ' "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/"}}</script>'
                  '<script type="module" src="../../assets/scene3d.js"></script>')
    pmeta = {"core": T.get("scene.core_cafes", ""), "captured": nice_date(meta["captured_on"])}
    for pr in ins.get("profiles") or []:
        d = out / "cafes" / pr["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(SX.profile_page(pr, ins, site, pmeta, head_extra,
                                                      nav_cta.replace('href="#contact"', 'href="../../#contact"'), mailto, k))
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
