# `refactor/` — reference modules (non-breaking)

These modules demonstrate the target architecture **alongside** the working pipeline.
Nothing here is wired into the live engines yet — adopt incrementally (see
`ARCHITECTURE_AUDIT_2026.md` §Refactor Strategy). All are tested/validated.

| Module | Replaces | Kills (problem) |
|---|---|---|
| `statlib.py` | 3 copy-pasted `within_pos_pctl` impls in dfs_scenarios + fusion | duplicated stats math; ambiguous NaN policy |
| `parse.py` | `num()`×11, `pct()`×6, team maps ×3, `pnum`/`ab` | duplicated parsers; 3 divergent team-code maps |
| `featurestore.py` | the 12 read→merge→rewrite ingest scripts | non-atomic CSV write; csv/json desync; silent skips |
| `registry.py` (+ `columns.json`) | nothing (new) | 139 columns with no provenance/coverage record |
| `pipeline.py` | the hand-run 18-step chain | no orchestrator; ordering footguns; silent column loss |
| `tests/test_refactor.py` | nothing (new) | zero tests (0/26 files) |

## Validation evidence
- `python3 refactor/tests/test_refactor.py` → 6/6 PASS
- `statlib.pctl` == live `dfs_scenarios.within_pos_pctl` exactly (371 rows, real data)
- `featurestore` declarative spec merges sis_* onto 145 WR/TE — identical to live `ingest_advanced6`
- `registry.py` → 139/139 columns registered, 0 unregistered
- `pipeline.py --check` → features.csv/json in sync, all 18 stages' expected columns present
