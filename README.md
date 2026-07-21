# lookml-parser

Parse a LookML project into a JSON catalog, then lint it.

I wrote this after a migration where I read a few thousand lines of someone
else's LookML. Two things I wanted and didn't have: a machine-readable
inventory of what actually exists in the project, and a way to catch the boring
mistakes before they reached review.

```bash
python cli.py catalog ./my_lookml_project -o catalog.json
python cli.py lint ./my_lookml_project        # exits 1 on errors -> drops into CI
```

```
[warning] missing_description: orders.order_count - measures should say what they mean
[warning] naming: customers.Country - field names should be snake_case
[error]   broken_reference: orders -> join shipments - joined view is not defined in this project
[warning] join_without_relationship: orders -> join shipments - relationship unset; Looker will assume many_to_one

1 errors, 3 warnings across 2 views
```

## The rules, and why each exists

| Rule | Severity | Why |
|---|---|---|
| `broken_reference` | error | A join pointing at a view nobody defined. Fails at query time, not at commit time. |
| `duplicate_field` | error | Same dimension declared twice in one view - last one silently wins. |
| `join_without_on` | error | No `sql_on`. Cartesian product waiting to happen. |
| `missing_primary_key` | error | A joined view without a primary key is how you get fanned-out sums that look plausible. |
| `join_without_relationship` | warning | Unset means Looker assumes `many_to_one`. Sometimes right, never explicit. |
| `missing_description` | warning | An undescribed measure is a support ticket in six months. |
| `naming` | warning | snake_case, consistently. |

## The catalog

```json
{
  "views": [{
    "name": "orders",
    "sql_table_name": "analytics.fact_orders",
    "fields": [
      {"name": "order_id", "kind": "dimension", "type": "number", "primary_key": true},
      {"name": "total_revenue", "kind": "measure", "type": "sum",
       "description": "Net order amount, excluding refunds and cancellations."}
    ]
  }],
  "explores": [{"name": "orders", "joins": [{"name": "customers", "relationship": "many_to_one"}]}]
}
```

That JSON is the input to [looker-ai-router](https://github.com/varund11dwivedi/looker-ai-router),
which uses it to decide which explore can answer a given question.

## Scope

A pragmatic block parser, not a full LookML grammar - it handles the shapes that
actually appear in view and model files, including single-line blocks and inline
comments. Liquid templating inside `sql:` is preserved as text rather than
evaluated. No dependencies beyond the standard library.

`python -m pytest tests/` (12 tests) / MIT.
