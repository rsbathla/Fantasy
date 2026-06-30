# Connecting the X (Twitter) MCP to refresh the dossier

The deep dossier (`dossier_deep.html`) surfaces tweets and video mentions. Today those come from a
static older ingest. The official **X MCP** (`api.x.com/mcp`) makes that layer **live and
auto-updating** — full-archive post search, user timelines, mentions, and news/trends.

You picked the **connect-the-MCP** path with all four scopes: analyst handles · player-mention
search · news & trends · video/media posts. Here's the split of work.

## Your one-time setup (credentials — I can't do this part)
1. In the **X Developer Portal**, create an app with **OAuth 2.0** enabled.
2. Add the redirect URI: `http://localhost:8080/callback`.
3. Copy your `CLIENT_ID` and `CLIENT_SECRET`.
4. Connect it to Claude — either:
   - **Claude app → Settings → Connectors → Add** the X MCP (`api.x.com/mcp`), approve the OAuth login; or
   - the local bridge: `npx @x/xurl mcp` (it opens your browser for OAuth, caches + auto-refreshes the token).
5. Tell me it's connected. The X tools then appear in my environment and I take it from here. I never see or store the token.

## What I do once it's connected
1. **Fetch** via the X MCP tools, bounded for cost:
   - recent posts from your **48 tracked handles** (`x_handles.txt` — edit to add/remove), capped per handle;
   - **full-archive search** for each of the ~370 players' names (mentions league-wide), capped per player;
   - **news/trends** for team/player breaking news (injuries, role changes);
   - posts with **video/media** for the film layer.
2. **Map → merge → rebuild** with `x_dossier_refresh.py`: each post is mapped to the player(s)/team(s) it
   names, deduped, ranked by engagement, written to `x_live.json`, and merged into the dossier (a live
   tweet layer + a "📰 Breaking news" section), then `dossier_deep.html` is rebuilt.
   - `python3 x_dossier_refresh.py --input x_live.json` (I run this after fetching)

## Cost (pay-per-use; you control it)
~$0.005 per post read, ~$0.001 for your own data, full-archive search included, 2M reads/month cap,
no free tier for new apps. A **full refresh** (48 handle pulls + ~370 player searches, capped) is
**low-tens of dollars**; a weekly batch is cheap. I cap results per handle/player so spend stays
bounded and predictable, and you set the cadence.

## Status
Pipeline is built and tested (mapper proven on 1,593 corpus tweets → 320 players). Waiting only on
the X MCP connection above.
