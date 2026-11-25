"""Write the VOC placement verdicts (one row per object in batches/voc.json) to verdicts/voc.csv.

Evidence used beyond the batch file (all read-only):
- facts/voc_mapping_direct_reads.csv: splits other people's mapping reads into reads through Dan's views and direct reads.
- facts/voc_matthew_lineage.csv and facts/voc_matthew_tables.csv: Matthew's nonprod tables and what they were built from.
- facts/voc_pii_columns.csv and facts/voc_prod_columns.csv: personal-data columns.
- VOC/sessions/2026-07-22-09-30-sandbox-to-prod--sixteen-tables-cross-the-finish-line.md: the 07-22 static loads.
- Vault voc-pipeline.md: the interview-ingestor handoff to Raines Warren and the mapping tables it reads.
"""
import csv
import json
from pathlib import Path

AUDIT_FOLDER: Path = Path(r"C:\Users\dan.chamberlin\TM\table-audit")
BATCH_PATH: Path = AUDIT_FOLDER / "batches" / "voc.json"
OUTPUT_PATH: Path = AUDIT_FOLDER / "verdicts" / "voc.csv"

PROD_GOLD: str = "prod_shared_gold.central_analytics_crd."
PROD_SILVER: str = "prod_shared_silver.central_analytics_enr."
NONPROD_GOLD: str = "nonprod_shared_gold.central_analytics_crd."

COLUMNS: list[str] = ["sheet_row", "full_name", "my_call", "target", "vs_sachin", "why", "facts", "confidence", "check_before_acting"]

# Shared evidence phrases, kept in one place so every row cites the same sources the same way.
DASHBOARD_FACT: str = "In Matthew Sutton's dashboard and Genie space \"VoC Won-Loss Competitive Intelligence\"; read by Shaan Arora's job CI-Bot (0 of 13 runs succeeded in 30 days)."
SESSION_0722: str = "VOC/sessions/2026-07-22-09-30-sandbox-to-prod--sixteen-tables-cross-the-finish-line.md: 16 tables copied from Dan's sandbox to prod and nonprod on 07-22; the interview loader writes straight to prod."
INGESTOR_FACT: str = "The interview loader handed to Raines Warren on 10-30 reads it by its prod gold name (VOC/ingestion_handoff_structure/skills/interview-ingestor/reference/mapping-lookups.md; vault voc-pipeline)."
STALE_COPY_FACT: str = "Written once on 07-22 from Dan's sandbox and never since; no reads by anyone, including Dan, in 90 days; no job, view, dashboard or Genie space names it (breakage.md)."
DELETE_CHECK: str = "Nothing to repoint. Tell Matthew Sutton the nonprod VOC copies are going so he does not build on them."
VIEW_REPOINT_CHECK: str = "Repoint Dan's views voc_vw_sf_opportunities and voc_vw_interview_sf_link to the silver name in the same change; tell Shaan Arora (CI-Bot) and the view readers Ashley Pierce, Anne Paulsen, Matthew Sutton and Raines Warren; the move is done by redeploying under sp_prod_tm_central_analytics."
INGESTOR_CHECK: str = "Update the interview loader package Raines Warren runs (mapping-lookups.md and SKILL.md name the prod gold table) before moving; move by redeploying under sp_prod_tm_central_analytics."


def build_verdicts() -> dict[str, dict[str, str]]:
    """Return verdict fields keyed by full table name."""
    verdicts: dict[str, dict[str, str]] = {}

    # Prod report objects the dashboard and Genie space read directly: stay in gold.
    prod_keep_rows: dict[str, tuple[str, str, str]] = {
        "voc_vw_qualtrics_survey_responses": (
            "Report view of Qualtrics survey responses with the Salesforce account match. Eight people read it and it backs the VOC dashboard and Genie space, so it is a consumer object and belongs in gold. It is a view that adds matching logic, not a copy of the Qualtrics tables.",
            "Readers 90 days: Ashley Pierce, Anne Paulsen, Matthew Sutton, Michael Wiederhold, Rachel Sussman, Raines Warren, Shaan Arora, Vladislav Gritsaenko; last 11-16. " + DASHBOARD_FACT + " Feeds views voc_vw_sf_opportunities and voc_vw_qualtrics_csat_scores. Reads prod_shared_gold.qualtrics_ca (owned by another principal). Comment: \"Auto-refreshes from Qualtrics bronze.\"",
            "Holds recipient_email (client contact emails): keep access limited and confirm that is acceptable in a shared gold schema. Nothing to move.",
        ),
        "voc_discovery_interviews": (
            "One row per discovery interview. Seven people read it and the dashboard and Genie space use it, so it stays in gold. The interview loader keeps it current.",
            "Readers 90 days: Ashley Pierce, Anne Paulsen, Matthew Sutton, Michael Wiederhold, Rachel Sussman, Raines Warren, Shaan Arora; last 11-16. " + DASHBOARD_FACT + " Feeds views voc_vw_sf_opportunities and voc_vw_interview_sf_link. Comment: \"Grain: one row per interview. 120 interviews.\" Last written 08-18 by Dan.",
            "Nothing to move. No scheduled job loads it; writes come from the interview loader run by hand (Dan, Raines Warren), so plan who runs it once moves go to sp_prod_tm_central_analytics.",
        ),
        "voc_wonloss_interviews": (
            "One row per won or lost deal interview. Seven people read it, the dashboard and Genie space use it, and Matthew's metric view mv_voc_wonloss is built on it, so it stays in gold.",
            "Readers 90 days: Ashley Pierce, Anne Paulsen, Matthew Sutton, Michael Wiederhold, Rachel Sussman, Raines Warren, Shaan Arora; last 11-16. " + DASHBOARD_FACT + " Named by mv_voc_wonloss (Matthew Sutton) and views voc_vw_sf_opportunities, voc_vw_interview_sf_link. Last written 10-30 by Raines Warren (interview loader).",
            "Nothing to move. Raines Warren writes it through the interview loader; keep his write access in mind if rights change.",
        ),
        "voc_vw_sf_opportunities": (
            "Report view of Salesforce deals with VOC loss themes and competitor names. Six people read it and 57 dashboard datasets use it, so it stays in gold. It adds VOC logic on top of Salesforce, so it is not a plain copy to retire.",
            "Readers 90 days: Ashley Pierce, Anne Paulsen, Matthew Sutton, Michael Wiederhold, Raines Warren, Shaan Arora; last 11-16. " + DASHBOARD_FACT + " Reads finance_nonprod.refinery_prod.client360_salesforce_account_sql and finance_nonprod.treasury_prod.client360_salesforce_opportunity_sql plus the mapping tables. Named by view voc_vw_interview_sf_link and Dan's workspace skill voc-competitor-brief.",
            "Nothing to move. When the two mapping tables move to silver, edit this view in the same change. Note it reads Salesforce from the finance_nonprod catalog: a prod view on a nonprod source, worth raising with the Salesforce table owners.",
        ),
        "voc_vw_qualtrics_csat_scores": (
            "Report view of single CSAT scores from Qualtrics. Five people read it and the dashboard and Genie space use it, so it stays in gold.",
            "Readers 90 days: Ashley Pierce, Matthew Sutton, Michael Wiederhold, Rachel Sussman, Shaan Arora; last 11-16. " + DASHBOARD_FACT + " Reads voc_vw_qualtrics_survey_responses and prod_shared_gold.qualtrics_ca. Comment: \"Auto-refreshes via view-on-view chain.\"",
            "Nothing to move.",
        ),
        "voc_wonloss_category_scores": (
            "Scores for Ticketmaster versus the competitor by category from each won or lost interview. The dashboard, Genie space and Matthew's metric view mv_voc_category_scores read it, so it stays in gold.",
            "Readers 90 days: Ashley Pierce, Matthew Sutton, Michael Wiederhold, Raines Warren, Shaan Arora; last 11-16. " + DASHBOARD_FACT + " Named by mv_voc_category_scores (Matthew Sutton). Comment: \"913 scores across 12 categories.\" Last written 08-18.",
            "Nothing to move.",
        ),
        "voc_wonloss_responses": (
            "Question and answer pairs from won or lost interviews. Five people read it and the dashboard and Genie space use it, so it stays in gold.",
            "Readers 90 days: Ashley Pierce, Matthew Sutton, Michael Wiederhold, Raines Warren, Shaan Arora; last 11-16. " + DASHBOARD_FACT + " Comment: \"1,021 responses across 77 interviews.\" Last written 10-30 by Raines Warren.",
            "Holds response_text, free-text interview answers that may name client staff; keep access limited. Nothing to move.",
        ),
        "voc_discovery_responses": (
            "Question and answer pairs from discovery interviews. Four people read it and the dashboard and Genie space use it, so it stays in gold.",
            "Readers 90 days: Ashley Pierce, Matthew Sutton, Michael Wiederhold, Shaan Arora; last 11-16. " + DASHBOARD_FACT + " Comment: \"953 responses across 110 interviews.\" Last written 08-12.",
            "Holds response_text, free-text interview answers that may name client staff; keep access limited. Nothing to move.",
        ),
        "voc_vw_interview_sf_link": (
            "Report view that ties each interview to Salesforce. Ashley Pierce and Shaan Arora read it and the dashboard and Genie space use it, so it stays in gold.",
            "Readers 90 days: Ashley Pierce (11-04 to 11-10), Shaan Arora (CI-Bot, to 11-14). " + DASHBOARD_FACT + " Comment: \"One row per VOC interview ... showing how it ties to Salesforce.\" Reads voc_mapping_competitors and finance_nonprod Salesforce tables.",
            "Nothing to move. When voc_mapping_competitors moves to silver, edit this view in the same change.",
        ),
    }
    for table_name, (why_text, facts_text, check_text) in prod_keep_rows.items():
        verdicts[PROD_GOLD + table_name] = {
            "my_call": "Keep as is", "target": PROD_GOLD + table_name + " (stays here)", "vs_sachin": "Agree",
            "why": why_text, "facts": facts_text, "confidence": "High", "check_before_acting": check_text,
        }

    # Prod hand-kept mapping tables. Test of rule 3: other people's reads came through Dan's views, not directly.
    prod_mapping_rows: dict[str, tuple[str, str, str, str]] = {
        "voc_mapping_sf_loss_reasons": (
            "Hand-kept lookup that turns Salesforce loss reasons into themes. Sachin counts six readers, but every one of their reads came through Dan's view voc_vw_sf_opportunities; only Michael Wiederhold queried it directly, once on 09-03. A lookup read through a view is a building block, so silver is right.",
            "Reads 90 days by person (via view / direct statements): Shaan Arora 108/0 (CI-Bot), Ashley Pierce 22/0, Anne Paulsen 9/0, Raines Warren 6/0, Matthew Sutton 2/0, Michael Wiederhold 4/1 (09-03). Not in any dashboard dataset or Genie space directly. Written once 07-22. docs/database/mappings.md: \"Manually Created: Based on SalesforceMapping.csv\". 117 rows.",
            VIEW_REPOINT_CHECK, "High",
        ),
        "voc_mapping_competitors": (
            "Hand-kept lookup of competitor names. Its six readers reached it through Dan's two views, apart from one direct query each by Michael Wiederhold (09-03) and Raines Warren (10-30, the interview loader). That makes it a building block, so silver is right.",
            "Reads 90 days by person (via view / direct statements): Shaan Arora 108/0 (CI-Bot), Ashley Pierce 22/0, Anne Paulsen 9/0, Raines Warren 6/1 (10-30), Matthew Sutton 1/0, Michael Wiederhold 0/1 (09-03). Named by views voc_vw_sf_opportunities and voc_vw_interview_sf_link. " + INGESTOR_FACT + " Written once 07-22.",
            VIEW_REPOINT_CHECK + " Also update the interview loader package Raines Warren runs, which names the prod gold table.", "High",
        ),
        "voc_mapping_client_names": (
            "Hand-kept lookup from interview client names to Salesforce account names, used by the interview loader. Its three readers were one view query (Rachel Sussman), one loader run (Raines Warren) and one look (Michael Wiederhold); nobody uses it as a report, so silver is right.",
            "Reads 90 days (via view / direct): Rachel Sussman 1/0 (11-03), Raines Warren 0/1 (10-30, loader run), Michael Wiederhold 0/1 (09-03). " + INGESTOR_FACT + " mappings.md: 62 rows, EXACT and FUZZY matches. Written once 07-22.",
            INGESTOR_CHECK + " Holds client business names only, no personal data.", "High",
        ),
        "voc_account_id_mapping": (
            "Hand-kept crosswalk from interview client names to Salesforce account IDs, a build input for the opportunity ID mapping. Only two single direct reads in 90 days (Michael Wiederhold 09-03, Siritha Akula 08-25), so it is a building block and silver is right.",
            "Reads 90 days: Michael Wiederhold 1 (09-03), Siritha Akula 1 (08-25), both direct. Dan has not read it in 90 days. Built and read by VOC/src/sql/gold/00_mapping_tables/03_voc_gold_opportunity_id18_mapping.sql, which names the prod gold table. Written once 07-22.",
            "Ask Siritha Akula and Michael Wiederhold whether they still query it, and give them the new name. Edit 03_voc_gold_opportunity_id18_mapping.sql to the silver name; move by redeploying under sp_prod_tm_central_analytics.", "Medium",
        ),
        "voc_mapping_questions": (
            "Hand-kept lookup that standardizes interview questions, read by the interview loader. Its only other readers were one loader run (Raines Warren 10-30) and one look (Michael Wiederhold 09-03), so silver is right.",
            "Reads 90 days: Raines Warren 1 direct (10-30, loader run), Michael Wiederhold 1 direct (09-03). " + INGESTOR_FACT + " Written once 07-22.",
            INGESTOR_CHECK, "High",
        ),
        "voc_mapping_categories": (
            "Hand-kept lookup that folds 61 raw categories into 12 standard ones, read by the interview loader. Only Michael Wiederhold queried it, once on 09-03, so silver is right.",
            "Reads 90 days: Michael Wiederhold 1 direct (09-03). Comment: \"Maps 61 category_raw values to 12 approved standardized categories\". " + INGESTOR_FACT + " Written once 07-22.",
            INGESTOR_CHECK, "High",
        ),
        "voc_mapping_products": (
            "Hand-kept lookup of product names mentioned in interviews. Only Michael Wiederhold queried it, once on 09-03, and no view or loader reads it, so it is reference data and belongs in silver.",
            "Reads 90 days: Michael Wiederhold 1 direct (09-03); Dan 0. No code names voc_mapping_products: the build SQL (src/sql/gold/01_wonloss/02_gold_wonloss_responses.sql) still names the old sandbox gold_product_mapping. Values kept in src/sql/gold/00_mapping_tables/02_gold_product_mapping.sql. mappings.md lists it as a maintained mapping. Written once 07-22.",
            "Confirm with Dan that product tagging will be rebuilt from this table; if not, it could be deleted instead, since its values live in 02_gold_product_mapping.sql. Move by redeploying under sp_prod_tm_central_analytics.", "Medium",
        ),
        "voc_opportunity_id18_mapping": (
            "Hand-kept crosswalk from interview files to Salesforce opportunity IDs, a build input. Only Michael Wiederhold queried it, once on 09-03, so it is a building block and silver is right.",
            "Reads 90 days: Michael Wiederhold 1 direct (09-03); Dan 0. Built by VOC/src/sql/gold/00_mapping_tables/07_gold_opportunity_id18_mapping.sql (\"Team-provided mapping\", 16 rows), which names the prod gold table. Written once 07-22.",
            "Edit 07_gold_opportunity_id18_mapping.sql to the silver name; tell Michael Wiederhold the new name; move by redeploying under sp_prod_tm_central_analytics. Holds client and file names only, no personal data.", "Medium",
        ),
    }
    for table_name, (why_text, facts_text, check_text, confidence_level) in prod_mapping_rows.items():
        verdicts[PROD_GOLD + table_name] = {
            "my_call": "Move to silver", "target": PROD_SILVER + table_name, "vs_sachin": "Agree",
            "why": why_text, "facts": facts_text, "confidence": confidence_level, "check_before_acting": check_text,
        }

    # Nonprod static copies of kept prod tables: Sachin keeps them, the rules say delete stale copies nothing rebuilds.
    nonprod_copy_rows: dict[str, tuple[str, str]] = {
        "voc_discovery_interviews": ("discovery interview table", "Holds client names only, no personal data."),
        "voc_discovery_responses": ("discovery answers table", "Holds free-text interview answers; a reason to delete rather than keep a spare copy. The workspace skill voc-competitor-brief names the table without a catalog and its queries file uses prod, so it does not read this copy."),
        "voc_wonloss_category_scores": ("won or lost category scores table", "The workspace skill voc-competitor-brief names the table without a catalog and its queries file uses prod, so it does not read this copy."),
        "voc_wonloss_interviews": ("won or lost interview table", "Prod twin was last written 10-30, so this copy is already out of date."),
        "voc_wonloss_responses": ("won or lost answers table", "Holds free-text interview answers; a reason to delete rather than keep a spare copy. The workspace skill voc-competitor-brief names the table without a catalog and uses prod in its queries file."),
    }
    for table_name, (description, extra_fact) in nonprod_copy_rows.items():
        verdicts[NONPROD_GOLD + table_name] = {
            "my_call": "Delete", "target": "", "vs_sachin": "Disagree",
            "why": f"A frozen 07-22 copy of the prod {description}. Nobody has read it in 90 days and nothing refreshes it, because the interview loader writes only to prod. Sachin keeps environment copies even when stale, but the cleanup rules delete stale copies nothing rebuilds; the live data is in prod and the build code is in the VOC project.",
            "facts": STALE_COPY_FACT + " " + SESSION_0722 + " " + extra_fact,
            "confidence": "High", "check_before_acting": DELETE_CHECK,
        }

    nonprod_mapping_rows: dict[str, str] = {
        "voc_account_id_mapping": "Holds client names and account IDs, no personal data.",
        "voc_mapping_categories": "No personal data.",
        "voc_mapping_client_names": "Holds client business names only, no personal data.",
        "voc_mapping_products": "No personal data.",
        "voc_mapping_questions": "No personal data.",
        "voc_mapping_sf_loss_reasons": "No personal data.",
        "voc_opportunity_id18_mapping": "Holds client and file names only, no personal data.",
    }
    for table_name, extra_fact in nonprod_mapping_rows.items():
        verdicts[NONPROD_GOLD + table_name] = {
            "my_call": "Delete", "target": "", "vs_sachin": "Disagree",
            "why": "A frozen 07-22 copy of a hand-kept lookup that lives on in prod. Nobody has read it in 90 days and nothing refreshes it. Sachin would move it to nonprod silver, but moving an unused stale copy just relocates clutter; the prod table and the VOC build code keep the values.",
            "facts": STALE_COPY_FACT + " " + SESSION_0722 + " Values also kept in VOC/src/sql/gold/00_mapping_tables. " + extra_fact,
            "confidence": "High", "check_before_acting": DELETE_CHECK,
        }

    verdicts[NONPROD_GOLD + "voc_mapping_competitors"] = {
        "my_call": "Delete", "target": "", "vs_sachin": "Disagree",
        "why": "A frozen 07-22 copy of the competitor lookup that lives on in prod. Its only use was Matthew building his nonprod voc_gold_wonloss_interviews from it once on 07-30; that table is stored data, so deleting this copy does not break it. If Matthew rebuilds, he should read the prod lookup, not a stale copy.",
        "facts": "Written once 07-22 from Dan's sandbox; no reads in 90 days. Lineage: matthew.sutton notebook built nonprod voc_gold_wonloss_interviews (a stored table, not a view) from it on 07-30, the only build in 365 days. " + SESSION_0722,
        "confidence": "Medium",
        "check_before_acting": "Ask Matthew Sutton whether he will re-run the 07-30 notebook that builds nonprod voc_gold_wonloss_interviews. If yes, point it at prod voc_mapping_competitors first; if no, delete.",
    }

    # Nonprod copies of the sandbox silver layer and of derived Qualtrics and Salesforce tables.
    silver_copy_rows: dict[str, str] = {
        "voc_silver_discovery_category_scores": "No personal data columns.",
        "voc_silver_discovery_interviews": "Holds interviewer_name, a staff name.",
        "voc_silver_discovery_responses": "Holds interviewer_notes, free text that may carry names or contact details.",
        "voc_silver_qualtrics_csat_scores": "No personal data columns.",
        "voc_silver_qualtrics_survey_responses": "Holds recipient_email (client contact emails).",
        "voc_silver_wonloss_category_scores": "No personal data columns.",
        "voc_silver_wonloss_responses": "Holds free-text interview answers.",
    }
    for table_name, pii_fact in silver_copy_rows.items():
        has_personal_data: bool = not pii_fact.startswith("No personal")
        why_text: str = "A frozen 07-22 copy of an early cleaning step from Dan's sandbox. Nothing reads it and nothing rebuilds it, because the interview loader now writes straight to prod gold; the cleaning logic is kept in VOC/src/sql/silver."
        if has_personal_data:
            why_text += " It also holds personal data, a further reason to delete rather than keep a spare copy."
        verdicts[NONPROD_GOLD + table_name] = {
            "my_call": "Delete", "target": "", "vs_sachin": "Agree",
            "why": why_text,
            "facts": STALE_COPY_FACT + " " + SESSION_0722 + " The session created 8 voc_silver_* copies as the VOC silver layer. " + pii_fact + " Only UI looks without a query by others (Matthew Sutton 10-13 and others, per Sachin).",
            "confidence": "High", "check_before_acting": DELETE_CHECK,
        }

    verdicts[NONPROD_GOLD + "voc_silver_wonloss_interviews"] = {
        "my_call": "Delete", "target": "", "vs_sachin": "Disagree",
        "why": "A frozen 07-22 copy of an early cleaning step. Sachin keeps it because Matthew built his nonprod voc_gold_wonloss_interviews from it on 07-30, but that table is stored data and will not break; nothing has read this copy in 90 days. If Matthew rebuilds, he should read the live prod voc_wonloss_interviews, not a stale copy.",
        "facts": "Written once 07-22 from Dan's sandbox; last read by Matthew Sutton 07-29 and Sean Poole 08-07, none in 90 days. Lineage: Matthew's notebook built nonprod voc_gold_wonloss_interviews (stored table) from it and nonprod voc_mapping_competitors on 07-30, the only build in 365 days. Cleaning logic kept in VOC/src/sql/silver/05_wonloss_interviews.sql. " + SESSION_0722,
        "confidence": "Medium",
        "check_before_acting": "Ask Matthew Sutton whether he will re-run the 07-30 notebook. If yes, repoint it to prod voc_wonloss_interviews first; if no, delete. Holds client names only, no personal data.",
    }

    verdicts[NONPROD_GOLD + "voc_qualtrics_csat_scores"] = {
        "my_call": "Delete", "target": "", "vs_sachin": "Agree",
        "why": "A frozen 07-22 copy of the CSAT scores. Prod serves the same data through the live view voc_vw_qualtrics_csat_scores, and nobody has queried this copy in 90 days.",
        "facts": STALE_COPY_FACT + " Prod view comment: \"Auto-refreshes via view-on-view chain.\" Only UI looks without a query (Daniel Sweetman 09-11, Matthew Sutton 10-13, Ashley Pierce 11-03, per Sachin). " + SESSION_0722,
        "confidence": "High", "check_before_acting": DELETE_CHECK,
    }
    verdicts[NONPROD_GOLD + "voc_qualtrics_survey_responses"] = {
        "my_call": "Delete", "target": "", "vs_sachin": "Agree",
        "why": "A frozen 07-22 copy of the Qualtrics survey responses, which hold client contact emails. Prod serves the same data through the live view voc_vw_qualtrics_survey_responses, and nobody has queried this copy in 90 days, so a spare copy of personal data should go.",
        "facts": STALE_COPY_FACT + " Holds recipient_email. Prod view comment: \"Auto-refreshes from Qualtrics bronze.\" Only UI looks without a query (Daniel Sweetman 09-11, Matthew Sutton 10-13, Ashley Pierce 11-03, per Sachin). " + SESSION_0722,
        "confidence": "High", "check_before_acting": DELETE_CHECK,
    }
    verdicts[NONPROD_GOLD + "voc_sf_opportunities"] = {
        "my_call": "Delete", "target": "", "vs_sachin": "Agree",
        "why": "A frozen 07-22 copy of Salesforce deals with VOC themes. Prod serves current deals through the view voc_vw_sf_opportunities, which reads Salesforce directly, and nobody has queried this copy in 90 days.",
        "facts": STALE_COPY_FACT + " Only UI looks without a query (Matthew Sutton 10-13; Dan 11-03, per Sachin). Prod voc_vw_sf_opportunities reads finance_nonprod Salesforce tables live. No personal data columns. " + SESSION_0722,
        "confidence": "High", "check_before_acting": DELETE_CHECK,
    }
    return verdicts


def main() -> None:
    with open(BATCH_PATH, encoding="utf-8") as batch_file:
        batch_records: list[dict] = json.load(batch_file)
    verdicts_by_name: dict[str, dict[str, str]] = build_verdicts()

    missing_names: list[str] = [record["full_name"] for record in batch_records if record["full_name"] not in verdicts_by_name]
    extra_names: set[str] = set(verdicts_by_name) - {record["full_name"] for record in batch_records}
    if missing_names or extra_names:
        raise SystemExit(f"Verdict set does not match the batch. Missing: {missing_names}. Extra: {sorted(extra_names)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for record in batch_records:
            writer.writerow({"sheet_row": record["sheet_row"], "full_name": record["full_name"], **verdicts_by_name[record["full_name"]]})
    print(f"Wrote {len(batch_records)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
