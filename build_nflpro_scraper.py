#!/usr/bin/env python3
"""Convert the NFL Pro (pro.nfl.com) season-aggregated EPA pull (nflpro_epa2.json)
into (a) the week*_ALL.csv interface that refactor/pipeline -> ingest_advanced4.py expects
(2025 season as one pseudo-week; ingest re-aggregates losslessly over a single row), and
(b) a rich both-seasons JSON (nfl_pro_epa.json) for the profiles/dashboard + year-over-year layer.

Auth note: this consumes a file already pulled through the user's own authenticated browser
session. No token is read/printed/stored here; this is pure local reshaping."""
import json, os, csv, sys

SRC = '/mnt/user-data/uploads/nflpro_epa2.json'
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, 'NFL-master', 'nfl_chat_app', 'app_data', 'nfl_pro_scraper')
ARRKEY = {'receiving': 'receivers', 'passing': 'passers', 'rushing': 'rushers'}

d = json.load(open(SRC))
print("tested statuses:", d.get('__tested'), "| auth candidates:", d.get('__nc'))

def rows_for(season, cat):
    block = d.get(f'{season}|{cat}', {})
    return block.get(ARRKEY[cat], []), block.get('total'), d.get(f'{season}|{cat}|st')

# ---- column maps: pipeline-expected header -> NFL Pro season field ----
PASS_MAP = [('Player','displayName'),('DB','db'),('EPA','epa'),('QBP','qbp'),
            ('CPOE','cpoe'),('TTT','avgTTT'),('Avg. Sep','avgSep'),
            # extras kept for the rich layer / future use
            ('Att','att'),('Cmp','cmp'),('Yds','yds'),('TD','td'),('Int','int'),
            ('Sack','sack'),('Rating','rating'),('YPA','ypa'),('aDOT','ayAtt'),
            ('PA%','paDbPct'),('Deep%','deepAttPct'),('TightWin%','twAttPct'),
            ('Blitz%','blitzR'),('xCmp','xCmp'),('GP','gp')]
REC_MAP  = [('Player','displayName'),('Rts','rt'),('Rec EPA','epa'),('Tgt','tgt'),
            ('Rec','rec'),('Avg. Sep','avgSep'),('YACOE','yacoe'),('CROE','croe'),
            ('Yds','yds'),('TD','td'),('aDOT','avgRtDep'),('AyTgt','ayTgt'),
            ('Catch%','catch'),('xCatch','xCatch'),('TightWin%','twPct'),
            ('Deep%','deepTgtPct'),('YACR','yacRec'),('Rating','rating'),
            ('EPA/Rt','epaRt'),('EPA/Tgt','epaTgt'),('TgtRt','tgtRt'),
            ('EzTgt','ezTgt'),('Drop','drop'),('Pos','position'),('GP','gp')]
RUSH_MAP = [('Player','displayName'),('Att','att'),('Rush EPA','epa'),('RYOE','ryoe'),
            ('20+ MPH','rush20PMph'),('15+ MPH','rush15PMph'),('Yds','yds'),('TD','td'),
            ('YPC','ypc'),('Success','success'),('EPA/Att','epaAtt'),('RYOE/Att','ryoeAtt'),
            ('YACO','yaco'),('YACO/Att','yacoAtt'),('YBCO/Att','ybcoAtt'),
            ('xYPC','xYpc'),('StackedBox%','stBoxPct'),('Fum','fum'),
            ('Eff','eff'),('Pos','position'),('GP','gp')]
MAPS = {'passing': PASS_MAP, 'receiving': REC_MAP, 'rushing': RUSH_MAP}

def write_pipeline_csv(season):
    """Write the season aggregate as one pseudo-week per category (week00_ALL.csv)."""
    for cat, cmap in MAPS.items():
        rows, total, st = rows_for(season, cat)
        outdir = os.path.join(SCR, cat)
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, 'week00_ALL.csv')
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow([h for h, _ in cmap])
            for r in rows:
                w.writerow([r.get(src, '') for _, src in cmap])
        print(f"  {season} {cat:10s} -> {os.path.relpath(path, HERE)}  ({len(rows)} rows, status {st})")

# pipeline consumes the CURRENT modeled season (2025)
print("\n[pipeline interface] writing 2025 season aggregate as pseudo-week00:")
write_pipeline_csv('2025')

# ---- rich both-seasons JSON for profiles / dashboard / YoY ----
rich = {'_meta': {'source': 'pro.nfl.com NFL Pro (season-aggregated, qualified set)',
                  'tested': d.get('__tested'),
                  'note': 'qualified players only (qualifiedReceiver/Passer/Rusher=true); '
                          'long-tail low-volume players excluded by NFL Pro qualification threshold'},
        'seasons': {}}
for season in ['2025', '2024']:
    rich['seasons'][season] = {}
    for cat in ['receiving', 'passing', 'rushing']:
        rows, total, st = rows_for(season, cat)
        rich['seasons'][season][cat] = {'total': total, 'status': st, 'rows': rows}
outp = os.path.join(HERE, 'nfl_pro_epa.json')
json.dump(rich, open(outp, 'w'))
print(f"\n[rich layer] wrote {os.path.relpath(outp, HERE)}")
for season in ['2025', '2024']:
    line = []
    for cat in ['receiving', 'passing', 'rushing']:
        line.append(f"{cat[:3]}={len(rich['seasons'][season][cat]['rows'])}")
    print(f"   {season}: " + "  ".join(line))
