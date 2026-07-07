#!/usr/bin/env python3
"""brain_common.py — shared helpers for the NFL-Brain ingest pipeline.

Entity resolution (which players/teams a text mentions), vault paths, an idempotency manifest,
slugging, and logging. Runs on the user's Mac against the cloned Fantasy repo (for the player/team
roster) and writes into the Obsidian vault.

No network. Pure text + file helpers.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

# ---------------------------------------------------------------- repo + vault
def repo_root(explicit=None):
    """Locate the Fantasy repo (for boom/statmenu.json). Default: this file's parent's parent."""
    if explicit:
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.dirname(here), here, os.getcwd()):
        if os.path.exists(os.path.join(cand, "boom", "statmenu.json")):
            return cand
    return os.path.dirname(here)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def slug(s, maxlen=80):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s.-]", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:maxlen].strip() or "untitled"


def now_utc():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- idempotency manifest
def manifest_path(vault):
    d = os.path.join(vault, "_status")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "ingested.json")


def load_manifest(vault):
    p = manifest_path(vault)
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            return {}
    return {}


def save_manifest(vault, m):
    json.dump(m, open(manifest_path(vault), "w"), indent=1)


def already_done(vault, key):
    return key in load_manifest(vault)


def mark_done(vault, key, note_rel):
    m = load_manifest(vault)
    m[key] = {"note": note_rel, "at": now_utc().isoformat(timespec="seconds")}
    save_manifest(vault, m)


# ---------------------------------------------------------------- entity resolution
_TEAMS = {
    "ARI": ["Arizona Cardinals", "Cardinals", "Arizona"], "ATL": ["Atlanta Falcons", "Falcons", "Atlanta"],
    "BAL": ["Baltimore Ravens", "Ravens", "Baltimore"], "BUF": ["Buffalo Bills", "Bills", "Buffalo"],
    "CAR": ["Carolina Panthers", "Panthers", "Carolina"], "CHI": ["Chicago Bears", "Bears", "Chicago"],
    "CIN": ["Cincinnati Bengals", "Bengals", "Cincinnati"], "CLE": ["Cleveland Browns", "Browns", "Cleveland"],
    "DAL": ["Dallas Cowboys", "Cowboys", "Dallas"], "DEN": ["Denver Broncos", "Broncos", "Denver"],
    "DET": ["Detroit Lions", "Lions", "Detroit"], "GB": ["Green Bay Packers", "Packers", "Green Bay"],
    "HOU": ["Houston Texans", "Texans", "Houston"], "IND": ["Indianapolis Colts", "Colts", "Indianapolis"],
    "JAX": ["Jacksonville Jaguars", "Jaguars", "Jacksonville", "Jags"], "KC": ["Kansas City Chiefs", "Chiefs", "Kansas City"],
    "LV": ["Las Vegas Raiders", "Raiders", "Las Vegas"], "LAC": ["Los Angeles Chargers", "Chargers"],
    "LAR": ["Los Angeles Rams", "Rams"], "MIA": ["Miami Dolphins", "Dolphins", "Miami"],
    "MIN": ["Minnesota Vikings", "Vikings", "Minnesota"], "NE": ["New England Patriots", "Patriots"],
    "NO": ["New Orleans Saints", "Saints", "New Orleans"], "NYG": ["New York Giants", "Giants"],
    "NYJ": ["New York Jets", "Jets"], "PHI": ["Philadelphia Eagles", "Eagles", "Philadelphia"],
    "PIT": ["Pittsburgh Steelers", "Steelers", "Pittsburgh"], "SF": ["San Francisco 49ers", "49ers", "Niners"],
    "SEA": ["Seattle Seahawks", "Seahawks", "Seattle"], "TB": ["Tampa Bay Buccaneers", "Buccaneers", "Bucs", "Tampa Bay", "Tampa"],
    "TEN": ["Tennessee Titans", "Titans", "Tennessee"], "WAS": ["Washington Commanders", "Commanders", "Washington"],
}
# curated short-form aliases that are unambiguous enough to match on their own
_ALIASES = {
    "jsn": "Jaxon Smith-Njigba", "cmc": "Christian McCaffrey", "ceedee": "CeeDee Lamb",
    "jamarr": "Ja'Marr Chase", "st brown": "Amon-Ra St. Brown", "st. brown": "Amon-Ra St. Brown",
    "sun god": "Amon-Ra St. Brown",
    "mhj": "Marvin Harrison Jr.", "nabers": "Malik Nabers", "bijan": "Bijan Robinson",
    "puka": "Puka Nacua", "jjettas": "Justin Jefferson", "jettas": "Justin Jefferson",
}
_TEAM_DISPLAY = {a: v[0] for v, k in [(v, k) for k, v in _TEAMS.items()] for a in [k] + v}


# Surnames that are also ordinary English words. Matching the bare last name in lowercased text
# creates false backlinks ("under price" -> Jadarian Price; "ups and downs" -> Josh Downs;
# "chase this group" -> Ja'Marr Chase). For these we still allow a last-name-only match, but ONLY
# when the surname appears Capitalized as a standalone proper noun in the ORIGINAL text — so
# "Chase caught three" links while "chase the ball" does not. Full-name mentions always match.
_COMMON_WORD_SURNAMES = {
    "price", "chase", "downs", "brown", "white", "green", "young", "fields", "flowers",
    "sweat", "mills", "berry", "burrow", "banks", "rivers", "waters", "wells", "meadows",
    "means", "little",
    # 2026-07-05 vault audit additions — each produced real false positives in the live corpus:
    "likely",    # Isaiah Likely vs the adverb ("will likely get creative") — 200 bad links
    "hurts",     # Jalen Hurts vs the verb ("it hurts to fade him")
    "golden",    # Matthew Golden vs "golden opportunity"
    "worthy",    # Xavier Worthy vs "worthy of a pick"
    "strange",   # Brenton Strange vs the adjective
    "waddle",    # Jaylen Waddle vs the verb
    "pitcher",   # Dan Pitcher (CIN OC) vs baseball — 94 Phillies/Red Sox tweets linked him
    # 2026-07-06 deep-audit additions — ordinary English words / lower-case-in-context surnames.
    # Cap-only: match "Marks"/"Burden" capitalized, never the bare noun ("question marks",
    # "burden of proof"). Each fired in the executed battery (BRAIN_DEEP_AUDIT.md §1a).
    "marks",     # Woody Marks vs "question marks"
    "burden",    # Luther Burden III vs "burden of proof"
    "black",     # Kaelon Black vs "black alternate jerseys"
    "pierce",    # Alec Pierce vs the verb ("pierce any two-high shell")
    "tremble",   # Tommy Tremble vs the verb ("defenses tremble")
    "cousins",   # Kirk Cousins vs "my cousins"
    "branch",    # Zachariah Branch vs "olive branch"
    "harvey",    # RJ Harvey vs Steve/Hurricane Harvey
    "hampton",   # Omarion Hampton vs the city
    "spears",    # Tyjae Spears vs the noun
    "irving",    # Bucky Irving vs Kyrie / Irving TX
    "montgomery",# David Montgomery vs the city
    "jackson",   # Lamar Jackson vs any other Jackson / the city
    "howard",    # Will Howard vs Howard University
    "simpson",   # Ty Simpson vs the surname at large
    "rodriguez", # Chris Rodriguez Jr. vs the common surname
    "tracy",     # Tyrone Tracy Jr. vs the given name
    "lemon",     # Makai Lemon vs the fruit
}

# Surnames that must NEVER get a bare key, not even Capitalized: a mid-sentence Capitalized hit is
# still ambiguous because the word is a city / famous cross-domain proper noun in its own right.
# "Boston Red Sox", "Taylor Swift", "London", "the Royals", "Robert Kraft", "Jason Kelce",
# "Charles Barkley", "the White House" are ALL capitalized in their normal (non-NFL) use, so the
# capitalized-proper-noun gate can't save them — only the full name or a distinctive-first-name
# corroboration may link these players. (Confirmed LIVE contamination: a Tampa Bay Rays tweet on
# Jalen Royals' card and a Charles Barkley tweet on Saquon Barkley's card, brain_intel.json 2026-07-05.)
_NEVER_BARE_SURNAMES = {
    "boston",                                            # Denzel Boston vs Boston (city)
    "swift",                                             # D'Andre Swift vs Taylor Swift
    "london",                                            # Drake London vs London (city / the game)
    "royals",                                            # Jalen Royals vs the Royals (MLB)  [LIVE]
    "kraft",                                             # Tucker Kraft vs Robert Kraft
    "kelce",                                             # Travis Kelce vs Jason Kelce
    "barkley",                                           # Saquon Barkley vs Charles Barkley [LIVE]
    "white",                                             # Rachaad White vs the White House
}

# ---- resolver tuning (2026-07-06 deep audit) ----
CONTEXT_MAXGAP = 3          # a (first,last) corroboration pair must appear within this many words of
                            # each other in the SAME document — was document-wide, which manufactured
                            # phantom players from any two co-occurring names (Sean McVay + Tucker
                            # Kraft -> "Sean Tucker"). Adjacent full names still match via the full key.
_CAPS_HEADLINE_MIN = 4      # if a text has >= this many ALL-CAPS words, ALL-CAPS stops counting as a
                            # proper-noun signal (it's a headline/caps caption, not emphasis) — so
                            # "PRICE CHECK: BIGGEST WR ADP MOVERS" no longer tags Jadarian Price.

# Capitalized words that are NOT personal given names — a bare surname preceded by one of these
# (e.g. "Sunday Chubb") is NOT read as "SomeFirstName Chubb", so the offensive player is still linked.
_NAME_STOP = {
    "the", "a", "an", "on", "in", "at", "but", "and", "or", "when", "after", "before", "this",
    "that", "these", "those", "his", "her", "their", "my", "our", "your", "no", "if", "as", "so",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
    "coach", "rookie", "veteran", "sir", "night", "week", "camp", "draft", "hall", "fame",
}

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _base_words(nm):
    """Name words minus any generational suffix: 'Brian Thomas Jr.' -> ['Brian','Thomas'].
    Raw split()[-1] treated 'Jr' as the surname, which (a) made colliding surnames look unique
    ('thomas' seemed to belong only to Zavion Thomas, 'etienne' only to Trevor) and (b) meant the
    full-name key 'brian thomas jr.' never matched text that says 'Brian Thomas'."""
    ws = nm.split()
    while len(ws) > 1 and _letters(ws[-1]) in _SUFFIXES:
        ws = ws[:-1]
    return ws


def _strip_handles(text):
    """Remove @handles before entity matching. Beat-writer handles embed player surnames
    (@_John_Shipley -> bare 'shipley' linked Will Shipley). Full names never matched inside a
    handle anyway (no spaces), so stripping only removes the false-positive class."""
    return re.sub(r"@\w+", " ", text)


def _letters(s):
    return re.sub(r"[^a-z]", "", s.lower())


def _norm_words(text):
    """lowercase, drop apostrophes so "Ja'Marr" -> "jamarr", turn other non-letters into spaces."""
    t = text.lower().replace("'", "").replace("’", "")
    return " " + re.sub(r"[^a-z]+", " ", t).strip() + " "


def _pair_close(words, a, b, maxgap=CONTEXT_MAXGAP):
    """True if letters-only words `a` and `b` occur within `maxgap` words of each other in the token
    list `words`. Proximity corroboration: 'Ja'Marr ... Chase' close together is Ja'Marr Chase;
    'Sean McVay ... Tucker Kraft' (5 words apart) is NOT 'Sean Tucker'."""
    ia = [i for i, w in enumerate(words) if w == a]
    ib = [i for i, w in enumerate(words) if w == b]
    return any(abs(i - j) <= maxgap for i in ia for j in ib)


def _prev_word(text, start):
    """The word immediately before position `start` in `text` (letters + internal '/-), or '' at a
    sentence/line boundary. Stops at sentence punctuation so '...it. Chubb' yields ''."""
    j = start - 1
    while j >= 0 and text[j] == " ":
        j -= 1
    e = j
    while j >= 0 and (text[j].isalpha() or text[j] in "'-"):
        j -= 1
    return text[j + 1:e + 1]


def _next_word(text, end):
    """The word immediately after position `end` in `text`, or '' at a boundary."""
    j = end
    while j < len(text) and text[j] == " ":
        j += 1
    s = j
    while j < len(text) and (text[j].isalpha() or text[j] in "'-"):
        j += 1
    return text[s:j]


def _looks_like_given_name(w):
    """A capitalized token that plausibly is a person's FIRST name (not a day/month/role/word)."""
    return bool(w) and w[:1].isupper() and len(_letters(w)) >= 3 and _letters(w) not in _NAME_STOP


def _foreign_first_prefixed(surname, own_first, text):
    """True when EVERY case-insensitive occurrence of `surname` in `text` is immediately preceded by a
    capitalized given name that is NOT the player's own first name — i.e. the text always names a
    DIFFERENT person of that surname ('Trevon Diggs', 'Bradley Chubb', 'Aidan Hutchinson'). If any
    occurrence stands alone or follows the player's own first name, returns False (keep the link).
    This is the data-light generalization of the defender/retired negative-roster guard: it needs no
    external roster and covers edge rushers and family names the CB-only grades file misses."""
    occ = list(re.finditer(r"(?<![A-Za-z])" + re.escape(surname) + r"(?![A-Za-z])", text, re.I))
    if not occ:
        return False
    for m in occ:
        prev = _prev_word(text, m.start())
        if not prev or _letters(prev) == own_first:   # boundary, or the player himself -> clean
            return False
        if not prev[:1].isupper():                    # lowercase word -> not a name -> clean
            return False
        if not _looks_like_given_name(prev):          # day/month/role/short -> not a foreign name
            return False
    return True                                       # all occurrences were 'ForeignFirst Surname'


def _used_as_first_name(surname, text):
    """Mirror of the above for COACH bare keys: True when every occurrence of `surname` is immediately
    FOLLOWED by a capitalized surname token — i.e. the coach's last name is being used as someone's
    FIRST name ('Bradley Chubb' is the edge rusher, not Gus Bradley). Kills the coach+team fold-in
    triple-corruption (BRAIN_DEEP_AUDIT.md §1b)."""
    occ = list(re.finditer(r"(?<![A-Za-z])" + re.escape(surname) + r"(?![A-Za-z])", text, re.I))
    if not occ:
        return False
    for m in occ:
        nxt = _next_word(text, m.end())
        if not _looks_like_given_name(nxt):
            return False
    return True


def _proper_noun_hit(word, text):
    """True if `word` appears as a proper noun in `text`. ALL-CAPS counts (titles/emphasis) EXCEPT
    inside an all-caps headline/caption (>= _CAPS_HEADLINE_MIN caps words), where capitalization
    carries no signal ("PRICE CHECK: BIGGEST WR ADP MOVERS" is not Jadarian Price). A mixed-case
    Capitalized hit counts only mid-sentence — NOT at the start or right after . ! ? — because
    ordinary words get auto-capitalized there ("Price is everything" is not the running back)."""
    caps_heavy = len(re.findall(r"(?<![A-Za-z])[A-Z]{2,}(?![a-z])", text)) >= _CAPS_HEADLINE_MIN
    rx = re.compile(r"(?<![A-Za-z])" + re.escape(word[:1].upper()) + r"(?i:" + re.escape(word[1:]) + r")(?![a-z])")
    for m in rx.finditer(text):
        if m.group(0).isupper():
            if caps_heavy:
                continue                             # ALL-CAPS headline — not a distinguishing signal
            return True                              # lone ALL-CAPS — strong emphasis signal
        j = m.start() - 1
        while j >= 0 and text[j] in " \t\"'([":      # skip spaces and opening quotes/brackets
            j -= 1
        if j >= 0 and text[j] not in ".!?\n":        # capitalized mid-sentence — genuine proper noun
            return True
    return False


def load_players(repo):
    """canonical display name -> (full, bare, cap, context).

    full     full-name variants — match case-insensitively ANYWHERE (always safe).
    bare     a unique, non-everyday last name (letters-only key + a hyphen/period-preserving variant
             so 'Smith-Njigba' isn't a dead key) — matched anywhere but VETOED when every occurrence
             reads 'ForeignFirst Surname' (a different person: 'Trevon Diggs', 'Bradley Chubb').
    cap      a unique last name that IS an everyday word (_COMMON_WORD_SURNAMES) — matched only as a
             Capitalized/ALL-CAPS proper noun (and never inside an all-caps headline).
    context  (first, last) when the player's first name is DISTINCTIVE (unique in the roster) — links a
             bare/blocked surname only when that first name appears WITHIN CONTEXT_MAXGAP words in the
             same document, so 'Ja'Marr ... Chase' links but 'Sean McVay ... Tucker Kraft' does not."""
    sm = json.load(open(os.path.join(repo, "boom", "statmenu.json")))
    last_count, first_count, names = {}, {}, []
    for k, v in sm.items():
        nm = v.get("name")
        if not nm:
            continue
        names.append(nm)
        bw = _base_words(nm)                       # suffix-stripped, so 'Thomas Jr.' counts as 'thomas'
        last_count[_letters(bw[-1])] = last_count.get(_letters(bw[-1]), 0) + 1
        first_count[_letters(bw[0])] = first_count.get(_letters(bw[0]), 0) + 1
    # coach surnames from the SAME canon detect_entities uses: a player bare-surname key must not
    # collide with a coach ("McCarthy" alone is Mike McCarthy at least as often as J.J.).
    coach_lasts = set()
    try:
        for t in json.load(open(os.path.join(repo, "web_teams.json"))):
            for role in ("hc", "oc", "dc"):
                if t.get(role):
                    coach_lasts.add(_letters(_base_words(t[role].strip())[-1]))
    except Exception:
        pass
    players = {}
    for nm in names:
        bw = _base_words(nm)
        last, first = _letters(bw[-1]), _letters(bw[0])
        last_raw = bw[-1].lower()          # keeps hyphens/periods: 'smith-njigba', 'croskey-merritt'
        base = " ".join(bw).lower()
        # full-name keys: raw, suffix-stripped, and period-less variants — 'Travis Etienne Jr.'
        # must match text saying 'Travis Etienne', and 'J.J. McCarthy' must match 'JJ McCarthy'.
        full = [nm.lower()]
        for var in (base, nm.lower().replace(".", ""), base.replace(".", "")):
            if var not in full:
                full.append(var)
        bare = []               # unique non-word last name (guarded against foreign first names)
        cap = []                # capitalized-only last-name keys (common-word surnames)
        context = None          # (first, last) corroboration for a distinctive first name
        distinctive_first = first_count.get(first) == 1 and len(first) >= 4
        if (last_count.get(last) == 1 and len(last) >= 5
                and last not in first_count            # 'james'/'parker' are other players' FIRST names
                and last not in coach_lasts            # 'mccarthy'/'moore' belong to coaches too
                and last not in _NEVER_BARE_SURNAMES): # 'boston'/'swift'/'kraft' cross-domain even Capitalized
            if last in _COMMON_WORD_SURNAMES:
                cap.append(last)
                if distinctive_first:
                    context = (first, last)
            else:
                bare.append(last)
                if last_raw != last and last_raw not in bare:
                    bare.append(last_raw)             # revive hyphenated/period surnames as live keys
        elif distinctive_first and last_count.get(last, 0) >= 1 and len(last) >= 5:
            # blocked or shared surname, but a distinctive first name lets the pair corroborate:
            # 'Denzel' + 'Boston' close together is Denzel Boston even though bare 'Boston' never links.
            context = (first, last)
        players[nm] = (full, bare, cap, context)
    return players


def detect_mentions(text, repo):
    """Return (players, teams) canonical display names mentioned in text. Conservative — full names,
    unambiguous last names, or curated aliases only. A last name links via: the full name (any case);
    a unique non-word surname anywhere (unless it reads 'ForeignFirst Surname'); a common-word surname
    only when Capitalized as a genuine proper noun; or the bare/blocked surname when the player's
    distinctive first name appears within a few words. A lone lowercase word with no corroboration
    stays out."""
    text = _strip_handles(text)         # @handles out first — surnames inside handles never count
    norm = re.sub(r"\s+", " ", text)
    t = " " + norm.lower() + " "        # case-insensitive matching (full names, normal surnames)
    t_orig = " " + norm + " "           # original case, for the proper-noun + foreign-first guards
    words = _norm_words(text).split()   # letters-only tokens, for first-name proximity corroboration
    players_map = load_players(repo)
    found_players = set()
    for disp, (full, bare, cap, context) in players_map.items():
        hit = any(re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t) for k in full)
        if not hit and bare:
            own_first = _letters(_base_words(disp)[0])
            for k in bare:
                if (re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t)
                        and not _foreign_first_prefixed(k, own_first, t_orig)):
                    hit = True
                    break
        if not hit and cap:
            hit = any(_proper_noun_hit(k, t_orig) for k in cap)
        if not hit and context:
            hit = _pair_close(words, context[0], context[1])
        if hit:
            found_players.add(disp)
    for al, disp in _ALIASES.items():
        if re.search(r"(?<![a-z])" + re.escape(al) + r"(?![a-z])", t):
            found_players.add(disp)
    found_teams = set()
    for abbr, names in _TEAMS.items():
        for nm in names:
            if re.search(r"(?<![a-z])" + re.escape(nm.lower()) + r"(?![a-z])", t):
                found_teams.add(names[0])
                break
    return sorted(found_players), sorted(found_teams)


# curated coach short-forms that are unambiguous on their own
_COACH_ALIASES = {"koc": "Kevin O'Connell"}


def load_coaches(repo):
    """coach display name -> (team_abbr, match_keys). Loaded from web_teams.json — the STRUCTURED
    coaching canon (hc/oc/dc per team, cross-checked against ground_truth_registry.json by
    integration_audit.py Check J). Never hardcode coach->team here: the carousel moves yearly and
    a hardcoded list is exactly the stale-label drift the audit exists to catch.
    A bare surname is a key only when it is unique across all coaches, >=5 letters, not an
    everyday word, and not any player's last name — so "Shanahan"/"McVay"/"Minter" link alone,
    while "Ben Johnson"/"Kellen Moore"/"Zac Taylor" require the full name."""
    wt = json.load(open(os.path.join(repo, "web_teams.json")))
    sm = json.load(open(os.path.join(repo, "boom", "statmenu.json")))
    player_lasts = {_letters(_base_words(v["name"])[-1]) for v in sm.values() if v.get("name")}
    player_firsts = {_letters(_base_words(v["name"])[0]) for v in sm.values() if v.get("name")}
    raw, last_count = [], {}
    for t in wt:
        for role in ("hc", "oc", "dc"):
            nm = (t.get(role) or "").strip()
            if nm:
                raw.append((nm, t["team"]))
                last = _letters(_base_words(nm)[-1])
                last_count[last] = last_count.get(last, 0) + 1
    coaches = {}
    for nm, team in raw:
        if nm in coaches:
            continue
        last = _letters(_base_words(nm)[-1])
        keys = [nm.lower()]
        base = " ".join(_base_words(nm)).lower()
        if base not in keys:
            keys.append(base)
        if (last_count[last] == 1 and len(last) >= 5
                and last not in _COMMON_WORD_SURNAMES     # 'pitcher' stays full-name-only
                and last not in player_lasts
                and last not in player_firsts             # 'parker' is Parker Washington's first name
                and last not in _NEVER_BARE_SURNAMES):
            keys.append(last)
        coaches[nm] = (team, keys)
    return coaches


def detect_entities(text, repo):
    """(players, teams, coaches) mentioned in text. Superset of detect_mentions: coaches resolve
    from the web_teams.json canon and FOLD THEIR TEAM into the teams list, so a play-caller take
    ("Monken's offense feasts") files under both the coach and his team."""
    players, teams = detect_mentions(text, repo)
    norm = re.sub(r"\s+", " ", _strip_handles(text))
    t = " " + norm.lower() + " "
    t_orig = " " + norm + " "                 # original case, for the bare-surname first-name veto
    found_teams, found_coaches = set(teams), set()
    coaches = load_coaches(repo)
    for disp, (team, keys) in coaches.items():
        for k in keys:
            if not re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t):
                continue
            # a bare (single-word) surname key is vetoed when it's actually someone's FIRST name
            # ('Bradley Chubb' is the edge rusher, not Gus Bradley); full-name keys are always safe.
            if " " not in k and _used_as_first_name(k, t_orig):
                continue
            found_coaches.add(disp)
            break
    for al, disp in _COACH_ALIASES.items():
        if disp in coaches and re.search(r"(?<![a-z])" + re.escape(al) + r"(?![a-z])", t):
            found_coaches.add(disp)
    for disp in found_coaches:
        full = _TEAMS.get(coaches[disp][0])
        if full:
            found_teams.add(full[0])
    return sorted(players), sorted(found_teams), sorted(found_coaches)


def wikilinks(names):
    return ", ".join(f'"[[{n}]]"' for n in names)


def write_note(vault, subdir, filename, content):
    d = os.path.join(vault, subdir)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, filename)
    open(p, "w", encoding="utf-8").write(content)
    return os.path.relpath(p, vault)


def write_status(vault, ok, summary_lines, errors=None):
    """Write _status/last-run.md — the glanceable health card you open in Obsidian."""
    errors = errors or []
    head = "✅ OK" if ok and not errors else ("⚠️ completed with errors" if ok else "❌ FAILED")
    body = [f"# Ingest — last run", "",
            f"> [!{'success' if ok and not errors else 'warning'}] {head} · {now_utc().strftime('%Y-%m-%d %H:%M UTC')}", ""]
    body += [f"- {ln}" for ln in summary_lines]
    if errors:
        body += ["", "## Errors", *[f"- {e}" for e in errors[:30]]]
        if len(errors) > 30:
            body.append(f"- …and {len(errors)-30} more")
    write_note(vault, "_status", "last-run.md", os.linesep.join(body) + os.linesep)
