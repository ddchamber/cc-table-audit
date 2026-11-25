"""Write verdicts/music.csv: one placement verdict per Music object, challenging Sachin's call.

Read-only with respect to Databricks and the sheet. Evidence comes from batches/music.json, breakage.md,
the Music project files named in each row, and two read-only queries saved under facts/
(music_fan_columns.csv, music_hist_eps.csv).
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

AUDIT_FOLDER: Path = Path(r"C:\Users\dan.chamberlin\TM\table-audit")
BATCH_PATH: Path = AUDIT_FOLDER / "batches" / "music.json"
OUTPUT_PATH: Path = AUDIT_FOLDER / "verdicts" / "music.csv"
GOLD_PREFIX: str = "prod_shared_gold.central_analytics_crd."
SILVER_PREFIX: str = "prod_shared_silver.central_analytics_enr."

records: list[dict] = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
records_by_short_name: dict[str, dict] = {record["full_name"].removeprefix(GOLD_PREFIX): record for record in records}

# Tables whose columns include fan identifiers (facts/music_fan_columns.csv: global_user_id, member_id).
FAN_ID_TABLES: set[str] = {"music_queue_member_fact_step16", "music_queue_member_fact_step16_live", "music_queue_member_fact_step22"}

JOB_MOVE_NOTE: str = (
    "Ships with the job move: music-dashboard-nightly runs as Dan, who cannot write prod silver, so the job must run as "
    "sp_prod_tm_central_analytics. Change the name in the generator and regenerate the music_nightly files, do not "
    "hand-edit 01 to 09 (sql/nightly/README.md). Files to change: {files}. Delete the old gold copy after the first "
    "green run. Tell Sachin Dewangan the move waits on that change."
)


def summarize_other_readers(record: dict) -> str:
    """Collapse other_reader_detail into 'name (days, last date, via)' per person."""
    days_by_reader: dict[str, int] = defaultdict(int)
    last_by_reader: dict[str, str] = {}
    via_by_reader: dict[str, set[str]] = defaultdict(set)
    for detail in record.get("other_reader_detail") or []:
        reader_name: str = detail["reader"].split("@")[0]
        days_by_reader[reader_name] += int(detail.get("read_days") or 0)
        last_by_reader[reader_name] = max(last_by_reader.get(reader_name, ""), detail.get("last_read") or "")
        via: str = detail.get("read_via") or "ad hoc"
        via_by_reader[reader_name].add({"DASHBOARD_V3": "dashboard", "DBSQL_QUERY": "SQL editor", "JOB": "a job"}.get(via, via))
    if not days_by_reader:
        return "No other reader in 90 days"
    ordered_readers: list[str] = sorted(days_by_reader, key=lambda name: -days_by_reader[name])
    parts: list[str] = [
        f"{name} ({days_by_reader[name]} days, last {last_by_reader[name][5:]}, {' and '.join(sorted(via_by_reader[name]))})"
        for name in ordered_readers
    ]
    return f"{len(ordered_readers)} other readers in 90 days: " + "; ".join(parts)


def looked_at_note(record: dict) -> str:
    """Pull Sachin's 'looked at by ... not queried' note, which is UI viewing and not use."""
    match = re.search(r"looked at by ([^·]+?), not queried", record["sachin"].get("why", ""))
    if not match:
        return ""
    return f"Viewed in the UI without a query by {match.group(1).strip()}, which does not count as use"


def code_files(record: dict) -> tuple[list[str], list[str]]:
    """Return (files that write it, files that read it) among the workspace code."""
    writers: list[str] = []
    readers: list[str] = []
    for item in record.get("named_by_workspace_code") or []:
        file_name: str = item["where"].split("/")[-1]
        (writers if item.get("writes_it") else readers).append(file_name)
    return sorted(set(writers)), sorted(set(readers))


def basic_facts(record: dict) -> list[str]:
    """Facts every row carries: readers, dashboards, Genie, size, last write, owner reads."""
    sachin: dict = record["sachin"]
    facts: list[str] = [summarize_other_readers(record)]
    if record.get("dashboards"):
        facts.append("Dashboard: " + ", ".join(dashboard["name"] for dashboard in record["dashboards"]))
    if record.get("genie_spaces"):
        facts.append("Genie: " + ", ".join(record["genie_spaces"]))
    writes: dict = record.get("writes_365d") or {}
    if writes:
        facts.append(f"Last write {writes.get('last_write')} ({writes.get('write_days')} write days in 365)")
    facts.append(f"Created {record['metadata']['created'][:10]}; size {sachin.get('size_gb')} GB; owner's own reads in 90 days: {record.get('owner_read_days_90d')} (not counted)")
    if record.get("sachin_crawl_dates"):
        facts.append("Sachin's inventory crawl also read it, not counted")
    if record.get("service_principal_readers"):
        facts.append("Service principal metadata sweeps, not counted")
    note: str = looked_at_note(record)
    if note:
        facts.append(note)
    if record["full_name"].removeprefix(GOLD_PREFIX) in FAN_ID_TABLES:
        facts.append("FAN DATA: columns global_user_id and member_id (fan identifiers)")
    facts.append("Nothing else names it (breakage.md)" if not (record.get("named_by_workspace_code") or record.get("named_by_views") or record.get("named_by_dashboard_datasets")) else "")
    return [fact for fact in facts if fact]


verdicts: dict[str, dict] = {}


def add_verdict(short_name: str, my_call: str, vs_sachin: str, why: str, extra_facts: list[str], confidence: str, check: str, target: str = "") -> None:
    record: dict = records_by_short_name[short_name]
    if my_call == "Keep as is":
        target = record["full_name"] + " (stays here)"
    elif my_call == "Move to silver":
        target = SILVER_PREFIX + short_name
    verdicts[short_name] = {
        "sheet_row": record["sheet_row"],
        "full_name": record["full_name"],
        "my_call": my_call,
        "target": target,
        "vs_sachin": vs_sachin,
        "why": why,
        "facts": ". ".join(basic_facts(record) + extra_facts),
        "confidence": confidence,
        "check_before_acting": check,
    }


# ---------- Published tables the dashboard, Genie space and other people read: keep in gold ----------
published_tables: dict[str, str] = {
    "music_artist_lookup": "Event lookup behind every dropdown and card",
    "music_event_phase_summary": "Per event and sale phase summary",
    "music_queue_member_fact": "Queue member fact (one row per fan in a queue)",
    "music_benchmark_stats": "Benchmark statistics for the comparison cards",
    "music_str_daily": "Daily sell-through table",
    "music_asu_tour_conversion": "Artist Sign Up conversion per campaign group",
    "music_asu_event_signups": "Artist Sign Up sign-ups per event",
    "music_benchmark_events": "Benchmark events table, new on 11-10",
}
for short_name, description in published_tables.items():
    record = records_by_short_name[short_name]
    reader_count: int = len({detail["reader"] for detail in record.get("other_reader_detail") or []})
    has_genie: bool = bool(record.get("genie_spaces"))
    surface: str = "the TM Music Post-Onsale Performance dashboard" + (" and Genie space" if has_genie else "")
    why: str = (
        f"{description}, published by the nightly job and read by {surface}. "
        f"{reader_count} other {'person reads' if reader_count == 1 else 'people read'} it. It is what consumers use, so it stays in gold."
    )
    extra: list[str] = ["Writer: music-dashboard-nightly, 99_publish.sql deep clones the _nightly copy onto this name"]
    if short_name == "music_asu_tour_conversion":
        extra.append("sean.poole's job 997576095041121 read it on 11-09")
    if short_name in ("music_benchmark_stats", "music_asu_event_signups"):
        why += " Sachin's 'fading, ask the readers' note does not change it, because the dashboard reads it every day."
    add_verdict(
        short_name, "Keep as is", "Agree", why, extra, "High",
        "Nothing to do. If the nightly job later moves to sp_prod_tm_central_analytics, keep this published name in 99_publish.sql.",
    )

# ---------- Nightly staging and intermediates: move to silver with the job ----------
staging_tables: dict[str, str] = {
    "music_artist_lookup_nightly": "Nightly staging copy of music_artist_lookup",
    "music_artist_lookup_nightly_base": "Nightly base event universe that feeds the queue fact, daily STR, phase summary and final lookup builds",
    "music_asu_event_signups_nightly": "Nightly staging copy of music_asu_event_signups",
    "music_asu_tour_conversion_nightly": "Nightly staging copy of music_asu_tour_conversion",
    "music_benchmark_events_nightly": "Nightly staging copy of music_benchmark_events",
    "music_benchmark_stats_nightly": "Nightly staging copy of music_benchmark_stats",
    "music_event_phase_summary_nightly": "Nightly staging copy of music_event_phase_summary",
    "music_missing_revenue_events_nightly": "Nightly staging copy of music_missing_revenue_events",
    "music_queue_member_fact_nightly": "Nightly staging copy of music_queue_member_fact",
    "music_str_daily_nightly": "Nightly staging copy of music_str_daily",
}
for short_name, description in staging_tables.items():
    record = records_by_short_name[short_name]
    writer_files, reader_files = code_files(record)
    is_base: bool = short_name.endswith("_base")
    why = (
        f"{description}. The nightly job builds it, {'reads it in later steps' if is_base else 'checks it in the gate and clones it onto the published name'}, "
        "and nobody but the job and Dan reads it. That is a silver building block, so it moves to silver."
    )
    extra = [f"Written by {', '.join(writer_files)}; read by {', '.join(reader_files)} (music_nightly, job 489488962317323)"]
    add_verdict(
        short_name, "Move to silver", "Agree", why, extra, "High",
        JOB_MOVE_NOTE.format(files=", ".join(writer_files + reader_files)),
    )

add_verdict(
    "music_phase_alias", "Move to silver", "Agree",
    "Hand-kept map from raw SmartQueue phase names to one clean name; the nightly phase summary reads it every night. "
    "Mapping tables are silver, and no dashboard, Genie space or other person reads it.",
    ["Comment: 'Phase name aliases for the TM Music post-onsale dashboard. One canonical name per raw SmartQueue phase name'",
     "Written once on 09-16 by hand (sql/materialized/00_music_phase_alias.sql); read by 04_event_phase_summary.sql"],
    "High",
    "The nightly job never rebuilds it, so copy the table as is (do not rerun the seed blindly). " + JOB_MOVE_NOTE.format(files="04_event_phase_summary.sql"),
)

add_verdict(
    "music_nightly_gate_log", "Move to silver", "Disagree",
    "Log of every nightly gate check, pass or fail. Pipeline bookkeeping is silver by role, and no dashboard, Genie space or other person reads it. "
    "Sachin keeps it in gold beside what it gates, but the rule places by role, not by neighbour.",
    ["Comment: 'Nightly refresh gate results, written by sql/nightly/10_gate.sql'", "Written by 10_gate.sql; listed as a pipeline table on the Confluence pipeline page (tasks/confluence-step21/changes-part3.md)"],
    "High",
    "Copy the existing history across first so past nights are kept, then point 10_gate.sql at silver. Update the 'why a night failed' query in sql/nightly/README.md and the Confluence table row. "
    + JOB_MOVE_NOTE.format(files="10_gate.sql"),
)

add_verdict(
    "music_missing_revenue_events", "Your decision", "Partly agree",
    "Published list of shows with tickets sold but no revenue; the show rule drops them from the cards and keeps them here to be traced. "
    "Only Dan and the gate read it in 90 days and no dashboard or Genie space uses it, so it acts like a data-quality work list (silver) unless it is meant for readers.",
    ["06_missing_revenue_events.sql: 'kept as a data-gap list'; 'kept here to be traced rather than hidden'",
     "Read by 10_gate.sql (row count band) and named in a comment in 05_lookup_show_rule.sql; listed on the Confluence pipeline table page"],
    "Low",
    "Question for Dan: is this list meant for readers such as Charlie Ogbechie or the music team to look up dropped shows? "
    "Yes: keep it in gold and tell them it exists. No: move it to prod_shared_silver.central_analytics_enr with its _nightly copy in the same job move (change 99_publish.sql and 10_gate.sql, job runs as sp_prod_tm_central_analytics).",
)

# ---------- Step 22 test builds: published once on 11-10, logic now in the nightly ----------
step22_note: str = (
    "cloned over the published table on 11-10 (tasks/step22-part2/build/publish_log.txt), and the same logic was then deployed to the nightly job, "
    "which has changed it again since (flush rule from 11-17)"
)
step22_tables: dict[str, str] = {
    "music_artist_lookup_step22": "Step 22 test build of the event lookup",
    "music_asu_event_signups_step22": "Step 22 test build of Artist Sign Up sign-ups",
    "music_asu_tour_conversion_step22": "Step 22 test build of Artist Sign Up conversion",
    "music_benchmark_events_step22": "Step 22 test build of benchmark events",
    "music_benchmark_stats_step22": "Step 22 test build of benchmark stats",
    "music_missing_revenue_events_step22": "Step 22 test build of the missing revenue list",
    "music_queue_member_fact_step22": "Step 22 test build of the queue member fact",
    "music_str_daily_step22": "Step 22 test build of daily sell-through",
}
for short_name, description in step22_tables.items():
    has_fans: bool = short_name in FAN_ID_TABLES
    why = (
        f"{description}, {step22_note}. Nothing reads it and the code is kept in tasks/step22-part2/build and sql/nightly, so Delete rather than Sandbox."
        + (" It holds fan identifiers in a 47.6 GB scratch copy, another reason not to keep it." if has_fans else "")
    )
    add_verdict(
        short_name, "Delete", "Partly agree", why,
        ["publish_log.txt: 'PUBLISHED " + short_name.removesuffix("_step22") + " <- " + short_name + "' at 11:50 to 11:51 on 11-10",
         "Rollback for that publish is Delta RESTORE of the live table (publish_step22.py rollback), not this copy"],
        "High",
        "Tell Sachin Dewangan Delete instead of Sandbox. Nothing names it, so no code change.",
    )

add_verdict(
    "music_artist_lookup_step22_base", "Delete", "Partly agree",
    "Step 22 base event universe built on 11-09 to feed the other step 22 test tables; it was never published itself. "
    "The nightly base table (music_artist_lookup_nightly_base) does this job now, and the code is in tasks/step22-part2/build/01_lookup_base.sql, so Delete rather than Sandbox.",
    ["Built into the step 22 lookup, phase summary, queue fact and daily tables on 11-09 and 11-10"],
    "High",
    "Tell Sachin Dewangan Delete instead of Sandbox. Nothing names it.",
)

add_verdict(
    "music_str_daily_step22v2", "Delete", "Partly agree",
    "Second test version of the daily sell-through build, used to prove a faster rewrite gave the same answer; it was never published. "
    "The project notes say it can be dropped, and the proof is recorded, so Delete rather than Sandbox.",
    ["tasks/step22-part2/STATE.md: 'Scratch table music_str_daily_step22v2 can be dropped'; compare checks c30 and c31 recorded there"],
    "High",
    "None beyond telling Sachin Dewangan. Nothing names it.",
)

add_verdict(
    "music_event_phase_summary_step22", "Delete", "Disagree",
    "Step 22 test build of the phase summary, " + step22_note + ". Duygu Unaldi ran one query on it on 11-10, the go-live day; the published music_event_phase_summary "
    "holds the same content, refreshed nightly. Sachin keeps it only because of that one read; one ad hoc read of a superseded test copy is not a reason to keep it.",
    ["publish_log.txt: 'PUBLISHED music_event_phase_summary <- music_event_phase_summary_step22' on 11-10 11:50"],
    "Medium",
    "Ask Duygu Unaldi whether she still needs it; if she does, point her at prod_shared_gold.central_analytics_crd.music_event_phase_summary. Then delete.",
)

# ---------- B4/B5 benchmark one-off and its control build ----------
for short_name, description in {
    "music_benchmark_events_b4b5": "One-off 11-11 build of the B4/B5 benchmark change (benchmark events)",
    "music_benchmark_stats_b4b5": "One-off 11-11 build of the B4/B5 benchmark change (benchmark stats)",
}.items():
    add_verdict(
        short_name, "Delete", "Partly agree",
        f"{description}, published over the live tables on 11-11; the change was then deployed to the nightly job, which has rebuilt the benchmark every night since. "
        "Nothing reads it and the code is in tasks/step22-part2/build/09_benchmark_stats_b4b5.sql, so Delete rather than Sandbox.",
        ["tasks/charlie-builds-1111/STATE.md: 'B4/B5 benchmark PUBLISHED' 11-11, then 02, 04 and 09 'Deployed to the nightly job'"],
        "High",
        "Tell Sachin Dewangan Delete instead of Sandbox. Nothing names it.",
    )
for short_name, description in {
    "music_benchmark_events_ctrl": "Control build of benchmark events made on 11-11 to compare against the B4/B5 change",
    "music_benchmark_stats_ctrl": "Control build of benchmark stats made on 11-11 to compare against the B4/B5 change",
}.items():
    add_verdict(
        short_name, "Delete", "Partly agree",
        f"{description}. The comparison is finished and its result is written down, so this QA table from finished work should be deleted, not sandboxed.",
        ["tasks/charlie-builds-1111/STATE.md: 'checked against a same-time control build, only released_* and net_sold_* differ, rest float noise max $9'"],
        "High",
        "Tell Sachin Dewangan Delete instead of Sandbox. Nothing names it.",
    )

# ---------- Step 16 candidates and baseline (September) ----------
for short_name, description in {
    "music_artist_lookup_step16": "Step 16 candidate event lookup from 09-23",
    "music_benchmark_stats_step16": "Step 16 candidate benchmark stats from 09-24",
    "music_event_phase_summary_step16": "Step 16 candidate phase summary from 09-24",
    "music_queue_member_fact_step16": "Step 16 candidate queue member fact from 09-23",
    "music_str_daily_step16": "Step 16 candidate daily sell-through from 09-23",
}.items():
    has_fans = short_name in FAN_ID_TABLES
    add_verdict(
        short_name, "Delete", "Partly agree",
        f"{description}. The step 17 swap put the step 17 candidates live and left these aside, and the nightly job has replaced the logic since. "
        "Nothing reads it and the SQL is in tasks/step16/candidates, so Delete rather than Sandbox."
        + (" It is a 40 GB scratch copy with fan identifiers, another reason not to keep it." if has_fans else ""),
        ["tasks/step17/post_swap/01_swap.sql: 'The _step15_snapshot tables and the _step16 candidates are left where they are'"],
        "High",
        "Tell Sachin Dewangan Delete instead of Sandbox. Nothing names it.",
    )

add_verdict(
    "music_benchmark_stats_step16_baseline", "Delete", "Partly agree",
    "Step 16 comparison baseline: the repaired September benchmark, built to time it and diff it against the step 15 snapshot. "
    "That work finished in September and the result is in the step 16 files, so Delete; Sachin himself notes the owner may prefer Delete.",
    ["docs/step-16-implementation-plan-2026-09-23.md item 2: 'Repaired benchmark build (Q37 fix) into music_benchmark_stats_step16_baseline'; diffs in tasks/step16/v25 and v32"],
    "High",
    "Tell Sachin Dewangan Delete instead of Sandbox. Nothing names it.",
)

add_verdict(
    "music_benchmark_stats_step15_snapshot", "Delete", "Agree",
    "Snapshot of the live benchmark stats taken on 09-23 so the step 16 rebuild could be diffed against it. The diff is done and the published table has changed logic several times since, so it is a dated copy nothing rebuilds.",
    ["docs/step-16-implementation-plan-2026-09-23.md item 7: 'Snapshots kept: music_benchmark_stats_step15_snapshot'; tasks/step16/v25_regression_diff_baseline_vs_snapshot.sql"],
    "High",
    "None beyond telling Sachin Dewangan. Nothing names it.",
)

# ---------- Rollback copies left by the September swaps ----------
LIVE_HISTORY_FACT: str = (
    "The nightly job rebuilds the live table from source every night behind a gate; rollback is now RESTORE of the live table's Delta versions "
    "(sql/nightly/README.md); live phase summary history holds versions from 11-05 back to a 10-05 VACUUM (facts/music_hist_eps.csv), so the September state is not in it"
)
rollback_copies: dict[str, tuple[str, str, str]] = {
    # short name: (made by, swap file and quote, published table it backs)
    "music_artist_lookup_step16_live": ("the step 17 swap on 09-28", "tasks/step17/post_swap/01_swap.sql: 'Each live table moves to _step16_live (rollback copy)'", "music_artist_lookup"),
    "music_benchmark_stats_step16_live": ("the step 17 swap on 09-28", "tasks/step17/post_swap/01_swap.sql: 'Each live table moves to _step16_live (rollback copy)'", "music_benchmark_stats"),
    "music_event_phase_summary_step16_live": ("the step 17 swap on 09-28", "tasks/step17/post_swap/01_swap.sql: 'Each live table moves to _step16_live (rollback copy)'", "music_event_phase_summary"),
    "music_queue_member_fact_step16_live": ("the step 17 swap on 09-28", "tasks/step17/post_swap/01_swap.sql: 'Each live table moves to _step16_live (rollback copy)'", "music_queue_member_fact"),
    "music_str_daily_step16_live": ("the step 17 swap on 09-28", "tasks/step17/post_swap/01_swap.sql: 'Each live table moves to _step16_live (rollback copy)'", "music_str_daily"),
    "music_artist_lookup_step17_live": ("the step 18 swap on 09-29", "tasks/step18/05_swap.sql: 'The current live tables are kept as _step17_live so the swap can be undone'", "music_artist_lookup"),
    "music_asu_tour_conversion_step17_live": ("the step 18 swap on 09-29", "tasks/step18/05_swap.sql: 'The current live tables are kept as _step17_live so the swap can be undone'", "music_asu_tour_conversion"),
    "music_benchmark_stats_step17_live": ("the step 18 swap on 09-29", "tasks/step18/05_swap.sql: 'The current live tables are kept as _step17_live so the swap can be undone'", "music_benchmark_stats"),
    "music_asu_tour_conversion_step18_live": ("the step 18b swap on 09-30", "tasks/step18/07_swap_asu_groups.sql: 'The tour-level table is kept as _step18_live for rollback'", "music_asu_tour_conversion"),
    "music_asu_event_signups_step19_rollback": ("the step 19 swap on 09-30", "tasks/step19/01_swap_asu_both_platforms.sql: 'The live tables are kept as _step19_rollback'", "music_asu_event_signups"),
    "music_asu_tour_conversion_step19_rollback": ("the step 19 swap on 09-30", "tasks/step19/01_swap_asu_both_platforms.sql: 'The live tables are kept as _step19_rollback'", "music_asu_tour_conversion"),
}
# Sachin flags these as the only backup of the published table (no other older copy exists).
ONLY_BACKUP: set[str] = {"music_event_phase_summary_step16_live", "music_queue_member_fact_step16_live", "music_asu_event_signups_step19_rollback", "music_str_daily_step16_live"}

for short_name, (made_by, swap_quote, published_name) in rollback_copies.items():
    record = records_by_short_name[short_name]
    sachin_call: str = record["sachin"]["suggested_call"]
    is_only_backup: bool = short_name in ONLY_BACKUP
    has_fans = short_name in FAN_ID_TABLES
    why = f"Rollback copy of {published_name} left by {made_by}. "
    if is_only_backup:
        why += ("It is the only older copy of that table, but it holds September logic that later steps replaced, and the nightly rebuild plus Delta "
                "restore make it unnecessary as a backup. Nothing reads it, so Delete.")
    else:
        why += "Later steps and the nightly rebuild replaced it, the swap it guarded is long settled, and nothing reads it, so Delete."
    if has_fans:
        why += " It is a 40 GB copy with fan identifiers."
    if sachin_call == "Sandbox":
        why += " Sachin says Sandbox; nothing about a superseded rollback copy is worth keeping."
    add_verdict(
        short_name, "Delete", "Agree" if sachin_call == "Delete" else "Partly agree", why,
        [swap_quote, LIVE_HISTORY_FACT] + ([f"Only backup of {published_name}"] if is_only_backup else []),
        "Medium" if is_only_backup else "High",
        ("Dan to confirm nobody needs the September numbers as shown at the time (the code for each step is kept in tasks/step16 to step19). " if is_only_backup else "")
        + "Tell Sachin Dewangan" + (" Delete instead of Sandbox" if sachin_call == "Sandbox" else "") + ". Nothing names it.",
    )

# ---------- Write and verify ----------
missing: list[str] = [name for name in records_by_short_name if name not in verdicts]
assert not missing, f"No verdict for: {missing}"
assert len(verdicts) == len(records) == 54, (len(verdicts), len(records))

COLUMNS: list[str] = ["sheet_row", "full_name", "my_call", "target", "vs_sachin", "why", "facts", "confidence", "check_before_acting"]
ordered_rows: list[dict] = sorted(verdicts.values(), key=lambda row: row["sheet_row"])
for row in ordered_rows:
    for column in COLUMNS:
        text_value: str = str(row[column])
        assert "\u2014" not in text_value and "\u2013" not in text_value, (row["full_name"], column)
        assert "\u2192" not in text_value, (row["full_name"], column)

OUTPUT_PATH.parent.mkdir(exist_ok=True)
with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as output_file:
    writer = csv.DictWriter(output_file, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(ordered_rows)
print(f"wrote {len(ordered_rows)} rows to {OUTPUT_PATH}")
