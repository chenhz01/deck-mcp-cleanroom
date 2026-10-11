"""Self-test for deck-mcp-cleanroom: functional / error-path / extreme-edge."""
from __future__ import annotations

import json
import sys

from deckclean import (audit, check_edit_idempotence, check_op_commutativity,
                       check_order_invariance, check_render_determinism,
                       overlaps, render_deck, render_hash, validate_spec)

_results = []


def record(family: str, name: str, ok: bool, detail: str = "") -> None:
    _results.append((family, name, "PASS" if ok else "FAIL", detail))


def mk(x, y, w, h, typ="text", text=None, font=18):
    el = {"type": typ, "x": x, "y": y, "w": w, "h": h}
    if text is not None:
        el["text"], el["font_size"] = text, font
    return el


GOOD_SPEC = {"slides": [{"elements": [mk(80, 60, 900, 80, text="Title", font=40)]}]}
OVERFLOW_SPEC = {"slides": [{"elements": [mk(80, 60, 100, 40, text="w" * 500, font=36)]}]}
OFFCANVAS_SPEC = {"slides": [{"elements": [mk(1200, 700, 200, 100, typ="image")]}]}
OVERLAP_SPEC = {"slides": [{"elements": [mk(0, 0, 200, 100, text="a"), mk(50, 20, 200, 100, text="b")]}]}
NONIDEM_OPS = [{"slide": 0, "element": 0, "patch": {}}]  # patch {} is fine; use grow-w op below


def _grow_op():
    # a real non-idempotent pattern: patch applied via list append is simulated by
    # an op that appends text each replay -> second replay changes render
    return [{"slide": 0, "element": 0, "patch": {"text": "!"}}]


# ---------------------------------------------------------------- functional


def t_functional():
    r = check_render_determinism(GOOD_SPEC, runs=5)
    record("functional", "render determinism across 5 runs", r["status"] == "PASS")

    good_ops = [{"slide": 0, "element": 0, "patch": {"text": "New Title"}}]
    r = check_edit_idempotence(GOOD_SPEC, good_ops)
    record("functional", "idempotent edit replay", r["status"] == "PASS")

    r = audit(GOOD_SPEC, ops=good_ops)
    record("functional", "clean deck audits PASS", r["verdict"] == "PASS")

    grow_spec = {"slides": [{"elements": [mk(80, 60, 900, 80, text="", font=40)]}]}
    r = check_edit_idempotence(grow_spec, [{"slide": 0, "element": 0, "patch": {"text": "x"}}])
    record("functional", "replay of value-set edit is stable", r["status"] == "PASS")

    r = validate_spec(OVERFLOW_SPEC)
    record("functional", "text overflow detected", any("overflow" in p for p in r))

    r = validate_spec(OFFCANVAS_SPEC)
    record("functional", "off-canvas detected", any("off-canvas" in p for p in r))

    ov = overlaps(OVERLAP_SPEC)
    record("functional", "overlap pair found", len(ov) == 1)

    a1 = render_hash(GOOD_SPEC)
    a2 = render_hash(json.loads(json.dumps(GOOD_SPEC)))  # roundtrip through JSON
    record("functional", "hash survives JSON roundtrip", a1 == a2)


# ---------------------------------------------------------------- error paths


def t_error_paths():
    r = apply_edits_safe = check_edit_idempotence(GOOD_SPEC, [{"slide": 9, "element": 0}])
    record("error", "out-of-range edit op -> ERROR", r["status"] == "ERROR")

    r = check_edit_idempotence(GOOD_SPEC, [{"slide": "zero", "element": None}])
    record("error", "non-numeric indices -> ERROR", r["status"] == "ERROR")

    bad = {"slides": [{"elements": [{"type": "alien", "x": 0, "y": 0, "w": 1, "h": 1}]}]}
    r = validate_spec(bad)
    record("error", "unknown element type flagged", any("unknown type" in p for p in r))

    nonum = {"slides": [{"elements": [{"type": "text", "x": "left", "y": 0, "w": 1, "h": 1}]}]}
    r = validate_spec(nonum)
    record("error", "non-numeric geometry flagged", any("not numeric" in p for p in r))

    badcanvas = {"canvas": {"w": "wide", "h": 720}, "slides": []}
    r = validate_spec(badcanvas)
    record("error", "non-numeric canvas flagged", len(r) == 1)


# ---------------------------------------------------------------- extreme edges


def t_extreme_edges():
    empty = {"slides": []}
    r = audit(empty)
    record("edge", "empty deck audits PASS", r["verdict"] == "PASS")

    slide_no_el = {"slides": [{"elements": []}]}
    record("edge", "slide with zero elements renders stable",
           render_hash(slide_no_el) == render_hash(slide_no_el))

    zero_box = {"slides": [{"elements": [mk(0, 0, 0, 0, text="", font=1)]}]}
    r = validate_spec(zero_box)
    record("edge", "zero-size element accepted (no crash)", r == [])

    tiny_font = {"slides": [{"elements": [mk(0, 0, 10, 10, text="x" * 100000, font=0.5)]}]}
    r = validate_spec(tiny_font)
    record("edge", "100K chars at 0.5pt -> overflow flagged, no crash", len(r) >= 1)

    big = {"slides": [{"elements": [mk(i % 1200, i % 700, 10, 10, typ="shape") for i in range(300)]}]}
    import time
    t0 = time.time()
    ov = overlaps(big)
    dt = time.time() - t0
    record("edge", "300-element overlap scan completes <2 s", dt < 2.0,
           "%.2fs [measured], %d overlaps" % (dt, len(ov)))

    neg = {"slides": [{"elements": [mk(-50, -50, 200, 100, text="neg", font=18)]}]}
    r = validate_spec(neg)
    record("edge", "negative origin (partially off-canvas) tolerated", r == [])

    unicode_spec = {"slides": [{"elements": [mk(0, 0, 400, 50, text="标题 \u00e9\u4e2d \U0001f600", font=18)]}]}
    r = audit(unicode_spec)
    record("edge", "unicode/emoji render determinism", r["results"][0]["status"] == "PASS")


# ------------------------------------------- v0.1.2: edit races + order invariance


def t_race_and_order():
    ops_a = [{"slide": 0, "element": 0, "patch": {"text": "A-text"}}]
    ops_b = [{"slide": 0, "element": 0, "patch": {"text": "B-text"}}]
    r = check_op_commutativity(GOOD_SPEC, ops_a, ops_b)
    record("functional", "conflicting same-field edits race (FAIL)", r["status"] == "FAIL",
           r.get("detail", ""))

    ops_c = [{"slide": 0, "element": 0, "patch": {"x": 100}}]
    ops_d = [{"slide": 0, "element": 0, "patch": {"y": 120}}]
    r = check_op_commutativity(GOOD_SPEC, ops_c, ops_d)
    record("functional", "disjoint-field edits commute", r["status"] == "PASS")

    r = check_order_invariance(GOOD_SPEC)
    record("functional", "single-element order invariance", r["status"] == "PASS")

    multi = {"slides": [{"elements": [mk(0, 0, 50, 50, text="a"), mk(200, 0, 50, 50, text="b"),
                                       mk(400, 0, 50, 50, text="c")]}]}
    r = check_order_invariance(multi)
    record("functional", "3-element reversal does not change render", r["status"] == "PASS")

    r = audit(GOOD_SPEC, ops=ops_c)
    record("functional", "audit includes order_invariance check",
           any(x["check"] == "order_invariance" for x in r["results"]))

    r = check_op_commutativity(GOOD_SPEC, [{"slide": 9, "element": 0}], ops_d)
    record("error", "out-of-range op in race -> ERROR", r["status"] == "ERROR")

    r = check_op_commutativity(GOOD_SPEC, [], [])
    record("edge", "two empty op lists commute", r["status"] == "PASS")

    r = check_order_invariance({"slides": []})
    record("edge", "empty deck is order-invariant", r["status"] == "PASS")


def main() -> int:
    t_functional()
    t_error_paths()
    t_extreme_edges()
    t_race_and_order()
    fails = [r for r in _results if r[2] == "FAIL"]
    for fam, name, status, detail in _results:
        print("[%s] %-9s %s%s" % (status, fam, name, (" | " + detail) if detail else ""))
    print("\n%d checks, %d failed" % (len(_results), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
