#!/usr/bin/env python3
"""[LEGACY WRITER — NOT CANONICAL] Reweight 2025 SIS defensive Points Saved onto 2026 rosters.

⚠️  normalize_defense_2026.py is the CANONICAL defense.json writer (snap-weighted RATE + rookie-aware).
    This legacy script sums Points Saved and FLOORS rookies to zero — running it overwrites defense.json
    with rookie-blind grades. It is kept only as the source of the shared MOVES map (normalize execs its
    head to import MOVES). Do NOT run it to regenerate defense.json; run normalize_defense_2026.py.
    A runtime guard below blocks an accidental full run unless BB_ALLOW_LEGACY_DEFENSE=1 is set.

Reweight 2025 SIS defensive Points Saved onto 2026 rosters (transparent accounting reweight,
NOT a refit). For each unit we start from the 2025 per-player (name, 2025 team, Points Saved) and
reassign each CONFIRMED mover's FULL 2025 PS to their 2026 team. RETIRED/UFA-unsigned -> subtract
only (production leaves the league). '2 teams' players -> their combined 2025 PS goes to their
confirmed 2026 team. Rookies / incoming players with no 2025 SIS data add NOTHING (replacement-level
floor; documented). Recompute each team's unit strength = sum of PS on its 2026 roster, then 32-team
percentiles per unit. defense.json keeps the 2025 strengths/pctls AND adds 2026-adjusted ones, updates
top contributors to the 2026 roster, and records a moves_2026 list per team. Then re-maps the
2026-adjusted opponent percentiles onto offensive players (same W15 mapping as ingest_defense.py).
"""
import core, csv, os, collections, bisect
fn=core.fn; nt=core.norm_team

NICK={'cardinals':'ARI','falcons':'ATL','ravens':'BAL','bills':'BUF','panthers':'CAR','bears':'CHI',
 'bengals':'CIN','browns':'CLE','cowboys':'DAL','broncos':'DEN','lions':'DET','packers':'GB',
 'texans':'HOU','colts':'IND','jaguars':'JAX','chiefs':'KC','chargers':'LAC','rams':'LAR','raiders':'LV',
 'dolphins':'MIA','vikings':'MIN','patriots':'NE','saints':'NO','giants':'NYG','jets':'NYJ','eagles':'PHI',
 'steelers':'PIT','seahawks':'SEA','49ers':'SF','niners':'SF','buccaneers':'TB','titans':'TEN',
 'commanders':'WAS','football team':'WAS'}
def nick(t): return NICK.get(str(t).strip().lower())
def num(x):
    try: return float(str(x).replace('%','').replace('"',''))
    except: return None

# ----------------------------------------------------------------------------------------------------
# MOVERS MAP: normalized-name -> {'to': team-code | 'RETIRED' | 'UFA', 'src': url, 'note': optional, 'conf': bool}
# Default assumption: a player STAYS unless listed here. '2 teams' players get their combined PS sent to 'to'.
# conf=False marks LOW-CONFIDENCE / assumed moves (sources disagreed); flagged in report.
# ----------------------------------------------------------------------------------------------------
MOVES={
 # --- SEED (confirmed) ---
 'myles garrett':{'to':'LAR','src':'https://www.espn.com/nfl/story/_/id/48939456/sources-browns-rams-finalizing-myles-garrett-blockbuster-trade'},
 'jared verse':{'to':'CLE','src':'https://www.nfl.com/news/nfl-network-browns-trading-myles-garrett-to-rams-jared-verse'},
 'trent mcduffie':{'to':'LAR','src':'https://www.aol.com/articles/rams-land-chiefs-trent-mcduffie-170732678.html'},
 'jaylen watson':{'to':'LAR','src':'https://www.therams.com/news/rams-agree-to-terms-with-cb-jaylen-watson-on-three-year-deal-free-agency-2026'},
 'trey hendrickson':{'to':'BAL','src':'https://www.nfl.com/news/trey-hendrickson-ravens-sign-de-four-year-112-million-contract-maxx-crosby-trade'},
 'calais campbell':{'to':'BAL','src':'https://www.baltimoreravens.com/news/calais-campbell-ravens-signing-veteran-free-agent-return-reunion-bringing-back'},
 'bradley chubb':{'to':'BUF','src':'https://www.nfl.com/news/bills-signing-ex-dolphins-pass-rusher-bradley-chubb'},
 'michael danna':{'to':'BUF','src':'https://www.buffalobills.com/news/bills-sign-olb-mike-danna-to-one-year-contract'},
 'mike danna':{'to':'BUF','src':'https://www.buffalobills.com/news/bills-sign-olb-mike-danna-to-one-year-contract'},
 'dexter lawrence':{'to':'CIN','src':'https://www.nfl.com/news/nfl-network-giants-trading-dt-dexter-lawrence-to-bengals-in-exchange-for-2026-no-10-overall-pick'},
 'demario davis':{'to':'NYJ','src':'https://www.newyorkjets.com/news/jets-sign-linebacker-demario-davis-free-agency-03-12-2026'},
 'nahshon wright':{'to':'NYJ','src':'https://www.newyorkjets.com/news/jets-sign-db-nahshon-wright-free-agency-03-12-2026'},
 'joseph ossai':{'to':'NYJ','src':'https://nfltraderumors.co/jets-signing-de-joseph-ossai-to-three-year-36m-deal/'},
 'kingsley enagbare':{'to':'NYJ','src':'https://www.acmepackingcompany.com/packers-kingsley-enagbare-signs-big-deal-with-new-york-jets'},
 'david onyemata':{'to':'NYJ','src':'https://www.yardbarker.com/nfl/articles/jets_contract_details_davis_onyemata_enagbare_wright_belton'},
 # cameron jordan re-signed NO -> no net move (stays NO); excluded.
 # --- PART B confirmed ---
 'jamel dean':{'to':'PIT','src':'https://www.si.com/nfl/steelers/onsi/news/pittsburgh-steelers-sign-buccaneers-jamel-dean'},
 'devin bush':{'to':'CHI','src':'https://chicago.suntimes.com/bears/2026/03/09/bears-to-sign-playmaking-veteran-devin-bush-jr'},
 'dee alford':{'to':'BUF','src':'https://sports.yahoo.com/articles/buffalo-bills-agree-terms-atlanta-035900209.html'},
 'alohi gilman':{'to':'KC','src':'https://sports.yahoo.com/articles/kansas-city-chiefs-sign-safety-164553767.html','note':'2 teams (LAC/BAL) 2025 -> KC 2026'},
 'tyson campbell':{'to':'CLE','src':'https://www.nfl.com/news/jaguars-trade-cb-tyson-campbell','note':'2 teams (mid-2025 JAX->CLE) -> CLE 2026'},
 'tremaine edmunds':{'to':'NYG','src':'https://chicago.suntimes.com/bears/2026/03/09/former-bears-linebacker-tremaine-edmunds-gets-3-year-36-million-deal-from-giants-report'},
 'reed blankenship':{'to':'HOU','src':'https://www.inquirer.com/eagles/reed-blankenship-houston-texans-2026-nfl-free-agency-20260309.html'},
 'dane belton':{'to':'NYJ','src':'https://www.newyorkjets.com/news/jets-sign-s-dane-belton-free-agency-03-12-2026'},
 # --- RETIRED / UNSIGNED / RELEASED (subtract only; production leaves the 2026 team) ---
 'joey bosa':{'to':'UFA','src':'https://www.si.com/nfl/bills/onsi/free-agency-why-buffalo-bills-haven-t-re-signed-de-joey-bosa-yet'},
 'jadeveon clowney':{'to':'UFA','src':'https://www.profootballrumors.com/2026/05/jadeveon-clowney-drawing-interest'},
 'bobby wagner':{'to':'UFA','src':'https://heavy.com/sports/nfl/washington-commanders/bobby-wagner-situation-turn-after-nfl-draft/'},
 # Terrion Arnold RELEASED by DET (legal case); off the 2026 roster. Web-verified Jul 2026 (CBS/FOX/SI/ESPN).
 # 2025 coverage PS 6.93 no longer credited to DET; replacement CB has no 2025 SIS data (replacement floor).
 'terrion arnold':{'to':'UFA','src':'https://www.foxsports.com/stories/nfl/lions-forced-cornerback-free-agent-market-after-releasing-terrion-arnold','note':'released by DET mid-2026 (legal case) -> off DET roster'},
 # --- PART C other major movers ---
 'jaelan phillips':{'to':'CAR','src':'https://www.nfl.com/news/top-101-nfl-free-agents-of-2026','note':'2 teams 2025 -> CAR 2026'},
 'devin lloyd':{'to':'CAR','src':'https://www.cbssports.com/nfl/news/2026-nfl-free-agency-panthers-jets-defense/'},
 'minkah fitzpatrick':{'to':'NYJ','src':'https://www.espn.com/nfl/story/_/id/48915793/2026-nfl-offseason-trade-tracker'},
 'jonathan greenard':{'to':'PHI','src':'https://www.foxsports.com/stories/nfl/2026-nfl-draft-trades-tracker-grades'},
 'jermaine johnson':{'to':'TEN','src':'https://www.nfl.com/news/2026-nfl-free-agency-tracker'},
 'tvondre sweat':{'to':'NYJ','src':'https://www.nfl.com/news/2026-nfl-free-agency-tracker'},
 'ljarius sneed':{'to':'LAR','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-best-unsigned-free-agents-2026/'},
 'greg newsome':{'to':'JAX','src':'https://www.aol.com/articles/jaguars-browns-swap-cornerbacks-draft-162449940.html','note':'2 teams 2025 -> JAX 2026'},
 'jalen thompson':{'to':'DAL','src':'https://www.nfl.com/news/2026-nfl-free-agency-tracker'},
 'pj locke':{'to':'DAL','src':'https://www.nfl.com/news/2026-nfl-free-agency-tracker'},
 'tim settle':{'to':'WAS','src':'https://www.nfl.com/news/2026-nfl-free-agency-tracker'},
 'dee winters':{'to':'WAS','src':'https://www.pff.com/news/2026-nfl-offseason-tracker-signings-trades-and-cuts-for-all-32-teams'},
 # --- LOW CONFIDENCE (sources disagreed); applied but flagged ---
 'kevin byard':{'to':'NE','src':'https://sports.yahoo.com/articles/contract-details-patriots-free-agency-140000073.html','conf':False,'note':'sources disagreed on destination'},
 'dremont jones':{'to':'NE','src':'https://sports.yahoo.com/articles/contract-details-patriots-free-agency-140000073.html','conf':False,'note':'2 teams 2025; destination disputed'},
 'klavon chaisson':{'to':'WAS','src':'https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/commanders-agree-to-terms-with-klavon-chaisson','note':'confirmed WAS (turned down Saints)'},
 # --- COMPREHENSIVE LONG-TAIL (added 2026-06; ESPN/CBS/NFL.com team trackers) ---
 # NFC/AFC depth + rotational signings & trades confirmed across multiple trackers.
 'andrew wingard':{'to':'ARI','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'S JAX->ARI'},
 'cameron thomas':{'to':'ATL','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'EDGE depth ->ATL'},
 'jaylinn hawkins':{'to':'BAL','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'S ->BAL'},
 'chidobe awuzie':{'to':'BAL','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'CB re-routed/retained BAL (was on BAL roster)','conf':False},
 'cj gardner johnson':{'to':'BUF','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'2 teams 2025 -> BUF'},
 'geno stone':{'to':'BUF','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'S CIN->BUF'},
 'taron johnson':{'to':'LV','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'CB traded BUF->LV'},
 'christian rozeboom':{'to':'TB','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'LB ->TB'},
 'alex anzalone':{'to':'TB','src':'https://www.espn.com/nfl/story/_/id/48083059/nfl-free-agency-2026-all-signings-afc-nfc-teams','note':'LB DET->TB'},
 'al quadin muhammad':{'to':'TB','src':'https://heavy.com/sports/nfl/free-agency-tracker-2026-news-signings-rumors/','note':'EDGE depth ->TB'},
 'coby bryant':{'to':'CHI','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'S SEA->CHI'},
 'boye mafe':{'to':'CIN','src':'https://www.espn.com/nfl/story/_/id/48083059/nfl-free-agency-2026-all-signings-afc-nfc-teams','note':'EDGE SEA->CIN'},
 'bryan cook':{'to':'CIN','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'S KC->CIN'},
 'jonathan allen':{'to':'CIN','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'DT MIN->CIN'},
 'quincy williams':{'to':'CLE','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'LB NYJ->CLE'},
 'cobie durant':{'to':'DAL','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'CB LAR->DAL'},
 'rashan gary':{'to':'DAL','src':'https://www.cbssports.com/nfl/news/rashan-gary-trade-cowboys-packers/','note':'EDGE traded GB->DAL'},
 'rock ya sin':{'to':'DET','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'CB ->DET'},
 'amik robertson':{'to':'WAS','src':'https://www.espn.com/nfl/story/_/id/48083059/nfl-free-agency-2026-all-signings-afc-nfc-teams','note':'CB ->WAS'},
 'javon hargrave':{'to':'GB','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'DT ->GB'},
 'benjamin st juste':{'to':'GB','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'CB LAC->GB'},
 'zaire franklin':{'to':'GB','src':'https://www.cbssports.com/nfl/news/nfl-trade-tracker-grades/','note':'LB traded IND->GB'},
 'colby wooden':{'to':'IND','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'DT traded GB->IND'},
 'logan hall':{'to':'HOU','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'DL TB->HOU'},
 'arden key':{'to':'IND','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'EDGE TEN->IND'},
 'kwity paye':{'to':'LV','src':'https://www.espn.com/nfl/story/_/id/48083059/nfl-free-agency-2026-all-signings-afc-nfc-teams','note':'EDGE IND->LV'},
 'quay walker':{'to':'LV','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'LB GB->LV'},
 'nakobe dean':{'to':'LV','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'LB PHI->LV'},
 'james pierre':{'to':'MIN','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'CB PIT->MIN'},
 'kaden elliss':{'to':'NO','src':'https://www.cbssports.com/nfl/news/nfl-free-agency-tracker-2026-full-list-signings-trades-moves/','note':'LB ATL->NO'},
 'jonathan jones':{'to':'PHI','src':'https://www.foxsports.com/stories/nfl/2026-nfl-free-agency-trades-tracker-signings-updates-best-players-available','note':'CB WAS->PHI'},
 'dante fowler':{'to':'SEA','src':'https://heavy.com/sports/nfl/free-agency-tracker-2026-news-signings-rumors/','note':'EDGE DAL->SEA'},
 'odafe oweh':{'to':'WAS','src':'https://www.nfl.com/news/odafe-oweh-commanders-sign-pass-rusher-four-year-100-million-contract','note':'EDGE -> WAS 4yr/$100M (was mis-registered NYG; corrected 2026-07-05, web-verified)'},
 'nick cross':{'to':'WAS','src':'https://www.nfl.com/videos/nick-cross-signs-2-year-14m-deal-with-commanders-free-agency-frenzy','note':'S IND->WAS 2yr/$14M (was mis-registered NYG; corrected 2026-07-05, web-verified)'},
 'cordale flott':{'to':'TEN','src':'https://www.tennesseetitans.com/news/titans-sign-cornerback-cor-dale-flott','note':'CB NYG->TEN'},
 'john franklin myers':{'to':'TEN','src':'https://www.aol.com/articles/titans-sign-john-franklin-myers-192951802.html','note':'DE DEN->TEN'},
 # --- 2026-07-05 funnel audit: web-verified moves the engine was stale-crediting or missing entirely ---
 'riq woolen':{'to':'PHI','src':'https://www.nfl.com/news/eagles-signing-former-seahawks-cb-riq-woolen-to-one-year-deal-worth-max-value-of-15-million','note':'CB SEA->PHI 1yr/$15M (engine was stale-crediting SEA)'},
 'alontae taylor':{'to':'TEN','src':'https://www.tennesseetitans.com/news/titans-sign-cornerback-alontae-taylor','note':'CB NO->TEN 3yr/$58M (engine was stale-crediting NO)'},
 'osa odighizuwa':{'to':'SF','src':'https://www.espn.com/nfl/story/_/id/48177910/sources-cowboys-trade-dt-odighizuwa-49ers-3rd-round-pick','note':'DT traded DAL->SF for a 3rd (engine was stale-crediting DAL)'},
 'quinnen williams':{'to':'DAL','src':'https://www.nfl.com/news/jets-trade-dt-quinnen-williams-to-cowboys-for-first-round-pick','note':'DT traded NYJ->DAL Nov-2025 deadline (was missing from engine)'},
 'sauce gardner':{'to':'IND','src':'https://www.colts.com/news/colts-acquire-cb-sauce-gardner-from-new-york-jets-in-exchange-for-2026-2027-first-round-picks-and-wr-adonai-mitchell','note':'CB traded NYJ->IND Nov-2025 deadline (was missing from engine)'},
 'dre greenlaw':{'to':'SF','src':'https://www.nfl.com/news/niners-bringing-back-lb-dre-greenlaw-on-one-year-7-5-million-deal','note':'LB DEN->SF 1yr/$7.5M (audit-confirmed)'},
}

# ----------------------------------------------------------------------------------------------------
# KNOWN DATA GAPS: players who materially affect a unit but are ABSENT from the SIS Points Saved source,
# so the reweight cannot credit them. Documented, NOT patched with a fabricated value -- grafting an
# off-scale PFF grade onto SIS Points Saved would be an arbitrary override AND would assume 2026 health.
# Surfaced honestly in defense.json meta so the reader can judge the residual uncertainty themselves.
# ----------------------------------------------------------------------------------------------------
KNOWN_GAPS=[
 {'player':'Kerby Joseph','team':'DET','unit':'coverage',
  'reason':('Absent from SIS coverage Points Saved top-200 in BOTH 2024 and 2025. 2025: injured '
            '(211 coverage snaps, PFF grade 57.7). 2024: healthy and elite by PFF (grade 91.5, 781 snaps) '
            'yet SIS PS still did not rank him top-200 -- SIS Points Saved structurally discounts his '
            'gambling / ball-hawk safety style. 2026 availability reported UNCERTAIN.'),
  'effect':('DET coverage is not credited for a healthy-Joseph outcome. If he returns to 2024 form, '
            "DET's coverage unit would rank materially higher than the SIS-based number shows."),
  'src':'https://www.detroitnews.com/story/sports/nfl/lions/2026/02/24/detroit-lions-give-update-on-injured-safeties-kerby-joseph-brian-branch/88846250007/'},
]

UNITS=[('coverage','sis_value/pass_defense.csv'),('pass_rush','sis_value/pass_rush.csv'),('run_def','sis_value/run_defense.csv')]
# ---- GUARD: everything ABOVE this line is what normalize_defense_2026.py execs to import MOVES.
# Everything BELOW writes the rookie-BLIND defense.json. Block an accidental full run so a stray
# invocation can't silently clobber the canonical (rookie-aware) grades again (2026-07-05 regression).
import os as _os, sys as _sys
if __name__=='__main__' and _os.environ.get('BB_ALLOW_LEGACY_DEFENSE')!='1':
    _sys.stderr.write("\n!! reweight_defense_2026.py is the LEGACY, rookie-BLIND writer. "
        "defense.json's canonical writer is normalize_defense_2026.py.\n"
        "   Refusing to overwrite defense.json. To force the legacy run anyway: "
        "BB_ALLOW_LEGACY_DEFENSE=1 python3 reweight_defense_2026.py\n")
    _sys.exit(2)
applied_log=collections.defaultdict(list)  # team-code -> list of move dicts (for moves_2026)
applied_keys=set()

def load_players(path):
    """Return list of dicts {name,key,team2025(code or '2T'),pos,ps,epatgt,tgts}. Keep '2 teams' (need them for movers)."""
    out=[]
    for r in csv.DictReader(open(path,encoding='utf-8')):
        raw=str(r.get('Team','')).strip()
        ps=num(r.get('Points Saved'))
        code = '2T' if raw=='2 teams' else nick(raw)
        out.append({'name':r.get('Player'),'key':fn(r.get('Player')),'team2025':code,'team2025raw':raw,
                    'pos':(r.get('Pos.') or '').strip(),'ps':ps,
                    'epatgt':num(r.get('EPA/Tgt')),'tgts':num(r.get('Tgts'))})
    return out

def reweight_unit(unit, path):
    """Return (str2025{code:sum}, str2026{code:sum}, roster2026{code:[player...]}, top2026 helper data)."""
    players=load_players(path)
    str2025=collections.defaultdict(float); str2026=collections.defaultdict(float)
    roster2026=collections.defaultdict(list)
    for p in players:
        if p['ps'] is None: continue
        c25=p['team2025']
        # 2025 strength: skip '2 teams' (matches ingest_defense's original behavior)
        if c25 and c25!='2T': str2025[c25]+=p['ps']
        # 2026 assignment
        mv=MOVES.get(p['key'])
        if mv:
            dest=mv['to']
            applied_keys.add(p['key'])
            if dest in ('RETIRED','UFA'):
                pass  # production leaves the league -> add nothing
            else:
                str2026[dest]+=p['ps']
                rp=dict(p); rp['from']=c25 if c25 and c25!='2T' else p['team2025raw']; rp['to']=dest
                roster2026[dest].append(rp)
                applied_log[dest].append({'player':p['name'],'unit':unit,'from':rp['from'],'to':dest,
                                          'ps':round(p['ps'],1),'src':mv['src'],
                                          'conf':mv.get('conf',True),'note':mv.get('note')})
        else:
            # stays; '2 teams' non-movers have no single 2026 home -> drop (rare, replacement-level)
            if c25 and c25!='2T':
                str2026[c25]+=p['ps']
                roster2026[c25].append(dict(p,**{'from':c25,'to':c25}))
    return str2025, str2026, roster2026

R={}
for unit,path in UNITS:
    R[unit]=reweight_unit(unit, core.P(path))

# unmatched movers (in map but never found in any CSV) -> note
all_csv_keys=set()
for unit,path in UNITS:
    for r in csv.DictReader(open(core.P(path),encoding='utf-8')):
        all_csv_keys.add(fn(r.get('Player')))
unmatched=[k for k in MOVES if k not in all_csv_keys]

ALL_TEAMS=sorted(set(NICK.values()))

def league_pctl(valmap):
    items=[(t,v) for t,v in valmap.items() if v is not None]
    if not items: return {}
    vals=sorted(v for _,v in items); n=len(vals); out={}
    for t,v in items:
        lo=bisect.bisect_left(vals,v); hi=bisect.bisect_right(vals,v)
        rank=(lo+hi+1)/2.0; p=(rank-0.5)/n*100.0; out[t]=round(p,1)
    return out

# Build strength maps over ALL 32 teams (default 0.0 so a team with no contributors still pctls)
def fullmap(d): return {t:round(d.get(t,0.0),1) for t in ALL_TEAMS}
cov25=fullmap(R['coverage'][0]);  cov26=fullmap(R['coverage'][1])
rush25=fullmap(R['pass_rush'][0]);rush26=fullmap(R['pass_rush'][1])
run25=fullmap(R['run_def'][0]);   run26=fullmap(R['run_def'][1])
covp25=league_pctl(cov25); covp26=league_pctl(cov26)
rushp25=league_pctl(rush25); rushp26=league_pctl(rush26)
runp25=league_pctl(run25); runp26=league_pctl(run26)

# cov epa/tgt on the 2026 roster (target-weighted)
def cov_epatgt_2026():
    out={}
    for code,plist in R['coverage'][2].items():
        nu=0.0; de=0.0
        for p in plist:
            if p.get('epatgt') is not None and p.get('tgts') is not None:
                nu+=p['epatgt']*p['tgts']; de+=p['tgts']
        out[code]=round(nu/de,4) if de>0 else None
    return out
cov_epa26=cov_epatgt_2026()

def top3(plist):
    return sorted([p for p in plist if p.get('ps') is not None], key=lambda p:p['ps'], reverse=True)[:3]

# also need 2025 cov epatgt + 2025 top3 for reference (recompute from original per-team, excl 2 teams)
import json
def _load_old_defense():
    import glob as _g
    for _p in [core.P('defense.json')]+sorted(_g.glob(core.P('_prebuild_backup_*/defense.json')),reverse=True):
        try: return json.load(open(_p,encoding='utf-8')).get('teams',{})
        except Exception: continue
    return {}
old=_load_old_defense()

team_profiles={}
for code in ALL_TEAMS:
    o=old.get(code,{})
    covros=R['coverage'][2].get(code,[]); rushros=R['pass_rush'][2].get(code,[]); runros=R['run_def'][2].get(code,[])
    team_profiles[code]={
        'team':code,
        # 2025 reference = TRUE no-moves baseline (computed this run), NOT prior output
        'pass_cov_strength_2025':cov25[code], 'pass_cov_pctl_2025':covp25.get(code),
        'pass_rush_strength_2025':rush25[code],'pass_rush_pctl_2025':rushp25.get(code),
        'run_def_strength_2025':run25[code],    'run_def_pctl_2025':runp25.get(code),
        'pass_cov_epatgt_2025':o.get('pass_cov_epatgt'),
        # 2026-adjusted (these drive the matchup engine going forward)
        'pass_cov_strength_2026':cov26[code], 'pass_cov_pctl_2026':covp26.get(code),
        'pass_rush_strength_2026':rush26[code],'pass_rush_pctl_2026':rushp26.get(code),
        'run_def_strength_2026':run26[code],   'run_def_pctl_2026':runp26.get(code),
        'pass_cov_epatgt_2026':cov_epa26.get(code),
        # CANONICAL fields consumed downstream (= 2026-adjusted)
        'pass_cov_strength':cov26[code], 'pass_cov_pctl':covp26.get(code), 'pass_cov_epatgt':cov_epa26.get(code),
        'pass_rush_strength':rush26[code],'pass_rush_pctl':rushp26.get(code),
        'run_def_strength':run26[code],   'run_def_pctl':runp26.get(code),
        # top contributors on the 2026 roster
        'top_coverage':[{'name':p['name'],'pos':p['pos'],'ps':round(p['ps'],1),'epatgt':p.get('epatgt')} for p in top3(covros)],
        'top_pass_rush':[{'name':p['name'],'pos':p['pos'],'ps':round(p['ps'],1)} for p in top3(rushros)],
        'top_run_def':[{'name':p['name'],'pos':p['pos'],'ps':round(p['ps'],1)} for p in top3(runros)],
        'moves_2026':sorted(applied_log.get(code,[]),key=lambda m:-abs(m['ps'])),
    }

defense_doc={'meta':{'n_teams':len(team_profiles),
    'source':'SIS DataHub 2025 Points Saved, REWEIGHTED onto 2026 rosters (accounting reweight, not a refit)',
    'method':'Each confirmed 2026 mover carries their FULL 2025 Points Saved to their 2026 team; RETIRED/UFA subtract only; "2 teams" players assign combined PS to their 2026 team; rookies/incoming-with-no-2025-data add NOTHING (replacement-level floor). 32-team percentiles recomputed per unit.',
    'fields':{'*_2025':'original 2025 strength/pctl (reference)','*_2026':'2026-roster-adjusted strength/pctl (canonical, used by the matchup engine)',
              'pass_cov_*':'coverage Points Saved (higher=better)','pass_rush_*':'pass-rush PS','run_def_*':'run-defense PS',
              '*_pctl':'league percentile across 32 teams (0-100, higher=better unit)',
              'pass_cov_epatgt':'target-weighted EPA/Tgt allowed (NEGATIVE=good)',
              'top_*':'top-3 contributors per unit on the 2026 roster','moves_2026':'applied 2026 roster moves (player, from->to, unit, ps, source, conf)'},
    'assumptions':['Default: a player STAYS on his 2025 team unless a CONFIRMED move was found.',
                   'Rookies/incoming players with no 2025 SIS data add nothing (honest replacement-level floor).',
                   'RETIRED/UFA-unsigned: production leaves the league (subtract only).',
                   'Low-confidence moves (conf=false): Kevin Byard->NE, Dre\'Mont Jones->NE, K\'Lavon Chaisson->WAS (sources disagreed).'],
    'known_gaps':KNOWN_GAPS,
    'unmatched_movers':unmatched},
    'teams':team_profiles}
core.safe_json_dump(defense_doc, core.P('defense.json'), indent=2)

# ---- re-map OPPONENT 2026 pctls onto offensive players (same W15 mapping) ----
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
nopp=0
for f in feats:
    if f['pos'] not in ('QB','RB','WR','TE'): continue
    opp=nt(f.get('w15') or '')
    prof=team_profiles.get(opp)
    if not prof: continue
    got=False
    if prof.get('pass_cov_pctl')  is not None: f['opp_pass_cov_pctl']=prof['pass_cov_pctl']; got=True
    if prof.get('pass_rush_pctl') is not None: f['opp_pass_rush_pctl']=prof['pass_rush_pctl']; got=True
    if prof.get('run_def_pctl')   is not None: f['opp_run_def_pctl']=prof['run_def_pctl']; got=True
    if prof.get('pass_cov_epatgt')is not None: f['opp_pass_cov_epatgt']=prof['pass_cov_epatgt']
    if got: nopp+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'added':'opponent (W15) 2026-ADJUSTED defense pctls: opp_pass_cov_pctl/opp_pass_rush_pctl/opp_run_def_pctl (+epatgt); abstain if no opp'},'players':feats}, core.P('features.json'))

# ---- report ----
print("defense.json: %d teams | offensive players w/ opp 2026 pctls: %d | feature cols %d"%(len(team_profiles),nopp,len(cols)))
print("applied movers: %d/%d (unmatched in CSVs: %s)"%(len(applied_keys),len(MOVES),unmatched))
def biggest(p25,p26,label,n=6):
    deltas=sorted(((t,round(p26.get(t,0)-(p25.get(t) or 0),1)) for t in ALL_TEAMS), key=lambda x:x[1])
    print("\n[%s] biggest pctl FALLS:"%label, deltas[:n])
    print("[%s] biggest pctl RISES:"%label, deltas[-n:][::-1])
# 2025 pctls = TRUE no-moves baseline computed above (not prior output) -> real deltas
biggest(covp25,covp26,'COVERAGE')
biggest(rushp25,rushp26,'PASS-RUSH')
biggest(runp25,runp26,'RUN-DEF')
