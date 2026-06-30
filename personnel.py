#!/usr/bin/env python3
"""
personnel.py  --  Module D: 2026 Personnel + Coaching change merger.

Builds a per-team view of how each team will look DIFFERENT in 2026 across:
  1. OFFENSE        -- DATA-MODELED  (from team_review_data.json 'delta' object)
  2. DEFENSE        -- CORPUS-SOURCED (mined from transcripts + team_notes)
  3. OFFENSIVE LINE -- CORPUS-SOURCED (mined from transcripts + team_notes)
  4. COORDINATOR    -- CORPUS-SOURCED (coordinator_notes.json + mined scheme/OC/DC chatter)

Rigorously honest about MODELED vs CORPUS vs MISSING.
A transcript sentence is attributed to a team ONLY when exactly ONE team is named in it.
2026 coordinators are NEVER asserted from memory -- only surfaced if present in the corpus.

Outputs: personnel_changes.json, PERSONNEL.md
Read-only on all shared inputs.
"""
import json, re, os, csv

HERE = os.path.dirname(os.path.abspath(__file__))
def P(f):  return os.path.join(HERE, f)

# ---------------------------------------------------------------------------
# Team identity + nickname/city -> abbrev map (for single-team attribution)
# ---------------------------------------------------------------------------
TEAMS = {
 'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills',
 'CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns',
 'DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers',
 'HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs',
 'LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins',
 'MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants',
 'NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks',
 'SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders',
}
ABBRS = list(TEAMS.keys())

# Patterns are word-boundary-anchored. Shared nicknames that collide across teams
# (e.g. "new york" alone) are intentionally NOT listed, so they never attribute.
def _pats():
    raw = {
      'ARI':[r'arizona cardinals', r'\bcardinals\b', r'\bcards\b', r'\barizona\b'],
      'ATL':[r'atlanta falcons', r'\bfalcons\b', r'\batlanta\b'],
      'BAL':[r'baltimore ravens', r'\bravens\b', r'\bbaltimore\b'],
      'BUF':[r'buffalo bills', r'\bbills\b', r'\bbuffalo\b'],
      'CAR':[r'carolina panthers', r'\bpanthers\b', r'\bcarolina\b'],
      'CHI':[r'chicago bears', r'\bbears\b', r'\bchicago\b'],
      'CIN':[r'cincinnati bengals', r'\bbengals\b', r'\bcincinnati\b', r'\bcincy\b'],
      'CLE':[r'cleveland browns', r'\bbrowns\b', r'\bcleveland\b'],
      'DAL':[r'dallas cowboys', r'\bcowboys\b', r'\bdallas\b'],
      'DEN':[r'denver broncos', r'\bbroncos\b', r'\bdenver\b'],
      'DET':[r'detroit lions', r'\blions\b', r'\bdetroit\b'],
      'GB' :[r'green bay packers', r'\bpackers\b', r'\bgreen bay\b', r'\bpack\b'],
      'HOU':[r'houston texans', r'\btexans\b', r'\bhouston\b'],
      'IND':[r'indianapolis colts', r'\bcolts\b', r'\bindianapolis\b', r'\bindy\b'],
      'JAX':[r'jacksonville jaguars', r'\bjaguars\b', r'\bjacksonville\b', r'\bjags\b'],
      'KC' :[r'kansas city chiefs', r'\bchiefs\b', r'\bkansas city\b'],
      'LAC':[r'los angeles chargers', r'\bchargers\b', r'\bbolts\b'],
      'LAR':[r'los angeles rams', r'\brams\b'],
      'LV' :[r'las vegas raiders', r'\braiders\b', r'\blas vegas\b'],
      'MIA':[r'miami dolphins', r'\bdolphins\b', r'\bmiami\b', r'\bfins\b'],
      'MIN':[r'minnesota vikings', r'\bvikings\b', r'\bminnesota\b', r'\bvikes\b'],
      'NE' :[r'new england patriots', r'\bpatriots\b', r'\bnew england\b', r'\bpats\b'],
      'NO' :[r'new orleans saints', r'\bsaints\b', r'\bnew orleans\b'],
      'NYG':[r'new york giants', r'\bgiants\b'],
      'NYJ':[r'new york jets', r'\bjets\b'],
      'PHI':[r'philadelphia eagles', r'\beagles?\b', r'\bphiladelphia\b', r'\bphilly\b'],
      'PIT':[r'pittsburgh steelers', r'\bsteelers\b', r'\bpittsburgh\b'],
      'SEA':[r'seattle seahawks', r'\bseahawks\b', r'\bseattle\b', r'\bhawks\b'],
      'SF' :[r'san francisco 49ers', r'\b49ers\b', r'\bniners\b', r'\bsan francisco\b'],
      'TB' :[r'tampa bay buccaneers', r'\bbuccaneers\b', r'\bbuccs?\b', r'\btampa bay\b', r'\btampa\b'],
      'TEN':[r'tennessee titans', r'\btitans\b', r'\btennessee\b'],
      'WAS':[r'washington commanders', r'\bcommanders\b', r'\bwashington\b', r'\bcommies\b'],
    }
    return {ab: [re.compile(p) for p in lst] for ab, lst in raw.items()}
TEAM_PATS = _pats()

def teams_in(text):
    """Return the SET of distinct team abbrevs named anywhere in `text`."""
    t = text.lower()
    found = set()
    for ab, pats in TEAM_PATS.items():
        for p in pats:
            if p.search(t):
                found.add(ab)
                break
    return found

def sole_team(text):
    """Return the abbrev iff EXACTLY ONE team is named, else None."""
    f = teams_in(text)
    return next(iter(f)) if len(f) == 1 else None

# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------
_SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])')
def sentences(txt):
    txt = (txt or '').replace('\n', ' ')
    out = []
    for s in _SENT.split(txt):
        s = ' '.join(s.split()).strip()
        if 25 <= len(s) <= 320:           # drop fragments + run-ons
            out.append(s)
    return out

def clean_q(s):
    s = ' '.join((s or '').split()).strip()
    return s.strip('"“” ').strip()

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------
DEF_KW = [
  'pass rush','pass-rush','pass rusher','pass-rusher','edge rusher','edge defender','sack',
  'secondary','cornerback','corner ','safety','safeties','run defense','run-defense',
  'pass defense','pass-defense','defensive line','d-line','defensive back','coverage',
  'defense','defender','defensive player','interception','blitz','front seven','linebacker',
]
OL_KW = [
  'offensive line','o-line','o line','offensive linemen','offensive lineman','offensive tackle',
  'left tackle','right tackle','left guard','right guard','interior offensive','interior line',
  'pass protection','pass-protection','pass protect','run blocking','run-blocking','run block',
  'linderbaum','offensive line is','o-line is','the o line','iol','at tackle','at guard',
  'blindside','front five',
]
OL_NEAR = re.compile(r'\b(guard|tackle|center)\b')
OL_CONTEXT = re.compile(r"\b(line|lineman|linemen|block|protect|snap|trench|contract|starting)\b")

COORD_KW = [
  'offensive coordinator','defensive coordinator','play caller','play-caller','play calling',
  'play-calling','new oc','new dc','new head coach','new scheme','his offense','his system',
  'new offense','hired','play action','play-action','run-heavy','pass-heavy','personnel grouping',
  '11 personnel','12 personnel','21 personnel','scheme','calls plays','calling plays',
  'offensive system','wide zone','zone running','air raid','west coast',
]

def has_kw(text, kws):
    t = text.lower()
    return any(k in t for k in kws)

# --- Precision gates: keep TEAM-UNIT defense/OL signal, drop player-action noise ---
# Offensive-action context => the sentence is about a ball-carrier/receiver/QB acting
# *against* a defense (or beating coverage), NOT about the team's own defensive unit.
OFF_ACTION = re.compile(
    r'\b(beat|beats|past|around|made|make|making|grab air|in space|run past|broke|breaks|'
    r'avoiding interception|avoided interception|touchdown|kicks it|kick it|stiff[- ]?arm|'
    r'juke|jukes|burst|another gear|running back|ball carrier|'
    r'success rate versus|success rate vs|versus man coverage|vs man coverage|versus press|'
    r'against the|against this|life impossible|life a nightmare|gives defenses|'
    r'something else to think|man coverage and everybody|line up at|lined up at)\b'
)
# Team-unit defensive subject: the team's defense / pass rush / secondary as the actor/topic.
DEF_UNIT = re.compile(
    r"\b(pass rush|pass-rush|pass rusher|pass-rusher|secondary|run defense|run-defense|"
    r"pass defense|pass-defense|defensive line|d-line|defensive player|defensive back|"
    r"defensive backs|edge rusher|edge defender|[a-z]+'s defense|[a-z]+ defense|"
    r"defensive coordinator|safeties coach|need at cornerback|need at corner|"
    r"bigger need at|led the nfl|extension)\b"
)

def is_def(text):
    t = text.lower()
    if not has_kw(t, DEF_KW):
        return False
    if not DEF_UNIT.search(t):
        return False
    if OFF_ACTION.search(t):
        return False
    return True

# Strong O-line unit subjects: the unit itself, or a lineman role/transaction.
OL_UNIT = re.compile(
    r"\b(offensive line|o-line|o line|offensive linemen|offensive lineman|"
    r"[a-z]+'s offensive line|broncos' offensive line|left tackle|right tackle|"
    r"left guard|right guard|interior offensive|interior line|pass protection|pass-protection|"
    r"record-setting contract for a center|signed (tyler )?linderbaum|the center coming over|"
    r"front five)\b"
)
# Drop cases where the 'block'/'run blocker' subject is a TE/WR/RB (not the OL unit).
OL_SKILL_BLOCK = re.compile(
    r'\b(tight end|tight ends|wide receiver|receivers block|run blocker|monster as a run blocker|'
    r'fullback|h[- ]?back|doesn\'t talk much)\b'
)

def is_ol(text):
    t = text.lower()
    if not has_kw(t, OL_KW) and not (OL_NEAR.search(t) and OL_CONTEXT.search(t)):
        return False
    if not OL_UNIT.search(t):
        return False
    if OL_SKILL_BLOCK.search(t):
        return False
    return True

def is_coord(text):
    return has_kw(text, COORD_KW)

# ---------------------------------------------------------------------------
# Load shared inputs (READ-ONLY)
# ---------------------------------------------------------------------------
REV = json.load(open(P('team_review_data.json'), encoding='utf-8'))
COORD_NOTES = json.load(open(P('coordinator_notes.json'), encoding='utf-8'))

def load_csv(f):
    p = P(f)
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))
TEAM_NOTES = load_csv('team_notes.csv')   # team, team_note, n_clips
OVERLAYS   = load_csv('overlays.csv')     # name, type, note

# transcripts (auto-discover the *transcripts.jsonl in uploads)
TRANS_PATH = None
udir = next((d for d in (
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Downloads', 'uploads'),
) if os.path.isdir(d)), '')  # portable: transcript uploads near the repo (optional layer, guarded below)
if os.path.isdir(udir):
    for fn_ in sorted(os.listdir(udir)):
        if fn_.endswith('transcripts.jsonl'):
            TRANS_PATH = os.path.join(udir, fn_)
            break
RECORDS = []
if TRANS_PATH:
    with open(TRANS_PATH, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                RECORDS.append(json.loads(line))

# ---------------------------------------------------------------------------
# 1. OFFENSE  -- data-driven summary + beneficiary detection
# ---------------------------------------------------------------------------
def best_beneficiaries(team, k=3):
    """
    Likely beneficiaries = skill players whose 2026 team is `team` (returning OR
    incoming/mover), ranked by ceiling (p95) then ADP, who can absorb vacated volume.
    QBs are excluded -- they don't 'absorb targets'.
    """
    plist = REV.get(team, {}).get('players', []) or []
    cands = [p for p in plist if p.get('pos') in ('WR', 'RB', 'TE') and p.get('p95') is not None]
    def keyf(p):
        adp = p.get('adp')
        adp = adp if isinstance(adp, (int, float)) else 9999
        return (-(p.get('p95') or 0), adp)
    cands.sort(key=keyf)
    out = []
    for p in cands[:k]:
        out.append({
            'name': p['name'], 'pos': p.get('pos'), 'adp': p.get('adp'),
            'p95': p.get('p95'), 'mover': str(p.get('mover')).strip().lower() in ('true','1'),
            'tgtshare25': p.get('tgtshare'),
        })
    return out

def offense_block(team):
    tv = REV.get(team, {})
    de = tv.get('delta') or {}
    vac = de.get('vac_tgt')
    d_pa = de.get('d_pa')
    departures = de.get('departures', []) or []
    arrivals   = de.get('arrivals', []) or []
    rookies    = de.get('rookies', []) or []

    # LAR special case: skill players tagged 'LA' in source -> delta empty. Be explicit.
    lar_note = (team == 'LAR' and not departures and not vac)

    bens = best_beneficiaries(team)

    if d_pa is None:
        vol = 'pass-volume change not modeled (skill group tagged to prior-name team in source)'
    elif d_pa >= 1.5:
        vol = 'projected pass attempts UP %+.1f/g vs 2025' % d_pa
    elif d_pa <= -1.5:
        vol = 'projected pass attempts DOWN %+.1f/g vs 2025' % d_pa
    else:
        vol = 'pass volume roughly flat (%+.1f/g)' % d_pa

    dep_str = '; '.join("%s (%.0f%% of '25 tgt vol -> %s)" % (n, sh, dest) for (n, sh, dest) in departures)
    arr_in  = [a[0] for a in arrivals]
    arr_str = ', '.join(arr_in) if arr_in else ''
    rk_str  = ', '.join(rookies) if rookies else ''

    ben_disp = []
    for b in bens:
        tag = ' [incoming]' if b['mover'] else ''
        ben_disp.append('%s (%s, ADP %s, p95 %s)%s' % (b['name'], b['pos'], b['adp'], b['p95'], tag))

    pieces = []
    if lar_note:
        pieces.append("LAR skill room returns intact in source (Stafford/Nacua/Kyren/Adams tagged "
                      "to prior name) so no vacated-target delta is modeled here; treat continuity "
                      "as the signal.")
    else:
        if vac and vac > 0:
            lead = '%.0f%% of 2025 target volume departs' % vac
            if dep_str:
                lead += ' (%s)' % dep_str
            pieces.append(lead + '.')
        else:
            pieces.append('Minimal target volume departs.')
        incoming_bits = []
        if arr_str: incoming_bits.append('arrivals: %s' % arr_str)
        if rk_str:  incoming_bits.append('rookies: %s' % rk_str)
        inc = ('Incoming -- ' + '; '.join(incoming_bits) + '.') if incoming_bits else 'No notable skill arrivals.'
        pieces.append(inc)
    if ben_disp:
        pieces.append('With %s, the vacated work most plausibly flows to %s.' % (vol, ', '.join(ben_disp)))
    else:
        pieces.append('Volume: %s.' % vol)

    return {
        'summary': ' '.join(pieces),
        'vac_tgt': vac,
        'd_pa': d_pa,
        'volume_shift': vol,
        'departures': [{'name': n, 'share_pct': sh, 'dest': dest} for (n, sh, dest) in departures],
        'arrivals':   [{'name': a[0], 'from': a[1]} for a in arrivals],
        'rookies':    list(rookies),
        'beneficiaries': bens,
        'source': 'MODELED (team_review_data.json delta)',
    }

# ---------------------------------------------------------------------------
# 2 & 3. DEFENSE / OFFENSIVE LINE  -- corpus mining
# ---------------------------------------------------------------------------
def mine_corpus():
    """dict[team] -> {'defense':[{q,handle}], 'oline':[...], 'coord':[...]}."""
    buckets = {t: {'defense': [], 'oline': [], 'coord': []} for t in ABBRS}
    seen = {t: {'defense': set(), 'oline': set(), 'coord': set()} for t in ABBRS}

    def add(team, cat, q, handle):
        if not team or team not in buckets:
            return
        key = q.lower()[:90]
        if key in seen[team][cat]:
            return
        seen[team][cat].add(key)
        buckets[team][cat].append({'q': q, 'handle': handle})

    # ---- transcripts: only single-team sentences ----
    for r in RECORDS:
        handle = r.get('handle', '')
        for s in sentences(r.get('transcript', '')):
            team = sole_team(s)
            if not team:
                continue
            q = clean_q(s)
            if len(q) < 25:
                continue
            if is_def(s):   add(team, 'defense', q, handle)
            if is_ol(s):    add(team, 'oline', q, handle)
            if is_coord(s): add(team, 'coord', q, handle)

    # ---- team_notes.csv (pre-attributed; clips are "quote" (@handle) | "quote" ...) ----
    for row in TEAM_NOTES:
        team = (row.get('team') or '').strip()
        note = row.get('team_note') or ''
        if team not in buckets:
            continue
        for clip in note.split('|'):
            m = re.search(r'[“"](.+?)[”"]\s*\(@?([A-Za-z0-9_]+)\)', clip)
            if not m:
                continue                 # skip malformed/truncated clips (no clean quote+handle)
            q = clean_q(m.group(1)); handle = m.group(2)
            if len(q) < 25:
                continue
            # single-team guard: skip if the sentence also names another team
            if (teams_in(q) - {team}):
                continue
            if is_def(q):   add(team, 'defense', q, handle)
            if is_ol(q):    add(team, 'oline', q, handle)
            if is_coord(q): add(team, 'coord', q, handle)
    return buckets

CORPUS = mine_corpus()

def pick_notes(team, cat, k=2):
    """Pick up to k cleanest notes: prefer ones with a handle, mid-length (substantive, not run-ons)."""
    items = CORPUS[team][cat]
    def score(it):
        hl = 1 if it['handle'] else 0
        lp = -abs(len(it['q']) - 130)   # sweet spot ~130 chars
        return (hl, lp)
    return sorted(items, key=score, reverse=True)[:k]

# ---------------------------------------------------------------------------
# 4. COORDINATOR / SCHEME  -- consolidate coordinator_notes + mined coord chatter
# ---------------------------------------------------------------------------
# Curated scheme_shift + fantasy implication, written ONLY for teams that actually
# have a corpus coordinator note. Direction claims are tied to the quoted evidence
# and/or the modeled d_pa. We NEVER invent a 2026 coordinator from memory.
SCHEME = {
 'ARI': ("Corpus names Hackett as the hired OC; Vance Joseph runs the defense (both per corpus).",
         "The note states a staff change but no clear pass/run lean; with modeled pass attempts DOWN sharply "
         "(-7.5/g) there is no confident WR-room lift -- treat as scheme-uncertain / neutral."),
 'GB' : ("Corpus references Love's prior system being less oriented to the intermediate middle.",
         "The scheme note describes a coach/system that LEFT GB, not a 2026 GB hire; no defensible 2026 "
         "direction -- hold neutral."),
 'LAC': ("Corpus: a defensive coordinator (O'Leary) with one year of DC experience; OL flagged as the "
         "perennial question.",
         "Signal is defense/OL-side, not an offensive scheme change -- no WR/RB volume implication can be "
         "defended from it."),
 'LV' : ("Corpus frames an OL-driven run-game identity under the new staff (Kubiak named as the prior OC, "
         "now a head coach elsewhere).",
         "Corpus stresses an OL-built run game, so the lean is toward establishing the run -> mild RB tilt; "
         "but pass volume is modeled roughly flat (-0.9/g), so no strong WR lift."),
 'MIA': ("New GM (Sullivan) + new HC drove 'one of the biggest roster overhauls' in the NFL (per corpus).",
         "Corpus confirms a top-to-bottom regime change but NOT the offensive pass/run direction; with the WR "
         "room gutted (Waddle/Hill out, 44% of targets vacated) the scheme is unsettled -- low confidence, "
         "treat incoming/young WRs as dart throws."),
 'NYJ': ("Corpus: an OC hired as an Aaron-Rodgers-tied hire under the new staff.",
         "The note establishes a new play-caller but no clear pass lean; with 40.5% of targets vacated and pass "
         "volume ~flat (-1.7/g) the room is wide open but the direction is unproven -- no confident tilt."),
 'PHI': ("New Eagles OC Sean Mannion (per corpus) -- a first-time NFL play-caller (Shrine Bowl OC).",
         "A first-time play-caller succeeding a run-leaning staff; corpus gives no explicit pass-up signal and "
         "modeled pass attempts are DOWN (-2.3/g) after A.J. Brown's exit -- do NOT assume a WR-friendly tilt; "
         "neutral-to-cautious."),
 'TB' : ("New Bucs OC Zach Robinson (per corpus, a Sean McVay-tree hire) -- plans to play Egbuka at Z.",
         "A McVay-branch OC plus an explicit role quote points to a defined WR-usage scheme; with 29.6% of "
         "targets vacated (Evans/Shepard) this most plausibly LIFTS the returning/young WRs (Egbuka, Godwin) "
         "even with pass volume modeled slightly down (-4.4/g)."),
 'HOU': ("Corpus: 2024 Texans ran 12-personnel at the 3rd-highest rate in the NFL (31.5%).",
         "A 12-personnel-heavy identity caps pure spread passing; with one WR (Kirk) departed and modeled pass "
         "attempts DOWN (-4.6/g), the implication is a TE/play-action tilt rather than a WR-volume spike."),
}

def coordinator_block(team):
    """{note, handle, all_notes, scheme_shift, implication, source}."""
    notes = []
    for it in COORD_NOTES.get(team, []):
        q = clean_q(it.get('q', ''))
        if (teams_in(q) - {team}):          # single-team guard
            continue
        notes.append({'q': q, 'handle': it.get('h', '')})
    for it in pick_notes(team, 'coord', k=3):
        if all(it['q'][:60].lower() != n['q'][:60].lower() for n in notes):
            notes.append(it)

    if not notes:
        return {
            'note': None, 'handle': None, 'all_notes': [],
            'scheme_shift': 'no corpus signal -- no scheme assumption',
            'implication': 'no corpus signal -- no scheme assumption',
            'source': 'CORPUS (none found)',
        }
    primary = notes[0]
    shift, impl = SCHEME.get(team, (None, None))
    return {
        'note': primary['q'], 'handle': primary['handle'], 'all_notes': notes,
        'scheme_shift': shift if shift else 'coordinator/scheme mentioned in corpus; no clean directional shift stated',
        'implication': impl if impl else 'corpus names a staff change but no pass/run direction is defensible from the evidence -- hold neutral',
        'source': 'CORPUS (coordinator_notes.json + mined transcripts)',
    }

# ---------------------------------------------------------------------------
# Assemble per-team records
# ---------------------------------------------------------------------------
def build():
    teams = {}
    for t in ABBRS:
        dnotes = pick_notes(t, 'defense', k=2)
        onotes = pick_notes(t, 'oline', k=2)
        teams[t] = {
            'team': t, 'name': TEAMS[t],
            'offense': offense_block(t),
            'defense': {
                'notes': dnotes,
                'source': 'CORPUS (transcripts + team_notes)' if dnotes else 'CORPUS (none found)',
                'status': 'signal' if dnotes else 'no corpus signal',
            },
            'oline': {
                'notes': onotes,
                'source': 'CORPUS (transcripts + team_notes)' if onotes else 'CORPUS (none found)',
                'status': 'signal' if onotes else 'no corpus signal',
            },
            'coordinator': coordinator_block(t),
        }
    coverage = {
        'teams_total': len(ABBRS),
        'offense_n': sum(1 for t in ABBRS if teams[t]['offense']['summary']),
        'defense_n': sum(1 for t in ABBRS if teams[t]['defense']['notes']),
        'oline_n':   sum(1 for t in ABBRS if teams[t]['oline']['notes']),
        'coordinator_n': sum(1 for t in ABBRS if teams[t]['coordinator']['note']),
    }
    return {'teams': teams, 'coverage': coverage}

DATA = build()

# ---------------------------------------------------------------------------
# Write personnel_changes.json
# ---------------------------------------------------------------------------
with open(P('personnel_changes.json'), 'w', encoding='utf-8') as fh:
    json.dump(DATA, fh, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# PERSONNEL.md helpers
# ---------------------------------------------------------------------------
def fmt(v):
    if v is None: return 'n/a'
    if isinstance(v, float): return '%.1f' % v
    return str(v)
def handle(h):
    return '(@%s)' % h if h else '(no handle)'

def md():
    cov = DATA['coverage']
    L = []
    L.append('# 2026 Personnel + Coaching Change Merger (Module D)')
    L.append('')
    L.append('Per-team view of how each roster looks **different** in 2026 across Offense, Defense, '
             'Offensive Line, and Coordinator/Scheme.')
    L.append('')
    L.append('## Legend -- read this first')
    L.append('')
    L.append('| Section | Source | Confidence |')
    L.append('|---|---|---|')
    L.append('| **OFFENSE** | **DATA-MODELED** -- from `team_review_data.json` `delta` (actual 2025 usage, '
             'vacated target %, projected pass-volume shift, player ceilings/ADP) | High; numbers are computed |')
    L.append('| **DEFENSE** | **CORPUS-SOURCED** -- mined from analyst transcripts + `team_notes.csv` | '
             'Sparse; verbatim analyst chatter only |')
    L.append('| **OFFENSIVE LINE** | **CORPUS-SOURCED** -- mined transcripts + notes | Sparse; chatter only |')
    L.append('| **COORDINATOR / SCHEME** | **CORPUS-SOURCED** -- `coordinator_notes.json` + mined OC/DC/scheme '
             'mentions | Sparse; **2026 coordinators are NEVER asserted from memory** |')
    L.append('')
    L.append('**Honesty rules applied:** (1) A transcript sentence is attributed to a team only when '
             '**exactly one** team is named in it. (2) Defense and OL carry **no modeled data** -- if the corpus '
             'is silent the section reads *"no corpus signal."* (3) Scheme implications only claim a pass/run '
             'direction that can be tied to the quoted evidence and/or the modeled `d_pa`. (4) 2026 coaching '
             'hires are reported only if they appear in the corpus -- never recalled from memory.')
    L.append('')
    L.append('**Coverage of %d teams:** Offense **%d** | Defense **%d** | Offensive Line **%d** | Coordinator **%d**.'
             % (cov['teams_total'], cov['offense_n'], cov['defense_n'], cov['oline_n'], cov['coordinator_n']))
    L.append('')
    L.append('---')
    L.append('')
    for t in ABBRS:
        tv = DATA['teams'][t]
        off = tv['offense']
        L.append('## %s -- %s' % (t, tv['name']))
        L.append('')
        L.append('**OFFENSE** _(modeled)_ -- vacated tgt: %s%% | d_pa: %s/g'
                 % (fmt(off['vac_tgt']), fmt(off['d_pa'])))
        L.append('')
        L.append(off['summary'])
        L.append('')
        L.append('**DEFENSE** _(corpus)_')
        if tv['defense']['notes']:
            for n in tv['defense']['notes']:
                L.append('- “%s” %s' % (n['q'], handle(n['handle'])))
        else:
            L.append('- no corpus signal')
        L.append('')
        L.append('**OFFENSIVE LINE** _(corpus)_')
        if tv['oline']['notes']:
            for n in tv['oline']['notes']:
                L.append('- “%s” %s' % (n['q'], handle(n['handle'])))
        else:
            L.append('- no corpus signal')
        L.append('')
        crd = tv['coordinator']
        L.append('**COORDINATOR / SCHEME** _(corpus)_')
        if crd['note']:
            L.append('- Note: “%s” %s' % (crd['note'], handle(crd['handle'])))
            L.append('- Assumed shift: %s' % crd['scheme_shift'])
            L.append('- Fantasy implication: %s' % crd['implication'])
        else:
            L.append('- no corpus signal -- no scheme assumption')
        L.append('')
        L.append('---')
        L.append('')
    return '\n'.join(L)

with open(P('PERSONNEL.md'), 'w', encoding='utf-8') as fh:
    fh.write(md())

# ---------------------------------------------------------------------------
# VERIFICATION (run + print)
# ---------------------------------------------------------------------------
def dump(t, label):
    tv = DATA['teams'][t]
    off = tv['offense']
    print('-' * 72)
    print('SAMPLE [%s]: %s -- %s' % (label, t, tv['name']))
    print('-' * 72)
    print('OFFENSE (MODELED):')
    print('  vac_tgt:', off['vac_tgt'], '| d_pa:', off['d_pa'], '|', off['volume_shift'])
    print('  ', off['summary'])
    ben = ', '.join('%s(%s,p95 %s,ADP %s%s)' % (
            b['name'], b['pos'], b['p95'], b['adp'], (',IN' if b['mover'] else ''))
            for b in off['beneficiaries'])
    print('  beneficiaries:', ben)
    print('DEFENSE (CORPUS):')
    if tv['defense']['notes']:
        for n in tv['defense']['notes']:
            print('   - "%s" (@%s)' % (n['q'], n['handle'] or '?'))
    else:
        print('   - no corpus signal')
    print('OFFENSIVE LINE (CORPUS):')
    if tv['oline']['notes']:
        for n in tv['oline']['notes']:
            print('   - "%s" (@%s)' % (n['q'], n['handle'] or '?'))
    else:
        print('   - no corpus signal')
    print('COORDINATOR / SCHEME (CORPUS):')
    crd = tv['coordinator']
    if crd['note']:
        print('   - note: "%s" (@%s)' % (crd['note'], crd['handle'] or '?'))
        print('   - shift: %s' % crd['scheme_shift'])
        print('   - implication: %s' % crd['implication'])
    else:
        print('   - no corpus signal -- no scheme assumption')
    print()

def verify():
    cov = DATA['coverage']
    print('=' * 72)
    print('MODULE D -- PERSONNEL + COACHING MERGER -- VERIFICATION')
    print('=' * 72)
    print()
    print('COVERAGE REPORT (of %d teams):' % cov['teams_total'])
    print('  OFFENSE (modeled) signal : %2d/%d' % (cov['offense_n'], cov['teams_total']))
    print('  DEFENSE (corpus) signal  : %2d/%d' % (cov['defense_n'], cov['teams_total']))
    print('  OFF. LINE (corpus) signal: %2d/%d' % (cov['oline_n'], cov['teams_total']))
    print('  COORDINATOR (corpus)     : %2d/%d' % (cov['coordinator_n'], cov['teams_total']))
    print()
    def_teams = [t for t in ABBRS if DATA['teams'][t]['defense']['notes']]
    ol_teams  = [t for t in ABBRS if DATA['teams'][t]['oline']['notes']]
    crd_teams = [t for t in ABBRS if DATA['teams'][t]['coordinator']['note']]
    print('  teams w/ DEFENSE note    :', ' '.join(def_teams))
    print('  teams w/ OL note         :', ' '.join(ol_teams))
    print('  teams w/ COORDINATOR note:', ' '.join(crd_teams))
    print()

    # 3 sample teams: one loaded offense, one with a coordinator note, one thin team.
    dump('WAS', 'LOADED OFFENSE')
    dump('TB',  'COORDINATOR NOTE')
    thin_candidates = [t for t in ABBRS
                       if not DATA['teams'][t]['defense']['notes']
                       and not DATA['teams'][t]['oline']['notes']
                       and not DATA['teams'][t]['coordinator']['note']]
    thin = 'DAL' if 'DAL' in thin_candidates else (thin_candidates[0] if thin_candidates else 'DAL')
    dump(thin, 'THIN TEAM')

    # single-team attribution audit
    print('-' * 72)
    print('SINGLE-TEAM ATTRIBUTION AUDIT')
    print('-' * 72)
    violations = 0
    checked = 0
    for t in ABBRS:
        tv = DATA['teams'][t]
        for cat in ('defense', 'oline'):
            for n in tv[cat]['notes']:
                checked += 1
                others = teams_in(n['q']) - {t}
                if others:
                    violations += 1
                    print('  !! %s/%s also names %s: %s' % (t, cat, others, n['q'][:80]))
        for n in tv['coordinator'].get('all_notes', []):
            checked += 1
            others = teams_in(n['q']) - {t}
            if others:
                violations += 1
                print('  !! %s/coord also names %s: %s' % (t, others, n['q'][:80]))
    print('  checked %d attributed corpus sentences; multi-team violations = %d' % (checked, violations))
    print('  -> PASS: no sentence attributed to >1 team.' if violations == 0 else '  -> FAIL: see above.')
    print()
    print('FILES WRITTEN:')
    print('  ', P('personnel_changes.json'))
    print('  ', P('PERSONNEL.md'))

if __name__ == '__main__':
    verify()
