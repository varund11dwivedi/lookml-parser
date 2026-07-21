from pathlib import Path

from lookml_parser import parse_project, parse_text

EX = Path(__file__).parent.parent / "examples"


def test_parses_views_and_fields():
    cat = parse_project(EX)
    assert {v.name for v in cat.views} == {"orders", "customers"}
    orders = cat.view("orders")
    assert orders.sql_table_name == "analytics.fact_orders"
    assert "total_revenue" in orders.field_names()


def test_field_kinds_and_flags():
    orders = parse_project(EX).view("orders")
    by_name = {f.name: f for f in orders.fields}
    assert by_name["order_id"].primary_key is True
    assert by_name["customer_id"].hidden is True
    assert by_name["created"].kind == "dimension_group"
    assert by_name["total_revenue"].kind == "measure"
    assert by_name["total_revenue"].type == "sum"


def test_descriptions_survive_quotes_and_semicolons():
    orders = parse_project(EX).view("orders")
    d = next(f for f in orders.fields if f.name == "total_revenue").description
    assert d.startswith("Net order amount")
    assert '"' not in d


def test_explores_and_joins():
    cat = parse_project(EX)
    exp = cat.explores[0]
    assert exp.name == "orders"
    joins = {j.name: j for j in exp.joins}
    assert set(joins) == {"customers", "shipments"}
    assert joins["customers"].relationship == "many_to_one"
    assert joins["shipments"].relationship is None


def test_comments_ignored():
    cat = parse_text("""
    # a leading comment
    view: v {
      dimension: d {   # trailing comment
        type: string
      }
    }
    """)
    assert cat.view("v").field_names() == {"d"}


def test_stats():
    s = parse_project(EX).stats()
    assert s["views"] == 2 and s["explores"] == 1 and s["joins"] == 2
