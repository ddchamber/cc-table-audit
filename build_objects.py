"""Step 1: write objects.csv (one row per object on Dan's tab, with its exact sheet row number)
and compare against what actually exists in Databricks.

Names are copied from the 'Dan Chamberlin' tab read on 2026-11-18 (A7:C77 prod, A88:C111 nonprod).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import run_sql

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
WAREHOUSE_ID: str = "dbb3244d6fa2f0fc"
SCHEMA_NAME: str = "central_analytics_crd"

PROD_NAMES_FROM_ROW_7: list[str] = """music_artist_lookup music_event_phase_summary music_queue_member_fact
voc_vw_qualtrics_survey_responses voc_discovery_interviews voc_wonloss_interviews voc_mapping_sf_loss_reasons
voc_vw_sf_opportunities music_benchmark_stats music_str_daily voc_mapping_competitors voc_vw_qualtrics_csat_scores
voc_wonloss_category_scores voc_wonloss_responses voc_discovery_responses music_asu_tour_conversion
voc_mapping_client_names music_asu_event_signups voc_account_id_mapping voc_mapping_questions
voc_vw_interview_sf_link music_event_phase_summary_step22 voc_mapping_categories voc_mapping_products
voc_opportunity_id18_mapping music_artist_lookup_nightly music_artist_lookup_nightly_base
music_artist_lookup_step16 music_artist_lookup_step16_live music_artist_lookup_step22
music_artist_lookup_step22_base music_asu_event_signups_nightly music_asu_event_signups_step22
music_asu_tour_conversion_nightly music_asu_tour_conversion_step22 music_benchmark_events
music_benchmark_events_b4b5 music_benchmark_events_ctrl music_benchmark_events_nightly
music_benchmark_events_step22 music_benchmark_stats_b4b5 music_benchmark_stats_ctrl music_benchmark_stats_nightly
music_benchmark_stats_step15_snapshot music_benchmark_stats_step16 music_benchmark_stats_step16_baseline
music_benchmark_stats_step16_live music_benchmark_stats_step22 music_event_phase_summary_nightly
music_event_phase_summary_step16 music_event_phase_summary_step16_live music_missing_revenue_events
music_missing_revenue_events_nightly music_missing_revenue_events_step22 music_nightly_gate_log music_phase_alias
music_queue_member_fact_nightly music_queue_member_fact_step16 music_queue_member_fact_step16_live
music_queue_member_fact_step22 music_str_daily_nightly music_str_daily_step16 music_str_daily_step22
music_str_daily_step22v2 music_artist_lookup_step17_live music_asu_event_signups_step19_rollback
music_asu_tour_conversion_step17_live music_asu_tour_conversion_step18_live
music_asu_tour_conversion_step19_rollback music_benchmark_stats_step17_live music_str_daily_step16_live""".split()

NONPROD_NAMES_FROM_ROW_88: list[str] = """voc_account_id_mapping voc_discovery_interviews voc_discovery_responses
voc_mapping_categories voc_mapping_client_names voc_mapping_competitors voc_mapping_products voc_mapping_questions
voc_mapping_sf_loss_reasons voc_opportunity_id18_mapping voc_qualtrics_csat_scores voc_qualtrics_survey_responses
voc_sf_opportunities voc_silver_discovery_category_scores voc_silver_discovery_interviews
voc_silver_discovery_responses voc_silver_qualtrics_csat_scores voc_silver_qualtrics_survey_responses
voc_silver_wonloss_category_scores voc_silver_wonloss_interviews voc_silver_wonloss_responses
voc_wonloss_category_scores voc_wonloss_interviews voc_wonloss_responses""".split()


def main() -> None:
    assert len(PROD_NAMES_FROM_ROW_7) == 71, len(PROD_NAMES_FROM_ROW_7)
    assert len(NONPROD_NAMES_FROM_ROW_88) == 24, len(NONPROD_NAMES_FROM_ROW_88)

    tab_objects: list[dict] = []
    for offset, name in enumerate(PROD_NAMES_FROM_ROW_7):
        tab_objects.append({"sheet_row": 7 + offset, "catalog": "prod_shared_gold", "name": name})
    for offset, name in enumerate(NONPROD_NAMES_FROM_ROW_88):
        tab_objects.append({"sheet_row": 88 + offset, "catalog": "nonprod_shared_gold", "name": name})

    columns, rows = run_sql(WAREHOUSE_ID, f"""
        SELECT table_catalog, table_name, table_type, table_owner, created, last_altered
        FROM system.information_schema.tables
        WHERE table_schema = '{SCHEMA_NAME}'
          AND table_catalog IN ('prod_shared_gold', 'nonprod_shared_gold')
          AND (table_name LIKE 'music\\_%' OR table_name LIKE 'voc\\_%')""")
    databricks_objects: dict[tuple[str, str], dict] = {
        (row[0], row[1]): dict(zip(columns, row)) for row in rows
    }

    with open(os.path.join(AUDIT_FOLDER, "objects.csv"), "w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["sheet_row", "full_name", "exists", "table_type", "owner", "created", "last_altered"])
        for tab_object in tab_objects:
            found = databricks_objects.get((tab_object["catalog"], tab_object["name"]))
            writer.writerow([
                tab_object["sheet_row"],
                f"{tab_object['catalog']}.{SCHEMA_NAME}.{tab_object['name']}",
                "yes" if found else "NO",
                found and found["table_type"], found and found["table_owner"],
                found and found["created"], found and found["last_altered"],
            ])

    tab_keys: set[tuple[str, str]] = {(o["catalog"], o["name"]) for o in tab_objects}
    missing_from_databricks = [o for o in tab_objects if (o["catalog"], o["name"]) not in databricks_objects]
    not_on_tab = [databricks_objects[key] for key in sorted(databricks_objects) if key not in tab_keys]

    print(f"tab objects: {len(tab_objects)}, found in Databricks: {len(tab_objects) - len(missing_from_databricks)}")
    print("on tab but missing in Databricks:", [f"row {o['sheet_row']} {o['name']}" for o in missing_from_databricks])
    print(f"in Databricks but not on tab ({len(not_on_tab)}):")
    for extra in not_on_tab:
        print(f"  {extra['table_catalog']}.{extra['table_name']}  type={extra['table_type']}  "
              f"owner={extra['table_owner']}  created={extra['created']}")


if __name__ == "__main__":
    main()
