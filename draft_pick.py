#!/usr/bin/env python3
"""Paste a DK draft board (.txt) -> auto-read who's gone + your roster -> run the draft assistant.
Handles the LIVE DK in-draft layout (player names present) and falls back to ADP resolution if only pos/team shown.
Usage:  python draft_pick.py Board.txt --seat rsbathla   [--portfolio "BAL@CIN:5,..."] [--n 10]
        python draft_pick.py clip --seat rsbathla        (reads the system clipboard: macOS/Windows/pyperclip)
"""
import re, sys, subprocess, argparse, os, pandas as pd
import os as _os, glob as _glob, shutil as _sh
HERE=_os.path.dirname(_os.path.abspath(__file__))
_cands=[_os.path.join(HERE,x) for x in ("dk_adp.csv","DkPreDraftRankings(2).csv","DkPreDraftRankings.csv")]
_cands+=sorted(_glob.glob(_os.path.join(HERE,"DkPreDraftRankings*.csv")))
ADP_FILE=next((c for c in _cands if _os.path.exists(c)), _cands[0])
def _read_clipboard():
    """Cross-platform clipboard read: macOS pbpaste, Windows PowerShell, else pyperclip."""
    if _sh.which('pbpaste'):
        return subprocess.run(['pbpaste'],capture_output=True,text=True).stdout
    if _sh.which('powershell'):
        return subprocess.run(['powershell','-NoProfile','-Command','Get-Clipboard'],capture_output=True,text=True).stdout
    try:
        import pyperclip; return pyperclip.paste()
    except Exception:
        raise SystemExit("Couldn't read clipboard; save the board to Board.txt and run: python draft_pick.py Board.txt --seat rsbathla")
ap=argparse.ArgumentParser()
ap.add_argument('board'); ap.add_argument('--seat',required=True)
ap.add_argument('--adp',default=ADP_FILE); ap.add_argument('--portfolio',default=''); ap.add_argument('--n',type=int,default=10)
ap.add_argument('--teams',type=int,default=12); ap.add_argument('--pick',type=int,default=0)
a=ap.parse_args()
if a.board.lower()=='clip':
    txt=_read_clipboard()
else:
    txt=open(a.board, errors='ignore').read()
txt=txt.replace(chr(13)+chr(10),chr(10)).replace(chr(13),chr(10))
if txt.lstrip().startswith('{\\rtf'):
    try:
        from striprtf.striprtf import rtf_to_text; txt=rtf_to_text(txt)
    except Exception:
        txt=re.sub(r'\\par[d]?|\\line','\n',txt); txt=re.sub(r'\\[a-zA-Z]+-?\d* ?','',txt); txt=re.sub(r'[{}]','',txt)

heads=re.findall(r'\n([A-Za-z0-9_\.]+)\s*\nQB\s*\n\d+\s*\nRB\s*\n\d+\s*\nWR\s*\n\d+\s*\nTE\s*\n\d+', txt)
if a.seat.isdigit(): seat=int(a.seat)
elif a.seat in heads: seat=heads.index(a.seat)+1
else:
    seat=next((i+1 for i,h in enumerate(heads) if a.seat.lower() in h.lower()), None)
if seat is None: print("could not find seat",a.seat,"in",heads); sys.exit(1)

named=re.findall(r'(\d+)\.(\d+)\s*\n\s*(\d+)\s*\n\s*(.+?)\s*icon\s*\n\s*(QB|RB|WR|TE)\s*\n\s*([A-Z]{2,3})\s*\n\s*\(BYE', txt)
gone=[]; bypick={}
if named:
    for rnd,inr,ov,name,pos,team in named:
        nm=name.strip(); gone.append(nm); bypick[int(ov)]=nm
else:
    picks=sorted(set((int(o),p,t) for _,_,o,p,t in
        re.findall(r'(\d+)\.(\d+)\s*\n\s*(\d+)\s*\n\s*(QB|RB|WR|TE)\s*\n\s*([A-Z]{2,3})', txt)))
    adp=pd.read_csv(a.adp); adp=adp[['Name','Position','ADP','Team']].dropna(subset=['ADP']); adp['Team']=adp['Team'].replace({'LA':'LAR'})
    taken=set()
    for ov,pos,team in picks:
        c=adp[(adp.Position==pos)&(adp.Team==team)&(~adp.Name.isin(taken))]
        if len(c):
            nm=c.assign(d=(c.ADP-ov).abs()).sort_values('d').iloc[0]['Name']; taken.add(nm); gone.append(nm); bypick[ov]=nm

def ov_for(s,r,T=a.teams): return (r-1)*T + (s if r%2==1 else T+1-s)
my_ov={ov_for(seat,r) for r in range(1,21)}
mine=[bypick[o] for o in sorted(my_ov) if o in bypick]
next_pick=a.pick if a.pick else min([o for o in sorted(my_ov) if o not in bypick] or [max(bypick)+1 if bypick else 1])
print(f"seat {seat} ({heads[seat-1] if seat<=len(heads) else a.seat}) | {len(gone)} drafted | your {len(mine)} picks | next pick #{next_pick}")
print("your roster:", ", ".join(mine) if mine else "(none yet)")
cmd=[sys.executable,_os.path.join(HERE,'draft_assistant.py'),'--pick',str(next_pick),'--mine',",".join(mine),'--gone',",".join(gone),'--n',str(a.n)]
if a.portfolio: cmd+=['--portfolio',a.portfolio]
print("\n--- recommendations ---")
subprocess.run(cmd, cwd=HERE)
