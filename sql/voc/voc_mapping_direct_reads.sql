-- For each prod VOC mapping table, split other people's reads into reads that came through one of Dan's
-- VOC views in the same statement (indirect) and reads where the statement named no VOC view (direct).
WITH mapping_reads AS (
  SELECT source_table_full_name, created_by, statement_id, entity_type, event_date, target_table_full_name
  FROM system.access.table_lineage
  WHERE event_date >= date_sub(current_date(), 90)
    AND source_table_full_name IN (
      'prod_shared_gold.central_analytics_crd.voc_mapping_sf_loss_reasons',
      'prod_shared_gold.central_analytics_crd.voc_mapping_competitors',
      'prod_shared_gold.central_analytics_crd.voc_mapping_client_names',
      'prod_shared_gold.central_analytics_crd.voc_account_id_mapping',
      'prod_shared_gold.central_analytics_crd.voc_mapping_questions',
      'prod_shared_gold.central_analytics_crd.voc_mapping_categories',
      'prod_shared_gold.central_analytics_crd.voc_mapping_products',
      'prod_shared_gold.central_analytics_crd.voc_opportunity_id18_mapping')
    AND created_by NOT IN ('dan.chamberlin@ticketmaster.com', 'sachin.dewangan@ticketmaster.com')
),
view_statements AS (
  SELECT DISTINCT statement_id
  FROM system.access.table_lineage
  WHERE event_date >= date_sub(current_date(), 90)
    AND (source_table_full_name LIKE 'prod_shared_gold.central_analytics_crd.voc_vw_%'
      OR target_table_full_name LIKE 'prod_shared_gold.central_analytics_crd.voc_vw_%')
)
SELECT
  replace(m.source_table_full_name, 'prod_shared_gold.central_analytics_crd.', '') AS mapping_table,
  m.created_by,
  count(DISTINCT m.statement_id) AS statements,
  count(DISTINCT CASE WHEN v.statement_id IS NOT NULL OR m.target_table_full_name LIKE '%voc_vw_%' THEN m.statement_id END) AS via_view_statements,
  count(DISTINCT CASE WHEN v.statement_id IS NULL AND coalesce(m.target_table_full_name, '') NOT LIKE '%voc_vw_%' THEN m.statement_id END) AS direct_statements,
  concat_ws(',', collect_set(m.entity_type)) AS entity_types,
  concat_ws(',', collect_set(CASE WHEN v.statement_id IS NULL AND coalesce(m.target_table_full_name, '') NOT LIKE '%voc_vw_%' THEN cast(m.event_date AS string) END)) AS direct_dates
FROM mapping_reads m
LEFT JOIN view_statements v ON m.statement_id = v.statement_id
GROUP BY 1, 2
ORDER BY 1, 2
