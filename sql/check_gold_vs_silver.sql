SELECT is_account_group_member('team_tm_central_analytics_users') AS in_ca_users,
       is_account_group_member('team_tm_central_analytics_rx') AS in_ca_rx,
       (SELECT concat_ws(', ', collect_set(privilege_type))
          FROM system.information_schema.schema_privileges
         WHERE catalog_name = 'prod_shared_gold' AND schema_name = 'central_analytics_crd'
           AND grantee = 'team_tm_central_analytics_users') AS ca_users_rights_on_prod_gold_crd,
       (SELECT concat_ws(', ', collect_set(privilege_type))
          FROM system.information_schema.schema_privileges
         WHERE catalog_name = 'prod_shared_silver' AND schema_name = 'central_analytics_enr'
           AND grantee = 'team_tm_central_analytics_users') AS ca_users_rights_on_prod_silver_enr
