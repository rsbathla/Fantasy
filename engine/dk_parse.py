#!/usr/bin/env python3
"""Parser for the LIVE DraftKings best-ball draft-room board (Ctrl+C of the page).
Robust to layout variants: player rows may be "Name / POS / TEAM / (BYE x)" OR "Name / POS ● TEAM",
and names may be abbreviated ("K. Walker III") or full ("Kenneth Walker III"). We detect each drafted
player by its POS/TEAM marker line and take the player NAME as the preceding line. -> draft state."""
import re

def _norm(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n)
    n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())

POS={'QB','RB','WR','TE','FLEX','DST','DEF','K'}
_PICK=re.compile(r'^\d+\.\d+$')
_TEAM=re.compile(r'^[A-Z]{2,3}$')
_NOTTEAM={'BYE','QB','RB','WR','TE','DST','DEF'}

def is_dk_live(text):
    return bool(re.search(r'On the clock:\s*Pick\s*\d+', text, re.I)) or 'On The Clock' in text

def _alpha(s):
    return [t for t in re.split(r'[^A-Za-z]+', s) if t]

def _marker(line, nextline):
    """If `line` is a POS or POS+TEAM marker, return (pos, team_or_None_from_this_line, used_next)."""
    toks=_alpha(line)
    if not toks or toks[0] not in POS: return None
    pos=toks[0]; team=None; used_next=False
    if len(toks)>=2 and _TEAM.match(toks[1]) and toks[1] not in _NOTTEAM:
        team=toks[1]
    else:
        t2=_alpha(nextline)
        if t2 and _TEAM.match(t2[0]) and t2[0] not in _NOTTEAM:
            team=t2[0]; used_next=True
    return (pos, team, used_next) if team else (pos, None, False)

def _expand(name, pos, team, idx):
    toks=_norm(name).split()
    if not toks: return None
    cands=idx.get((toks[0][:1], toks[-1]), [])
    if not cands: return None
    if len(cands)==1: return cands[0]['name']
    t=[c for c in cands if c.get('team')==team]
    if len(t)==1: return t[0]['name']
    pool=t or cands
    tp=[c for c in pool if c.get('pos')==pos]
    return (tp or pool)[0]['name']

def parse_dk_board(text, me, board):
    lines=[l.strip() for l in text.splitlines() if l.strip()]
    n=len(lines)
    idx={}
    for p in board:
        nm=_norm(p['name']).split()
        if nm: idx.setdefault((nm[0][:1], nm[-1]), []).append(p)
    cur_pick=None; rnd=None
    for l in lines:
        m=re.search(r'On the clock:\s*Pick\s*(\d+)', l, re.I)
        if m: cur_pick=int(m.group(1))
        m=re.search(r'Round\s*(\d+)\s*of', l, re.I)
        if m and rnd is None: rnd=int(m.group(1))
    starts=[i for i in range(n-8) if lines[i+1]=='QB' and lines[i+3]=='RB' and lines[i+5]=='WR' and lines[i+7]=='TE'
            and lines[i+2].isdigit() and lines[i+4].isdigit() and lines[i+6].isdigit() and lines[i+8].isdigit()]
    drafted=[]; my_roster=[]; my_seat=None; my_counts=None
    for bi,si in enumerate(starts):
        user=lines[si]
        counts={'QB':int(lines[si+2]),'RB':int(lines[si+4]),'WR':int(lines[si+6]),'TE':int(lines[si+8])}
        end=starts[bi+1] if bi+1<len(starts) else n
        first_label=None
        mi=si+9
        while mi<end:
            l=lines[mi]
            if _PICK.match(l) and first_label is None: first_label=l
            mk=_marker(l, lines[mi+1] if mi+1<end else '')
            if mk and mk[1]:                                   # POS + TEAM marker -> a drafted player
                pos,team,used=mk
                name=lines[mi-1] if mi-1>=si+9 else None
                if name and not _PICK.match(name) and not name.isdigit() and not _alpha(name)[:1]==[pos]:
                    full=_expand(name,pos,team,idx)
                    if full:
                        drafted.append(full)
                        if user==me: my_roster.append(full)
                mi += 2 if used else 1
                continue
            mi+=1
        if user==me:
            my_counts=counts
            if first_label: my_seat=int(first_label.split('.')[1])
    # de-dup my_roster preserving order
    seen=set(); my_roster=[x for x in my_roster if not (x in seen or seen.add(x))]
    gone={_norm(x) for x in drafted}
    available=[p['name'] for p in board if _norm(p['name']) not in gone]
    if rnd is None and cur_pick: rnd=(cur_pick-1)//12+1
    if not my_seat and cur_pick: my_seat=((cur_pick-1)%12)+1
    return {'pick':cur_pick,'round':rnd,'seat':my_seat,'my_roster':my_roster,
            'counts':my_counts or {'QB':0,'RB':0,'WR':0,'TE':0},'available':available,
            'n_drafted':len(drafted),'n_teams':len(starts)}

if __name__=='__main__':
    import bbengine as bb, sys
    txt=open(sys.argv[1] if len(sys.argv)>1 else 'fixtures/dk_full_board.txt',encoding='utf-8',errors='replace').read()
    st=parse_dk_board(txt,'rsbathla',bb.load_board())
    print('pick',st['pick'],'round',st['round'],'seat',st['seat'],'teams',st['n_teams'],'drafted',st['n_drafted'])
    print('MY ROSTER:',st['my_roster'],'| counts',st['counts'])
