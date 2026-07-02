#!/usr/bin/env python3
"""Thin runnable wrapper over the best-ball grader for headless / chat use.

    python3 bb_grade.py <board.txt> [--mine "Name|Name"] [--seat rsbathla] [--platform dk|ud]

It runs the proven draft.py pipeline headless (auto-detects DK vs UD, grades every
available pick through the Monte-Carlo survival chain, writes decision_dashboard.html)
and then prints a compact, readable decision summary to stdout — so you get the answer
in text without opening the 600 KB dashboard, plus the dashboard for full detail.

Nothing new is modeled here; this only orchestrates draft.py and formats its output.
"""
import os, sys, json, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.join(HERE, 'engine', 'live_tree.json')
DASH = os.path.join(HERE, 'decision_dashboard.html')


def _fmt_delta(x):
    if x is None:
        return "  n/a"
    return f"{x:+.1f}" if isinstance(x, (int, float)) else str(x)


def _roster_line(state):
    r = state.get('roster', [])
    if not r:
        return "(empty)"
    return ", ".join(f"{p['name']} ({p['pos']})" for p in r)


def _construction_line(con):
    counts = con.get('counts', {})
    tgts = con.get('targets', {})
    parts = []
    for pos in ('QB', 'RB', 'WR', 'TE'):
        parts.append(f"{pos} {counts.get(pos, 0)}/{tgts.get(pos, '?')}")
    anc = con.get('anchor', 'none')
    byes = con.get('byes', [])
    bye_s = "/".join(str(int(b)) for b in byes if b) if byes else "-"
    return " · ".join(parts) + f" · anchor {anc} · byes {bye_s}"


def _print_branch(br, indent="   "):
    take = br.get('take'); pos = br.get('pos'); team = br.get('team')
    cond = br.get('cond', '')
    dt = br.get('dTitle'); da = br.get('dAdv')
    print(f"{indent}{cond}")
    print(f"{indent}  → {take} ({pos}, {team})   ΔTitle {_fmt_delta(dt)}  ΔAdv {_fmt_delta(da)}")
    then = br.get('then') or {}
    sub = then.get('branches', [])
    if sub:
        lbl = then.get('label', 'look-ahead')
        print(f"{indent}  ↳ {lbl}:")
        for s in sub[:2]:
            st, sp = s.get('take'), s.get('pos')
            print(f"{indent}      {s.get('cond','')} — {st} ({sp}) ΔTitle {_fmt_delta(s.get('dTitle'))}")


def _strategy_lines(t):
    """Compact 5-10 line strategy summary from tree['strategy']."""
    sp = t.get('strategy')
    if not sp:
        return []
    if sp.get('error') and not sp.get('slot_detected'):
        return [f"   Strategy: {sp['error']}"]
    bf = sp.get('best_fit') or {}
    lines = []
    slot = sp.get('slot')
    adh = bf.get('adherence', '?')
    sid = bf.get('id', '?')
    sname = bf.get('name', '')
    score = bf.get('score', 0)
    lines.append(f"   Slot S{slot} | Best-fit: {sid} — {sname.split(',')[0]}")
    lines.append(f"   Adherence: {adh} (score {score:.1f})")
    # Live targets
    targets = sp.get('live_targets', [])
    avail_tgts = [t2 for t2 in targets if t2.get('available')]
    if avail_tgts:
        names = [f"{t2['name']}{'*' if t2.get('synergy') else ''}{'[S]' if t2.get('stack_pick') else ''}" for t2 in avail_tgts[:4]]
        lines.append(f"   This-round targets (avail): {', '.join(names)}")
    else:
        lines.append(f"   This-round targets: all gone or none defined")
    # Stack status
    for ss in (sp.get('stack_status') or [])[:2]:
        team = ss.get('team', '?')
        tier = ss.get('tier', '?')
        held = ss.get('held', [])
        avail_rem = ss.get('available_remaining', [])
        parts = []
        if held:
            parts.append(f"held: {', '.join(held[:2])}")
        if avail_rem:
            parts.append(f"avail: {', '.join(avail_rem[:2])}")
        elif ss.get('remaining'):
            parts.append("(stack pieces gone)")
        lines.append(f"   Stack {team} ({tier}): {' | '.join(parts) if parts else 'no data'}")
    # Checkpoint warnings
    for cp in (sp.get('checkpoints') or [])[:2]:
        imp = cp.get('impossible', [])
        risk = cp.get('at_risk', [])
        if imp:
            lines.append(f"   ⚠ R{cp['round']} IMPOSSIBLE: {', '.join(imp)}")
        elif risk:
            lines.append(f"   ⚠ R{cp['round']} AT RISK: {', '.join(risk)}")
    # Floor warnings
    for fw in (sp.get('floor_warnings') or [])[:2]:
        lines.append(f"   ⚠ {fw}")
    return lines


def summarize():
    if not os.path.exists(TREE):
        print("(no live_tree.json — the grade did not complete)")
        return
    t = json.load(open(TREE, encoding='utf-8'))
    state = t.get('state', {}); con = t.get('construction', {}); hl = t.get('headline', {})
    plat = os.environ.get('BB_PLATFORM', '?')
    bar = "═" * 62
    print("\n" + bar)
    print(f" BEST BALL DRAFT GRADE — {plat}")
    print(bar)
    print(f" Pick {state.get('pick','?')} · Round {state.get('round','?')} · Seat {state.get('seat','?')}")
    print(f" Your roster ({len(state.get('roster',[]))}): {_roster_line(state)}")
    print(f" Construction: {_construction_line(con)}")
    print("\n──── BEST PICK " + "─" * 47)
    print(f" → {hl.get('take','?')}")
    print(f"   ΔTitle {_fmt_delta(hl.get('dTitle'))}   ΔAdvance {_fmt_delta(hl.get('dAdv'))}")
    why = hl.get('why', '')
    if why:
        print(f"   Why: {why}")
    branches = t.get('tree', {}).get('branches', [])
    if branches:
        print("\n──── DECISION TREE " + "─" * 43)
        for br in branches[:3]:
            _print_branch(br)
            print()
    print("\n──── STRATEGY (advisory) " + "─" * 37)
    for ln in _strategy_lines(t):
        print(ln)
    print(bar)
    print(f" Full dashboard (signals · stacks · scouting): decision_dashboard.html")
    print(bar + "\n")


def main():
    ap = argparse.ArgumentParser(description="Grade a best-ball board (headless) + print a summary.")
    ap.add_argument('board', help="Path to the board text file")
    ap.add_argument('--mine', default=None, help='Underdog: your picks, pipe-separated (recommended for UD)')
    ap.add_argument('--seat', default='rsbathla', help="Your draft handle (default rsbathla)")
    ap.add_argument('--platform', choices=['dk', 'ud'], default=None, help="Force platform (else auto-detect)")
    ap.add_argument('--fast', action='store_true',
                    help="On-the-clock mode: ~10s. 600 sims + shortlist 10 + no look-ahead subtree. "
                         "Keeps the same top pick as the full grade on tested boards; only the look-ahead 'then' advice is dropped.")
    ap.add_argument('--open', dest='open_dash', action='store_true',
                    help="Open decision_dashboard.html in your browser when done (used by the one-click runner).")
    a = ap.parse_args()

    is_clip = str(a.board).lower() in ('clip', 'clipboard', '-')
    if not is_clip and not os.path.exists(a.board):
        raise SystemExit(f"Board file not found: {a.board}")

    if a.fast:
        # env overrides read by engine/decision_tree.py + run_live.py at import (defaults otherwise unchanged).
        # Tuned: dropping the look-ahead (BB_PLIES=1) is free — it never changes the current pick, only the
        # 'then' subtree — and 600 sims held the same top pick as 1000 in testing; 400 was too noisy (flipped it).
        os.environ.update({'BB_TREE_NS': '600', 'BB_SHORTLIST_PICK': '10', 'BB_PLIES': '1', 'BB_GRADED_N': '5'})
        print("fast mode ON: 600 sims · shortlist 10 · no look-ahead (~10s)")

    cmd = [sys.executable, os.path.join(HERE, 'draft.py'), a.board, '--no-open', '--seat', a.seat]
    if a.mine:
        cmd += ['--mine', a.mine]
    if a.platform:
        cmd += ['--platform', a.platform]

    # run the proven pipeline; stream its progress lines through
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # capture the platform draft.py detected so the summary header is right
    for line in proc.stdout.splitlines():
        if line.startswith('platform:'):
            os.environ['BB_PLATFORM'] = line.split(':', 1)[1].strip().split()[0]
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"grade failed (exit {proc.returncode})")

    summarize()
    print(f"dashboard written: {DASH}")
    if a.open_dash:
        try:
            import webbrowser; webbrowser.open('file://' + DASH)
        except Exception:
            pass


if __name__ == '__main__':
    main()
