# deck-mcp-cleanroom

A cleanroom acceptance harness for deck/presentation engines: it proves a slide spec renders deterministically, that edit replays are idempotent, and that layout is sane (overlaps, off-canvas elements, text overflow) — then emits a PASS / REVIEW / REJECT report. If an agent assembles your decks unattended, run this audit before anyone presents the result.

**Confidence: High (85%)** that hash-based determinism + replay idempotence catches the retry-drift bugs agent loops produce; **Medium (65%)** that the heuristic text-overflow estimate (chars-per-line ≈ w / 0.6·font) matches your renderer's metrics [estimated].

## Problem

Agent-built decks fail in boring, preventable ways: the same spec renders differently across runs (non-deterministic ordering, timestamps, locale), a retried edit appends the title twice, an element lands at x=1200 on a 1280 canvas, or the 500-character "headline" overflows its 80-px box. Template tools catch none of this, and human reviewers see it only after export. Contract checking — not content checking — is the unguarded half of the deck pipeline.

- **Why novel:** the family idea is "clean-room acceptance": verify the engine's behavioral contract (deterministic output, honest idempotence) instead of judging slide content.
- **Overlooked angle:** a deck engine that exposes a pure function `spec → render string` becomes regression-testable with nothing more than a SHA-256 — pixel-accurate screenshot diffs can come later.

## How it works

Input is a JSON spec (`canvas` + `slides[]` with typed, positioned elements) and an optional `edits` op list. The harness runs four checks:

| Check | Method | Verdict trigger |
|---|---|---|
| render_determinism | render N times, SHA-256 of canonical XML output | hashes differ |
| edit_idempotence | apply op list once → hash; replay on result → hash | hashes differ |
| layout_validation | required fields, numeric geometry, off-canvas bounds, overflow estimate | any problem |
| overlap_scan | pairwise bounding-box intersection per slide | WARN (not fail) |
| order_invariance | reverse each slide's element list, re-render | hash changes |
| op_commutativity | apply op lists A→B and B→A, compare hashes | hashes differ |

The renderer is deliberately minimal: canonical XML text (elements sorted by y then x, XML-escaped text), so it is byte-stable without fonts or rendering engines. Pass a second op list as `edits_b` in the audit payload (or use `--demo`) to enable the race probe. Exit codes: 0 = PASS/REVIEW, 1 = REJECT, 2 = ERROR.

## How this differs from ykuwai/ppt-mcp and Ayushmaniar/powerpoint-mcp

Both anchors are strong at what they do, and what they do is drive a *live* PowerPoint: ykuwai/ppt-mcp (93★) exposes 156 tools across 26 categories over COM on Windows and Apple Events on macOS, with real-time on-screen edits, theme-color awareness, and 2,500+ Material Symbols insertion; Ayushmaniar/powerpoint-mcp (119★, Windows-only via pywin32) adds template-first deck building, bidirectional read/edit of open presentations, `slide_snapshot` visual analysis, and native LaTeX equations. Neither will run on a machine without PowerPoint installed, and neither README describes any behavioral verification of the edit stream itself.

This repo has zero presentation capability — it cannot produce a single slide. What it adds on top of engines like those two (their export/import surface can be reduced to a spec + op stream, which is all this harness consumes):

- **Edit-race probe (op commutativity)** — ppt-mcp's README highlights locking a session to one presentation to avoid wrong-file edits, but says nothing about *two agents editing the same deck concurrently*. `check_op_commutativity` applies op lists in both orders and flags divergence — the race that neither anchor's docs address.
- **Order-invariance audit** — agent pipelines assemble element lists in arbitrary order (parallel slide builders, retry re-emission). Neither anchor specifies whether output depends on element order. This harness reverses each slide's element list and requires a byte-identical render, catching order-dependent output before it ships.

Use ppt-mcp or powerpoint-mcp to build the deck; use this harness to prove the edit stream is replay-safe before anyone presents it.

## Quickstart (~2 min)

```bash
# 1. Self-test: 28 checks, functional / error-path / extreme-edge (~1 s)
python self_test.py

# 2. Demo audit — the demo deck intentionally has an off-canvas image,
#    an overlapping text pair, and an overflowing headline (~1 s)
python cli.py audit --demo        # -> REJECT, exit 1

# 3. Audit your own deck: spec + edits (+ optional edits_b race pair) in one JSON payload
python cli.py audit my_deck.json --report report.json
```

## Why not X

| Alternative | Why not |
|---|---|
| Screenshot/pixel diff (perceptual hash) | Catches visual drift but needs a real renderer + image deps; can't distinguish "edit replayed" from "font changed"; this harness needs zero deps and explains *why* |
| python-pptx round-trip validation | Checks OOXML well-formedness, not behavioral contract; says nothing about determinism or edit replay |
| Human review in a slide editor | Reviewers catch ugliness, not x=1200-on-1280 or second-replay drift; doesn't scale to agent-generated volume |
| Template linters (PPTX schema lint) | Schema-valid decks can still be non-deterministic or non-idempotent; lint is necessary, contract is the missing half |

## Minimal Fallback (PLAN B)

No Python? Enforce the core contract in one line of shell: render your spec twice and `diff` the outputs — identical bytes is the determinism check. The spec schema and the four-check table above are the full contract; any language can re-implement them in ~100 lines. The `render` subcommand's XML output is the reference serialization.

## Design Trade-offs

Priority order: **safety > determinism > layout coverage**. We hash a canonical text render instead of comparing pixel output (loses font-level fidelity, gains zero-dependency reproducibility). Overlaps are a WARN, not REJECT — designers legitimately stack shapes, so overlapping boxes alone shouldn't block a deck. Text overflow is a conservative geometric estimate, flagged as such; it may false-positive on tight fonts and never false-silent on absurd inputs. Edit ops are patch-merge only — richer op semantics would require trusting the engine's own op log.

## Limits & Second-order Effects

- The overflow heuristic is calibrated for default sans-serif metrics; a dense font can fool it. Treat it as a smoke test, not typography.
- If this audit becomes the gate, engines may optimize for the *canonical render string* rather than real visual output (Goodhart) — keep screenshot spot-checks in the loop for hero decks.
- Idempotence is checked for the provided op list only; a different op ordering may still drift.
- WARN-tolerant overlap policy may train teams to ignore warnings entirely.

## FAQ

**Does this render real slides?** No. It renders a canonical XML fingerprint of the spec. It proves the engine's contract, not the aesthetics — pair it with screenshot review for final decks.

**Why is overlap only a warning?** Layered shapes and background fills are legitimate design. The REJECT tier is reserved for contract violations (non-determinism, non-idempotence) and hard layout errors (off-canvas, overflow).

**When NOT to use this?** Skip it if your engine is already a pure function used once per deck with no retries (determinism checks add nothing to a one-shot, no-state flow), or for hand-designed decks where a human opens the file anyway — the audit targets unattended agent pipelines. And don't use it as a design critique tool; it will not tell you the deck is ugly.

**Is this tied to PowerPoint/OOXML?** No — the spec is engine-agnostic JSON. Anything that can emit a slide spec (an MCP deck server, a python-pptx script, a hand-written file) can be audited.

## [Core Assumptions]

1. SHA-256 over a canonical text render is a sufficient drift detector for this threat model (accidental non-determinism, not adversarial collision).
2. Deck engines can expose their spec as JSON and their edits as replayable op lists — the MCP-command pattern this family assumes.
3. The 0.6·font char-width heuristic is a reasonable smoke-test bound for default sans-serif text [estimated, see Limits].
4. Off-canvas and overflow are hard failures while overlap is stylistic — a policy choice, stated so users can re-tune it.

*Data as of 2026-10-11. Measured: 28/28 self-test checks (~1 s) and 300-element overlap scan 0.02 s, both reproducible via `python self_test.py` on Windows 10 / CPython 3.11. Anchor facts (tool counts, stars, platform notes) from the anchors' READMEs as of this date. Other timings [estimated].*
