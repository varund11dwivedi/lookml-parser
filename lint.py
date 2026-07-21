"""Lint a parsed catalog. Rules are the mistakes I kept finding in review."""
from __future__ import annotations

import re
from dataclasses import dataclass

from lookml_parser import Catalog

SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class Issue:
    rule: str
    severity: str            # error | warning
    where: str
    message: str

    def __str__(self):
        return f"[{self.severity}] {self.rule}: {self.where} - {self.message}"


def naming(cat: Catalog) -> list[Issue]:
    out = []
    for v in cat.views:
        if not SNAKE.match(v.name):
            out.append(Issue("naming", "warning", f"view {v.name}",
                             "view names should be snake_case"))
        for f in v.fields:
            if not SNAKE.match(f.name):
                out.append(Issue("naming", "warning", f"{v.name}.{f.name}",
                                 "field names should be snake_case"))
    return out


def missing_descriptions(cat: Catalog) -> list[Issue]:
    out = []
    for v in cat.views:
        for f in v.fields:
            if f.kind == "measure" and not f.description and not f.hidden:
                out.append(Issue("missing_description", "warning",
                                 f"{v.name}.{f.name}",
                                 "measures should say what they mean"))
    return out


def duplicate_fields(cat: Catalog) -> list[Issue]:
    out = []
    for v in cat.views:
        seen = set()
        for f in v.fields:
            if f.name in seen:
                out.append(Issue("duplicate_field", "error", f"{v.name}.{f.name}",
                                 "declared more than once in the same view"))
            seen.add(f.name)
    return out


def broken_joins(cat: Catalog) -> list[Issue]:
    """Joins that reference a view the project never defines."""
    known = {v.name for v in cat.views}
    out = []
    for e in cat.explores:
        if e.view_name and e.view_name not in known:
            out.append(Issue("broken_reference", "error", f"explore {e.name}",
                             f"view_name '{e.view_name}' is not defined"))
        for j in e.joins:
            if j.name not in known:
                out.append(Issue("broken_reference", "error",
                                 f"{e.name} -> join {j.name}",
                                 "joined view is not defined in this project"))
            if not j.sql_on:
                out.append(Issue("join_without_on", "error",
                                 f"{e.name} -> join {j.name}",
                                 "join has no sql_on"))
            if j.relationship is None:
                out.append(Issue("join_without_relationship", "warning",
                                 f"{e.name} -> join {j.name}",
                                 "relationship unset; Looker will assume many_to_one"))
    return out


def missing_primary_key(cat: Catalog) -> list[Issue]:
    joined = {j.name for e in cat.explores for j in e.joins}
    out = []
    for v in cat.views:
        if v.name in joined and not any(f.primary_key for f in v.fields):
            out.append(Issue("missing_primary_key", "error", f"view {v.name}",
                             "joined view has no primary_key; fanout risk"))
    return out


RULES = [naming, missing_descriptions, duplicate_fields, broken_joins,
         missing_primary_key]


def lint(cat: Catalog) -> list[Issue]:
    return [i for rule in RULES for i in rule(cat)]


def summary(issues: list[Issue]) -> dict:
    return {"errors": sum(i.severity == "error" for i in issues),
            "warnings": sum(i.severity == "warning" for i in issues),
            "total": len(issues)}
