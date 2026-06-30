#!/usr/bin/env python3
"""x_dossier_refresh.py — map a pull of X (Twitter) posts into the dossier and rebuild it.

DESIGNED FOR THE OFFICIAL X MCP (api.x.com/mcp). Once you connect the X MCP in your Claude app,
the fetch is done by calling its tools directly (full-archive post search, user timeline, mentions,
news/trends) for: your tracked analyst HANDLES, each PLAYER's name (mention search), team/player NEWS,
and posts with VIDEO/media. Each post is normalized to:
    {handle, name, text, date, likes, url, kind, has_media, source}
and saved to x_live.json. THIS script maps that dump to players/teams and merges it into the deep
dossier (a live `x` layer alongside the existing `tweets`/`video`), then rebuilds dossier_deep.html.

Run modes:
  python3 x_dossier_refresh.py --input x_live.json     # map a real X pull -> refresh dossier
  python3 x_dossier_refresh.py --selftest              # prove map+merge on the existing tweets (no X calls)

Cost note: the X API is pay-per-use (~$0.005/post read, full-archive search). Keep per-handle and
per-player result caps modest (set when fetching); a full refresh is low-tens of dollars.
"""
import core, json, os, re, csv, argparse, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
fn = core.fn
def J(p):
    fp = os.path.join(HERE, p)
    return json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}

# ---- the tracked analyst handles (seed = the 48 already in the corpus; extend freely) ----
def tracked_handles():
    hs = set()
    intel = J('intel_data.json')
    for p in (intel.get('players') or []):
        for t in (p.get('about') or []) + (p.get('comp') or []):
            if isinstance(t, dict) and t.get('handle'):
                hs.add(t['handle'].lstrip('@'))
    cfg = os.path.join(HERE, 'x_handles.txt')
    if os.path.exists(cfg):
        for line in open(cfg):
            h = line.strip().lstrip('@')
            if h and not h.startswith('#'):
                hs.add(h)
    return sorted(hs)

# ---- player / team index for mapping ----
def player_index():
    rows = list(csv.DictReader(open(os.path.join(HERE, 'features.csv'), encoding='utf-8')))
    players = {}
    for r in rows:
        nm = r.get('name')
        if nm and r.get('pos') in ('QB', 'RB', 'WR', 'TE'):
            players[fn(nm)] = {'name': nm, 'pos': r['pos'], 'team': core.team_abbr(r.get('team'))}
    # distinctive last-name -> player(s) for substring hits in tweet text
    by_last = {}
    for k, p in players.items():
        toks = k.split()
        if len(toks) >= 2 and len(toks[-1]) > 3:
            by_last.setdefault(toks[-1], []).append(p)
    return players, by_last

TEAM_WORDS = {  # team nickname -> abbr for team-level mapping
    'cardinals': 'ARI', 'falcons': 'ATL', 'ravens': 'BAL', 'bills': 'BUF', 'panthers': 'CAR',
    'bears': 'CHI', 'bengals': 'CIN', 'browns': 'CLE', 'cowboys': 'DAL', 'broncos': 'DEN',
    'lions': 'DET', 'packers': 'GB', 'texans': 'HOU', 'colts': 'IND', 'jaguars': 'JAX',
    'chiefs': 'KC', 'chargers': 'LAC', 'rams': 'LAR', 'raiders': 'LV', 'dolphins': 'MIA',
    'vikings': 'MIN', 'patriots': 'NE', 'saints': 'NO', 'giants': 'NYG', 'jets': 'NYJ',
    'eagles': 'PHI', 'steelers': 'PIT', 'seahawks': 'SEA', '49ers': 'SF', 'niners': 'SF',
    'buccaneers': 'TB', 'bucs': 'TB', 'titans': 'TEN', 'commanders': 'WAS'}

def map_post(post, players, by_last):
    """Return ({player_fn_keys}, {team_abbrs}) mentioned in the post text."""
    text = ' ' + re.sub(r'[^a-z0-9 ]+', ' ', str(post.get('text', '')).lower().replace("'", "")) + ' '
    hit_players = set(); hit_teams = set()
    for last, plist in by_last.items():
        if (' ' + last + ' ') in text:
            for p in plist:
                # require the first-name initial to also appear to reduce last-name collisions
                fk = fn(p['name']); first = fk.split()[0]
                if (' ' + first + ' ') in text or len(plist) == 1:
                    hit_players.add(fk)
    for word, ab in TEAM_WORDS.items():
        if (' ' + word + ' ') in text:
            hit_teams.add(ab)
    # players also tag their team
    for fk in list(hit_players):
        t = players.get(fk, {}).get('team')
        if t:
            hit_teams.add(t)
    return hit_players, hit_teams

def normalize(post):
    """Accept either an already-normalized dict or a raw X-MCP post; coerce to our shape."""
    return {
        'handle': (post.get('handle') or post.get('author') or post.get('username') or '').lstrip('@'),
        'name': post.get('name') or post.get('author_name'),
        'text': post.get('text') or post.get('content') or '',
        'date': post.get('date') or post.get('created_at'),
        'likes': post.get('likes') or (post.get('public_metrics') or {}).get('like_count'),
        'url': post.get('url') or (f"https://x.com/i/status/{post['id']}" if post.get('id') else None),
        'kind': post.get('kind') or post.get('source') or 'tweet',
        'has_media': bool(post.get('has_media') or post.get('media') or post.get('attachments')),
        'source': post.get('source') or 'x_mcp',
    }

def refresh(posts):
    players, by_last = player_index()
    per_player = {}   # fn -> [posts]
    per_team = {}
    seen = set()
    for raw in posts:
        p = normalize(raw)
        key = (p['handle'], (p['text'] or '')[:80])
        if key in seen:
            continue
        seen.add(key)
        pl, tm = map_post(p, players, by_last)
        for fk in pl:
            per_player.setdefault(fk, []).append(p)
        for t in tm:
            per_team.setdefault(t, []).append(p)
    # rank each player's posts by likes desc, cap for display
    for fk in per_player:
        per_player[fk].sort(key=lambda x: -(x.get('likes') or 0))
        per_player[fk] = per_player[fk][:25]
    out = {'_meta': {'n_posts': len(posts), 'n_players': len(per_player), 'n_teams': len(per_team)},
           'players': per_player, 'teams': per_team}
    json.dump(out, open(os.path.join(HERE, 'x_live.json'), 'w'), ensure_ascii=False)
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', help="JSON list of normalized X posts (a real pull) to map + merge")
    ap.add_argument('--selftest', action='store_true', help="prove map+merge on existing corpus tweets")
    ap.add_argument('--no-rebuild', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        intel = J('intel_data.json'); posts = []
        for p in (intel.get('players') or []):
            for t in (p.get('about') or []):
                if isinstance(t, dict):
                    posts.append({**t, 'source': 'corpus_selftest'})
        print(f"[selftest] feeding {len(posts)} existing corpus tweets through the mapper…")
        res = refresh(posts)
        print(f"mapped -> {res['_meta']['n_players']} players, {res['_meta']['n_teams']} teams")
        # spot check
        for nm in ['Jahmyr Gibbs', "Ja'Marr Chase", 'Puka Nacua']:
            k = fn(nm); print(f"  {nm}: {len(res['players'].get(k, []))} posts")
        print(f"tracked handles ready for X-MCP pull: {len(tracked_handles())}")
    elif a.input:
        posts = json.load(open(a.input, encoding='utf-8'))
        posts = posts if isinstance(posts, list) else posts.get('posts', [])
        res = refresh(posts)
        print(f"x_live.json: {res['_meta']['n_posts']} posts -> {res['_meta']['n_players']} players, {res['_meta']['n_teams']} teams")
        if not a.no_rebuild:
            subprocess.run([sys.executable, os.path.join(HERE, 'build_dossier_deep.py')])
    else:
        print("Connect the X MCP, fetch posts via its tools into x_live.json, then run with --input x_live.json.")
        print(f"Tracked handles ({len(tracked_handles())}):", ', '.join('@' + h for h in tracked_handles()[:12]), '…')
