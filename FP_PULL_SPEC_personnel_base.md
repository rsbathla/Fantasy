# FP Data Suite — two pulls to add (base receiving + Personnel)

Both entries follow the dimension convention documented in `FP_SWEEP_CATALOG.md`:
`<dimension>/<value>.csv`, one row per player, and **season + position ride in `filterMatch`
automatically** (catalog §6). Drop these into the puller's dimension list (rename keys to match
your puller's actual field names — the shape is what matters).

```python
# ── 1) BASE RECEIVING — no dimension filter → clean full-season alignment (one row/player).
#    This is what turns build_fp_alignment.py from proxy into accurate.
#    Output: NFL-master/FP/2025/Receiving/base_season.csv   (all AlignmentSlot/Wide/Inline/
#    BackfieldRoutesPercentage columns + RoutesTotal + Name + POS come back by default)
BASE_RECEIVING = {
    "tool":        "Receiving",
    "filterMatch": {"season": 2025, "positions": ["WR", "TE", "RB"]},  # your puller's filterMatch keys
    "dimension":   None,          # unfiltered = full-season totals
    "out":         "NFL-master/FP/2025/Receiving/base_season.csv",
}

# ── 2) PERSONNEL — receiving routes split by offensive grouping (11/12/13/21/22 …).
#    This is the "available but not pulled" dimension from catalog §5, now mapped.
#    Output: NFL-master/FP_SWEEP/2025/Receiving/personnel/<grouping>.csv  (11.csv, 12.csv, …)
PERSONNEL = {
    "tool":        "Receiving",
    "filterMatch": {"season": 2025, "positions": ["WR", "TE", "RB"]},
    "dimension":   "personnel",
    "match_type":  "in",          # enum → the `in` operator (catalog type system)
    "param_path":  "<CAPTURE — one authenticated look, see below>",  # FP's internal $$play.* code
    "values":      ["11", "12", "13", "21", "22"],   # add 10/20/23/01/02/12-heavy if your set uses them
    "out_dir":     "NFL-master/FP_SWEEP/2025/Receiving/personnel",    # write each value as <value>.csv
}
```

## The one value I can't fill for you: `param_path`

Your catalog flags these situational filters (§5) as **not probe-discoverable** — FP's internal
`$$play.*` code for Personnel has to be read off one authenticated request, which is the single step
that needs your logged-in session. I won't guess it (a wrong path silently pulls the wrong split).

**Capture it in ~20 seconds, in the session you're already logged into:**
1. Open the **Receiving** tool in the Data Suite, DevTools → **Network** tab.
2. Apply the **Personnel** filter once (pick any grouping, e.g. 11).
3. Look at the request that fires — in its body `filterMatch`, the personnel field is a
   `$$play.…` path (the same shape as, e.g., `dropbackType` → `$$play.pass.dropbackType.dropbackTypeId`).
4. Paste that exact string into `param_path`. Note whether the values come back as the literal
   groupings (`"11"`) or as internal codes — use whatever the request shows for `values`, but still
   name each output file by the human grouping (`11.csv`, `12.csv`, …) so the consumer reads it.

## Then (I run these the moment the CSVs land)

```bash
python3 build_fp_alignment.py --base NFL-master/FP/2025/Receiving/base_season.csv   # accurate, not proxy
python3 build_fp_personnel.py  --repo .                                             # activates personnel
```

- **base_season.csv** → `build_fp_alignment.py` drops the "proxy" flag and cross-checks each player's
  true season Slot/Wide vs NFL Pro (the 306-agree / 78-diverge check, on real data instead of the
  route-weighted proxy).
- **personnel/*.csv** → `build_fp_personnel.py` writes `fp_personnel.json` and upgrades
  `personnel_2026.json` with FP-charted per-player route share by grouping + per-team heavy rate —
  the every-team version of the ARI 12-personnel find.
