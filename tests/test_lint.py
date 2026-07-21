from pathlib import Path

from lint import lint, summary
from lookml_parser import parse_project, parse_text

EX = Path(__file__).parent.parent / "examples"


def rules_fired(cat):
    return {i.rule for i in lint(cat)}


def test_example_project_flags_known_problems():
    fired = rules_fired(parse_project(EX))
    assert "missing_description" in fired      # orders.order_count
    assert "naming" in fired                   # customers.Country
    assert "broken_reference" in fired         # shipments is never defined
    assert "join_without_relationship" in fired


def test_clean_project_is_quiet():
    cat = parse_text("""
    view: t {
      dimension: id { primary_key: yes  type: number }
      measure: c { type: count  description: "rows" ;; }
    }
    """)
    assert lint(cat) == []


def test_duplicate_field_is_an_error():
    cat = parse_text("""
    view: v {
      dimension: dup { type: string }
      dimension: dup { type: number }
    }
    """)
    issues = [i for i in lint(cat) if i.rule == "duplicate_field"]
    assert issues and issues[0].severity == "error"


def test_join_without_sql_on():
    cat = parse_text("""
    view: a { dimension: id { primary_key: yes } }
    view: b { dimension: id { primary_key: yes } }
    explore: a { join: b { type: left_outer  relationship: many_to_one } }
    """)
    assert any(i.rule == "join_without_on" for i in lint(cat))


def test_joined_view_needs_primary_key():
    cat = parse_text("""
    view: a { dimension: id { primary_key: yes } }
    view: b { dimension: x { type: string } }
    explore: a {
      join: b { type: left_outer  relationship: many_to_one  sql_on: 1=1 ;; }
    }
    """)
    assert any(i.rule == "missing_primary_key" for i in lint(cat))


def test_summary_counts():
    s = summary(lint(parse_project(EX)))
    assert s["total"] == s["errors"] + s["warnings"]
    assert s["errors"] >= 1
