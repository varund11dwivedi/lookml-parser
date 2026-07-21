view: orders {
  sql_table_name: analytics.fact_orders ;;

  dimension: order_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.order_id ;;
  }

  dimension: customer_id {
    type: number
    hidden: yes
    sql: ${TABLE}.customer_id ;;
  }

  dimension_group: created {
    type: time
    timeframes: [raw, date, week, month, year]
    sql: ${TABLE}.created_at ;;
  }

  measure: total_revenue {
    type: sum
    sql: ${TABLE}.amount ;;
    description: "Net order amount, excluding refunds and cancellations." ;;
    value_format_name: usd
  }

  measure: order_count {
    type: count
    # no description - the linter will flag this one
  }
}
