#!/usr/bin/env python3
"""ROSTER-MOVE AUDIT -- catches wrong-team data errors and makes 2026 roster moves legible.
Data-side companion of integration_audit.py (which audits code wiring; this audits the DATA).

WHY THIS EXISTS (the Kyler Murray gap): DEFENSIVE roster moves have curated, sourced provenance
(reweight_defense_2026.py MOVES = {player: {'to','src','note','conf'}}), but OFFENSIVE team
assignments are taken on faith from the ADP source files with no verification layer. So a REAL
move (Kyler Murray ARI->MIN) and a DATA ERROR (a stray name-join putting a player on the wrong
team) looked identical -- Kyler->MIN was only confirmed because a Q&A agent stumbled on it.
The separating signature is CROSS-SOURCE AGREEMENT: a real move shows every independent source
agreeing on the new team; a mis-join/stale row shows sources disagreeing. This audit makes that
signature systematic and re-checks it on every rebuild.

CHECK 1 -- CROSS-SOURCE TEAM CONSISTENCY (the catch). For every board player, compare the team
  assigned by each source:
    dk         dk_adp.csv Team               (DraftKings market; the team feeder for the model)
    ffdataroma models-projections__player-teams.csv  (INDEPENDENT outside site)
    clay       pipeline/clay_2026.csv        (INDEPENDENT projection source)
    signals    draft_board_signals.csv       (board snapshot; team copied from dk at build time)
    features   features.csv                  (model feature store)
    flags      flag_ranks.json               (model rank layer)
  ffdataroma + clay are genuinely independent; signals/features/flags inherit team from dk, so a
  model-vs-dk mismatch = internal drift/mis-join (stale rebuild or a bad name join), and a
  dk-vs-ffdataroma/clay mismatch = a genuine source conflict needing eyeballs. Names are joined
  via core.fn/core.resolve (pos-aware, first-name-variant safe) so normalization noise doesn't
  fake a disagreement; players PRESENT in one source but MISSING in another are reported too.

CHECK 2 -- MOVE RECONCILIATION (legibility/provenance). Prior team = each player's 2025 gamelog
  team (mode team over 2025 PBP, pipeline/player_games.parquet, via the canonical
  core.build_usage_index/match_usage join -- the same authority features.csv team25 uses).
  Every player whose 2026 board team differs is a MOVE, cross-referenced against the curated
  defense MOVES dict: DOCUMENTED (curated, with source URL) vs UNDOCUMENTED (offensive,
  ADP-sourced only -- the class that needs eyeballing) vs UNSIGNED-FA.

CHECK 3 -- MOVE PROPAGATION (the ripple). A move must not leave stale context behind:
    a. schedule: every player's W15/W16/W17 in features.csv must be his 2026 team's schedule.
    b. QB context: boom/opp_offense.json[team].qb (lowest-ADP QB, drives qb_q/off_q/DST flags)
       must itself be boarded on that team (catches a stale McCarthy-as-MIN-starter class).
    c. usage: every detected mover must carry a reprojected usage_src in
       boom/movers_reprojection.json (reproject_movers.py ran and saw him).
    d. team25: features.csv team25 must equal the recomputed 2025 gamelog team (stale build).

Run:  python3 audit_roster_moves.py            # write ROSTER_MOVES_2026.md + console summary
      python3 audit_roster_moves.py --strict   # exit 1 on any genuine finding (pipeline gate)
"""
import os, sys, csv, json, ast, collections
import core

HERE = os.path.dirname(os.path.abspath(__file__))
FF_TEAMS = os.path.join(HERE, 'ffdataroma_draft_guide_export', 'ffdataroma', 'csv',
                        'models-projections__player-teams.csv')


def rows_csv(path):
    return list(csv.DictReader(open(path, encoding='utf-8')))


def load_defense_moves():
    """Parse the curated MOVES dict out of reweight_defense_2026.py WITHOUT importing it
    (that module executes its full reweight at import time). ast.literal_eval = data only."""
    src = open(core.P('reweight_defense_2026.py'), encoding='utf-8').read()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'MOVES' for t in node.targets):
            return ast.literal_eval(node.value)
    return {}


class Source:
    """One team-assignment source: (fn,pos)-exact lookup first, then the shared safe fuzzy
    resolver (core.resolve) so jr/sr + first-name variants never fake a disagreement.
    SAME-NAME COLLISIONS (two distinct players sharing fn+pos, e.g. dk_adp's two 'Kyle Williams'
    WRs on TEN and NE) are disambiguated by ADP when the source carries one (the board row's ADP
    is exact-copied from dk_adp, so the nearest-ADP candidate IS the same physical row); an
    unresolvable collision returns None and is logged in self.ambiguous -- reported as an
    ambiguity, never as a fake disagreement."""
    def __init__(self, key, pairs):
        # pairs: iterable of (display_name, pos, team, adp_or_None)
        self.key = key
        self.by_np = collections.defaultdict(list)   # (fn,pos) -> [(team, adp)]
        idx_pairs = []
        self.team_of = collections.defaultdict(list)
        self.ambiguous = []                          # (board_name, [candidate teams]) log
        for disp, pos, team, adp in pairs:
            k = core.fn(disp); t = core.norm_team(team)
            try: a = float(adp)
            except (TypeError, ValueError): a = None
            self.by_np[(k, (pos or '').upper())].append((t, a))
            self.team_of[k].append(t)
            idx_pairs.append((disp, pos))
        self.idx = core.build_name_index(idx_pairs)

    def _pick(self, name, cands, adp):
        teams = {t for t, _ in cands}
        if len(teams) == 1:
            return next(iter(teams))                 # duplicate rows, one team -> unambiguous
        if adp is not None:
            with_adp = [(abs(a - adp), t) for t, a in cands if a is not None]
            if with_adp:
                return min(with_adp)[1]              # nearest-ADP row = the same physical player
        self.ambiguous.append((name, sorted(teams)))
        return None                                  # cannot tell WHICH same-name player -> abstain
    def team(self, name, pos, adp=None):
        k = core.fn(name)
        cands = self.by_np.get((k, (pos or '').upper()))
        if cands:
            return self._pick(name, cands, adp)
        disp = core.resolve(name, pos, self.idx)
        if not disp:
            return None
        teams = self.team_of.get(core.fn(disp), [])
        return teams[0] if len(set(teams)) == 1 else self._pick(name, [(t, None) for t in teams], adp)


def main():
    strict = '--strict' in sys.argv

    # ---------- load every team view ----------
    board = rows_csv(core.P('draft_board_signals.csv'))
    dk    = Source('dk', ((r['Name'], r['Position'], r['Team'], r.get('ADP')) for r in rows_csv(core.P('dk_adp.csv'))))
    ff    = Source('ffdataroma', ((r['player'], r['position'], r['team'], None) for r in rows_csv(FF_TEAMS)))
    clay  = Source('clay', ((r['name'], r['pos'], r['team'], None) for r in rows_csv(core.PP('clay_2026.csv'))))
    featr = rows_csv(core.P('features.csv'))
    feats = Source('features', ((r['name'], r['pos'], r['team'], r.get('adp')) for r in featr))
    frp   = json.load(open(core.P('flag_ranks.json'), encoding='utf-8'))['players']
    flags = Source('flags', ((v['name'], v.get('pos'), v.get('team'), v.get('adp')) for v in frp.values()))
    SOURCES = [('dk', dk), ('ffdataroma', ff), ('clay', clay), ('signals', None),
               ('features', feats), ('flags', flags)]

    # ---------- CHECK 1: cross-source team consistency ----------
    disagreements, missing = [], collections.defaultdict(list)   # source -> [(name,pos,team,adp)]
    per_player_teams = {}
    for r in board:
        nm, pos = r['name'], r['pos']
        sig = core.norm_team(r.get('team'))
        try: badp = float(r.get('adp'))
        except (TypeError, ValueError): badp = None
        t = {'signals': sig}
        for skey, s in SOURCES:
            if s is None:
                continue
            t[skey] = s.team(nm, pos, badp)
            if t[skey] is None:
                missing[skey].append((nm, pos, sig, badp or 0))
        per_player_teams[core.fn(nm)] = t
        got = {v for v in t.values() if v}
        if len(got) > 1:
            disagreements.append({'name': nm, 'pos': pos, 'adp': float(r['adp'] or 0), 'teams': t})

    # presence gaps: a FA board player is EXPECTED to be absent from team-roster sources
    def split_fa(lst):
        return ([x for x in lst if x[2] != 'FA'], [x for x in lst if x[2] == 'FA'])

    # ---------- CHECK 2: move reconciliation ----------
    DEF_MOVES = load_defense_moves()
    ag, IDX, _SH = core.build_usage_index()      # 2025 PBP mode team (canonical join)
    fmap = {core.fn(r['name']): r for r in featr}
    mrs = {}
    mr_note = ''
    mrp = core.P(os.path.join('boom', 'movers_reprojection.json'))
    if os.path.exists(mrp):
        mrs = {core.fn(m.get('name')): m for m in json.load(open(mrp, encoding='utf-8')).get('movers', [])}
    else:
        mr_note = 'boom/movers_reprojection.json missing -> usage-reprojection subcheck SKIPPED'

    moves, stale25, unreproj, doc_mismatch = [], [], [], []
    n_prior = 0
    for r in board:
        nm, pos = r['name'], r['pos']; k = core.fn(nm)
        tm26 = core.norm_team(r.get('team'))
        u = core.match_usage(nm, pos, tm26, IDX)
        if u is None:
            continue                      # rookie / no 2025 usage -> not a "move"
        n_prior += 1
        t25 = core.norm_team(u['team'])
        # features team25 staleness (d)
        f25 = core.norm_team((fmap.get(k) or {}).get('team25') or '')
        if f25 and f25 != t25:
            stale25.append((nm, f25, t25))
        if not t25 or not tm26 or t25 == tm26:
            continue
        dm = DEF_MOVES.get(k)
        if dm:
            status, prov = 'DOCUMENTED (defense MOVES)', dm.get('src', '')
            if dm.get('to') not in (tm26, 'RETIRED', 'UFA'):
                doc_mismatch.append((nm, dm.get('to'), tm26))
        elif tm26 == 'FA':
            status, prov = 'UNSIGNED-FA', 'DK lists no 2026 team (unsigned)'
        else:
            status, prov = 'UNDOCUMENTED (ADP-sourced)', 'no curated source; team = ADP feeds only'
        t = per_player_teams.get(k, {})
        known = {v for v in t.values() if v}
        mrec = mrs.get(k, {})
        if mrs and not mrec.get('usage_src'):
            unreproj.append(nm)           # mover whose usage was never re-projected (c)
        moves.append({'name': nm, 'pos': pos, 'adp': float(r['adp'] or 0), 'from': t25, 'to': tm26,
                      'status': status, 'prov': prov, 'clean': len(known) == 1,
                      'usage_src': mrec.get('usage_src'), 'conf': mrec.get('mover_conf')})
    moves.sort(key=lambda m: m['adp'])
    n_doc = sum(1 for m in moves if m['status'].startswith('DOCUMENTED'))
    n_fa = sum(1 for m in moves if m['status'] == 'UNSIGNED-FA')
    n_undoc = len(moves) - n_doc - n_fa

    # ---------- CHECK 3a: schedule follows the 2026 team ----------
    # NB: schedule_2026.csv Team = FULL names ('Arizona Cardinals') -> core.team_abbr, NOT norm_team
    # (build_features.py:20 maps norm_team here, which is why features' opp_w15/16/17 are all empty;
    # harmless today -- every live consumer reads the board-derived w15/w16/w17 -- but don't copy it).
    sched = {}
    for r in rows_csv(core.PP('schedule_2026.csv')):
        tmc = core.team_abbr(r['Team'])
        sched[tmc] = {w: core.norm_team(str(r['Week ' + str(w)]).replace('@', '').replace('vs', '').strip())
                      for w in (15, 16, 17)}
    sched_bad = []
    for r in featr:
        tmc = core.norm_team(r.get('team'))
        if tmc not in sched:
            continue                      # FA / unknown -> no schedule to check
        for wk, col in ((15, 'w15'), (16, 'w16')):
            got = core.norm_team(r.get(col) or '')
            if got and sched[tmc][wk] and got != sched[tmc][wk]:
                sched_bad.append((r['name'], tmc, wk, got, sched[tmc][wk]))
        w17 = r.get('w17') or ''
        if '@' in w17 and tmc not in [core.norm_team(x) for x in w17.split('@')]:
            sched_bad.append((r['name'], tmc, 17, w17, 'team not in W17 game'))

    # ---------- CHECK 3b: per-team QB context is a QB boarded on that team ----------
    qbctx_bad, qb_rows = [], []
    oo_path = core.P(os.path.join('boom', 'opp_offense.json'))
    oo = json.load(open(oo_path, encoding='utf-8')) if os.path.exists(oo_path) else {}
    board_team = {core.fn(r['name']): core.norm_team(r['team']) for r in board}
    if oo:
        for tmc, v in sorted(oo.items()):
            qb = v.get('qb')
            bt = board_team.get(core.fn(qb)) if qb else None
            if not qb or bt != tmc:
                qbctx_bad.append((tmc, qb, bt))
    # QB starter/backup table for every team touched by a QB move (both ends)
    qb_teams = sorted({m[key] for m in moves if m['pos'] == 'QB' for key in ('from', 'to')} - {'FA'})
    for tmc in qb_teams:
        qbs = sorted([(float(r['adp'] or 999), r['name'], r.get('proj_pg'))
                      for r in board if r['pos'] == 'QB' and core.norm_team(r['team']) == tmc])[:2]
        qb_rows.append((tmc, (oo.get(tmc) or {}).get('qb'), (oo.get(tmc) or {}).get('qb_q'), qbs))

    # ---------- verdicts ----------
    p0 = len(disagreements) + len(doc_mismatch) + len(sched_bad) + len(qbctx_bad) + len(stale25) + len(unreproj)

    # ---------- ROSTER_MOVES_2026.md ----------
    L = ['# ROSTER MOVES 2026 — cross-source audit', '',
         '_Regenerated by `audit_roster_moves.py` on every rebuild; data-side companion of INTEGRATION_AUDIT.md._',
         '_A REAL move = every source agrees on the new team. A DATA ERROR (mis-join / stale row) = sources disagree._', '']
    L.append('## Summary')
    L.append(f'- **{len(board)} board players** audited across 6 team views '
             f'(dk / ffdataroma / clay independent+market; signals / features / flags model-side)')
    L.append(f'- **{len(disagreements)} cross-source team disagreements** (P0 — each one is a mis-join or a source conflict)')
    L.append(f'- **{len(moves)} roster moves** detected vs 2025 gamelog team ({n_prior} players with 2025 priors): '
             f'**{n_doc} documented** (curated defense MOVES) · **{n_undoc} undocumented** (offensive, ADP-sourced) · **{n_fa} to-FA/unsigned**')
    L.append(f'- propagation: **{len(sched_bad)}** stale-schedule rows · **{len(qbctx_bad)}** stale QB-context teams · '
             f'**{len(unreproj)}** movers without usage re-projection · **{len(stale25)}** stale `team25` rows'
             + (f' _({mr_note})_' if mr_note else ''))
    nf_ff, fa_ff = split_fa(missing.get('ffdataroma', []))
    nf_cl, fa_cl = split_fa(missing.get('clay', []))
    L.append(f'- presence gaps: ffdataroma missing {len(nf_ff)} non-FA (+{len(fa_ff)} FA, expected) · '
             f'clay missing {len(nf_cl)} non-FA (+{len(fa_cl)} FA) · '
             f'features missing {len(missing.get("features", []))} · flags missing {len(missing.get("flags", []))}')
    L.append('')

    L.append('## 1. Cross-source team DISAGREEMENTS (the catch)')
    L.append('')
    if disagreements:
        L.append('| player | pos | adp | dk | ffdataroma | clay | signals | features | flags |')
        L.append('|---|---|---|---|---|---|---|---|---|')
        for d in disagreements:
            t = d['teams']
            L.append('| %s | %s | %.1f | %s | %s | %s | %s | %s | %s |' % (
                d['name'], d['pos'], d['adp'],
                *(t.get(kk) or '—' for kk in ('dk', 'ffdataroma', 'clay', 'signals', 'features', 'flags'))))
        L.append('')
        L.append('_Every row above needs eyeballing: dk-vs-model split = internal mis-join/stale rebuild; '
                 'dk-vs-ffdataroma/clay split = genuine source conflict (verify the move)._')
    else:
        L.append('_None. Every board player has ONE team across all resolvable sources — '
                 'every move in section 3 is source-unanimous (the real-move signature)._')
    L.append('')

    L.append('## 2. Presence gaps (in some sources, missing in others)')
    L.append('')
    for label, nonfa, fa in (('ffdataroma', nf_ff, fa_ff), ('clay', nf_cl, fa_cl)):
        L.append(f'- **{label}**: {len(nonfa)} non-FA board players unresolved'
                 + (': ' + ', '.join('%s (%s %s, adp %.0f)' % x for x in sorted(nonfa, key=lambda x: x[3])[:15]) if nonfa else '')
                 + (f' — plus {len(fa)} FA players (expected: team-roster sources don\'t list unsigned FAs)' if fa else ''))
    for skey in ('dk', 'features', 'flags'):
        lst = missing.get(skey, [])
        L.append(f'- **{skey}**: {len(lst)} board players unresolved'
                 + (': ' + ', '.join('%s (%s %s)' % (n, p, t) for n, p, t, _ in lst[:10]) if lst else ''))
    amb = [(s.key, n, tset) for _, s in SOURCES if s is not None for n, tset in s.ambiguous]
    if amb:
        L.append('- **same-name collisions left ambiguous** (distinct players sharing name+pos, no ADP to '
                 'disambiguate; abstained rather than guessed): '
                 + '; '.join('%s in %s %s' % (n, sk, ts) for sk, n, ts in amb))
    L.append('')
    L.append('_A non-FA player missing from an independent source is a soft catch: he cannot be '
             'cross-verified there, so his team rides on fewer sources. Same-name collisions '
             '(e.g. dk_adp carries two `Kyle Williams` WRs, TEN + NE) are resolved by nearest ADP '
             'when the source has one; otherwise the source abstains for that player._')
    L.append('')

    L.append('## 3. Move reconciliation — 2025 gamelog team → 2026 board team')
    L.append('')
    L.append('_Prior team = 2025 PBP mode team (pipeline/player_games.parquet, canonical join). '
             'DOCUMENTED = in the curated defense MOVES dict (reweight_defense_2026.py, with source URL). '
             'UNDOCUMENTED = offensive move known only through the ADP feeds — legit once cross-source-clean '
             '(column `all agree`), but with no curated provenance; this is the class to eyeball._')
    L.append('')
    if moves:
        L.append('| player | pos | adp | 2025 | 2026 | all agree | status | usage reproj | provenance |')
        L.append('|---|---|---|---|---|---|---|---|---|')
        for m in moves:
            us = (m['usage_src'] or '—') + (f' ({m["conf"]})' if m.get('conf') else '')
            L.append('| %s | %s | %.1f | %s | %s | %s | %s | %s | %s |' % (
                m['name'], m['pos'], m['adp'], m['from'], m['to'],
                'YES' if m['clean'] else '**NO**', m['status'], us, m['prov']))
    else:
        L.append('_No moves detected._')
    L.append('')
    if doc_mismatch:
        L.append('**Documented-destination MISMATCHES (P0 — curated `to` disagrees with the board):** '
                 + '; '.join('%s: MOVES says %s, board says %s' % x for x in doc_mismatch))
        L.append('')

    L.append('## 4. Propagation spot-checks (the ripple a move must carry)')
    L.append('')
    L.append(f'- **Schedule follows the 2026 team** (features W15/16/17 vs schedule_2026.csv): '
             + ('OK — 0 violations' if not sched_bad else f'**{len(sched_bad)} violations**: '
                + '; '.join('%s (%s) wk%s has %s want %s' % x for x in sched_bad[:10])))
    L.append(f'- **Team QB context is the boarded starter** (boom/opp_offense.json, drives qb_q / off_q / DST flags): '
             + ('OK — all 32 teams' if (oo and not qbctx_bad) else
                (f'**{len(qbctx_bad)} stale**: ' + '; '.join('%s qb=%s boarded on %s' % x for x in qbctx_bad)
                 if oo else 'SKIPPED (boom/opp_offense.json missing)')))
    L.append(f'- **Mover usage re-projected** (boom/movers_reprojection.json): '
             + (mr_note or ('OK — every detected mover carries a usage_src' if not unreproj
                            else f'**{len(unreproj)} stale-usage movers**: ' + ', '.join(unreproj[:12]))))
    L.append(f'- **features.team25 = recomputed 2025 team**: '
             + ('OK' if not stale25 else f'**{len(stale25)} stale**: '
                + '; '.join('%s features=%s recomputed=%s' % x for x in stale25[:10])))
    L.append('')
    if qb_rows:
        L.append('### QB rooms touched by a QB move (starter = lowest ADP; drives the team QB context)')
        L.append('')
        L.append('| team | QB context (opp_offense) | qb_q | QB1 (adp, proj) | QB2 (adp, proj) |')
        L.append('|---|---|---|---|---|')
        for tmc, qb, qq, qbs in qb_rows:
            def _pg(p):
                try: return '%.1f pg' % float(p)
                except (TypeError, ValueError): return '—'
            cells = ['%s (%.0f, %s)' % (n, a, _pg(p)) for a, n, p in qbs] + ['—', '—']
            L.append('| %s | %s | %s | %s | %s |' % (tmc, qb or '—', qq if qq is not None else '—', cells[0], cells[1]))
        L.append('')
        L.append('_proj is per-game WHEN PLAYING (Clay dk_pg): a deep backup can show a high pg over few '
                 'projected games (Carson Beck: 30.8 season pts over 2 games = 15.4 pg). Starter/backup '
                 'status is the ADP order, matching the QB-context rule._')
        L.append('')

    L.append('## 5. Method / provenance notes')
    L.append('')
    L.append('- signals/features/flags inherit team from dk_adp.csv at build time — agreement there proves '
             'the model is NOT drifting/mis-joining; INDEPENDENT confirmation of a move comes from ffdataroma + clay.')
    L.append('- Names joined with `core.fn` + `core.resolve` (pos-aware, first-name-variant-safe, no unsafe guesses); '
             'a resolver miss reports as a presence gap (section 2), never as a fake disagreement.')
    L.append('- The curated defense MOVES dict stays the provenance gold standard; offensive moves that matter '
             'should graduate into a curated offensive analogue over time (add source URLs as they are verified).')
    L.append('- `--strict` exits 1 on: cross-source disagreements, documented-destination mismatches, '
             'stale schedule/QB-context/usage/team25 (the P0 classes).')
    L.append('')
    open(core.P('ROSTER_MOVES_2026.md'), 'w', encoding='utf-8').write('\n'.join(L))

    # ---------- console ----------
    print('ROSTER-MOVE AUDIT -> ROSTER_MOVES_2026.md')
    print(f'  board players            : {len(board)}  (2025 priors: {n_prior})')
    print(f'  cross-source disagreements: {len(disagreements)}')
    for d in disagreements[:12]:
        print('     - %-24s %s  %s' % (d['name'], d['pos'], d['teams']))
    print(f'  moves 2025->2026         : {len(moves)}  (documented {n_doc} | undocumented {n_undoc} | to-FA {n_fa})')
    for m in moves:
        if not m['clean'] or m['status'].startswith('DOCUMENTED'):
            print('     - %-24s %s->%s %s clean=%s' % (m['name'], m['from'], m['to'], m['status'], m['clean']))
    print(f'  doc-destination mismatch : {len(doc_mismatch)}')
    print(f'  stale schedule rows      : {len(sched_bad)}')
    print(f'  stale QB-context teams   : {len(qbctx_bad)}  {qbctx_bad if qbctx_bad else ""}')
    print(f'  movers w/o usage reproj  : {len(unreproj)}  {"(" + mr_note + ")" if mr_note else ""}')
    print(f'  stale team25 rows        : {len(stale25)}')
    print(f'  presence gaps            : ffdataroma {len(nf_ff)} non-FA | clay {len(nf_cl)} non-FA | '
          f'features {len(missing.get("features", []))} | flags {len(missing.get("flags", []))}')
    if strict and p0:
        print(f'\nSTRICT: {p0} P0 finding(s) -> exit 1')
        sys.exit(1)


if __name__ == '__main__':
    main()
