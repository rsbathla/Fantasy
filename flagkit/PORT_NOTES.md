# Flag-engine port — all five positions (verified byte-parity)

The five duplicated `build_flags_{QB,RB,WR,TE,DST}.py` builders are migrated onto one shared
engine. **Every position's output is byte-for-byte identical to its legacy builder** (sha256
match on all five), so nothing about the model, the numbers, or the file format changes.

## Verification

| Position | players | sha256 (legacy == unified) | parity |
|---|---|---|---|
| QB  | 53  | `c5e45dce0b209483…` | ✅ byte-identical |
| RB  | 104 | `db7959986cebb4c1…` | ✅ byte-identical |
| WR  | 153 | `e92acfc087a78191…` | ✅ byte-identical |
| TE  | 61  | `93d2603d0e53a51b…` | ✅ byte-identical |
| DST | 32  | `2f27dc660fab6538…` | ✅ byte-identical |

Reproduce: `python3 build_flags_v2.py --all` then `cmp boom/flags_<POS>.json` against the
legacy builder's output for each position.

## What this is

| File | Lines | Role |
|---|---|---|
| `flagkit/engine.py` | 127 | The shared engine — player loop, per-week activation, BYE/FA handling, grading, record/week assembly, write. **One copy, all five positions.** |
| `build_flags_v2.py` | 42 | One CLI: `python3 build_flags_v2.py QB` / `--all`. |
| `flagkit/qb.py` | 1199 | QB semantics only. |
| `flagkit/rb.py` | 1013 | RB semantics only. |
| `flagkit/wr.py` | 900 | WR semantics only. |
| `flagkit/te.py` | 1346 | TE semantics only. |
| `flagkit/dst.py` | 308 | DST semantics only. |

Scoring and serialization reuse the existing calibrated paths unchanged — `boom_lib.prob` /
`boom_lib.label` (via `flag_engine.grade`) and `boom_lib.write`.

## Honest impact — read this

**Line count: 5,776 → 4,935 (−841, ~15% smaller).** This is *more modest than the ~70% I first
projected from the DST sample, and that projection was wrong.* Most of those 5,776 lines are
**genuine, position-specific football logic** — hundreds of thresholds (RB ~266, QB ~199, TE ~195,
WR ~171, DST ~48) and verbose `{f,d,amp}` flag descriptions — which *should* differ per position
and does not compress. DST shrank a lot (709 → 308) because it has the fewest thresholds; the
others carry far more real content.

**The actual win is structural, not raw line count:**

- The **~1,000 lines of copy-pasted scaffolding** (load → player loop → per-week loop → grade →
  write → BYE/FA → `main`/accumulators), previously duplicated in all five files, is now a single
  **127-line engine**. Change the plumbing once, not five times.
- **One verified code path** for every position → the whole class of copy-paste divergence bugs is
  eliminated *by construction*. Concretely, this port surfaced and removed:
  - **TE was a silent no-op when run directly** — `build_flags_TE.py` has `def main()` but no
    `if __name__=='__main__': main()` guard. (DST has it; TE didn't.)
  - **WR wrote its output file twice** — a shared verified write, then a redundant raw write that
    clobbered it.
  - **QB hand-rolled its own `mkstemp` writer** instead of the shared `boom_lib.write`; writing was
    handled three different ways across the five files.
  - **Silent per-field inconsistencies** the copies had drifted into, now explicit and centralized
    via small optional hooks: BYE-week `of` (DST/QB/WR use 0; RB/TE carry the player's `of_total`),
    `adp` formatting (RB rounds to 2 decimals; others store raw), and free-agent handling (RB/TE
    emit 18 `BYE` sentinel weeks; WR emits 18 `FA` sentinel weeks).
- Position logic is now cleanly **separated** from plumbing: each `flagkit/<pos>.py` is pure
  semantics behind a 7-function contract (`context`, `base`, `skill_flags`, `line`, `empirical`,
  `opp_data`, and `conditions` *or* `activate`).

## The engine contract (how a position plugs in)

Required: `context`, `base`, `skill_flags`, `line`, `empirical`, `opp_data`, and per-week activation
in either style — `conditions(prof)` (static, DST) or `activate(prof, base, skill_flags, opp_data,
week_ctx)` (functional, QB/RB/WR/TE). `activate` may return a 3-tuple `(flags, mults, of)` or a
4-tuple `(flags, mults, of, lit)` — the 4th element lets WR show suppressor flags while keeping them
out of the `lit` count. Optional hooks (default to DST/QB behavior, which is why those two stayed
byte-identical through every engine change): `adp(v)`, `bye_of(prof)`, `empty_schedule(prof)`.

## Adopting it / next steps

- Replace the five `build_flags_<POS>.py` subprocess calls in `boom_pipeline.py` with
  `build_flags_v2.py --all` (or per-position). Run the Phase-0 golden test (`--full`) to confirm
  the downstream `boom/flags_*.json` are unchanged, then delete the five legacy builders.
- **Further consolidation is available** (not done here, to keep this a pure parity migration): the
  per-position `empirical` summaries and small numeric helpers (`g`/`sg`/`num`) are still near-
  duplicated across the five models and could move into a shared `flagkit/util.py` for another
  meaningful cut — each change still guarded by the byte-parity diff.
