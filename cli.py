"""CLI for deck-mcp-cleanroom. Pure argparse, standard library only."""
from __future__ import annotations

import argparse
import json
import sys

from deckclean import audit, overlaps, render_deck, validate_spec

DEMO_SPEC = {
    "canvas": {"w": 1280, "h": 720},
    "slides": [
        {"elements": [
            {"type": "text", "x": 80, "y": 60, "w": 900, "h": 80, "text": "Quarterly Review", "font_size": 40},
            {"type": "shape", "x": 80, "y": 200, "w": 500, "h": 300},
        ]},
        {"elements": [
            {"type": "text", "x": 80, "y": 60, "w": 300, "h": 60, "text": "Overflowing headline text that simply does not fit inside this narrow box at all", "font_size": 36},
            {"type": "text", "x": 200, "y": 90, "w": 400, "h": 100, "text": "overlapping note", "font_size": 18},
            {"type": "image", "x": 1200, "y": 700, "w": 200, "h": 100},
        ]},
    ],
}

DEMO_OPS = [{"slide": 0, "element": 0, "patch": {"text": "Quarterly Review 2026"}}]
DEMO_OPS_B = [{"slide": 0, "element": 1, "patch": {"x": 120}}]  # disjoint -> commutes


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_validate(args: argparse.Namespace) -> int:
    spec = DEMO_SPEC if args.demo else _load_json(args.spec)
    problems = validate_spec(spec)
    ov = overlaps(spec)
    for p in problems:
        print("PROBLEM:", p)
    for o in ov:
        print("OVERLAP:", o)
    print("%d problems, %d overlaps" % (len(problems), len(ov)))
    return 0 if not problems else 1


def cmd_render(args: argparse.Namespace) -> int:
    spec = DEMO_SPEC if args.demo else _load_json(args.spec)
    print(render_deck(spec))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    if args.demo:
        spec, ops, ops_b = DEMO_SPEC, DEMO_OPS, DEMO_OPS_B
    else:
        payload = _load_json(args.spec)
        spec = payload.get("spec", payload)
        ops = payload.get("edits", [])
        ops_b = payload.get("edits_b")
    report = audit(spec, ops=ops, runs=args.runs, ops_b=ops_b)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
    return {"PASS": 0, "REVIEW": 0, "REJECT": 1, "ERROR": 2}[report["verdict"]]


def cmd_spec_template(_args: argparse.Namespace) -> int:
    print(json.dumps({"spec": DEMO_SPEC, "edits": DEMO_OPS, "edits_b": DEMO_OPS_B}, indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="deck-mcp-cleanroom",
                                description="Cleanroom acceptance audit for deck/presentation engines.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="full audit: determinism, edit idempotence, layout")
    a.add_argument("spec", nargs="?", help="path to deck spec JSON (or {spec,edits} payload)")
    a.add_argument("--demo", action="store_true", help="audit the built-in demo deck")
    a.add_argument("--runs", type=int, default=3, help="determinism repetitions")
    a.add_argument("--report", help="write JSON report to this path")
    a.set_defaults(func=cmd_audit)

    v = sub.add_parser("validate", help="layout validation + overlap scan only")
    v.add_argument("spec", nargs="?")
    v.add_argument("--demo", action="store_true")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("render", help="emit the canonical deterministic render")
    r.add_argument("spec", nargs="?")
    r.add_argument("--demo", action="store_true")
    r.set_defaults(func=cmd_render)

    t = sub.add_parser("spec-template", help="print a starter {spec, edits} payload")
    t.set_defaults(func=cmd_spec_template)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
