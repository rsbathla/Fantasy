#!/usr/bin/env python3
"""
switch_test.py — THE SWITCH AUDIT.

Runs every candidate signal ("switch") in the model through one honest gate and
classifies it:

  ADD  -> it predicts realized booms BEYOND the base rate (residual-vs-base corr is
          meaningfully non-zero, same sign as intuition). Eligible to move a boom
          probability (as a shrunk multiplier / base adjuster), per position.
  VIEW -> it does NOT add beyond the base (residual ~ 0). The base already encodes it.
          Keep for display/context only; wiring it as a multiplier would be overfitting.

Method (per position): for each signal s and player p with >=4 active 2025 games,
  resid_p = realized_2025_boom_rate(p) - modeled_base(p)
  score   = corr(s_p, resid_p)            # does s explain what the base misses?
We also report raw corr(s, boom_rate) so you can see volume/scoring collinearity.
This is the IN-SAMPLE screen (2025->2025): an UPPER BOUND on real signal, so anything
that fails here (resid ~ 0) is conclusively redundant; anything that passes is a
candidate for the stricter 2024->2025 out-of-sample confirmation.

Thresholds (|residual corr|):  >=0.15 ADD   0.10-0.15 WEAK   <0.10 VIEW
"""
import json, os, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')
sm = json.load(open(f"{B}/statmenu.json"))
gl = json.load(open(f"{B}/gamelog.json"))
from boomutil import fn

# realized 2025 boom rate per player (>=4 games)
boom = {fn(k): (sum(g['boom'] for g in v)/len(v)) for k, v in gl.items() if len(v) >= 4}

def base_of(v):
    for key in ('base_blended', 'base_hist2', 'base_proj'):
        if v.get(key) is not None: return float(v[key])
    return None

def dig(v, path):
    cur = v
    for part in path.split('.'):
        if not isinstance(cur, dict): return None
        cur = cur.get(part)
    return cur if isinstance(cur, (int, float)) and not isinstance(cur, bool) else None

def corr(a, b):
    if len(a) < 12: return None
    ma, mb = st.mean(a), st.mean(b)
    cov = sum((x-ma)*(y-mb) for x, y in zip(a, b))
    sa = sum((x-ma)**2 for x in a)**.5; sb = sum((y-mb)**2 for y in b)**.5
    return cov/(sa*sb) if sa*sb else 0.0

# candidate switches per position: (label, statmenu path)
COMMON = [
    ("fus.ceiling_pctl","fus.ceiling_pctl"), ("fus.spike_pctl","fus.spike_pctl"),
    ("fus.boom_pctl","fus.boom_pctl"), ("fus.explosive_pctl","fus.explosive_pctl"),
    ("fus.matchup_pctl","fus.matchup_pctl"), ("fus.oline_pctl","fus.oline_pctl"),
    ("team_env.env_idx","team_env.env_idx"), ("team_env.pace_pctl","team_env.pace_pctl"),
    ("team_env.off_q","team_env.off_q"), ("usage.dk_pg","usage.dk_pg"),
]
REC = COMMON + [
    ("adv2.aDOT","adv2.aDOT"), ("adv2.ay_share","adv2.ay_share"), ("adv2.tgt_share","adv2.tgt_share"),
    ("adv2.td_pg","adv2.td_pg"), ("adv2.ypt","adv2.ypt"),
    ("chart2.yprr(25)","chart2.y2025.yprr"), ("chart2.tprr(25)","chart2.y2025.tprr"),
    ("chart2.yac(25)","chart2.y2025.yac_rec"), ("chart2.yaco(25)","chart2.y2025.yaco_rec"),
    ("chart2.mtf(25)","chart2.y2025.mtf_rec"),
    ("rz.rz_tgt_share","rz.rz_tgt_share"), ("rz.ez_tgt_share","rz.ez_tgt_share"), ("rz.ez_td_pg","rz.ez_td_pg"),
    ("fus.separation_pctl","fus.separation_pctl"), ("fus.yac_pctl","fus.yac_pctl"),
    ("fus.coverage_proof_pctl","fus.coverage_proof_pctl"), ("fus.route_eff_pctl","fus.route_eff_pctl"),
    ("cspec.ratio","cspec.ratio"), ("cspec.pctl","cspec.pctl"),
    ("opp.route_pct","opp.route_pct"), ("sep.sep_pctl","sep.sep_pctl"), ("sep.man_sep_pctl","sep.man_sep_pctl"),
]
RB = COMMON + [
    ("usage.carry_share","usage.carry_share"), ("usage.tgt_share","usage.tgt_share"), ("usage.ypc","usage.ypc"),
    ("adv2.td_pg","adv2.td_pg"), ("chart2.mtf_att(25)","chart2.y2025.mtf_att"),
    ("chart2.yaco_att(25)","chart2.y2025.yaco_att"), ("chart2.success(25)","chart2.y2025.success"),
    ("chart2.exp_run(25)","chart2.y2025.exp_run"), ("chart2.i5_pct(25)","chart2.y2025.i5_pct"),
    ("fus.run_eff_pctl","fus.run_eff_pctl"), ("fus.rush_eff_pctl","fus.rush_eff_pctl"),
    ("fus.yac_pctl","fus.yac_pctl"), ("opp.route_pct","opp.route_pct"),
]
QB = COMMON + [
    ("adv2.ypa","adv2.ypa"), ("adv2.ptd_pg","adv2.ptd_pg"), ("adv2.rush_pg","adv2.rush_pg"),
    ("adv2.rushyd_pg","adv2.rushyd_pg"), ("adv2.rushtd_g","adv2.rushtd_g"),
    ("chart2.deep_pct(25)","chart2.y2025.deep_pct"), ("chart2.cpoe(25)","chart2.y2025.cpoe"),
    ("chart2.press_pct(25)","chart2.y2025.press_pct"), ("chart2.ttt(25)","chart2.y2025.ttt"),
    ("chart2.scrm(25)","chart2.y2025.scrm"), ("cspec.ratio","cspec.ratio"), ("fus.protection_pctl","fus.protection_pctl"),
]
SIG = {'WR': REC, 'TE': REC, 'RB': RB, 'QB': QB}

def classify(r, n):
    if r is None: return "n/a "
    if n < 25: return "LOW-N"          # sample too small to trust (e.g. TE pool) -> don't act
    a = abs(r)
    return "ADD " if a >= 0.15 else ("WEAK" if a >= 0.10 else "VIEW")

results = {}
for pos in ('QB', 'RB', 'WR', 'TE'):
    rows = []
    pool = [(k, v) for k, v in sm.items() if v.get('pos') == pos and fn(k) in boom and base_of(v) is not None]
    for label, path in SIG[pos]:
        xs, raw, res = [], [], []
        for k, v in pool:
            s = dig(v, path)
            if s is None: continue
            br = boom[fn(k)]; bs = base_of(v)
            xs.append(s); raw.append(br); res.append(br - bs)
        rc = corr(xs, raw); rr = corr(xs, res)
        if rr is not None:
            rows.append((label, len(xs), rc, rr, classify(rr, len(xs))))
    rows.sort(key=lambda r: -(abs(r[3]) if r[3] is not None else -1))
    results[pos] = rows

# ---- report ----
print("="*78)
print("SWITCH AUDIT  —  ADD (predicts booms beyond base) vs VIEW (context only)")
print("  screen: in-sample residual-vs-base corr (upper bound). |r|>=.15 ADD, .10-.15 WEAK, <.10 VIEW")
print("="*78)
summ = {'ADD': [], 'WEAK': [], 'VIEW': []}
for pos in ('QB', 'RB', 'WR', 'TE'):
    print(f"\n### {pos}  (signal | n | raw corr | residual-vs-base | verdict)")
    for label, n, rc, rr, verdict in results[pos]:
        print(f"  {label:26} n={n:3}  raw={rc:+.2f}  resid={rr:+.2f}  -> {verdict}")
        if verdict.strip() in summ: summ[verdict.strip()].append(f"{pos}:{label}")
print("\n" + "="*78)
print(f"SUMMARY: {len(summ['ADD'])} ADD  |  {len(summ['WEAK'])} WEAK  |  {len(summ['VIEW'])} VIEW")
print("="*78)
print("\nADD (eligible as a shrunk multiplier / base-adjuster, pending 2024->2025 OOS confirm):")
for s in summ['ADD']: print("  +", s)
audit = {pos: [{'signal': l, 'n': n, 'raw': round(rc,3) if rc is not None else None,
                'resid': round(rr,3) if rr is not None else None, 'verdict': v.strip()}
               for l, n, rc, rr, v in results[pos]] for pos in results}
json.dump(audit, open(f"{B}/switch_audit.json", 'w'), indent=1)
print("\nwrote boom/switch_audit.json")
