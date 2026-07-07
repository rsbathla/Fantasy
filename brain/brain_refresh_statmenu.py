#!/usr/bin/env python3
"""brain_refresh_statmenu.py — light weekly refresh of the FAST-ROTTING fields in
boom/statmenu.json, without re-running the heavy boom pipeline (which needs raw scrapes).

Stamps three things into each player entry (quant audit: "missing vital" items):
  adp / _refresh.adp_asof   — newest DkPreDraftRankings*.csv in ~/Downloads, with as-of date
  avail                     — availability flag (injury/suspension/holdout mention in the
                              brain's recent intel; source: brain_intel.json, same-day when
                              run after brain_export)
  sched                     — bye week + W15/W16/W17 opponents from game_sim.json (the
                              survival-chain weeks a best-ball drafter actually grades on)

Fail-loud: refuses to write if the DK join matches < 100 players or game_sim lacks weeks.
brain_pages.py renders these as new Model-read lines on the next pages run.
"""
import glob, json, os, re, sys, time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brain_common as bc

# NB: short terms need BOTH boundaries — a start-only \b(mcl|...) matched the first three
# letters of "McLaurin" and flagged every tweet about him as injury news (caught 2026-07-07)
INJ = re.compile(r'\b(acl|mcl|pup|ir|torn|achilles|hamstring|holdout|setback)\b|\b(injur|suspen|rehab|surger|fractur|arrest)|\bhold out\b|\bout for (the )?(season|year)\b|\bmiss(es|ing)? (the )?(season|weeks|time)\b|coinflip to be ready', re.I)

def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    n = n.replace('.', '').replace("'", '').replace('-', ' '); return ' '.join(n.split())

def newest(pattern):
    fs = glob.glob(os.path.expanduser(pattern))
    return max(fs, key=os.path.getmtime) if fs else None

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=None)
    a = ap.parse_args()
    repo = bc.repo_root(a.repo)
    smp = os.path.join(repo, "boom", "statmenu.json")
    sm = json.load(open(smp))

    # ---- 1. ADP from newest DK export --------------------------------------------------
    dk_path = newest('~/Downloads/DkPreDraftRankings*.csv')
    n_adp = 0
    if dk_path:
        import csv
        adp = {}
        with open(dk_path) as f:
            for r in csv.DictReader(f):
                if r.get('Name') and r.get('ADP'):
                    try: adp[fn(r['Name'])] = (float(r['ADP']), r.get('Team', ''), r.get('Position', ''))
                    except ValueError: pass
        # surname/team/pos fallback for nickname mismatches (Ken vs Kenneth Walker)
        bysig = {}
        for k, (v, tm, ps) in adp.items():
            bysig.setdefault((k.split()[-1], tm, ps), []).append(k)
        for v in sm.values():
            if not isinstance(v, dict) or not v.get('name'): continue
            k = fn(v['name'])
            hit = adp.get(k)
            if not hit:
                sig = (k.split()[-1] if k.split() else '', v.get('team', ''), v.get('pos', ''))
                cands = bysig.get(sig, [])
                if len(cands) == 1: hit = adp[cands[0]]
            if hit:
                v['adp'] = hit[0]; n_adp += 1
        asof = datetime.fromtimestamp(os.path.getmtime(dk_path)).strftime('%Y-%m-%d')
        if n_adp < 100:
            raise SystemExit(f"FATAL: only {n_adp} ADP matches from {os.path.basename(dk_path)} — refusing to write statmenu")
    else:
        asof = None
        print("  no DkPreDraftRankings*.csv in ~/Downloads — ADP left as-is")

    # ---- 2. availability from the brain's own intel ------------------------------------
    n_av = 0
    bip = os.path.join(repo, "brain_intel.json")
    if os.path.exists(bip):
        intel = json.load(open(bip)).get("players", {})
        since = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        by_key = {fn(k): e for k, e in intel.items()}
        for v in sm.values():
            if not isinstance(v, dict) or not v.get('name'): continue
            e = by_key.get(fn(v['name']))
            v.pop('avail', None)
            if not e: continue
            hits = [t for t in e.get('tw', []) if t.get('d', '') >= since and INJ.search(t.get('t', ''))]
            hits += [c for c in e.get('claims', []) if c.get('d', '') >= since and INJ.search(c.get('t', ''))]
            if hits:
                latest = max(hits, key=lambda h: h.get('d', ''))
                m = INJ.search(latest.get('t', ''))
                v['avail'] = {"d": latest.get('d', ''), "term": (m.group(0) if m else '').lower(),
                              "n": len(hits)}
                n_av += 1

    # ---- 3. bye + W15/16/17 opponents from game_sim ------------------------------------
    gsp = os.path.join(repo, "game_sim.json")
    n_sched = 0
    if os.path.exists(gsp):
        g = json.load(open(gsp)).get("weeks", {})
        if not all(str(w) in g for w in (15, 16, 17)):
            raise SystemExit("FATAL: game_sim.json missing W15-17 — refusing to stamp schedule")
        allteams, opp = set(), {}
        for w, blk in g.items():
            for gm in blk.get("games", []):
                t1, t2 = gm["teams"]; allteams.update((t1, t2))
                opp.setdefault(t1, {})[int(w)] = t2; opp.setdefault(t2, {})[int(w)] = t1
        bye = {}
        for t in allteams:
            missing = [w for w in range(1, 15) if w not in opp.get(t, {})]
            bye[t] = missing[0] if missing else None
        for v in sm.values():
            if not isinstance(v, dict) or not v.get('name'): continue
            t = v.get('team')
            if t in allteams:
                v['sched'] = {"bye": bye.get(t),
                              "w15": opp[t].get(15), "w16": opp[t].get(16), "w17": opp[t].get(17)}
                n_sched += 1

    sm['_refresh'] = {"adp_asof": asof, "adp_source": os.path.basename(dk_path) if dk_path else None,
                      "stamped": datetime.now().strftime('%Y-%m-%d %H:%M')}
    json.dump(sm, open(smp, 'w'), ensure_ascii=False)
    bc.log(f"statmenu refresh: {n_adp} ADP (as of {asof}) · {n_av} availability flags · {n_sched} schedules")
    print(json.dumps({"adp": n_adp, "avail": n_av, "sched": n_sched, "asof": asof}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
