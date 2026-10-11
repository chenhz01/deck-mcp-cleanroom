"""deck-mcp-cleanroom: cleanroom acceptance harness for deck/presentation engines.

Pure standard library. Independent from any CAD sibling repo. Verifies:
  1. Render determinism   - identical spec -> byte-identical canonical render.
  2. Edit idempotence     - replaying the same edit op list changes nothing further.
  3. Layout sanity        - overlaps, off-canvas elements, estimated text overflow.
No OOXML, no fonts, no network: the renderer emits canonical XML-ish text.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, List

CANVAS_DEFAULT = {"w": 1280, "h": 720}

# ---------------------------------------------------------------- spec model


def _validate_element(el: dict, canvas: dict, idx: int) -> List[str]:
    problems = []
    for k in ("type", "x", "y", "w", "h"):
        if k not in el:
            problems.append("element %d missing %r" % (idx, k))
    if problems:
        return problems
    if el["type"] not in ("text", "shape", "image"):
        problems.append("element %d unknown type %r" % (idx, el["type"]))
    numeric = all(isinstance(el[k], (int, float)) and not isinstance(el[k], bool) for k in ("x", "y", "w", "h"))
    if not numeric:
        for k in ("x", "y", "w", "h"):
            if not isinstance(el[k], (int, float)) or isinstance(el[k], bool):
                problems.append("element %d field %r not numeric" % (idx, k))
        return problems
    if el["x"] + el["w"] > canvas["w"] + 1e-9 or el["y"] + el["h"] > canvas["h"] + 1e-9:
        problems.append("element %d extends off-canvas" % idx)
    if el["type"] == "text":
        est = _text_overflow(el)
        if est:
            problems.append("element %d %s" % (idx, est))
    return problems


def _text_overflow(el: dict) -> str:
    """Estimate overflow: chars-per-line ~ w/(0.6*font), lines ~ area budget."""
    text = str(el.get("text", ""))
    font = float(el.get("font_size", 18))
    cpl = max(1, int(el["w"] / (0.6 * font)))
    usable_h = el["h"]
    line_h = font * 1.25
    # bullet markers count as chars too
    lines_needed = -(-len(text) // cpl)  # ceil
    if lines_needed * line_h > usable_h + 1e-9:
        return ("text likely overflows box (%d chars need ~%d lines of height %.0f > %.0f)"
                % (len(text), lines_needed, lines_needed * line_h, usable_h))
    return ""


def validate_spec(spec: dict) -> List[str]:
    problems = []
    canvas = spec.get("canvas", CANVAS_DEFAULT)
    if not isinstance(canvas.get("w"), (int, float)) or not isinstance(canvas.get("h"), (int, float)):
        problems.append("canvas w/h must be numeric")
        return problems
    for i, slide in enumerate(spec.get("slides", [])):
        if not isinstance(slide, dict):
            problems.append("slide %d is not an object" % i)
            continue
        for j, el in enumerate(slide.get("elements", [])):
            problems.extend(_validate_element(el, canvas, i * 1000 + j))
    return problems


def overlaps(spec: dict, pad: float = 0.0) -> List[str]:
    """Report pairwise bounding-box overlaps within each slide."""
    out = []
    for i, slide in enumerate(spec.get("slides", [])):
        els = slide.get("elements", [])
        for a in range(len(els)):
            for b in range(a + 1, len(els)):
                ea, eb = els[a], els[b]
                if (ea["x"] < eb["x"] + eb["w"] - pad and eb["x"] < ea["x"] + ea["w"] - pad and
                        ea["y"] < eb["y"] + eb["h"] - pad and eb["y"] < ea["y"] + ea["h"] - pad):
                    out.append("slide %d: elements %d and %d overlap" % (i, a, b))
    return out


# ---------------------------------------------------------------- render

def render_slide_xml(slide: dict, index: int) -> str:
    parts = ['<slide n="%d">' % index]
    for el in sorted(slide.get("elements", []), key=lambda e: (e["y"], e["x"])):
        parts.append('<el type="%s" x="%s" y="%s" w="%s" h="%s">%s</el>' % (
            el["type"], el["x"], el["y"], el["w"], el["h"],
            str(el.get("text", "")).replace("&", "&amp;").replace("<", "&lt;")))
    parts.append("</slide>")
    return "".join(parts)


def render_deck(spec: dict) -> str:
    """Deterministic canonical render string (stable across runs/machines)."""
    canvas = spec.get("canvas", CANVAS_DEFAULT)
    parts = ['<deck w="%s" h="%s">' % (canvas["w"], canvas["h"])]
    for i, slide in enumerate(spec.get("slides", [])):
        parts.append(render_slide_xml(slide, i))
    parts.append("</deck>")
    return "".join(parts)


def render_hash(spec: dict) -> str:
    return hashlib.sha256(render_deck(spec).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- harness checks

def check_render_determinism(spec: dict, runs: int = 3) -> dict:
    hashes = [render_hash(spec) for _ in range(max(1, runs))]
    ok = len(set(hashes)) == 1
    return {"check": "render_determinism", "status": "PASS" if ok else "FAIL",
            "hashes": hashes[:2], "detail": "stable" if ok else "same spec rendered differently"}


def apply_edits(spec: dict, ops: List[dict]) -> dict:
    """Deep-copy-free edit application on a fresh copy per call (import copy)."""
    import copy
    s = copy.deepcopy(spec)
    for op in ops:
        try:
            si, ei = int(op["slide"]), int(op["element"])
            s["slides"][si]["elements"][ei].update(op.get("patch", {}))
        except (KeyError, IndexError, TypeError, ValueError):
            return {"ok": False, "error": "bad op %r" % (op,)}
    return {"ok": True, "spec": s}


def check_edit_idempotence(spec: dict, ops: List[dict]) -> dict:
    """Apply the op list once, hash; apply once more to the result, hash.

    If a second identical replay changes the hash, agents retrying edits
    will drift the deck.
    """
    r1 = apply_edits(spec, ops)
    if not r1["ok"]:
        return {"check": "edit_idempotence", "status": "ERROR", "error": r1["error"]}
    h1 = render_hash(r1["spec"])
    r2 = apply_edits(r1["spec"], ops)
    if not r2["ok"]:
        return {"check": "edit_idempotence", "status": "ERROR", "error": r2["error"]}
    h2 = render_hash(r2["spec"])
    ok = h1 == h2
    return {"check": "edit_idempotence", "status": "PASS" if ok else "FAIL",
            "detail": "replay is a no-op" if ok else "second identical replay changed the render"}


# ---------------------------------------------------------------- v0.1.2 additions

def check_op_commutativity(spec: dict, ops_a: List[dict], ops_b: List[dict]) -> dict:
    """Concurrent-agent race probe: apply A then B vs B then A, compare hashes.

    Divergence means op order matters — two agents editing the same deck in
    parallel will produce order-dependent results, and neither retry nor
    idempotence probing alone reveals it.
    """
    ra = apply_edits(spec, ops_a)
    rb = apply_edits(spec, ops_b)
    ra2 = apply_edits(ra["spec"], ops_b) if ra["ok"] else ra
    rb2 = apply_edits(rb["spec"], ops_a) if rb["ok"] else rb
    if not (ra2.get("ok") and rb2.get("ok")):
        return {"check": "op_commutativity", "status": "ERROR",
                "error": (ra2.get("error") or rb2.get("error") or "an op list failed to apply")}
    ok = render_hash(ra2["spec"]) == render_hash(rb2["spec"])
    return {"check": "op_commutativity", "status": "PASS" if ok else "FAIL",
            "detail": "order-independent" if ok else "A->B and B->A diverge: parallel agents will race on this op pair"}


def check_order_invariance(spec: dict) -> dict:
    """Reversing each slide's element list must not change the canonical render.

    The renderer sorts by (y, x), so input order should be irrelevant; a hash
    change means the output depends on how the spec was assembled — a silent
    non-determinism when different agents emit elements in different orders.
    Elements sharing identical (y, x) keys are genuinely ambiguous and will
    trip this check; that is informative, not a false positive.
    """
    import copy
    s2 = copy.deepcopy(spec)
    for slide in s2.get("slides", []):
        if isinstance(slide, dict) and isinstance(slide.get("elements"), list):
            slide["elements"] = list(reversed(slide["elements"]))
    ok = render_hash(spec) == render_hash(s2)
    return {"check": "order_invariance", "status": "PASS" if ok else "FAIL",
            "detail": "render independent of element order" if ok
            else "reversing element order changed the render (sort-key collision or order-dependent output)"}


def audit(spec: dict, ops: List[dict] | None = None, runs: int = 3, ops_b: List[dict] | None = None) -> dict:
    results = [check_render_determinism(spec, runs)]
    if ops is not None:
        results.append(check_edit_idempotence(spec, ops))
    layout = validate_spec(spec)
    results.append({"check": "layout_validation", "status": "PASS" if not layout else "FAIL",
                    "detail": "; ".join(layout) if layout else "no problems"})
    ov = overlaps(spec)
    results.append({"check": "overlap_scan", "status": "PASS" if not ov else "WARN",
                    "detail": "; ".join(ov[:5]) if ov else "no overlaps"})
    results.append(check_order_invariance(spec))
    if ops is not None and ops_b is not None:
        results.append(check_op_commutativity(spec, ops, ops_b))
    hard_fail = any(r["status"] == "FAIL" for r in results)
    errored = any(r["status"] == "ERROR" for r in results)
    verdict = "ERROR" if errored else ("REJECT" if hard_fail else ("REVIEW" if any(r["status"] == "WARN" for r in results) else "PASS"))
    return {"tool": "deck-mcp-cleanroom", "verdict": verdict, "results": results}
