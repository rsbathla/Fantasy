#!/usr/bin/env python3
"""backtest_composite_2025.py — POINT-IN-TIME 2025 backtest of RANKING-composite candidates.

Question: which built-but-unranked signals (graded coverage/EPA skill, opportunity, RZ equity,
QB pressure slate) EARN a vote in build_flag_ranks.py's composite, and at what weight — judged by
INCREMENTAL, MARKET-ORTHOGONAL lift over a 2025-preseason-ADP-only baseline?

LEAK CONTROLS (mirrors backtest_boom.py discipline + woptimize_rookie.py methodology):
  * Predictors: 2024-and-prior ONLY.
      - chart2yr.json 'y2024' per-season split (FantasyPoints charting, 2024 season)
      - NFL-master/FP/2024/Receiving/CoverageType/*.csv (2024-only per-scheme YPRR percentiles;
        the on-disk boom/coverage_route_spec.json is POOLED 2024+2025 so it is NOT used here)
      - nfl_pro_epa.json seasons['2024'] (per-season on disk; 2025 section untouched)
      - pipeline/player_games.parquet season==2024 rows (2024 volume shares)
      - sis_value/pass_rush_2024.csv (2024 team pass-rush quality) x 2025 schedule
        (../dfs_review/schedule_2025.json — schedules publish in spring, preseason-known)
  * Baseline: sis_value/fp_adp_2025.csv = 2025 preseason FantasyPros ADP (same file
    woptimize_rookie.py uses as its "real 2025 preseason baseline").
  * Outcomes (realized 2025, from boom/base2yr.json, built off the 2025 gamelog):
      A) SPIKE COUNT  = b25 booms (0 for ADP players with no 2025 sample — busts count against you)
      B) BOOM RATE    = b25/g25 with g25>=6 (repo currency; conditions on staying active — noted)
  * NOT CLEANLY TESTABLE point-in-time (excluded from weight claims, stated in the report):
      - scheme_fit / coverage_route_spec AS BUILT (pools 2025), coordinator sack_rate_adj's
        new-DC rider (no 2025 DC registry on disk), ffdataroma vacated targets (2026 offseason
        file only), the p95 ceiling term and 2026 smq term (2025-preseason projections not on disk).
  * The 2024-only "flag count" is a PROXY: the real builders consume pooled statmenu/fusion inputs
    that cannot be reconstructed as-of-2024; family thresholds are copied from the builders
    (build_flags_WR/RB/QB.py) applied to the y2024 season slice.

METRIC: Spearman rho of blend = (1-W)*adp_pctl + W*signal_pctl vs realized outcome, within position.
  "Beats market" bar = positive OUT-OF-SAMPLE delta rho: 200 random split-halves, fit W* on train,
  score rho(test,W*) - rho(test,W=0). Plus ADP-partialed Spearman with a permutation p-value, and
  a bootstrap of the optimal W (wide IQR = data does not pin the weight).
HOLDOUT HONESTY: one season. 2025 is fully out-of-sample w.r.t. the 2024 predictors, but there is
  no second season to validate the CHOSEN weights (no 2024-preseason ADP / 2023 charting on disk),
  so split-half OOS within 2025 is the only guard; weights are single-season estimates.
"""
import csv, json, os, random, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core
B = os.path.join(HERE, 'boom')
random.seed(17); np.random.seed(17)

SPIKE_MIN_G24 = 6      # min 2024 games for a y2024 charting line to count (validate_signal_stability convention)
W_GRID = [round(i / 20, 2) for i in range(21)]
N_SPLITS = 200         # split-half OOS repetitions
N_PERM = 2000          # permutation draws for partial-rho p-value
N_BOOT = 1000          # bootstrap draws for optimal-W stability

# ---------------------------------------------------------------- loaders
def load_adp():
    return {core.fn(r['name']): float(r['adp'])
            for r in csv.DictReader(open(os.path.join(HERE, 'sis_value', 'fp_adp_2025.csv'), encoding='utf-8'))}

def load_outcomes():
    b2 = json.load(open(os.path.join(B, 'base2yr.json'), encoding='utf-8'))
    outA = {k: (v.get('b25') or 0) for k, v in b2.items()}                       # spike count (missing -> handled as 0)
    outB = {k: v['b25'] / v['g25'] for k, v in b2.items()
            if (v.get('g25') or 0) >= 6}                                          # boom rate, active-sample conditioned
    return outA, outB

def load_positions():
    pos = {}
    feat = json.load(open(os.path.join(HERE, 'features.json'), encoding='utf-8'))['players']
    for p in feat:
        if p.get('pos'): pos.setdefault(core.fn(p['name']), p['pos'].upper())
    c2 = json.load(open(os.path.join(B, 'chart2yr.json'), encoding='utf-8'))
    for k, v in c2.items():
        if isinstance(v, dict) and v.get('pos'): pos.setdefault(k, v['pos'])
    return pos

def load_chart_y2024():
    c2 = json.load(open(os.path.join(B, 'chart2yr.json'), encoding='utf-8'))
    out = {}
    for k, v in c2.items():
        if not isinstance(v, dict): continue
        y = v.get('y2024')
        if y and (y.get('g') or 0) >= SPIKE_MIN_G24:
            out[k] = dict(y, pos=v.get('pos'))
    return out

def load_parquet_2024():
    """2024 volume shares via features.json pid->name map (validate_signal_stability convention)."""
    feat = {str(p['pid']): core.fn(p['name'])
            for p in json.load(open(os.path.join(HERE, 'features.json'), encoding='utf-8'))['players']
            if p.get('pid') is not None}
    g = pd.read_parquet(core.PP('player_games.parquet'))
    d = g[(g.season == 2024) & (g.week <= 17)].copy()
    d['team'] = d.team.map(core.norm_team)
    tt = d.groupby('team').agg(tgt=('targets', 'sum'), car=('carries', 'sum'))
    out = {}
    for pid, gr in d.groupby('pid'):
        k = feat.get(str(pid))
        if not k or gr.week.nunique() < SPIKE_MIN_G24: continue
        T = tt.loc[gr.team.mode().iloc[0]]
        gm = gr.week.nunique()
        out[k] = {'tgt_share': 100.0 * gr.targets.sum() / T.tgt if T.tgt else 0.0,
                  'carry_share': 100.0 * gr.carries.sum() / T.car if T.car else 0.0,
                  'rec_pg': gr.rec.sum() / gm, 'rush_ypg': gr.rush_yds.sum() / gm, 'g': gm}
    return out

def load_cov2024():
    """2024-ONLY per-scheme YPRR percentiles (WR/TE), single-season rebuild of build_coverage_spec.py.
    Route minimums halved vs the pooled-2yr builder (25->13 scheme, 100->50 overall) since one season."""
    SCHEMES = ['Cover 0', 'Cover 1', 'Cover 2', 'Cover 3', 'Cover 4', 'Cover 6', 'Man Cover 2']
    MIN_RTE, MIN_OVR, MIN_PEERS = 13, 50, 12
    def num(v):
        v = (v or '').strip().replace(',', '')
        if v in ('', '-'): return 0
        try: return float(v)
        except ValueError: return 0
    cells, agg = {}, {}
    for s in SCHEMES:
        p = os.path.join(HERE, 'NFL-master', 'FP', '2024', 'Receiving', 'CoverageType', s + '.csv')
        pool = {}
        for r in csv.DictReader(open(p, encoding='utf-8-sig')):
            pos = (r.get('POS') or '').strip().upper()
            if pos not in ('WR', 'TE'): continue
            k = core.fn(r['Name'])
            a = pool.setdefault(k, {'pos': pos, 'rte': 0, 'yds': 0})
            a['rte'] += num(r['RTE']); a['yds'] += num(r['YDS'])
            o = agg.setdefault(k, {'pos': pos, 'rte': 0, 'yds': 0})
            o['rte'] += num(r['RTE']); o['yds'] += num(r['YDS'])
        cells[s] = pool
    def pctl_map(pairs):  # [(key, yprr)] -> {key: pctl}
        vals = sorted(v for _, v in pairs); n = len(vals)
        return {k: 100.0 * (sum(1 for x in vals if x < v) + 0.5 * sum(1 for x in vals if x == v)) / n
                for k, v in pairs}
    out = {}
    for pos in ('WR', 'TE'):
        per_scheme = {}
        for s in SCHEMES:
            qual = [(k, a['yds'] / a['rte']) for k, a in cells[s].items()
                    if a['pos'] == pos and a['rte'] >= MIN_RTE]
            if len(qual) < MIN_PEERS: continue
            pm = pctl_map(qual)
            for k, _ in qual:
                per_scheme.setdefault(k, []).append((pm[k], cells[s][k]['rte']))
        ov_qual = [(k, a['yds'] / a['rte']) for k, a in agg.items() if a['pos'] == pos and a['rte'] >= MIN_OVR]
        ov = pctl_map(ov_qual)
        for k, _ in ov_qual:
            ws = per_scheme.get(k) or []
            wmean = (sum(p * r for p, r in ws) / sum(r for _, r in ws)) if ws else None
            out[k] = {'pos': pos, 'cov24': (ov[k] + wmean) / 2.0 if wmean is not None else ov[k]}
    return out

def load_nflpro_2024():
    d = json.load(open(os.path.join(HERE, 'nfl_pro_epa.json'), encoding='utf-8'))['seasons']['2024']
    rec = {core.fn(r['displayName']): r for r in d['receiving']['rows']}
    rush = {core.fn(r['displayName']): r for r in d['rushing']['rows']}
    qb = {core.fn(r['displayName']): r for r in d['passing']['rows']}
    return rec, rush, qb

def load_press_slate():
    """QB 2025-schedule pressure: 2024 team pass-rush Points Saved (SIS) averaged over 2025 opponents.
    Higher = TOUGHER slate. The 2026 sack_rate_adj new-DC rider is NOT reproducible for 2025."""
    NICK = {'49ers': 'SF', 'Bears': 'CHI', 'Bengals': 'CIN', 'Bills': 'BUF', 'Broncos': 'DEN', 'Browns': 'CLE',
            'Buccaneers': 'TB', 'Cardinals': 'ARI', 'Chargers': 'LAC', 'Chiefs': 'KC', 'Colts': 'IND',
            'Commanders': 'WAS', 'Cowboys': 'DAL', 'Dolphins': 'MIA', 'Eagles': 'PHI', 'Falcons': 'ATL',
            'Giants': 'NYG', 'Jaguars': 'JAX', 'Jets': 'NYJ', 'Lions': 'DET', 'Packers': 'GB',
            'Panthers': 'CAR', 'Patriots': 'NE', 'Raiders': 'LV', 'Rams': 'LAR', 'Ravens': 'BAL',
            'Saints': 'NO', 'Seahawks': 'SEA', 'Steelers': 'PIT', 'Texans': 'HOU', 'Titans': 'TEN',
            'Vikings': 'MIN'}
    team_ps = {}
    for r in csv.DictReader(open(os.path.join(HERE, 'sis_value', 'pass_rush_2024.csv'), encoding='utf-8')):
        ab = NICK.get(r['Team'])
        if ab: team_ps[ab] = team_ps.get(ab, 0.0) + float(r['Points Saved'] or 0)
    sched = json.load(open(os.path.join(os.path.dirname(HERE), 'dfs_review', 'schedule_2025.json'), encoding='utf-8'))
    feat = json.load(open(os.path.join(HERE, 'features.json'), encoding='utf-8'))['players']
    team25 = {core.fn(p['name']): core.norm_team(p.get('team25') or p.get('team') or '')
              for p in feat if p.get('pos') == 'QB'}
    slate = {}
    for k, tm in team25.items():
        opps = [core.norm_team(sched.get(str(w), {}).get(tm, '')) for w in range(1, 18)]
        vals = [team_ps[o] for o in opps if o in team_ps]
        if len(vals) >= 14: slate[k] = sum(vals) / len(vals)
    return slate

# ---------------------------------------------------------------- 2024-only signal builders
def build_signals():
    """key -> {pos, count24, graded24, cov24, epa24, opp24, rz24, press24} — ALL 2024-only."""
    y24 = load_chart_y2024(); vol = load_parquet_2024(); cov = load_cov2024()
    rec, rush, qb = load_nflpro_2024(); slate = load_press_slate()
    pos_map = load_positions()

    def pctl_of(d, keys, fn):
        vals = {k: fn(d[k]) for k in keys if fn(d[k]) is not None}
        sv = sorted(vals.values()); n = len(sv)
        return {k: 100.0 * (sum(1 for x in sv if x < v) + 0.5 * sum(1 for x in sv if x == v)) / n
                for k, v in vals.items()} if n else {}

    sig = {}
    def S(k, pos):
        return sig.setdefault(k, {'pos': pos})

    # --- WR/TE: proxy 2024 flag count (builder families/thresholds on the y2024 slice) ---
    for k, y in y24.items():
        pos = y.get('pos')
        if pos in ('WR', 'TE'):
            fam = 0
            fam += 1 if ((y.get('aDOT') or 0) >= 12.0 or (y.get('ay_share') or 0) >= 30 or (y.get('deep_pct') or 0) >= 20) else 0
            fam += 1 if ((y.get('yprr') or 0) >= 2.0 or (y.get('tprr') or 0) >= 0.23 or (y.get('fr_pct') or 0) >= 19 or (y.get('contested_pct') or 0) >= 12) else 0
            fam += 1 if ((y.get('yprr') or 0) >= 1.7) else 0
            fam += 1 if ((y.get('yac_rec') or 0) >= 5.0 or (y.get('yaco_rec') or 0) >= 1.5 or (y.get('mtf_rec') or 0) >= 0.14) else 0
            fam += 1 if ((vol.get(k, {}).get('tgt_share') or 0) >= 20) else 0
            fam += 1 if ((y.get('rz_tgt_rate') or 0) >= 18 or (y.get('ez_tgt') or 0) >= 5 or (y.get('i20_pg') or 0) >= 0.5) else 0
            S(k, pos)['count24'] = fam
        elif pos == 'RB':
            fam = 0
            fam += 1 if ((y.get('exp_run') or 0) >= 5.5 or (y.get('mtf_att') or 0) >= 0.17 or (y.get('yaco_att') or 0) >= 2.45) else 0
            fam += 1 if ((y.get('i5_pct') or 0) >= 39 or (y.get('td_rate') or 0) >= 3.5) else 0
            fam += 1 if ((vol.get(k, {}).get('carry_share') or 0) >= 45) else 0
            fam += 1 if ((vol.get(k, {}).get('rec_pg') or 0) >= 2.5) else 0
            S(k, 'RB')['count24'] = fam
        elif pos == 'QB':
            fam = 0
            fam += 1 if ((y.get('cpoe') or -9) >= 2.0) else 0
            fam += 1 if ((y.get('aDOT') or 0) >= 9.0 or (y.get('deep_pct') or 0) >= 13) else 0
            fam += 1 if ((y.get('scrm') or 0) >= 30 or (vol.get(k, {}).get('rush_ypg') or 0) >= 25) else 0
            S(k, 'QB')['count24'] = fam

    # --- graded skill (coverage YPRR pctl + NFL Pro EPA efficiency), within position ---
    wr_keys = [k for k, r in rec.items() if r.get('positionGroup') == 'WR']
    te_keys = [k for k, r in rec.items() if r.get('positionGroup') == 'TE']
    rb_rec_keys = [k for k, r in rec.items() if r.get('positionGroup') == 'RB']
    rb_keys = [k for k, r in rush.items() if r.get('positionGroup') == 'RB']
    qb_keys = list(qb.keys())
    ep_wr = pctl_of(rec, wr_keys, lambda r: r.get('epaRt'))
    ep_te = pctl_of(rec, te_keys, lambda r: r.get('epaRt'))
    ep_rbrec = pctl_of(rec, rb_rec_keys, lambda r: r.get('epaRt'))
    ry_rb = pctl_of(rush, rb_keys, lambda r: r.get('ryoeAtt'))
    ep_qb = pctl_of(qb, qb_keys, lambda r: r.get('epaDb'))
    cp_qb = pctl_of(qb, qb_keys, lambda r: r.get('cpoe'))
    for k, v in cov.items():
        S(k, v['pos'])['cov24'] = v['cov24']
    for src in (ep_wr, ep_te):
        for k, p in src.items():
            S(k, pos_map.get(k, 'WR'))['epa24'] = p
    for k in set(list(ry_rb) + list(ep_rbrec)):
        parts = [x for x in (ry_rb.get(k), ep_rbrec.get(k)) if x is not None]
        S(k, 'RB')['epa24'] = sum(parts) / len(parts)
    for k in qb_keys:
        parts = [x for x in (ep_qb.get(k), cp_qb.get(k)) if x is not None]
        if parts: S(k, 'QB')['epa24'] = sum(parts) / len(parts)
    for k, v in sig.items():
        parts = [x for x in (v.get('cov24'), v.get('epa24')) if x is not None]
        if parts: v['graded24'] = sum(parts) / len(parts)

    # --- opportunity / volume (2024 shares + earned-target rate) ---
    for k, y in y24.items():
        pos = y.get('pos')
        if pos in ('WR', 'TE'):
            t = vol.get(k, {}).get('tgt_share')
            parts = [x for x in (t, (y.get('tprr') or 0) * 400 if y.get('tprr') else None) if x is not None]
            # raw scales differ; percentile below fixes it — store raw pair for pctl-ing
            S(k, pos)['opp_tgt'] = t
            S(k, pos)['opp_tprr'] = y.get('tprr')
        elif pos == 'RB':
            S(k, 'RB')['opp_car'] = vol.get(k, {}).get('carry_share')
            S(k, 'RB')['opp_tgt'] = vol.get(k, {}).get('tgt_share')
    for pos, fields in (('WR', ('opp_tgt', 'opp_tprr')), ('TE', ('opp_tgt', 'opp_tprr')),
                        ('RB', ('opp_car', 'opp_tgt'))):
        keys = [k for k, v in sig.items() if v['pos'] == pos]
        pmaps = [pctl_of(sig, keys, lambda v, f=f: v.get(f)) for f in fields]
        for k in keys:
            parts = [pm[k] for pm in pmaps if k in pm]
            if parts: sig[k]['opp24'] = sum(parts) / len(parts)

    # --- RZ / TD equity (2024) ---
    for k, y in y24.items():
        pos = y.get('pos')
        if pos in ('WR', 'TE'):
            g = y.get('g') or 1
            S(k, pos)['rz_ez'] = (y.get('ez_tgt') or 0) / g
            S(k, pos)['rz_rate'] = y.get('rz_tgt_rate')
            S(k, pos)['rz_i20'] = y.get('i20_pg')
        elif pos == 'RB':
            S(k, 'RB')['rz_i5'] = y.get('i5_pct')
            S(k, 'RB')['rz_td'] = y.get('td_rate')
    for pos, fields in (('WR', ('rz_ez', 'rz_rate', 'rz_i20')), ('TE', ('rz_ez', 'rz_rate', 'rz_i20')),
                        ('RB', ('rz_i5', 'rz_td'))):
        keys = [k for k, v in sig.items() if v['pos'] == pos]
        pmaps = [pctl_of(sig, keys, lambda v, f=f: v.get(f)) for f in fields]
        for k in keys:
            parts = [pm[k] for pm in pmaps if k in pm]
            if parts: sig[k]['rz24'] = sum(parts) / len(parts)

    # --- QB pressure slate (sign-flipped: softer slate = higher score) ---
    qkeys = [k for k, v in sig.items() if v['pos'] == 'QB' and k in slate]
    pm = pctl_of({k: -slate[k] for k in qkeys}, qkeys, lambda v: v)
    for k in qkeys: sig[k]['press24'] = pm[k]
    return sig

# ---------------------------------------------------------------- stats machinery
def spearman(xs, ys):
    def rk(a):
        o = sorted(range(len(a)), key=lambda i: a[i]); r = [0.0] * len(a); i = 0
        while i < len(a):
            j = i
            while j < len(a) and a[o[j]] == a[o[i]]: j += 1
            for t in range(i, j): r[o[t]] = (i + j - 1) / 2.0
            i = j
        return r
    rx, ry = rk(xs), rk(ys); n = len(xs)
    mx = sum(rx) / n; my = sum(ry) / n
    nu = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    de = (sum((rx[i] - mx) ** 2 for i in range(n)) * sum((ry[i] - my) ** 2 for i in range(n))) ** 0.5
    return nu / de if de else 0.0

def cohort_pctl(vals):
    pres = [v for v in vals if v is not None]; n = len(pres)
    return [None if v is None else 100.0 * (sum(1 for x in pres if x < v) + 0.5 * sum(1 for x in pres if x == v)) / n
            for v in vals]

def blend_eval(adp_p, sig_p, out, idx=None):
    idx = idx if idx is not None else list(range(len(out)))
    def rho_at(W):
        return spearman([(1 - W) * adp_p[i] + W * sig_p[i] for i in idx], [out[i] for i in idx])
    curve = {W: rho_at(W) for W in W_GRID}
    bw = max(W_GRID, key=lambda W: curve[W])
    return curve, bw

def oos_split_half(adp_p, sig_p, out):
    n = len(out); deltas = []
    for _ in range(N_SPLITS):
        perm = list(range(n)); random.shuffle(perm)
        tr, te = perm[:n // 2], perm[n // 2:]
        if len(tr) < 8 or len(te) < 8: return None, None
        _, bw = blend_eval(adp_p, sig_p, out, tr)
        r_te = spearman([(1 - bw) * adp_p[i] + bw * sig_p[i] for i in te], [out[i] for i in te])
        r0 = spearman([adp_p[i] for i in te], [out[i] for i in te])
        deltas.append(r_te - r0)
    return sum(deltas) / len(deltas), sum(1 for d in deltas if d > 0) / len(deltas)

def partial_spearman(adp_p, sig_p, out):
    """rank-residualize sig and outcome on ADP, Pearson of residuals + permutation p (one-sided)."""
    def rank(a):
        o = sorted(range(len(a)), key=lambda i: a[i]); r = [0.0] * len(a)
        for i, ix in enumerate(o): r[ix] = i
        return np.array(r, float)
    ra, rs, ro = rank(adp_p), rank(sig_p), rank(out)
    def resid(y, x):
        x1 = np.vstack([x, np.ones_like(x)]).T
        beta, *_ = np.linalg.lstsq(x1, y, rcond=None)
        return y - x1 @ beta
    es, eo = resid(rs, ra), resid(ro, ra)
    if es.std() == 0 or eo.std() == 0: return 0.0, 1.0
    r = float(np.corrcoef(es, eo)[0, 1])
    cnt = 0
    es_c = es.copy()
    for _ in range(N_PERM):
        np.random.shuffle(es_c)
        if float(np.corrcoef(es_c, eo)[0, 1]) >= r: cnt += 1
    return r, cnt / N_PERM

def boot_w(adp_p, sig_p, out):
    n = len(out); arg = []
    for _ in range(N_BOOT):
        idx = [random.randrange(n) for _ in range(n)]
        _, bw = blend_eval(adp_p, sig_p, out, idx)
        arg.append(bw)
    arg.sort()
    return arg[len(arg) // 2], arg[int(0.25 * len(arg))], arg[int(0.75 * len(arg))]

# ---------------------------------------------------------------- test runner
def test_signal(name, pos, field, sig, adp, outA, outB, results):
    for out_name, outcome in (('spike_count', outA), ('boom_rate', outB)):
        keys = [k for k, v in sig.items() if v['pos'] == pos and v.get(field) is not None and k in adp]
        if out_name == 'boom_rate':
            keys = [k for k in keys if k in outcome]
        rows = [(k, -adp[k], sig[k][field], (outcome.get(k, 0) if out_name == 'spike_count' else outcome[k]))
                for k in keys]
        if len(rows) < 20:
            results.append({'signal': name, 'pos': pos, 'outcome': out_name, 'n': len(rows), 'verdict': 'n<20 untestable'})
            continue
        adp_p = cohort_pctl([r[1] for r in rows])
        sig_p = cohort_pctl([r[2] for r in rows])
        out = [r[3] for r in rows]
        curve, bw = blend_eval(adp_p, sig_p, out)
        oos_d, oos_f = oos_split_half(adp_p, sig_p, out)
        pr, pp = partial_spearman(adp_p, sig_p, out)
        wmed, wlo, whi = boot_w(adp_p, sig_p, out)
        res = {'signal': name, 'pos': pos, 'outcome': out_name, 'n': len(rows),
               'rho_adp_only': round(curve[0.0], 3), 'rho_sig_only': round(curve[1.0], 3),
               'best_W': bw, 'rho_best': round(curve[bw], 3),
               'delta_in_sample': round(curve[bw] - curve[0.0], 3),
               'oos_delta_rho': round(oos_d, 4) if oos_d is not None else None,
               'oos_frac_positive': round(oos_f, 3) if oos_f is not None else None,
               'partial_rho_given_adp': round(pr, 3), 'perm_p_one_sided': round(pp, 4),
               'bootW_median': wmed, 'bootW_IQR': [wlo, whi]}
        res['verdict'] = ('BEATS MARKET' if (oos_d or 0) > 0.01 and oos_f is not None and oos_f >= 0.60 and pr > 0
                          else 'marginal' if (oos_d or 0) > 0 and pr > 0 else 'no lift')
        results.append(res)

def headline_table(results):
    print(f"\n{'signal':<22}{'pos':<5}{'outcome':<13}{'n':>4} {'rho_adp':>8} {'rho_sig':>8} {'W*':>5} "
          f"{'d_in':>6} {'d_OOS':>7} {'%OOS+':>6} {'partial':>8} {'p':>7}  verdict")
    for r in results:
        if 'rho_adp_only' not in r:
            print(f"{r['signal']:<22}{r['pos']:<5}{r['outcome']:<13}{r['n']:>4}  -- {r['verdict']}")
            continue
        print(f"{r['signal']:<22}{r['pos']:<5}{r['outcome']:<13}{r['n']:>4} {r['rho_adp_only']:>8} {r['rho_sig_only']:>8} "
              f"{r['best_W']:>5} {r['delta_in_sample']:>6} {r['oos_delta_rho']:>7} {r['oos_frac_positive']:>6} "
              f"{r['partial_rho_given_adp']:>8} {r['perm_p_one_sided']:>7}  {r['verdict']}")

def combined_weights(sig, adp, outA, pos, fields):
    """Simplex grid over ADP + fields, split-half OOS at each grid point (mirrors woptimize)."""
    keys = [k for k, v in sig.items() if v['pos'] == pos and k in adp and all(v.get(f) is not None for f in fields)]
    if len(keys) < 30: return None
    rows = [(k, -adp[k], [sig[k][f] for f in fields], outA.get(k, 0)) for k in keys]
    adp_p = cohort_pctl([r[1] for r in rows])
    fps = [cohort_pctl([r[2][j] for r in rows]) for j in range(len(fields))]
    out = [r[3] for r in rows]
    n = len(out)
    grid = []
    steps = [round(i / 20, 2) for i in range(0, 9)]  # each signal weight 0..0.40
    def gen(k, left, acc):
        if k == len(fields):
            grid.append(tuple(acc)); return
        for s in steps:
            if s <= left + 1e-9: gen(k + 1, left - s, acc + [s])
    gen(0, 0.6, [])  # ADP keeps >= 0.40 total weight (anchored discipline)
    def rho_at(ws, idx):
        comb = [(1 - sum(ws)) * adp_p[i] + sum(w * fp[i] for w, fp in zip(ws, fps)) for i in idx]
        return spearman(comb, [out[i] for i in idx])
    full = list(range(n))
    best = max(grid, key=lambda ws: rho_at(ws, full))
    r0, rb = rho_at((0,) * len(fields), full), rho_at(best, full)
    oos = []
    for _ in range(N_SPLITS):
        perm = list(range(n)); random.shuffle(perm)
        tr, te = perm[:n // 2], perm[n // 2:]
        bw = max(grid, key=lambda ws: rho_at(ws, tr))
        oos.append(rho_at(bw, te) - rho_at((0,) * len(fields), te))
    return {'pos': pos, 'n': n, 'fields': list(fields), 'rho_adp_only': round(r0, 3),
            'best_weights': dict(zip(fields, best)), 'adp_weight_at_best': round(1 - sum(best), 2),
            'rho_best_in_sample': round(rb, 3), 'delta_in_sample': round(rb - r0, 3),
            'oos_delta_rho_mean': round(sum(oos) / len(oos), 4),
            'oos_frac_positive': round(sum(1 for d in oos if d > 0) / len(oos), 3)}

def main():
    adp = load_adp(); outA, outB = load_outcomes(); sig = build_signals()
    print(f"cohort raw: ADP={len(adp)} | signals={len(sig)} | outcomeB(g25>=6)={len(outB)}")
    results = []
    # (a) HEADLINE: graded skill vs flag count (same-cohort comparison enforced below)
    for pos in ('WR', 'TE', 'RB', 'QB'):
        both = {k: v for k, v in sig.items() if v['pos'] == pos and v.get('count24') is not None and v.get('graded24') is not None}
        sub = {k: dict(v) for k, v in both.items()}
        test_signal('count24(proxy)', pos, 'count24', sub, adp, outA, outB, results)
        test_signal('graded24(cov+epa)', pos, 'graded24', sub, adp, outA, outB, results)
        if pos in ('WR', 'TE'):
            test_signal('cov24_only', pos, 'cov24', sub, adp, outA, outB, results)
            test_signal('epa24_only', pos, 'epa24', sub, adp, outA, outB, results)
    # (b) QB pressure slate
    test_signal('press_slate24', 'QB', 'press24', sig, adp, outA, outB, results)
    # (c) opportunity
    for pos in ('WR', 'TE', 'RB'):
        test_signal('opportunity24', pos, 'opp24', sig, adp, outA, outB, results)
    # (d) RZ equity
    for pos in ('WR', 'TE', 'RB'):
        test_signal('rz24', pos, 'rz24', sig, adp, outA, outB, results)
    headline_table(results)
    # weight re-derivation on the signals that can earn a place
    print("\n--- combined weight grid (ADP anchored >= 0.60 total; spike-count outcome) ---")
    combos = []
    for pos, fields in (('WR', ('graded24', 'opp24', 'rz24')), ('TE', ('graded24', 'opp24', 'rz24')),
                        ('RB', ('graded24', 'opp24', 'rz24'))):
        c = combined_weights(sig, adp, outA, pos, fields)
        if c:
            combos.append(c)
            print(f"{pos}: n={c['n']} rho_adp={c['rho_adp_only']} -> best {c['best_weights']} "
                  f"(ADP {c['adp_weight_at_best']}) rho={c['rho_best_in_sample']} "
                  f"d_in={c['delta_in_sample']} d_OOS={c['oos_delta_rho_mean']} (%+ {c['oos_frac_positive']})")
    out = {'design': {'predictors': '2024-and-prior only', 'baseline': '2025 preseason FP ADP',
                      'outcomes': {'A': '2025 spike count (b25; 0 if no sample)', 'B': 'b25/g25, g25>=6'},
                      'oos': f'{N_SPLITS}x split-half, W* fit on train', 'seed': 17},
           'results': results, 'combined': combos}
    core.safe_json_dump(out, os.path.join(B, 'backtest_composite_2025.json'), indent=1)
    print("\nwrote boom/backtest_composite_2025.json")

if __name__ == '__main__':
    main()
