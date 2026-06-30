# bb-components — Accessible Web Component Library

A small, dependency-free Web Component library for the Best Ball / DFS Command
Center. Five custom elements — `<bb-tabs>`, `<bb-segmented>`, `<bb-search>`,
`<bb-badge>`, `<bb-data-table>` — each fully keyboard-operable, screen-reader
labeled, themeable, and responsive.

- **No build step, no framework, no external dependencies.**
- Ships as a **classic script** (`<script src="./bb-components.js"></script>`) —
  works straight from `file://` with no CORS or module concerns.
- Styling is encapsulated in **Shadow DOM**; theming flows in through **CSS
  custom properties** that fall back to host vars and then to safe defaults.

```html
<link rel="stylesheet" href="./bb-components.css">
<script src="./bb-components.js"></script>
```

Open `components-demo.html` for a live showcase of every component in every state.

---

## 1 · Architecture

### 1.1 The `BBElement` base class

Every component extends a shared base, `BBElement extends HTMLElement`:

```js
class BBElement extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' }); // encapsulated subtree
    this._built = false;                              // build-once guard
  }
  _injectStyles(componentCss) { /* TOKENS + componentCss into one <style> */ }
  _emit(name, detail) { /* bubbling, composed CustomEvent */ }
  _reflectBool(name, on) { /* reflect a boolean attribute */ }
  $(sel) { /* querySelector inside the shadow root */ }
  $$(sel) { /* querySelectorAll -> array */ }
}
```

The base provides four things every component needs: a shadow root, a one-call
style injector (shared design tokens + that component's CSS), a typed event
emitter, and small DOM helpers. Each element is also **idempotent**: it builds
its shadow DOM exactly once (`_built` guard) and only *updates* on subsequent
`connectedCallback` / attribute / property changes — so moving an element around
the DOM never rebuilds it.

Each `customElements.define(...)` call is guarded:

```js
if (!customElements.get('bb-tabs')) customElements.define('bb-tabs', BBTabs);
```

so the script is safe to include more than once (e.g. on a page that also pulls
the dashboard bundle).

### 1.2 Shadow DOM + token theming model

All component CSS lives inside the shadow root, injected as a single `<style>`
that begins with a shared **design-token block**. Each token resolves in three
tiers — **host `--bb-*` → legacy host var → hard default**:

```css
:host{
  --_accent: var(--bb-accent, var(--acc, #4ea1ff));
  --_warn:   var(--bb-warn,   var(--warn, #e8a33d));
  --_muted:  var(--bb-muted,  var(--mut, #9aa3b6));
  /* ...surfaces, lines, radius, spacing, font, focus, motion... */
}
```

That means the components automatically inherit the existing dashboard theme
(which already defines `--acc`, `--warn`, `--mut`, `--p1`, `--ln`, ...). To
re-skin them explicitly, define the **`--bb-*`** palette — globally in
`bb-components.css` (`:root`, with a `prefers-color-scheme: dark` block), or on
any ancestor to scope a local theme. Components expose **`::part()`** hooks so
hosts can reach inside the shadow boundary for fine-grained overrides, and every
focusable control gets a **`:focus-visible`** ring (keyboard-only). All
animation and transition is gated behind
`@media (prefers-reduced-motion: reduce)`.

### 1.3 CustomEvent communication model

Components are decoupled from the host: they never call host functions. They
announce state changes by dispatching **`CustomEvent`s** that are
`bubbles: true, composed: true` (so they cross the shadow boundary) with a typed
`detail` payload. The host listens on the element:

```js
table.addEventListener('bb-search', e => applyFilter(e.detail.query));
posFilter.addEventListener('bb-change', e => setPosition(e.detail.value));
tabs.addEventListener('bb-tab-change', e => track(e.detail.id));
```

This is the same pattern the existing dashboard uses for its inline controls,
so wiring is familiar: data flows *down* via properties/attributes, intent flows
*up* via events.

### 1.4 Build-once / reorder performance design of the table

`<bb-data-table>` is built for large boards (the real dashboard renders ~370
rows) and avoids the classic "re-`innerHTML` on every interaction" trap:

- **Build once.** When `.rows`/`.columns` are set, each `<tr>` is created
  exactly once and cached in a parallel array (`this._trCache`). The first paint
  appends them all via a single `DocumentFragment`.
- **Sort = reorder, never rebuild.** Sorting computes an order over the *cached*
  nodes and appends them into a `DocumentFragment` in the new order;
  `appendChild` **moves** an already-attached node, so the rows are re-sequenced
  without recreating a single DOM node or touching `innerHTML`. Sorting is
  **stable** (ties keep original order) and numeric sort treats `null`/blank as
  lowest.
- **Filter = toggle display.** Filtering flips `row.style.display` on the cached
  rows — no add/remove, no rebuild.
- **One delegated header handler.** A single click listener on `<thead>`
  handles all sortable columns (event delegation), bound once at build time.
- **No innerHTML churn after first paint.** Loading/empty/error states are added
  and removed as discrete state rows, leaving the cached data rows intact
  (hidden) so returning to the populated state is instant.

The net effect: the cost of a sort or filter is O(n) pointer moves / style
writes, with zero parse/layout-thrash from markup regeneration.

---

## 2 · Component API reference

> Conventions: **Attributes** are HTML attributes (those marked *reflected* are
> kept in sync with the element's state). **Properties** are JS-set
> (`el.prop = ...`). **Events** are `CustomEvent`s (bubbling + composed).

---

### `<bb-tabs>` — WAI-ARIA Tabs

Tab panels are **light-DOM children** with `data-tab="<id>"`; the component shows
the active one and hides the rest.

| Aspect | Detail |
|---|---|
| **Attributes** | `tabs` (JSON array of `{id,label}`); `selected` (active id, **reflected**) |
| **Properties** | `.tabs = [{id,label}]` (array); `.selected` (string, get/set) |
| **Events** | `bb-tab-change` → `detail: { id }` (fires only when the active tab actually changes) |
| **Slots** | default slot = the panel elements (`<div data-tab="id">…</div>`) |
| **CSS parts** | `tablist`, `tab` |
| **CSS custom props** | `--bb-accent` (active underline + focus), `--bb-text`, `--bb-muted`, `--bb-line`, `--bb-radius-sm`, `--bb-duration` |
| **ARIA** | tablist `role="tablist"`; each tab `role="tab"` + `aria-selected` + `aria-controls`; each panel `role="tabpanel"` + `aria-labelledby` + `tabindex="0"`; inactive panels get `hidden` |
| **Keyboard** | `ArrowLeft`/`ArrowRight` (and `Up`/`Down`) move between tabs and wrap; `Home`/`End` jump to first/last; `Enter`/`Space` select; **focus follows selection**; **roving tabindex** (selected tab `0`, others `-1`) |
| **Responsive** | tablist scrolls horizontally (`overflow-x:auto`) on narrow screens |

```html
<bb-tabs id="tabs" selected="board">
  <div data-tab="board">…Best-Ball plan…</div>
  <div data-tab="dfs">…DFS scenarios…</div>
  <div data-tab="def">…Defense…</div>
</bb-tabs>
<script>
  tabs.tabs = [
    { id: 'board', label: 'Best-Ball Plan' },
    { id: 'dfs',   label: 'DFS Scenarios' },
    { id: 'def',   label: 'Defense' }
  ];
  tabs.addEventListener('bb-tab-change', e => console.log('now on', e.detail.id));
</script>
```

---

### `<bb-segmented>` — radiogroup (segmented control)

A single-select control, e.g. the position filter `ALL / QB / RB / WR / TE`.

| Aspect | Detail |
|---|---|
| **Attributes** | `options` (comma-separated list); `value` (**reflected**); `label` (becomes the group's `aria-label`) |
| **Properties** | `.options = ['ALL','QB',…]` (array or comma string); `.value` (string, get/set) |
| **Events** | `bb-change` → `detail: { value }` (fires only on actual change) |
| **Slots** | none (options are generated from `options`) |
| **CSS parts** | `group`, `option` |
| **CSS custom props** | `--bb-accent` (selected background), `--bb-surface`, `--bb-muted`, `--bb-line`, `--bb-radius`, `--bb-radius-sm`, `--bb-duration` |
| **ARIA** | group `role="radiogroup"` + `aria-label`; each option `role="radio"` + `aria-checked` |
| **Keyboard** | `ArrowLeft`/`ArrowRight`/`ArrowUp`/`ArrowDown` move and wrap; `Home`/`End` jump; `Space`/`Enter` select; **roving tabindex** (checked option `0`, others `-1`) |
| **Responsive** | options wrap (`flex-wrap`) when space is tight |

```html
<bb-segmented id="pos" label="Filter by position"
              options="ALL,QB,RB,WR,TE" value="ALL"></bb-segmented>
<script>
  pos.addEventListener('bb-change', e => filterBoard(e.detail.value));
</script>
```

---

### `<bb-search>` — labeled, debounced search box

| Aspect | Detail |
|---|---|
| **Attributes** | `label` (rendered SR-only but present for AT); `placeholder`; `debounce` (ms, default `80`); `value` (initial value) |
| **Properties** | `.value` (string, get/set); `.count` (number) → announces "`{n} results`" in the live region |
| **Events** | `bb-search` → `detail: { query }`, **debounced** (also fires immediately with `''` on clear) |
| **Slots** | none |
| **CSS parts** | `field`, `input`, `clear`, `status` |
| **CSS custom props** | `--bb-surface-2` (input bg), `--bb-text`, `--bb-muted`, `--bb-muted-2`, `--bb-line`, `--bb-radius`, `--bb-focus` |
| **ARIA** | `<input type="search">` linked to a visually-hidden `<label>` via `aria-labelledby`; Clear button has `aria-label="Clear search"`; a `aria-live="polite"` region announces the result count |
| **Keyboard** | type to search (debounced emit); `Escape` clears the field, refocuses it, and emits `bb-search {query:''}`; Clear button is reachable via Tab and operable with Enter/Space; Clear appears only when the field is non-empty |

```html
<bb-search id="q" label="Search players by name"
           placeholder="Type a name…" debounce="120"></bb-search>
<script>
  q.addEventListener('bb-search', e => {
    const n = runFilter(e.detail.query);
    q.count = n;                 // -> screen reader hears "12 results"
  });
</script>
```

---

### `<bb-badge>` — status / flag chip

The slotted **text is the accessible name** — color is never the only signal,
and every variant meets ≥ 4.5:1 contrast on the dark surface.

| Aspect | Detail |
|---|---|
| **Attributes** | `variant` = `good` \| `warn` \| `bad` \| `info` \| `neutral` \| `accent` (default `neutral`); `title` (optional tooltip) |
| **Properties** | — (driven by attributes + slotted text) |
| **Events** | — |
| **Slots** | default slot = the badge text (real content) |
| **CSS parts** | `badge` |
| **CSS custom props** | `--bb-good`, `--bb-warn`, `--bb-bad`, `--bb-info`, `--bb-accent`, `--bb-muted`, `--bb-radius-sm` |
| **ARIA** | none added — the badge is a decorative wrapper around real text, so the text alone is the accessible content (no redundant role) |
| **Keyboard** | not focusable (it is static content, not a control) |

```html
<bb-badge variant="good"   title="High weekly ceiling">BOOM MERCHANT</bb-badge>
<bb-badge variant="accent" title="Beats man coverage">MAN-BEATER</bb-badge>
<bb-badge variant="bad"    title="Low weekly floor">FLOOR RISK</bb-badge>
```

---

### `<bb-data-table>` — high-performance accessible table

The centerpiece. A real `<table>` with sortable headers, build-once rows,
sort-by-reorder, filter-by-display, four states (populated / loading / empty /
error), and a responsive cards mode.

| Aspect | Detail |
|---|---|
| **Attributes** | `loading` (bool → skeleton + `aria-busy`); `error` (string → error state); `empty-text` (default empty message); `responsive` = `scroll` (default) \| `cards`; `caption`; `sticky` (default **on**; sticky header) |
| **Properties** | `.columns = [{ key, label, align?, sortable?, sortType?('num'|'text'), render?(value,row)=>string\|Node, width? }]`; `.rows` (array); `.rowKey` (key string or `fn(row)`) |
| **Methods** | `setRows(rows)`; `setFilter(predicate \| null)`; `sort(key, dir)` where `dir` ∈ `'asc'`/`'desc'` |
| **Events** | — (the table reflects state visually + via the live region; pair it with `<bb-search>`/`<bb-segmented>` in the toolbar slot for interaction) |
| **Slots** | `toolbar` (renders above the table — drop search/segmented here); `empty` (custom empty content); `error` (custom error content) |
| **CSS parts** | `wrap`, `toolbar`, `table`, `caption`, `header`, `header-cell`, `body`, `row`, `cell` |
| **CSS custom props** | `--bb-surface`, `--bb-surface-2` (skeleton), `--bb-line`, `--bb-text`, `--bb-muted`, `--bb-bad` (error text), `--bb-accent` (row hover/focus), `--bb-radius` |
| **ARIA** | semantic `<table><caption><thead><tbody>`; `<th scope="col">`; sortable headers contain a `<button>`; the active `<th>` carries `aria-sort` (`none`/`ascending`/`descending`); loading sets `tbody aria-busy="true"` with ~6 skeleton rows marked `aria-hidden="true"`; empty is one full-colspan row with `role="status"`; error is one full-colspan row with `role="alert"`; a `aria-live="polite"` region announces the new sort and the visible-row count |
| **Keyboard** | sort buttons are reachable via Tab and toggle on `Enter`/`Space`, cycling `none → descending → ascending → none`; the populated rows are static content (no per-cell focus trap), so keyboard users tab straight through the header controls |
| **Edge cases** | `null`/`undefined`/empty cell → en-dash `–`; numeric sort puts `null` lowest; long text wraps (`overflow-wrap:anywhere`, no horizontal overflow break); 0 columns or 0 rows render the empty state gracefully; sorting is stable |
| **Responsive** | `scroll` (default): horizontally scrollable wrapper (`overflow-x:auto`) with a sticky `<thead>`. `cards`: under ~640px each row reflows into a labeled card — the header is hidden and each cell shows its column label via `data-label`/`::before`. |

```html
<bb-data-table id="board"
  caption="Fantasy board — sortable; filtered live by the toolbar."
  responsive="scroll" empty-text="No players match your filters.">
  <!-- toolbar slot: controls render above the table -->
  <div slot="toolbar" style="display:flex;gap:10px;flex-wrap:wrap">
    <bb-search id="bq" label="Search the table" placeholder="Filter…"></bb-search>
    <bb-segmented id="bp" label="Position" options="ALL,QB,RB,WR,TE" value="ALL"></bb-segmented>
  </div>
  <!-- optional custom states -->
  <span slot="empty">No players for this slate yet.</span>
  <span slot="error">Feed timed out — please retry.</span>
</bb-data-table>

<script>
  const POS = { QB:'#e0567a', RB:'#37b87a', WR:'#3b8ef0', TE:'#e8a33d' };
  board.columns = [
    { key:'n', label:'Player', sortable:true, sortType:'text' },
    { key:'p', label:'Pos', align:'center',
      render: v => { const s=document.createElement('span'); s.textContent=v;
        s.style.cssText='font-weight:800;border-radius:4px;padding:1px 6px;background:'+(POS[v]||'#9aa3b6'); return s; } },
    { key:'c', label:'Consensus', align:'right', sortable:true, sortType:'num' },
    { key:'pw17', label:'% W17', align:'right', sortable:true, sortType:'num',
      render: v => v == null ? null : v + '%' }   // null -> en-dash automatically
  ];
  board.rowKey = 'n';
  board.setRows(players);          // build once
  board.sort('c', 'desc');         // reorder cached nodes, never rebuild

  // wire the toolbar controls -> filter (display toggle, no rebuild)
  let q = '', pos = 'ALL';
  const refilter = () => {
    board.setFilter(r =>
      (pos === 'ALL' || r.p === pos) &&
      (!q || r.n.toLowerCase().includes(q.toLowerCase())));
    bq.count = players.filter(r =>
      (pos === 'ALL' || r.p === pos) &&
      (!q || r.n.toLowerCase().includes(q.toLowerCase()))).length;
  };
  bq.addEventListener('bb-search', e => { q = e.detail.query; refilter(); });
  bp.addEventListener('bb-change', e => { pos = e.detail.value; refilter(); });

  // states
  board.setAttribute('loading', '');      // skeleton + aria-busy
  board.removeAttribute('loading');
  board.setAttribute('error', 'Could not load projections.'); // role="alert"
</script>
```

---

## 3 · Theming quick reference

Override any of these on `:root` (in `bb-components.css`) or any ancestor to
re-skin the whole library. Each falls back to the dashboard's legacy var, then a
default.

| Token | Falls back to | Purpose |
|---|---|---|
| `--bb-accent` | `--acc` | primary accent (active tab, selected segment, focus) |
| `--bb-good` / `--bb-warn` / `--bb-bad` / `--bb-info` | `--good`/`--warn`/`--bad`/`--acc` | badge + status colors |
| `--bb-text` / `--bb-muted` / `--bb-muted-2` | `--tx` / `--mut` / `--mut2` | foreground text tiers |
| `--bb-bg` / `--bb-surface` / `--bb-surface-2` | `--bg` / `--p1` / `--p2` | backgrounds |
| `--bb-line` | `--ln` | borders / dividers |
| `--bb-radius` / `--bb-radius-sm` | — | corner radii |
| `--bb-space` / `--bb-space-sm` | — | spacing rhythm |
| `--bb-font` | — | font stack |
| `--bb-focus` | `--bb-accent` → `--acc` | focus-ring color |
| `--bb-duration` | — | transition duration (forced to `0s` under reduced-motion) |

`bb-components.css` ships sensible light defaults plus a
`@media (prefers-color-scheme: dark)` block tuned to match the Command Center.
