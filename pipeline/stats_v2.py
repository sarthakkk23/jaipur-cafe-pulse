"""Statistical findings for the v2 site, computed on the full latest run.

Everything here is an aggregate over at least `k` cafés. Each finding carries its number, a plain-language
sentence, an evidence grade and a "how we know" note, so any figure on the page can be explained if asked.
The wording follows the result: if an interval crosses zero the sentence says so, rather than claiming an effect.
Pure numpy (bootstrap and permutation), so the build needs no extra dependencies.
"""
from collections import Counter

import numpy as np
import pandas as pd

SEED = 20261017
M_LAT = 111_320.0
M_LON = 111_320.0 * np.cos(np.radians(26.88))
TYPES = ["Coffee-led", "Tea & chai", "Bakery", "All-day café"]
AMEN = {  # Zomato highlight -> label; wifi and work-friendly are read together (they travel together)
    "wifi_work": "Wi-Fi or work-friendly", "outdoor_seating": "Outdoor seating", "breakfast": "Breakfast",
    "kid_friendly": "Kid-friendly", "smoking_area": "Smoking area", "board_games_or_books": "Board games or books",
    "home_delivery": "Home delivery", "veg_only": "Vegetarian only",
}


def _pct(x):
    return None if x is None or pd.isna(x) else int(round(100 * float(x)))


def _rank_corr(a, b):
    return float(np.corrcoef(pd.Series(a).rank().values, pd.Series(b).rank().values)[0, 1])


def _perm_p(stat, a, b, rng, n=4000):
    obs = stat(a, b)
    hits = sum(abs(stat(rng.permutation(a), b)) >= abs(obs) for _ in range(n))
    return (hits + 1) / (n + 1)


def _wilson(p, n, z=1.96):
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def _grade(n, decisive, k):
    """Strong: a clear result on a large base. Moderate: clear but on a smaller base. Weak: not clear."""
    if not decisive:
        return "Weak"
    return "Strong" if n >= 10 * k else "Moderate"


def _hull_area(P):
    pts = sorted(map(tuple, P))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    return 0.5 * abs(sum(h[i][0] * h[i - 1][1] - h[i - 1][0] * h[i][1] for i in range(len(h))))


def findings(core, k, parse_hours=None):
    """core: operating core cafés seen this run (one row per venue, private). Returns public aggregates only."""
    rng = np.random.default_rng(SEED)
    out = []
    c = core.copy()

    # 1. attention is concentrated (Lorenz curve, Gini)
    g = c.google_reviews.dropna().values
    if len(g) >= k:
        s = np.sort(g)[::-1]
        top = s[: len(s) // 10].sum() / s.sum()
        boots = []
        for _ in range(2000):
            b = np.sort(rng.choice(g, len(g)))[::-1]
            boots.append(b[: len(b) // 10].sum() / b.sum())
        lo, hi = np.percentile(boots, [2.5, 97.5])
        asc = np.sort(g)
        cum = np.r_[0, np.cumsum(asc)] / asc.sum()
        xs = np.linspace(0, 1, 21)
        lorenz = [[_pct(x), _pct(np.interp(x, np.linspace(0, 1, len(cum)), cum))] for x in xs]
        gini = 1 - 2 * np.trapz(cum, dx=1 / len(asc))
        out.append({
            "id": "attention", "value": _pct(top), "unit": "%",
            "headline": "of all Google reviews go to the top 10% of cafés.",
            "body": "Everyone else shares a thin slice of attention, so each new review counts for more. Asking happy customers for one is the cheapest way up.",
            "limit": "It doesn't say the most-reviewed cafés are the best, only that they are found the most.",
            "grade": _grade(len(g), True, k),
            "how": [f"The typical café has {int(np.median(g)):,} Google reviews; {_pct((g < 100).mean())}% have fewer than a hundred.",
                    f"I sorted the {len(g):,} cafés with Google reviews from most reviewed to least and added up the top tenth.",
                    f"Resampling the cafés 2,000 times puts the share between {_pct(lo)}% and {_pct(hi)}% (95% interval).",
                    f"The Gini coefficient, a 0-to-1 measure of how unevenly something is shared, is {gini:.2f}. "
                    "Zero would mean every café had the same number of reviews."],
            "chart": {"kind": "split", "parts": [["Top 10% of cafés", _pct(top)], ["The other 90%", 100 - _pct(top)]]},
            "n": int(len(g)),
        })

    # 2. cafés cluster (nearest neighbours, Clark-Evans)
    geo = c.dropna(subset=["lat", "lon"])
    if len(geo) >= k:
        X = np.c_[geo.lon.values * M_LON, geo.lat.values * M_LAT]
        D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
        np.fill_diagonal(D, np.inf)
        near = (D <= 500).sum(1)
        share10 = (near >= 10).mean()
        areas = []
        for a in sorted(geo.area.unique()):
            m = (geo.area == a).values
            if m.sum() < k:
                continue
            A = _hull_area(X[m])
            obs = D[np.ix_(m, m)].min(1).mean()
            exp = 0.5 / np.sqrt(m.sum() / A)
            se = 0.26136 / np.sqrt(m.sum() ** 2 / A)
            areas.append({"area": a, "n": int(m.sum()), "observed_m": int(round(obs)), "random_m": int(round(exp)),
                          "closer": _pct(1 - obs / exp), "z": round(float((obs - exp) / se), 1)})
        closer = ", ".join(f"{x['closer']}% in {x['area']}" for x in areas)
        decisive = all(x["z"] < -2.6 for x in areas)
        out.append({
            "id": "cluster", "value": _pct(share10), "unit": "%",
            "headline": "of cafés have 10 or more other cafés within a 5-minute walk.",
            "body": "Customers here always have a choice next door. Location alone won't set a café apart; what it offers has to.",
            "limit": "It doesn't say whether a crowded street helps or hurts a café's trade.",
            "grade": _grade(len(geo), decisive, k),
            "how": [f"For each of the {len(geo):,} mapped cafés I counted the others within 500 metres, about a five-minute walk. "
                    f"The typical café has {int(np.median(near)):,}.",
                    f"Cafés sit closer together than chance would put them: {closer}.",
                    "To test for clustering I compared the average distance to the nearest café with what the same number "
                    "of cafés, scattered at random over the same ground, would give (the Clark-Evans test).",
                    "; ".join(f"{x['area']}: {x['observed_m']} m observed against {x['random_m']} m at random" for x in areas)
                    + ". Gaps this large would arise by chance less than one time in a hundred."],
            "chart": {"kind": "spacing", "areas": areas},
            "n": int(len(geo)),
        })
        c.loc[geo.index, "near500"] = near

    # 3. new ratings run high (rating against evidence)
    r = c.dropna(subset=["google_rating", "google_reviews"])
    if len(r) >= k:
        edges = [0, 10, 50, 200, 1000, np.inf]
        labels = ["Under 10", "10 to 49", "50 to 199", "200 to 999", "1,000 or more"]
        bands = []
        for lo_, hi_, lab in zip(edges, edges[1:], labels):
            b = r[(r.google_reviews >= lo_) & (r.google_reviews < hi_)]
            if len(b) >= k:
                bands.append({"band": lab, "n": int(len(b)), "share48": _pct((b.google_rating >= 4.8).mean()),
                              "spread": round(float(b.google_rating.std()), 2)})
        rho = _rank_corr(r.google_rating.values, np.log1p(r.google_reviews.values))
        p = _perm_p(_rank_corr, r.google_rating.values, np.log1p(r.google_reviews.values), rng, 2000)
        out.append({
            "id": "ratings", "value": bands[0]["share48"], "unit": "%",
            "headline": "of cafés with under 10 reviews rate 4.8 or more.",
            "body": f"With 1,000+ reviews, just {bands[-1]['share48']}% do. A perfect score on a few reviews is mostly luck: judge any rating, yours or a rival's, by the reviews behind it.",
            "limit": "It doesn't say new cafés inflate their scores; a few reviews simply swing more.",
            "grade": _grade(len(r), p < 0.01, k),
            "how": [f"I grouped the {len(r):,} rated cafés by how many reviews they have and took the share rated 4.8 or above in each group.",
                    f"Ratings also spread less as reviews grow: the typical gap from the group average falls from "
                    f"{bands[0]['spread']} stars to {bands[-1]['spread']}.",
                    f"Across all cafés, more reviews go with a lower rating (rank correlation {rho:.2f}; a shuffle test puts the chance "
                    f"of this by luck below {max(p, 0.001):.3f}). Mostly that is small numbers swinging more, not a sign that popular cafés are worse."],
            "chart": {"kind": "bands", "bands": bands},
            "n": int(len(r)),
        })

    # 4. Google rates kinder than Zomato (same cafés, paired)
    pr = c.dropna(subset=["google_rating", "zomato_dining_rating"])
    if len(pr) >= k:
        d = (pr.google_rating - pr.zomato_dining_rating).values
        bm = [rng.choice(d, len(d)).mean() for _ in range(4000)]
        lo, hi = np.percentile(bm, [2.5, 97.5])
        higher, equal = (d > 0).mean(), (d == 0).mean()
        out.append({
            "id": "platforms_rate", "value": _pct(higher), "unit": "%",
            "headline": "of cafés rate higher on Google than on Zomato.",
            "body": f"By about {d.mean():.1f} stars for the very same café. Compare yourself with cafés on the same app, never across apps.",
            "limit": "It doesn't say which app is right, only that their scores are not interchangeable.",
            "grade": _grade(len(d), lo > 0 or hi < 0, k),
            "how": [f"I took the {len(d):,} cafés rated on both Google and Zomato dine-in and subtracted one rating from the other, café by café.",
                    f"Resampling those cafés 4,000 times puts the average gap between {lo:.2f} and {hi:.2f} stars (95% interval), "
                    "clear of zero.",
                    f"{_pct(equal)}% score the same on both; {_pct(1 - higher - equal)}% score higher on Zomato. "
                    "Shares are rounded, so they may not add to exactly 100."],
            "chart": {"kind": "split", "parts": [["Higher on Google", _pct(higher)], ["Same", _pct(equal)], ["Higher on Zomato", _pct(1 - higher - equal)]]},
            "n": int(len(d)),
        })

    # 5. delivery speaks louder than the table, among cafés that deliver
    dv = c[c.on_zomato == "Y"].dropna(subset=["zomato_delivery_reviews", "zomato_dining_reviews"])
    dd = dv[dv.zomato_delivery_reviews > 0]
    if len(dd) >= k:
        more = (dd.zomato_delivery_reviews > dd.zomato_dining_reviews).mean()
        lo, hi = _wilson(more, len(dd))
        out.append({
            "id": "delivery", "value": _pct(more), "unit": "%",
            "headline": "of cafés that deliver through Zomato get more delivery reviews than dine-in reviews.",
            "body": ("For most cafés that deliver, the delivery order shapes the reputation more than the table does. "
                     "Packaging and delivery time deserve the same care as the room." if lo > 0.5 else
                     "Delivery and the table shape the reputation about equally. Packaging and delivery time deserve the same care as the room."),
            "limit": "It doesn't say delivery earns more than the dining room, only that it is reviewed more.",
            "grade": _grade(len(dd), lo > 0.5 or hi < 0.5, k),
            "how": [f"The {len(dd):,} cafés on Zomato with at least one delivery review: I compared each café's delivery reviews with its dine-in reviews.",
                    f"The share is between {_pct(lo)}% and {_pct(hi)}% (95% Wilson interval).",
                    f"Across all {len(dv):,} cafés on Zomato, counting those that don't deliver as more dine-in, it's "
                    f"{_pct((dv.zomato_delivery_reviews > dv.zomato_dining_reviews).mean())}%."],
            "chart": {"kind": "split", "parts": [["More delivery reviews", _pct(more)], ["More dine-in reviews", 100 - _pct(more)]]},
            "n": int(len(dd)),
        })

    # 6. amenities travel together: raw gap against like-for-like
    z = c[c.on_zomato == "Y"].dropna(subset=["google_reviews", "zomato_cost_for_two_inr"]).copy()
    if len(z) >= 5 * k:
        z["wifi_work"] = ((z.wifi == "Y") | (z.work_friendly == "Y")).map({True: "Y", False: "N"})
        flags = {a: (z[a] == "Y").astype(float).values for a in AMEN}
        ctrl = [(z.area == "Malviya Nagar").astype(float).values] + [(z.type_base == t).astype(float).values for t in TYPES[:3]]
        ctrl.append(np.log(z.zomato_cost_for_two_inr.values) - np.log(600))
        Xm = np.c_[np.ones(len(z)), np.column_stack(list(flags.values())), np.column_stack(ctrl)]
        y = np.log1p(z.google_reviews.values)
        beta = np.linalg.lstsq(Xm, y, rcond=None)[0]
        bs = np.array([np.linalg.lstsq(Xm[i], y[i], rcond=None)[0] for i in (rng.integers(0, len(z), len(z)) for _ in range(3000))])
        items = []
        for j, (a, lab) in enumerate(AMEN.items(), 1):
            yes, no = z.google_reviews[flags[a] == 1].values, z.google_reviews[flags[a] == 0].values
            if len(yes) < k or len(no) < k:
                continue
            lo, hi = np.percentile(bs[:, j], [2.5, 97.5])
            items.append({"label": lab, "share": _pct(flags[a].mean()), "raw": _pct(np.median(yes) / np.median(no) - 1),
                          "adj": _pct(np.expm1(beta[j])), "lo": _pct(np.expm1(lo)), "hi": _pct(np.expm1(hi)),
                          "holds": bool(lo > 0 or hi < 0)})
        items.sort(key=lambda x: -x["raw"])
        lead = next(x for x in items if x["label"].startswith("Wi-Fi"))
        held = [x["label"].lower() for x in items if x["holds"]]
        nfeat = np.column_stack(list(flags.values())).sum(1)
        others = lambda m: float(np.mean(nfeat[m] - 1))
        wf = flags["wifi_work"] == 1
        # family- or kid-friendly, held against similar cafés AND the number of other features listed
        fam_line, fam = "", None
        if "family_or_kid" in z and "n_highlights" in z:
            zf = z.dropna(subset=["family_or_kid", "n_highlights"])
            fk = (zf.family_or_kid == "Y").astype(float).values
            if len(zf) >= 5 * k and k <= fk.sum() <= len(zf) - k:
                other = np.log1p(np.clip(zf.n_highlights.values - fk, 0, None))
                cf = [(zf.area == "Malviya Nagar").astype(float).values] + [(zf.type_base == t).astype(float).values for t in TYPES[:3]]
                cf.append(np.log(zf.zomato_cost_for_two_inr.values) - np.log(600))
                Xf = np.c_[np.ones(len(zf)), fk, other, np.column_stack(cf)]
                yf = np.log1p(zf.google_reviews.values)
                bf = np.linalg.lstsq(Xf, yf, rcond=None)[0][1]
                bsf = np.array([np.linalg.lstsq(Xf[i], yf[i], rcond=None)[0][1] for i in (rng.integers(0, len(zf), len(zf)) for _ in range(3000))])
                flo, fhi = np.percentile(bsf, [2.5, 97.5])
                zall = c[c.on_zomato == "Y"].dropna(subset=["family_or_kid"])
                fam = {"share": _pct((zall.family_or_kid == "Y").mean()), "n_all": int(len(zall)), "x": float(np.exp(bf)), "lo": float(np.expm1(flo)), "hi": float(np.expm1(fhi)), "n": int(len(zf))}
                if flo > 0:
                    fam_line = (f" The one feature that holds up against similar cafés: the {fam['share']}% that say they're family- or "
                                f"kid-friendly carry about {fam['x']:.0f}× the reviews.")
        out.append({
            "id": "amenities", "value": round(1 + lead["raw"] / 100, 1), "unit": "×",
            "headline": "the Google reviews for cafés that list Wi-Fi.",
            "body": (("Against similar cafés, that gap can't be told from none: Wi-Fi tends to come with everything else." if not lead["holds"]
                      else "Against similar cafés, part of that gap holds: some of it is Wi-Fi itself.") + fam_line),
            "limit": "It doesn't say Wi-Fi is worthless; customers may still choose a café for it.",
            "grade": "Moderate",
            "how": [f"All cafés: the median Google reviews of cafés that list a feature against those that don't, for the {len(z):,} "
                    f"cafés on Zomato with a listed price. Cafés with Wi-Fi list {others(wf):.1f} other features on average, against "
                    f"{float(np.mean(nfeat[~wf])):.1f} for the rest.",
                    "Similar cafés: a regression on the logarithm of reviews that holds area, café type and price level fixed, "
                    f"so each feature is compared against cafés that are otherwise alike. Wi-Fi: {lead['adj']:+d}% "
                    f"(95% interval {lead['lo']:+d}% to {lead['hi']:+d}% from 3,000 resamples). The range includes zero, which is the point: "
                    "once similar cafés are compared, Wi-Fi's own effect can't be told apart from none.",
                    "; ".join(f"{x['label']}: {x['raw']:+d}% across all cafés, {x['adj']:+d}% among similar ones" for x in items) + ".",
                    *([f"Family- or kid-friendly, also holding the number of other listed features fixed: {fam['x'] - 1:+.0%} reviews "
                       f"(95% interval {fam['lo']:+.0%} to {fam['hi']:+.0%}), {fam['n']:,} cafés. {fam['share']}% of all {fam['n_all']:,} cafés on Zomato list it."] if fam else []),
                    "This is association, not cause: a listing can mark the kind of café that draws reviews without drawing them itself."],
            "chart": {"kind": "bars", "sign": True, "bars": [["All cafés", lead["raw"]], ["Similar cafés", lead["adj"]]],
                      "note": "Extra Google reviews for cafés with Wi-Fi, compared with"},
            "n": int(len(z)),
        })

    # 7. price does not buy a rating
    p = c.dropna(subset=["zomato_cost_for_two_inr"])
    if len(p) >= k:
        pr2 = p.dropna(subset=["google_rating"])
        rho = _rank_corr(pr2.zomato_cost_for_two_inr.values, pr2.google_rating.values)
        pv = _perm_p(_rank_corr, pr2.zomato_cost_for_two_inr.values, pr2.google_rating.values, rng, 2000)
        pz2 = p.dropna(subset=["zomato_dining_rating"])
        rho_z = _rank_corr(pz2.zomato_cost_for_two_inr.values, pz2.zomato_dining_rating.values) if len(pz2) >= k else 0.0
        pv_z = _perm_p(_rank_corr, pz2.zomato_cost_for_two_inr.values, pz2.zomato_dining_rating.values, rng, 2000) if len(pz2) >= k else 1.0
        z_line = (" On Zomato, dearer cafés do rate a little higher." if rho_z > 0 and pv_z < 0.05 else
                  " On Zomato, dearer cafés rate a little lower." if rho_z < 0 and pv_z < 0.05 else "")
        cuts = [0, 300, 500, 800, 1200, np.inf]
        labs = ["Up to ₹300", "₹301 to ₹500", "₹501 to ₹800", "₹801 to ₹1,200", "Over ₹1,200"]
        dist = [[lab, _pct(((p.zomato_cost_for_two_inr > lo_) & (p.zomato_cost_for_two_inr <= hi_)).mean())]
                for lo_, hi_, lab in zip(cuts, cuts[1:], labs)]
        by_area = {a: int(g_.zomato_cost_for_two_inr.median()) for a, g_ in p.groupby("area") if len(g_) >= k}
        out.append({
            "id": "price", "value": _pct((p.zomato_cost_for_two_inr <= 500).mean()), "unit": "%",
            "headline": "of cafés charge ₹500 or less for two.",
            "body": "Price shows no link to Google rating: dearer cafés rate no higher there, cheaper ones no lower." + z_line + " Price for your customer, not for your score.",
            "limit": "It doesn't say price doesn't matter to customers, only how it lines up with ratings.",
            "grade": _grade(len(pr2), True, k),
            "how": [f"Cost for two as listed on Zomato, for {len(p):,} cafés. The typical café charges ₹{int(p.zomato_cost_for_two_inr.median()):,}: "
                    + " and ".join(f"₹{v:,} in {a}" for a, v in by_area.items()) + ".",
                    f"Price against Google rating, for {len(pr2):,} cafés: rank correlation {rho:+.2f}, where zero means no link "
                    f"and ±1 a perfect one. A shuffle test finds nothing (chance of a link this size by luck: {pv:.2f}).",
                    *([f"Price against Zomato dine-in rating, for {len(pz2):,} cafés: rank correlation {rho_z:+.2f} (chance by luck: {pv_z:.3f})."] if len(pz2) >= k else []),
                    "Price does go with more reviews, weakly; dearer cafés tend to be bigger.",
                    "Zomato recomputed its cost for two in October 2026, so price levels are provisional; how cafés rank against each other held steady."],
            "chart": {"kind": "bars", "bars": dist},
            "n": int(len(p)),
        })

    # 7b. the same kind of café costs more in C-Scheme
    pz = c.dropna(subset=["zomato_cost_for_two_inr"])
    pz = pz[pz.zomato_cost_for_two_inr > 0]
    if len(pz) >= k and min((pz.area == a).sum() for a in ("C-Scheme", "Malviya Nagar")) >= k:
        csd = (pz.area == "C-Scheme").astype(float).values
        Xp = np.c_[np.ones(len(pz)), csd, np.column_stack([(pz.type_base == t).astype(float).values for t in TYPES[1:]])]
        yp = np.log(pz.zomato_cost_for_two_inr.values.astype(float))
        bp = np.linalg.lstsq(Xp, yp, rcond=None)[0][1]
        bsp = np.array([np.linalg.lstsq(Xp[i], yp[i], rcond=None)[0][1] for i in (rng.integers(0, len(pz), len(pz)) for _ in range(3000))])
        plo, phi = np.percentile(bsp, [2.5, 97.5])
        perm = np.array([np.linalg.lstsq(np.c_[Xp[:, :1], rng.permutation(csd), Xp[:, 2:]], yp, rcond=None)[0][1] for _ in range(2000)])
        pperm = float((np.abs(perm) >= abs(bp)).mean())
        over = {a: _pct((pz[pz.area == a].zomato_cost_for_two_inr > 600).mean()) for a in ("C-Scheme", "Malviya Nagar")}
        if bp > 0:
            out.append({
                "id": "cs_price_premium", "value": _pct(np.expm1(bp)), "unit": "%",
                "headline": "more for two at a C-Scheme café than at the same kind of café in Malviya Nagar.",
                "body": (f"Compare your price with cafés like yours in your own area: {over['C-Scheme']}% of C-Scheme cafés charge over ₹600 for two, "
                         f"against {over['Malviya Nagar']}% in Malviya Nagar."),
                "limit": "It doesn't say C-Scheme cafés earn more: rent and costs are higher there too, and Zomato's cost for two is the app's estimate, not a menu price.",
                "grade": _grade(len(pz), plo > 0 and pperm < 0.05, k),
                "how": [f"Zomato cost for two for {len(pz):,} cafés ({int(csd.sum())} in C-Scheme, {int(len(pz) - csd.sum())} in Malviya Nagar), "
                        "compared on a log scale with café type held fixed.",
                        f"C-Scheme {_pct(np.expm1(bp)):+d}% (95% interval {_pct(np.expm1(plo)):+d}% to {_pct(np.expm1(phi)):+d}% from 3,000 resamples). "
                        f"Shuffling the area labels 2,000 times gives a gap this large {pperm:.3f} of the time.",
                        "It held on the September update too. Zomato recomputed its cost for two in October 2026, so the level is provisional; the gap held on both versions."],
                "chart": {"kind": "bars", "bars": [["C-Scheme", over["C-Scheme"]], ["Malviya Nagar", over["Malviya Nagar"]]],
                          "note": "Share of cafés charging over ₹600 for two"},
                "n": int(len(pz)),
            })

    # 7c. most Zomato listings say very little
    if "n_features" in c:
        za = c[(c.on_zomato == "Y")].dropna(subset=["n_features"])
        zl = za.dropna(subset=["google_reviews", "zomato_cost_for_two_inr"])
        zl = zl[zl.zomato_cost_for_two_inr > 0]
        if len(zl) >= 5 * k:
            nf = za.n_features.values.astype(float)            # the share: every café on Zomato
            top = (zl.n_features.values > np.median(nf)).astype(float)
            cl = [(zl.area == "Malviya Nagar").astype(float).values] + [(zl.type_base == t).astype(float).values for t in TYPES[:3]]
            cl.append(np.log(zl.zomato_cost_for_two_inr.values) - np.log(600))
            Xl = np.c_[np.ones(len(zl)), top, np.column_stack(cl)]
            yl = np.log1p(zl.google_reviews.values)
            bl = np.linalg.lstsq(Xl, yl, rcond=None)[0][1]
            bsl = np.array([np.linalg.lstsq(Xl[i], yl[i], rcond=None)[0][1] for i in (rng.integers(0, len(zl), len(zl)) for _ in range(3000))])
            llo, lhi = np.percentile(bsl, [2.5, 97.5])
            le3 = (nf <= 3).mean()
            out.append({
                "id": "listing_detail", "value": _pct(le3), "unit": "%",
                "headline": "of cafés on Zomato list three or fewer features beyond the basics.",
                "body": (f"Cafés in the top half for listed features have about {np.exp(bl):.1f}× the Google reviews of similar cafés. "
                         "Filling in your listing (seating, parking, Wi-Fi, who it suits) takes ten minutes." if llo > 0 else
                         "A fuller listing shows no clear link to reviews among similar cafés, but it costs ten minutes and tells customers what to expect."),
                "limit": "It doesn't say a fuller listing brings reviews: established cafés may simply have more to list.",
                "grade": _grade(len(zl), llo > 0, k),
                "how": [f"Zomato's listed highlights for {len(zl):,} cafés, leaving out the basics nearly every café lists (lunch, dinner, breakfast, "
                        f"indoor seating, takeaway, delivery, vegetarian). The typical café lists {int(np.median(nf))} beyond those. "
                        f"The comparison below uses the {len(zl):,} with a Google review count and a price.",
                        f"Top half against bottom half, with area, café type and price level held fixed: {np.expm1(bl):+.0%} Google reviews "
                        f"(95% interval {np.expm1(llo):+.0%} to {np.expm1(lhi):+.0%} from 3,000 resamples).",
                        "It held on the September update too. Fuller listings didn't gain reviews faster over three weeks, so this isn't shown to be cause."],
                "chart": {"kind": "bars", "bars": [["0 to 3 features", _pct(le3)], ["4 to 7", _pct(((nf >= 4) & (nf <= 7)).mean())], ["8 or more", _pct((nf >= 8).mean())]]},
                "n": int(len(za)),
            })

    # 7d. Swiggy and Zomato quote different prices for the same café
    if "sw_cost_for_two" in c:
        sz = c.dropna(subset=["sw_cost_for_two", "zomato_cost_for_two_inr"])
        sz = sz[(sz.sw_cost_for_two > 0) & (sz.zomato_cost_for_two_inr > 0)]
        if len(sz) >= k:
            lower = (sz.sw_cost_for_two < sz.zomato_cost_for_two_inr).mean()
            slo, shi = _wilson(lower, len(sz))
            gap = float(np.median(sz.sw_cost_for_two / sz.zomato_cost_for_two_inr - 1))
            out.append({
                "id": "swiggy_cost_for_two", "value": _pct(lower), "unit": "%",
                "headline": "of cafés on both apps show a lower cost for two on Swiggy than on Zomato.",
                "body": f"By about {abs(_pct(gap))}% for the very same café. When you compare your price with a rival's, compare on the same app.",
                "limit": "It doesn't say the café charges less on Swiggy; the two apps work out cost for two differently.",
                "grade": _grade(len(sz), slo > 0.5 or shi < 0.5, k),
                "how": [f"The {len(sz):,} cafés with a cost for two on both apps, compared café by café.",
                        f"The share is between {_pct(slo)}% and {_pct(shi)}% (95% Wilson interval). The typical gap is {_pct(gap):+d}%.",
                        "Swiggy finds fewer of the area's cafés than Zomato, and fewer of them again from one update to the next, so this rests on a smaller base."],
                "chart": {"kind": "split", "parts": [["Lower on Swiggy", _pct(lower)], ["Same or higher", 100 - _pct(lower)]]},
                "n": int(len(sz)),
            })

    # 8. menus are wide
    cu = c[c.on_zomato == "Y"].z_cuisines.dropna().str.lower().str.split(r",\s*")
    cu = cu[cu.map(len) > 0]
    if len(cu) >= k:
        cnt = Counter(x.strip() for l in cu for x in set(l))
        skip = {"cafe", "beverages"}
        top = [[name.title() if name != "fast food" else "Fast food", _pct(v / len(cu))] for name, v in cnt.most_common(14) if name not in skip][:8]
        out.append({
            "id": "menus", "value": _pct((cu.map(len) >= 5).mean()), "unit": "%",
            "headline": "of cafés list 5 or more cuisines.",
            "body": f"More list fast food ({_pct(cnt['fast food'] / len(cu))}%) than coffee ({_pct(cnt['coffee'] / len(cu))}%). A short, focused menu stands out simply by being rare.",
            "limit": "It doesn't say a short menu does better, only that it is rarer.",
            "grade": _grade(len(cu), True, k),
            "how": [f"The typical menu spans {int(cu.map(len).median())} cuisines. The cuisine tags each of {len(cu):,} cafés lists on Zomato. 'Café' and 'Beverages', which nearly all list, are left out of the chart."],
            "chart": {"kind": "bars", "bars": top},
            "n": int(len(cu)),
        })

    # 9. most cafés show up on one platform
    on = {"Google Maps": c.on_google, "Zomato": c.on_zomato, "Swiggy": c.on_swiggy}
    npl = sum((v == "Y").astype(int) for v in list(on.values()) + [c.on_magicpin])
    out.append({
        "id": "visibility", "value": _pct((npl == 1).mean()), "unit": "%",
        "headline": "of cafés show up on only one app.",
        "body": f"Only {_pct((c.on_zomato == 'Y').mean())}% are on Zomato and {_pct((c.on_swiggy == 'Y').mean())}% on Swiggy. Every app a café is missing from is a crowd that never sees it.",
        "limit": ("It doesn't count apps outside Google Maps, Zomato, Swiggy and magicpin." if (c.on_magicpin == "Y").any() else
                  "It doesn't count apps outside Google Maps, Zomato and Swiggy. magicpin couldn't be read in this update, so it isn't counted."),
            "grade": "Moderate",
        "how": ["; ".join(f"{_pct((v == 'Y').mean())}% on {name}" for name, v in on.items()) + ".",
                f"Each of the {len(c):,} cafés matched across the platform searches I run on every update.",
                "Absent means it did not appear in my searches of that platform, which is how a customer browsing the area would miss it too."],
        "chart": {"kind": "split", "parts": [["One app", _pct((npl == 1).mean())], ["Two", _pct((npl == 2).mean())], ["Three or more", _pct((npl >= 3).mean())]]},
        "n": int(len(c)),
    })

    # 10. the two areas differ in kind (chi-square, permutation). Off: weak, and the map shows the mix cell by cell.
    ct = pd.crosstab(c.area, c.type_base).reindex(columns=TYPES, fill_value=0)
    if False and (ct.sum(1) >= k).all():
        def chi(a_, t_):
            t = pd.crosstab(a_, t_).values
            E = np.outer(t.sum(1), t.sum(0)) / t.sum()
            return ((t - E) ** 2 / E).sum()
        a_v, t_v = c.area.values, c.type_base.values
        obs = chi(a_v, t_v)
        pv = (sum(chi(rng.permutation(a_v), t_v) >= obs for _ in range(2000)) + 1) / 2001
        sh = (ct.T / ct.sum(1)).T
        out.append({
            "id": "areas", "value": _pct(sh.loc["Malviya Nagar", "Tea & chai"]), "unit": "%",
            "headline": "of Malviya Nagar's cafés are chai cafés.",
            "body": f"In C-Scheme it is {_pct(sh.loc['C-Scheme', 'Tea & chai'])}%, where coffee-led cafés are a larger share "
                    f"({_pct(sh.loc['C-Scheme', 'Coffee-led'])}% against {_pct(sh.loc['Malviya Nagar', 'Coffee-led'])}%). "
                    + ("A real difference in kind." if pv < 0.05 else "A lean, not yet a firm difference: the gap could still be chance."),
            "grade": _grade(len(c), pv < 0.05, k),
            "how": [f"The type mix of all {len(c):,} operating cafés, by area.",
                    f"A chi-square test, run by shuffling the area labels 2,000 times, puts the chance of a mix this different by luck at {pv:.2f}."],
            "chart": {"kind": "mix", "rows": [[a, [[t, _pct(sh.loc[a, t])] for t in TYPES]] for a in ct.index]},
            "n": int(len(c)),
        })
    return out


def hexes(core, k, bbox, size_m=300, parse_hours=None):
    """Hexagonal bins for the map. Counts everywhere; shares and medians only where a bin holds k cafés or more."""
    geo = core.dropna(subset=["lat", "lon"]).copy()
    lat0, lon0 = bbox["lat"][0], bbox["lon"][0]
    x = (geo.lon.values - lon0) * M_LON
    y = (geo.lat.values - lat0) * M_LAT
    # pointy-top axial coordinates
    q = (np.sqrt(3) / 3 * x - y / 3) / size_m
    r = (2 / 3 * y) / size_m
    cx, cz = q, r
    cy = -cx - cz
    rx, ry, rz = np.round(cx), np.round(cy), np.round(cz)
    dx, dy, dz = abs(rx - cx), abs(ry - cy), abs(rz - cz)
    fx = (dx > dy) & (dx > dz)
    fz = ~fx & (dz >= dy)
    rx = np.where(fx, -ry - rz, rx)
    rz = np.where(fz, -rx - ry, rz)
    geo["hq"], geo["hr"] = rx.astype(int), rz.astype(int)
    out = []
    for (hq, hr), g in geo.groupby(["hq", "hr"]):
        px = size_m * np.sqrt(3) * (hq + hr / 2)
        py = size_m * 1.5 * hr
        cell = {"lat": round(lat0 + py / M_LAT, 5), "lon": round(lon0 + px / M_LON, 5), "n": int(len(g))}
        if len(g) >= k:                       # the type split, like every share, only for a group of k or more
            cell["types"] = {t: int((g.type_base == t).sum()) for t in TYPES}
            cell["mix"] = {t: _pct((g.type_base == t).mean()) for t in TYPES}
            if parse_hours is not None:
                hrs = g.zomato_hours.dropna().map(parse_hours).dropna()
                if len(hrs) >= k:
                    cell["open_by_8"] = _pct(np.mean([h[0] <= 480 for h in hrs]))
            pr = g.zomato_cost_for_two_inr.dropna()
            if len(pr) >= k:
                cell["price"] = int(pr.median())
            rv = g.google_reviews.dropna()
            if len(rv) >= k:
                cell["reviews"] = int(rv.median())
        out.append(cell)
    return {"size_m": size_m, "cells": out}
