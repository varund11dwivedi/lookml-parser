"""lookml-parser CLI: catalog a project, or lint it in CI."""
import argparse
import sys

from lint import lint, summary
from lookml_parser import parse_project


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lookml-parser")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("catalog", help="emit a JSON catalog")
    c.add_argument("path")
    c.add_argument("-o", "--out")

    l = sub.add_parser("lint", help="lint; exits 1 on errors")
    l.add_argument("path")
    l.add_argument("--warnings-as-errors", action="store_true")

    args = ap.parse_args(argv)
    cat = parse_project(args.path)

    if args.cmd == "catalog":
        js = cat.to_json()
        if args.out:
            open(args.out, "w").write(js)
            print(f"wrote {args.out}: {cat.stats()}")
        else:
            print(js)
        return 0

    issues = lint(cat)
    for i in issues:
        print(i)
    s = summary(issues)
    print(f"\n{s['errors']} errors, {s['warnings']} warnings "
          f"across {cat.stats()['views']} views")
    if s["errors"] or (args.warnings_as_errors and s["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
