"""Layer 1 (raw) -> layer 2 (public aggregates).

Reads the current snapshot and writes data/public/insights_<label>.json plus
insights_latest.json. Nothing venue-level leaves this script: every published
figure is an aggregate over at least `publish.min_group_size` venues, and every
suppressed cell is marked so the narrative cannot quote it.

Usage: python pipeline/build_insights.py [--config config.yaml]
"""
import argparse, json, re, statistics, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent

TYPE_LABEL = {
    "Coffee-led café": "Coffee-led",
    "Tea/chai café": "Tea & chai",
    "Bakery / patisserie café": "Bakery",
    "All-day café / café-restaurant": "All-day café",
}
AREA_SHORT = {"C-Scheme": "cs", "Malviya Nagar": "mn"}
# Trends reports whole numbers, so a 2019 yearly average under this many index
# points is mostly rounding noise; we show the line but don't quote a multiple.
LOW_BASE = 3

TYPE_SHORT = {"Coffee-led": "coffee", "Tea & chai": "tea", "Bakery": "bakery", "All-day café": "allday"}

AMENITIES = [  # Zomato "More info" highlights, as Y/N columns in Cafe_Master
    ("wifi", "Wi-Fi"), ("work_friendly", "Work-friendly"), ("outdoor_seating", "Outdoor seating"),
    ("breakfast", "Breakfast"), ("all_day_breakfast", "All-day breakfast"), ("rooftop", "Rooftop"),
    ("board_games_or_books", "Board games or books"), ("kid_friendly", "Kid-friendly"),
    ("pet_friendly", "Pet-friendly"), ("live_music_or_entertainment", "Live music"),
    ("vegan_options", "Vegan options"), ("gluten_free_options", "Gluten-free options"),
    ("valet_parking", "Valet parking"),
]


# ---------- loading ----------
PRIV = ROOT / "private"

# Zomato highlight text -> amenity flag (spec §6.8; same mapping as the baseline workbook)
AM_MAP = {
    "veg_only": ["Vegetarian only"], "serves_alcohol": ["Full bar available", "Cocktails", "Serves alcohol", "Wine and beer", "Resto bar"],
    "outdoor_seating": ["Outdoor seating"], "rooftop": ["Rooftop"], "wifi": ["Wifi"], "work_friendly": ["Work friendly"],
    "breakfast": ["Breakfast"], "all_day_breakfast": ["All day breakfast"], "smoking_area": ["Smoking area"],
    "board_games_or_books": ["Board games", "Books"], "live_music_or_entertainment": ["Live music", "Live entertainment"],
    "pet_friendly": ["Pet friendly"], "kid_friendly": ["Kid friendly"], "valet_parking": ["Valet parking"],
    "free_parking": ["Free parking"], "home_delivery": ["Home delivery"], "vegan_options": ["Vegan options"],
    "gluten_free_options": ["Gluten free options"],
}
METRICS = ["google_rating", "google_reviews", "zomato_dining_rating", "zomato_dining_reviews", "zomato_delivery_rating",
           "zomato_delivery_reviews", "swiggy_rating", "zomato_cost_for_two_inr", "zomato_cost_for_one_inr"]


def history():
    return json.load(open(PRIV / "master" / "index.json"))


def snapshot_rows(label):
    import csv
    with open(PRIV / "snapshots" / "snapshots.csv", newline="") as f:
        return {r["fig_id"]: r for r in csv.DictReader(f) if r["snapshot"] == label}


def _yn(v):
    return None if v is None else ("Y" if v else "N")


def frame(label):
    """One run as a venue-level DataFrame (private master + that run's snapshot rows)."""
    master = json.load(open(PRIV / "master" / f"master_{label}.json"))
    rows = snapshot_rows(label)
    out = []
    for r in master:
        s = rows.get(r["fig_id"])
        if r.get("merged_into") or s is None:
            continue
        hl = [h.strip().lower() for h in (r.get("z_highlights") or "").split(";")]
        d = {"fig_id": r["fig_id"], "name": r.get("name"), "area": r.get("area"), "fig_scope": r.get("fig_scope"),
             "fig_type": r.get("fig_type"), "status": s["status"], "seen": s["seen_this_run"] == "Y",
             "first_seen": r.get("first_seen"), "national_chain": "Y" if r.get("national_chain") else "N",
             "zomato_hours": r.get("z_hours"), "lat": pd.to_numeric(r.get("lat"), errors="coerce"),
             "lon": pd.to_numeric(r.get("lon"), errors="coerce"), "z_cuisines": r.get("z_cuisines"),
             "on_zomato": "Y" if r.get("src_zomato") else "N", "on_google": "Y" if r.get("g_cid") else "N",
             "on_swiggy": "Y" if r.get("sw_id") else "N", "on_magicpin": "Y" if r.get("mp_url") else "N"}
        for k, keys in AM_MAP.items():
            d[k] = _yn(any(h in [x.lower() for x in keys] for h in hl)) if r.get("src_zomato") else None
        if not r.get("src_zomato"):
            d["rooftop"] = "Y" if "rooftop" in ((r.get("name") or "") + (r.get("g_address") or "")).lower() else None
        for m in METRICS:
            d[m] = pd.to_numeric(s.get(m) or None, errors="coerce")
        out.append(d)
    return pd.DataFrame(out)


def load_snapshot(cfg, label=None):
    """Return (venues DataFrame, meta) for a run (default: the latest)."""
    idx = history()
    label = label or idx["labels"][-1]
    m = idx["meta"][label]
    meta = {"snapshot": label, "captured_on": m["captured_on"], "failed_sources": m.get("failed_sources", [])}
    return frame(label), meta


def load_trends(cfg):
    t = pd.read_excel(ROOT / cfg["baseline"]["research_xlsx"], "Google_Trends_Monthly")
    return t


# ---------- suppression ----------
class Publisher:
    def __init__(self, k, max_share):
        self.k, self.max_share = k, max_share
        self.suppressed = []

    def ok(self, n, where):
        if n < self.k:
            self.suppressed.append({"where": where, "n": int(n)})
            return False
        return True

    def dominance_ok(self, values, where):
        """For any published absolute total: no single venue above max_share of it."""
        tot = float(sum(values))
        if tot <= 0:
            return True
        if max(values) / tot > self.max_share:
            self.suppressed.append({"where": where, "reason": "dominance"})
            return False
        return True


# ---------- hours parsing (Zomato hours text) ----------
_T = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|noon|midnight)", re.I)


def _minutes(tok):
    m = _T.fullmatch(tok.strip())
    if not m:
        return None
    h, mi, suf = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
    if suf == "noon":
        return 12 * 60 + mi
    if suf == "midnight":
        return 0 + mi
    if suf == "am":
        h = 0 if h == 12 else h
    else:
        h = 12 if h == 12 else h + 12
    return h * 60 + mi


def parse_day_hours(text):
    """First day-group of a Zomato hours string -> (open_min, close_min) where close
    may exceed 1440 (past midnight). None if unparseable or closed."""
    if not isinstance(text, str) or ":" not in text:
        return None
    if "24 hours" in text.lower():
        return (0, 1440)
    groups = [g for g in text.split(";") if ":" in g and "closed" not in g.lower()]
    if not groups:
        return None
    spans = groups[0].split(":", 1)[1]
    segs = []
    for seg in spans.split(","):
        parts = re.split(r"\s*[–-]\s*", seg.strip())
        if len(parts) != 2:
            continue
        a, b = _minutes(parts[0]), _minutes(parts[1])
        if a is None or b is None:
            continue
        segs.append((a, b))
    if not segs:
        return None
    # a "12midnight – 1am" segment is yesterday's late session running on; skip it
    main = [s for s in segs if not (s[0] == 0 and s[1] <= 6 * 60)] or segs
    o, c = min(main, key=lambda s: s[0])
    c_main = max(s[1] if s[1] > s[0] else s[1] + 1440 for s in main)
    return (o, c_main)


# ---------- helpers ----------
def pct(x):
    return None if x is None else round(100 * x)


def med(xs):
    xs = [float(x) for x in xs if pd.notna(x)]
    return statistics.median(xs) if xs else None


def quantile(xs, q):
    s = pd.Series([x for x in xs if pd.notna(x)], dtype=float)
    return float(s.quantile(q)) if len(s) else None


# Distributions feed the in-browser benchmark tool. They are published only for groups
# of at least DIST_MIN venues and rounded, so no single listing's figure can be read back.
DIST_MIN = 20


def sig2(v):
    if v is None or v <= 0:
        return 0
    from math import floor, log10
    return int(round(v, -int(floor(log10(v))) + 1))


def deciles(xs, rnd):
    xs = [x for x in xs if pd.notna(x)]
    if len(xs) < DIST_MIN:
        return None
    return [rnd(quantile(xs, q / 10)) for q in range(1, 10)]


def fmt_pct(p):
    return "—" if p is None else f"{p}%"


def fmt_inr(v):
    return "—" if v is None else f"₹{int(round(v)):,}"


def fmt_hour(mins):
    if mins is None:
        return "—"
    h, m = divmod(int(round(mins)) % 1440, 60)
    suf = "am" if h < 12 else "pm"
    h12 = 12 if h % 12 == 0 else h % 12
    return f"{h12}{suf}" if m == 0 else f"{h12}:{m:02d}{suf}"


# ---------- insights ----------
def build(cfg, label=None):
    pub = Publisher(cfg["publish"]["min_group_size"], cfg["publish"]["max_single_venue_share"])
    k = pub.k
    df, meta = load_snapshot(cfg, label)
    df["type_base"] = df["fig_type"].str.split(" – ").str[-1].map(TYPE_LABEL)
    core = df[(df.fig_scope == "Core café") & df.status.str.startswith("Operating")].copy()
    areas = cfg["site"]["areas"]
    T = {}       # flat tokens the narrative may quote
    out = {"meta": {}, "insights": {}}

    # --- scene ---
    scene = {"venues_tracked": int(len(df)), "core_operating": int(len(core)), "by_area": {}, "by_type": {}}
    T["scene.venues_tracked"] = f"{len(df):,}"
    T["scene.core_cafes"] = f"{len(core):,}"
    for a in areas:
        n = int((core.area == a).sum())
        scene["by_area"][a] = n
        T[f"scene.core.{AREA_SHORT[a]}"] = f"{n:,}"
        for t in TYPE_LABEL.values():
            nt = int(((core.area == a) & (core.type_base == t)).sum())
            key = f"{a}|{t}"
            scene["by_type"][key] = nt if pub.ok(nt, f"scene {key}") else None
    chains = int((core.national_chain == "Y").sum())
    indep = 1 - chains / len(core)
    scene["independent_share"] = pct(indep)
    T["scene.independent_share"] = fmt_pct(pct(indep))
    out["insights"]["scene"] = scene

    # --- hours ---
    core["hrs"] = core["zomato_hours"].map(parse_day_hours)
    h = core[core.hrs.notna()].copy()
    h["open_m"] = h.hrs.map(lambda x: x[0])
    h["close_m"] = h.hrs.map(lambda x: x[1])
    hours = {"n": int(len(h)), "source": "Zomato listed hours (first listed day)", "by_type": {}, "curve": {}}
    if pub.ok(len(h), "hours all"):
        hours["open_by_8"] = pct((h.open_m <= 480).mean())
        hours["open_by_9"] = pct((h.open_m <= 540).mean())
        hours["median_open"] = fmt_hour(med(h.open_m))
        hours["open_past_midnight"] = pct((h.close_m > 1440).mean())
        T["hours.n"] = str(len(h))
        T["hours.open_by_8"] = fmt_pct(hours["open_by_8"])
        T["hours.open_by_9"] = fmt_pct(hours["open_by_9"])
        T["hours.median_open"] = hours["median_open"]
        T["hours.open_past_midnight"] = fmt_pct(hours["open_past_midnight"])
    for t in TYPE_LABEL.values():
        g = h[h.type_base == t]
        if pub.ok(len(g), f"hours {t}"):
            row = {"n": int(len(g)), "open_by_8": pct((g.open_m <= 480).mean()), "median_open": fmt_hour(med(g.open_m))}
            hours["by_type"][t] = row
            T[f"hours.open_by_8.{TYPE_SHORT[t]}"] = fmt_pct(row["open_by_8"])
            T[f"hours.median_open.{TYPE_SHORT[t]}"] = row["median_open"]
        else:
            hours["by_type"][t] = None
    # share of cafés open at each half hour, 6am -> 2am
    slots = list(range(6 * 60, 26 * 60 + 1, 30))
    for a in areas:
        g = h[h.area == a]
        if not pub.ok(len(g), f"hours curve {a}"):
            hours["curve"][a] = None
            continue
        hours["curve"][a] = {"n": int(len(g)), "points": [
            [s, pct(((g.open_m <= s) & (g.close_m > s)).mean())] for s in slots]}
    open_slots = list(range(6 * 60, 13 * 60 + 1, 30))
    hours["open_cdf"] = {"slots": open_slots, "all": [pct((h.open_m <= m).mean()) for m in open_slots]}
    for t in TYPE_LABEL.values():
        g = h[h.type_base == t]
        hours["open_cdf"][t] = [pct((g.open_m <= m).mean()) for m in open_slots] if len(g) >= DIST_MIN else None
    out["insights"]["hours"] = hours

    # --- prices (Zomato cost for two) ---
    price = {"source": "Zomato cost for two (₹, as listed)", "cells": []}
    for t in TYPE_LABEL.values():
        for a in areas:
            v = core[(core.type_base == t) & (core.area == a)]["zomato_cost_for_two_inr"].dropna()
            cell = {"type": t, "area": a, "n": int(len(v))}
            if pub.ok(len(v), f"price {t} {a}"):
                cell.update(median=med(v), p25=quantile(v, .25), p75=quantile(v, .75),
                            deciles=deciles(v, lambda x: int(round(x / 50) * 50)))
                T[f"price.{TYPE_SHORT[t]}.{AREA_SHORT[a]}"] = fmt_inr(cell["median"])
            price["cells"].append(cell)
    price["by_area"] = {}
    for a in areas:
        v = core[core.area == a]["zomato_cost_for_two_inr"].dropna()
        if pub.ok(len(v), f"price all {a}"):
            T[f"price.all.{AREA_SHORT[a]}"] = fmt_inr(med(v))
            price["by_area"][a] = {"n": int(len(v)), "deciles": deciles(v, lambda x: int(round(x / 50) * 50))}
    out["insights"]["price"] = price

    # --- attention concentration (Google review counts) ---
    att = {"source": "Google Maps review counts", "by_area": {}}
    for a in [None] + areas:
        g = core if a is None else core[core.area == a]
        v = g["google_reviews"].dropna().sort_values(ascending=False).tolist()
        key = a or "Both areas"
        if not v or not pub.ok(len(v) // 10, f"attention top-decile {key}"):
            att["by_area"][key] = None
            continue
        tot = sum(v)
        n = len(v)
        bounds = [round(i * n / 10) for i in range(11)]
        dec = [sum(v[bounds[i]:bounds[i + 1]]) / tot for i in range(10)]
        att["by_area"][key] = {"n": n, "deciles": [round(100 * d, 1) for d in dec],
                               "top10_share": pct(dec[0]), "median_reviews": int(round(med(v))),
                               "review_deciles": deciles(v, sig2)}
        sk = "all" if a is None else AREA_SHORT[a]
        T[f"attention.top10_share.{sk}"] = fmt_pct(pct(dec[0]))
        T[f"attention.median_reviews.{sk}"] = f"{att['by_area'][key]['median_reviews']:,}"
        T[f"attention.bottom_half_share.{sk}"] = fmt_pct(pct(sum(dec[5:])))
    out["insights"]["attention"] = att

    # --- ratings mature as reviews grow ---
    g = core[core.google_rating.notna() & core.google_reviews.notna()]
    buckets = [(0, 10, "Under 10"), (10, 50, "10–49"), (50, 200, "50–199"), (200, 1000, "200–999"), (1000, 10**9, "1,000+")]
    rm = {"source": "Google Maps rating and review count", "buckets": []}
    for lo, hi, lab in buckets:
        b = g[(g.google_reviews >= lo) & (g.google_reviews < hi)]
        row = {"label": lab, "n": int(len(b))}
        if pub.ok(len(b), f"ratings {lab}"):
            row["share_48_plus"] = pct((b.google_rating >= 4.8).mean())
            row["median_rating"] = med(b.google_rating)
            row["lo"], row["hi"] = lo, hi
            row["rating_deciles"] = deciles(b.google_rating, lambda x: round(x, 1))
        rm["buckets"].append(row)
    first, last = rm["buckets"][0], rm["buckets"][-1]
    T["ratings.share48.newest"] = fmt_pct(first.get("share_48_plus"))
    T["ratings.share48.established"] = fmt_pct(last.get("share_48_plus"))
    T["ratings.median.newest"] = f"{first['median_rating']:.1f}" if first.get("median_rating") else "—"
    T["ratings.median.established"] = f"{last['median_rating']:.1f}" if last.get("median_rating") else "—"
    out["insights"]["ratings"] = rm

    # --- amenities (Zomato highlights, venues on Zomato only) ---
    z = core[core.on_zomato == "Y"]
    am = {"source": "Zomato 'More info' highlights", "n": int(len(z)), "items": []}
    T["amenities.n"] = str(len(z))
    for col, lab in AMENITIES:
        yes = z[z[col] == "Y"]
        no = z[z[col] == "N"]
        row = {"key": col, "label": lab, "n_yes": None, "share": None}
        if pub.ok(len(yes), f"amenity {col}"):
            row.update(n_yes=int(len(yes)), share=pct(len(yes) / len(z)))
            ry, rn = yes.zomato_dining_reviews.dropna(), no.zomato_dining_reviews.dropna()
            if pub.ok(len(ry), f"amenity reviews {col} yes") and pub.ok(len(rn), f"amenity reviews {col} no"):
                row.update(median_reviews_yes=med(ry), median_reviews_no=med(rn))
            T[f"amenities.share.{col}"] = fmt_pct(row["share"])
        else:
            T[f"amenities.share.{col}"] = f"fewer than {k}"
        am["items"].append(row)
    out["insights"]["amenities"] = am

    # --- platform presence ---
    pp = {"source": "FIG cross-platform match", "shares": {}}
    src_of = {"on_google": "google_maps_ui", "on_zomato": "zomato", "on_swiggy": "swiggy", "on_magicpin": "magicpin"}
    for col, lab in [("on_google", "Google Maps"), ("on_zomato", "Zomato"), ("on_swiggy", "Swiggy"), ("on_magicpin", "magicpin")]:
        pp["shares"][lab] = None if src_of[col] in meta["failed_sources"] else pct((core[col] == "Y").mean())
        T[f"platforms.{col}"] = fmt_pct(pp["shares"][lab])
    out["insights"]["platforms"] = pp

    # --- demand (Google Trends, Rajasthan) ---
    tr = load_trends(cfg)
    tr = tr[tr.geo == "IN-RJ"]
    dem = {"source": "Google Trends, Rajasthan (index within each query set)", "sets": []}
    for qs, terms in [("cafe|coffee|cafe near me@IN-RJ", ["coffee", "cafe"]),
                      ("matcha|cold brew|specialty coffee@IN-RJ", ["matcha", "cold brew"])]:
        s = tr[tr.query_set == qs]
        years = sorted(int(y) for y in s.year.unique() if 2015 <= int(y) <= 2025)
        series = []
        for term in terms:
            ys = s[s.term == term].groupby("year").index_0_100.mean()
            pts = [[y, round(float(ys.get(y)), 1)] for y in years if y in ys.index]
            base, now = ys.get(2019), ys.get(2025)
            mult = round(float(now / base), 1) if base is not None and base >= LOW_BASE else None
            series.append({"term": term, "points": pts, "x2025_vs_2019": mult,
                           "low_base": bool(base is not None and base < LOW_BASE)})
            tk = term.replace(" ", "_")
            T[f"demand.{tk}.multiple"] = f"{mult}×" if mult else "—"
        dem["sets"].append({"query_set": qs, "series": series})
    out["insights"]["demand"] = dem

    # ---------- time machine, terrain, top-café profiles ----------
    import insights_extra as X
    idx = history()
    labels = [l for l in idx["labels"] if l <= meta["snapshot"]]
    frames = {l: (df if l == meta["snapshot"] else frame(l)) for l in labels}
    hist = []
    grids = {}
    for l in labels:
        m = idx["meta"][l]
        hist.append({"label": l, "captured_on": m["captured_on"], **X.summary(frames[l], m.get("failed_sources", []), k)})
        grids[l] = X.terrain(frames[l])
    peak = max(float(g.max()) for gs in grids.values() for g in gs.values()) or 1.0
    out["insights"]["history"] = hist
    out["insights"]["terrain"] = {"bbox": X.BBOX, "grid": list(X.GRID), "bandwidth_m": X.BANDWIDTH_M,
                                  "areas": {"C-Scheme": [26.9119, 75.8040], "Malviya Nagar": [26.8540, 75.8130]},
                                  "frames": {l: X.quantise(g, peak) for l, g in grids.items()}}
    T["history.runs"] = str(len(labels))
    if len(labels) >= 2:
        from datetime import date as _d
        pl, cl = labels[-2], labels[-1]
        days = (_d.fromisoformat(idx["meta"][cl]["captured_on"]) - _d.fromisoformat(idx["meta"][pl]["captured_on"])).days
        ch = X.changes(frames[pl], frames[cl], days, meta["failed_sources"], k, cfg["publish"]["max_single_venue_share"])
        ch["from"], ch["to"] = idx["meta"][pl]["captured_on"], idx["meta"][cl]["captured_on"]
        out["insights"]["changes"] = ch
        T["changes.days"] = str(days)
        T["changes.from"] = datetime.strptime(ch["from"], "%Y-%m-%d").strftime("%-d %B")
        T["changes.newly_listed"] = str(ch["newly_listed_total"])
        T["changes.not_found"] = str(ch["not_found"])
        T["changes.closed"] = str(ch["closed"])
        T["changes.churn_in"] = str(ch["search_churn_in"]); T["changes.churn_out"] = str(ch["search_churn_out"])
        mom = ch.get("momentum") or {}
        if mom.get("median_gain") is not None:
            T["changes.median_gain"] = f"{int(round(mom['median_gain'])):,}"
            T["changes.share_gaining"] = fmt_pct(mom["share_gaining"])
            if mom.get("dominance_ok"):
                T["changes.gain_per_week"] = f"{mom['gain_per_week']:,}"
            for a, v in (mom.get("by_area") or {}).items():
                if v:
                    T[f"changes.median_gain.{AREA_SHORT[a]}"] = f"{int(round(v['median_gain'])):,}"
                    T[f"changes.share_gaining.{AREA_SHORT[a]}"] = fmt_pct(v["share_gaining"])
            best = max(((t, v) for t, v in (mom.get("by_type") or {}).items() if v), key=lambda tv: tv[1]["share_gaining"], default=None)
            if best:
                T["changes.busiest_type"] = best[0].lower()
                T["changes.busiest_type_share"] = fmt_pct(best[1]["share_gaining"])

    tc = yaml.safe_load(open(ROOT / "content" / "top_cafes.yaml")).get("entries") or []
    kud = yaml.safe_load(open(ROOT / "content" / "kudos.yaml")).get("entries") or []
    master_rows = json.load(open(PRIV / "master" / f"master_{meta['snapshot']}.json"))
    amen_share = {a["key"]: a["share"] for a in out["insights"]["amenities"]["items"]}
    out["profiles"] = X.profiles(tc, master_rows, df, hours["open_cdf"], amen_share, kud, fmt_hour, dict(AMENITIES))

    out["meta"] = {
        **meta,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "areas": areas,
        "min_group_size": k,
        "base_population": "Operating core cafés (coffee-led, tea & chai, bakery, all-day café)",
        "suppressed": pub.suppressed,
    }
    T["meta.captured_on"] = datetime.strptime(meta["captured_on"], "%Y-%m-%d").strftime("%-d %B %Y")
    T["meta.min_group_size"] = str(k)
    out["tokens"] = T
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--label", help="a past run to rebuild; default the latest")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    out = build(cfg, args.label)
    pub_dir = ROOT / "data" / "public"
    pub_dir.mkdir(parents=True, exist_ok=True)
    label = out["meta"]["snapshot"]
    names = [f"insights_{label}.json"] + ([] if args.label and args.label != history()["labels"][-1] else ["insights_latest.json"])
    for name in names:
        (pub_dir / name).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"wrote insights for {label}: {len(out['tokens'])} tokens, {len(out['meta']['suppressed'])} suppressed cells")


if __name__ == "__main__":
    sys.exit(main())
