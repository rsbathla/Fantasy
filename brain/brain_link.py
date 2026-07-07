#!/usr/bin/env python3
"""brain_link.py — the condenser. Reads captured source notes, extracts CLAIMS, and appends them
(dated, sourced, deduped) into the ## Intel log of the entity pages brain_pages.py generated.

Extractor v1: STEALING SIGNALS notes. Gretch pre-labels his film-signal per game as "Signal:" /
"Noise:" items — a structured taxonomy, parsed deterministically (no model guessing):
  game heading ("Chargers 27, Titans 17") -> Signal/Noise paragraphs -> per-item player claims.

Handles trafilatura's bold-boundary mangling ("with**Hayden Hurst**back" -> "withHayden Hurstback")
via a case-boundary-repair variant plus prefix-tolerant full-name matching on item text.

Idempotent: every appended claim is hashed into _status/intel_claims.json; re-runs add nothing.
Append-only: writes ONLY new lines under "## Intel log"; never touches Model read or Notes.

  python3 brain/brain_link.py --vault ~/Downloads/NFL-Brain --dry-run     # show claims, write nothing
  python3 brain/brain_link.py --vault ~/Downloads/NFL-Brain               # file them into player pages
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

import brain_common as bc

GAME_RE = re.compile(r"(?m)^#{1,5}\s+(.+?\s\d+,\s.+?\s\d+)\s*$")     # "Chargers 27, Titans 17"
LABEL_RE = re.compile(r"(?m)^(Signal|Noise):\s*(.+?)(?=\n\s*\n|\n(?:Signal|Noise):|\Z)", re.S)


def despace_variant(text):
    """Insert spaces at lowercase->Uppercase joins (repairs most bold-boundary mangling)."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)


def find_players_in_item(item, players_map):
    """Player display names in one Signal/Noise item, in order of first appearance.
    Prefix-tolerant full-name match (mangled trailing joins like 'Hurstback' still hit),
    run on both the raw item and the case-repaired variant. Each display name also matches
    with its generational suffix stripped — Gretch writes 'James Cook', the roster says
    'James Cook III', and before this variant existed those claims were silently dropped."""
    hits = {}
    for variant in (item, despace_variant(item)):
        low = variant.lower().replace("'", "").replace("’", "")
        for disp in players_map:
            names = {disp, " ".join(bc._base_words(disp))}
            for nm in names:
                key = nm.lower().replace("'", "").replace("’", "").replace(".", r"\.?")
                m = re.search(r"(?<![a-z])" + key.replace(" ", r"\s*"), low)
                if m and (disp not in hits or m.start() < hits[disp]):
                    hits[disp] = m.start()
    return [d for d, _ in sorted(hits.items(), key=lambda x: x[1])]


def claims_path(vault):
    d = os.path.join(vault, "_status")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "intel_claims.json")


def parse_stealing_signals(text):
    """[(game_or_None, 'Signal'|'Noise', item_text), ...] — items split on ';' within each block."""
    out = []
    # map every position to the most recent game heading above it
    games = [(m.start(), m.group(1).strip()) for m in GAME_RE.finditer(text)]
    def game_at(pos):
        g = None
        for p, name in games:
            if p <= pos:
                g = name
            else:
                break
        return g
    for m in LABEL_RE.finditer(text):
        label, block = m.group(1), m.group(2).strip()
        for item in re.split(r";\s*", block):
            item = " ".join(item.split())
            if len(item) >= 25:                      # drop stubs
                out.append((game_at(m.start()), label, item))
    return out


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

def _claim_date(line):
    """Sort key: the LAST date in the line (the source-note link), '' if undated."""
    m = _DATE_RE.findall(line)
    return m[-1] if m else ""

def intel_append(page_path, lines):
    """Add lines under '## Intel log' and keep the zone NEWEST-FIRST. Only dated claim
    bullets are (re)ordered; the header, zone hint, and user free-text stay in place."""
    txt = open(page_path, encoding="utf-8").read()
    i = txt.find("## Intel log")
    if i < 0:
        return False
    end = txt.find("\n## ", i + 5)                   # end of the Intel log zone (next section)
    if end < 0:
        end = len(txt)
    zone = txt[i:end]
    zlines = zone.split("\n")
    bullets = [l for l in zlines if l.lstrip().startswith("- ") and _claim_date(l)]
    keep = [l for l in zlines if l not in bullets and l.strip()]   # header, hint, user notes
    bullets += [f"- {ln}" for ln in lines]
    bullets.sort(key=_claim_date, reverse=True)      # newest first
    new = txt[:i] + "\n".join(keep + bullets) + "\n" + txt[end:].lstrip("\n")
    open(page_path, "w", encoding="utf-8").write(new)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--match", default="stealing signals", help="filename filter for source notes")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)
    players_map = bc.load_players(repo)              # display names (keys) drive matching

    cpath = claims_path(vault)
    done = {}
    if os.path.exists(cpath):
        try:
            done = json.load(open(cpath))
        except Exception:
            done = {}

    sources = sorted(p for p in glob.glob(os.path.join(vault, "Sources", "*.md"))
                     if a.match.lower() in os.path.basename(p).lower())
    bc.log(f"condenser: {len(sources)} source notes match '{a.match}'")

    n_claims = n_new = n_filed = 0
    missing_pages, per_player = set(), {}
    for sp in sources:
        note = os.path.basename(sp)[:-3]
        text = open(sp, encoding="utf-8").read()
        # label from the note title: "... Week 10 Part 2" -> SS W10
        wk = re.search(r"Week\s*(\d+)", note, re.I)
        season = re.search(r"\b(20\d\d)-", note)
        tag = "SS" + (f" {season.group(1)}" if season else "") + (f" W{wk.group(1)}" if wk else "")
        for game, label, item in parse_stealing_signals(text):
            n_claims += 1
            players = find_players_in_item(item, players_map)
            if not players:
                continue
            lead = players[0]
            h = hashlib.sha1(f"{note}|{lead}|{item[:100]}".encode()).hexdigest()[:16]
            if h in done:
                continue
            n_new += 1
            line = (f"**[{tag} · {label}]** {item[:400]}"
                    + (f" _({game})_" if game else "") + f" — [[{note}]]")
            if a.dry_run:
                per_player.setdefault(lead, []).append(line)
                continue
            page = os.path.join(vault, "Players", bc.slug(lead, 80) + ".md")
            if not os.path.exists(page):
                missing_pages.add(lead)
                continue
            if intel_append(page, [line]):
                n_filed += 1
                done[h] = {"player": lead, "note": note}
        if not a.dry_run:
            json.dump(done, open(cpath, "w"), indent=1)

    if a.dry_run:
        for pl in sorted(per_player):
            print(f"\n### {pl} ({len(per_player[pl])} claims)")
            for ln in per_player[pl][:4]:
                print("  -", ln[:160])
    if missing_pages:
        bc.log(f"  no page for {len(missing_pages)} players (not in statmenu): "
               + ", ".join(sorted(missing_pages)[:8]) + ("…" if len(missing_pages) > 8 else ""))
    bc.log(f"condenser: {n_claims} items parsed · {n_new} new claims · "
           f"{n_filed if not a.dry_run else 0} filed into player pages")
    print(json.dumps({"items": n_claims, "new": n_new, "filed": (0 if a.dry_run else n_filed),
                      "players_missing_page": len(missing_pages)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
