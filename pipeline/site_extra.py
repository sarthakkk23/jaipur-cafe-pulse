"""HTML for the time machine, the 3D terrain map, top-café cards and profile pages."""
import html
import json
from datetime import date

E = html.escape


def _nice(iso):
    return date.fromisoformat(iso).strftime("%-d %b %Y")


def timemachine(ins, nar, fill, words, sec_head, idx, T):
    hist = ins["insights"].get("history") or []
    ch = ins["insights"].get("changes")
    tm = nar["timemachine"]
    stops = "".join(f'<button type="button" class="tm-stop" data-i="{i}" aria-pressed="{str(i == len(hist) - 1).lower()}">'
                    f'<span class="tm-dot"></span><span class="tm-date">{E(_nice(h["captured_on"]))}</span></button>'
                    for i, h in enumerate(hist))
    cards = "".join(f'<article class="tm-card reveal"><p class="tm-k">{E(c["k"])}</p><p class="tm-v">{fill(c["v"], T)}</p>'
                    f'<p class="tm-t">{fill(c["t"], T)}</p></article>' for c in (tm["cards"] if ch else tm.get("cards_first", [])))
    data = json.dumps(hist, ensure_ascii=False).replace("</", "<\\/")
    return f"""<section id="timemachine" class="timemachine" aria-labelledby="tm-h">
  <div class="wrap">
    {sec_head(tm['eyebrow'], idx, 'timemachine')}
    <h2 id="tm-h" class="headline split">{words(tm['headline'] if ch else tm['headline_first'])}</h2>
    <p class="lede-sm reveal">{fill(tm['lede'] if ch else tm['lede_first'], T)}</p>
    <div class="tm-rail reveal" role="group" aria-label="Snapshots">{stops}<span class="tm-line" aria-hidden="true"></span></div>
    <div class="tm-now reveal" aria-live="polite"></div>
    <div class="tm-cards">{cards}</div>
    <p class="tm-note">{fill(tm['note'], T)}</p>
  </div>
  <script type="application/json" id="tm-data">{data}</script>
</section>"""


def terrain(ins, nar, fill, words, sec_head, idx, T):
    hist = ins["insights"].get("history") or []
    tr = nar["terrain"]
    snaps = "".join(f'<label class="chip-in"><input type="radio" name="tr-snap" value="{E(h["label"])}"{" checked" if i == len(hist) - 1 else ""}>'
                    f'<span>{E(_nice(h["captured_on"]))}</span></label>' for i, h in enumerate(hist))
    data = json.dumps(ins["insights"]["terrain"]).replace("</", "<\\/")
    return f"""<section id="map" class="terrain" data-scene="pin" aria-labelledby="tr-h">
  <div class="pin tr-pin">
    <canvas class="tr-canvas" aria-hidden="true"></canvas>
    <div class="tr-labels" aria-hidden="true"></div>
    <div class="wrap tr-copy">
      {sec_head(tr['eyebrow'], idx, 'map')}
      <h2 id="tr-h" class="headline split">{words(tr['headline'])}</h2>
      <p class="lede-sm reveal">{fill(tr['lede'], T)}</p>
      <div class="tr-controls reveal">
        <div class="chip-row" role="radiogroup" aria-label="Which cafés">
          <label class="chip-in"><input type="radio" name="tr-kind" value="all" checked><span>All cafés</span></label>
          <label class="chip-in"><input type="radio" name="tr-kind" value="coffee"><span>Coffee-led</span></label>
        </div>
        <div class="chip-row" role="radiogroup" aria-label="Snapshot">{snaps}</div>
      </div>
      <p class="tr-legend reveal"><span class="tr-ramp"></span> Height and colour: how many cafés are nearby (counts only, smoothed over ~200 m).</p>
    </div>
  </div>
  <script type="application/json" id="terrain-data">{data}</script>
</section>"""


def top_cards(ins, nar, fill, words, sec_head, idx, T):
    profs = ins.get("profiles") or []
    if not profs:
        return ""
    tc = nar["top"]
    cards = "".join(f"""
      <a class="top-card reveal" href="cafes/{E(p['slug'])}/">
        <span class="top-glow" aria-hidden="true"></span>
        <span class="top-areas">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))}</span>
        <span class="top-name">{E(p['name'])}</span>
        <span class="top-tag">{E(p['tagline'])}</span>
        <span class="top-more">What they did right <span aria-hidden="true">→</span></span>
      </a>""" for p in profs)
    return f"""<section id="top" class="top" aria-labelledby="top-h">
  <div class="wrap">
    {sec_head(tc['eyebrow'], idx, 'top')}
    <h2 id="top-h" class="headline split">{words(tc['headline'])}</h2>
    <p class="lede-sm reveal">{fill(tc['lede'], T)}</p>
    <div class="top-grid">{cards}</div>
    <p class="tm-note">{fill(tc['note'], T)}</p>
  </div>
</section>"""


def profile_page(p, ins, site, meta, head_extra, nav_cta, mailto, k):
    def src(s):
        if not s.get("url"):
            return f'<span class="src">{E(s["publication"])}, {E(s["date"])}</span>'
        return f'<a class="src" href="{E(s["url"])}" rel="noopener" target="_blank">{E(s["publication"])}, {E(s["date"])}</a>'
    story = "".join(f'<li class="reveal"><p>{E(x["text"])}</p>{src(x["source"])}</li>' for x in p["story"])
    sig = "".join(f'<article class="res reveal"><p class="res-k">{E(s["k"])}</p><p class="res-big">{E(s["v"])}</p><p class="res-body">{E(s["t"])}</p></article>'
                  for s in p["signals"])
    feats = "".join(
        f'<li><span class="f-name">{E(f["f"])}</span>'
        + (f'<span class="f-bar"><i style="--w:{f["share"]}%"></i></span><span class="f-share">{f["share"]}% of cafés</span>'
           if f["share"] is not None else '<span class="f-share">rarely listed</span>') + "</li>"
        for f in sorted(p["features"], key=lambda f: (f["share"] is None, f["share"] or 0)))
    rows = "".join(f'<tr><td>{E(o["area"])}</td><td>{E(o["locality"] or "")}</td><td>{E(o["opens"] or "—")}–{E(o["closes"] or "—")}</td>'
                   f'<td>{E(", ".join(o["on"]))}</td><td>{"Yes" if o["delivers"] else "Dine-in"}</td></tr>' for o in p["outlets"])
    cuis = sorted({c.strip() for o in p["outlets"] for c in (o["cuisines"] or "").split(",") if c.strip()})
    notes = (f'<blockquote class="notes reveal">{E(p["notes"])}<cite>Visit notes, Sarthak Oberoi</cite></blockquote>'
             if p.get("notes") else '<p class="tm-note">Visit notes coming soon.</p>')
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(p['name'])} · {E(site['title'])}</title>
<meta name="description" content="{E(p['tagline'])} What {E(p['name'])} did right, from Jaipur Café Pulse.">
<meta name="color-scheme" content="light">
<script>document.documentElement.classList.add("js");setTimeout(function(){{if(!window.__pulse)document.documentElement.classList.remove("js","motion")}},3000)</script>
<link rel="stylesheet" href="../../assets/styles.css">
<script src="../../assets/app.js" defer></script>
{head_extra}
</head>
<body class="profile">
<header class="localnav">
  <div class="nav-bar">
    <a class="brand" href="../../"><span class="brand-mark" aria-hidden="true"></span>{E(site['title'])}</a>
    <nav class="nav-links" aria-label="Back"><a class="nl" href="../../#top">← All top cafés</a></nav>
    {nav_cta}
  </div>
  <div class="nav-progress" aria-hidden="true"><i></i></div>
</header>
<main>
<section class="hero pf-hero">
  <div class="hero-glow" aria-hidden="true"></div>
  <canvas class="scene3d" data-scene3d="coffee" aria-hidden="true"></canvas>
  <div class="wrap">
    <p class="eyebrow reveal">Top cafés in Jaipur right now</p>
    <h1 class="hero-title rise"><span class="glow-text">{E(p['name'])}</span></h1>
    <p class="lede reveal">{E(p['tagline'])}</p>
    <p class="badge reveal">{E(' · '.join(sorted({o['area'] for o in p['outlets']})))} · {len(p['outlets'])} {"café" if len(p['outlets']) == 1 else "cafés"}</p>
  </div>
</section>
<section class="pf-sec">
  <div class="wrap">
    <div class="sec-head"><p class="eyebrow">What they did right</p><span class="idx">(01)</span><span class="rule" data-scene="enter" aria-hidden="true"></span></div>
    <ol class="story">{story}</ol>
  </div>
</section>
<section class="pf-sec">
  <div class="wrap">
    <div class="sec-head"><p class="eyebrow">Signals</p><span class="idx">(02)</span><span class="rule" data-scene="enter" aria-hidden="true"></span></div>
    <p class="lede-sm reveal">How {E(p['name'])} stands against the {E(meta['core'])} cafés we track. Area figures are aggregates; we never show a café's own ratings, review counts or prices.</p>
    <div class="tool-results">{sig}</div>
  </div>
</section>
<section class="pf-sec">
  <div class="wrap">
    <div class="sec-head"><p class="eyebrow">What they offer</p><span class="idx">(03)</span><span class="rule" data-scene="enter" aria-hidden="true"></span></div>
    <ul class="feat-list reveal">{feats or '<li>Not listed.</li>'}</ul>
    {'<p class="tm-note">Menu tags: ' + E(", ".join(cuis)) + '</p>' if cuis else ''}
    <div class="table-view open reveal"><table><caption>Cafés we track</caption>
      <thead><tr><th>Area</th><th>Locality</th><th>Hours (first listed day)</th><th>Listed on</th><th>Delivery</th></tr></thead><tbody>{rows}</tbody></table></div>
  </div>
</section>
<section class="pf-sec">
  <div class="wrap">
    <div class="sec-head"><p class="eyebrow">From a visit</p><span class="idx">(04)</span><span class="rule" data-scene="enter" aria-hidden="true"></span></div>
    {notes}
    <div class="contact reveal"><a class="cta" href="{mailto}">Run a café? Get your own breakdown</a><a class="cta ghost" href="../../#benchmark">Benchmark your café</a></div>
  </div>
</section>
</main>
<footer class="foot"><div class="wrap">
  <p>Facts are from the sources linked and from public listings captured on {E(meta['captured'])}. Area comparisons are aggregates of {E(meta['core'])} cafés; groups smaller than {k} are not shown. Independent research, not affiliated with any platform.</p>
</div></footer>
</body>
</html>
"""
