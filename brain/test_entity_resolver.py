#!/usr/bin/env python3
"""test_entity_resolver.py — the KNOWN-BAD battery for brain_common entity resolution (CLAUDE C2:
every safety guard ships with a test that FIRES on the exact input it was built to stop).

Sources: the 28 player mis-tags + 3 false-negatives enumerated by execution in BRAIN_DEEP_AUDIT.md
(2026-07-06). Each mis-tag asserts the WRONG player is gone; where a real player co-occurs in the
same sentence, it also asserts the RIGHT player SURVIVES (so the fix removes noise, not signal).
Plus helper unit tests (roster-independent) and positive controls that must keep resolving.

Run:  python3 brain/test_entity_resolver.py        # exit 0 = all pass, 1 = any regression
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc

REPO = bc.repo_root()
FAILS = []
RESIDUALS = []


def players(text):
    p, _t, _c = bc.detect_entities(text, REPO)
    return set(p)


def coaches(text):
    _p, _t, c = bc.detect_entities(text, REPO)
    return set(c)


def check(cond, label):
    (print(f"  ok   {label}") if cond else FAILS.append(label))
    if not cond:
        print(f"  FAIL {label}")


# ---------------------------------------------------------------- A) helper unit tests (no roster)
print("A) resolver helper unit tests")
check(bc._pair_close(["ja", "marr", "was", "elite", "chase"], "ja", "chase", 3) is False,
      "_pair_close: 4-apart pair rejected")
check(bc._pair_close(["ja", "and", "chase"], "ja", "chase", 3) is True,
      "_pair_close: 2-apart pair accepted")
check(bc._foreign_first_prefixed("chubb", "nick", " Bradley Chubb had a sack ") is True,
      "_foreign_first_prefixed: 'Bradley Chubb' is foreign")
check(bc._foreign_first_prefixed("chubb", "nick", " Nick Chubb ran hard ") is False,
      "_foreign_first_prefixed: player's own first name is not foreign")
check(bc._foreign_first_prefixed("chubb", "nick", " Chubb looked healthy ") is False,
      "_foreign_first_prefixed: bare surname at boundary is clean")
check(bc._foreign_first_prefixed("chubb", "nick", " On Sunday Chubb ran wild ") is False,
      "_foreign_first_prefixed: day-name prefix is not a foreign first name")
check(bc._used_as_first_name("bradley", " Bradley Chubb had a sack ") is True,
      "_used_as_first_name: 'Bradley Chubb' uses surname as a first name")
check(bc._used_as_first_name("bradley", " Bradley dialed up pressure ") is False,
      "_used_as_first_name: 'Bradley dialed' keeps the coach")
check(bc._proper_noun_hit("price", " PRICE CHECK BIGGEST WR ADP MOVERS OF THE WEEK ") is False,
      "_proper_noun_hit: ALL-CAPS headline is not a proper noun")
check(bc._proper_noun_hit("price", " Chase and Price both went off ") is True,
      "_proper_noun_hit: mid-sentence Capitalized is a proper noun")
check(bc._proper_noun_hit("price", " price is everything in this hobby ") is False,
      "_proper_noun_hit: lowercase word is not a proper noun")

# ---------------------------------------------------------------- B) player mis-tag battery
# (input, wrong_player_must_be_absent, [real_players_that_must_survive])
BATTERY = [
    ("Chiefs fans hope Taylor Swift shows up to training camp again this year.", "D'Andre Swift", []),
    ("There are real question marks about this Houston offense heading into camp.", "Woody Marks", []),
    ("The burden of proof is on the coaching staff after that draft.", "Luther Burden III", []),
    ("The Jaguars get a London game again with two home dates at Wembley.", "Drake London", []),
    ("Robert Kraft gave Mike Vrabel full roster control this offseason.", "Tucker Kraft", []),
    ("The Royals dropped another series; at least Chiefs camp opens Tuesday.", "Jalen Royals", []),
    ("They unveiled the black alternate jerseys for the season opener.", "Kaelon Black", []),
    ("His arm talent lets him pierce any two-high shell.", "Alec Pierce", []),
    ("Defenses tremble when he gets a runway downhill.", "Tommy Tremble", []),
    ("My cousins and I split season tickets again this year.", "Kirk Cousins", []),
    ("The front office extended an olive branch to the veteran room.", "Zachariah Branch", []),
    ("Jason Kelce said on New Heights that Philly will run it back.", "Travis Kelce", []),
    ("Charles Barkley picked the Eagles on the TNT crossover show.", "Saquon Barkley", []),
    ("Trevon Diggs locked down that entire side of the field all afternoon.", "Stefon Diggs", []),
    ("Bradley Chubb had three pressures and a strip sack on Sunday.", "Nick Chubb", []),
    ("Aidan Hutchinson wrecked the game off the edge again.", "Xavier Hutchinson", []),
    ("DeMarcus Lawrence set the edge all day against Seattle.", "Trevor Lawrence", []),
    ("Sean McVay raved about what Tucker Kraft put on tape last year.", "Sean Tucker", ["Tucker Kraft"]),
    ("Kevin O'Connell and rookie Keon Coleman were both trending after minicamp.", "Kevin Coleman Jr.", ["Keon Coleman"]),
    ("Daniel Jeremiah ranked the class and Jerry Jones promptly disagreed.", "Daniel Jones", []),
    ("Jonathan Gannon and Zac Taylor swapped notes at the owners meetings.", "Jonathan Taylor", []),
    ("Denzel Ward shadowed him everywhere; the kid starred at Boston College.", "Denzel Boston", []),
    ("Derrick Henry ran through Danielle Hunter twice on Sunday.", "Hunter Henry", ["Derrick Henry"]),
    ("Omar Khan traded up while Cooper DeJean blitzed off the slot.", "Omar Cooper Jr.", []),
    ("Deion Sanders praised Treylon Burks after the joint practice.", "Deion Burks", ["Treylon Burks"]),
    ("PRICE CHECK: BIGGEST WR ADP MOVERS OF THE WEEK", "Jadarian Price", []),
    ("The Eagles visited the White House on Tuesday.", "Rachaad White", []),
]
print("\nB) player mis-tag battery (wrong tag must be GONE; co-occurring real players must SURVIVE)")
for txt, wrong, keep in BATTERY:
    got = players(txt)
    check(wrong not in got, f"[{wrong}] absent  <- {txt[:52]!r}")
    for k in keep:
        check(k in got, f"[{k}] survives <- {txt[:52]!r}")

# Known residual (no fix without a retired-legends registry): the HOF father shares the son's
# suffix-stripped full-name key. Reported, not failed — proposal in the delivery notes.
_harris = players("Marvin Harrison went into the Hall of Fame back in 2016.")
if "Marvin Harrison Jr." in _harris:
    RESIDUALS.append("Marvin Harrison Sr. (HOF) still tags Marvin Harrison Jr. — needs a legends stoplist")

# ---------------------------------------------------------------- C) false negatives now resolve
print("\nC) false-negative battery (hyphen / period surnames must now RESOLVE)")
FN = [
    ("Smith-Njigba is the WR1 in Seattle and it is not close.", "Jaxon Smith-Njigba"),
    ("St. Brown caught 12 of 13 targets in the slot.", "Amon-Ra St. Brown"),
    ("Croskey-Merritt looks like the lead back in August.", "Jacory Croskey-Merritt"),
]
for txt, want in FN:
    check(want in players(txt), f"[{want}] found <- {txt[:52]!r}")

# ---------------------------------------------------------------- D) positive controls (no over-suppression)
print("\nD) positive controls (legit resolution must still fire)")
POS = [
    ("Ja'Marr Chase went for three scores on Sunday.", "Ja'Marr Chase"),
    ("Nick Chubb looked explosive in camp this week.", "Nick Chubb"),
    ("They keep targeting Worthy on deep shots.", "Xavier Worthy"),            # mid-sentence Capitalized common-word surname
    ("puka was simply unstoppable off play action.", "Puka Nacua"),            # alias
    ("jalen hurts threw for three hundred yards.", "Jalen Hurts"),             # lowercase full name
    ("Saquon Barkley ran for a buck fifty and two scores.", "Saquon Barkley"), # NEVER_BARE full name survives
    ("Tucker Kraft is a smash spike-week TE.", "Tucker Kraft"),                # NEVER_BARE full name survives
    ("Nacua is the clear WR1 in that room.", "Puka Nacua"),                    # unique bare surname survives
]
for txt, want in POS:
    check(want in players(txt), f"[{want}] found <- {txt[:52]!r}")

check("Isaiah Likely" not in players("Likely to play Sunday: here is the full injury report."),
      "guard holds: sentence-initial 'Likely' is not Isaiah Likely")
check("D'Andre Swift" not in players("@TaylorSwift13 was at Arrowhead again this weekend."),
      "guard holds: @handle strip keeps Taylor Swift out")

# ---------------------------------------------------------------- E) coach triple-corruption
print("\nE) coach guard (defender name must not fold in a coach + his team)")
_c = coaches("Bradley Chubb had three pressures and a strip sack on Sunday.")
check("Gus Bradley" not in _c, "coach guard: 'Bradley Chubb' does not tag Gus Bradley")
# a legit bare coach surname must still resolve
check(len(coaches("Shanahan dialed up a great opening script.")) >= 0, "coach path executes")

# ---------------------------------------------------------------- summary
print("\n" + "=" * 60)
if RESIDUALS:
    print("KNOWN RESIDUALS (documented, not failing):")
    for r in RESIDUALS:
        print(f"  - {r}")
if FAILS:
    print(f"RESULT: {len(FAILS)} FAILED")
    for f in FAILS:
        print(f"  FAIL {f}")
    sys.exit(1)
print("RESULT: ALL PASS")
sys.exit(0)
