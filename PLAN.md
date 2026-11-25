# Table audit plan: Dan Chamberlin tab (draft 2026-11-18, awaiting Dan's OK)

Sources: `Downloads/Central Analytics schema cleanup review 2026-11-16.xlsx`, `Downloads/SKILL (1).md`
(ca-table-audit, the procedure used on Matthew's tab), `Downloads/README.md`.

## What is in scope
- 95 objects on Dan's tab: 71 prod, 24 nonprod; all in `*_shared_gold.central_analytics_crd` today.
- 54 Music, 41 VOC; 91 tables, 4 views.
- Sachin's suggested calls: Keep 53, Sandbox 24, Delete 18.
- Reference: on Matthew's tab Claude disagreed with Sachin on 177 of 376 objects.

## Steps
1. **Set up.** This folder plus `STATE.md`. Pull the 95 objects with full names and exact tab row numbers
   into `objects.csv`.
2. **Gather facts (read-only, one batch query each).**
   - Q1 metadata and comments (`system.information_schema.tables`).
   - Q2 readers, 90 days (`system.access.table_lineage`), excluding Dan's own reads, Sachin's inventory crawl
     (09-29, 11-16) and service-account metadata sweeps.
   - Q3 upstream sources and writer jobs, 365 days.
   - Q4 job names, run_as, 30-day run health (`system.lakeflow.jobs`, `job_run_timeline`).
   - Q5 dashboard names and Genie spaces (full-name match, so nonprod and prod copies stay separate).
   - Local evidence: ripgrep every table name (LF pattern file) over `C:\Users\dan.chamberlin\TM\` project
     folders and `~/Vault/`.
3. **Breakage check (added beyond the skill, because the goal is that everything still works).** For every
   object that would move or be deleted, list everything that names it:
   - views whose stored SQL mentions it (`information_schema.views.view_definition`; lineage can miss these);
   - dashboard dataset SQL;
   - job and notebook code that writes it (for example the nightly deep clone from `_nightly` to published).
   Output: "what must change before this moves" per object.
4. **Review in two groups, Music and VOC, in parallel.** Apply the skill's placement rules; do not take
   Sachin's call at face value. Already flagged to test:
   - 24 Sandbox calls (`_step16`, `_step22`, `_b4b5`, `_ctrl` builds): rules prefer Delete when nothing reads it
     and the logic is kept elsewhere.
   - VOC mapping tables marked "move to silver": several are read directly by 3 to 6 people; rules put directly
     read objects in gold.
   - `music_event_phase_summary_step22`: Keep only because one person read it once.
   - 24 nonprod objects: any backing a dashboard or read by others on a schedule becomes Promote to prod.
   - `_nightly` staging tables to silver: each needs the job code changed first.
5. **Fact-check.** Re-query any Delete or Sandbox with a reader, dashboard, Genie space or recent job write;
   correct missed readers. Every object has exactly one row.
6. **Hand back, write nothing.** No Google connection, so deliver an .xlsx with columns R to X keyed to Dan's
   tab row numbers (paste-ready) plus a summary tab in the same layout as Matthew's. Show totals and 5 sample
   rows first and get a yes.

Nothing in Databricks is changed: no DROP, ALTER, CREATE or GRANT.

## Open items
- Databricks MCP connection test was still running after 2 minutes; SSO sign-in may need refreshing.
- Confirm Databricks user `dan.chamberlin@ticketmaster.com` and project folders under `C:\Users\dan.chamberlin\TM\`.
- README expects a "google-mcp plugin"; ask Matthew or the manager how they connected (may avoid an IT request).
