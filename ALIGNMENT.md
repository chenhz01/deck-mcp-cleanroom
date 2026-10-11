# Alignment Audit (Rules 85-100 / 16 items) — deck-mcp-cleanroom

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | N/A | Not a security-research repo; no dangerous content. |
| 2 | Privacy/keys | PASS | No keys/tokens/real names/emails in any file; placeholder-only examples. |
| 3 | Copyright boundary | PASS | All code/text written fresh; no copied source-repo text; MIT LICENSE present. |
| 4 | Fact-check numbers | PASS | 28/28 checks & 0.02 s overlap scan are measured (repro: `python self_test.py`); overflow heuristic explicitly marked [estimated]; anchor facts dated as-of. |
| 5 | Confidence grading | PASS | README has High (85%) and Medium (65%) [estimated] labels with basis sentences. |
| 6 | Minimal Fallback | PASS | "Minimal Fallback (PLAN B)": render-twice + diff in any shell; schema is the contract. |
| 7 | Quickstart timing | PASS | Quickstart labelled ~2 min, staged (self-test → demo → own deck). |
| 8 | Conflict arbitration | PASS | "Design Trade-offs": safety > determinism > layout coverage, with concrete examples. |
| 9 | Changelog ≥2 iterations | PASS | CHANGELOG v0.1.0 → v0.1.1 → v0.1.2; v0.1.2 adds anchor-differentiation features (edit-race probe, order invariance). |
| 10 | Exemption (session rule) | N/A | Session-level governance item; static repo not applicable. |
| 11 | Knowledge cutoff | PASS | README footer: "Data as of 2026-10-11"; anchor facts dated same. |
| 12 | Explicit assumptions | PASS | `[Core Assumptions]` lists 4 premises. |
| 13 | Three-part self-test | PASS | functional (13) + error paths (6) + extreme edges (9) = 28/28 PASS. |
| 14 | Socratic FAQ | PASS | FAQ "When NOT to use this?" — one-shot no-retry engines, hand-designed decks. |
| 15 | Pareto iteration | PASS | Round 2: 12→20 tests (+67%), one crash fixed. Round 3 (v0.1.2): 20→28 tests (+40%) + two new capabilities; CHANGELOG-traceable. |
| 16 | ≤60-word opening | PASS | First paragraph is 58 words with a judgment sentence ("run this audit before anyone presents"). |

Additional: **Second-order effects** — "Limits & Second-order Effects" covers Goodhart risk on the canonical render, op-ordering blind spot, and warning fatigue.
