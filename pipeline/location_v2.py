"""Location check: what lies within a five-minute walk of any spot in C-Scheme or Malviya Nagar.

Spots sit on a 150 m grid over each area. For each spot this counts the operating cafés within 500 m and,
only where that count is k or more, their type mix, the share open by 8am, the typical cost for two and the
typical Google reviews. Shares are rounded to the nearest 5% and medians to round steps, so neighbouring
spots that differ by one café cannot be subtracted to read that café. No venue is named or located.
Context from OpenStreetMap (ODbL): hotels and bus stops within the walk, and the nearest operating metro station.
"""
import json
import re
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


# who is around to buy coffee: Google Maps place categories sorted into plain groups, most specific first
DEMAND = [
    ("coworking", "Coworking spaces", ["coworking", "co-working", "shared office", "office space rental", "business center", "business centre"]),
    ("college", "Colleges", ["college", "university", "institute of technology", "engineering institute", "management institute", "academic department"]),
    ("coaching", "Coaching centres and institutes", ["coaching", "tutor", "tuition", "training institute", "training centre", "training center", "academy",
                                                     "education center", "education centre", "educational institution"]),
    ("school", "Schools", ["school"]),
    ("gym", "Gyms and yoga studios", ["gym", "fitness", "yoga", "pilates", "crossfit", "health club", "martial arts", "personal trainer", "meditation", "wellness center"]),
    ("hospital", "Hospitals and clinics", ["hospital", "medical center", "medical centre", "nursing home", "clinic", "diagnostic", "physiotherapy"]),
    ("hotel", "Hotels", ["hotel", "resort", "guest house", "hostel", "lodge"]),
    ("mall", "Malls and big stores", ["shopping mall", "mall", "shopping center", "shopping centre"]),
    ("office", "Offices and banks", ["corporate office", "corporate campus", "company", "software", "it services", "consultant", "bank", "insurance",
                                     "financial", "accounting", "marketing", "advertising", "office", "telecommunications", "chartered",
                                     "loan agency", "website designer", "computer support", "bpo"]),
]
NOT_DEMAND = ["cafe", "café", "coffee", "restaurant", "bakery", "tea house", "dessert", "food", "atm", "store", "wholesaler", "supplier", "dealer"]
STAY = re.compile(r"^(\d-star hotel|hotel|resort hotel|resort|guest house|hostel|backpacker hostel|lodge|homestay)$", re.I)


def _category(lines):
    """The category text in a Google Maps result card ('4.6(5,025) | Gym · 33, Mahavir Marg | Open ...')."""
    segs = [x.strip() for x in (lines or "").split(" | ")]
    for seg in segs:
        if "·" in seg and not seg.startswith(("Open", "Closed", "Closes", "Opens")):
            return seg.split("·")[0].strip()
    return next((x for x in segs if STAY.match(x)), "")      # hotel cards carry their category on its own


def demand_places(raw_path):
    """Unique places, each sorted into one group by its own Google category (not by the query that found it)."""
    raw = json.load(open(raw_path)) if raw_path and Path(raw_path).exists() else {}
    seen, out = set(), []
    for key, rows in raw.items():
        for r in rows or []:
            k = r.get("cid") or r.get("name")
            if not k or k in seen or not r.get("lat"):
                continue
            seen.add(k)
            cat = _category(r.get("lines")).lower()
            if not cat or any(w in cat for w in NOT_DEMAND):
                continue
            kind = next((g for g, _, words in DEMAND if any(w in cat for w in words)), None)
            if kind:
                out.append([float(r["lat"]), float(r["lon"]), kind])
    return out


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


def build(core, k, parse_hours, poi_path, demand_path=None):
    c = core.dropna(subset=["lat", "lon"]).copy()
    c["open_m"] = c.zomato_hours.map(lambda t: (parse_hours(t) or (None,))[0])
    P = np.c_[c.lat.values, c.lon.values]
    poi = json.load(open(poi_path)) if Path(poi_path).exists() else {"metro": [], "hotels": [], "bus_stops": []}
    metro = [m for m in poi["metro"] if m[2] and "u/c" not in m[2] and "metro station" not in m[2].lower()]   # operating stations, once each
    M = np.array([m[:2] for m in metro], float).reshape(-1, 2)
    Hh = np.array([h[:2] for h in poi["hotels"]], float).reshape(-1, 2)
    Bs = np.array([b[:2] for b in poi["bus_stops"]], float).reshape(-1, 2)
    places = demand_places(demand_path)
    kinds = [g for g, _, _ in DEMAND]
    Dp = np.array([p[:2] for p in places], float).reshape(-1, 2)
    Dk = np.array([kinds.index(p[2]) for p in places], int)

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
                if len(Dp):                                  # counts of places, never their names
                    near = Dk[_dist(Dp, la, lo) <= RADIUS]
                    s["demand"] = {g: int((near == i).sum()) for i, g in enumerate(kinds) if (near == i).any()}
                s["hotels"] = int((_dist(Hh, la, lo) <= RADIUS).sum())
                s["stops"] = int((_dist(Bs, la, lo) <= RADIUS).sum())
                if len(M):
                    dm = _dist(M, la, lo)
                    s["metro_m"] = _step(dm.min(), 50)
                    s["metro"] = metro[int(dm.argmin())][2]
                spots.append([la, lo, ai, s])
                ns.append(s["n"])
        inbox = [p for p in places if la0 <= p[0] <= la1 and lo0 <= p[1] <= lo1]
        areas[area] = {"box": [la0, la1, lo0, lo1], "cafes": base, "spot_counts": sorted(ns), "places": PLACES[area],
                       "demand": {g: sum(1 for p in inbox if p[2] == g) for g in kinds}}
    return {"radius_m": RADIUS, "spacing_m": SPACING, "k": k, "types": TYPES, "areas": areas, "spots": spots,
            "demand_groups": [[g, label] for g, label, _ in DEMAND], "demand_places": len(places),
            "source": "Operating cafés from the latest update; offices, colleges, gyms and other places from Google Maps searches; "
                      "bus stops and metro stations from OpenStreetMap (ODbL)."}
