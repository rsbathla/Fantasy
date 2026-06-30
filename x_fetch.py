#!/usr/bin/env python3
"""x_fetch.py — pull recent X posts for the dossier using an App-Only Bearer token.

Reads the token from the ENV VAR X_BEARER_TOKEN (never a literal, never from chat). Uses the X API v2
recent-search endpoint (7-day window — exactly what a 'keep the dossier current' refresh wants):
  * each tracked HANDLE  -> from:<handle> -is:retweet   (their recent originals)
  * each PLAYER name     -> "<name>" -is:retweet lang:en (recent league-wide mentions)
Writes a flat normalized list to x_posts.json, which x_dossier_refresh.py maps into the dossier.

SAFE BY DEFAULT: with no flag it does a DRY RUN — prints the query plan + estimated reads + $ cost and
calls nothing. Add --go to actually fetch. Caps keep spend bounded and predictable.

  X_BEARER_TOKEN=… python3 x_fetch.py                 # dry run: plan + cost, no calls
  X_BEARER_TOKEN=… python3 x_fetch.py --go            # fetch -> x_posts.json
  X_BEARER_TOKEN=… python3 x_fetch.py --go --handles-only   # cheaper: skip per-player search
then:  python3 x_dossier_refresh.py --input x_posts.json     # map + rebuild the dossier
"""
import os, json, time, csv, argparse, urllib.request, urllib.parse, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.x.com/2/tweets/search/recent"
COST_PER_READ = 0.005   # pay-per-use post read

def _load_dotenv():
    """Load KEY=value lines from a .env file (script dir or cwd) into the environment if not already
    set. Lets you keep X_BEARER_TOKEN in a gitignored .env instead of exporting it each time."""
    for d in (HERE, os.getcwd()):
        p = os.path.join(d, '.env')
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_dotenv()

def handles():
    p = os.path.join(HERE, 'x_handles.txt'); out = []
    if os.path.exists(p):
        for line in open(p):
            h = line.strip().lstrip('@')
            if h and not h.startswith('#'):
                out.append(h)
    return out

def players():
    rows = list(csv.DictReader(open(os.path.join(HERE, 'features.csv'), encoding='utf-8')))
    seen = set(); out = []
    for r in rows:
        nm = (r.get('name') or '').strip()
        if nm and r.get('pos') in ('QB', 'RB', 'WR', 'TE') and nm not in seen:
            seen.add(nm); out.append(nm)
    return out

def _get(url):
    tok = os.environ.get('X_BEARER_TOKEN')
    if not tok:
        raise SystemExit("Set X_BEARER_TOKEN in your environment (App-Only Bearer token) — never paste it in chat.")
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + tok, 'User-Agent': 'dossier-refresh'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode()), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code == 429:   # rate limit — back off to the reset
                reset = e.headers.get('x-rate-limit-reset')
                wait = max(5, int(reset) - int(time.time())) if reset else (2 ** attempt) * 5
                print(f"  rate-limited; waiting {min(wait,90)}s…"); time.sleep(min(wait, 90)); continue
            if e.code in (401, 403):
                raise SystemExit(f"X API {e.code}: check the Bearer token / app access. {e.read()[:200]}")
            time.sleep(2 ** attempt)
    return None, {}

def search(query, max_results):
    qs = urllib.parse.urlencode({
        'query': query, 'max_results': max(10, min(100, max_results)),
        'tweet.fields': 'created_at,public_metrics,entities,attachments',
        'expansions': 'author_id', 'user.fields': 'username,name'})
    data, _ = _get(f"{API}?{qs}")
    if not data:
        return []
    users = {u['id']: u for u in (data.get('includes', {}).get('users') or [])}
    out = []
    for t in (data.get('data') or []):
        u = users.get(t.get('author_id'), {})
        pm = t.get('public_metrics') or {}
        out.append({'handle': u.get('username'), 'name': u.get('name'), 'text': t.get('text'),
                    'date': t.get('created_at'), 'likes': pm.get('like_count'),
                    'url': f"https://x.com/i/status/{t['id']}", 'kind': 'tweet',
                    'has_media': bool(t.get('attachments')), 'source': 'x_mcp'})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--go', action='store_true', help="actually call the API (default = dry run)")
    ap.add_argument('--handles-only', action='store_true', help="skip per-player mention search (cheaper)")
    ap.add_argument('--per-handle', type=int, default=20)
    ap.add_argument('--per-player', type=int, default=10)
    ap.add_argument('--max-players', type=int, default=400)
    a = ap.parse_args()
    H = handles(); P = players()[:a.max_players]
    n_h = len(H); n_p = 0 if a.handles_only else len(P)
    reads = n_h * a.per_handle + n_p * a.per_player
    print(f"PLAN: {n_h} handles x {a.per_handle} + {n_p} players x {a.per_player} = ~{reads} reads")
    print(f"EST COST: ~${reads * COST_PER_READ:.2f} (pay-per-use @ ${COST_PER_READ}/read), 7-day recent window")
    if not a.go:
        print("\nDRY RUN — nothing was called. Re-run with --go to fetch.")
        return
    posts = []
    for i, h in enumerate(H):
        posts += search(f"from:{h} -is:retweet", a.per_handle)
        if (i + 1) % 10 == 0:
            print(f"  handles {i+1}/{n_h} · {len(posts)} posts"); time.sleep(1)
    if not a.handles_only:
        for i, nm in enumerate(P):
            posts += search(f'"{nm}" -is:retweet lang:en', a.per_player)
            if (i + 1) % 25 == 0:
                print(f"  players {i+1}/{n_p} · {len(posts)} posts"); time.sleep(1)
    json.dump(posts, open(os.path.join(HERE, 'x_posts.json'), 'w'), ensure_ascii=False)
    print(f"\nwrote x_posts.json — {len(posts)} posts. Next: python3 x_dossier_refresh.py --input x_posts.json")

if __name__ == '__main__':
    main()
