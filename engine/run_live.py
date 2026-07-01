#!/usr/bin/env python3
"""Production entry: DK board (file OR clipboard) -> parsed state -> 12-team field -> decision tree +
RICH payload (per-player signals, STACK tags vs your roster, multi-source scouting notes) -> dashboard.
Usage:  python run_live.py clip rsbathla    |    python run_live.py ..\\Board.txt rsbathla"""
import os, sys, json, subprocess, shutil
import pandas as pd
import bbengine as bb
import decision_tree as dt

_HERE=os.path.dirname(os.path.abspath(__file__)); _REPO=os.path.dirname(_HERE)
_DEFAULT_OUT=os.path.join(_HERE,"live_tree.json")

def _read_clipboard():
    if shutil.which('pbpaste'): return subprocess.run(['pbpaste'],capture_output=True,text=True).stdout
    if shutil.which('powershell'): return subprocess.run(['powershell','-NoProfile','-Command','Get-Clipboard'],capture_output=True,text=True).stdout
    try:
        import pyperclip; return pyperclip.paste()
    except Exception: raise SystemExit("No clipboard tool. Save the board to a file and pass its path.")

def _board_text(arg):
    if arg and arg.lower() in ('clip','clipboard','-'):
        t=_read_clipboard()
        if not t or not t.strip(): raise SystemExit("Clipboard empty - copy the DK board first (Ctrl+C).")
        return t
    return open(arg,encoding="utf-8",errors="replace").read()

def reconstruct_field(state, board, me='rsbathla', teams=12):
    gradeable={p['name'] for p in board if p['proj'] is not None}
    grad_keys={bb._norm(n) for n in gradeable}
    avail=set(state['available']); mine=set(state['my_roster'])
    drafted_opp=[p for p in board if p['proj'] is not None and p['name'] not in avail and p['name'] not in mine]
    drafted_opp.sort(key=lambda p:(p['adp'] if p['adp'] else 9999))
    rosters={me:[n for n in state['my_roster'] if n in gradeable]}
    dropped=[n for n in state['my_roster'] if bb._norm(n) not in grad_keys]
    opps=[f'opp{i}' for i in range(1,teams)]
    for o in opps: rosters[o]=[]
    for i,p in enumerate(drafted_opp): rosters[opps[i%len(opps)]].append(p['name'])
    return rosters,dropped

def _num(v):
    try: f=float(v); return round(f,2) if f==f else None
    except Exception: return None

def _name_in_text(name, text):
    """True if a distinctive part (len>2) of the player's name appears in text. Rejects the ~50% of
    qual_summary.top_quote rows that are viral/comparative tweets stapled to the wrong player
    (e.g. a 'rewatching the Chicago Bears' quote attached to Josh Allen / Patrick Mahomes)."""
    t=str(text).lower()
    return any(part in t for part in bb._norm(name).split() if len(part)>2)

def _load_signals():
    sig=pd.read_csv(os.path.join(_REPO,'draft_board_signals.csv')); sig['k']=sig['name'].map(bb._norm)
    S={r['k']:r for _,r in sig.iterrows()}
    def load_kv(fn, col):
        out={}
        try:
            d=pd.read_csv(os.path.join(_REPO,fn))
            for _,r in d.iterrows():
                v=str(r.get(col,'')).strip()
                if v and v.lower()!='nan': out[bb._norm(r['name'])]=r
        except Exception: pass
        return out
    notes=load_kv('bestball_notes.csv','bestball_note')
    qual=load_kv('qual_summary.csv','summary')
    overl={}
    try:
        d=pd.read_csv(os.path.join(_REPO,'overlays.csv'))
        for _,r in d.iterrows():
            overl.setdefault(bb._norm(r['name']),[]).append({'type':str(r.get('type','')).strip(),'note':str(r.get('note','')).strip()})
    except Exception: pass
    # USAGE / ROLE profile (layer2_player_params) + MODEL card (fusion_table) - the deep data
    usage={}
    try:
        u=pd.read_csv(os.path.join(_REPO,'pipeline','layer2_player_params.csv'))
        for _,r in u.iterrows(): usage[bb._norm(r['name'])]=r
    except Exception: pass
    fus={}
    try:
        f=pd.read_csv(os.path.join(_REPO,'fusion_table.csv'))
        for _,r in f.iterrows(): fus[bb._norm(r['name'])]=r
    except Exception: pass
    # FILM notes (video_notes.csv) + analyst CONVICTION (qual_signal.csv) - the two missing curated layers
    film={}
    try:
        v=pd.read_csv(os.path.join(_REPO,'video_notes.csv'))
        for _,r in v.iterrows(): film[bb._norm(r['name'])]=r
    except Exception: pass
    conv={}
    try:
        c=pd.read_csv(os.path.join(_REPO,'qual_signal.csv'))
        for _,r in c.iterrows(): conv[bb._norm(r['name'])]=r
    except Exception: pass
    ptw={}
    try:
        _id=json.load(open(os.path.join(_REPO,'intel_data.json'),encoding='utf-8',errors='replace'))
        for _p in _id.get('players',[]):
            _ab=_p.get('about',[])
            if _ab: ptw[bb._norm(_p['name'])]={'tweets':_ab,'n':_p.get('n_about',len(_ab))}
    except Exception: pass
    psp={}
    try: psp=json.load(open(os.path.join(_REPO,'player_splits.json'),encoding='utf-8',errors='replace'))
    except Exception: pass
    return S,notes,qual,overl,usage,fus,film,conv,ptw,psp

def _stack_index(roster_detail):
    """teams where I hold a QB / a pass-catcher, and the W17 games my roster is in (for bring-backs)."""
    qb_teams={}; catch_teams={}; w17games={}
    for r in roster_detail:
        t=r.get('team'); p=r.get('pos'); g=r.get('w17')
        if p=='QB': qb_teams.setdefault(t,[]).append(r['name'])
        elif p in ('WR','TE'): catch_teams.setdefault(t,[]).append(r['name'])
        if g and g not in ('nan','None'): w17games.setdefault(g,[]).append(r['name'])
    return qb_teams,catch_teams,w17games

def _stack_tag(pos,team,w17,qb_teams,catch_teams,w17games):
    if pos=='QB' and team in catch_teams:
        return "🔗 QB-stack → "+", ".join(catch_teams[team][:2])
    if pos in ('WR','TE') and team in qb_teams:
        return "🔗 stacks your "+qb_teams[team][0]+" (QB)"
    if pos in ('WR','TE') and team in catch_teams:
        return "🔗 onslaught w/ "+catch_teams[team][0]
    if pos=='RB' and team in (set(qb_teams)|set(catch_teams)):
        return "🔗 same team as "+ (qb_teams.get(team) or catch_teams.get(team))[0]
    if w17 and w17 in w17games:
        mates=[m for m in w17games[w17] if True]
        return "↩ bring-back ("+w17+")" if mates else None
    return None

def enrich(tree, st, board, me):
    S,notes,qual,overl,usage,fus,film,conv,ptw,psp=_load_signals()
    pu={bb._norm(p['name']):p.get('playoff_up') for p in board}
    deltas={}
    def harvest(node):
        for b in node.get('branches',[]):
            if b.get('take'): deltas[bb._norm(b['take'])]={'dTitle':b.get('dTitle'),'dAdv':b.get('dAdv'),'dW17':b.get('dW17')}
            if b.get('then'): harvest(b['then'])
    harvest(tree.get('tree',{}))
    # roster detail first (needed for stack index)
    def base_row(nm):
        k=bb._norm(nm); s=S.get(k); d={'name':nm,'k':k}
        if s is not None:
            d.update(dict(pos=s['pos'],team=s['team'],adp=_num(s['adp']),rank=_num(s['merged_rank']),
                proj=_num(s['proj_pg']),ceiling=_num(s['p95']),ceil_pct=_num(s['ceil_pct']),cv=_num(s['cv']),
                spike=_num(s['spike']),bye=_num(s['bye']),w15=str(s['w15_opp']),w16=str(s['w16_opp']),
                w17=str(s['w17_game']),w17rank=_num(s['w17_blowup_rank']),adv_pct=_num(s['adv_pct'])))
            v,r=d.get('adp'),d.get('rank'); d['value']=round(v-r,1) if (v is not None and r is not None) else None
        d['playoff_up']=round(pu[k],3) if pu.get(k) is not None else None
        return d
    tree['roster_detail']=[base_row(n) for n in st['my_roster']]
    qb_teams,catch_teams,w17games=_stack_index(tree['roster_detail'])
    # DEEP-note set: the next ~24 available by rank + my roster + any tree-pick player get the FULL
    # film/tweet/quote treatment (with larger caps); everyone else keeps the compact signals
    # (2026 outlook, conviction, usage, model). Concentrates depth where it matters + shrinks the file.
    DEEP_N=24
    def _rk(nm):
        sx=S.get(bb._norm(nm))
        try: return float(sx['merged_rank'])
        except Exception: return 9999.0
    _availset=set(st['available'])
    _ranked=sorted([p['name'] for p in board if p['name'] in _availset and p['proj'] is not None and bb._norm(p['name']) in S], key=_rk)
    deep_keys={bb._norm(n) for n in _ranked[:DEEP_N]} | {bb._norm(n) for n in st['my_roster']} | set(deltas.keys())
    def full_row(nm):
        d=base_row(nm); k=d['k']; deep = k in deep_keys
        d['deep']=bool(deep)
        # compact signals kept for EVERY board player
        q=qual.get(k)
        d['scouting']=str(q['summary']) if q is not None else None
        d['flags']=[f for f in overl.get(k,[]) if f['type']]
        d['stack']=_stack_tag(d.get('pos'),d.get('team'),d.get('w17'),qb_teams,catch_teams,w17games)
        u=usage.get(k)
        if u is not None:
            d['usage']={x:_num(u.get(x)) for x in ('carry_pg','carry_share','ypc','tgt_share','catch_rate','ypt','cv_carry','cv_tgt','dk_pg')}
            d['usage']['role']=str(u.get('role'))
        fr=fus.get(k)
        if fr is not None:
            d['model']={x:_num(fr.get(x)) for x in ('value_pctl','proj_pctl','ceiling_pctl','spike_pctl','adv_pctl','run_eff_pctl','rec_eff_pctl','route_eff_pctl','explosive_pctl','oline_pctl','matchup_pctl','boom_pctl','separation_pctl','yac_pctl','sis_value_pctl')}
            d['model']['consensus']=_num(fr.get('consensus')); d['model']['divergence']=_num(fr.get('divergence')); d['model']['n_votes']=_num(fr.get('n_votes'))
        cc=conv.get(k)
        if cc is not None and _num(cc.get('qual_score')) is not None:
            d['conviction']={'score':_num(cc.get('qual_score')),'n_sources':_num(cc.get('n_sources')),
                'n_tweets':_num(cc.get('n_tweets')),'n_categories':_num(cc.get('n_categories'))}
        # HEAVY prose only for the deep set (larger caps so they read fuller)
        if deep:
            tq=str(q['top_quote']) if q is not None else ''
            if tq.strip().lower() not in ('','nan') and _name_in_text(nm,tq): d['quote']=tq
            nt=notes.get(k)
            if nt is not None and _name_in_text(nm,str(nt['bestball_note'])): d['tweet']=str(nt['bestball_note'])[:520]
            vf=film.get(k)
            if vf is not None and str(vf.get('video_note','')).strip().lower() not in ('','nan') and _name_in_text(nm,str(vf['video_note'])):
                d['film']=str(vf['video_note'])[:700]; d['n_clips']=_num(vf.get('n_clips'))
            tf=ptw.get(k)
            if tf and tf.get('tweets'):
                d['tweets']=[{'d':x.get('date'),'h':x.get('handle'),'t':str(x.get('text',''))[:240],'l':x.get('likes')} for x in tf['tweets'][:5]]
                d['n_tweets']=tf.get('n')
            sp=psp.get(k)
            if sp: d['splits']=sp
        if k in deltas: d.update(deltas[k])
        return d
    # re-enrich roster_detail with stack/notes too
    tree['roster_detail']=[full_row(n) for n in st['my_roster']]
    avail=set(st['available'])
    cand=[full_row(p['name']) for p in board if p['name'] in avail and p['proj'] is not None and bb._norm(p['name']) in S]
    cand.sort(key=lambda x:(x.get('rank') or 9999))
    tree['board']=cand[:250]
    cnts=tree['state'].get('counts',{})
    tree['construction']={'counts':cnts,'targets':{'QB':'2-3','RB':'5-6','WR':'8-9','TE':'2-3'},
        'anchor':tree['state'].get('anchor'),'byes':sorted({r['bye'] for r in tree['roster_detail'] if r.get('bye')})}
    return tree

def _write_json_safely(obj, out, tries=3):
    """Compact + atomic + byte-verified write with retries. A truncated/interrupted write can never
    replace the good file; prints a loud stamp so you can confirm THIS writer actually ran."""
    import time
    payload=json.dumps(obj,separators=(',',':'),ensure_ascii=False)   # compact ~25% smaller than indented
    for attempt in range(1,tries+1):
        tmp=out+'.tmp'
        try:
            with open(tmp,'w',encoding='utf-8') as fh:
                fh.write(payload); fh.flush(); os.fsync(fh.fileno())
            with open(tmp,encoding='utf-8') as fh: back=fh.read()
            if len(back)==len(payload):
                json.loads(back)                      # must parse
                os.replace(tmp,out)
                print(f"[write OK v3] {os.path.basename(out)}: {len(payload):,} bytes written+verified (attempt {attempt})")
                return True
            print(f"[write retry {attempt}] read-back {len(back):,}/{len(payload):,} bytes - retrying")
        except Exception as e:
            print(f"[write retry {attempt}] {e}")
        time.sleep(0.3)
    raise SystemExit(f"!! FAILED to write a complete {out} after {tries} tries; previous file left intact. Re-run.")

def run(board_path, me='rsbathla', plies=None, out=None):
    if plies is None: plies=int(os.environ.get('BB_PLIES','2'))  # BB_PLIES=1 (fast) omits the look-ahead subtree
    out=out or _DEFAULT_OUT
    txt=_board_text(board_path)
    try:
        with open(os.path.join(_HERE,'last_board_raw.txt'),'w',encoding='utf-8') as _rf: _rf.write(txt); _rf.flush(); os.fsync(_rf.fileno())
    except Exception: pass
    board=bb.load_board()
    import dk_parse
    if dk_parse.is_dk_live(txt):
        st=dk_parse.parse_dk_board(txt,me,board)
        print(f"[DK live draft board: {st['n_teams']} managers, {st['n_drafted']} drafted]")
        if int(st.get('n_drafted',0))==0 and int(st.get('pick',1))>1:
            raise SystemExit(
                "\n!! No drafted players found in what you copied - nothing was simulated.\n"
                "   The clipboard text looks like the DraftKings site menu (Lobby/Lineups/Balance...),\n"
                "   not the draft-room board.\n"
                "   FIX: in the DK draft room, click inside the draft BOARD area, then Ctrl+A, Ctrl+C,\n"
                "        and re-run. (Your previous dashboard was left untouched.)\n")
    elif os.environ.get('BB_PLATFORM','DK').upper()=='UD':
        import ud_parse
        _mine=os.environ.get('BB_MINE','').split('|') if os.environ.get('BB_MINE') else None
        st=ud_parse.parse_ud_board(txt,me,board,mine=_mine)
        print(f"[Underdog board: {st['n_drafted']} drafted, my roster {len(st['my_roster'])}]")
    else:
        st=bb.parse_board(txt,me)
    rosters,dropped=reconstruct_field(st,board,me)
    drafted_n=len(st['my_roster']); modeled_n=len(rosters[me])
    print(f"state: pick {st['pick']} R{st['round']} seat {st['seat']} | my gradeable roster {modeled_n} | field {sum(len(v) for v in rosters.values())} players over {len(rosters)} teams")
    if dropped: print(f"WARNING: {len(dropped)} drafted players have no sim projection (not modeled): {', '.join(dropped)}")
    tree=dt.build_tree(board,rosters,me,seat=st.get('seat'),plies=plies,pick=st.get('pick'),rnd=st.get('round'))
    tree['state']['modeled_n']=int(modeled_n); tree['state']['drafted_n']=int(drafted_n)
    if dropped: tree['state']['untracked']=list(dropped); tree['state']['dropped']=list(dropped)
    tree=enrich(tree,st,board,me)
    _write_json_safely(tree,out)
    print(f"wrote {out}  (board {len(tree['board'])} w/ notes+stacks, roster {len(tree['roster_detail'])})")
    return tree

if __name__=='__main__':
    bp=sys.argv[1] if len(sys.argv)>1 else os.path.join(_REPO,'Board.txt')
    me=sys.argv[2] if len(sys.argv)>2 else 'rsbathla'
    import time; t0=time.time()
    tree=run(bp,me)
    print(f"\n=== HEADLINE: {tree['headline']['take']}  dTitle={tree['headline'].get('dTitle')} dAdv={tree['headline'].get('dAdv')} ===")
    print(f"branches {len(tree['tree']['branches'])} | board {len(tree['board'])} | built {time.time()-t0:.0f}s")
    try:
        sys.path.insert(0,_REPO)
        import build_decision_dashboard as bdd
        html=os.path.join(_REPO,'decision_dashboard.html')
        bdd.write_dashboard(tree, html, src="in-process from live tree")   # no flaky file round-trip
        print(f"dashboard: {html}")
        import webbrowser; webbrowser.open('file:///'+html.replace('\\','/'))
    except Exception as e: print(f"(auto-build/open skipped: {e})")
