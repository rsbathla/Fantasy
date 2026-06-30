// Headless jsdom validation of decision_dashboard.html (Contract 5, DATA-RICH).
// Loads the page, lets the inline script render the embedded live_tree.json
// payload, then asserts every section + interaction, INCLUDING the new
// STACK tags + RICH scouting cards:
//   * header (counts vs targets, modeled N/M, byes, anchor, roster chips)
//   * headline card (+ stack badge when the pick has a stack)
//   * decision tree renders + a dispatched click expands a branch
//   * candidate board: >50 rows, sort, filter, STACK badges + highlighted rows,
//     a row click reveals a RICH scouting card (flags + scouting + quote + buzz + metrics)
//   * my-roster panel renders + Flags column + per-row flags/note expansion
//   * live buildFromText() consumes a fresh payload unchanged (stack + flags too)
//   * ZERO jsdom JS errors
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const file = path.join(__dirname, 'decision_dashboard.html');
const html = fs.readFileSync(file, 'utf-8');

const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => errors.push(String((e && e.stack) || e)));
const consoleErrs = [];
vc.on('error', (...a) => consoleErrs.push(a.join(' ')));

let dom;
try {
  dom = new JSDOM(html, {
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(w) { w.sendPrompt = () => {}; }
  });
} catch (e) {
  console.error('JSDOM construct error:', e);
  process.exit(2);
}

const w = dom.window, doc = w.document;

function branchVisible(node) {
  const body = node.querySelector(':scope > .bbody, :scope > .subbody');
  if (!body) return false;
  return node.classList.contains('open');
}
function noteVisible(nr) { return nr.classList.contains('show'); }

function colIndex(headSel, key) {
  const ths = Array.from(doc.querySelectorAll(headSel + ' th'));
  for (let i = 0; i < ths.length; i++) {
    if (ths[i].getAttribute('data-k') === key) return i;
  }
  return -1;
}
function columnValues(bodySel, idx) {
  const rows = Array.from(doc.querySelectorAll(bodySel + ' tr.drow'));
  return rows.map(r => {
    const tds = r.querySelectorAll('td');
    return tds[idx] ? tds[idx].textContent.trim() : '';
  });
}

setTimeout(() => {
  const results = {};

  // ---- 1) state header ----
  results.state_kv = doc.querySelectorAll('#stateCard .kv').length;
  results.state_counts = doc.querySelectorAll('#stateCard .cnt').length;
  results.state_counts_below = doc.querySelectorAll('#stateCard .cnt.below').length;
  results.state_roster_chips = doc.querySelectorAll('#stateCard .rchip').length;
  results.state_anchor = (doc.querySelector('#stateCard .anchor .v') || {}).textContent || null;
  results.state_byes = (doc.querySelector('#stateCard .byes .v') || {}).textContent || null;
  results.state_modeled = (doc.querySelector('#stateCard .modeled .big') || {}).textContent || null;

  // ---- 2) headline ----
  const hlTake = doc.querySelector('#headline .hl-take');
  results.headline_take = hlTake ? hlTake.textContent.trim() : null;
  results.headline_delta_count = doc.querySelectorAll('#headline .delta').length;
  results.headline_has_why = !!doc.querySelector('#headline .hl-why');
  // NOTE: the dashboard boots from the REAL live_tree.json embedded at build time;
  // that headline (e.g. Rome Odunze) may have no stack, so the badge is correctly absent
  // on first paint. We prove the headline-stack wiring with an explicit stacked-headline
  // render below (and again in live mode).
  results.headline_stack_present_firstpaint = !!doc.querySelector('#headline .hl-stack');
  // explicit: render a payload whose headline player has a stack in the board -> badge must appear
  (function(){
    var payload = {
      headline: { take: 'Stacked Star', dTitle: 1.2, dAdv: 2.3, why: 'stacked headline render test' },
      tree: { label: 't', branches: [] },
      board: [{ name: 'Stacked Star', pos: 'WR', team: 'CIN', adp: 10, rank: 9, proj: 16, ceiling: 34, ceil_pct: 0.9, bye: 12, w15: 'A', w16: 'B', w17: 'C@D', w17rank: 2, adv_pct: 0.9, value: 1, playoff_up: 0.7, stack: String.fromCodePoint(0x1F517) + ' onslaught w/ Joe Burrow (QB)', scouting: 's', quote: null, flags: [], tweet: null }],
      roster_detail: []
    };
    w.renderHeadline(payload.headline, payload.board);
    var hb = doc.querySelector('#headline .hl-stack');
    results.headline_stack_render = { present: !!hb, isLink: !!(hb && hb.classList.contains('link')), text: hb ? hb.textContent : null };
  })();

  // ---- 3) decision tree ----
  const branches = doc.querySelectorAll('#tree .branch');
  const subbranches = doc.querySelectorAll('#tree .subbranch');
  results.branch_nodes = branches.length;
  results.subbranch_nodes = subbranches.length;
  results.first_branch_has_condition = !!doc.querySelector('#tree .branch .cond code');
  results.tree_color_chips = doc.querySelectorAll('#tree .chip.pos-good, #tree .chip.pos-bad').length;
  results.tree_playoff_chips = doc.querySelectorAll('#tree .chip.pup').length;

  const tgt = branches[1];
  const tHead = tgt.querySelector(':scope > .bhead');
  const tBefore = { open: tgt.classList.contains('open'), vis: branchVisible(tgt), aria: tHead.getAttribute('aria-expanded') };
  tHead.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const tAfter = { open: tgt.classList.contains('open'), vis: branchVisible(tgt), aria: tHead.getAttribute('aria-expanded') };
  results.tree_click_toggle = { before: tBefore, after: tAfter };

  // ---- 4) CANDIDATE BOARD ----
  results.board_head_cols = doc.querySelectorAll('#boardHead th').length;
  results.board_rows = doc.querySelectorAll('#boardBody tr.drow').length;
  results.board_note_rows = doc.querySelectorAll('#boardBody tr.noterow').length;
  results.board_intree_rows = doc.querySelectorAll('#boardBody tr.drow.intree').length;
  results.board_heat_colored = doc.querySelectorAll('#boardBody tr.drow td[style*="rgb"]').length;

  // 4a) SORT ADP asc/desc
  const adpIdx = colIndex('#boardHead', 'adp');
  const beforeSortFirst = columnValues('#boardBody', adpIdx)[0];
  const adpTh = doc.querySelectorAll('#boardHead th')[adpIdx];
  adpTh.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const ascVals = columnValues('#boardBody', adpIdx).map(parseFloat).filter(x => !isNaN(x));
  const ascFirst = columnValues('#boardBody', adpIdx)[0];
  const ascSortedOK = ascVals.every((v, i) => i === 0 || ascVals[i - 1] <= v);
  adpTh.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const descVals = columnValues('#boardBody', adpIdx).map(parseFloat).filter(x => !isNaN(x));
  const descFirst = columnValues('#boardBody', adpIdx)[0];
  const descSortedOK = descVals.every((v, i) => i === 0 || descVals[i - 1] >= v);
  results.board_sort = {
    col: 'adp', firstBeforeSort: beforeSortFirst,
    firstAsc: ascFirst, ascMonotonic: ascSortedOK,
    firstDesc: descFirst, descMonotonic: descSortedOK,
    reordered: ascFirst !== descFirst
  };

  // 4b) SORT Player (text)
  const nameIdx = colIndex('#boardHead', 'name');
  const nameTh = doc.querySelectorAll('#boardHead th')[nameIdx];
  nameTh.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const names = columnValues('#boardBody', nameIdx).map(s => s.replace(/^\*\s*/, '').toLowerCase());
  const nameSortedOK = names.every((v, i) => i === 0 || names[i - 1] <= v);
  results.board_sort_name_monotonic = nameSortedOK;

  // 4c) FILTER RB
  const totalRows = doc.querySelectorAll('#boardBody tr.drow').length;
  const rbBtn = doc.querySelector('#boardFilters button[data-pos="RB"]');
  rbBtn.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const posIdx = colIndex('#boardHead', 'pos');
  const rbRows = doc.querySelectorAll('#boardBody tr.drow').length;
  const rbPositions = columnValues('#boardBody', posIdx);
  const allRB = rbPositions.length > 0 && rbPositions.every(p => p === 'RB');
  results.board_filter_RB = { totalRows, rbRows, allRB, narrowed: rbRows < totalRows && rbRows > 0 };
  doc.querySelector('#boardFilters button[data-pos="ALL"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  results.board_rows_after_all = doc.querySelectorAll('#boardBody tr.drow').length;

  // 4d) ROW CLICK reveals the RICH scouting card
  const firstRow = doc.querySelector('#boardBody tr.drow');
  const noteId = firstRow.getAttribute('data-exp');
  const noteRow = doc.getElementById(noteId);
  const noteBefore = noteVisible(noteRow);
  firstRow.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const noteAfter = noteVisible(noteRow);
  const noteText = (noteRow.querySelector('.notebox') || {}).textContent || '';
  results.board_row_note = { before: noteBefore, after: noteAfter, hasText: noteText.length > 10 };

  // 4e) STACK BADGES on the board (CHANGE 1)
  results.board_stack_badges = doc.querySelectorAll('#boardBody tr.drow td.player .stk').length;
  results.board_stack_link_badges = doc.querySelectorAll('#boardBody tr.drow td.player .stk.link').length;
  results.board_stack_bring_badges = doc.querySelectorAll('#boardBody tr.drow td.player .stk.bring').length;
  results.board_hasstack_rows = doc.querySelectorAll('#boardBody tr.drow.hasstack').length;
  results.board_bringback_rows = doc.querySelectorAll('#boardBody tr.drow.hasstack.bringback').length;
  results.board_stack_badge_match = (results.board_stack_badges === results.board_hasstack_rows);

  // 4f) RICH SCOUTING CARD content (CHANGE 2): find a row whose card has FLAGS, expand, assert
  let richCardOK = { found: false };
  const allDataRows = Array.from(doc.querySelectorAll('#boardBody tr.drow'));
  for (const r of allDataRows) {
    const nid = r.getAttribute('data-exp');
    const nr = doc.getElementById(nid);
    if (!nr) continue;
    const fchips = nr.querySelectorAll('.notebox .fchip');
    if (fchips.length > 0) {
      r.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
      const box = nr.querySelector('.notebox');
      const metaTxt = (box.querySelector('.nmeta') || {}).textContent || '';
      richCardOK = {
        found: true,
        shown: noteVisible(nr),
        flagChips: fchips.length,
        flagHasDangerOrCaution: !!nr.querySelector('.fchip.danger, .fchip.caution'),
        flagHasNoteText: Array.from(fchips).some(c => (c.textContent || '').length > 8),
        hasScouting: !!box.querySelector('.scout') || /(?:2026 Outlook|Scouting)/.test(box.textContent || ''),
        hasMetrics: !!box.querySelector('.nmeta') && /playoff_up/.test(metaTxt),
        hasW17rank: /W17 blow-up rank/.test(metaTxt)
      };
      break;
    }
  }
  results.board_rich_card_flags = richCardOK;

  // ---- 4g) USAGE line + MODEL CARD percentile chips (real data) ----
  // Expand EVERY row (cards are built at render time but we still assert on
  // the live DOM), then look for a usage line + color-scaled model chips.
  (function(){
    var rows = Array.from(doc.querySelectorAll('#boardBody tr.drow'));
    var usageFound = null, modelFound = null;
    var anyColorScaled = false, footerFound = null, fracPctFound = false;
    var nUsageCards = 0, nModelCards = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var nid = r.getAttribute('data-exp');
      var nr = doc.getElementById(nid);
      if (!nr) continue;
      // ensure expanded so layout/text is present
      if (!nr.classList.contains('show')) {
        r.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
      }
      var box = nr.querySelector('.notebox');
      if (!box) continue;
      var uline = box.querySelector('.usage');
      if (uline) {
        nUsageCards++;
        var utxt = uline.textContent || '';
        // first usage line that actually carries usage numbers
        if (usageFound === null && (/car\/g/.test(utxt) || /ypc/.test(utxt) || /tgt/.test(utxt) || /ypt/.test(utxt) || /catch/.test(utxt))) {
          usageFound = utxt.replace(/\s+/g, ' ').trim();
          if (/%/.test(utxt)) fracPctFound = true; // fractions rendered as %
        }
      }
      var mcard = box.querySelector('.modelcard');
      if (mcard) {
        nModelCards++;
        var chips = mcard.querySelectorAll('.mchip');
        var foot = mcard.querySelector('.mfoot');
        if (modelFound === null && chips.length > 0) {
          modelFound = { chips: chips.length, sampleLabels: Array.from(chips).slice(0,4).map(function(c){ var l=c.querySelector('.ml'); return l?l.textContent:''; }) };
        }
        // color-scaling: at least one chip value span carries an inline hsla background
        Array.from(mcard.querySelectorAll('.mchip .mv')).forEach(function(mv){
          var st = (mv.getAttribute('style') || '');
          if (/hsla?\(/.test(st) || /rgb/.test(st)) anyColorScaled = true;
        });
        if (footerFound === null && foot) {
          var ft = foot.textContent || '';
          if (/consensus/.test(ft)) footerFound = ft.replace(/\s+/g,' ').trim();
        }
      }
    }
    results.board_usage_cards = nUsageCards;
    results.board_usage_line = usageFound;           // e.g. "RB 18.6 car/g ..."
    results.board_usage_frac_as_pct = fracPctFound;
    results.board_model_cards = nModelCards;
    results.board_model_chips_sample = modelFound;    // {chips, sampleLabels}
    results.board_model_color_scaled = anyColorScaled;
    results.board_model_footer = footerFound;          // "model consensus N · divergence N · N signals"
  })();

  // full-profile cards somewhere on the board
  results.board_cards_with_stackbanner = doc.querySelectorAll('#boardBody .notebox .stackbanner').length;
  results.board_cards_with_quote = doc.querySelectorAll('#boardBody .notebox blockquote.quote').length;
  results.board_cards_with_buzz = doc.querySelectorAll('#boardBody .notebox .buzz').length;

  // ---- 5) MY ROSTER PANEL ----
  results.roster_head_cols = doc.querySelectorAll('#rosterHead th').length;
  results.roster_rows = doc.querySelectorAll('#rosterBody tr').length;
  results.roster_count_label = (doc.getElementById('rosterCount') || {}).textContent || null;
  const rHeadTxt = Array.from(doc.querySelectorAll('#rosterHead th')).map(t => t.textContent).join(',');
  results.roster_playoff_cols = /W15/.test(rHeadTxt) && /W16/.test(rHeadTxt) && /W17/.test(rHeadTxt);
  results.roster_has_flags_col = /Flags/.test(rHeadTxt);
  results.roster_stack_badges = doc.querySelectorAll('#rosterBody tr.rosterrow td.player .stk').length;
  const rRow = doc.querySelector('#rosterBody tr.rosterrow');
  const rNote = doc.getElementById(rRow.getAttribute('data-exp'));
  const rBefore = rNote.classList.contains('show');
  rRow.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const rAfter = rNote.classList.contains('show');
  const rBoxTxt = (rNote.querySelector('.rmetabox') || {}).textContent || '';
  results.roster_note_expand = { before: rBefore, after: rAfter, hasText: rBoxTxt.length > 5 };

  // ---- 6) LIVE MODE: fresh payload (stack + flags + headline-stack lookup) ----
  const livePayload = {
    state: { pick: 99, round: 9, seat: 3, roster: [{ name: 'X', pos: 'WR', team: 'KC' }],
             counts: { QB: 0, RB: 2, WR: 3, TE: 0 }, anchor: 'KC@BUF', modeled_n: 1, drafted_n: 2,
             untracked: ['Untracked Guy'] },
    headline: { take: 'Live Headline Player', dTitle: -0.4, dAdv: 2.0, why: 'live-mode injected object' },
    construction: { targets: { QB: '2-3', RB: '5-6', WR: '8-9', TE: '2-3' }, byes: [7, 14], anchor: 'KC@BUF' },
    tree: { label: 'LIVE Pick 99', branches: [
      { cond: 'if live A', take: 'Live A', pos: 'WR', team: 'KC', dTitle: 0.1, dAdv: 0.2, dW17: 0.3, playoff_up: 0.8, reason: 'r', then: null },
      { cond: 'else live B', take: 'Live B', pos: 'RB', team: 'BUF', dTitle: -0.1, dAdv: 0.05, dW17: 0.0, playoff_up: 0.3, reason: 'r', then: null }
    ] },
    board: [
      { name: 'Live Headline Player', pos: 'WR', team: 'KC', adp: 48, rank: 40, proj: 13, ceiling: 30, ceil_pct: 0.72, bye: 7, w15: 'X', w16: 'Y', w17: 'A@B', w17rank: 3, adv_pct: 0.66, value: 8, playoff_up: 0.82,
        stack: 'LINKSTACK stacks your Patrick Mahomes (QB)',
        scouting: 'Bullish: alpha role, plus a game-stack with the build.',
        quote: 'He is the clear number one option in that offense.',
        flags: [{ type: 'injury', note: 'Hamstring tweak in camp; monitor practice reports.' }],
        tweet: 'Beat writers buzzing about his role expansion.', dTitle: 0.1, dAdv: 0.2,
        usage: { role: 'WR', carry_pg: null, carry_share: null, ypc: null, tgt_share: 0.27, catch_rate: 0.63, ypt: 9.1, cv_carry: null, cv_tgt: 0.31, dk_pg: 15.2 },
        model: { value_pctl: 88, proj_pctl: 84, ceiling_pctl: 71, spike_pctl: 25, adv_pctl: 84, run_eff_pctl: null, rec_eff_pctl: 66, route_eff_pctl: 70, explosive_pctl: 65, oline_pctl: 80, matchup_pctl: 55, boom_pctl: 62, separation_pctl: 60, yac_pctl: 72, sis_value_pctl: 50, consensus: 70.5, divergence: 18.0, n_votes: 15 } },
      { name: 'Live A', pos: 'WR', team: 'KC', adp: 50, rank: 45, proj: 12, ceiling: 28, ceil_pct: 0.7, bye: 7, w15: 'X', w16: 'Y', w17: 'A@B', w17rank: 4, adv_pct: 0.6, value: 5, playoff_up: 0.8,
        stack: 'LINKSTACK same team as Patrick Mahomes', scouting: 'Solid WR2 stack piece.', quote: null, flags: [], tweet: null, dTitle: 0.1, dAdv: 0.2 },
      { name: 'Live B', pos: 'RB', team: 'BUF', adp: 60, rank: 70, proj: 10, ceiling: 22, ceil_pct: 0.6, bye: 14, w15: 'P', w16: 'Q', w17: 'C@D', w17rank: 9, adv_pct: 0.5, value: -10, playoff_up: 0.3,
        stack: 'BRINGBACK bring-back (KC@BUF)', scouting: 'Bearish bring-back dart.', quote: null,
        flags: [{ type: 'trap', note: 'Trap - better value at the same cost nearby.' }], tweet: null,
        usage: { role: 'RB', carry_pg: 14.3, carry_share: 0.58, ypc: 4.1, tgt_share: 0.09, catch_rate: 0.74, ypt: 5.6, cv_carry: 0.27, cv_tgt: 0.49, dk_pg: 11.8 },
        model: { value_pctl: 41, proj_pctl: 45, ceiling_pctl: 38, spike_pctl: 22, adv_pctl: 45, run_eff_pctl: 30, rec_eff_pctl: null, route_eff_pctl: null, explosive_pctl: 28, oline_pctl: 35, matchup_pctl: 18, boom_pctl: 40, separation_pctl: null, yac_pctl: 55, sis_value_pctl: 33, consensus: 39.0, divergence: 24.0, n_votes: 12 } }
    ],
    roster_detail: [
      { name: 'X', pos: 'WR', team: 'KC', bye: 7, proj: 15, ceiling: 33, playoff_up: 0.75, w15: 'X', w16: 'Y', w17: 'A@B',
        stack: 'LINKSTACK onslaught w/ Live Headline Player', scouting: 'Anchor WR on my roster.',
        flags: [{ type: 'age', note: 'Age/role-decline watch.' }], quote: null, tweet: null }
    ]
  };
  // use the real stack glyphs (🔗 link, ↩ bring-back) without embedding raw bytes in this heredoc
  const LINK = String.fromCodePoint(0x1F517), BRING = String.fromCodePoint(0x21A9);
  function fixStacks(o){
    if (o && o.stack) o.stack = o.stack.replace('LINKSTACK', LINK).replace('BRINGBACK', BRING);
  }
  livePayload.board.forEach(fixStacks);
  livePayload.roster_detail.forEach(fixStacks);

  doc.getElementById('board').value = JSON.stringify(livePayload);
  w.buildFromText();
  results.live_branch_nodes = doc.querySelectorAll('#tree .branch').length;
  results.live_board_rows = doc.querySelectorAll('#boardBody tr.drow').length;
  results.live_headline_take = (doc.querySelector('#headline .hl-take') || {}).textContent || null;
  results.live_headline_bad = !!doc.querySelector('#headline .delta.pos-bad');
  results.live_roster_rows = doc.querySelectorAll('#rosterBody tr').length;
  results.live_counts_below = doc.querySelectorAll('#stateCard .cnt.below').length;
  results.live_untracked = doc.querySelectorAll('#stateCard .nchip').length;
  results.live_status = (doc.getElementById('status') || {}).textContent || null;

  // CHANGE 3: headline stack badge renders (headline has no stack key -> looked up from board)
  const liveHlStack = doc.querySelector('#headline .hl-stack');
  results.live_headline_stack = {
    present: !!liveHlStack,
    isLink: !!(liveHlStack && liveHlStack.classList.contains('link')),
    text: liveHlStack ? liveHlStack.textContent : null
  };
  results.live_board_stack_badges = doc.querySelectorAll('#boardBody tr.drow td.player .stk').length;
  results.live_board_hasstack_rows = doc.querySelectorAll('#boardBody tr.drow.hasstack').length;
  results.live_board_bringback_rows = doc.querySelectorAll('#boardBody tr.drow.hasstack.bringback').length;
  results.live_roster_flagcells = doc.querySelectorAll('#rosterBody tr.rosterrow .fchip').length;
  const liveRrow = doc.querySelector('#rosterBody tr.rosterrow');
  liveRrow.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
  const liveRnote = doc.getElementById(liveRrow.getAttribute('data-exp'));
  results.live_roster_note_flagchip = !!(liveRnote && liveRnote.querySelector('.fchip'));
  results.live_roster_note_scouting = !!(liveRnote && /(?:2026 Outlook|Scouting)/.test(liveRnote.textContent || ''));

  // live USAGE + MODEL CARD: expand the first board row (Live Headline Player) and the RB row
  (function(){
    var lrows = Array.from(doc.querySelectorAll('#boardBody tr.drow'));
    var luFound = null, lmFound = null, lmColor = false, lmFoot = null, lRbUsage = null;
    lrows.forEach(function(r){
      var nr = doc.getElementById(r.getAttribute('data-exp'));
      if (!nr) return;
      r.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
      var box = nr.querySelector('.notebox'); if (!box) return;
      var u = box.querySelector('.usage');
      if (u) {
        var t = (u.textContent || '').replace(/\s+/g,' ').trim();
        if (/WR/.test(t) && luFound === null) luFound = t;
        if (/RB/.test(t) && /car\/g/.test(t)) lRbUsage = t;
      }
      var mc = box.querySelector('.modelcard');
      if (mc) {
        if (lmFound === null) lmFound = mc.querySelectorAll('.mchip').length;
        Array.from(mc.querySelectorAll('.mchip .mv')).forEach(function(mv){
          // jsdom normalizes hsla() -> rgba() on read-back, so accept either
          if (/hsla?\(|rgba?\(/.test(mv.getAttribute('style')||'')) lmColor = true;
        });
        var f = mc.querySelector('.mfoot');
        if (f && lmFoot === null && /consensus/.test(f.textContent||'')) lmFoot = (f.textContent||'').replace(/\s+/g,' ').trim();
      }
    });
    results.live_usage_wr = luFound;
    results.live_usage_rb = lRbUsage;
    results.live_model_chips = lmFound;
    results.live_model_color_scaled = lmColor;
    results.live_model_footer = lmFoot;
  })();

  // ---- assertions ----
  const TT = results.tree_click_toggle;
  const BS = results.board_sort;
  const BF = results.board_filter_RB;
  const BN = results.board_row_note;
  const RC = results.board_rich_card_flags;
  const RN = results.roster_note_expand;
  const LHS = results.live_headline_stack;
  const checks = [
    ['state shows 4 position counts', results.state_counts === 4],
    ['counts color RED below target (QB/RB/WR/TE all under low bound)', results.state_counts_below === 4],
    ['anchor rendered (' + results.state_anchor + ')', !!results.state_anchor && results.state_anchor !== '-'],
    ['roster byes rendered (' + results.state_byes + ')', !!results.state_byes && results.state_byes !== '-'],
    ['modeled N of M rendered (' + results.state_modeled + ')', /of/.test(results.state_modeled || '')],
    ['roster chips present (' + results.state_roster_chips + ')', results.state_roster_chips >= 3],
    ['headline take rendered (' + results.headline_take + ')', !!results.headline_take],
    ['headline has 2 deltas', results.headline_delta_count === 2],
    ['headline why present', results.headline_has_why],
    ['headline STACK badge renders for a stacked headline pick', results.headline_stack_render && results.headline_stack_render.present === true && results.headline_stack_render.isLink === true],
    ['tree branch nodes present (' + results.branch_nodes + ')', results.branch_nodes >= 1],
    ['tree branch has condition', results.first_branch_has_condition],
    ['tree color-coded delta chips', results.tree_color_chips > 0],
    ['tree playoff_up chips present', results.tree_playoff_chips > 0],
    ['board header has >=14 columns (' + results.board_head_cols + ')', results.board_head_cols >= 14],
    ['board renders >50 rows (' + results.board_rows + ')', results.board_rows > 50],
    ['board has a hidden note row per data row', results.board_note_rows === results.board_rows],
    ['board highlights tree picks (' + results.board_intree_rows + ')', results.board_intree_rows >= 1],
    ['board heat-colors playoff_up cells', results.board_heat_colored > 0],
    ['board ADP sort ascending monotonic', BS.ascMonotonic === true],
    ['board ADP sort descending monotonic', BS.descMonotonic === true],
    ['board sort click REORDERS rows', BS.reordered === true],
    ['board Player (text) sort monotonic', results.board_sort_name_monotonic === true],
    ['board RB filter -> only RB rows', BF.allRB === true],
    ['board RB filter narrows row count (' + BF.rbRows + '<' + BF.totalRows + ')', BF.narrowed === true],
    ['board ALL restores full rows (' + results.board_rows_after_all + ')', results.board_rows_after_all === results.board_rows],
    ['board row click hidden->card shown', BN.before === false && BN.after === true],
    ['board card has text', BN.hasText === true],
    // STACK tags (CHANGE 1)
    ['board renders STACK badges (' + results.board_stack_badges + ')', results.board_stack_badges > 0],
    ['board STACK badges split link/bring (' + results.board_stack_link_badges + ' link / ' + results.board_stack_bring_badges + ' bring)', results.board_stack_link_badges > 0 && results.board_stack_bring_badges > 0],
    ['board highlights stack rows (' + results.board_hasstack_rows + ')', results.board_hasstack_rows > 0],
    ['board badge count == highlighted-stack-row count', results.board_stack_badge_match === true],
    ['board flags bring-back rows amber (' + results.board_bringback_rows + ')', results.board_bringback_rows > 0],
    // RICH scouting card (CHANGE 2)
    ['rich card: a flagged row was found', RC.found === true],
    ['rich card shows after click', RC.found && RC.shown === true],
    ['rich card has FLAG warning chips (' + (RC.flagChips || 0) + ')', RC.found && RC.flagChips > 0],
    ['rich card flag chips colored danger/caution', RC.found && RC.flagHasDangerOrCaution === true],
    ['rich card flag chips carry note text', RC.found && RC.flagHasNoteText === true],
    ['rich card has Scouting take', RC.found && RC.hasScouting === true],
    ['rich card has metrics (cv/spike/adv/ceiling/playoff_up)', RC.found && RC.hasMetrics === true],
    ['rich card has W17 blow-up rank metric', RC.found && RC.hasW17rank === true],
    ['some cards render a STACK banner (' + results.board_cards_with_stackbanner + ')', results.board_cards_with_stackbanner > 0],
    ['some cards render a quote blockquote (' + results.board_cards_with_quote + ')', results.board_cards_with_quote > 0],
    ['some cards render Buzz/tweet color (' + results.board_cards_with_buzz + ')', results.board_cards_with_buzz > 0],
    // roster
    ['roster panel has columns (' + results.roster_head_cols + ')', results.roster_head_cols >= 8],
    ['roster panel renders rows (' + results.roster_rows + ')', results.roster_rows >= 2],
    ['roster shows W15/W16/W17 schedule', results.roster_playoff_cols === true],
    ['roster has a Flags column (CHANGE 4)', results.roster_has_flags_col === true],
    ['roster shows per-player stack badges (' + results.roster_stack_badges + ')', results.roster_stack_badges > 0],
    ['roster row expands to flags+note', RN.before === false && RN.after === true && RN.hasText === true],
    // live
    ['live render: 2 tree branches', results.live_branch_nodes === 2],
    ['live render: 2+ board rows (' + results.live_board_rows + ')', results.live_board_rows >= 2],
    ['live headline swapped', results.live_headline_take === 'Live Headline Player'],
    ['live negative delta color-coded bad', results.live_headline_bad === true],
    ['live roster re-rendered (1 row)', results.live_roster_rows >= 1],
    ['live counts below target (all 4 under low bound)', results.live_counts_below === 4],
    ['live untracked name shown', results.live_untracked >= 1],
    // live STACK + headline badge (CHANGE 3) + roster flags (CHANGE 4)
    ['live HEADLINE stack badge renders (looked up from board)', LHS.present === true],
    ['live headline stack badge is a link kind', LHS.isLink === true],
    ['live board renders stack badges (' + results.live_board_stack_badges + ')', results.live_board_stack_badges >= 3],
    ['live board highlights stack rows (' + results.live_board_hasstack_rows + ')', results.live_board_hasstack_rows >= 3],
    ['live board flags bring-back row amber (' + results.live_board_bringback_rows + ')', results.live_board_bringback_rows >= 1],
    ['live roster shows a flag chip in Flags column', results.live_roster_flagcells >= 1],
    ['live roster note expands with flag chip', results.live_roster_note_flagchip === true],
    ['live roster note has scouting', results.live_roster_note_scouting === true],
    // USAGE / ROLE line + MODEL CARD (real data)
    ['board cards render a USAGE/ROLE line (' + results.board_usage_cards + ')', results.board_usage_cards > 0],
    ['usage line carries volume numbers (' + (results.board_usage_line || '').slice(0,60) + ')', !!results.board_usage_line && /(car\/g|ypc|tgt|ypt|catch)/.test(results.board_usage_line)],
    ['usage line formats fractions as % (share/tgt/catch)', results.board_usage_frac_as_pct === true],
    ['board cards render a MODEL CARD (' + results.board_model_cards + ')', results.board_model_cards > 0],
    ['model card has labeled percentile chips (' + (results.board_model_chips_sample ? results.board_model_chips_sample.chips : 0) + ')', !!results.board_model_chips_sample && results.board_model_chips_sample.chips > 0],
    ['model chips are COLOR-SCALED by percentile (hsla/rgb)', results.board_model_color_scaled === true],
    ['model card footer shows consensus/divergence/signals (' + (results.board_model_footer || '').slice(0,70) + ')', !!results.board_model_footer && /consensus/.test(results.board_model_footer) && /divergence/.test(results.board_model_footer) && /signals/.test(results.board_model_footer)],
    // live USAGE + MODEL CARD
    ['live WR card renders WR usage line (' + (results.live_usage_wr || '').slice(0,50) + ')', !!results.live_usage_wr && /(tgt|ypt|catch)/.test(results.live_usage_wr)],
    ['live RB card renders RB usage line w/ car/g (' + (results.live_usage_rb || '').slice(0,50) + ')', !!results.live_usage_rb && /car\/g/.test(results.live_usage_rb)],
    ['live model card chips render (' + results.live_model_chips + ')', isFinite(results.live_model_chips) && results.live_model_chips > 0],
    ['live model chips color-scaled', results.live_model_color_scaled === true],
    ['live model footer has consensus (' + (results.live_model_footer || '').slice(0,60) + ')', !!results.live_model_footer && /consensus/.test(results.live_model_footer)],
    // global
    ['ZERO jsdom JS errors', errors.length === 0]
  ];

  console.log('=== decision_dashboard.html jsdom validation (STACK + RICH cards) ===\n');
  console.log(JSON.stringify(results, null, 2));
  console.log('\n--- checks ---');
  let fail = 0;
  checks.forEach(([n, ok]) => {
    if (!ok) { fail++; console.log('FAIL: ' + n); }
    else console.log('PASS: ' + n);
  });
  console.log('\njsdomError count: ' + errors.length);
  if (errors.length) errors.slice(0, 5).forEach(e => console.log('  ERR: ' + e));
  console.log('console.error count (non-fatal): ' + consoleErrs.length);
  console.log(fail === 0 ? '\nVALIDATION: ALL PASS' : ('\nVALIDATION: ' + fail + ' FAILURE(S)'));
  process.exit(fail === 0 ? 0 : 1);
}, 300);
