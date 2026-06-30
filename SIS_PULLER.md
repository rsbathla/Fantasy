# SIS DataHub CFB — systematic puller (no clicking)

Reverse-engineered so any metric x season x coverage/situation can be pulled programmatically
from the authenticated browser, instead of toggling tabs and downloading by hand.

## The mechanism
The leaderboard table POSTs its query form (`form#querybuilder`, ~685 fields) to a single API:

- **Endpoint:** `POST https://api.sportsinfosolutions.com/api/v1/cfb/players/query`
- **Body:** the serialized `form#querybuilder` (URL-encoded)
- **Auth:** `Authorization: Bearer <access_token>` — the OIDC token stored in the page's
  session storage under the `oidc.user:*` entry (the 401 we saw was only a missing token)
- **Sub-tabs:** Totals / Rates / Value are client-side column views of the SAME response —
  one pull returns every stat, so you never need to toggle them.

## Parameter map (the only fields you usually override)
| Field | Meaning | Values |
|---|---|---|
| `MetricGroup` | metric | Passing=1, Rushing=3, Receiving=5, PassDef=9, PassRush=10, RunDef=11 |
| `TimeFilters.SeasonFrom` / `SeasonTo` | season range | 2016–2025 |
| `PassingFilters.Schemes` | coverage scheme (checkboxes) | MAN = 0 (Cover 0), 1 (Cover 1), 5 (Man Cover 2); ZONE = 2,3,4,6 (Cover 2/3/4/6) |
| (others) | GameFilters.* / SituationFilters.* / PersonnelFilters.* | same form, override as needed |

## Use it
1. Be logged in on the SIS DataHub CFB tab (`pro.sisdatahub.com/cfb/Leaders/Players`).
2. Paste `bbdfs/tools/sis_pull.js` into the console (or it's run for you via the browser tool).
3. Pull anything:
```js
// receiving man vs zone, 2025 college (for the rookie man/zone tag)
const man  = await sisPull({metricGroup:SIS.MG.receiving, seasonFrom:2025, seasonTo:2025, schemes:SIS.MAN});
const zone = await sisPull({metricGroup:SIS.MG.receiving, seasonFrom:2025, seasonTo:2025, schemes:SIS.ZONE});
// or a whole batch, then download each:
const data = await sisBatch([
  {name:"rec_man_2025",  metricGroup:5, seasonFrom:2025, seasonTo:2025, schemes:SIS.MAN},
  {name:"rec_zone_2025", metricGroup:5, seasonFrom:2025, seasonTo:2025, schemes:SIS.ZONE},
]);
sisDownload(data, "sis_rec_manzone_2025.json");
```

## Notes
- One bad request can freeze the renderer; if a call hangs, reload the tab and re-paste.
- Be polite (the batch helper waits 600ms between calls) — it's your own subscription, just don't hammer it.
- The same form drives every filter, so coverage, personnel, down/distance, field position, motion,
  play-action, pressure, etc. are all pull-able by overriding the matching `*.*` field.

---

## Pulling MORE than ~200 rows (the leaderboard cap)

The ~200 cap is **not** a hard limit — it's a page-size field carried inside `form#querybuilder`
(named something like `Take` / `PageSize` / `RowCount` / `DisplayLength`, default ~200). The original
puller serialized the form as-is, so it inherited that default. `bbdfs/tools/sis_pull_full.js` fixes it:

- `sisDiscover()` — lists every form field whose name looks like paging OR whose value is a common
  page size (25/50/100/200/250/…). The one showing **200** is the cap.
- `sisPullAll()` — re-serializes the current report's form with **every** paging-ish field bumped to a
  large number (and appends `Take/Skip/PageSize/RowCount/length/start` as a fallback), then paginates
  until a short page; de-dupes; stores to `window.__sisLast`.
- Endpoint auto-detects `nfl` vs `cfb` from the page URL, so it works on the **NFL** Players leaderboard.

### Steps (NFL defensive Value, full depth)
1. Log in, open `https://pro.sisdatahub.com/nfl/Leaders/Players`, choose the report + season
   (e.g. **Pass Defense, 2025**). The on-page filters ARE the query — no metric codes needed.
2. Paste `bbdfs/tools/sis_pull_full.js` into the console.
3. `sisDiscover()` (optional, to see the cap field) → `await sisPullAll()` → `sisDownload(window.__sisLast,"nfl_pass_defense_2025.json")`.
4. Repeat for **Pass Rush** and **Run Defense**, and again with the season set to **2024**.

Drop the 3 (or 6) JSON files in the `bestball/` folder; the JSON→CSV conversion + wiring into
`normalize_defense_2026.py` is handled on the code side.
