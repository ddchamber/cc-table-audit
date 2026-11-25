# Table audit (Dan Chamberlin tab): state

Last updated: 2026-11-18. Plan: `PLAN.md` in this folder (approved by Dan in outline; no audit step run yet).

## Where it stands
- Sources read: `~/Downloads/Central Analytics schema cleanup review 2026-11-16.xlsx`, `~/Downloads/SKILL (1).md`
  (ca-table-audit procedure), `~/Downloads/README.md`.
- Sheet ID: `1A2E8CJUINNhTznKOvXaJcZOuRhs8cYxvw_SUcUnGZrE`, tab "Dan Chamberlin", 95 objects.
- Nothing in Databricks or the sheet has been changed.

## 2026-11-18 (afternoon): connections and step 1
- Google MCP works (tab list read). Databricks: use the REST API through `dbx_api.py` (Dan's call; the
  token is in the environment), warehouse `dbb3244d6fa2f0fc` (Serverless Starter). Signed in as
  dan.chamberlin@ticketmaster.com.
- Step 1 done: `objects.csv` has 95 rows. Prod is on sheet rows 7 to 77, nonprod on rows 88 to 111, and all 95
  exist in Databricks. Nonprod has 13 more VOC tables that are not on the tab; all 13 are owned by
  matthew.sutton (the `voc_gold_*` and `voc_*_fact_*` tables), so they are out of scope here.
- The tab's columns run A to Q, with "Your decision" in P and "Comment" in Q. The plan's "R to X" came from
  Matthew's layout, so check this before handing anything back.

## 2026-11-18: step 2 (facts) done
- Dan confirmed: local folders are Music and VOC under TM (`voc-dashboard-v2` and `VOCtest` also scanned as VOC).
- The personal token is SQL-only (403 "missing scopes" on dashboards, genie, jobs and workspace). Dashboards, Genie and
  job definitions are read in `step2b_sso_objects.py` through the SDK SSO login, run with the
  databricks-mcp venv python.
- Outputs: `facts/q1..q5*`, `facts/local_files.json`, `evidence_pack.json` (95 records; the .xlsx export rows match).
- Dashboards (2): "VoC Won-Loss Competitive Intelligence" (Matthew's) and "TM Music Post-Onsale Performance" (Dan's).
  Genie: the same two spaces, prod objects only (9 VOC, 6 Music). 8 Genie spaces are visible to Dan and 3 of them are
  unreadable (TikTok, Skai, Attendance), so a Genie miss is "not in any space Dan can see".
- Writer jobs: `music-dashboard-nightly` (Dan, run as Dan, 05:00 UTC; 8 of 13 runs succeeded in 30 days) and `CI-Bot`
  (shaan.arora, 0 of 13 succeeded; it reads VOC tables).
- Reader counts match Sachin's on 91 of 95 rows. The 4 that differ (rows 7, 17, 22, 42) differ because the 90-day
  window moved: Matthew's dashboard and ad-hoc reads on 11-16 and 11-18 are new, and one older reader dropped off
  row 7. No object Sachin marked Sandbox or Delete has another reader, a dashboard, a Genie space or a reading job.

## 2026-11-18: new full-access token
- Dan's new personal token passed every API check (identity, SQL, dashboards, Genie, jobs, workspace, Unity Catalog).
  It replaced the SQL-only token in `~/.claude/settings.json` and `~/.bashrc`; backups are `*.bak-2026-11-18`.
- From the next Claude Code start, `dbx_api.py` can do everything, so the SSO workaround in step2b is no longer needed.

## 2026-11-18: step 3 (breakage check) done
- `step3_breakage.py` -> `facts/breakage.json`; `step3_report.py` -> `breakage.md` (one row per object, what names it,
  what must change first). Searched: all views (27 name an object), 376 metric views (77 readable; 299 are 403),
  dashboard SQL for 4 dashboards (2 deleted, 404), Dan's 20 workspace files including `music_nightly/*.sql`, Genie,
  reading jobs, and tables built from each object in 365 days.
- All 42 objects Sachin marks Sandbox or Delete: nothing names them. Safe as is.
- 28 objects Sachin marks "Keep, move to silver": 13 have nothing pointing at them. The other 15 need changes first:
  11 Music nightly objects (edit `music_nightly` SQL files 01 to 10 and 99), 2 prod VOC mappings (repoint the views
  `voc_vw_sf_opportunities` and `voc_vw_interview_sf_link`, and tell Shaan about CI-Bot), and 2 nonprod objects
  (Matthew's `voc_gold_wonloss_interviews` was built from them on 07-30).
- CORRECTED later the same day: this does not block the prod moves. The owner of
  `prod_shared_silver.central_analytics_enr` is the team service principal `sp_prod_tm_central_analytics`, and the
  skill says moves happen by redeploying code under that principal. The real constraint is that `music-dashboard-nightly`
  runs as Dan and cannot write prod silver, so the job must move to the team principal in the same change.
- Original finding: in `prod_shared_silver.central_analytics_enr`, Dan's groups have read rights only. Dan writes gold through `cia-users` (CREATE_TABLE, MODIFY on `prod_shared_gold.central_analytics_crd`),
  and no group has those rights on prod silver. That schema's owner is service principal `29ac445e-...`. Nonprod silver
  does grant CREATE_TABLE and MODIFY to `team_tm_central_analytics_users`, so the 9 nonprod moves are possible.
- Metric views `mv_voc_wonloss` and `mv_voc_category_scores` (Matthew) read prod `voc_wonloss_interviews` and
  `voc_wonloss_category_scores`, both Keep and staying in gold.
- Next: step 4 (review in two groups, Music and VOC).

## 2026-11-18: steps 4 and 5 (review and fact-check) done
- Verdicts: `verdicts/music.csv` (54), `verdicts/voc.csv` (41). Merged and checked into
  `out/dan_chamberlin_audit_fact_checked.csv` by `step5_merge_check.py`: 95 rows, no missing, extra or duplicate rows,
  no dashes.
- Claude's calls: Delete 57, Move to silver 20, Keep as is 17, Your decision 1. Sachin's: Keep 53, Sandbox 24, Delete 18.
  Agree 54, Partly agree 25, Disagree 16. Confidence: High 84, Medium 10, Low 1.
- 8 risk flags were re-queried and all hold. The b4b5 and ctrl tables were written once by hand by Dan on 11-11, with
  no job and no other reader. Duygu's single read of step22 on 11-10 is already in the check column. The 3 nonprod
  VOC "named in code" hits are Dan's `.assistant/skills/voc-competitor-brief/SKILL.md`, which reads the prod copies.
- New facts from the reviewers: 3 Music queue backups hold fan ids (global_user_id, member_id); the interview loader
  package handed to Raines on 10-30 reads 4 VOC mappings by their prod gold names (update it before those move); the
  prod view `voc_vw_sf_opportunities` reads Salesforce from `finance_nonprod`; `recipient_email` is in the Qualtrics
  view.
- Next (step 6): write columns R to X on Dan's tab, plus a summary tab, ONLY after Dan says yes.

## 2026-11-18: Dan's answers (nothing changed yet, by his request)
- VOC: "this will need to be updated when new interviews are ingested, so keep them". Taken to mean the 14 nonprod
  VOC tables Claude called Delete. Still to confirm: the lineage shows no write to those copies since 07-22, while the
  prod tables are the ones the loader refreshes.
- `music_missing_revenue_events`: Dan does not know it, so it is not meant for readers. Built by `06_missing_revenue_events.sql` and
  read only by `05_lookup_show_rule.sql`, so it is a building block: Move to silver with its `_nightly` copy.
- CI-Bot: ignore its code; Dan will tell Shaan where to point it when the changes are made.
- Sheet: write later. Do nothing until Dan says so.

## 2026-11-23: live rechecks (read-only)
- Music safety (`step7_music_safety_live.py` -> `facts/music_safety_live.json`): the live dashboard (42 datasets,
  updated 11-20), the Genie space and all 12 nightly job files were scanned. 0 objects in use have a Delete verdict.
- 3 new tables are not on the tab (created after Sachin's sheet): `music_asu_tour_conversion_by_tour` (dashboard +
  Genie, gold), `music_asu_tour_conversion_by_tour_nightly` (job staging, silver), `music_dashboard_guide` (Genie, gold).
  The other 6 "not on tab" names (`_step17`, `_step18`, `_step19`, `_step21`) appear only in SQL comments and do not exist.
- Nonprod VOC (`step8_voc_nonprod_live.py`): all 24 created and written once on 07-22 by Dan, never again; 0 other
  readers in 90 days. 14 have prod twins that the loader refreshes (latest 10-30); 10 have no prod twin.
- Column layout settled: the skill says to add new columns R to X and never touch A to Q, so P and Q stay Dan's.

## 2026-11-23: step 6 done, sheet written (audit complete)
- Dan's answers applied (`step9_apply_dan_answers.py` -> `out/dan_chamberlin_audit_final.csv`): nonprod VOC 24 Delete
  (confirmed), music_missing_revenue_events Move to silver. Two Music "why" texts corrected after the 11-20 dashboard
  edit (music_asu_tour_conversion, music_asu_event_signups: still Keep, dashboard no longer reads them directly).
- Final: Delete 57, Move to silver 21, Keep 17; Agree 54, Partly 25, Disagree 16; High 85, Medium 10.
- Written to the sheet: 'Dan Chamberlin' R5:X6 and R86:X87 (band and headers), R7:X77 and R88:X111 (95 rows), via
  `out/sheet_chunks/*.json`. Read back R, S, T and W: counts match the final file. Columns A to Q untouched.
- New tab 'Claude challenge - Dan summary' (gid 610264818): totals, why the reviews differ, facts before acting,
  the 3 tables not on the tab, and the 10 Medium rows to check.
- Not part of this audit: the actual moves and deletes (later, by redeploying under sp_prod_tm_central_analytics).

## 2026-11-23: token and silver access
- Old SQL-only token (dbx-cc) and both .bak-2026-11-18 files were already gone before this session; nothing to do.
  Active tokens: 'music nightly', 'jobs/workspace/dashboard', 'All-aboard'. Current token works.
- Prod silver `central_analytics_enr` (checked live): team_tm_central_analytics_users has read only (SELECT,
  USE_SCHEMA, EXECUTE, READ_VOLUME); owner is sp_prod_tm_central_analytics (29ac445e-...). Nonprod silver: the same
  group has full write. Recommended ask: 'Service principal: User' on sp_prod_tm_central_analytics so Dan can set
  music-dashboard-nightly to run as it. Who administers the principal was not visible to Dan's token.

## 2026-11-23: Your decision pre-filled (Dan's request)
- P7:Q77 and P88:Q111 written by `step11_your_decision_payload.py`: Keep 38 (17 stay, 21 moves with the silver
  destination in Comment), Delete 57. P is a Keep / Sandbox / Delete / Not sure dropdown, so moves are Keep.
- Nightly job facts for the job move (from TM/Music/sql/nightly): every file writes fixed prod_shared_gold names
  (01 to 09 CREATE OR REPLACE, 10_gate MERGE into the gate log, 99_publish DEEP CLONE onto the live names); 04 reads
  music_phase_alias, which the job never rebuilds; files live in Dan's workspace folder; job reads about 40 outside
  tables in 6 catalogs (`facts/nightly_outside_sources.txt`), which the service principal would need to read.

## Before step 1 (resolved, kept for history)
1. **Google:** `google-mcp@techops-marketplace` v0.1.2 is installed. After restart, finish Okta sign-in, then the
   Google consent (`https://google.mcp.tmaws.io/google/authorize`, @ticketmaster.com account). Test: list the
   sheet's tabs. Error 403 org_internal: retry in Incognito.
2. **Databricks:** the databricks-sso `test_connection` hung for 30 minutes on 2026-11-18 with two server
   processes running. Make sure only one runs after restart, finish SSO, test again.
3. **Confirm with Dan:** Databricks user `dan.chamberlin@ticketmaster.com`; project folders under
   `C:\Users\dan.chamberlin\TM\` (Music, VOC) plus `~/Vault/`.

## Next
Run PLAN.md steps 1 to 3: objects.csv with tab row numbers, the five fact queries, the local-file scan, and the
breakage check.
