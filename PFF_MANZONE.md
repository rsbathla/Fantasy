# PFF College — man/zone receiving (CFB) source + recipe

PFF's **"Receiving vs Scheme"** report has WR/TE/RB receiving stats split by MAN vs ZONE coverage
(TGT, REC, YDS, **Y/RR**, aDOT, grade, RTG for each side). This is the college man/zone source.

## Where it lives
- Page: `https://premium.pff.com/ncaa/positions/{season}/{weeks}/receiving-scheme?position=WR,TE,RB,ORCV`
- Data API: `https://premium.pff.com/api/v1/facet/receiving/scheme?league=NCAA&season=2025&division=fbs[&week=...]`
  - auth: PFF uses Clerk session cookies (same-origin); the API base is `premium.pff.com/api/v1/`.
  - NOTE: the SPA freezes the renderer on programmatic fetch/eval, so a scripted pull from inside
    the page is unreliable; navigation + page-read works, and the report has a native CSV export.

## Cleanest pull (CSV export) — set these filters on the page, then click CSV
1. LEAGUE = **NCAA**, SEASON = **2025**
2. WEEKS = **Regular** (the default "AS" is All-Star = tiny samples — must change)
3. DIVISION = **FBS**
4. DRAFT YEAR = **2026**  (isolates the incoming rookie class directly)
5. POSITION = **All** (WR/TE/RB)
6. Click **CSV** (top-right of the report) -> drops `*.csv` in Downloads

## Then tag the class
The export has man/zone Y/RR per player. Feed it to the existing tagger:
`build_manzone_tags.py` (already maps man-YPRR vs zone-YPRR -> within-position percentiles ->
MAN-CAPABLE / ZONE-RELIANT / ALL-AROUND / LIMITED). Point it at the PFF CSV (man Y/RR vs zone Y/RR
columns) and it tags every 2026 prospect, which folds into the rookie profile.
