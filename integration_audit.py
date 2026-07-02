#!/usr/bin/env python3
"""INTEGRATION AUDIT -- catches the "layer built but not properly consumed" bug class.

The recurring failure in this project: a layer gets built, later work adds a parallel layer
that *should* consume it, and the wiring silently never happens. Nothing errors; the output still
looks plausible; the signal just isn't there. (Live example: build_scheme_fit.py read only the
`dc_new` flag off the coordinator layer and blanket-regressed every new-DC team to the mean,
ignoring the coordinator-aware man_rate_adj / conf / dc_scheme that lever_count and def_profile
already used. Historical example: build_dossier_deep.py sat orphaned until someone noticed.)

This scanner makes that class LOUD and re-runnable. Five shapes it looks for:
  1. PARTIAL CONSUMPTION -- a layer is read, but its rich fields are ignored.
  2. DIVERGENT LOGIC     -- two consumers of one layer read different fields (one under-uses it).
  3. ORPHANED PRODUCTION -- a builder writes an artifact no builder reads.
  4. SILENT FALLBACK     -- code defaults to mean/league-avg/last-year when better data existed.
  5. FROZEN INPUT        -- a "live" layer is actually a stale snapshot.

Four checks, each written to INTEGRATION_AUDIT.md:
  A. LINEAGE   -- producer->consumer graph; orphans; builders missing from the pipeline runner.
  B. FIELD USE -- per rich artifact, which keys each consumer reads; unused fields; divergences.
  C. INVARIANTS-- curated assertions ("X must honor field Y"), grown as we learn.
  D. FALLBACKS -- fallback/skip counters harvested from every output's _meta, made visible.

Run:  python3 integration_audit.py            # write report + console summary
      python3 integration_audit.py --strict   # exit 1 if any P0 finding (pipeline gate)
Producer map is read from the authoritative pipeline declarations (boom_pipeline.py STAGES and
run_all.py chains) first, then falls back to write-call heuristics, so it is not fooled by reads
through variables/globs.
Data-side companion: audit_roster_moves.py cross-checks every player's TEAM across independent
sources and reconciles 2026 roster moves against curated provenance -> ROSTER_MOVES_2026.md.
"""
import os, re, glob, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIRS = ('NFL-master', 'ffdataroma_draft_guide_export', 'pff_', 'ftn_', 'nfl_pro',
            'FP_SWEEP', 'node_modules', '.git', 'api/', '__pycache__', 'refactor/',
            '_prebuild_backup', '_prune_baseline', 'backup', 'archive/')
SELF = os.path.basename(__file__)
# orchestrators name artifacts for existence-checks/sequencing -- they are NOT field consumers
ORCHESTRATORS = ('run_all.py', 'boom_pipeline.py')
def is_bak(name): return name.startswith('_bak_') or '.bak' in name or name.startswith('_prebuild')

# ---- artifacts that are TERMINAL by design (a missing consumer is expected, not a bug) ----
TERMINAL_RE = [
    r'\.html$', r'\.baseline\.json$', r'\.pre[A-Za-z0-9]+\.json$', r'\.recovered\.json$',
    r'backtest', r'_audit.*\.json$', r'INTEGRATION_AUDIT', r'console_log\.json$',
    r'columns\.json$', r'sample_tree\.json$', r'_upload\.csv$', r'_live\.csv$',
    r'portfolio_', r'_2026\.csv$', r'rankings_2026\.csv$', r'flag_rank_delta\.csv$',
    r'chain_live\.csv$', r'draft_analysis_live\.csv$',
    # -- ORPHAN_TRIAGE 2026-07-02: confirmed TERMINAL by design (human exports / memos / frozen snapshots) --
    r'^analysis/',                  # analysis exports dir (w17_blowup_rank etc. -- one-shot analysis outputs)
    r'profiles_summary\.csv$',      # build_profiles.py human-readable situational matrix (player_profiles.json is the consumed layer)
    r'ud_cheatsheet\.csv$',         # pipeline/build_ud_board.py Underdog draft sheet (deliverable)
    r'video_notes_review\.csv$',    # X-pull review sheet (schema: handle/sentence); the wired film-notes input is video_notes.csv
    r'rookie_weight_opt\.json$',    # woptimize_rookie.py grid-search snapshot; best_W=0.15 hardcoded at apply_rookie_to_statmenu.py:12
    r'rookie_situations\.json$',    # analyze_rookie_situations.py findings memo (draft-capital dominates etc.), not a model input
    r'manzone_tags_cfb\.json$',     # frozen FBS snapshot; build_rookie_manzone_pff.py re-derives fresh from sis_value/pff_receiving_scheme_2025.csv
]
def is_terminal(a): return any(re.search(p, a) for p in TERMINAL_RE)

# ---- CURATED CONSUMPTION the literal-basename scan cannot see (ORPHAN_TRIAGE.md, 2026-07-02) ----
# The refs() scan matches literal basenames in ROOT *.py only, so f-string paths
# (f'cfb_receiving_value_{season}.csv'), suffix swaps (.replace('.csv','_2024.csv')) and engine/ +
# pipeline/ subdir scripts are invisible to it. Each entry here is RE-VERIFIED at audit time: the
# named consumer file must still contain `needle`, else the artifact drops back to being an orphan
# (self-healing -- a refactor that removes the read re-opens the flag).
CURATED_CONSUMERS = [
    {'artifact_re': r'^pipeline/byes_2026\.json$',     'consumer': 'engine/bbengine.py',             'needle': 'byes_2026.json'},
    {'artifact_re': r'^pipeline/games_by_week\.json$', 'consumer': 'engine/playoff_overlay.py',      'needle': 'games_by_week.json'},
    {'artifact_re': r'^pipeline/clay_2026_ud\.csv$',   'consumer': 'engine/bbengine.py',             'needle': 'clay_2026_ud.csv'},
    {'artifact_re': r'^engine/tree_schema\.json$',     'consumer': 'engine/verify_decision_tree.py', 'needle': 'tree_schema.json'},
    {'artifact_re': r'^sis_value/cfb/cfb_receiving_value_20(24|25)\.csv$', 'consumer': 'build_rookie_profiles.py',  'needle': 'cfb_receiving_value_'},
    {'artifact_re': r'^sis_value/cfb/cfb_rushing_value_20(24|25)\.csv$',   'consumer': 'build_rookie_profiles.py',  'needle': 'cfb_rushing_value_'},
    {'artifact_re': r'^sis_value/cfb/cfb_passing_value_20(24|25)\.csv$',   'consumer': 'build_rookie_profiles.py',  'needle': 'cfb_passing_value_'},
    {'artifact_re': r'^sis_value/(pass_defense|pass_rush|run_defense)_2024\.csv$',
     'consumer': 'normalize_defense_2026.py', 'needle': "_2024.csv"},  # 2024 recovery blend via path.replace
]

# ---- CURATED PRODUCERS the write-call heuristic misses (variable path, or a ')' inside open(...) ----
# is_writer()'s `open\([^)]*,'w'` cannot cross the ')' of os.path.join/core.P, so these real producers
# were misclassified as CONSUMERS of their own output (inflating peer-max in the divergence check) and
# their OFF-PIPELINE status was invisible. Verified writes:
#   build_coverage_spec.py:186  json.dump(out, open(jp,'w'))            -> boom/coverage_route_spec.json
#   build_profiles.py:302       json.dump(full, open(os.path.join(OUT,'player_profiles.json'),'w'))
#   build_cc_context.py:171     json.dump(ctx, open(core.P('cc_context.json'),'w'))
KNOWN_PRODUCERS = {
    'boom/coverage_route_spec.json': 'build_coverage_spec.py',
    'profiles/player_profiles.json': 'build_profiles.py',
    'cc_context.json': 'build_cc_context.py',
    'offense_profile.json': 'build_offense_profile.py',   # :119 json.dump(out, open(os.path.join(HERE,'offense_profile.json'),'w'))
}


def curated_consumers(art):
    """Verified dynamic/subdir consumers for one artifact (empty when the needle is gone)."""
    out = []
    for c in CURATED_CONSUMERS:
        if not re.search(c['artifact_re'], art):
            continue
        p = os.path.join(HERE, c['consumer'])
        try:
            if c['needle'] in open(p, encoding='utf-8', errors='ignore').read():
                out.append(c['consumer'])
        except OSError:
            pass
    return out

# ---- rich layers whose FIELD-LEVEL utilization matters (declare new config/projection layers here) ----
RICH_ARTIFACTS = [
    'coordinator_scheme_2026.json', 'coordinator_changes_2026.json',
    'boom/scheme_fit.json', 'boom/defensive_profile.json', 'boom/coverage_route_spec.json',
    'flag_ranks.json', 'lever_count.json',
]

# ---- CURATED INVARIANTS: (artifact, required_field, applies_to_predicate, human message) ----
# applies_to = substring(s) that identify consumers where the field is load-bearing.
INVARIANTS = [
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'man_rate_adj',
     'applies_to': ['scheme_fit', 'lever_count', 'lever_calendar', 'def_profile'],
     'msg': 'defense-adjusting consumers must use the coordinator-aware man_rate_adj, not raw/dc_new alone'},
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'conf',
     'applies_to': ['scheme_fit', 'lever_count', 'def_profile'],
     'msg': 'consumers that shrink new-DC teams must gate on conf (blend-prior vs regress-mean), not blanket-shrink'},
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'dc_scheme',
     'applies_to': ['scheme_fit'],
     'msg': 'the shell (single/two-high) split should use the sourced dc_scheme prose where available'},
    # -- added 2026-07-02 (ORPHAN_TRIAGE.md Parts 2-3): confirmed OPEN gaps, kept loud until wired --
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'conf',
     'applies_to': ['lever_calendar'],
     'msg': "build_lever_calendar 'mirrors build_lever_count' (its own comment) but percentile-ranks "
            "man_rate_adj RAW: lever_count gates its lambda on conf (build_lever_count.py:65) and refines "
            "the regressed man rate toward the researched lean (:73-75); the calendar's man-lever weeks "
            "drift from the count for new-DC teams  [OPEN gap -- fires until wired]"},
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'sack_rate_adj',
     'applies_to': ['lever_count'],
     'msg': "the pressure/protection side uses defense.json pass_rush_pctl (roster-aware) but NO lever reads "
            "the coordinator-aware 2026 sack projection (sack_rate_2025 -> sack_rate_adj, computed per new-DC "
            "team by build_coordinator_scheme.py:31); build_flags_QB's sackp amps are 2025-frozen too "
            "(boom_foundation.py:192)  [OPEN gap -- fires until wired]"},
]


def builders():
    out = {}
    for f in glob.glob(os.path.join(HERE, '*.py')):
        b = os.path.basename(f)
        if b == SELF or is_bak(b):
            continue
        out[b] = open(f, encoding='utf-8', errors='ignore').read()
    return out


def artifact_universe():
    arts = set()
    for pat in ('**/*.json', '**/*.csv', '**/*.html'):
        for p in glob.glob(os.path.join(HERE, pat), recursive=True):
            rel = os.path.relpath(p, HERE)
            if any(r in rel for r in RAW_DIRS):
                continue
            arts.add(rel.replace(os.sep, '/'))
    return arts


def pipeline_producers(src):
    """Authoritative producer map + pipeline membership from boom_pipeline.py + run_all.py."""
    producer, members = {}, set()
    bp = src.get('boom_pipeline.py', '')
    for name, outs in re.findall(r'\(\s*"([A-Za-z_0-9]+)"\s*,\s*\[([^\]]*)\]', bp):
        members.add(name + '.py')
        for o in re.findall(r'["\']([^"\']+\.(?:json|csv|html))["\']', outs):
            producer.setdefault(o, set()).add(name + '.py')
    ra = src.get('run_all.py', '')
    for script, outs in re.findall(r'\(\s*\[\s*["\']([^"\']+\.py)["\']\s*\]\s*,\s*\[([^\]]*)\]', ra):
        members.add(script)
        for o in re.findall(r'["\']([^"\']+\.(?:json|csv|html))["\']', outs):
            producer.setdefault(o, set()).add(script)
    # also any script named in the runner chains, even without declared outputs
    for m in re.findall(r'["\']([A-Za-z_0-9]+\.py)["\']', bp + ra):
        members.add(m)
    return producer, members


def is_writer(txt, art):
    """Heuristic producer fallback: a write call mentioning the basename."""
    base = os.path.basename(art)
    for m in re.finditer(re.escape(base), txt):
        w = txt[max(0, m.start() - 140):m.start() + 40]
        if 'safe_json_dump' in w or re.search(r"open\([^)]*,\s*['\"]w", w) or '.write(' in w:
            return True
    return False


def refs(src, arts):
    """artifact -> {'producers':set, 'consumers':set} using basename OR relpath match."""
    prod_map, _ = pipeline_producers(src)
    graph = {a: {'producers': set(prod_map.get(a, set())), 'consumers': set()} for a in arts}
    for f, txt in src.items():
        for a in arts:
            base = os.path.basename(a)
            if base not in txt and a not in txt:
                continue
            if f in graph[a]['producers']:
                continue
            if is_writer(txt, a):
                graph[a]['producers'].add(f)
            else:
                graph[a]['consumers'].add(f)
    # curated producers the write-window heuristic misses (they'd otherwise count as consumers)
    for art, b in KNOWN_PRODUCERS.items():
        if art in graph:
            graph[art]['producers'].add(b)
            graph[art]['consumers'].discard(b)
    return graph


def record_fields(obj):
    """Field names at the RECORD level of a rich artifact (not container index keys or meta)."""
    if not isinstance(obj, dict):
        return set()
    body = {k: v for k, v in obj.items() if k not in ('_meta', 'meta')}
    container = None
    for name in ('players', 'teams', 'records', 'items', 'data'):
        if isinstance(body.get(name), dict):
            container = body[name]; break
    if container is None:
        vals = [v for v in body.values() if isinstance(v, dict)]
        # body itself is a {code: record} map if most values are dicts; else a flat config
        container = body if vals and len(vals) >= max(1, 0.5 * len(body)) else None
        if container is None:
            return set(str(k) for k in body)
    keys = set()
    for rec in list(container.values())[:30]:
        if isinstance(rec, dict):
            keys |= set(str(k) for k in rec)
            for v in rec.values():          # one level into nested record dicts (e.g. proj:{...})
                if isinstance(v, dict):
                    keys |= set(str(k) for k in v)
    return keys


def rich_layers(graph):
    """REPO-WIDE: every record-structured in-repo JSON that has >=1 consumer, plus curated extras.
    Auto-discovery means new layers are field-audited the moment something reads them -- no manual list."""
    cands = set(RICH_ARTIFACTS)
    for a, g in graph.items():
        if a.endswith('.json') and not is_terminal(a) and g['consumers']:
            cands.add(a)
    return sorted(cands)


def field_use(src, graph):
    rows = []
    for a in rich_layers(graph):
        path = os.path.join(HERE, a)
        if not os.path.exists(path):
            continue
        try:
            obj = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        keys = {k for k in record_fields(obj) if re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{1,40}', k)}
        if not keys:
            continue
        consumers = [c for c in sorted(graph.get(a, {}).get('consumers', set())) if c not in ORCHESTRATORS]
        matrix, used_anywhere = {}, set()
        for c in consumers:
            t = src[c]
            u = {k for k in keys if re.search(r"['\"]" + re.escape(k) + r"['\"]", t)}
            matrix[c] = u
            used_anywhere |= u
        unused = sorted(keys - used_anywhere)
        # DIVERGENCE: with >=2 consumers, one reading STARKLY fewer fields than its peers under-uses
        # the layer -- the generalized scheme_fit bug (read ~1 field of a rich 8+ schema). Tuned to
        # fire only on stark gaps (peer reads >=8, this reads <25%) to avoid flagging (a) legitimately
        # specialized consumers that need a subset, and (b) consumers that iterate fields dynamically
        # rather than by string literal (they look like they read nothing). Divergence is a CANDIDATE
        # feed for review, not a verdict -- the precise checks are orphans/invariants/fallbacks.
        divergent = []
        if len(consumers) >= 2:
            mx = max(len(matrix[c]) for c in consumers)
            if mx >= 8:
                divergent = [c for c in consumers if len(matrix[c]) < 0.25 * mx]
        rows.append({'artifact': a, 'keys': sorted(keys), 'consumers': consumers,
                     'matrix': matrix, 'unused': unused, 'divergent': divergent})
    return rows


def check_invariants(src, graph):
    findings = []
    for inv in INVARIANTS:
        a = inv['artifact']
        consumers = graph.get(a, {}).get('consumers', set())
        for c in sorted(consumers):
            if not any(tag in c for tag in inv['applies_to']):
                continue
            if not re.search(r"['\"]" + re.escape(inv['field']) + r"['\"]", src[c]):
                findings.append({'artifact': a, 'field': inv['field'], 'consumer': c, 'msg': inv['msg']})
    return findings


def fallbacks():
    """Harvest fallback/skip counters from every output's _meta -- silent gaps made loud."""
    hits = []
    pat = re.compile(r'skip|fallback|regress|charting|no_|missing|stale|shrink|degrade', re.I)
    for p in glob.glob(os.path.join(HERE, '**/*.json'), recursive=True):
        rel = os.path.relpath(p, HERE)
        if any(r in rel for r in RAW_DIRS):
            continue
        try:
            obj = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        meta = obj.get('_meta') or obj.get('meta') if isinstance(obj, dict) else None
        if not isinstance(meta, dict):
            continue
        for k, v in meta.items():
            if pat.search(str(k)) and v not in (None, 0, [], {}, False):
                hits.append((rel.replace(os.sep, '/'), k, v))
    return hits


def split_source(src):
    """FROZEN/DUP-INPUT class: a data file read via BOTH core.find_data(...) (the parent-level,
    resync-fresh copy) AND a repo-relative accessor (J('..')/core.P('..')/os.path.join(HERE,..))
    -- two physical copies of one logical file that silently drift. This is the cc_context matchup
    bug (build_cc_context read the repo-local copy while sync_boom_defense/boom_foundation/build_splits
    read the parent copy). One logical file, one access convention."""
    find, rel = {}, {}
    for f, t in src.items():
        for m in re.finditer(r"find_data\(([^)]*)\)", t):
            a = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
            if a:
                find.setdefault(a[-1].split('/')[-1], set()).add(f)
        for m in re.finditer(r"(?:\bJ\(|core\.P\(|\bP\(|os\.path\.join\(HERE,\s*)['\"]([^'\"]+\.(?:json|csv))['\"]", t):
            rel.setdefault(os.path.basename(m.group(1)), set()).add(f)
    return [(b, sorted(find[b]), sorted(rel[b])) for b in sorted(set(find) & set(rel))]


# ---- deliverables that must be pipeline-fresh (built AFTER flag_ranks in the DOSSIER chain) ----
CORE_DELIVERABLES = ['rankings.html', 'dossier.html', 'dossier_deep.html', 'lever_board.html',
                     'adp_cluster_board.html', 'big_board_2026.html']
def stale_deliverables():
    """A core rendered deliverable OLDER than the model tip (flag_ranks.json) shipped stale under a
    fresher model -- the adp_cluster_board bug (board built off yesterday's ranks). HTML-only builders
    are invisible to the off-pipeline check (terminal output), so this catches the class by freshness."""
    tip = os.path.join(HERE, 'flag_ranks.json')
    if not os.path.exists(tip):
        return []
    t = os.path.getmtime(tip)
    out = []
    for d in CORE_DELIVERABLES:
        p = os.path.join(HERE, d)
        if os.path.exists(p) and os.path.getmtime(p) < t - 5:   # 5s grace
            out.append((d, int(t - os.path.getmtime(p))))
    return out


def main():
    strict = '--strict' in sys.argv
    src = builders()
    arts = artifact_universe()
    graph = refs(src, arts)
    _, members = pipeline_producers(src)

    # CHECK A -- orphans + pipeline coverage
    orphans, curated_ok = [], []
    for a in sorted(arts):
        if is_terminal(a):
            continue
        g = graph[a]
        if not g['consumers']:
            cur = curated_consumers(a)
            if cur:
                curated_ok.append((a, cur))   # verified dynamic/subdir read -- NOT an orphan
                continue
            why = ('produced by %s but consumed by none' % sorted(g['producers'])) if g['producers'] \
                else 'on disk, referenced by no builder'
            orphans.append((a, why))
    missing_from_pipeline = sorted(
        b for b in src
        if b not in members and b not in ('run_all.py', 'boom_pipeline.py', SELF)
        and re.match(r'(build_|make_|render_|apply_|derive_|sync_|tighten_|mark_)', b)
        and (b in KNOWN_PRODUCERS.values()
             or any(is_writer(src[b], a) for a in arts if not is_terminal(a))))

    fld = field_use(src, graph)
    inv = check_invariants(src, graph)
    fb = fallbacks()
    ss = split_source(src)
    sd = stale_deliverables()

    # ---- write report ----
    L = []
    L.append('# INTEGRATION AUDIT\n')
    L.append('_Catches "layer built but not properly consumed". Re-run: `python3 integration_audit.py`._\n')
    L.append('_Data-side companion: `audit_roster_moves.py` (cross-source player-team check + roster-move reconciliation) → ROSTER_MOVES_2026.md._\n')
    p0 = len(inv) + len(ss) + len(sd)
    L.append('## Summary\n')
    L.append(f'- **{len(inv)} invariant violations** (P0 -- a layer is being under-used)')
    L.append(f'- **{len(ss)} split-source files** (P0 -- one logical file read from two drifting copies)')
    L.append(f'- **{len(sd)} stale deliverables** (P0 -- a rendered board older than the model tip it renders)')
    L.append(f'- **{len(orphans)} orphan candidates** (produced/on-disk, no consumer; terminals + verified curated dynamic reads excluded)')
    L.append(f'- **{len(missing_from_pipeline)} builders** produce artifacts but are absent from the pipeline runner')
    L.append(f'- **{sum(len(r["unused"]) for r in fld)} unused fields** across {len(fld)} record-structured layers (auto-discovered, repo-wide)')
    L.append(f'- **{sum(len(r.get("divergent", [])) for r in fld)} divergent consumers** (a consumer under-using a layer its peers read fully)')
    L.append(f'- **{len(fb)} fallback counters** currently firing (see check D)\n')

    L.append('## A. Invariant violations (P0)\n')
    if inv:
        for f in inv:
            L.append(f'- `{f["consumer"]}` does not read `{f["field"]}` from `{f["artifact"]}`  \n  ↳ {f["msg"]}')
    else:
        L.append('_None._')
    L.append('')

    L.append('## B. Field utilization (per rich layer)\n')
    for r in fld:
        L.append(f'### `{r["artifact"]}`  ({len(r["keys"])} fields, {len(r["consumers"])} consumers)')
        if r['consumers']:
            L.append('| consumer | # fields read |')
            L.append('|---|---|')
            for c in r['consumers']:
                L.append(f'| {c} | {len(r["matrix"][c])} |')
        if r['unused']:
            L.append(f'\n**Unused by ALL consumers:** {", ".join("`%s`" % k for k in r["unused"])}')
        if r.get('divergent'):
            L.append(f'\n**Divergent consumers (read <40% of peer max — likely under-using the layer):** '
                     f'{", ".join("`%s`" % c for c in r["divergent"])}')
        L.append('')

    L.append('## C. Orphan candidates\n')
    if orphans:
        for a, why in orphans:
            L.append(f'- `{a}` — {why}')
    else:
        L.append('_None._')
    if curated_ok:
        L.append('\n_Cleared by CURATED dynamic/subdir reads (needle re-verified this run; an entry drops back to orphan the moment its read is refactored away):_\n')
        for a, cur in curated_ok:
            L.append(f'- `{a}` ← {", ".join("`%s`" % c for c in cur)}')
    L.append('')
    L.append('## Builders missing from the pipeline runner\n')
    if missing_from_pipeline:
        for b in missing_from_pipeline:
            L.append(f'- `{b}`')
    else:
        L.append('_None._')
    L.append('')

    L.append('## D. Fallback telemetry (silent gaps made loud)\n')
    if fb:
        for rel, k, v in fb:
            vs = json.dumps(v)
            L.append(f'- `{rel}` · `{k}` = {vs[:120]}')
    else:
        L.append('_No fallback counters found in output metas. (Add `_meta.fallbacks` to builders to populate.)_')
    L.append('')

    L.append('## E. Split-source files (P0 — one logical file, two drifting copies)\n')
    if ss:
        for base, fnd, rl in ss:
            L.append(f'- `{base}` — via `core.find_data` in {", ".join("`%s`" % c for c in fnd)}; '
                     f'via repo-relative accessor in {", ".join("`%s`" % c for c in rl)}. Pick one convention.')
    else:
        L.append('_None — every near-repo data file is read through a single access convention._')
    L.append('')

    L.append('## F. Stale deliverables (P0 — a board older than the model it renders)\n')
    if sd:
        for d, age in sd:
            L.append(f'- `{d}` is {age}s older than `flag_ranks.json` — rebuild it (add its builder to run_all).')
    else:
        L.append('_None — every core board is at least as fresh as the model tip._')
    L.append('')

    open(os.path.join(HERE, 'INTEGRATION_AUDIT.md'), 'w', encoding='utf-8').write('\n'.join(L))

    # ---- console summary ----
    print('INTEGRATION AUDIT ->  INTEGRATION_AUDIT.md')
    print(f'  P0 invariant violations : {len(inv)}')
    for f in inv:
        print(f'     - {f["consumer"]} ignores {f["field"]} of {f["artifact"]}')
    print(f'  orphan candidates       : {len(orphans)}  (+{len(curated_ok)} cleared by verified curated dynamic/subdir reads)')
    print(f'  builders off-pipeline   : {len(missing_from_pipeline)}  {missing_from_pipeline}')
    print(f'  layers field-audited    : {len(fld)}  (auto-discovered, repo-wide)')
    print(f'  unused rich fields      : {sum(len(r["unused"]) for r in fld)}')
    div = [(r["artifact"], r["divergent"]) for r in fld if r.get("divergent")]
    print(f'  divergent consumers     : {sum(len(d) for _, d in div)}')
    for a, d in div:
        print(f'     - {a}: {d} under-use vs peers')
    print(f'  fallback counters firing: {len(fb)}')
    print(f'  split-source files       : {len(ss)}' + (f'  {[b for b, _, _ in ss]}' if ss else ''))
    print(f'  stale deliverables       : {len(sd)}' + (f'  {[d for d, _ in sd]}' if sd else ''))
    if strict and p0:
        print(f'\nSTRICT: {p0} P0 finding(s) -> exit 1')
        sys.exit(1)


if __name__ == '__main__':
    main()
