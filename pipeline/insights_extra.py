"""Time machine, density terrain and top-café profiles.

Everything here is either an aggregate (suppressed below min_group_size, dominance-checked
where a total is published) or, for top-café profiles, a fact about the café that is NOT a
platform rating, review count or price.
"""
import math
import statistics

import numpy as np
import pandas as pd

TYPE_LABEL = {"Coffee-led café": "Coffee-led", "Tea/chai café": "Tea & chai",
              "Bakery / patisserie café": "Bakery", "All-day café / café-restaurant": "All-day café"}

# terrain frame: both areas plus a margin (WGS84)
BBOX = {"lat": (26.832, 26.922), "lon": (75.786, 75.844)}
GRID = (96, 62)            # rows (north-south), cols (east-west): ~105 m cells
BANDWIDTH_M = 210


def _core(df):
    d = df[(df.fig_scope == "Core café") & df.status.str.startswith("Operating")].copy()
    d["type_base"] = d["fig_type"].str.split(" – ").str[-1].map(TYPE_LABEL)
    return d


def _confirmed(d):
    """On Zomato (whose area listings are close to a census) or on two platforms: not search churn."""
    n = sum((d[c] == "Y").astype(int) for c in ("on_zomato", "on_google", "on_swiggy", "on_magicpin"))
    return (d.on_zomato == "Y") | (n >= 2)


def _med(xs):
    xs = [float(x) for x in xs if pd.notna(x)]
    return statistics.median(xs) if xs else None


def summary(df, failed, k):
    """A small, comparable summary of one run (for the time machine)."""
    c = _core(df)
    cc = c[_confirmed(c)]
    s = {"core": int(len(c)), "core_confirmed": int(len(cc)),
         "by_area": {a: int((cc.area == a).sum()) for a in ("C-Scheme", "Malviya Nagar")},
         "by_type": {t: int((c.type_base == t).sum()) for t in TYPE_LABEL.values()},
         "independent_share": round(100 * (1 - (c.national_chain == "Y").mean()))}
    if "zomato" not in failed:
        s["median_price"] = {a: (_med(c[c.area == a].zomato_cost_for_two_inr) if c[c.area == a].zomato_cost_for_two_inr.notna().sum() >= k else None)
                             for a in ("C-Scheme", "Malviya Nagar")}
    return s


def changes(prev, cur, days, failed, k, max_share):
    """What moved between two runs. Aggregates only."""
    pc, cc = _core(prev), _core(cur)
    out = {"days": days}
    seen_prev = set(prev.loc[prev.seen].fig_id)
    new = cc[~cc.fig_id.isin(seen_prev)]
    newc = new[_confirmed(new)]
    out["newly_listed"] = {a: int((newc.area == a).sum()) for a in ("C-Scheme", "Malviya Nagar")}
    out["newly_listed_total"] = int(len(newc))
    out["search_churn_in"] = int(len(new) - len(newc))
    gone = pc[~pc.fig_id.isin(set(cc.fig_id))]
    gone_now = cur.set_index("fig_id").reindex(gone.fig_id)
    gconf = gone.set_index("fig_id")[_confirmed(gone).values]
    st = gone_now.status.fillna("")
    out["not_found"] = int((st.str.startswith("Not found") & st.index.isin(gconf.index)).sum())
    out["search_churn_out"] = int((st.str.startswith("Not found") & ~st.index.isin(gconf.index)).sum())
    out["closed"] = int((st.str.contains("closed")).sum())
    out["source_unavailable"] = int((st.str.startswith("Source unavailable")).sum())

    if "google_maps_ui" not in failed:
        both = pc[["fig_id", "google_reviews"]].merge(cc[["fig_id", "area", "type_base", "google_reviews"]], on="fig_id", suffixes=("_a", "_b"))
        both = both.dropna(subset=["google_reviews_a", "google_reviews_b"])
        both["gain"] = both.google_reviews_b - both.google_reviews_a
        both = both[both.gain >= 0]        # falls are platform resets; QA flags them for a human
        mom = {"n": int(len(both))}
        if len(both) >= k:
            mom["median_gain"] = _med(both.gain)
            mom["share_gaining"] = round(100 * (both.gain > 0).mean())
            mom["gain_per_week"] = round(both.gain.sum() / max(days, 1) * 7)
            mom["dominance_ok"] = bool(both.gain.max() <= max_share * max(both.gain.sum(), 1))
            mom["by_area"], mom["by_type"] = {}, {}
            for a in ("C-Scheme", "Malviya Nagar"):
                g = both[both.area == a]
                mom["by_area"][a] = ({"n": int(len(g)), "median_gain": _med(g.gain), "share_gaining": round(100 * (g.gain > 0).mean()),
                                      "median_growth_pct": _med((g.gain / g.google_reviews_a.clip(lower=1)) * 100)}
                                     if len(g) >= k else None)
            for t in TYPE_LABEL.values():
                g = both[both.type_base == t]
                mom["by_type"][t] = ({"n": int(len(g)), "median_gain": _med(g.gain), "share_gaining": round(100 * (g.gain > 0).mean()),
                                      "median_growth_pct": _med((g.gain / g.google_reviews_a.clip(lower=1)) * 100)}
                                     if len(g) >= k else None)
        out["momentum"] = mom

    # Price moves are not published: on 17 Oct 2026, 71% of cafés' Zomato cost-for-two moved by ±30–50% while
    # area medians stayed identical, which reads as a change in how Zomato computes the figure, not repricing.
    return out


def terrain(df):
    """Café density surface (operating core cafés with coordinates), counts only, normalised later."""
    c = _core(df).dropna(subset=["lat", "lon"])
    rows, cols = GRID
    lat0, lat1 = BBOX["lat"]; lon0, lon1 = BBOX["lon"]
    lats = np.linspace(lat1, lat0, rows)[:, None]          # north at the top
    lons = np.linspace(lon0, lon1, cols)[None, :]
    mlat = 111_320.0
    mlon = 111_320.0 * math.cos(math.radians(26.88))
    out = {}
    for key, sub in (("all", c), ("coffee", c[c.type_base == "Coffee-led"])):
        z = np.zeros((rows, cols))
        for la, lo in zip(sub.lat.astype(float), sub.lon.astype(float)):
            d2 = ((lats - la) * mlat) ** 2 + ((lons - lo) * mlon) ** 2
            z += np.exp(-d2 / (2 * BANDWIDTH_M ** 2))
        out[key] = z
    return out


def quantise(grids, peak):
    return {k: (np.clip(v / peak, 0, 1) * 255).round().astype(int).flatten().tolist() for k, v in grids.items()}


# ---------- top-café profiles ----------
def _open_close(hours):
    import re
    from build_insights import parse_day_hours
    p = parse_day_hours(hours)
    return p


def profiles(entries, master_rows, df, open_cdf, amen_share, kudos, fmt_clock, amen_label=None):
    """entries: content/top_cafes.yaml. master_rows: latest master (private). Facts + area context only."""
    by_id = {r["fig_id"]: r for r in master_rows}
    core = _core(df).dropna(subset=["lat", "lon"])
    out = []
    for e in entries:
        outlets = [by_id[f] for f in e["fig_ids"] if f in by_id and not by_id[f].get("merged_into")]
        if not outlets:
            continue
        o = []
        feats = set()
        for r in outlets:
            hl = [h.strip() for h in (r.get("z_highlights") or "").split(";") if h.strip() and not h.startswith("NO:")]
            feats |= set(hl)
            hrs = _open_close(r.get("z_hours"))
            near = None
            if r.get("lat"):
                la, lo = float(r["lat"]), float(r["lon"])
                d = np.sqrt(((core.lat.astype(float) - la) * 111_320) ** 2 + ((core.lon.astype(float) - lo) * 111_320 * math.cos(math.radians(26.88))) ** 2)
                near = {"cafes_500m": int((d <= 500).sum() - 1), "coffee_500m": int(((d <= 500) & (core.type_base == "Coffee-led")).sum() - (1 if TYPE_LABEL.get(r.get("fig_type", "").split(" – ")[-1]) == "Coffee-led" else 0))}
            o.append({"area": r.get("area"), "locality": (r.get("address") or r.get("g_address") or "").split(",")[0][:60],
                      "type": TYPE_LABEL.get((r.get("fig_type") or "").split(" – ")[-1], "Café"),
                      "opens": fmt_clock(hrs[0]) if hrs else None, "closes": fmt_clock(hrs[1]) if hrs else None,
                      "open_min": hrs[0] if hrs else None, "near": near,
                      "on": [p for p, f in (("Zomato", "src_zomato"), ("Google Maps", "g_cid"), ("Swiggy", "sw_id")) if r.get(f)],
                      "delivers": bool(r.get("sw_id")) or ("Does not offer Delivery" not in (r.get("z_delivery_note") or "") and bool(r.get("src_zomato")) and r.get("z_delivery_note") not in (None, "")),
                      "cuisines": r.get("z_cuisines") or r.get("sw_cuisines") or "",
                      "first_seen": r.get("first_seen")})
        # signals: each is a fact about the café, framed against an area aggregate
        signals = []
        early = [x for x in o if x["open_min"] is not None]
        if early:
            first = min(early, key=lambda x: x["open_min"])
            slots, cdf = open_cdf["slots"], open_cdf.get(first["type"]) or open_cdf["all"]
            i = max([j for j, s in enumerate(slots) if s <= first["open_min"]], default=None)
            if i is not None:
                signals.append({"k": "Mornings", "v": first["opens"],
                                "t": f"Opens at {first['opens']}: only {cdf[i]}% of {first['type'].lower()} cafés are open by then." if cdf[i] <= 50
                                else f"Opens at {first['opens']}, with the morning crowd."})
        flist = []
        for f in sorted(feats):
            key = {"Wifi": "wifi", "Work friendly": "work_friendly", "Outdoor seating": "outdoor_seating", "Breakfast": "breakfast",
                   "All day breakfast": "all_day_breakfast", "Rooftop": "rooftop", "Board games": "board_games_or_books",
                   "Kid friendly": "kid_friendly", "Pet friendly": "pet_friendly", "Live music": "live_music_or_entertainment",
                   "Vegan options": "vegan_options", "Gluten free options": "gluten_free_options", "Valet parking": "valet_parking"}.get(f)
            share = amen_share.get(key) if key else None
            flist.append({"f": (amen_label or {}).get(key, f), "share": share})
        rare = [x for x in flist if x["share"] is not None and x["share"] < 25]
        if rare:
            signals.append({"k": "Stands apart", "v": str(len(rare)),
                            "t": "Offers what few cafés list: " + ", ".join(f"{x['f']} ({x['share']}% of cafés)" for x in rare[:4]) + "."})
        if len(outlets) > 1:
            areas = sorted({x["area"] for x in o})
            signals.append({"k": "Reach", "v": str(len(outlets)),
                            "t": (f"{len(outlets)} cafés across {' and '.join(areas)}: a format that has travelled." if len(areas) > 1
                                  else f"{len(outlets)} cafés in {areas[0]}.")})
        dense = [x for x in o if x["near"]]
        if dense:
            busiest = max(dense, key=lambda x: x["near"]["cafes_500m"])
            signals.append({"k": "Neighbourhood", "v": str(busiest["near"]["cafes_500m"]),
                            "t": f"Shares its 500 m in {busiest['area']} with {busiest['near']['cafes_500m']} other cafés"
                                 + (f", {busiest['near']['coffee_500m']} of them coffee-led." if busiest['near']['coffee_500m'] else ".")})
        press = [x for x in kudos if x["id"] in e.get("kudos", []) and x.get("approved")]
        out.append({"slug": e["slug"], "name": e["name"], "tagline": e.get("tagline", ""), "story": e.get("story", []),
                    "notes": e.get("notes", ""), "outlets": o, "features": flist, "signals": signals,
                    "press": [{"praise": x["praise"], "sources": x["sources"]} for x in press]})
    return out
