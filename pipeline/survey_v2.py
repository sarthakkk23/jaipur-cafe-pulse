"""Café-goer survey: aggregate findings for the site, computed from the private response file.

The responses stay in private/survey/responses/; only shares of people reach the site. Free-text answers are never published.
Rules (private/survey/README.md):
- under-18 answers are left out;
- headline shares use the whole sample, with a 95% Wilson interval and the sample described next to them;
- a comparison between two groups appears only inside a finding's body, marked as an early sign, when each group has 25+
  people and a shuffle test puts the gap's chance below 1%;
- survey findings are graded Moderate at most, because the sample is reached through Sarthak's own network.
"""
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

COLS = ["ts", "area", "when", "reason", "heard", "spend", "doing", "stay", "back", "first_cup", "delivery", "age", "occupation", "wish"]
SEED = 23


def latest(priv):
    files = sorted(Path(priv, "survey", "responses").glob("wave*_*.csv"))
    return files[-1] if files else None


def _wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return round(100 * p), round(100 * (c - h)), round(100 * (c + h))


def _pct(x):
    return int(round(100 * x))


def _gap_p(a, b, rng, n=20000):
    """Two-sided shuffle test on the difference between two shares (a, b: 0/1 arrays)."""
    obs = abs(a.mean() - b.mean())
    pool = np.r_[a, b]
    hits = 0
    for _ in range(n):
        rng.shuffle(pool)
        hits += abs(pool[:len(a)].mean() - pool[len(a):].mean()) >= obs - 1e-12
    return hits / n


def _share_bars(s, order):
    return [[lab, _pct((s == key).mean())] for lab, key in order]


def findings(path):
    d = pd.read_csv(path, encoding="utf-8-sig")
    d.columns = COLS
    d = d[d.age != "Under 18"].copy()
    n = len(d)
    rng = np.random.default_rng(SEED)
    ts = pd.to_datetime(d.ts.str.slice(0, 10), errors="coerce")
    d0, d1 = ts.min(), ts.max()
    span = f"{d0.day} to {d1.day} {d1.strftime('%B %Y')}" if d0.month == d1.month else f"{d0.strftime('%-d %B')} to {d1.strftime('%-d %B %Y')}"
    young = _pct((d.age == "18 to 24").mean())
    sample = (f"{n} adults answered a two-minute survey I shared between {span}. {young}% are aged 18 to 24, and they were reached "
              "through my own network, so these are signs from a young, social crowd rather than a measure of the whole city.")
    meta = {"n": n, "from": str(d0.date()), "to": str(d1.date()), "share_18_24": young, "file": Path(path).name,
            "last_visit_area": {a: int((d.area == a).sum()) for a in ("C-Scheme", "Malviya Nagar", "Somewhere else in Jaipur")}}
    out = []

    def add(fid, k, headline, body, limit, how, chart, data=None):
        v, lo, hi = _wilson(k, n)
        out.append({"id": fid, "value": v, "unit": "%", "headline": headline, "body": body, "limit": limit,
                    "grade": "Moderate", "source": "survey", "base": "people",
                    "how": [sample, f"The share is between {lo}% and {hi}% (95% Wilson interval)."] + how, "chart": chart, "n": n,
                    "data": data or {}})

    # 1. how people hear about a café
    wom = d.heard.isin(["A friend or family", "Instagram"])
    apps = d.heard.isin(["Google Maps", "Zomato or Swiggy"])
    fr, ig = d[d.heard == "A friend or family"], d[d.heard == "Instagram"]
    sign, sign_how, sign_data = "", [], {}
    if min(len(fr), len(ig)) >= 25:
        a, b = (fr.back == "Yes, definitely").values.astype(float), (ig.back == "Yes, definitely").values.astype(float)
        p = _gap_p(a, b, rng)
        if p < 0.01 and a.mean() > b.mean():
            sign = (f" An early sign worth watching: people who heard from a friend were more than twice as likely to say they'd definitely "
                    f"go back ({_pct(a.mean())}%) as people who found the café on Instagram ({_pct(b.mean())}%)."
                    if a.mean() >= 2 * b.mean() else
                    f" An early sign worth watching: people who heard from a friend were more likely to say they'd definitely go back "
                    f"({_pct(a.mean())}%) than people who found the café on Instagram ({_pct(b.mean())}%).")
            sign_data = {"friend_back": _pct(a.mean()), "insta_back": _pct(b.mean()), "n_friend": len(fr), "n_insta": len(ig)}
            sign_how = [f"Going back, by how they heard: {_pct(a.mean())}% of {len(fr)} who heard from a friend or family said \"Yes, definitely\", "
                        f"against {_pct(b.mean())}% of {len(ig)} who found it on Instagram. Shuffling those labels 20,000 times gives a gap this "
                        f"large {p:.4f} of the time. The groups are small, so the next survey wave is the real test."]
    add("survey_word_of_mouth", int(wom.sum()),
        "of people I asked heard about their last café from a friend, family or Instagram.",
        f"Only {_pct(apps.mean())}% found it on Google Maps or a delivery app. Ratings may confirm a choice, but the choice starts with "
        f"someone people know or a post they saw.{sign}",
        "It doesn't say ratings don't matter: people may still check them before they go.",
        [f"Friend or family {_pct((d.heard == 'A friend or family').mean())}%, Instagram {_pct((d.heard == 'Instagram').mean())}%, "
         f"walked or drove past {_pct((d.heard == 'Walked or drove past it').mean())}%, Google Maps {_pct((d.heard == 'Google Maps').mean())}%, "
         f"Zomato or Swiggy {_pct((d.heard == 'Zomato or Swiggy').mean())}%."] + sign_how,
        {"kind": "bars", "bars": _share_bars(d.heard, [("Friend or family", "A friend or family"), ("Instagram", "Instagram"),
                                                       ("Walked or drove past", "Walked or drove past it"), ("Google Maps", "Google Maps"),
                                                       ("Zomato or Swiggy", "Zomato or Swiggy")])},
        {"apps": _pct(apps.mean()), **sign_data})

    # 2. why they picked it
    place = d.reason.str.startswith("The place itself")
    menu, close, other = (d.reason == "For something specific on the menu"), (d.reason == "It was close by"), (d.reason == "Someone else chose it")
    add("survey_the_place", int(place.sum()),
        "of people I asked picked their last café for the place itself: the space and the vibe.",
        f"{_pct(menu.mean())}% came for something specific on the menu and {_pct(close.mean())}% because it was close by. "
        f"{_pct(other.mean())}% didn't choose at all: someone else did. A signature can be the room as much as a dish.",
        "It doesn't say the menu doesn't matter, only what tipped this visit.",
        [f"For the place itself {_pct(place.mean())}%, close by {_pct(close.mean())}%, something on the menu {_pct(menu.mean())}%, "
         f"someone else chose {_pct(other.mean())}%, to work or study {_pct((d.reason == 'Somewhere to work or study').mean())}%; the rest wrote their own reason."],
        {"kind": "bars", "bars": [["The place itself", _pct(place.mean())], ["Close by", _pct(close.mean())],
                                  ["Something on the menu", _pct(menu.mean())], ["Someone else chose", _pct(other.mean())]]},
        {"menu": _pct(menu.mean())})

    # 3. on the fence about returning
    maybe = d.back == "Maybe"
    add("survey_on_the_fence", int(maybe.sum()),
        "of people I asked are only \"maybe\" about going back to the café they last visited.",
        f"{_pct((d.back == 'Yes, definitely').mean())}% said yes, definitely, and {_pct((d.back == 'Probably not').mean())}% probably not. "
        "The undecided are the regulars still up for grabs: give them a reason to come back.",
        "It doesn't say why they're unsure, or that they won't return.",
        [],
        {"kind": "split", "parts": [["Yes, definitely", _pct((d.back == "Yes, definitely").mean())], ["Maybe", _pct(maybe.mean())],
                                    ["Probably not", 100 - _pct((d.back == "Yes, definitely").mean()) - _pct(maybe.mean())]]})

    # 4. the long table is friends, not laptops
    long_ = d.stay.isin(["1 to 2 hours", "Over 2 hours"])
    lg = d[long_]
    add("survey_long_stays", int(long_.sum()),
        "of people I asked stayed more than an hour on their last café visit.",
        f"{_pct((lg.doing == 'Catching up with someone').mean())}% of those long visits were people catching up with someone; "
        f"{int((lg.doing == 'Working or studying').sum())} of {len(lg)} were working or studying. The long table is friends, not laptops, "
        "so plan the room for small groups first.",
        "It doesn't say how much long visits spend, or how full the café was.",
        [f"Under 30 minutes {_pct((d.stay == 'Under 30 minutes').mean())}%, 30 minutes to an hour {_pct((d.stay == '30 minutes to 1 hour').mean())}%, "
         f"1 to 2 hours {_pct((d.stay == '1 to 2 hours').mean())}%, over 2 hours {_pct((d.stay == 'Over 2 hours').mean())}%."],
        {"kind": "bars", "bars": _share_bars(d.stay, [("Under 30 minutes", "Under 30 minutes"), ("30 minutes to 1 hour", "30 minutes to 1 hour"),
                                                      ("1 to 2 hours", "1 to 2 hours"), ("Over 2 hours", "Over 2 hours")])},
        {"catching_up": _pct((lg.doing == "Catching up with someone").mean()), "working": int((lg.doing == "Working or studying").sum()), "n_long": int(len(lg))})

    # 5. mornings are thin
    early = d.first_cup.isin(["Before 8am", "8am to 10am"])
    none_ = _pct((d.first_cup == "I don't, on weekdays").mean())    # Python 3.9: no backslash inside an f-string expression
    add("survey_mornings", int(early.sum()),
        "of people I asked have their first coffee or tea out before 10am on a weekday.",
        f"{none_}% don't buy one at all on weekdays, and {_pct((d.first_cup == 'After 12pm').mean())}% "
        "not until after noon. Morning trade depends on a crowd that's already out early, so check who's around you before opening early.",
        f"It doesn't speak for office workers near you: {young}% of the people I asked are aged 18 to 24.",
        [],
        {"kind": "bars", "bars": _share_bars(d.first_cup, [("Before 8am", "Before 8am"), ("8am to 10am", "8am to 10am"),
                                                           ("10am to 12pm", "10am to 12pm"), ("After 12pm", "After 12pm"),
                                                           ("Not on weekdays", "I don't, on weekdays")])},
        {"none": none_})
    return {"meta": meta, "findings": out}
