#!/usr/bin/env python3
"""build_x_store.py — the ACCUMULATION store for browser pulls.

Each browser pull only sees X's recent window (~50 tweets / ~7h for a fresh list). This merges every
pull into a persistent, de-duplicated store keyed by tweet id, so history GROWS FORWARD over time —
"everything since the last pull" accumulates automatically. Run it right after each pull, before the
dossier refresh; the dossier then maps the FULL store, not just the latest ~50.

Flow:
  (browser pull) -> build_x_posts.py -> x_posts.json          # latest pull
  python3 build_x_store.py                                     # merge pull -> x_store.json (grows)
  python3 x_dossier_refresh.py --input x_store.json --no-rebuild
  python3 build_x_narrative.py && python3 build_x_media.py && python3 build_dossier_deep.py

Merge rules: new id -> add; existing id -> keep max engagement (likes), union links, keep earliest
first_seen. Nothing is ever dropped. Tracks last-pull time + newest/oldest so a scheduled pull knows
its high-water mark.
"""
import json, os, datetime, glob
HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, 'x_store.json')

def load(p):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None

def _as_list(x):
    if isinstance(x, dict):
        return x.get('posts', [])
    return x or []

def main():
    # merge the canonical latest pull (x_posts.json) + every dated pull (x_pull_*.json)
    pull_files = [os.path.join(HERE, 'x_posts.json')] + sorted(glob.glob(os.path.join(HERE, 'x_pull_*.json')))
    pull = []
    for pf in pull_files:
        pull += _as_list(load(pf))
    store = load(STORE) or {'_meta': {}, 'posts': []}
    by_id = {p['id']: p for p in store.get('posts', []) if p.get('id')}
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    added = updated = 0
    for p in pull:
        pid = p.get('id')
        if not pid:
            continue
        if pid not in by_id:
            p = dict(p); p['first_seen'] = now
            by_id[pid] = p; added += 1
        else:
            cur = by_id[pid]
            # keep the richer record
            if (p.get('likes') or 0) > (cur.get('likes') or 0):
                cur['likes'] = p['likes']
            if p.get('links') and not cur.get('links'):
                cur['links'] = p['links']; updated += 1
    posts = sorted(by_id.values(), key=lambda x: x.get('date') or '', reverse=True)
    dates = [p.get('date') for p in posts if p.get('date')]
    meta = {
        'n_total': len(posts),
        'pulls': (store.get('_meta', {}).get('pulls', 0) + 1),
        'last_pull_utc': now,
        'newest_date': max(dates) if dates else None,
        'oldest_date': min(dates) if dates else None,
        'newest_id': (posts[0]['id'] if posts else None),
    }
    json.dump({'_meta': meta, 'posts': posts}, open(STORE, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"x_store.json: +{added} new, {updated} enriched -> {len(posts)} total "
          f"(pull #{meta['pulls']}, {meta['oldest_date']} .. {meta['newest_date']})")

if __name__ == '__main__':
    main()
