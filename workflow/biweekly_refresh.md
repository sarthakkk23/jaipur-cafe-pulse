# Biweekly refresh — scheduled Claude task prompt

Installed as a desktop-app scheduled task, weekly on Monday at 11:00 IST (`0 11 * * 1`);
the parity check below skips alternate weeks, since plain cron can't say "every other week".

---

You are refreshing **Jaipur Café Index** (formerly Jaipur Café Pulse), an independent record of cafés in C-Scheme and
Malviya Nagar, Jaipur. Project folder: `/Users/sarthak/Documents/projects/consulting-business/cafes`.
Work only inside it. Two git repositories live here:
- the folder itself → `sarthakkk23/jaipur-cafe-pulse` (public: site, aggregates, copy)
- `private/` → `sarthakkk23/jaipur-cafe-pulse-data` (private: raw pulls, per-venue data)

Never copy anything from `private/` into the public repo except through
`pipeline/build_insights.py`.

## 0. Should this run happen?
- Compute today's ISO week number. If it is **odd**, stop and report "off-week, skipped".
- `git pull` in both repos. Read `config.yaml`; collect only from sources set to `true`.

## 1. Collect and process (private/collect, private/process; spec §2–8)
- `.venv/bin/python private/collect/run_collect.py --label <YYYY-Www>` opens headed Chrome (headless is
  refused) and saves raw pulls to `private/raw/<YYYY-Www>/` before any processing. Takes 45–75 minutes.
  If Zomato rate-limits detail pages (429), the collector pauses and retries once, slowly. Never more.
- `.venv/bin/python private/process/run_refresh.py --label <YYYY-Www>`: QA, consolidation (regression-
  tested port), venue ID carry-over, snapshot rows, master, run report in `private/reports/runs/`.
- A source that fails QA is null for this run (never reuse last run's numbers); a site that blocks or
  shows a CAPTCHA is recorded as failed, never worked around. A fatal QA failure stops everything.
- Commit and push `private/`: `git -C private add -A && git -C private commit -m "run <YYYY-Www>" && git -C private push`.

## 2. Rebuild the aggregates
- Run `.venv/bin/python pipeline/build_insights.py`.
- Compare `data/public/insights_latest.json` with the previous `insights_<label>.json`.

## 3. Rewrite every insight: `content/narrative.yaml`
Set `written_for_snapshot` to the new label, then rewrite the copy for this snapshot.
- Every figure comes in as a `{{token}}`. Never type a number. Allowed literals: clock
  times ("8am"), years, "top 10%", "4.8".
- If a token is missing or suppressed ("—"), rewrite the sentence without it.
- Lead each section with what's most useful to someone who runs, or is opening, a café.
  Where something moved since the last snapshot, say what moved, with tokens.
- Verify every claim that isn't a token (e.g. "lower for every café type") against the JSON.
  If you can't verify it, cut it.
- Never name a café. Never criticise a café, an area or a type of café.
- Say plainly what the data can't show (correlation, listed vs real, attention vs sales).

## 4. Kudos: `content/kudos.yaml`
- On the first run of each month, look for new public press about café openings and
  milestones in the two areas. Add candidates with `approved: false`, each with a source
  URL and date, praise only: no ratings, review counts, prices or ranks.
- Never set `approved: true`. Only Sarthak approves.

## 5. Check locally (the full gate, including the venue-name scan CI can't run)
- Run `./build.sh publish`. It must finish with **0 errors**. If not, fix the copy and rerun
  (at most three attempts), then stop and report what failed.
- Write `private/reports/runs/<YYYY-MM-DD>.md`: counts by source and area, QA results, new
  and missing venues (counts only), suppressed cells, which sections changed and why,
  kudos proposed. Commit and push `private/`.

## 6. Open the pull request
- `git switch -c refresh/<YYYY-MM-DD>`; commit `data/public/` and `content/`; push.
- `gh pr create --title "Refresh <YYYY-MM-DD> (snapshot <label>)" --body "<three-line summary of
  what changed, suppressed cells, kudos awaiting approval>"`.
- CI runs the gate and builds a preview. Sarthak reviews and merges; merging deploys the site.
- If `config.yaml` → `publish.auto_publish` is `true`, merge the PR yourself once CI passes:
  `gh pr merge --squash --auto`.
