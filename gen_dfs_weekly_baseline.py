import json

with open('/root/bestball/bestball/dfs_season_baseline.json') as f:
    raw = f.read()

# Validate it parses
data = json.loads(raw)
print(f"Loaded {len(data['weeks'])} weeks")

SEASON_JSON = json.dumps([
  {"wk":1,"game":"DAL vs NYG","total":50.5,"smash_spots":96,"highlight":False},
  {"wk":2,"game":"DAL vs WAS","total":52.5,"smash_spots":92,"highlight":True},
  {"wk":3,"game":"BAL vs DAL","total":52.5,"smash_spots":91,"highlight":False},
  {"wk":4,"game":"IND vs WAS","total":50.0,"smash_spots":101,"highlight":False},
  {"wk":5,"game":"BUF vs LAR","total":51.5,"smash_spots":86,"highlight":False},
  {"wk":6,"game":"DAL vs GB","total":51.5,"smash_spots":81,"highlight":False},
  {"wk":7,"game":"BAL vs CIN","total":51.0,"smash_spots":80,"highlight":False},
  {"wk":8,"game":"BAL vs BUF","total":51.0,"smash_spots":88,"highlight":False},
  {"wk":9,"game":"DAL vs IND","total":52.5,"smash_spots":88,"highlight":True},
  {"wk":10,"game":"DAL vs SF","total":52.0,"smash_spots":88,"highlight":False},
  {"wk":11,"game":"CIN vs WAS","total":51.5,"smash_spots":86,"highlight":False},
  {"wk":12,"game":"CHI vs DET","total":50.0,"smash_spots":97,"highlight":False},
  {"wk":13,"game":"DAL vs SEA","total":50.0,"smash_spots":79,"highlight":False},
  {"wk":14,"game":"LAR vs SF","total":50.0,"smash_spots":80,"highlight":False},
  {"wk":15,"game":"DAL vs LAR","total":53.0,"smash_spots":106,"highlight":True},
  {"wk":16,"game":"CIN vs IND","total":51.0,"smash_spots":103,"highlight":False},
  {"wk":17,"game":"BAL vs CIN","total":51.0,"smash_spots":99,"highlight":False},
  {"wk":18,"game":"DAL vs WAS","total":52.5,"smash_spots":97,"highlight":False}
])

html_before = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>2026 DFS Weekly Baseline</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Space Grotesk', Inter, system-ui, -apple-system, sans-serif;
      background: #ffffff;
      color: #111827;
      font-size: 14px;
      line-height: 1.5;
    }

    /* ── Hero ── */
    .hero {
      background: #003c33;
      color: #ffffff;
      padding: 48px 32px 40px;
      text-align: center;
    }
    .hero h1 {
      font-size: 2rem;
      font-weight: 700;
      letter-spacing: -0.5px;
      margin-bottom: 10px;
    }
    .hero .subtitle {
      color: rgba(255,255,255,0.78);
      font-size: 0.95rem;
      margin-bottom: 14px;
    }
    .hero .tag {
      display: inline-block;
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.25);
      border-radius: 20px;
      padding: 4px 14px;
      font-size: 0.78rem;
      color: rgba(255,255,255,0.8);
    }

    /* ── Layout ── */
    .page-wrap {
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 24px 64px;
    }

    /* ── Section headers ── */
    .section-header {
      font-size: 1.05rem;
      font-weight: 600;
      color: #111827;
      margin-bottom: 14px;
      padding-bottom: 8px;
      border-bottom: 2px solid #003c33;
    }
    .section-wrap {
      margin-bottom: 40px;
    }

    /* ── Tables ── */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    thead th {
      background: #003c33;
      color: #ffffff;
      font-weight: 600;
      padding: 9px 12px;
      text-align: left;
      white-space: nowrap;
    }
    tbody tr {
      border-bottom: 1px solid #e5e7eb;
    }
    tbody tr:nth-child(even) {
      background: #f9fafb;
    }
    tbody tr:hover {
      background: #f0faf6;
    }
    tbody td {
      padding: 8px 12px;
      vertical-align: middle;
    }
    .rank-cell { color: #6b7280; font-weight: 600; width: 42px; }
    .name-cell { font-weight: 600; }
    .muted { color: #6b7280; }

    /* ── Season overview ── */
    .season-table tr.highlight-row {
      background: #e6f4f1 !important;
    }
    .season-note {
      margin-top: 10px;
      font-size: 12px;
      color: #6b7280;
      font-style: italic;
    }

    /* ── Week picker ── */
    .week-picker-wrap {
      overflow-x: auto;
      padding-bottom: 8px;
      margin-bottom: 28px;
    }
    .week-picker {
      display: flex;
      gap: 6px;
      min-width: max-content;
    }
    .week-btn {
      background: #ffffff;
      border: 1.5px solid #003c33;
      color: #003c33;
      border-radius: 6px;
      padding: 6px 13px;
      font-family: inherit;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s, color 0.15s;
      white-space: nowrap;
    }
    .week-btn:hover {
      background: #e6f4f1;
    }
    .week-btn.active {
      background: #003c33;
      color: #ffffff;
      border-color: #003c33;
    }

    /* ── Anchor games ── */
    .anchor-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 28px;
    }
    .game-card {
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 12px 16px;
      background: #fff;
    }
    .game-card.top-game {
      border-color: #00875a;
    }
    .game-card.first-game {
      border: 2px solid #00875a;
      background: #f0faf6;
    }
    .top-game-label {
      font-size: 10px;
      font-weight: 700;
      color: #00875a;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }
    .game-name {
      font-weight: 600;
      font-size: 14px;
      color: #111827;
    }
    .game-total {
      font-size: 20px;
      font-weight: 700;
      color: #003c33;
      margin-top: 4px;
    }
    .game-total::before { content: 'O/U '; font-size: 11px; font-weight: 400; color: #6b7280; }

    /* ── Pos chips ── */
    .pos-chip {
      display: inline-block;
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      border-radius: 4px;
      padding: 2px 6px;
      letter-spacing: 0.3px;
    }

    /* ── Play bar ── */
    .play-cell {
      min-width: 90px;
    }
    .play-val {
      font-weight: 600;
      font-size: 13px;
    }
    .play-bar {
      height: 4px;
      background: #e5e7eb;
      border-radius: 2px;
      margin-top: 3px;
      overflow: hidden;
    }
    .play-fill {
      height: 100%;
      border-radius: 2px;
      background: linear-gradient(to right, #a7f3d0, #00875a);
    }

    /* ── Smash chips ── */
    .smash-chip {
      display: inline-block;
      background: #00875a;
      color: #fff;
      font-size: 10px;
      font-weight: 700;
      border-radius: 3px;
      padding: 1px 5px;
      margin: 1px 2px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    .no-smash { color: #d1d5db; }

    /* ── Top plays table ── */
    .play-row {
      cursor: pointer;
    }
    .play-row.expanded {
      background: #f0faf6 !important;
    }
    .play-row:hover td { background: none; }

    .edge-detail td {
      background: #f8fffe !important;
      padding: 0 !important;
    }
    .edge-table-wrap {
      padding: 12px 24px;
      border-left: 3px solid #00875a;
    }
    .edge-inner {
      width: 100%;
      font-size: 12px;
    }
    .edge-inner thead th {
      background: #e6f4f1;
      color: #003c33;
      font-size: 11px;
    }
    .edge-inner tbody tr:nth-child(even) { background: #f9fafb; }
    .edge-inner td { padding: 6px 10px; }

    /* ── Position boards ── */
    .pos-boards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 18px;
      margin-bottom: 32px;
    }
    .pos-board {
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
    }
    .pos-board-header {
      padding: 9px 14px;
      font-weight: 700;
      font-size: 13px;
      color: #fff;
      letter-spacing: 0.5px;
    }
    .pos-board table { font-size: 12px; }
    .pos-board thead th {
      background: #f9fafb;
      color: #374151;
      font-size: 11px;
      padding: 7px 10px;
    }
    .pos-board tbody td { padding: 6px 10px; }
    .stars { font-size: 12px; }

    /* ── Smash board ── */
    #smash-board-body tr:nth-child(even) { background: #f9fafb; }

    /* ── Scrollable table wrapper ── */
    .table-scroll {
      overflow-x: auto;
    }

    /* ── Dynamic section heading ── */
    .week-label {
      font-size: 0.82rem;
      font-weight: 600;
      color: #00875a;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 20px;
    }

    /* ── Subsection ── */
    .subsection-header {
      font-size: 0.9rem;
      font-weight: 600;
      color: #374151;
      margin: 20px 0 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-size: 11px;
    }
  </style>
</head>
<body>

<!-- ── HERO ── -->
<div class="hero">
  <h1>2026 DFS Weekly Baseline</h1>
  <p class="subtitle">Forward-looking model baseline · Game totals + matchup edges · Not live Vegas lines</p>
  <span class="tag">Built: 2026-07-03 · Model data</span>
</div>

<div class="page-wrap">

  <!-- ── SEASON OVERVIEW ── -->
  <div class="section-wrap">
    <div class="section-header">Season Overview — Which Weeks Have The Best Environments</div>
    <div class="table-scroll">
      <table class="season-table" id="season-table">
        <thead>
          <tr>
            <th>Week</th>
            <th>Top Game</th>
            <th>Total</th>
            <th>Smash Spots</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody id="season-tbody"></tbody>
      </table>
    </div>
    <p class="season-note">DAL appears in high-total matchups across 8+ weeks · ARI defense is a recurring smash spot (LAR vs ARI, SF vs ARI, SEA vs ARI)</p>
  </div>

  <!-- ── WEEK PICKER ── -->
  <div class="section-wrap">
    <div class="section-header">Select Week</div>
    <div class="week-picker-wrap">
      <div class="week-picker" id="week-picker"></div>
    </div>
  </div>

  <!-- ── DYNAMIC WEEK CONTENT ── -->
  <div id="week-content">
    <div class="week-label" id="week-label">Week 1</div>

    <!-- Anchor Games -->
    <div class="section-wrap">
      <div class="section-header">Anchor Games</div>
      <div class="anchor-grid" id="anchor-games"></div>
    </div>

    <!-- Top Plays -->
    <div class="section-wrap">
      <div class="section-header">Top 24 Plays</div>
      <div class="table-scroll">
        <table id="top-plays-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Player</th>
              <th>Pos</th>
              <th>Team</th>
              <th>Opp</th>
              <th>Play</th>
              <th>Edge</th>
              <th>Impl</th>
              <th>Smash</th>
            </tr>
          </thead>
          <tbody id="top-plays-body"></tbody>
        </table>
      </div>
    </div>

    <!-- Position Boards -->
    <div class="section-wrap">
      <div class="section-header">Position Boards — Top 8 by Position</div>
      <div class="pos-boards">
        <div class="pos-board" id="board-QB">
          <div class="pos-board-header" style="background:#1863dc">QB Board</div>
          <table>
            <thead><tr><th>Rk</th><th>Name</th><th>Team</th><th>Opp</th><th>Play</th><th>★</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
        <div class="pos-board" id="board-RB">
          <div class="pos-board-header" style="background:#00875a">RB Board</div>
          <table>
            <thead><tr><th>Rk</th><th>Name</th><th>Team</th><th>Opp</th><th>Play</th><th>★</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
        <div class="pos-board" id="board-WR">
          <div class="pos-board-header" style="background:#9254de">WR Board</div>
          <table>
            <thead><tr><th>Rk</th><th>Name</th><th>Team</th><th>Opp</th><th>Play</th><th>★</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
        <div class="pos-board" id="board-TE">
          <div class="pos-board-header" style="background:#d46b08">TE Board</div>
          <table>
            <thead><tr><th>Rk</th><th>Name</th><th>Team</th><th>Opp</th><th>Play</th><th>★</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Smash Board -->
    <div class="section-wrap">
      <div class="section-header">Smash Board — Multi-Edge Plays</div>
      <div class="table-scroll">
        <table id="smash-board">
          <thead>
            <tr>
              <th>Player</th>
              <th>Pos</th>
              <th>Matchup</th>
              <th>Play</th>
              <th>Edge Score</th>
              <th>Smash Axes</th>
            </tr>
          </thead>
          <tbody id="smash-board-body"></tbody>
        </table>
      </div>
    </div>

  </div><!-- /week-content -->

</div><!-- /page-wrap -->

<script>
const DATA = """

html_after = """;
const SEASON = """ + SEASON_JSON + """;

let activeWeek = '1';

// ── Build season overview table ──
function buildSeasonTable() {
  const tbody = document.getElementById('season-tbody');
  tbody.innerHTML = SEASON.map(row => {
    const notes = row.highlight ? '&#9733; Elite environment' : '';
    const cls = row.highlight ? 'highlight-row' : '';
    return `<tr class="${cls}">
      <td>Wk ${row.wk}</td>
      <td>${row.game}</td>
      <td>${row.total}</td>
      <td>${row.smash_spots}</td>
      <td>${notes}</td>
    </tr>`;
  }).join('');
}

// ── Build week picker ──
function buildWeekPicker() {
  const picker = document.getElementById('week-picker');
  picker.innerHTML = Array.from({length:18}, (_,i) => i+1).map(wk => {
    return `<button class="week-btn${wk===1?' active':''}" data-wk="${wk}" onclick="setWeek(${wk})">Wk ${wk}</button>`;
  }).join('');
}

function setWeek(wk) {
  activeWeek = String(wk);
  document.querySelectorAll('.week-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.wk === activeWeek);
  });
  document.getElementById('week-label').textContent = 'Week ' + wk;
  renderWeek(activeWeek);
}

function renderWeek(wk) {
  const weekData = DATA.weeks[wk];
  if (!weekData) return;
  renderAnchorGames(weekData.anchor_games);
  renderTopPlays(weekData.players);
  renderPositionBoards(weekData.players);
  renderSmashBoard(weekData.players);
}

function renderAnchorGames(games) {
  const sorted = [...games].sort((a,b) => b.total - a.total);
  const html = sorted.map((g, i) => {
    const isTop = i < 3;
    const isFirst = i === 0;
    return `<div class="game-card${isTop?' top-game':''}${isFirst?' first-game':''}">
      ${isFirst ? '<div class="top-game-label">&#128293; TOP GAME ENVIRONMENT</div>' : ''}
      <div class="game-name">${g.g}</div>
      <div class="game-total">${g.total}</div>
    </div>`;
  }).join('');
  document.getElementById('anchor-games').innerHTML = html;
}

function posColor(pos) {
  const colors = {QB:'#1863dc', RB:'#00875a', WR:'#9254de', TE:'#d46b08'};
  return colors[pos] || '#6b7280';
}

function renderTopPlays(players) {
  const top24 = players.slice(0, 24);
  const rows = top24.map((p, idx) => {
    const smashAxes = (p.edges||[]).filter(e => e.smash).map(e =>
      `<span class="smash-chip">${e.axis}</span>`).join('');
    const barWidth = Math.min(100, p.play);
    const edgesStr = JSON.stringify(p.edges||[]).replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'");
    return `<tr class="play-row" data-idx="${idx}" data-edges='${JSON.stringify(p.edges||[]).replace(/'/g,"&apos;")}' onclick="toggleEdge(this)">
      <td class="rank-cell">${p.rank}</td>
      <td class="name-cell">${p.name}</td>
      <td><span class="pos-chip" style="background:${posColor(p.pos)}">${p.pos}</span></td>
      <td>${p.team}</td>
      <td class="muted">${p.opp}</td>
      <td class="play-cell">
        <span class="play-val">${p.play.toFixed(1)}</span>
        <div class="play-bar"><div class="play-fill" style="width:${barWidth}%"></div></div>
      </td>
      <td>${p.edge_score.toFixed(1)}</td>
      <td>${p.imp}</td>
      <td>${smashAxes}</td>
    </tr>
    <tr class="edge-detail" id="edge-${idx}" style="display:none">
      <td colspan="9">
        <div class="edge-table-wrap">
          <table class="edge-inner">
            <thead><tr><th>Axis</th><th>Player %ile</th><th>Def Soft %ile</th><th>Score</th><th>Smash?</th></tr></thead>
            <tbody id="edge-body-${idx}"></tbody>
          </table>
        </div>
      </td>
    </tr>`;
  }).join('');
  document.getElementById('top-plays-body').innerHTML = rows;
}

function toggleEdge(row) {
  const idx = row.dataset.idx;
  const detailRow = document.getElementById('edge-' + idx);
  const isVisible = detailRow.style.display !== 'none';
  // hide all
  document.querySelectorAll('.edge-detail').forEach(r => r.style.display = 'none');
  document.querySelectorAll('.play-row').forEach(r => r.classList.remove('expanded'));
  if (!isVisible) {
    detailRow.style.display = '';
    row.classList.add('expanded');
    const edges = JSON.parse(row.dataset.edges.replace(/&apos;/g,"'"));
    const body = document.getElementById('edge-body-' + idx);
    body.innerHTML = edges.map(e => `
      <tr>
        <td>${e.axis}</td>
        <td>${e.player_pctl != null ? e.player_pctl + 'th' : '&mdash;'}</td>
        <td>${e.def_soft_pctl != null ? e.def_soft_pctl + 'th' : '&mdash;'}</td>
        <td>${typeof e.score === 'number' ? e.score.toFixed(1) : e.score}</td>
        <td>${e.smash ? '<span class="smash-chip">SMASH</span>' : '<span class="no-smash">&mdash;</span>'}</td>
      </tr>`).join('');
  }
}

function renderPositionBoards(players) {
  ['QB','RB','WR','TE'].forEach(pos => {
    const posPlayers = players.filter(p => p.pos === pos).slice(0,8);
    const rows = posPlayers.map((p,i) => {
      const nSmash = p.n_smash||0;
      const stars = '&#9733;'.repeat(Math.min(3, nSmash));
      return `<tr>
        <td class="rank-cell">${i+1}</td>
        <td class="name-cell">${p.name}</td>
        <td>${p.team}</td>
        <td class="muted">${p.opp}</td>
        <td>${p.play.toFixed(1)}</td>
        <td class="stars" style="color:${nSmash>=2?'#00875a':'#d1d5db'}">${stars || '&mdash;'}</td>
      </tr>`;
    }).join('');
    document.getElementById('board-' + pos).querySelector('tbody').innerHTML = rows;
  });
}

function renderSmashBoard(players) {
  const smashPlayers = players.filter(p => (p.n_smash||0) >= 2)
    .sort((a,b) => b.edge_score - a.edge_score);
  const rows = smashPlayers.map(p => {
    const smashAxes = (p.edges||[]).filter(e => e.smash)
      .map(e => `<span class="smash-chip">${e.axis}</span>`).join('');
    return `<tr>
      <td class="name-cell">${p.name}</td>
      <td><span class="pos-chip" style="background:${posColor(p.pos)}">${p.pos}</span></td>
      <td>${p.team} vs ${p.opp}</td>
      <td>${p.play.toFixed(1)}</td>
      <td>${p.edge_score.toFixed(1)}</td>
      <td>${smashAxes}</td>
    </tr>`;
  }).join('');
  document.getElementById('smash-board-body').innerHTML = rows || '<tr><td colspan="6" style="color:#6b7280;text-align:center;padding:20px">No players with 2+ smash edges this week</td></tr>';
}

// ── Init ──
buildSeasonTable();
buildWeekPicker();
renderWeek('1');
</script>
</body>
</html>"""

with open('/root/bestball/bestball/dfs_weekly_baseline.html', 'w') as f:
    f.write(html_before)
    f.write(raw)
    f.write(html_after)

print("Done writing HTML")
