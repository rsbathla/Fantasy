#!/usr/bin/env python3
"""Shared mechanics for the player-by-player FLAG-BASED boom model, so every position
script stays consistent. Each build_flags_<pos>.py imports this, supplies the position's
flag library + per-week activation logic, and calls write().

Model in one sentence: a player's ceiling probability in a given week = his regularized
base ceiling rate, multiplied UP by each independent boom-enabling flag that lights up that
week (skill x matchup x environment) and DOWN by suppressors -- the more flags lit, the
higher the probability. No single flag is required.
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')

def load():
    return (json.load(open(f"{B}/statmenu.json")), json.load(open(f"{B}/gamelog.json")),
            json.load(open(f"{B}/schedule2026.json")), json.load(open(f"{B}/defense2026.json")),
            json.load(open(f"{B}/boomdef.json")))

def players(sm, pos):
    out = [k for k, v in sm.items() if v['pos'] == pos]
    out.sort(key=lambda k: (sm[k]['adp'] if sm[k].get('adp') else 9999))
    return out

def cap(x, lo, hi): return max(lo, min(hi, x))

def reg_base(v, posbase, K=4.0):
    """Base ceiling rate. Prefers the 2-season(2024-25)+2026-projection blended rate computed in
    boom_base2yr.py (v['base_blended']); falls back to 2025-only shrinkage, then None."""
    if v.get('base_blended') is not None:
        return float(v['base_blended'])
    ng = v.get('n_games', 0); bg = v.get('boom_games', 0)
    pb = posbase.get(v['pos'], 0.15)
    if ng and ng >= 1:
        return round((bg + pb * K) / (ng + K), 3)
    if v.get('rookie_boom_prior') is not None:  # validated college-ceiling prior (rookies w/ no NFL history)
        return float(v['rookie_boom_prior'])
    return None

# Matchup/environment multiplier strength. The end-to-end backtest (backtest_boom.py) found the
# per-week multipliers were OVER-SIZED: at full strength they LOWERED cross-player AUC
# (0.739 -> 0.724). The shrinkage sweep showed lambda=0.25 is Brier-optimal and lambda=0.5
# retains decision-useful within-player spread while removing the cross-player degradation.
# Shipping 0.5; set to 0.25 for the Brier-optimal point. (0 -> base only, 1 -> old behavior.)
SHRINK_LAMBDA = 0.5

def prob(base, mults):
    """base ceiling rate scaled by the product of lit-flag multipliers (>1 boost, <1 suppress),
    each shrunk toward 1.0 by SHRINK_LAMBDA per the backtest calibration."""
    p = base
    for m in mults: p *= (1.0 + SHRINK_LAMBDA * (m - 1.0))
    return round(cap(p, 0.01, 0.80), 3)

def label(p, base):
    """Bin a week's ceiling prob into a 4-level setup grade. Uses BOTH an absolute ceiling-prob
    trigger (so elite high-base players whose great weeks hit the cap still read SMASH) AND a
    matchup-relative lift vs the player's own base (so mid-base players in great spots read SMASH)."""
    base = base if base and base > 0 else 0.12
    r = p / base
    if p >= 0.45 or (p >= 0.22 and r >= 1.45): return 'SMASH'
    if p >= 0.33 or r >= 1.12: return 'GOOD'
    # TOUGH trigger recalibrated after SHRINK_LAMBDA compressed the p scale (kept TOUGH a
    # usable ~5%% 'avoid' tier instead of the 0.3%% it collapsed to under the old 0.20/0.72 bins):
    if p < 0.26 and r <= 0.85: return 'TOUGH'
    return 'NEU'

def write(pos, data):
    """verify-retry write of flags_<pos>.json (compact, byte-checked)."""
    path = f"{B}/flags_{pos}.json"
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    for _ in range(3):
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(payload); fh.flush()
            try: os.fsync(fh.fileno())
            except OSError: pass  # skip fsync on FUSE/network mounts
        with open(path, encoding='utf-8') as fh:
            back = fh.read()
        if len(back) == len(payload):
            print(f"wrote flags_{pos}.json: {len(data)} players, {round(len(payload)/1024)} KB (verified)")
            return True
    print(f"WARN: flags_{pos}.json write not verified"); return False

# position ceiling swing targets (soft vs tough), measured in defense_variance.py -- agents
# calibrate their multiplier sets so a fully-soft setup lands near base*SOFT/POS and a fully-
# tough setup near base*TOUGH/POS (keeps the flag model honest vs measured reality).
SWING = {'QB': (0.06, 0.19), 'RB': (0.14, 0.25), 'WR': (0.13, 0.29), 'TE': (0.08, 0.33), 'DST': (0.06, 0.30)}
