"""Location check: what lies within a five-minute walk of any spot in C-Scheme or Malviya Nagar.

Spots sit on a 150 m grid over each area. For each spot this counts the operating cafés within 500 m and,
only where that count is k or more, their type mix, the share open by 8am, the typical cost for two and the
typical Google reviews. Shares are rounded to the nearest 5% and medians to round steps, so neighbouring
spots that differ by one café cannot be subtracted to read that café. No venue is named or located.
Context from OpenStreetMap (ODbL): hotels and bus stops within the walk, and the nearest operating metro station.
"""
import json
from pathlib import Path

import numpy as np

M_LAT = 111_320.0
M_LON = 111_320.0 * np.cos(np.radians(26.88))
RADIUS = 500
SPACING = 150
TYPES = ["Coffee-led", "Tea & chai", "Bakery", "All-day café"]
# the study areas, as in private/process/consolidate.py
BOX = {"C-Scheme": (26.899, 26.9185, 75.7915, 75.8145), "Malviya Nagar": (26.836, 26.87, 75.797, 75.839)}
# named spots to start from, all positions from OpenStreetMap
PLACES = {
    "C-Scheme": [["Ashok Marg", 26.91337, 75.81098], ["Sardar Patel Marg", 26.90328, 75.79342], ["Prithviraj Road", 26.90518, 75.8111],
                 ["Crystal Palm", 26.90335, 75.79246], ["Central Park", 26.90421, 75.81032]],
    "Malviya Nagar": [["World Trade Park", 26.85397, 75.80524], ["Gaurav Tower", 26.85564, 75.80658], ["MNIT", 26.86184, 75.80994],
                      ["Jawahar Circle", 26.84177, 75.8021], ["Sector 10", 26.84676, 75.80915]],
}


def _r5(x):
    return int(5 * round(100 * x / 5))


def _step(v, s):
    return int(s * round(v / s))


def _xy(lat, lon):
    return np.c_[np.asarray(lon, float) * M_LON, np.asarray(lat, float) * M_LAT]


def _dist(pts, la, lo):
    """Great-circle metres from (la, lo) to an (n, 2) array of [lat, lon]; exact at the 500 m edge."""
    if not len(pts):
        return np.zeros(0)
    a = np.radians
    h = np.sin((a(pts[:, 0]) - a(la)) / 2) ** 2 + np.cos(a(la)) * np.cos(a(pts[:, 0])) * np.sin((a(pts[:, 1]) - a(lo)) / 2) ** 2
    return 2 * 6_371_000 * np.arcsin(np.sqrt(h))


def _summary(g, k):
    """Aggregates for a group of cafés: always the count, the rest only for k or more."""
    out = {"n": int(len(g))}
    if len(g) < k:
        return out
    out["mix"] = {t: _r5((g.type_base == t).mean()) for t in TYPES}
    op = g.open_m.dropna()
    if len(op) >= k:
        out["open8"] = _r5((op <= 480).mean())
    pr = g.zomato_cost_for_two_inr.dropna()
    if len(pr) >= k:
        out["price"] = _step(pr.median(), 50)
    rv = g.google_reviews.dropna()
    if len(rv) >= k:
        out["reviews"] = _step(rv.median(), 5) if rv.median() >= 20 else int(round(rv.median()))
    return out


def build(core, k, parse_hours, poi_path):
    c = core.dropna(subset=["lat", "lon"]).copy()
    c["open_m"] = c.zomato_hours.map(lambda t: (parse_hours(t) or (None,))[0])
    P = np.c_[c.lat.values, c.lon.values]
    poi = json.load(open(poi_path)) if Path(poi_path).exists() else {"metro": [], "hotels": [], "bus_stops": []}
    metro = [m for m in poi["metro"] if m[2] and "u/c" not in m[2] and "metro station" not in m[2].lower()]   # operating stations, once each
    M = np.array([m[:2] for m in metro], float).reshape(-1, 2)
    Hh = np.array([h[:2] for h in poi["hotels"]], float).reshape(-1, 2)
    Bs = np.array([b[:2] for b in poi["bus_stops"]], float).reshape(-1, 2)

    areas, spots = {}, []
    for ai, (area, (la0, la1, lo0, lo1)) in enumerate(BOX.items()):
        base = _summary(core.assign(open_m=core.zomato_hours.map(lambda t: (parse_hours(t) or (None,))[0]))[core.area == area], k)   # same area as the rest of the site
        ns = []
        lats = np.arange(la0, la1 + 1e-9, SPACING / M_LAT)
        lons = np.arange(lo0, lo1 + 1e-9, SPACING / M_LON)
        for la in lats:
            for lo in lons:
                la, lo = round(float(la), 5), round(float(lo), 5)      # count from exactly the coordinates that are published
                s = _summary(c[_dist(P, la, lo) <= RADIUS], k)
                s["hotels"] = int((_dist(Hh, la, lo) <= RADIUS).sum())
                s["stops"] = int((_dist(Bs, la, lo) <= RADIUS).sum())
                if len(M):
                    dm = _dist(M, la, lo)
                    s["metro_m"] = _step(dm.min(), 50)
                    s["metro"] = metro[int(dm.argmin())][2]
                spots.append([la, lo, ai, s])
                ns.append(s["n"])
        areas[area] = {"box": [la0, la1, lo0, lo1], "cafes": base, "spot_counts": sorted(ns), "places": PLACES[area]}
    return {"radius_m": RADIUS, "spacing_m": SPACING, "k": k, "types": TYPES, "areas": areas, "spots": spots,
            "source": "Operating cafés from the latest update; hotels, bus stops and metro stations from OpenStreetMap (ODbL)."}
