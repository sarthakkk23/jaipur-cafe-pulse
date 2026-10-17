# Jaipur Café Index

Jaipur's cafés, measured. (Formerly Jaipur Café Pulse.)

An independent, dated record of the café scene in C-Scheme and Malviya Nagar, Jaipur,
refreshed every two weeks. The public site shows aggregates only, and it names a café
only to credit it.

## How it fits together

```
private/                     RAW + PER-VENUE data. A separate private repo; gitignored here.
data/public/                 AGGREGATES: the only data the site reads (one file per snapshot).

pipeline/build_insights.py   private/raw -> data/public/insights_<snapshot>.json (suppresses small groups)
content/narrative.yaml       the site copy; numbers only via {{tokens}}; rewritten each run by Claude
content/kudos.yaml           the only place a café is named: sourced praise, approved by hand
pipeline/check_publish.py    the gate: no invented numbers, no names, no criticism, no leaks
pipeline/build_site.py       aggregates + copy + kudos + web/ -> dist/ (static, no framework)
web/assets/                  styles and the motion layer (scroll scenes, reveals, chart draw-in)
.github/workflows/site.yml   PRs: gate + preview build. main: gate + build + deploy to GitHub Pages
workflow/biweekly_refresh.md the scheduled Claude task: collect -> aggregate -> rewrite -> PR
```

## Build locally

```bash
./build.sh draft      # pending kudos shown with a badge
./build.sh publish    # pending kudos left out; refuses to build on any gate error
python3 -m http.server 8411 --directory dist
```

Live at https://sarthakkk23.github.io/jaipur-cafe-pulse once the first deploy runs.

## House rules

- Every figure has a source and a date. A blank beats a guess.
- Aggregates only. Any group smaller than `publish.min_group_size` (config.yaml) is hidden.
- No café's rating, review count or price is ever readable on the site.
- Cafés are named only through approved entries in `content/kudos.yaml`.
- Each data source is a module that can be switched off in `config.yaml`.

## Status

- [x] Site, motion layer, aggregates, publish gate, CI and Pages deploy, September 2026 baseline
- [ ] Collectors and refresh pipeline in `private/collect/`, per the pipeline spec.
      Needs the decision on which sources stay on.
- [ ] Author name, LinkedIn and email in `config.yaml`
- [ ] Kudos entries checked against their sources and approved
- [ ] Custom domain (optional)

## Licence

Code: MIT (see LICENSE). Published aggregates may be cited with attribution to Jaipur Café Index
and the snapshot date.
