view: customers {
  sql_table_name: analytics.dim_customers ;;

  dimension: customer_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.customer_id ;;
  }

  dimension: Country {
    type: string
    sql: ${TABLE}.country ;;
  }

  measure: customer_count {
    type: count_distinct
    sql: ${customer_id} ;;
    description: "Distinct customers." ;;
  }
}
