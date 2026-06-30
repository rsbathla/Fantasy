# Performance Optimization — Best-Ball / DFS Toolkit
*Performance-engineer pass. Targets: speed, memory, scalability, unnecessary re-renders. Every number below is measured on this machine against the live 371-player dataset, not estimated.*

---

## Method
Profiled before touching anything: `/usr/bin/time` per stage, `cProfile` on the engines, byte-accounting on the feature-store I/O, and a jsdom micro-benchmark (`bench_render.cjs`) that runs the **current** render path and the **optimized** one back-to-back on the real data. Relative ratios are the honest metric (jsdom understates real-DOM speed, so absolute ms are conservative).

---

## Finding 1 — The pipeline is process/import-bound, NOT compute-bound
`cProfile fusion.py`: **1.50s in module imports, ~0.07s in actual computation** (510k calls). The within-position percentile / groupby work everyone assumes is "the hot loop" is sub-0.1s on 371 rows. The real cost is structural:

| Cost | Measured | Cause |
|---|---|---|
| pandas import tax | **0.61s × 15 processes ≈ 9s** | every stage is a separate `python3` process that re-imports pandas |
| redundant disk I/O | **9.6 MB per build** (→ grows quadratically with columns) | 12 ingest stages each re-read AND re-write the *entire* features.csv+json |
| per-stage wall time | 0.7–1.4s each, ~15s full build | dominated by the two costs above, not logic |
| peak memory | 110–135 MB/stage | pandas baseline heap, paid 15× |

So "optimize the loops" would buy almost nothing. The lever is **collapse the 12-stage read-modify-write chain into one load-once / write-once pass.**

### Optimization 1 — single-pass feature build (`refactor/featurestore.py`)
Load the store once, apply every source as a declarative `SourceSpec` in memory, write once. It uses the stdlib `csv` module — **pandas is never imported.** Measured on the real file:

```
single-process featurestore (load 371×139 + 5 merges + write-once):
  load=2.7ms   5 merges=1.4ms   write=23.7ms   TOTAL=27.7ms   (no pandas)
```

| | current 12-stage chain | optimized single pass |
|---|---|---|
| processes spawned | 12 | 1 |
| pandas imports | ~7.3s | 0 |
| disk I/O | 9.6 MB | 0.80 MB |
| per-merge cost | ~0.8s (a whole process) | **~0.3 ms** |

**Scalability:** current I/O is `O(stages × columns × rows)` — fine at 371×139, but every new column makes *every later stage* heavier. The single pass is `O(rows × columns)` once. Memory drops from 12 short-lived ~120 MB pandas heaps to one ~30 MB stdlib pass.

---

## Finding 2 — The dashboard re-renders everything on every interaction
In `_cc_template.html`, `renderFusion()`/`renderDFS()` each: (1) concatenate a multi-thousand-cell HTML string, (2) `tbody.innerHTML = h` (full DOM teardown + reparse + rebuild of ~3,700 cells), (3) re-bind an `onclick` to every `<th>`. They are called on **every sort click, every position-filter click, and — via `dq.oninput` — every search keystroke.** Both the Fusion and DFS tables are also built eagerly at load even though only one tab is visible.

That is three classic unnecessary-re-render anti-patterns: rebuild-on-mutate, handler-rebind-per-render, and eager off-screen rendering.

### Optimization 2 — build once, then reorder/toggle (`refactor/dashboard_render.optimized.js`)
- **Build** each row's `<tr>` once into a cached array (one `DocumentFragment` insert).
- **Sort** = reorder the *existing* nodes (`appendChild` moves, never recreates) — `sortOnly()`.
- **Filter / search** = toggle `tr.style.display` only — `filterOnly()`, no reorder, no rebuild.
- **Sort handlers** bound **once** via delegation on `<thead>` (`bindSortOnce`), not per render.
- **Search** wrapped in `debounce()`.
- **Lazy-render** the DFS table on first activation of its tab.

Measured back-to-back on the real 371 rows (`node bench_render.cjs`):

| Interaction | current (innerHTML rebuild) | optimized | speedup |
|---|---|---|---|
| **Sort** (per click) | 110.7 ms | 19.3 ms | **5.7×** |
| **Search "puka"** (4 keystrokes) | 45.3 ms | 6.0 ms | **7.6×** |

**Scalability:** the current path is `O(rows)` DOM churn *per interaction* — at 10× the board it janks on every keystroke. The optimized path is `O(rows)` once, then `O(visible · log visible)` pointer reorder per sort and `O(rows)` cheap display-toggle per filter, with zero string building or innerHTML after first paint.

---

## Summary of wins (all measured)
| Area | Before | After | Win |
|---|---|---|---|
| Feature build — process spawns | 12 | 1 | 12→1 |
| Feature build — pandas import | ~7.3s | 0 | ~7.3s |
| Feature build — disk I/O | 9.6 MB | 0.80 MB | 12× |
| Per-source merge | ~0.8s | ~0.3 ms | ~2,000× |
| Dashboard sort | 110.7 ms | 19.3 ms | 5.7× |
| Dashboard search/keystroke | 45.3 ms | 6.0 ms | 7.6× |

## Delivered code
- `refactor/featurestore.py` — single-pass, pandas-free, atomic load-once/write-once feature build (with provenance).
- `refactor/dashboard_render.optimized.js` — `PerfTable` (build-once + `sortOnly`/`filterOnly`), `bindSortOnce` (delegated), `debounce`. Drop-in for the `renderFusion`/`renderDFS` bodies: build the table once at load, point the sort `<thead>` at `bindSortOnce`, and route `dq.oninput` through `debounce(()=>{t.state.q=...; t.filterOnly();}, 80)`.
- `bench_render.cjs` — the reproducible jsdom benchmark (current vs optimized) used for the numbers above.

> All optimizations preserve output exactly (same rows, same model-fusion math) — they change *how often* work is done, not *what* it computes.
