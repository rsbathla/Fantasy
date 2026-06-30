#!/usr/bin/env python3
"""CANONICAL best-ball draft entry — paste a DraftKings OR Underdog board, get the best pick.

    python3 draft.py <Board.txt | clip> [--seat rsbathla] [--platform dk|ud] [--mine "Player A|Player B"]

What it does:
  1. Reads the board text (a file path, or 'clip' for the clipboard).
  2. AUTO-DETECTS the platform (DraftKings vs Underdog) from the board markers — or honors --platform.
  3. Sets the platform BEFORE importing the engine (scoring, lineup, rounds, and playoff-cut structure
     are all platform-specific: DK = 20 rounds / full-PPR / W15-W16-W17 top-50/50/10 gates;
     UD = 18 rounds / half-PPR / win-your-pod gates).
  4. Grades every available pick with the Monte-Carlo survival chain (advancement x playoff title),
     roster-construction aware, and writes decision_dashboard.html.

Underdog note: the board paste auto-detects the drafted set; to be certain which picks are YOURS,
pass --mine "Name|Name|...". (The exact UD copy layout is being finalized against a real paste.)
"""
import os, sys, re, argparse, subprocess, shutil

def _read_clipboard():
    if shutil.which('pbpaste'):
        return subprocess.run(['pbpaste'], capture_output=True, text=True).stdout
    if shutil.which('powershell'):
        return subprocess.run(['powershell', '-NoProfile', '-Command', 'Get-Clipboard'], capture_output=True, text=True).stdout
    try:
        import pyperclip; return pyperclip.paste()
    except Exception:
        raise SystemExit("No clipboard tool available — save the board to a file and pass its path.")

def read_board_text(arg):
    if arg and arg.lower() in ('clip', 'clipboard', '-'):
        t = _read_clipboard()
        if not t or not t.strip():
            raise SystemExit("Clipboard is empty — copy the draft board first (Ctrl+A, Ctrl+C inside the draft room).")
        return t
    if not os.path.exists(arg):
        raise SystemExit(f"Board file not found: {arg}")
    return open(arg, encoding='utf-8', errors='replace').read()

def detect_platform(text):
    """Return 'DK', 'UD', or None (ambiguous -> caller defaults to DK, the proven path)."""
    t = text or ''
    # DraftKings draft room: explicit 'On the clock: Pick N' + 'Round X of 20' + QB/RB/WR/TE column headers.
    if re.search(r'On the clock:\s*Pick\s*\d+', t, re.I):
        return 'DK'
    if re.search(r'Round\s*\d+\s*of\s*20', t, re.I):
        return 'DK'
    # Underdog Best Ball Mania: 18-round drafts; 'Round X of 18' or UD-specific chrome.
    if re.search(r'Round\s*\d+\s*of\s*18', t, re.I) or re.search(r'\bUnderdog\b', t, re.I):
        return 'UD'
    return None

def main():
    ap = argparse.ArgumentParser(description="Paste a DK or UD best-ball board -> best pick.")
    ap.add_argument('board', help="Board file path, or 'clip' for the clipboard")
    ap.add_argument('--seat', default='rsbathla', help="Your draft username/handle (default rsbathla)")
    ap.add_argument('--platform', choices=['dk', 'ud'], default=None, help="Force platform (else auto-detect)")
    ap.add_argument('--mine', default=None, help="Underdog only: your picks, pipe-separated, if auto-detect is uncertain")
    ap.add_argument('--no-open', action='store_true', help="Don't open the dashboard in a browser (headless)")
    a = ap.parse_args()

    txt = read_board_text(a.board)
    plat = (a.platform or detect_platform(txt) or 'DK').upper()
    os.environ['BB_PLATFORM'] = plat
    if a.mine:
        os.environ['BB_MINE'] = a.mine
    print(f"platform: {plat}" + (" (auto-detected)" if not a.platform else " (forced)"))

    HERE = os.path.dirname(os.path.abspath(__file__))
    ENG = os.path.join(HERE, 'engine')
    sys.path.insert(0, ENG)
    # write the board to a temp file run_live can read (keeps its retry-safe IO), then grade
    import time
    t0 = time.time()
    import run_live
    tree = run_live.run(a.board if os.path.exists(str(a.board)) else _stash(txt, ENG), a.seat)
    hl = tree.get('headline', {})
    print(f"\n=== BEST PICK: {hl.get('take')}   dTitle={hl.get('dTitle')}  dAdv={hl.get('dAdv')} ===")
    branches = tree.get('tree', {}).get('branches', [])
    print(f"branches: {len(branches)} | board {len(tree.get('board', []))} | {time.time()-t0:.0f}s")

    sys.path.insert(0, HERE)
    import build_decision_dashboard as bdd
    out = os.path.join(HERE, 'decision_dashboard.html')
    bdd.write_dashboard(tree, out, src=f"{plat} live draft")
    print(f"dashboard: {out}")
    if not a.no_open:
        try:
            import webbrowser; webbrowser.open('file://' + out)
        except Exception:
            pass

def _stash(txt, eng):
    p = os.path.join(eng, '_draft_paste.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(txt)
    return p

if __name__ == '__main__':
    main()
