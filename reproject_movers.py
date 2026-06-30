#!/usr/bin/env python3
"""Fix 1 -- MOVER USAGE RE-PROJECTION.
The feature store carries each player's 2025 usage (tgt_share/carry_share/tgt_pg/car_pg/rec_pg)
keyed by NAME, so a player who changed teams in 2026 still shows the role he had on his OLD team.
build_features.py already flags these players (mover==True, team25!=team) but does NOT re-project
their role. This stage does:

  best  (reproj_clay)        : projected share = Clay 2026 share -> per-game = share x NEW-team volume
  fallback (reproj_carry)    : Clay share missing -> carry the player's 2025 share onto NEW-team volume
                               (assumes role continuity, fixes only the team-context/pace)

Portable skill traits (aDOT, YPRR, EPA, man/zone) are left untouched -- they travel with the player.
Raw 2025 values are preserved under *_25raw (idempotent: re-runs reproject from the raw, not the
already-shifted value). Provenance: usage_src + mover_conf on every skill player. Non-movers are
tagged usage_src='2025_actual' and left as-is. Audit report -> boom/movers_reprojection.json."""
import core, csv, json

POS_CATCH = {'WR':0.64,'TE':0.70,'RB':0.75}  # league catch-rate fallback if player ratio unknown

def num(x):
    try: return float(x)
    except: return None
def pct(v):
    """normalize a share to 0-100 percent (accept fraction or percent)."""
    v=num(v)
    if v is None: return None
    return v*100 if v<=1.0 else v

d=json.load(open(core.P('features.json'),encoding='utf-8'))
players=d['players']
rep=[]; n_clay=n_carry=n_skip=0
for f in players:
    pos=(f.get('pos') or '').upper()
    if pos not in ('WR','TE','RB','QB'):
        continue
    # NOTE: the upstream 'mover' flag is unreliable (CSV stringifies bool -> 'False' is truthy).
    # Recompute authoritatively from normalized teams.
    t25=core.norm_team(str(f.get('team25') or '').strip()); tmn=core.norm_team(str(f.get('team') or '').strip())
    is_mover = bool(t25) and bool(tmn) and t25!=tmn and t25 not in ('NONE','NAN')
    f['mover']=is_mover
    if not is_mover:
        f['usage_src']='2025_actual'; f['mover_conf']=None
        continue
    if tmn=='FA':  # released / unsigned -> no NFL role to project; flag, keep raw
        f['usage_src']='moved_to_FA'; f['mover_conf']='low'
        rep.append({'name':f.get('name'),'pos':pos,'team25':t25,'team':'FA','usage_src':'moved_to_FA','mover_conf':'low'})
        continue
    # NEW-team 2026 volume
    tm_pa = num(f.get('tm_pass_att'))            # team pass att / game
    tm_pl = num(f.get('tm_plays'))               # team plays / game
    tm_car = (tm_pl - tm_pa) if (tm_pl is not None and tm_pa is not None) else None
    # raw 2025 (idempotent: prefer preserved raw if a prior run stored it)
    def raw(k):
        rk=k+'_25raw'
        if rk in f: return num(f.get(rk))
        f[rk]=num(f.get(k)); return num(f.get(k))
    tgt_share25=raw('tgt_share'); car_share25=raw('carry_share')
    tgt_pg25=raw('tgt_pg'); car_pg25=raw('car_pg'); rec_pg25=raw('rec_pg')
    catch = (rec_pg25/tgt_pg25) if (rec_pg25 and tgt_pg25) else POS_CATCH.get(pos,0.66)
    clay_t=pct(f.get('clay_targ_pct')); clay_c=pct(f.get('clay_car_pct'))
    rec={'name':f.get('name'),'pos':pos,'team25':f.get('team25'),'team':f.get('team'),
         'tgt_share_25raw':tgt_share25,'carry_share_25raw':car_share25,
         'tgt_pg_25raw':tgt_pg25,'car_pg_25raw':car_pg25}
    src=None; conf=None
    # ---- receiving role (WR/TE/RB) ----
    if pos in ('WR','TE','RB'):
        share = clay_t if clay_t is not None else tgt_share25
        used_clay = clay_t is not None
        if share is not None:
            f['tgt_share']=round(share,1)
            if tm_pa is not None:
                f['tgt_pg']=round(share/100.0*tm_pa,1)
                f['rec_pg']=round(share/100.0*tm_pa*catch,1)
            src = 'reproj_clay' if used_clay else 'reproj_carry'
    # ---- rushing role (RB/QB) ----
    if pos in ('RB','QB'):
        cshare = clay_c if clay_c is not None else car_share25
        used_clay_c = clay_c is not None
        if cshare is not None:
            f['carry_share']=round(cshare,1)
            if tm_car is not None:
                f['car_pg']=round(cshare/100.0*tm_car,1)
            if pos=='RB':
                src = ('reproj_clay' if used_clay_c else 'reproj_carry') if src is None else src
            else:  # QB: rushing only
                src = 'reproj_clay' if used_clay_c else 'reproj_carry'
    if src is None:
        src='stale_no_volume'; conf='low'; n_skip+=1
    else:
        conf='high' if 'clay' in src else 'med'
        if 'clay' in src: n_clay+=1
        else: n_carry+=1
    f['usage_src']=src; f['mover_conf']=conf
    rec['usage_src']=src; rec['mover_conf']=conf
    rec['tgt_share_2026']=f.get('tgt_share'); rec['tgt_pg_2026']=f.get('tgt_pg')
    rec['carry_share_2026']=f.get('carry_share'); rec['car_pg_2026']=f.get('car_pg')
    rep.append(rec)

# ---- write feature store back (json + csv in sync) ----
cols=[]
for f in players:
    for c in f:
        if c not in cols: cols.append(c)
core.safe_json_dump({'meta':{'n':len(players),'cols':cols,
    'note':'+ mover usage re-projection (reproject_movers.py): movers re-cast onto 2026 team role; raw under *_25raw; usage_src/mover_conf provenance'},
    'players':players}, core.P('features.json'))
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader()
    for f in players: w.writerow(f)
core.safe_json_dump({'note':'2026 mover usage re-projection audit. reproj_clay=Clay 2026 share x new-team volume; reproj_carry=2025 share carried onto new-team volume; raw under *_25raw.',
    'n_movers':len(rep),'n_reproj_clay':n_clay,'n_reproj_carry':n_carry,'n_stale_no_volume':n_skip,
    'movers':sorted(rep,key=lambda r:-((num(r.get('tgt_pg_2026')) or num(r.get('car_pg_2026')) or 0)))}, core.P('boom/movers_reprojection.json'))
print(f"movers re-projected: {len(rep)} | clay={n_clay} carry={n_carry} stale={n_skip} | feature cols={len(cols)}")
