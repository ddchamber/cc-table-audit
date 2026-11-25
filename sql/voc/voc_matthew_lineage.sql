SELECT source_table_full_name, target_table_full_name, entity_type, created_by, max(event_date) AS last_date, count(*) AS events
FROM system.access.table_lineage
WHERE event_date >= date_sub(current_date(), 365)
  AND (source_table_full_name LIKE 'nonprod_shared_gold.central_analytics_crd.voc_gold_wonloss_interviews'
    OR target_table_full_name LIKE 'nonprod_shared_gold.central_analytics_crd.voc_gold_wonloss_interviews'
    OR source_table_full_name LIKE 'nonprod_shared_gold.central_analytics_crd.voc_silver_wonloss_interviews'
    OR source_table_full_name LIKE '%mv_voc%' OR target_table_full_name LIKE '%mv_voc%')
GROUP BY 1,2,3,4 ORDER BY 1,2,4
