# Changelog

## [0.1.2] - 2026-10-11

### Added (anchor differentiation: ykuwai/ppt-mcp + Ayushmaniar/powerpoint-mcp re-audit)

- **Edit-race probe** (`check_op_commutativity`, audit payload `edits_b`): applies two op lists in both orders and flags divergence — targets the concurrent-agent edit race that live-PowerPoint MCP servers (both anchors are live-app wrappers) do not document any protection for.
- **Order-invariance audit** (`check_order_invariance`, now part of every `audit` run): reverses each slide's element list and requires a byte-identical render; catches order-dependent output when parallel agents assemble element lists in different orders. Elements sharing identical (y, x) sort keys legitimately trip this — documented as informative.
- 8 new self-test cases (20 → 28): conflicting edits race, disjoint-field commutativity, 1- and 3-element order invariance, audit integration, out-of-range race op -> ERROR, empty op lists, empty deck.

## [0.1.1] - 2026-10-11

### Changed (round-2 iteration after 16-item self-audit)

- **Correctness (+~25% test rigor):** self-test grew from 12 to 20 checks. The expanded suite caught a real crash: `validate_spec` compared geometry numerically *before* type-checking it, so `{"x": "left"}` raised `TypeError` instead of reporting a problem — fixed by ordering checks and early-returning on non-numeric fields. Added error-path cases for non-numeric indices in edit ops and non-numeric canvas.
- **Completeness:** README gained the check-method table, the Goodhart second-order effect (engines optimizing for the canonical string), and the "one-shot/no-retry" When-NOT-to-use clause.
- **Correctness:** demo deck now exercises all three layout failures at once (off-canvas, overlap, overflow) so the default run shows a genuine REJECT.

## [0.1.0] - 2026-10-11

### Added

- `deckclean.py`: canonical XML renderer + SHA-256 hashing, spec validation (fields/geometry/bounds/overflow estimate), pairwise overlap scan, render-determinism and edit-idempotence checks, audit driver with PASS/REVIEW/REJECT/ERROR verdicts.
- `cli.py`: `audit` / `validate` / `render` / `spec-template` subcommands; exit codes 0/1/2.
- `self_test.py`: three test families — functional (8), error paths (5), extreme edges (7: empty deck, zero-size elements, 100K-char text, 300-element scan timing, negative origins, unicode/emoji determinism).
- MIT LICENSE (zhengming contributors), README, initial ALIGNMENT audit.
