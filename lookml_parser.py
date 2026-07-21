"""Parse LookML into a JSON catalog, then lint it.

Written after reading a few thousand lines of other people's LookML during a
migration. Two things I wanted and didn't have: a machine-readable inventory of
what exists, and a way to catch the boring mistakes (missing descriptions,
duplicate dimensions, joins pointing at views nobody defined) before review.

Not a full LookML grammar - a pragmatic block parser that handles the shapes
that actually appear in view and model files.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

BLOCK_RE = re.compile(r'^\s*(\w+)\s*:\s*(\w+)?\s*\{')
PARAM_RE = re.compile(r'^\s*(\w+)\s*:\s*(.+?)\s*;;\s*$')
SIMPLE_RE = re.compile(r'^\s*(\w+)\s*:\s*(.+?)\s*$')


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] if "#" in line and not _in_sql(line)
                     else line for line in text.splitlines())


def _in_sql(line: str) -> bool:
    # '#' inside a sql: block is usually a comment too, but a '#' after ';;'
    # never is. Keep it simple: only protect lines that look like sql params.
    return line.lstrip().startswith(("sql", "html")) and ";;" in line


@dataclass
class Field:
    name: str
    kind: str                      # dimension | dimension_group | measure | filter | parameter
    type: str | None = None
    sql: str | None = None
    description: str | None = None
    label: str | None = None
    hidden: bool = False
    primary_key: bool = False


@dataclass
class View:
    name: str
    file: str
    sql_table_name: str | None = None
    derived: bool = False
    fields: list[Field] = field(default_factory=list)

    def field_names(self) -> set[str]:
        return {f.name for f in self.fields}


@dataclass
class Join:
    name: str
    type: str | None = None
    relationship: str | None = None
    sql_on: str | None = None


@dataclass
class Explore:
    name: str
    file: str
    view_name: str | None = None
    label: str | None = None
    description: str | None = None
    joins: list[Join] = field(default_factory=list)


@dataclass
class Catalog:
    views: list[View] = field(default_factory=list)
    explores: list[Explore] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent)

    def view(self, name: str) -> View | None:
        return next((v for v in self.views if v.name == name), None)

    def stats(self) -> dict:
        return {
            "views": len(self.views),
            "explores": len(self.explores),
            "fields": sum(len(v.fields) for v in self.views),
            "joins": sum(len(e.joins) for e in self.explores),
        }


def _body(lines: list[str], start: int) -> tuple[list[str], int]:
    """Return the lines inside a block opened on `start`, and the index after it.

    Handles single-line blocks (`dimension: id { primary_key: yes }`) as well as
    the usual multi-line form - LookML in the wild uses both.
    """
    depth, out, i = 0, [], start
    while i < len(lines):
        line = lines[i]
        opens, closes = line.count("{"), line.count("}")
        if i == start:
            depth = opens - closes
            if depth <= 0:                      # opened and closed on one line
                inner = line[line.index("{") + 1:line.rindex("}")]
                # split on whitespace-separated params, keeping ;; terminators
                return [seg.strip() for seg in re.split(r"(?<=;;)|\s{2,}", inner)
                        if seg and seg.strip()], i + 1
            i += 1
            continue
        if depth + opens - closes <= 0:
            return out, i + 1
        out.append(line)
        depth += opens - closes
        i += 1
    return out, i


def _params(lines: list[str]) -> dict:
    """Scalar params at this nesting level (skips nested blocks)."""
    params, depth = {}, 0
    for line in lines:
        if depth == 0:
            m = PARAM_RE.match(line) or SIMPLE_RE.match(line)
            if m and "{" not in line:
                params[m.group(1)] = m.group(2).strip().strip('"')
        depth += line.count("{") - line.count("}")
    return params


def parse_view(name: str, body: list[str], path: str) -> View:
    p = _params(body)
    view = View(name=name, file=path, sql_table_name=p.get("sql_table_name"),
                derived="derived_table" in "\n".join(body))
    i = 0
    while i < len(body):
        m = BLOCK_RE.match(body[i])
        if m and m.group(1) in ("dimension", "dimension_group", "measure",
                                "filter", "parameter") and m.group(2):
            inner, nxt = _body(body, i)
            fp = _params(inner)
            view.fields.append(Field(
                name=m.group(2), kind=m.group(1), type=fp.get("type"),
                sql=fp.get("sql"), description=fp.get("description"),
                label=fp.get("label"),
                hidden=fp.get("hidden", "no") == "yes",
                primary_key=fp.get("primary_key", "no") == "yes"))
            i = nxt
        else:
            i += 1
    return view


def parse_explore(name: str, body: list[str], path: str) -> Explore:
    p = _params(body)
    exp = Explore(name=name, file=path, view_name=p.get("view_name"),
                  label=p.get("label"), description=p.get("description"))
    i = 0
    while i < len(body):
        m = BLOCK_RE.match(body[i])
        if m and m.group(1) == "join" and m.group(2):
            inner, nxt = _body(body, i)
            jp = _params(inner)
            exp.joins.append(Join(name=m.group(2), type=jp.get("type"),
                                  relationship=jp.get("relationship"),
                                  sql_on=jp.get("sql_on")))
            i = nxt
        else:
            i += 1
    return exp


def parse_text(text: str, path: str = "<string>") -> Catalog:
    lines = _strip_comments(text).splitlines()
    cat, i = Catalog(), 0
    while i < len(lines):
        m = BLOCK_RE.match(lines[i])
        if m and m.group(2):
            kind, name = m.group(1), m.group(2)
            body, nxt = _body(lines, i)
            if kind == "view":
                cat.views.append(parse_view(name, body, path))
            elif kind == "explore":
                cat.explores.append(parse_explore(name, body, path))
            i = nxt
        else:
            i += 1
    return cat


def parse_project(root: str | Path) -> Catalog:
    """Walk a LookML project directory and merge everything into one catalog."""
    root = Path(root)
    cat = Catalog()
    for p in sorted(root.rglob("*.lkml")):
        part = parse_text(p.read_text(), str(p.relative_to(root)))
        cat.views.extend(part.views)
        cat.explores.extend(part.explores)
    return cat
