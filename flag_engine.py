#!/usr/bin/env python3
"""flag_engine — the shared scaffolding the 5 flag builders each re-implement (the audit found
the per-week condition encoded 3 incompatible ways and write() handled 3 ways). This is the
canonical OUTPUT contract + grading, so a migrated builder carries only its position-specific
flag SEMANTICS. It is the single source of the schema that validate_boom enforces today;
migrating the 5 builders to call record()/week()/grade() is the gated mechanical follow-up.

  grade(base, mults) -> (p_int 0-100, label)   # one path via boom_lib (shrink-aware + capped)
  week(...) -> 9-key week dict   bye_week/fa_week -> sentinels
  record(...) -> 12-key player dict
  enforce_min_flags(lit_flags, candidates, k=3) -> lit_flags padded toward k
"""
import boom_lib

WEEK_KEYS = ('wk', 'opp', 'home', 'dome', 'p', 'lab', 'lit', 'of', 'flags')
REC_KEYS = ('name', 'pos', 'team', 'adp', 'base', 'hist', 'n_games', 'boom_games',
            'skill_flags', 'line', 'weeks', 'empirical')

def grade(base, mults):
    """base (0-1) x shrunk mults -> (p as 0-100 int, label). The ONE grading path."""
    p = boom_lib.prob(base, mults)            # shrink-aware + capped in boom_lib
    return round(p * 100), boom_lib.label(p, base)

def week(wk, opp, home, dome, p, lab, lit, of, flags):
    return {'wk': wk, 'opp': opp, 'home': home, 'dome': dome, 'p': p,
            'lab': lab, 'lit': lit, 'of': of, 'flags': list(flags)}

def bye_week(wk): return week(wk, 'BYE', None, None, None, 'BYE', 0, 0, [])
def fa_week(wk):  return week(wk, None, None, None, None, 'FA', 0, 0, [])

def record(name, pos, team, adp, base, hist, n_games, boom_games, skill_flags, line, weeks, empirical):
    return {'name': name, 'pos': pos, 'team': team, 'adp': adp, 'base': base, 'hist': hist,
            'n_games': n_games, 'boom_games': boom_games, 'skill_flags': skill_flags,
            'line': line, 'weeks': weeks, 'empirical': empirical}

def enforce_min_flags(lit_flags, candidates, k=3):
    """The '>=3 flags' rule (QB/WR did it as an if-cascade, RB as a while-loop): one impl."""
    out = list(lit_flags)
    for c in candidates:
        if len(out) >= k:
            break
        if c not in out:
            out.append(c)
    return out

if __name__ == '__main__':
    w = week(1, 'KC', True, False, 40, 'GOOD', 3, 8, ['a', 'b'])
    assert tuple(w) == WEEK_KEYS, tuple(w)
    r = record('X', 'WR', 'LAR', 12.0, 30, True, 8, 4, [], 'line', [w], 'emp')
    assert tuple(r) == REC_KEYS, tuple(r)
    assert tuple(bye_week(7)) == WEEK_KEYS and bye_week(7)['lab'] == 'BYE'
    p, lab = grade(0.30, [1.5]); assert 0 <= p <= 100
    assert enforce_min_flags(['a'], ['a', 'b', 'c', 'd']) == ['a', 'b', 'c']
    print(f"flag_engine self-test OK: schema (week/record) + grade(0.30,[1.5])={p},{lab} + min_flags")
