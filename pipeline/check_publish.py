"""Publish gate. Fails (exit 1) if anything public could break the house rules:

  1. every {{token}} in the copy resolves to a real, unsuppressed value
  2. the copy contains no literal figures (all numbers come through tokens)
  3. no café is named outside content/kudos.yaml
  4. kudos entries are sourced and carry no platform metrics
  5. the public data and the built site contain no venue IDs or names
     (other than kudos entries included in that build)

Warnings (exit 0) flag tone: words that read as criticism.

Usage: python pipeline/check_publish.py [--mode draft|publish] [--html dist/index.html]
"""
import argparse, json, re, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TOKEN = re.compile(r"{{\s*([\w.]+)\s*}}")
ALLOWED_LITERALS = [
    re.compile(r"\b\d{1,2}(:\d{2})?\s?(am|pm)\b", re.I),   # clock times that define a question
    re.compile(r"\b(19|20)\d{2}\b"),                        # years
    re.compile(r"\btop 10%"),                               # the decile we describe
    re.compile(r"\b4\.8\b"),                                # the rating threshold
]
NEGATIVE = ["worst", "bad", "poor", "failing", "fail", "struggl", "declin", "avoid", "overpriced",
            "dirty", "flop", "lowest", "terrible", "disappoint", "mediocre", "weak", "losing"]
KUDOS_FORBIDDEN = [
    (re.compile(r"\b[1-5]\.\d\b"), "looks like a rating"),
    (re.compile(r"review", re.I), "mentions reviews"),
    (re.compile(r"rating|rated|stars?\b|★", re.I), "mentions ratings"),
    (re.compile(r"₹|\brs\.?\s?\d|cost for", re.I), "mentions prices"),
    (re.compile(r"\b(ranked|ranking|#\d)", re.I), "ranks cafés"),
]
GENERIC = {"cafe", "coffee", "tea", "chai", "bakery", "bakers", "house", "kitchen", "shop", "bar",
           "restaurant", "lounge", "point", "corner", "express", "the", "cafe coffee", "coffee house",
           "tea house", "food", "foods", "bistro", "brew", "brews", "dessert", "desserts", "cake", "cakes"}
FIG_ID = re.compile(r"FIG-(CS|MN)-\d{4}")


def norm(s):  # same normalisation family as the consolidation step
    s = (s or "").lower().replace("&", " and ").replace("café", "cafe").replace("caffe", "cafe")
    s = re.sub(r"\|.*$", "", s)
    s = re.sub(r"\b(c[\s-]?scheme|malviya nagar|jaipur|wtp|world trade park|gaurav tower|gt|the|"
               r"cafe and restaurant|restro|and|by|co|company|pvt|ltd)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings(v, f"{path}[{i}]")


def venue_names(cfg):
    """Distinctive normalised venue names from the raw master (local runs only)."""
    xlsx = ROOT / cfg["baseline"]["dataset_xlsx"]
    if not xlsx.exists():
        return None
    import pandas as pd
    names = pd.read_excel(xlsx, "Cafe_Master", usecols=["name"])["name"].dropna()
    out = set()
    for n in names:
        k = norm(n)
        if len(k) >= 5 and k not in GENERIC and not all(w in GENERIC for w in k.split()):
            out.add(k)
    return out


def find_names(text, names):
    t = " " + norm(text) + " "
    return sorted(n for n in names if f" {n} " in t)


def check(mode="draft", html_path=None):
    cfg = yaml.safe_load(open(ROOT / "config.yaml"))
    ins = json.load(open(ROOT / "data/public/insights_latest.json"))
    nar = yaml.safe_load(open(ROOT / "content/narrative.yaml"))
    kud = yaml.safe_load(open(ROOT / "content/kudos.yaml"))["entries"]
    tokens = ins["tokens"]
    errors, warnings = [], []
    names = venue_names(cfg)
    if names is None:
        warnings.append("raw master not present; venue-name scan skipped (run locally before publishing)")
        names = set()
    included = [k for k in kud if k.get("approved") or mode == "draft"]
    allowed_names = {norm(k["name"]) for k in included}
    # Sarthak's named top-café picks may be named; their pages carry facts only
    tops = (yaml.safe_load(open(ROOT / "content/top_cafes.yaml")) or {}).get("entries") or []
    allowed_names |= {norm(t["name"]) for t in tops}

    if nar.get("written_for_snapshot") != ins["meta"]["snapshot"]:
        errors.append(f"narrative was written for {nar.get('written_for_snapshot')}, "
                      f"data is {ins['meta']['snapshot']}: rewrite the copy for this snapshot")

    # 1-3: narrative (only the copy that will render: the time machine has a first-run variant)
    scan = {k: v for k, v in nar.items() if k != "written_for_snapshot"}
    if "timemachine" in scan:
        has = "changes" in ins.get("insights", {})
        scan["timemachine"] = {k: v for k, v in scan["timemachine"].items()
                               if (k.endswith("_first") and not has) or (not k.endswith("_first") and (has or k in ("eyebrow", "note")))}
    for path, text in strings(scan):
        for t in TOKEN.findall(text):
            if t not in tokens:
                errors.append(f"{path}: unknown token {{{{{t}}}}}")
            elif tokens[t] in ("—", "", None):
                errors.append(f"{path}: token {{{{{t}}}}} is suppressed or empty; rewrite without it")
        bare = TOKEN.sub(" ", text)
        for rx in ALLOWED_LITERALS:
            bare = rx.sub(" ", bare)
        if re.search(r"\d", bare):
            found = re.findall(r"[^ ]*\d[^ ]*", bare)[:3]
            errors.append(f"{path}: literal figure in copy ({found}); use a token")
        hits = find_names(text, names)
        if hits:
            errors.append(f"{path}: names a café ({', '.join(hits)}); names belong only in kudos.yaml")
        low = text.lower()
        for w in NEGATIVE:
            if re.search(rf"\b{w}", low):
                # house rule: never criticise. Draft builds warn; publish builds refuse.
                (errors if mode == "publish" else warnings).append(f"{path}: '{w}…' may read as criticism")

    # 4: kudos
    for k in kud:
        where = f"kudos[{k.get('id')}]"
        if not k.get("sources") or not all(s.get("url") and s.get("date") for s in k["sources"]):
            errors.append(f"{where}: every source needs a url and a date")
        for rx, why in KUDOS_FORBIDDEN:
            if rx.search(k.get("praise", "")):
                errors.append(f"{where}: praise {why}; kudos never carry platform metrics")
        for w in NEGATIVE:
            if re.search(rf"\b{w}", k.get("praise", "").lower()):
                errors.append(f"{where}: praise contains '{w}…'")
        if k.get("approved") and not k.get("approved_on"):
            errors.append(f"{where}: approved without approved_on date")
    pending = [k["id"] for k in kud if not k.get("approved")]
    if pending:
        warnings.append(
            f"{len(pending)} kudos awaiting approval ({', '.join(pending)}); "
            + ("shown with a draft badge" if mode == "draft" else "left out of this build"))

    # 5: public data and built site
    for p in ins.get("profiles") or []:
        texts = [x["text"] for x in p.get("story", [])] + [x["t"] for x in p.get("signals", [])] + [p.get("tagline", ""), p.get("notes", "")]
        for t in texts:
            for rx, why in KUDOS_FORBIDDEN:
                if rx.search(t):
                    errors.append(f"profile[{p['slug']}]: text {why}: '{t[:60]}…'")
            for w in NEGATIVE:
                if re.search(rf"\b{w}", t.lower()):
                    errors.append(f"profile[{p['slug']}]: contains '{w}…'")
    blob = json.dumps(ins, ensure_ascii=False)
    if FIG_ID.search(blob):
        errors.append("public insights contain a private venue ID")
    leaked = [n for n in find_names(blob, names) if not any(n in a or a in n for a in allowed_names)]
    if leaked:
        errors.append(f"public insights contain venue names: {leaked[:5]}")
    pages = [Path(html_path)] if html_path else []
    if html_path:
        pages += sorted(Path(html_path).parent.glob("cafes/*/index.html"))
    for page in pages:
        if not page.exists():
            continue
        html = page.read_text()
        text = re.sub(r"<[^>]+>", " ", html)
        if FIG_ID.search(html):
            errors.append(f"{page.name if page == Path(html_path) else page.parent.name}: contains a private venue ID")
        leaked = [n for n in find_names(text, names) if not any(n in a or a in n for a in allowed_names)]
        if leaked:
            errors.append(f"{page.parent.name}: names cafés outside kudos/top picks: {leaked[:5]}")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["draft", "publish"], default="draft")
    ap.add_argument("--html")
    a = ap.parse_args()
    errors, warnings = check(a.mode, a.html)
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{'FAILED' if errors else 'OK'}: {len(errors)} errors, {len(warnings)} warnings ({a.mode})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
