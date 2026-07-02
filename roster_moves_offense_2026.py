#!/usr/bin/env python3
"""Curated OFFENSIVE roster-move registry, 2026 -- the offensive analogue of the defense
MOVES dict in reweight_defense_2026.py. Closes the provenance gap flagged in
ROSTER_MOVES_2026.md ("offensive moves have no sourced provenance like defense does").

One entry per 2025->2026 mover detected by audit_roster_moves.py (2025 PBP gamelog team !=
2026 board team). Keys are core.fn-normalized names (lowercase, jr/sr/ii-v suffix stripped,
periods/apostrophes removed, hyphens->spaces) so joins stay robust.

Fields per entry:
  from       2025 gamelog team (PBP mode team, canonical core join)
  to         2026 board team, or 'UFA' when DK lists no 2026 team (unsigned)
  src        REAL news URL, attached ONLY when actually retrieved (WebFetch, 2026-07-02)
             and confirmed to report the exact from->to move; None otherwise. NO URL here
             is guessed or reconstructed -- consensus-only entries honestly carry src=None.
  conf       'high' = both independent sources (ffdataroma + clay) attest the 2026 team
             alongside dk + all model views (or, for UFA, a retrieved news URL confirms);
             'med'  = at least one attesting source missing (see note).
  provenance the in-repo team views that attest this exact 2026 team, recomputed from the
             sources themselves (dk=dk_adp / ffdataroma=player-teams export / clay=pipeline
             projections / signals=board / features / flags). This cross-source unanimity is
             the PRIMARY verifiable documentation; the news URL is corroboration on top.
  note       short human-readable route + mechanism (mechanism stated only when a retrieved
             article reports it -- consensus-only entries make no signing-vs-trade claim).

Consumed by audit_roster_moves.py (ast.literal_eval of MOVES, mirroring how it already reads
the defense dict) to mark offensive moves DOCUMENTED and to cross-check destinations on every
rebuild (a registry 'to'/'from' that stops matching the board fires a P0 doc-mismatch).
"""

MOVES = {
 # --- NEWS-SOURCED team moves (URL retrieved & verified 2026-07-02; ADP-notable players) ---
 'kenneth walker':{'from':'SEA','to':'KC','conf':'high','src':'https://www.nfl.com/news/chiefs-signing-ex-seahawks-rb-kenneth-walker-iii-mvp-of-super-bowl-lx','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'SEA->KC; FA signing, 3-yr deal (NFL.com 2026-03-09)'},
 'aj brown':{'from':'PHI','to':'NE','conf':'high','src':'https://www.patriots.com/news/patriots-acquire-wr-a-j-brown-in-a-trade-with-the-philadelphia-eagles','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'PHI->NE; traded to NE for draft picks (patriots.com 2026-06-01)'},
 'travis etienne':{'from':'JAX','to':'NO','conf':'high','src':'https://www.nfl.com/news/saints-signing-ex-jaguars-rb-travis-etienne-ex-bills-ol-david-edwards','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'JAX->NO; FA signing (NFL.com 2026-03-09)'},
 'dj moore':{'from':'CHI','to':'BUF','conf':'high','src':'https://www.nfl.com/news/bears-trading-wr-dj-moore-to-bills-for-mid-round-draft-pick','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'CHI->BUF; traded for a 2026 2nd-rounder (NFL.com 2026-03-05)'},
 'jaylen waddle':{'from':'MIA','to':'DEN','conf':'high','src':'https://www.nfl.com/news/dolphins-trading-wr-jaylen-waddle-to-broncos-for-draft-picks-including-2026-first-rounder','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'MIA->DEN; traded for picks incl a 2026 1st (NFL.com 2026-03-17)'},
 'david montgomery':{'from':'DET','to':'HOU','conf':'high','src':'https://www.detroitlions.com/news/lions-trade-rb-david-montgomery-to-houston-texans','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'DET->HOU; traded for Juice Scruggs + picks (detroitlions.com 2026-03-11)'},
 'mike evans':{'from':'TB','to':'SF','conf':'high','src':'https://www.nfl.com/news/mike-evans-to-sign-with-49ers-ending-12-year-tenure-with-buccaneers','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'TB->SF; 3-yr FA signing, ends 12-yr TB tenure (NFL.com 2026-03-09)'},
 'rico dowdle':{'from':'CAR','to':'PIT','conf':'high','src':'https://sports.yahoo.com/nfl/breaking-news/article/steelers-sign-former-panthers-standout-rb-rico-dowdle-to-2-year-deal-232129628.html','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'CAR->PIT; 2-yr FA signing (Yahoo Sports 2026-03-13)'},
 'kenneth gainwell':{'from':'PIT','to':'TB','conf':'high','src':'https://www.buccaneers.com/news/rb-kenneth-gainwell-signs-bucs-2026-nfl-free-agency','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'PIT->TB; 2-yr FA signing (buccaneers.com 2026-03-12)'},
 'michael pittman':{'from':'IND','to':'PIT','conf':'high','src':'https://www.nfl.com/news/michael-pittman-jr-trade-steelers-colts','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'IND->PIT; trade + 3yr/$59M extension (NFL.com 2026-03-09)'},
 'wandale robinson':{'from':'NYG','to':'TEN','conf':'high','src':'https://www.nfl.com/news/titans-signing-ex-giants-wr-wan-dale-robinson-to-four-year-78-million-deal','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'NYG->TEN; 4yr/$78M FA signing (NFL.com 2026-03-09)'},
 'kyler murray':{'from':'ARI','to':'MIN','conf':'high','src':'https://www.nfl.com/news/vikings-sign-kyler-murray-one-year-deal-release-cardinals','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'ARI->MIN; released by ARI, 1-yr league-min MIN deal; MIN QB1 on board, McCarthy to backup (NFL.com 2026-03-12)'},
 'rachaad white':{'from':'TB','to':'WAS','conf':'high','src':'https://www.commanders.com/news/commanders-sign-rb-rachaad-white','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'TB->WAS; FA signing (commanders.com 2026-03-13)'},
 'romeo doubs':{'from':'GB','to':'NE','conf':'high','src':'https://www.nfl.com/news/romeo-doubs-patriots-sign-former-packers-wr-four-year-contract','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'GB->NE; 4-yr FA signing (NFL.com 2026-03-10)'},
 'isaiah likely':{'from':'BAL','to':'NYG','conf':'high','src':'https://www.baltimoreravens.com/news/isaiah-likely-signing-new-york-giants-ravens-free-agent-tight-end','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'BAL->NYG; 3yr/$40M, follows HC Harbaugh to NYG (baltimoreravens.com 2026-03-09)'},
 'geno smith':{'from':'LV','to':'NYJ','conf':'high','src':'https://www.newyorkjets.com/news/jets-acquire-quarterback-geno-smith-trade-raiders-03-11-2026','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'LV->NYJ; traded LV->NYJ in late-round pick swap (newyorkjets.com 2026-03-11)'},
 'tua tagovailoa':{'from':'MIA','to':'ATL','conf':'high','src':'https://www.atlantafalcons.com/news/atlanta-falcons-sign-qb-tua-tagovailoa','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'MIA->ATL; signed by ATL after MIA exit (atlantafalcons.com 2026-03-13)'},
 'kirk cousins':{'from':'ATL','to':'LV','conf':'high','src':'https://www.nfl.com/news/former-falcons-qb-kirk-cousins-signing-with-raiders','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'ATL->LV; FA signing; bridge/mentor for No.1 pick Mendoza (NFL.com 2026-04-02)'},
 'justin fields':{'from':'NYJ','to':'KC','conf':'high','src':'https://www.newyorkjets.com/news/jets-trade-justin-fields-kansas-city-chiefs-03-18-2026','provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'NYJ->KC; traded for a 2027 6th; KC QB2 on board (newyorkjets.com 2026-03-18)'},
 # --- CONSENSUS-ONLY team moves (long tail; src=None -- provenance = in-repo cross-source unanimity) ---
 'chris rodriguez':{'from':'WAS','to':'JAX','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'WAS->JAX; no news URL attached (long tail) -- team attested by every in-repo source'},
 'chig okonkwo':{'from':'TEN','to':'WAS','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'TEN->WAS; no news URL attached (long tail) -- team attested by every in-repo source'},
 'isiah pacheco':{'from':'KC','to':'DET','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'KC->DET; no news URL attached (long tail) -- team attested by every in-repo source'},
 'jauan jennings':{'from':'SF','to':'MIN','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'SF->MIN; no news URL attached (long tail) -- team attested by every in-repo source'},
 'jalen nailor':{'from':'MIN','to':'LV','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'MIN->LV; no news URL attached (long tail) -- team attested by every in-repo source'},
 'tyler allgeier':{'from':'ATL','to':'ARI','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'ATL->ARI; no news URL attached (long tail) -- team attested by every in-repo source'},
 'adonai mitchell':{'from':'IND','to':'NYJ','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'IND->NYJ; no news URL attached (long tail) -- team attested by every in-repo source'},
 'dontayvion wicks':{'from':'GB','to':'PHI','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'GB->PHI; no news URL attached (long tail) -- team attested by every in-repo source'},
 'david njoku':{'from':'CLE','to':'LAC','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'CLE->LAC; no news URL attached (long tail) -- team attested by every in-repo source'},
 'christian kirk':{'from':'HOU','to':'SF','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'HOU->SF; no news URL attached (long tail) -- team attested by every in-repo source'},
 'darnell mooney':{'from':'ATL','to':'NYG','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'ATL->NYG; no news URL attached (long tail) -- team attested by every in-repo source'},
 'emanuel wilson':{'from':'GB','to':'SEA','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'GB->SEA; no news URL attached (long tail) -- team attested by every in-repo source'},
 'trevor etienne':{'from':'JAX','to':'CAR','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'JAX->CAR; no news URL attached (long tail) -- team attested by every in-repo source'},
 'jalen tolbert':{'from':'DAL','to':'MIA','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'DAL->MIA; no news URL attached (long tail) -- team attested by every in-repo source'},
 'juju smith schuster':{'from':'KC','to':'NYG','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'KC->NYG; no news URL attached (long tail) -- team attested by every in-repo source'},
 'john metchie':{'from':'NYJ','to':'CAR','conf':'med','src':None,'provenance':['dk', 'ffdataroma', 'signals', 'features', 'flags'],'note':'NYJ->CAR; no news URL attached -- confirmed by dk+ffdataroma+signals+features+flags (missing from clay)'},
 'jmari taylor':{'from':'IND','to':'JAX','conf':'med','src':None,'provenance':['dk', 'ffdataroma', 'signals', 'features', 'flags'],'note':'IND->JAX; no news URL attached -- confirmed by dk+ffdataroma+signals+features+flags (missing from clay)'},
 'calvin austin':{'from':'PIT','to':'NYG','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'PIT->NYG; no news URL attached (long tail) -- team attested by every in-repo source'},
 'greg dortch':{'from':'ARI','to':'DET','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'ARI->DET; no news URL attached (long tail) -- team attested by every in-repo source'},
 'kendrick bourne':{'from':'SF','to':'ARI','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'SF->ARI; no news URL attached (long tail) -- team attested by every in-repo source'},
 'kalif raymond':{'from':'DET','to':'CHI','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'DET->CHI; no news URL attached (long tail) -- team attested by every in-repo source'},
 'jahan dotson':{'from':'PHI','to':'ATL','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'PHI->ATL; no news URL attached (long tail) -- team attested by every in-repo source'},
 'olamide zaccheaus':{'from':'CHI','to':'ATL','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'CHI->ATL; no news URL attached (long tail) -- team attested by every in-repo source'},
 'tutu atwell':{'from':'LAR','to':'MIA','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'LAR->MIA; no news URL attached (long tail) -- team attested by every in-repo source'},
 'charlie kolar':{'from':'BAL','to':'LAC','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'BAL->LAC; no news URL attached (long tail) -- team attested by every in-repo source'},
 'dyami brown':{'from':'JAX','to':'WAS','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'JAX->WAS; no news URL attached (long tail) -- team attested by every in-repo source'},
 'tyler conklin':{'from':'LAC','to':'DET','conf':'med','src':None,'provenance':['dk', 'ffdataroma', 'signals', 'features'],'note':'LAC->DET; no news URL attached -- confirmed by dk+ffdataroma+signals+features (missing from clay+flags)'},
 'jakobi lane':{'from':'WAS','to':'BAL','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'WAS->BAL; no news URL attached (long tail) -- team attested by every in-repo source'},
 'kevin coleman':{'from':'BUF','to':'MIA','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'BUF->MIA; no news URL attached (long tail) -- team attested by every in-repo source'},
 'noah fant':{'from':'CIN','to':'NO','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'CIN->NO; no news URL attached (long tail) -- team attested by every in-repo source'},
 'nick westbrook ikhine':{'from':'MIA','to':'IND','conf':'high','src':None,'provenance':['dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'],'note':'MIA->IND; no news URL attached (long tail) -- team attested by every in-repo source'},
 # --- DEPARTED TO FREE AGENCY (DK lists no 2026 team; ffdataroma/clay absence expected for unsigned) ---
 'stefon diggs':{'from':'NE','to':'UFA','conf':'high','src':'https://www.espn.com/nfl/story/_/id/48103213/new-england-patriots-release-stefon-diggs-free-agent-means-wr-nfl-draft','provenance':['dk', 'signals', 'features', 'flags'],'note':'NE->UFA; released by NE (ESPN 2026-03-04); DK board lists him unsigned'},
 'deebo samuel':{'from':'WAS','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features', 'flags'],'note':'WAS->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
 'nick chubb':{'from':'HOU','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features', 'flags'],'note':'HOU->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
 'kareem hunt':{'from':'KC','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features', 'flags'],'note':'KC->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
 'deandre hopkins':{'from':'BAL','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features', 'flags'],'note':'BAL->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
 'keenan allen':{'from':'LAC','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features', 'flags'],'note':'LAC->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
 'darren waller':{'from':'MIA','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features', 'flags'],'note':'MIA->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
 'zach ertz':{'from':'WAS','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features', 'flags'],'note':'WAS->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
 'jonnu smith':{'from':'PIT','to':'UFA','conf':'med','src':None,'provenance':['dk', 'signals', 'features'],'note':'PIT->UFA; DK board lists no 2026 team; absent from both roster sources (consistent w/ unsigned)'},
}

if __name__ == '__main__':   # self-check: keys are fn-normalized, teams are canonical codes
    import core
    codes = set(core.FULL2ABBR.values()) | {'UFA'}
    bad = [k for k in MOVES if core.fn(k) != k]
    badt = [(k, v) for k, v in MOVES.items() if v['to'] not in codes or v['from'] not in codes - {'UFA'}]
    n_url = sum(1 for v in MOVES.values() if v['src'])
    n_fa = sum(1 for v in MOVES.values() if v['to'] == 'UFA')
    print('entries=%d news-sourced=%d consensus-only=%d to-UFA=%d bad-keys=%s bad-teams=%s'
          % (len(MOVES), n_url, len(MOVES) - n_url, n_fa, bad, badt))
