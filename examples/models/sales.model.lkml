connection: "warehouse"

explore: orders {
  label: "Orders"
  description: "Order-level facts joined to customer attributes."

  join: customers {
    type: left_outer
    relationship: many_to_one
    sql_on: ${orders.customer_id} = ${customers.customer_id} ;;
  }

  join: shipments {
    type: left_outer
    sql_on: ${orders.order_id} = ${shipments.order_id} ;;
  }
}
