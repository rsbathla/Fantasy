#!/usr/bin/env python3
"""brain_repair_mentions.py — one-shot vault repair after a resolver fix. Re-runs entity detection
over every captured tweet and source note with the CURRENT brain_common rules and rewrites the
`mentions:` frontmatter plus the `**Mentions:**` body line wherever the result changed. Nothing
else in any note is touched; Obsidian backlinks heal automatically because they come from these
lines.

Why it exists (2026-07-05 audit): bare-surname keys had six false-positive classes — 'likely' the
adverb (200 bad Isaiah Likely links), 'pitcher' the baseball noun (94 bad Dan Pitcher links),
surnames equal to other players' FIRST names (Jordan James <- James Cook, Christian Parker <-
Parker Washington), generational-suffix surnames counted as 'Jr' (Brian Thomas Jr. tweets linked
Zavion Thomas; Travis Etienne Jr. tweets linked Trevor), player/coach surname collisions
(J.J. McCarthy <- Mike McCarthy), and @handles (@_John_Shipley -> Will Shipley). Idempotent:
re-running after the vault is clean changes nothing.

  python3 brain/brain_repair_mentions.py --vault ~/Downloads/NFL-Brain --dry-run   # report only
  python3 brain/brain_repair_mentions.py --vault ~/Downloads/NFL-Brain             # rewrite
"""
import argparse
import collections
import glob
import os
import re
import sys

import brain_common as bc

FM_MENTIONS_RE = re.compile(r"(?m)^mentions: .*$")
BODY_MENTIONS_RE = re.compile(r"(?m)^\*\*Mentions:\*\* .*$")


def note_kind(txt):
    m = re.search(r"(?m)^type: (.+)$", txt[:400])
    return m.group(1).strip() if m else ""


def tweet_text(body):
    lines = [ln[2:] for ln in body.splitlines()
             if ln.startswith("> ") and not ln.startswith("> [!quote]")]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)

    # detection maps are static per run — cache them so 6k notes don't re-read statmenu 12k times
    _pm = bc.load_players(repo)
    _cm = bc.load_coaches(repo)
    bc.load_players = lambda r: _pm
    bc.load_coaches = lambda r: _cm

    notes = sorted(glob.glob(os.path.join(vault, "Tweets", "*", "*.md"))) + \
        sorted(glob.glob(os.path.join(vault, "Sources", "*.md")))
    bc.log(f"repair: rechecking {len(notes)} notes with current resolver rules")

    changed = now_empty = 0
    adds, drops = collections.Counter(), collections.Counter()
    for i, p in enumerate(notes, 1):
        txt = open(p, encoding="utf-8").read()
        kind = note_kind(txt)
        if kind == "book-chapter":                      # chapter team fold-in is brain_book's job
            continue
        end = txt.find("\n---", 3)
        if end < 0:
            continue
        body = txt[end + 4:]
        fm_m = FM_MENTIONS_RE.search(txt[:end + 4])
        old = set(re.findall(r"\[\[([^\]]+)\]\]", fm_m.group(0))) if fm_m else set()
        det_text = tweet_text(body) if kind == "tweet" else body
        players, teams, coaches = bc.detect_entities(det_text, repo)
        new = players + teams + coaches
        if set(new) == old:
            continue
        changed += 1
        for m in set(new) - old:
            adds[m] += 1
        for m in old - set(new):
            drops[m] += 1
        if not new:
            now_empty += 1
        if not a.dry_run:
            fm_line = f"mentions: [{bc.wikilinks(new)}]"
            body_line = ("**Mentions:** " +
                         (", ".join(f"[[{m}]]" for m in new) if new else "_none detected_"))
            txt2 = FM_MENTIONS_RE.sub(lambda _: fm_line, txt, count=1)
            txt2 = BODY_MENTIONS_RE.sub(lambda _: body_line, txt2, count=1)
            open(p, "w", encoding="utf-8").write(txt2)
        if i % 1000 == 0:
            bc.log(f"  …{i}/{len(notes)} checked · {changed} changed")

    bc.log(f"repair: {changed} notes rewritten ({'DRY RUN — nothing written' if a.dry_run else 'applied'}) "
           f"· {now_empty} now have no entities at all")
    def show(c, label):
        if c:
            print(f"\n{label}:")
            for nm, n in c.most_common(12):
                print(f"  {nm:28s} {n:>4} notes")
    show(drops, "TOP DROPS (false links removed)")
    show(adds, "TOP ADDS (links the old rules missed)")
    print(f'\n{{"checked": {len(notes)}, "changed": {changed}, "now_empty": {now_empty}}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
