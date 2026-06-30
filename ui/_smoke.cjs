/* jsdom smoke test for bb-components.js — run: node ui/_smoke.cjs
 * Requires jsdom the same way the repo's _validate_cc.cjs does. */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const jsPath = path.join(__dirname, 'bb-components.js');
const js = fs.readFileSync(jsPath, 'utf-8');

let pass = 0, fail = 0;
function ok(name, cond) {
  if (cond) { pass++; console.log('PASS: ' + name); }
  else { fail++; console.error('FAIL: ' + name); }
}

const dom = new JSDOM('<!doctype html><html><head></head><body></body></html>', {
  runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(w) { w.sendPrompt = function () {}; }
});
const w = dom.window, doc = w.document;

// Inject the library as a classic inline script (mirrors <script src>).
const s = doc.createElement('script');
s.textContent = js;
doc.body.appendChild(s);

// 1) all 5 elements defined
['bb-tabs', 'bb-segmented', 'bb-search', 'bb-badge', 'bb-data-table'].forEach(function (tag) {
  ok('defined ' + tag, !!w.customElements.get(tag));
});

// ---------- bb-data-table ----------
const table = doc.createElement('bb-data-table');
table.columns = [
  { key: 'n', label: 'Name', sortable: true, sortType: 'text' },
  { key: 'c', label: 'Consensus', align: 'right', sortable: true, sortType: 'num' },
  { key: 'pos', label: 'Pos', render: function (v) { return v ? ('[' + v + ']') : null; } }
];
table.rows = [
  { n: 'Bijan Robinson', c: 92, pos: 'RB' },
  { n: 'CeeDee Lamb', c: 88, pos: 'WR' },
  { n: 'Mystery Player', c: null, pos: null } // null cell + null render
];
doc.body.appendChild(table);

const sr = table.shadowRoot;
function bodyRows() { return sr.querySelectorAll('tbody tr:not(.state):not(.skel)'); }

ok('(a) 3 <tr> in tbody', bodyRows().length === 3);

const sortableTh = Array.prototype.slice.call(sr.querySelectorAll('thead th'))
  .filter(function (th) { return th.querySelector('button'); })[0];
ok('(b) sortable <th> has <button>', !!sortableTh && !!sortableTh.querySelector('button'));
ok('(b) sortable <th> has aria-sort', !!sortableTh && sortableTh.hasAttribute('aria-sort'));

// (c) sort reorders without changing count
const before = bodyRows().length;
table.sort('c', 'asc');
const afterCount = bodyRows().length;
// after asc by num, null is lowest -> Mystery first
const firstCellText = sr.querySelector('tbody tr:not(.state):not(.skel) td').textContent.trim();
ok('(c) sort keeps row count', before === 3 && afterCount === 3);
ok('(c) sort asc puts null-num row first', firstCellText === 'Mystery Player');
table.sort('c', 'desc');
const firstDesc = sr.querySelector('tbody tr:not(.state):not(.skel) td').textContent.trim();
ok('(c) sort desc puts highest first (Bijan)', firstDesc === 'Bijan Robinson');

// (g) null cell renders en-dash
const enDash = '–';
var nullCellFound = false;
Array.prototype.slice.call(sr.querySelectorAll('tbody tr:not(.state):not(.skel)')).forEach(function (tr) {
  var cells = tr.querySelectorAll('td');
  // Consensus column is index 1
  if (tr.textContent.indexOf('Mystery') >= 0) {
    if (cells[1].textContent.trim() === enDash) nullCellFound = true;
  }
});
ok('(g) null cell renders en-dash', nullCellFound);

// (d) loading sets aria-busy
table.setAttribute('loading', '');
ok('(d) loading sets tbody aria-busy=true', sr.querySelector('tbody').getAttribute('aria-busy') === 'true');
const skel = sr.querySelectorAll('tbody tr.skel').length;
ok('(d) loading renders skeleton rows', skel >= 1);
table.removeAttribute('loading');

// (e) clearing rows -> role=status empty row
table.setRows([]);
const emptyRow = sr.querySelector('tbody tr.state [role="status"]');
ok('(e) empty shows role=status row', !!emptyRow);

// (f) error -> role=alert
table.setAttribute('error', 'Failed to load.');
const errRow = sr.querySelector('tbody tr.state [role="alert"]');
ok('(f) error shows role=alert row', !!errRow && errRow.textContent.indexOf('Failed') >= 0);
table.removeAttribute('error');

// edge: 0 columns / 0 rows graceful
const t2 = doc.createElement('bb-data-table');
t2.columns = [];
t2.rows = [];
doc.body.appendChild(t2);
ok('edge: 0 cols/0 rows does not throw + shows empty', !!t2.shadowRoot.querySelector('tbody tr.state [role="status"]'));

// ---------- bb-tabs ----------
const tabs = doc.createElement('bb-tabs');
const p1 = doc.createElement('div'); p1.setAttribute('data-tab', 'a'); p1.textContent = 'Panel A';
const p2 = doc.createElement('div'); p2.setAttribute('data-tab', 'b'); p2.textContent = 'Panel B';
tabs.appendChild(p1); tabs.appendChild(p2);
tabs.tabs = [{ id: 'a', label: 'Alpha' }, { id: 'b', label: 'Beta' }];
doc.body.appendChild(tabs);

const tsr = tabs.shadowRoot;
ok('tabs: role=tablist present', !!tsr.querySelector('[role="tablist"]'));
const tabButtons = tsr.querySelectorAll('[role="tab"]');
ok('tabs: 2 tabs rendered', tabButtons.length === 2);
const zeroTab = Array.prototype.slice.call(tabButtons).filter(function (b) { return b.tabIndex === 0; });
ok('tabs: exactly one tab has tabindex=0', zeroTab.length === 1);
ok('tabs: first panel visible, second hidden',
  !p1.hasAttribute('hidden') && p2.hasAttribute('hidden'));

// ArrowRight moves selection + emits bb-tab-change
let gotEvent = null;
tabs.addEventListener('bb-tab-change', function (e) { gotEvent = e.detail.id; });
const firstTab = tabButtons[0];
firstTab.focus();
const kev = new w.KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true, cancelable: true });
firstTab.dispatchEvent(kev);
ok('tabs: ArrowRight moved selection to b', tabs.getAttribute('selected') === 'b');
ok('tabs: ArrowRight emitted bb-tab-change {id:b}', gotEvent === 'b');
ok('tabs: panel B now visible after move', !p2.hasAttribute('hidden') && p1.hasAttribute('hidden'));

// ---------- bb-segmented ----------
const seg = doc.createElement('bb-segmented');
seg.setAttribute('label', 'Position');
seg.options = ['ALL', 'QB', 'RB', 'WR', 'TE'];
doc.body.appendChild(seg);
const ssr = seg.shadowRoot;
ok('segmented: role=radiogroup present', !!ssr.querySelector('[role="radiogroup"]'));
ok('segmented: 5 radios', ssr.querySelectorAll('[role="radio"]').length === 5);
let segVal = null;
seg.addEventListener('bb-change', function (e) { segVal = e.detail.value; });
const qbRadio = ssr.querySelector('[role="radio"][data-value="QB"]');
qbRadio.dispatchEvent(new w.KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true }));
// space selects the focused radio; ensure focus then space path also covered via click
qbRadio.click();
ok('segmented: selecting QB sets value + emits bb-change', seg.getAttribute('value') === 'QB' && segVal === 'QB');
ok('segmented: aria-checked reflects selection', qbRadio.getAttribute('aria-checked') === 'true');

// ---------- bb-search ----------
const search = doc.createElement('bb-search');
search.setAttribute('label', 'Search players');
search.setAttribute('debounce', '0');
doc.body.appendChild(search);
const sesr = search.shadowRoot;
ok('search: has labelled input', !!sesr.querySelector('input[aria-labelledby]'));
ok('search: has aria-live region', !!sesr.querySelector('[aria-live="polite"]'));
search.count = 7;
ok('search: count announces results', sesr.querySelector('[aria-live="polite"]').textContent.indexOf('7 results') >= 0);

// ---------- bb-badge ----------
const badge = doc.createElement('bb-badge');
badge.setAttribute('variant', 'good');
badge.textContent = 'BOOM MERCHANT';
doc.body.appendChild(badge);
ok('badge: ::part(badge) wrapper exists', !!badge.shadowRoot.querySelector('[part="badge"]'));
ok('badge: text is accessible name (slotted)', badge.textContent === 'BOOM MERCHANT');

console.log('\n----------------------------------------');
console.log('SMOKE RESULT: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
