#!/usr/bin/env python3
"""fp_puller.py — FantasyPoints Data Suite puller (seed-and-iterate), matched to the real DS v2 API.

Recreates the lost puller WITHOUT reverse-engineering FP's private API: you capture ONE real request
from your authenticated Data Suite session ("Copy as cURL"), and this replays it across the values of
a dimension, swapping only the filter. Everything about the wire format — URL, headers (incl. auth)
and body — comes from YOUR captured request, so nothing here is invented.

Matched to the real DS v2 request shape (confirmed from a live capture):
  POST https://fpds.fantasypoints.com/v2/ds/nfl/tools/player/receiving-advanced/values
    body.context.filterMatch  -> season / position / isGamePlayed         (the population)
    body.context.filterPlay   -> the play-level dimension being split, e.g.
        {"personnel": {"in": ["$$play.offense.personnel.personnelId", [5]]}}
    body.context.filterResult -> qualifiers (games/routes >= 1)
FP stores dimension values as INTERNAL CODES (personnel came back as [5], not "11"). So the personnel
sweep pulls by code and names files by code; the code→grouping map is resolved downstream by route
volume (11 personnel = by far the most routes, then 12, 21, 13, 22 ...).

SECURITY: your seed file holds a live bearer + cookies. Keep it LOCAL, gitignore it. This script never
prints header values (they're masked) and runs only on your machine — it never leaves it.

────────────────────────────────────────────────────────────────────────────────────────────────
CAPTURE THE SEED (once): Receiving tool @ fpds.fantasypoints.com → DevTools (Cmd+Opt+I) → Network →
Fetch/XHR → apply the Personnel filter → right-click the .../receiving-advanced/values request →
Copy → Copy as cURL → save as seed.sh in this folder.
RUN:
  python3 fp_puller.py --seed seed.sh --mode personnel --dry-run          # preview, sends nothing
  python3 fp_puller.py --seed seed.sh --mode base --out NFL-master/FP/2025/Receiving/base_season.csv
  python3 fp_puller.py --seed seed.sh --mode personnel --out-root NFL-master/FP_SWEEP/2025/Receiving
Options: --codes 1,2,3,4,5,6,7,8,9,10,11 (personnel codes to try) · --positions WR,TE,RB (override) ·
         --sleep 1.5 · --retries 4 · --rows-key a.b (if the row list isn't auto-found)
"""
import argparse, csv, json, os, re, sys, time, copy, urllib.request, urllib.error
from collections import Counter

PERSONNEL_PATH = "$$play.offense.personnel.personnelId"   # confirmed from a live capture


def _friendly(c):
    """FP raw field name -> the friendly schema the rest of the pipeline uses."""
    if c == "playerPosition":
        return "POS"
    if c == "teamAbbreviation":
        return "Team"
    for pre in ("playerStatsReceiving", "playerStatsPassing", "playerStatsRushing", "playerStats"):
        if c.startswith(pre) and len(c) > len(pre):
            return c[len(pre):]
    return c


def normalize_row(r):
    """Combine first/last -> Name, rename position/team, strip stat prefixes; keep other keys as-is."""
    out = {}
    nm = f"{r.get('playerFirstName', '').strip()} {r.get('playerLastName', '').strip()}".strip()
    if nm:
        out["Name"] = nm
    for k, v in r.items():
        if k in ("playerFirstName", "playerLastName"):
            continue
        out[_friendly(k)] = json.dumps(v) if isinstance(v, (dict, list)) else v
    return out


def parse_curl(text):
    """Parse a Chrome/Firefox 'Copy as cURL' blob → {method,url,headers{},body}."""
    t = text.replace("\\\n", " ").strip()
    m = re.search(r"curl\s+(?:-[A-Za-z-]+\s+\S+\s+)*?['\"]([^'\"]+)['\"]", t) or re.search(r"(https?://\S+)", t)
    url = m.group(1) if m else None
    headers = {}
    for hm in re.finditer(r"-H\s+'([^']+)'|-H\s+\"([^\"]+)\"", t):
        raw = hm.group(1) or hm.group(2)
        if ":" in raw:
            k, v = raw.split(":", 1); headers[k.strip()] = v.strip()
    cm = re.search(r"(?:-b|--cookie)\s+'([^']*)'", t)
    if cm and not any(k.lower() == "cookie" for k in headers):
        headers["Cookie"] = cm.group(1)
    bm = re.search(r"--data(?:-raw|-binary|-ascii)?\s+'((?:[^'\\]|\\.)*)'", t) or re.search(r"-d\s+'((?:[^'\\]|\\.)*)'", t)
    body = bm.group(1).encode().decode("unicode_escape") if bm else None
    method = "POST" if body else "GET"
    xm = re.search(r"-X\s+([A-Z]+)", t)
    if xm:
        method = xm.group(1)
    return {"method": method, "url": url, "headers": headers, "body": body}


def _find_key(node, key):
    """(parent, key) for the first occurrence of `key`; parent[key] is the value. Else (None, None)."""
    if isinstance(node, dict):
        if key in node:
            return node, key
        for v in node.values():
            r = _find_key(v, key)
            if r[0] is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = _find_key(v, key)
            if r[0] is not None:
                return r
    return None, None


def make_base(seed_body):
    """Unfiltered population pull: empty the play-level filter (filterPlay -> {})."""
    b = copy.deepcopy(seed_body)
    p, k = _find_key(b, "filterPlay")
    if p is not None:
        p[k] = {}
    return b


def make_dim(seed_body, dim_key, path, code):
    """Set filterPlay to a single dimension clause in FP's real shape: {dim:{'in':[path,[code]]}}."""
    b = copy.deepcopy(seed_body)
    p, k = _find_key(b, "filterPlay")
    if p is None:
        raise ValueError("seed body has no filterPlay object — is this a Data Suite 'values' request?")
    p[k] = {dim_key: {"in": [path, [code]]}}
    return b


def set_positions(body, positions):
    if not positions:
        return
    p, k = _find_key(body, "filterMatch")
    if p is not None and isinstance(p[k], dict):
        p[k]["player.position"] = {"in": positions}


def _walk_lists(node, path="", depth=0, acc=None):
    if acc is None:
        acc = []
    if depth > 9:
        return acc
    if isinstance(node, dict):
        for k, v in node.items():
            np = f"{path}.{k}".lstrip(".")
            if isinstance(v, list):
                acc.append((np, v))
            _walk_lists(v, np, depth + 1, acc)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_lists(v, f"{path}[{i}]", depth + 1, acc)
    return acc


def _walk_dod(node, path="", depth=0, acc=None):
    """Find dicts that are really keyed collections of row-dicts (grouping by playerId → {id:{row}})."""
    if acc is None:
        acc = []
    if depth > 9:
        return acc
    if isinstance(node, dict):
        vals = list(node.values())
        if len(vals) >= 5 and sum(isinstance(v, dict) for v in vals) >= 0.8 * len(vals):
            acc.append((path or "<root>", node))
        for k, v in node.items():
            _walk_dod(v, f"{path}.{k}".lstrip("."), depth + 1, acc)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_dod(v, f"{path}[{i}]", depth + 1, acc)
    return acc


def flatten_rows(resp, rows_key=None):
    """Locate the player-row list anywhere in FP's response envelope, robustly.
    Strategies, in order: explicit --rows-key · top-level list · deepest/longest list-of-dicts ·
    columnar (list-of-lists + a matching column-name list) · keyed dict-of-row-dicts."""
    rows = None
    if rows_key:
        cur = resp
        for part in rows_key.split("."):
            cur = cur[int(part)] if part.lstrip("-").isdigit() else cur[part]
        rows = cur
    elif isinstance(resp, list):
        rows = resp
    else:
        lists = _walk_lists(resp)
        lod = [(p, l) for p, l in lists if l and isinstance(l[0], dict)]
        if lod:
            rows = max(lod, key=lambda pl: len(pl[1]))[1]                       # longest list-of-dicts
        else:
            lol = [(p, l) for p, l in lists if l and isinstance(l[0], list)]     # columnar?
            colnames = [l for _, l in lists if l and all(isinstance(x, str) for x in l)]
            if lol:
                data = max(lol, key=lambda pl: len(pl[1]))[1]
                width = len(data[0]) if data else 0
                cols = next((c for c in colnames if len(c) == width), None)
                if cols:
                    rows = [dict(zip(cols, r)) for r in data]
            if rows is None:                                                     # keyed dict-of-dicts?
                dod = _walk_dod(resp)
                if dod:
                    rows = list(max(dod, key=lambda pd: len(pd[1]))[1].values())
    if rows is None:
        raise ValueError("could not locate the row list in the response; run --inspect and share the shape")
    return [normalize_row(r) for r in rows if isinstance(r, dict)]   # -> friendly schema (Name/POS/Team/…)


def skeleton(node, depth=0, maxd=5):
    """Compact structural summary of a JSON response — keys, list lengths, leaf types (no data values)."""
    ind = "  " * depth
    if isinstance(node, dict):
        lines = ["{"]
        for k, v in list(node.items())[:30]:
            lines.append(f"{ind}  {k}: {skeleton(v, depth + 1, maxd) if depth < maxd else type(v).__name__}")
        return "\n".join(lines) + f"\n{ind}}}"
    if isinstance(node, list):
        if node and depth < maxd:
            return f"[len={len(node)}] of " + skeleton(node[0], depth + 1, maxd)
        return f"[len={len(node)}]" + (f" of {type(node[0]).__name__}" if node else " empty")
    return type(node).__name__


def write_csv(rows, path):
    if not rows:
        return 0
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    cols = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    return len(rows)


def _mask(h):
    return {k: ("***" if k.lower() in ("authorization", "cookie", "x-api-key") else v) for k, v in h.items()}


def send(body_obj, seed, sleep, retries, dry):
    if dry:
        return {"_dry": True, "body_preview": json.dumps(body_obj)[:700]}
    data = json.dumps(body_obj).encode()
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(seed["url"], data=data, method=seed["method"] or "POST")
            for k, v in seed["headers"].items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503):
                wait = sleep * (2 ** attempt)
                sys.stderr.write(f"  {e.code} — backoff {wait:.0f}s\n"); time.sleep(wait); continue
            raise
        except Exception as e:  # noqa
            last = e; time.sleep(sleep * (2 ** attempt))
    raise last


def main():
    ap = argparse.ArgumentParser(description="FantasyPoints Data Suite puller (seed-and-iterate, DS v2).")
    ap.add_argument("--seed", required=True, help="file with one 'Copy as cURL' from your FP session")
    ap.add_argument("--mode", choices=["base", "personnel"],
                    help="base = unfiltered season; personnel = sweep personnel codes")
    ap.add_argument("--inspect", action="store_true",
                    help="make ONE real request and print the response's structure (to find the row path); writes nothing")
    ap.add_argument("--codes", default="1,2,3,4,5,6,7,8,9,10,11", help="personnel codes to try (unknown ones are skipped)")
    ap.add_argument("--positions", default="", help="override player.position, e.g. WR,TE,RB")
    ap.add_argument("--out", default="NFL-master/FP/2025/Receiving/base_season.csv", help="output for --mode base")
    ap.add_argument("--out-root", default="NFL-master/FP_SWEEP/2025/Receiving", help="root for the personnel sweep")
    ap.add_argument("--rows-key", default=None, help="dotted path to the row list if not auto-found")
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="print planned requests (auth masked); send nothing")
    a = ap.parse_args()

    seed = parse_curl(open(os.path.expanduser(a.seed)).read())
    if not seed["url"] or not seed["body"]:
        sys.exit("!! couldn't parse URL/body from the seed — is it a POST 'Copy as cURL' from the Data Suite?")
    body = json.loads(seed["body"])
    positions = [p.strip() for p in a.positions.split(",") if p.strip()] if a.positions else None

    if a.dry_run:
        sys.stderr.write(f"seed OK · {seed['method']} {seed['url']}\n  headers={_mask(seed['headers'])}\n")
        fp_par, fp_key = _find_key(body, "filterPlay")
        sys.stderr.write(f"  filterPlay in seed: {json.dumps(fp_par[fp_key]) if fp_par else '(none!)'}\n")

    # --inspect: one real request, print the response skeleton so we can pin the row path
    if a.inspect:
        r = send(make_base(body), seed, a.sleep, a.retries, False)
        print("RESPONSE SHAPE (structure only — no data values):\n")
        print(skeleton(r))
        try:
            print(f"\nauto-detect found {len(flatten_rows(r))} rows — looks good.")
        except Exception as e:  # noqa
            print(f"\nauto-detect still can't find rows ({e}); the shape above tells me the path.")
        return

    if not a.mode:
        sys.exit("!! pass --mode base | --mode personnel  (or --inspect to check the response shape)")

    _shape_shown = [False]
    def flatten_or_show(r):
        try:
            return flatten_rows(r, a.rows_key)
        except Exception:
            if not _shape_shown[0]:
                sys.stderr.write("\n!! couldn't find the row list. RESPONSE SHAPE — paste this to me:\n"
                                 + skeleton(r) + "\n\n")
                _shape_shown[0] = True
            raise

    if a.mode == "base":
        b = make_base(body); set_positions(b, positions)
        r = send(b, seed, a.sleep, a.retries, a.dry_run)
        if a.dry_run:
            print(f"[BASE] → {a.out}\n  {r['body_preview']}")
        else:
            try:
                n = write_csv(flatten_or_show(r), os.path.expanduser(a.out))
                print(f"[BASE] {n} rows → {a.out}")
            except Exception as e:  # noqa
                print(f"[BASE] failed — {str(e)[:80]} (see RESPONSE SHAPE above)")
        return

    # personnel sweep — pull each code, skip ones FP rejects/returns empty
    codes = [int(c) for c in a.codes.split(",") if c.strip()]
    got = 0
    for code in codes:
        b = make_dim(body, "personnel", PERSONNEL_PATH, code); set_positions(b, positions)
        if a.dry_run:
            r = send(b, seed, a.sleep, a.retries, True)
            print(f"[personnel code {code}] → …/personnel/<grouping>.csv\n  {r['body_preview']}"); continue
        try:
            rows = flatten_or_show(send(b, seed, a.sleep, a.retries, False))
        except Exception as e:  # noqa
            print(f"[personnel code {code}] skip ({str(e)[:80]})"); time.sleep(a.sleep); continue
        # name the file by the REAL grouping (11/12/13…) read from the data, not FP's internal code
        keys = Counter(r.get("playOffensePersonnelKey", "") for r in rows if r.get("playOffensePersonnelKey", ""))
        grp = keys.most_common(1)[0][0] if keys else str(code)
        out = os.path.join(os.path.expanduser(a.out_root), "personnel", f"{grp}.csv")
        n = write_csv(rows, out)
        print(f"[personnel code {code} → grouping {grp}] {n} rows → {out}"); got += n and 1 or 0
        time.sleep(a.sleep)
    if not a.dry_run:
        print(f"done — {got} personnel code(s) returned data. (codes are FP-internal; map to 11/12/… by route volume.)")


if __name__ == "__main__":
    main()
