# Music nightly silver move: prep plan (draft 2026-11-23, awaiting Dan's OK)

Goal: when the cleanup move happens, the switch of music-dashboard-nightly to silver is a tested, one-day change.
Nothing in prod is changed by this plan.

## What we found first (2026-11-23)
- The 11 deployed job files match `TM/Music/sql/nightly/` exactly, so those files are the starting point.
- The old generators (`tasks/step20/make_nightly.py`, `tasks/step22-part2/make_nightly_part2.py`) are out of date:
  later fixes (flush rule 11-17, by-tour 11-18) edited `sql/nightly/` directly. Rerunning a generator would bring
  old logic back, so the rename works on the current files, not by regenerating.
- Nonprod: Dan can write nonprod silver, only read nonprod gold. Prod silver: read only.

## Steps
1. **Name map** (`name_map.csv`): every table the job names, with its prod target (13 to silver, 9 published
   tables stay gold) and its dry-run target. Done when: every music_* name in the 11 files is in the map once.
2. **Rename script** (`make_silver_files.py --target prod|dryrun`): copies the 11 files and swaps fully quoted
   names only (no hand edits), then refuses to write a file that still names an unmapped table. Done when: both
   outputs are written and the check passes.
   - `prod` output: what ships on move day. Staging, alias, gate log and missing revenue in
     `prod_shared_silver.central_analytics_enr`; the 9 published names stay in `prod_shared_gold`.
   - `dryrun` output: everything the job writes goes to `nonprod_shared_silver.central_analytics_enr`; the gate
     still compares against today's prod gold live tables (read only). Step 99 (publish) and the dashboard refresh
     are left out of the dry run, because publishing would need nonprod gold write rights.
3. **Compile check**: EXPLAIN every file of both outputs (same approach as `explain_nightly.py`). Done when: all OK.
4. **Dry run, once, by hand**: copy `music_phase_alias` into nonprod silver, then run files 01 to 10 of the dryrun
   output as a separate, paused job named `music-nightly-silver-dryrun` (run as Dan). Done when: the gate passes
   and the row counts match tonight's prod run.
   - Cost: the real job takes about 3h45m on warehouse `dbb3244d6fa2f0fc` and writes about 90 GB (two 45 GB queue
     copies). Run it outside the 05:00 to 09:00 UTC prod window.
5. **Move-day kit** (prepared, not run): the prod files from step 2; a `job.json` with run_as set to
   `sp_prod_tm_central_analytics`; SQL to copy `music_phase_alias` and the gate log history into prod silver;
   the order of operations; and the list of about 40 source tables the service account must be able to read.
6. **Clean up the dry run**: drop the dry-run tables in nonprod silver and delete the dry-run job, after Dan says so.

## What the dry run proves, and what it does not
- Proves: the renamed SQL is complete and correct, and the build works with its working tables in silver.
- Does not prove: that the team service account can read every source table. Only someone with that account can
  test it, so it goes on the move-day questions.
