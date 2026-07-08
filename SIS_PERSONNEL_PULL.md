# SIS personnel — pull recipe (second source for the FP×SIS personnel cross-check)

Goal: pull each NFL offense's **personnel usage** from SIS DataHub and diff it against the FP personnel
we just landed (`fp_personnel.json`). Personnel then has two independent sources, exactly like alignment
has FP + NFL Pro. You run the pull on your own SIS subscription (the bearer never leaves your box);
`build_sis_personnel.py` does the aggregation + cross-check.

## The pull uses your existing SIS tooling
Per `SIS_PULLER.md`, the SIS query form (`form#querybuilder`) already exposes a **`PersonnelFilters.*`**
field group, and the NFL endpoint is auto-detected. So personnel is pullable through the same
console-paste flow as your man/zone and value tables — no new mechanism.

1. Be logged in on the SIS DataHub **NFL** Players (or Teams) leaderboard.
2. Paste `bbdfs/tools/sis_pull_full.js` into the console.
3. **Discover the personnel field** (one-time, like FP's parameter path):
   ```js
   sisDiscover();   // lists form fields; look for the PersonnelFilters.* entries and their option values
   ```
   Note the field name (e.g. `PersonnelFilters.Groupings` or similar) and the value codes for 11/12/13/21/22.
4. **Pull per grouping** (mirrors the FP code sweep) — one call per grouping, then save the rows:
   ```js
   const groupings = { "11":<code>, "12":<code>, "13":<code>, "21":<code>, "22":<code> };  // from step 3
   const out = [];
   for (const [label, code] of Object.entries(groupings)) {
     const d = await sisPullAll({ metricGroup: 5 /*Receiving*/, seasonFrom: 2025, seasonTo: 2025,
                                  extra: { "PersonnelFilters.Groupings": code } });
     d.forEach(r => out.push({ ...r, personnel: label }));   // tag each row with its grouping
   }
   sisDownload(out, "sis_personnel_2025.json");
   ```
   (If SIS instead offers a single **team personnel report** that returns all groupings at once, pull that
   — the consumer reads either shape.)
5. Save the file to `NFL-master/SIS/personnel_2025.json`.

## Then I run the cross-check
```
python3 build_sis_personnel.py --sis NFL-master/SIS/personnel_2025.json
```
It aggregates SIS to per-team heavy-rate + mix and diffs each team vs `fp_personnel.json`
(`agree` / `DIVERGE` on the non-11 "heavy" rate). If column auto-detect misses, it prints the columns it
sees so we pin `--team-col/--grouping-col/--count-col` (same reconcile-against-real-data step we did for FP).

## Note
- It's your subscription — the `sisBatch`/`sisPullAll` helpers already space calls out; don't hammer it.
- If the existing `sis_pull.js` is awkward for personnel, capture ONE SIS request (Copy as cURL, with a
  personnel filter applied) the way you did for FP, and I'll build a dedicated SIS personnel puller that
  replays it across groupings — same seed-and-iterate pattern.
