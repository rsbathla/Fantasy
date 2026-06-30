/* dashboard_render.optimized.js — drop-in replacement for the renderFusion/renderDFS
 * pattern in _cc_template.html.
 *
 * PROBLEM (current code): every sort click, every position-filter click, and every
 * SEARCH KEYSTROKE calls render*() which (1) re-concatenates a multi-thousand-cell
 * HTML string, (2) does tbody.innerHTML = h (full DOM teardown + reparse + rebuild of
 * ~3,700 cells for the 371-row tables), and (3) re-binds an onclick to every <th>.
 *
 * FIX (this module): build each row's <tr> ONCE. Thereafter:
 *   - sort   = reorder the EXISTING <tr> nodes (appendChild moves, never recreates)
 *   - filter = toggle tr.style.display (no rebuild)
 *   - search = same, DEBOUNCED
 *   - sort handlers bound ONCE via delegation on <thead> (no per-render rebind)
 *   - rows for a tab are built LAZILY on first view
 * Net: one O(n) build, then O(n log n) pointer reorder per sort and O(n) display
 * toggle per filter — zero string building or innerHTML churn after first paint.
 */
function PerfTable(tbody, data, opts) {
  // opts: {buildRow(d)->tr, cmp(a,b,state), match(d,state), state}
  const rows = new Array(data.length);
  const frag = document.createDocumentFragment();
  for (let i = 0; i < data.length; i++) {        // BUILD ONCE
    const tr = opts.buildRow(data[i]);
    tr.__d = data[i];
    rows[i] = tr;
    frag.appendChild(tr);
  }
  tbody.appendChild(frag);
  const state = opts.state;

  function filterOnly() {                 // search / position filter: NO reorder, NO rebuild
    for (let i = 0; i < rows.length; i++)
      rows[i].style.display = opts.match(rows[i].__d, state) ? '' : 'none';
  }
  function sortOnly() {                   // header click: reorder EXISTING nodes only
    const vis = [];
    for (let i = 0; i < rows.length; i++) if (rows[i].style.display !== 'none') vis.push(rows[i]);
    vis.sort((a, b) => opts.cmp(a.__d, b.__d, state));
    const f = document.createDocumentFragment();
    for (let i = 0; i < vis.length; i++) f.appendChild(vis[i]);
    tbody.appendChild(f);
  }
  function apply() { filterOnly(); sortOnly(); }
  apply();
  return { apply, filterOnly, sortOnly, state, rows };
}

function bindSortOnce(thead, state, apply) {            // ONE delegated listener
  thead.addEventListener('click', e => {
    const th = e.target.closest('th[data-k]'); if (!th) return;
    const k = th.dataset.k;
    if (state.sort === k) state.dir *= -1;
    else { state.sort = k; state.dir = (k === 'n' || k === 'adp') ? 1 : -1; }
    apply();
  });
}

function debounce(fn, ms) {                              // for search oninput
  let t; return function (...a) { clearTimeout(t); t = setTimeout(() => fn.apply(this, a), ms); };
}

if (typeof module !== 'undefined') module.exports = { PerfTable, bindSortOnce, debounce };
