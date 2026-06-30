#!/usr/bin/env python3
"""flagkit/engine.py — the ONE shared boom-flag engine.

This owns every piece of scaffolding that build_flags_QB/RB/WR/TE/DST.py each
copy-paste today (~150 lines × 5): player iteration (adp order), the per-week
activation loop, BYE/FA handling, grading, record/week assembly, and the verified write.

A position supplies ONLY its semantics via a small `model` module. Required hooks:

    model.context(k, v, gl, bd)      -> profile dict (position-specific feature extraction)
    model.base(v, posbase, profile)  -> (base_float, hist_bool)
    model.skill_flags(profile)       -> list   (the position's {f,d,amp} dicts)
    model.line(profile)              -> str
    model.empirical(k, gl, bd)       -> str
    model.opp_data(opp_code)         -> dict    (per-week opponent inputs)

  ...plus the per-week activation, in EITHER style:

    (a) STATIC conditions  (DST-style: independent flag checks)
        model.conditions(profile) -> list of {"key","mult","fn"}; fn(opp_data, week_ctx) -> bool
        Engine evaluates each in order; `of` = len(conditions); `lit` = #fired.

    (b) FUNCTIONAL activation  (QB/RB/WR/TE-style: inline per-week logic / suppressors)
        model.activate(profile, base, skill_flags, opp_data, week_ctx)
            -> (flags, mults, of_total)            # lit defaults to len(flags)
            -> (flags, mults, of_total, lit)       # 4-tuple when the displayed flag list
                                                   #   and the lit-count differ (WR shows
                                                   #   suppressors in `flags` but excludes
                                                   #   them from `lit`)
        `activate` takes precedence over `conditions` if both are defined.

  OPTIONAL hooks (each defaults to the original DST/QB behavior, so positions that don't
  define them are unaffected — this is why DST/QB stay byte-identical):

    model.adp(v)            -> adp value to store          (default: v.get('adp'))
                              RB rounds: round((v.get('adp') or 999), 2)
    model.bye_of(profile)   -> the `of` on scheduled BYE   (default: 0)
                              RB/TE carry the player's of_total; DST/QB/WR use 0.
    model.empty_schedule(profile) -> 'BYE' | 'FA' | None   (default: None)
                              For players whose team has no schedule (free agents),
                              synthesize 18 sentinel weeks: 'BYE' (of = bye_of, RB/TE)
                              or 'FA' (of = 0, WR). None = emit nothing (DST/QB).

Grading and serialization reuse the EXISTING, backtest-calibrated paths
(boom_lib.prob / boom_lib.label / boom_lib.write, via flag_engine). A migrated builder
is therefore byte-for-byte identical to the legacy one — verified by diffing
boom/flags_<POS>.json before/after.
"""
import boom_lib
import flag_engine


def build(pos, model, *, sources=None, write=True):
    sm, gl, sch, de, bd = sources if sources is not None else boom_lib.load()
    posbase = bd['posbase']
    use_activate = hasattr(model, 'activate')
    adp_fn = getattr(model, 'adp', None)
    bye_of_fn = getattr(model, 'bye_of', None)
    empty_fn = getattr(model, 'empty_schedule', None)
    out = {}

    for k in boom_lib.players(sm, pos):          # adp order — identical to legacy
        v = sm[k]
        prof = model.context(k, v, gl, bd)
        base, hist = model.base(v, posbase, prof)
        skill_flags = model.skill_flags(prof)
        line = model.line(prof)
        empirical = model.empirical(k, gl, bd)
        team = v.get('team', '')
        conditions = None if use_activate else model.conditions(prof)
        bye_of = bye_of_fn(prof) if bye_of_fn else 0

        def bye(wk):
            return {"wk": wk, "opp": "BYE", "home": None, "dome": None,
                    "p": None, "lab": "BYE", "lit": 0, "of": bye_of, "flags": []}

        def fa(wk):
            return {"wk": wk, "opp": None, "home": None, "dome": None,
                    "p": None, "lab": "FA", "lit": 0, "of": 0, "flags": []}

        sched = sch.get(team, [])
        weeks = []
        if not sched and empty_fn:
            kind = empty_fn(prof)
            mk = fa if kind == 'FA' else bye
            weeks = [mk(wk) for wk in range(1, 19)]      # 18 synthetic sentinel weeks
        else:
            for w in sched:
                if w['opp'] == 'BYE':
                    weeks.append(bye(w['wk']))
                    continue
                opp_d = model.opp_data(w['opp'])
                week_ctx = {"home": w.get('home'), "dome": w.get('dome'), "opp": w['opp']}
                if use_activate:
                    res = model.activate(prof, base, skill_flags, opp_d, week_ctx)
                    if len(res) == 4:
                        flags, mults, of, lit = res
                    else:
                        flags, mults, of = res
                        lit = len(flags)
                else:
                    flags, mults = [], []
                    for c in conditions:
                        try:
                            active = c['fn'](opp_d, week_ctx)
                        except Exception:
                            active = False
                        if active:
                            flags.append(c['key'])
                            mults.append(c['mult'])
                    of = len(conditions)
                    lit = len(flags)
                p_int, lab = flag_engine.grade(base, mults)   # = boom_lib.prob + boom_lib.label
                weeks.append(flag_engine.week(
                    w['wk'], w['opp'],
                    bool(w.get('home')) if w.get('home') is not None else False,
                    bool(w.get('dome')) if w.get('dome') is not None else False,
                    p_int, lab, lit, of, flags))

        out[k] = flag_engine.record(
            v['name'], pos, team, (adp_fn(v) if adp_fn else v.get('adp')),
            int(round(base * 100)), hist, v.get('n_games', 0), v.get('boom_games', 0),
            skill_flags, line, weeks, empirical)

    if write:
        boom_lib.write(pos, out)
    return out
