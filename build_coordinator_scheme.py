#!/usr/bin/env python3
"""Coordinator-scheme layer: project 2026 DEFENSIVE scheme (man-coverage rate, blitz/sack rate) for
teams with a NEW DC, instead of freezing them at 2025. OFFENSE is intentionally untouched -- team
pass-rate/pace come from Clay's 2026 projections (validated: Clay departs from 2025 most for
coordinator-change teams), so offense coordinator effects are already implicit.

Per team with dc_new: blend the 2025 team rate with the DC's prior-stop rate if known; else regress
the 2025 rate toward the league mean by LAMBDA (scheme uncertain under a new DC). Sourced registry
only (coordinator_changes_2026.json). Output: coordinator_scheme_2026.json -> funnel/man-zone layer."""
import core, csv, json, os, statistics as st
LAMBDA=0.5; BLEND=0.5
def num(x):
    try: return float(x)
    except: return None
cov=list(csv.DictReader(open(core.P('defense_coverage.csv'),encoding='utf-8')))
man={core.norm_team(r['team']):num(r.get('def_man_rate')) for r in cov}
sk ={core.norm_team(r['team']):num(r.get('def_sack_rate')) for r in cov}
man_mean=st.mean([v for v in man.values() if v is not None]); sk_mean=st.mean([v for v in sk.values() if v is not None])
reg=json.load(open(core.P('coordinator_changes_2026.json'),encoding='utf-8'))
def adj(v,prior,vmean,dc_new):
    if v is None: return v,'no-2025'
    if dc_new and prior is not None: return round(BLEND*v+(1-BLEND)*prior,1),'blend-prior'
    if dc_new: return round(vmean+(v-vmean)*(1-LAMBDA),1),'regress-mean'
    return v,'2025-actual'
out={}
for t in man:
    e=reg.get(t,{}) if t in reg else {}
    dc=bool(e.get('dc_new'))
    ma,mc=adj(man[t],e.get('dc_prior_man_rate'),man_mean,dc)
    sa,sc=adj(sk[t],e.get('dc_prior_sack_rate'),sk_mean,dc)
    out[t]={'man_rate_2025':man[t],'man_rate_adj':ma,'sack_rate_2025':sk[t],'sack_rate_adj':sa,
            'dc_new':dc,'oc_new':bool(e.get('oc_new')),'dc_name':e.get('dc_name'),'conf':mc,
            'verified':e.get('verified'),'source':e.get('source')}
core.safe_json_dump({'meta':{'lambda':LAMBDA,'man_league_mean':round(man_mean,1),'sack_league_mean':round(sk_mean,1),
    'method':'new-DC: blend w/ DC prior tendency if known else regress 2025 toward league mean; OFFENSE untouched (Clay).',
    'registry_teams':len([k for k in reg if not k.startswith('_')]),'NOTE':'registry needs the full SOURCED 2026 DC/OC list to be impactful'},
    'teams':out}, core.P('coordinator_scheme_2026.json'))
nd=sum(1 for t in out if out[t]['dc_new'])
print(f"coordinator_scheme_2026.json: {len(out)} teams | new-DC adjusted: {nd} | man mean={man_mean:.1f} sack mean={sk_mean:.1f}")
for t in out:
    if out[t]['dc_new']: print(f"   {t}: man {out[t]['man_rate_2025']}->{out[t]['man_rate_adj']} | sack {out[t]['sack_rate_2025']}->{out[t]['sack_rate_adj']} ({out[t]['conf']})")
