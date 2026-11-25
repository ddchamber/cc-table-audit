# Music nightly silver move prep: state

Last updated: 2026-11-23. Plan: `PLAN.md` in this folder (drafted, awaiting Dan's OK). Parent: `../STATE.md`.

## Where it stands
- Baseline checked (`check_baseline.py`): the 11 deployed job files in
  `/Users/dan.chamberlin@ticketmaster.com/music_nightly/` match `TM/Music/sql/nightly/` exactly.
- Old generators are out of date (later fixes edited `sql/nightly/` directly), so the rename works on the current
  files, not by regenerating.
- Nonprod gold: Dan's groups have SELECT only. Nonprod silver: full write (team_tm_central_analytics_users).
- Nothing built, run or changed yet.

## Next
TABLED 2026-11-23 by Dan: he will discuss with his manager whether the prep is needed. Nothing was built. If it
resumes, start at PLAN.md step 1; re-run check_baseline.py first, because the job files may have changed.
