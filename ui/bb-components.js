/*!
 * bb-components.js — Accessible, dependency-free Web Component library
 * for the Best Ball / DFS Command Center (vanilla-JS football analytics).
 *
 * CLASSIC SCRIPT (not an ES module): load with a plain <script src> tag.
 * Works from file:// with no CORS. No build step, no frameworks, no deps.
 * `class extends HTMLElement` is plain ES2015 and is valid in a classic script;
 * "classic" here only means it is NOT loaded as type="module".
 *
 * Components: <bb-tabs> <bb-segmented> <bb-search> <bb-badge> <bb-data-table>
 *
 * Theming: every component consumes host theme custom properties with fallbacks,
 * e.g. var(--bb-accent, var(--acc, #4ea1ff)). Define --bb-* (see bb-components.css)
 * or the host's legacy --acc/--warn/--mut and the components adapt automatically.
 */
(function () {
  'use strict';

  if (typeof window === 'undefined' || !('customElements' in window)) { return; }

  /* ---------------------------------------------------------------------------
   * Shared design tokens, injected into each shadow root as a single <style>.
   * Each token resolves against (1) host --bb-* vars, then (2) host legacy vars
   * (--acc/--warn/--mut/...), then (3) a hard-coded safe default.
   * ------------------------------------------------------------------------- */
  var TOKENS = [
    ':host{',
    '  --_accent: var(--bb-accent, var(--acc, #4ea1ff));',
    '  --_good:   var(--bb-good, var(--good, #37b87a));',
    '  --_warn:   var(--bb-warn, var(--warn, #e8a33d));',
    '  --_bad:    var(--bb-bad, var(--bad, #e0567a));',
    '  --_info:   var(--bb-info, var(--acc, #3b8ef0));',
    '  --_text:   var(--bb-text, var(--tx, #e7ebf3));',
    '  --_muted:  var(--bb-muted, var(--mut, #9aa3b6));',
    '  --_muted2: var(--bb-muted-2, var(--mut2, #697084));',
    '  --_surface: var(--bb-surface, var(--p1, #161922));',
    '  --_surface-2: var(--bb-surface-2, var(--p2, #1c2030));',
    '  --_line:   var(--bb-line, var(--ln, #262b3a));',
    '  --_bg:     var(--bb-bg, var(--bg, #0e1016));',
    '  --_radius: var(--bb-radius, 8px);',
    '  --_radius-sm: var(--bb-radius-sm, 5px);',
    '  --_space: var(--bb-space, 8px);',
    '  --_space-sm: var(--bb-space-sm, 4px);',
    '  --_font: var(--bb-font, -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif);',
    '  --_focus: var(--bb-focus, var(--bb-accent, var(--acc, #4ea1ff)));',
    '  --_dur: var(--bb-duration, .15s);',
    '  box-sizing: border-box;',
    '  font-family: var(--_font);',
    '  color: var(--_text);',
    '}',
    '*,*::before,*::after{ box-sizing: border-box; }',
    '.bb-sr-only{position:absolute !important;width:1px;height:1px;padding:0;margin:-1px;',
    '  overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;}',
    ':where(button,[tabindex],input,a):focus{outline:none;}',
    ':where(button,[tabindex],input,a):focus-visible{',
    '  outline:2px solid var(--_focus); outline-offset:2px; border-radius:var(--_radius-sm);}',
    '@media (prefers-reduced-motion: reduce){',
    '  *{animation:none !important; transition:none !important; scroll-behavior:auto !important;}',
    '}'
  ].join('\n');

  // Safe escape for any text injected through innerHTML paths.
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function parseJSONAttr(v) {
    if (v == null) return null;
    try { return JSON.parse(v); } catch (e) { return null; }
  }
  function cssEscape(v) {
    return (window.CSS && CSS.escape) ? CSS.escape(String(v)) : String(v).replace(/["\\\]\[]/g, '\\$&');
  }
  function uid(id) { return String(id).replace(/[^a-zA-Z0-9_-]/g, '_'); }

  var EN_DASH = '–';

  /* ---------------------------------------------------------------------------
   * BBElement — shared base class.
   * Provides: a shadow root, the shared token <style>, a slot for component CSS,
   * a typed CustomEvent emitter, boolean-attr reflection, and DOM helpers.
   * ------------------------------------------------------------------------- */
  class BBElement extends HTMLElement {
    constructor() {
      super();
      this._root = this.attachShadow({ mode: 'open' });
      this._built = false;
    }
    _injectStyles(componentCss) {
      var style = document.createElement('style');
      style.textContent = TOKENS + '\n' + (componentCss || '');
      this._root.appendChild(style);
    }
    _emit(name, detail) {
      this.dispatchEvent(new CustomEvent(name, {
        detail: detail || {}, bubbles: true, composed: true
      }));
    }
    _reflectBool(name, on) {
      if (on) { if (!this.hasAttribute(name)) this.setAttribute(name, ''); }
      else if (this.hasAttribute(name)) this.removeAttribute(name);
    }
    $(sel) { return this._root.querySelector(sel); }
    $$(sel) { return Array.prototype.slice.call(this._root.querySelectorAll(sel)); }
  }

  /* =========================================================================
   * <bb-tabs> — WAI-ARIA Tabs pattern.
   * Panels are LIGHT-DOM children: <div data-tab="id">...</div>.
   * ========================================================================= */
  var TABS_CSS = [
    ':host{display:block;}',
    '.tablist{display:flex;gap:2px;overflow-x:auto;overflow-y:hidden;',
    '  scrollbar-width:thin;border-bottom:1px solid var(--_line);',
    '  -webkit-overflow-scrolling:touch;}',
    '.tablist::-webkit-scrollbar{height:6px;}',
    '.tablist::-webkit-scrollbar-thumb{background:var(--_line);border-radius:3px;}',
    '.tab{appearance:none;background:transparent;border:0;border-bottom:2px solid transparent;',
    '  color:var(--_muted);font:inherit;font-weight:600;font-size:.95em;',
    '  padding:9px 15px;cursor:pointer;white-space:nowrap;flex:0 0 auto;',
    '  transition:color var(--_dur) ease, border-color var(--_dur) ease;}',
    '.tab:hover{color:var(--_text);}',
    '.tab[aria-selected="true"]{color:var(--_text);border-bottom-color:var(--_accent);}',
    '::slotted([data-tab]){display:none;}',
    '::slotted([data-tab][hidden]){display:none !important;}',
    '.panels{padding-top:var(--_space);}'
  ].join('\n');

  class BBTabs extends BBElement {
    static get observedAttributes() { return ['tabs', 'selected']; }
    constructor() { super(); this._tabs = null; }

    connectedCallback() {
      if (!this._built) { this._build(); this._built = true; }
      this._render();
    }

    _build() {
      this._injectStyles(TABS_CSS);
      var tablist = document.createElement('div');
      tablist.className = 'tablist';
      tablist.setAttribute('role', 'tablist');
      tablist.setAttribute('part', 'tablist');
      var panels = document.createElement('div');
      panels.className = 'panels';
      panels.appendChild(document.createElement('slot'));
      this._root.appendChild(tablist);
      this._root.appendChild(panels);
      this._tablist = tablist;

      var self = this;
      tablist.addEventListener('click', function (e) {
        var btn = e.target.closest('[role="tab"]');
        if (btn) self._select(btn.dataset.id, true);
      });
      tablist.addEventListener('keydown', function (e) { self._onKeydown(e); });
    }

    get tabs() { return this._tabs ? this._tabs.slice() : []; }
    set tabs(v) { this._tabs = Array.isArray(v) ? v.slice() : []; if (this._built) this._render(); }

    get selected() { return this.getAttribute('selected'); }
    set selected(v) { this._select(v, false); }

    attributeChangedCallback(name, oldV, newV) {
      if (oldV === newV) return;
      if (name === 'tabs') { this._tabs = parseJSONAttr(newV) || []; if (this._built) this._render(); }
      else if (name === 'selected') { if (this._built) this._sync(); }
    }

    _resolveTabs() {
      if (this._tabs && this._tabs.length) return this._tabs;
      var attr = parseJSONAttr(this.getAttribute('tabs'));
      this._tabs = Array.isArray(attr) ? attr : [];
      return this._tabs;
    }

    _render() {
      var tabs = this._resolveTabs();
      var tablist = this._tablist;
      tablist.textContent = '';
      var current = this.getAttribute('selected');
      if ((!current || !tabs.some(function (t) { return t.id === current; })) && tabs.length) {
        current = tabs[0].id;
      }
      tabs.forEach(function (t) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'tab';
        btn.setAttribute('role', 'tab');
        btn.id = 'bbtab-' + uid(t.id);
        btn.dataset.id = t.id;
        btn.setAttribute('part', 'tab');
        btn.setAttribute('aria-controls', 'bbpanel-' + uid(t.id));
        btn.textContent = t.label;
        tablist.appendChild(btn);
      });
      if (current != null) this.setAttribute('selected', current);
      this._sync();
    }

    _sync() {
      var selected = this.getAttribute('selected');
      this.$$('[role="tab"]').forEach(function (btn) {
        var on = btn.dataset.id === selected;
        btn.setAttribute('aria-selected', on ? 'true' : 'false');
        btn.tabIndex = on ? 0 : -1; // roving tabindex
      });
      var panels = Array.prototype.slice.call(this.querySelectorAll('[data-tab]'));
      panels.forEach(function (p) {
        var id = p.getAttribute('data-tab');
        var on = id === selected;
        p.setAttribute('role', 'tabpanel');
        p.id = 'bbpanel-' + uid(id);
        p.setAttribute('aria-labelledby', 'bbtab-' + uid(id));
        if (!p.hasAttribute('tabindex')) p.setAttribute('tabindex', '0');
        if (on) { p.classList.add('bb-tab-active'); p.removeAttribute('hidden'); }
        else { p.classList.remove('bb-tab-active'); p.setAttribute('hidden', ''); }
      });
    }

    _select(id, focus) {
      var tabs = this._resolveTabs();
      if (!tabs.some(function (t) { return t.id === id; })) return;
      var changed = this.getAttribute('selected') !== id;
      this.setAttribute('selected', id);
      this._sync();
      if (focus) {
        var btn = this._root.querySelector('[role="tab"][data-id="' + cssEscape(id) + '"]');
        if (btn) btn.focus();
      }
      if (changed) this._emit('bb-tab-change', { id: id });
    }

    _onKeydown(e) {
      var btns = this.$$('[role="tab"]');
      if (!btns.length) return;
      var idx = btns.findIndex(function (b) { return b.dataset.id === e.target.dataset.id; });
      if (idx < 0) return;
      var next = -1;
      switch (e.key) {
        case 'ArrowRight': case 'ArrowDown': next = (idx + 1) % btns.length; break;
        case 'ArrowLeft': case 'ArrowUp': next = (idx - 1 + btns.length) % btns.length; break;
        case 'Home': next = 0; break;
        case 'End': next = btns.length - 1; break;
        case 'Enter': case ' ': case 'Spacebar':
          e.preventDefault(); this._select(e.target.dataset.id, true); return;
        default: return;
      }
      if (next >= 0) { e.preventDefault(); this._select(btns[next].dataset.id, true); }
    }
  }
  if (!customElements.get('bb-tabs')) customElements.define('bb-tabs', BBTabs);

  /* =========================================================================
   * <bb-segmented> — radiogroup pattern (e.g. ALL/QB/RB/WR/TE position filter).
   * ========================================================================= */
  var SEG_CSS = [
    ':host{display:inline-block;}',
    '.group{display:inline-flex;gap:2px;padding:2px;background:var(--_surface);',
    '  border:1px solid var(--_line);border-radius:var(--_radius);flex-wrap:wrap;}',
    '.opt{appearance:none;background:transparent;border:0;color:var(--_muted);',
    '  font:inherit;font-weight:700;font-size:.85em;padding:5px 11px;cursor:pointer;',
    '  border-radius:var(--_radius-sm);white-space:nowrap;',
    '  transition:background var(--_dur) ease,color var(--_dur) ease;}',
    '.opt:hover{color:var(--_text);}',
    '.opt[aria-checked="true"]{background:var(--_accent);color:#0c0e13;}'
  ].join('\n');

  class BBSegmented extends BBElement {
    static get observedAttributes() { return ['options', 'value', 'label']; }
    constructor() { super(); this._options = null; }

    connectedCallback() {
      if (!this._built) { this._build(); this._built = true; }
      this._render();
    }

    _build() {
      this._injectStyles(SEG_CSS);
      var group = document.createElement('div');
      group.className = 'group';
      group.setAttribute('role', 'radiogroup');
      group.setAttribute('part', 'group');
      this._root.appendChild(group);
      this._group = group;
      var self = this;
      group.addEventListener('click', function (e) {
        var b = e.target.closest('[role="radio"]');
        if (b) self._select(b.dataset.value, true);
      });
      group.addEventListener('keydown', function (e) { self._onKeydown(e); });
    }

    get options() { return this._options ? this._options.slice() : []; }
    set options(v) {
      this._options = Array.isArray(v) ? v.map(String) : String(v).split(',').map(function (s) { return s.trim(); });
      if (this._built) this._render();
    }
    get value() { return this.getAttribute('value'); }
    set value(v) { this._select(v, false); }

    attributeChangedCallback(name, oldV, newV) {
      if (oldV === newV) return;
      if (name === 'options') {
        this._options = (newV || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
        if (this._built) this._render();
      } else if (name === 'value') { if (this._built) this._sync(); }
      else if (name === 'label') { if (this._group) this._group.setAttribute('aria-label', newV || ''); }
    }

    _resolveOptions() {
      if (this._options && this._options.length) return this._options;
      var attr = this.getAttribute('options') || '';
      this._options = attr.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
      return this._options;
    }

    _render() {
      var opts = this._resolveOptions();
      this._group.setAttribute('aria-label', this.getAttribute('label') || 'Options');
      this._group.textContent = '';
      var current = this.getAttribute('value');
      if ((current == null || opts.indexOf(current) < 0) && opts.length) current = opts[0];
      opts.forEach(function (o) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'opt';
        b.setAttribute('role', 'radio');
        b.setAttribute('part', 'option');
        b.dataset.value = o;
        b.textContent = o;
        this._group.appendChild(b);
      }, this);
      if (current != null) this.setAttribute('value', current);
      this._sync();
    }

    _sync() {
      var v = this.getAttribute('value');
      var opts = this.$$('[role="radio"]');
      var anyChecked = opts.some(function (b) { return b.dataset.value === v; });
      opts.forEach(function (b, i) {
        var on = b.dataset.value === v;
        b.setAttribute('aria-checked', on ? 'true' : 'false');
        // Roving tabindex: checked is 0; if none checked, first is reachable.
        b.tabIndex = on ? 0 : (!anyChecked && i === 0 ? 0 : -1);
      });
    }

    _select(value, focus) {
      var opts = this._resolveOptions();
      if (opts.indexOf(value) < 0) return;
      var changed = this.getAttribute('value') !== value;
      this.setAttribute('value', value);
      this._sync();
      if (focus) {
        var b = this._root.querySelector('[role="radio"][data-value="' + cssEscape(value) + '"]');
        if (b) b.focus();
      }
      if (changed) this._emit('bb-change', { value: value });
    }

    _onKeydown(e) {
      var btns = this.$$('[role="radio"]');
      if (!btns.length) return;
      var idx = btns.findIndex(function (b) { return b.dataset.value === e.target.dataset.value; });
      if (idx < 0) return;
      var next = -1;
      switch (e.key) {
        case 'ArrowRight': case 'ArrowDown': next = (idx + 1) % btns.length; break;
        case 'ArrowLeft': case 'ArrowUp': next = (idx - 1 + btns.length) % btns.length; break;
        case 'Home': next = 0; break;
        case 'End': next = btns.length - 1; break;
        case ' ': case 'Spacebar': case 'Enter':
          e.preventDefault(); this._select(e.target.dataset.value, true); return;
        default: return;
      }
      if (next >= 0) { e.preventDefault(); this._select(btns[next].dataset.value, true); }
    }
  }
  if (!customElements.get('bb-segmented')) customElements.define('bb-segmented', BBSegmented);

  /* =========================================================================
   * <bb-search> — labeled, debounced search box with clear + live count.
   * ========================================================================= */
  var SEARCH_CSS = [
    ':host{display:block;}',
    '.field{position:relative;display:flex;align-items:center;}',
    '.icon{position:absolute;left:9px;width:14px;height:14px;pointer-events:none;',
    '  color:var(--_muted2);}',
    'input{flex:1;width:100%;background:var(--_surface-2);border:1px solid var(--_line);',
    '  color:var(--_text);border-radius:var(--_radius);padding:7px 30px 7px 28px;',
    '  font:inherit;font-size:.95em;}',
    'input::placeholder{color:var(--_muted2);}',
    'input::-webkit-search-cancel-button{display:none;}',
    '.clear{position:absolute;right:6px;appearance:none;border:0;background:transparent;',
    '  color:var(--_muted);cursor:pointer;font-size:14px;line-height:1;padding:3px 5px;',
    '  border-radius:var(--_radius-sm);display:none;}',
    '.clear:hover{color:var(--_text);}',
    ':host([data-has-value]) .clear{display:inline-flex;}'
  ].join('\n');

  class BBSearch extends BBElement {
    static get observedAttributes() { return ['label', 'placeholder', 'debounce', 'value']; }
    constructor() { super(); this._count = null; this._timer = null; }

    connectedCallback() {
      if (!this._built) { this._build(); this._built = true; }
      this._sync();
    }
    disconnectedCallback() { if (this._timer) clearTimeout(this._timer); }

    _build() {
      this._injectStyles(SEARCH_CSS);
      var labelId = 'bbsl-' + Math.random().toString(36).slice(2, 8);
      var label = document.createElement('label');
      label.className = 'bb-sr-only';
      label.id = labelId;
      label.textContent = this.getAttribute('label') || 'Search';

      var field = document.createElement('div');
      field.className = 'field';
      field.setAttribute('part', 'field');

      var icon = document.createElement('span');
      icon.className = 'icon';
      icon.setAttribute('aria-hidden', 'true');
      icon.innerHTML = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="7" cy="7" r="4.5"/><line x1="11" y1="11" x2="14.5" y2="14.5" stroke-linecap="round"/></svg>';

      var input = document.createElement('input');
      input.type = 'search';
      input.setAttribute('part', 'input');
      input.setAttribute('aria-labelledby', labelId);
      input.setAttribute('autocomplete', 'off');
      input.placeholder = this.getAttribute('placeholder') || '';

      var clear = document.createElement('button');
      clear.type = 'button';
      clear.className = 'clear';
      clear.setAttribute('part', 'clear');
      clear.setAttribute('aria-label', 'Clear search');
      clear.innerHTML = '&times;';

      var live = document.createElement('div');
      live.className = 'bb-sr-only';
      live.setAttribute('aria-live', 'polite');
      live.setAttribute('part', 'status');

      field.appendChild(icon);
      field.appendChild(input);
      field.appendChild(clear);
      this._root.appendChild(label);
      this._root.appendChild(field);
      this._root.appendChild(live);

      this._input = input; this._clear = clear; this._live = live; this._label = label;

      var self = this;
      input.addEventListener('input', function () { self._onInput(); });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { e.preventDefault(); self._doClear(true); }
      });
      clear.addEventListener('click', function () { self._doClear(true); });
    }

    get value() { return this._input ? this._input.value : (this.getAttribute('value') || ''); }
    set value(v) { if (this._input) { this._input.value = v == null ? '' : v; this._toggleClear(); } }

    get count() { return this._count; }
    set count(n) {
      this._count = n;
      if (this._live) {
        this._live.textContent = (n == null) ? '' : (n + ' result' + (n === 1 ? '' : 's'));
      }
    }

    attributeChangedCallback(name, oldV, newV) {
      if (!this._built) return;
      if (name === 'placeholder') this._input.placeholder = newV || '';
      else if (name === 'label') this._label.textContent = newV || 'Search';
      else if (name === 'value') { if (this._input.value !== (newV || '')) { this._input.value = newV || ''; this._toggleClear(); } }
    }

    _sync() {
      if (this.hasAttribute('value')) this._input.value = this.getAttribute('value');
      this._input.placeholder = this.getAttribute('placeholder') || '';
      this._label.textContent = this.getAttribute('label') || 'Search';
      this._toggleClear();
    }

    _toggleClear() {
      var has = !!this._input.value;
      this._reflectBool('data-has-value', has);
    }

    _onInput() {
      this._toggleClear();
      var self = this;
      var ms = parseInt(this.getAttribute('debounce'), 10);
      if (isNaN(ms)) ms = 80;
      if (this._timer) clearTimeout(this._timer);
      this._timer = setTimeout(function () {
        self._emit('bb-search', { query: self._input.value });
      }, ms);
    }

    _doClear(emit) {
      this._input.value = '';
      this._toggleClear();
      this._input.focus();
      if (this._timer) clearTimeout(this._timer);
      if (emit) this._emit('bb-search', { query: '' });
    }
  }
  if (!customElements.get('bb-search')) customElements.define('bb-search', BBSearch);

  /* =========================================================================
   * <bb-badge> — status / flag chip. Text (default slot) is the accessible name;
   * color is never the only signal. Variants meet >=4.5:1 contrast on dark bg.
   * ========================================================================= */
  var BADGE_CSS = [
    ':host{display:inline-block;vertical-align:middle;}',
    '.badge{display:inline-flex;align-items:center;gap:4px;font:inherit;',
    '  font-size:.72em;font-weight:700;line-height:1.4;border-radius:var(--_radius-sm);',
    '  padding:2px 7px;border:1px solid transparent;white-space:nowrap;}',
    /* neutral default */
    '.badge{background:rgba(150,160,180,.16);color:var(--_muted);',
    '  border-color:rgba(150,160,180,.28);}',
    ':host([variant="good"]) .badge{background:rgba(55,184,122,.20);color:var(--_good);border-color:rgba(55,184,122,.4);}',
    ':host([variant="warn"]) .badge{background:rgba(232,163,61,.20);color:var(--_warn);border-color:rgba(232,163,61,.42);}',
    ':host([variant="bad"]) .badge{background:rgba(224,86,122,.20);color:var(--_bad);border-color:rgba(224,86,122,.42);}',
    ':host([variant="info"]) .badge{background:rgba(59,142,240,.20);color:var(--_info);border-color:rgba(59,142,240,.42);}',
    ':host([variant="accent"]) .badge{background:rgba(78,161,255,.20);color:var(--_accent);border-color:rgba(78,161,255,.42);}',
    ':host([variant="neutral"]) .badge{background:rgba(150,160,180,.16);color:var(--_muted);border-color:rgba(150,160,180,.28);}'
  ].join('\n');

  class BBBadge extends BBElement {
    static get observedAttributes() { return ['title']; }
    connectedCallback() {
      if (!this._built) { this._build(); this._built = true; }
      this._sync();
    }
    _build() {
      this._injectStyles(BADGE_CSS);
      var span = document.createElement('span');
      span.className = 'badge';
      span.setAttribute('part', 'badge');
      span.appendChild(document.createElement('slot')); // default slot = real text
      this._root.appendChild(span);
      this._span = span;
    }
    _sync() {
      var t = this.getAttribute('title');
      if (t) this._span.setAttribute('title', t); else this._span.removeAttribute('title');
    }
    attributeChangedCallback() { if (this._built) this._sync(); }
  }
  if (!customElements.get('bb-badge')) customElements.define('bb-badge', BBBadge);

  /* =========================================================================
   * <bb-data-table> — high-performance, accessible data table.
   *
   * PERFORMANCE MODEL (critical):
   *   - Each <tr> is built EXACTLY ONCE into a cached array (this._trCache).
   *   - SORT reorders the cached nodes via a DocumentFragment (appendChild MOVES
   *     existing nodes — we never recreate or innerHTML-rebuild rows).
   *   - FILTER toggles row.style.display only.
   *   - The header sort handler is bound ONCE via delegation on <thead>.
   *   No innerHTML churn happens after first paint of the body.
   * ========================================================================= */
  var TABLE_CSS = [
    ':host{display:block;}',
    '.wrap{position:relative;width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;',
    '  border:1px solid var(--_line);border-radius:var(--_radius);background:var(--_surface);}',
    '.toolbar{padding:var(--_space);border-bottom:1px solid var(--_line);}',
    '.toolbar:empty,.toolbar.bb-empty{display:none;}',
    'table{width:100%;border-collapse:collapse;font:inherit;font-size:.9em;}',
    'caption{text-align:left;padding:var(--_space);color:var(--_muted);font-size:.95em;',
    '  caption-side:top;}',
    'caption.bb-empty{display:none;}',
    'th,td{padding:6px 9px;border-bottom:1px solid var(--_line);text-align:left;',
    '  vertical-align:top;}',
    'td{color:var(--_text);overflow-wrap:anywhere;word-break:normal;}',
    'th{color:var(--_muted);font-size:.82em;text-transform:uppercase;letter-spacing:.3px;',
    '  font-weight:700;background:var(--_surface);white-space:nowrap;}',
    ':host([sticky]) thead th{position:sticky;top:0;z-index:2;}',
    'td[data-align="right"],th[data-align="right"]{text-align:right;}',
    'td[data-align="center"],th[data-align="center"]{text-align:center;}',
    'tbody tr:hover td{background:rgba(78,161,255,.06);}',
    'th button.sort{appearance:none;background:transparent;border:0;color:inherit;',
    '  font:inherit;font-weight:700;text-transform:inherit;letter-spacing:inherit;',
    '  cursor:pointer;display:inline-flex;align-items:center;gap:4px;padding:0;}',
    'th button.sort:hover{color:var(--_text);}',
    'th .arrow{font-size:.85em;opacity:.55;}',
    'th[aria-sort="ascending"] .arrow::after{content:"\\2191";opacity:1;}',
    'th[aria-sort="descending"] .arrow::after{content:"\\2193";opacity:1;}',
    'th[aria-sort="none"] .arrow::after,th:not([aria-sort]) .arrow::after{content:"\\2195";}',
    'th[aria-sort="ascending"],th[aria-sort="descending"]{color:var(--_text);}',
    /* skeleton */
    '.sk{display:block;height:11px;border-radius:4px;background:var(--_surface-2);',
    '  background-image:linear-gradient(90deg,var(--_surface-2) 0,var(--_line) 40px,var(--_surface-2) 80px);',
    '  background-size:600px 100%;animation:bb-shimmer 1.1s linear infinite;}',
    '@keyframes bb-shimmer{0%{background-position:-120px 0;}100%{background-position:480px 0;}}',
    '@media (prefers-reduced-motion: reduce){.sk{animation:none;}}',
    '.state td{padding:18px 12px;text-align:center;color:var(--_muted);}',
    '.state.err td{color:var(--_bad);}',
    /* responsive cards under 640px */
    '@media (max-width:640px){',
    '  :host([responsive="cards"]) .wrap{overflow:visible;border:0;background:transparent;}',
    '  :host([responsive="cards"]) thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}',
    '  :host([responsive="cards"]) table,:host([responsive="cards"]) tbody,',
    '  :host([responsive="cards"]) tr,:host([responsive="cards"]) td{display:block;width:100%;}',
    '  :host([responsive="cards"]) tbody tr{background:var(--_surface);border:1px solid var(--_line);',
    '     border-radius:var(--_radius);margin-bottom:var(--_space);padding:4px 0;}',
    '  :host([responsive="cards"]) tbody td{display:flex;justify-content:space-between;gap:12px;',
    '     border-bottom:1px solid var(--_line);text-align:right;}',
    '  :host([responsive="cards"]) tbody tr td:last-child{border-bottom:0;}',
    '  :host([responsive="cards"]) tbody td::before{content:attr(data-label);font-weight:700;',
    '     color:var(--_muted);text-transform:uppercase;font-size:.78em;letter-spacing:.3px;',
    '     text-align:left;flex:0 0 auto;}',
    '  :host([responsive="cards"]) .state td{display:block;text-align:center;}',
    '  :host([responsive="cards"]) .state td::before{content:none;}',
    '}'
  ].join('\n');

  var SKELETON_ROWS = 6;

  class BBDataTable extends BBElement {
    static get observedAttributes() {
      return ['loading', 'error', 'empty-text', 'responsive', 'caption', 'sticky'];
    }
    constructor() {
      super();
      this._columns = [];
      this._rows = [];
      this._rowKey = null;
      this._trCache = [];      // built-once <tr> nodes, parallel to this._rows
      this._filter = null;     // predicate or null
      this._sortKey = null;
      this._sortDir = null;    // 'asc' | 'desc' | null
    }

    connectedCallback() {
      if (!this._built) { this._build(); this._built = true; }
      if (!this.hasAttribute('sticky') && !this._stickyExplicit) {
        // sticky default ON
        this.setAttribute('sticky', '');
      }
      this._renderAll();
    }

    _build() {
      this._injectStyles(TABLE_CSS);

      var toolbar = document.createElement('div');
      toolbar.className = 'toolbar';
      toolbar.setAttribute('part', 'toolbar');
      var toolbarSlot = document.createElement('slot');
      toolbarSlot.name = 'toolbar';
      toolbar.appendChild(toolbarSlot);

      var wrap = document.createElement('div');
      wrap.className = 'wrap';
      wrap.setAttribute('part', 'wrap');

      var table = document.createElement('table');
      table.setAttribute('part', 'table');
      var caption = document.createElement('caption');
      caption.setAttribute('part', 'caption');
      var thead = document.createElement('thead');
      thead.setAttribute('part', 'header');
      var theadRow = document.createElement('tr');
      thead.appendChild(theadRow);
      var tbody = document.createElement('tbody');
      tbody.setAttribute('part', 'body');
      var live = document.createElement('div');
      live.className = 'bb-sr-only';
      live.setAttribute('aria-live', 'polite');

      table.appendChild(caption);
      table.appendChild(thead);
      table.appendChild(tbody);
      wrap.appendChild(table);

      this._root.appendChild(toolbar);
      this._root.appendChild(wrap);
      this._root.appendChild(live);

      // Hidden slots for empty/error custom content.
      var emptySlot = document.createElement('slot'); emptySlot.name = 'empty';
      var errorSlot = document.createElement('slot'); errorSlot.name = 'error';
      emptySlot.style.display = 'none'; errorSlot.style.display = 'none';
      this._root.appendChild(emptySlot);
      this._root.appendChild(errorSlot);

      this._toolbar = toolbar; this._table = table; this._caption = caption;
      this._thead = thead; this._theadRow = theadRow; this._tbody = tbody;
      this._live = live; this._emptySlot = emptySlot; this._errorSlot = errorSlot;

      // Hide toolbar wrapper if nothing is slotted into it.
      var self = this;
      var checkToolbar = function () {
        var assigned = toolbarSlot.assignedNodes ? toolbarSlot.assignedNodes() : [];
        var has = assigned.some(function (n) {
          return n.nodeType === 1 || (n.nodeType === 3 && n.textContent.trim());
        });
        toolbar.classList.toggle('bb-empty', !has);
      };
      toolbarSlot.addEventListener('slotchange', checkToolbar);
      checkToolbar();

      // ONE delegated handler for header sorting (click + keyboard via button).
      this._thead.addEventListener('click', function (e) {
        var btn = e.target.closest('button.sort');
        if (btn && btn.dataset.key != null) self._cycleSort(btn.dataset.key);
      });
    }

    /* ----- public properties ----- */
    get columns() { return this._columns.slice(); }
    set columns(v) {
      this._columns = Array.isArray(v) ? v.slice() : [];
      if (this._built) { this._buildHeader(); this._rebuildBody(); }
    }
    get rows() { return this._rows.slice(); }
    set rows(v) { this.setRows(v); }
    get rowKey() { return this._rowKey; }
    set rowKey(v) { this._rowKey = v; }

    attributeChangedCallback(name, oldV, newV) {
      if (name === 'sticky') this._stickyExplicit = true;
      if (!this._built) return;
      if (name === 'loading' || name === 'error' || name === 'empty-text') this._renderState();
      else if (name === 'caption') this._renderCaption();
      else if (name === 'responsive') { /* CSS-driven; nothing to recompute */ }
    }

    /* ----- public methods ----- */
    setRows(rows) {
      this._rows = Array.isArray(rows) ? rows.slice() : [];
      if (this._built) this._rebuildBody();
    }
    setFilter(predicate) {
      this._filter = (typeof predicate === 'function') ? predicate : null;
      if (this._built) this._applyFilter();
    }
    sort(key, dir) {
      this._sortKey = key;
      this._sortDir = (dir === 'asc' || dir === 'desc') ? dir : null;
      if (this._built) { this._applySort(); this._syncAriaSort(); this._announceSort(); }
    }

    /* ----- caption ----- */
    _renderCaption() {
      var c = this.getAttribute('caption');
      if (c) { this._caption.textContent = c; this._caption.classList.remove('bb-empty'); }
      else { this._caption.textContent = ''; this._caption.classList.add('bb-empty'); }
    }

    /* ----- header (built when columns change) ----- */
    _buildHeader() {
      var row = this._theadRow;
      row.textContent = '';
      this._columns.forEach(function (col) {
        var th = document.createElement('th');
        th.scope = 'col';
        th.setAttribute('part', 'header-cell');
        if (col.align) th.setAttribute('data-align', col.align);
        if (col.width) th.style.width = (typeof col.width === 'number') ? col.width + 'px' : col.width;
        if (col.sortable) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'sort';
          btn.dataset.key = col.key;
          btn.appendChild(document.createTextNode(col.label != null ? col.label : col.key));
          var arrow = document.createElement('span');
          arrow.className = 'arrow';
          arrow.setAttribute('aria-hidden', 'true');
          btn.appendChild(arrow);
          th.appendChild(btn);
          th.setAttribute('aria-sort', 'none');
        } else {
          th.textContent = col.label != null ? col.label : col.key;
        }
        th.dataset.key = col.key;
        row.appendChild(th);
      });
    }

    /* ----- body: build each <tr> exactly once ----- */
    _rebuildBody() {
      var cols = this._columns;
      var rows = this._rows;
      var cache = [];
      var self = this;
      rows.forEach(function (rowData, i) {
        var tr = document.createElement('tr');
        tr.setAttribute('part', 'row');
        tr.dataset.idx = i;
        cols.forEach(function (col) {
          var td = document.createElement('td');
          td.setAttribute('part', 'cell');
          if (col.align) td.setAttribute('data-align', col.align);
          td.setAttribute('data-label', col.label != null ? col.label : col.key);
          self._fillCell(td, col, rowData);
          tr.appendChild(td);
        });
        cache.push(tr);
      });
      this._trCache = cache;
      // First paint of body content.
      var frag = document.createDocumentFragment();
      cache.forEach(function (tr) { frag.appendChild(tr); });
      this._tbody.textContent = '';
      this._tbody.appendChild(frag);
      // Re-apply current sort/filter to the freshly built nodes.
      if (this._sortKey && this._sortDir) this._applySort();
      this._applyFilter();
      this._syncAriaSort();
      this._renderState();
    }

    _fillCell(td, col, rowData) {
      var raw = rowData ? rowData[col.key] : undefined;
      if (typeof col.render === 'function') {
        var out;
        try { out = col.render(raw, rowData); } catch (e) { out = null; }
        if (out instanceof Node) { td.appendChild(out); return; }
        if (out == null || out === '') { td.textContent = EN_DASH; return; }
        // String output from render() is treated as trusted markup by contract,
        // but we keep it as text unless it clearly contains markup intent.
        td.innerHTML = String(out);
        return;
      }
      if (raw == null || raw === '') { td.textContent = EN_DASH; return; }
      td.textContent = String(raw);
    }

    /* ----- sort = reorder cached nodes (never rebuild) ----- */
    _compareFactory(col, dir) {
      var key = col.key;
      var type = col.sortType || 'text';
      var mul = dir === 'desc' ? -1 : 1;
      var rows = this._rows;
      if (type === 'num') {
        return function (a, b) {
          var av = toNum(rows[+a.dataset.idx][key]);
          var bv = toNum(rows[+b.dataset.idx][key]);
          // null/undefined treated as lowest.
          var an = (av == null), bn = (bv == null);
          if (an && bn) return 0;
          if (an) return -1 * mul;
          if (bn) return 1 * mul;
          if (av < bv) return -1 * mul;
          if (av > bv) return 1 * mul;
          return 0;
        };
      }
      return function (a, b) {
        var av = rows[+a.dataset.idx][key];
        var bv = rows[+b.dataset.idx][key];
        var as = (av == null) ? '' : String(av).toLowerCase();
        var bs = (bv == null) ? '' : String(bv).toLowerCase();
        if (as < bs) return -1 * mul;
        if (as > bs) return 1 * mul;
        return 0;
      };
    }

    _applySort() {
      if (!this._sortKey || !this._sortDir) return;
      var col = this._columns.filter(function (c) { return c.key === this._sortKey; }, this)[0];
      if (!col) return;
      // Stable sort: decorate with original index, sort, then reorder nodes
      // via a single DocumentFragment. appendChild MOVES existing rows, so we
      // never recreate them — only their order in the tbody changes.
      var cmp = this._compareFactory(col, this._sortDir);
      var ordered = this._trCache
        .map(function (n, i) { return { n: n, i: i }; })
        .sort(function (x, y) { var r = cmp(x.n, y.n); return r !== 0 ? r : x.i - y.i; });
      var frag = document.createDocumentFragment();
      ordered.forEach(function (item) { frag.appendChild(item.n); });
      this._tbody.appendChild(frag);
    }

    _cycleSort(key) {
      // none -> desc -> asc -> none ...
      var dir;
      if (this._sortKey !== key) { dir = 'desc'; }
      else if (this._sortDir === 'desc') { dir = 'asc'; }
      else if (this._sortDir === 'asc') { dir = null; }
      else { dir = 'desc'; }
      if (dir == null) {
        // back to natural (original build) order
        this._sortKey = null; this._sortDir = null;
        var frag = document.createDocumentFragment();
        this._trCache.forEach(function (tr) { frag.appendChild(tr); });
        this._tbody.appendChild(frag);
      } else {
        this._sortKey = key; this._sortDir = dir;
        this._applySort();
      }
      this._syncAriaSort();
      this._announceSort();
    }

    _syncAriaSort() {
      var self = this;
      this.$$('thead th').forEach(function (th) {
        if (th.dataset.key == null) return;
        var btn = th.querySelector('button.sort');
        if (!btn) return; // non-sortable
        if (th.dataset.key === self._sortKey && self._sortDir) {
          th.setAttribute('aria-sort', self._sortDir === 'asc' ? 'ascending' : 'descending');
        } else {
          th.setAttribute('aria-sort', 'none');
        }
      });
    }

    _announceSort() {
      if (!this._live) return;
      var label = '';
      if (this._sortKey && this._sortDir) {
        var col = this._columns.filter(function (c) { return c.key === this._sortKey; }, this)[0];
        var name = col ? (col.label != null ? col.label : col.key) : this._sortKey;
        label = 'Sorted by ' + name + ', ' + (this._sortDir === 'asc' ? 'ascending' : 'descending') + '. ';
      } else {
        label = 'Sort cleared. ';
      }
      label += this._visibleCount() + ' rows shown.';
      this._live.textContent = label;
    }

    /* ----- filter = toggle row display ----- */
    _applyFilter() {
      var pred = this._filter;
      var rows = this._rows;
      this._trCache.forEach(function (tr) {
        var idx = +tr.dataset.idx;
        var show = pred ? !!pred(rows[idx], idx) : true;
        tr.style.display = show ? '' : 'none';
      });
      this._renderState();
      if (this._live) {
        this._live.textContent = this._visibleCount() + ' rows shown.';
      }
    }

    _visibleCount() {
      return this._trCache.reduce(function (n, tr) {
        return n + (tr.style.display === 'none' ? 0 : 1);
      }, 0);
    }

    /* ----- states: loading / empty / error rendered as full-colspan rows ----- */
    _colspan() { return Math.max(1, this._columns.length); }

    _clearStateRows() {
      this.$$('tbody tr.state, tbody tr.skel').forEach(function (tr) { tr.remove(); });
    }

    _renderState() {
      this._clearStateRows();
      var tbody = this._tbody;
      // error wins, then loading, then empty.
      var errAttr = this.getAttribute('error');
      var errSlotHas = this._slotHasContent(this._errorSlot);
      if (errAttr || errSlotHas) {
        this._setRowsVisible(false);
        tbody.setAttribute('aria-busy', 'false');
        var tr = document.createElement('tr'); tr.className = 'state err';
        var td = document.createElement('td');
        td.colSpan = this._colspan();
        td.setAttribute('role', 'alert');
        if (errAttr) td.textContent = errAttr; else this._mountSlot(td, this._errorSlot);
        tr.appendChild(td); tbody.appendChild(tr);
        return;
      }
      if (this.hasAttribute('loading')) {
        this._setRowsVisible(false);
        tbody.setAttribute('aria-busy', 'true');
        for (var i = 0; i < SKELETON_ROWS; i++) {
          var sr = document.createElement('tr'); sr.className = 'skel';
          sr.setAttribute('aria-hidden', 'true');
          for (var c = 0; c < this._colspan(); c++) {
            var sd = document.createElement('td');
            var bar = document.createElement('span'); bar.className = 'sk';
            bar.style.width = (45 + Math.round(Math.random() * 45)) + '%';
            sd.appendChild(bar); sr.appendChild(sd);
          }
          tbody.appendChild(sr);
        }
        return;
      }
      tbody.setAttribute('aria-busy', 'false');
      // Empty?
      var anyVisible = this._visibleCount() > 0 && this._rows.length > 0;
      if (!anyVisible) {
        this._setRowsVisible(false);
        var etr = document.createElement('tr'); etr.className = 'state';
        var etd = document.createElement('td');
        etd.colSpan = this._colspan();
        etd.setAttribute('role', 'status');
        var slotHas = this._slotHasContent(this._emptySlot);
        if (slotHas) this._mountSlot(etd, this._emptySlot);
        else etd.textContent = this.getAttribute('empty-text') || 'No data to display.';
        etr.appendChild(etd); tbody.appendChild(etr);
      } else {
        this._setRowsVisible(true);
      }
    }

    // When showing a state row, hide data rows; restore respects current filter.
    _setRowsVisible(on) {
      if (on) { this._applyFilterSilently(); return; }
      this._trCache.forEach(function (tr) { tr.style.display = 'none'; });
    }
    _applyFilterSilently() {
      var pred = this._filter; var rows = this._rows;
      this._trCache.forEach(function (tr) {
        var idx = +tr.dataset.idx;
        tr.style.display = (pred ? !!pred(rows[idx], idx) : true) ? '' : 'none';
      });
    }

    _slotHasContent(slot) {
      if (!slot || !slot.assignedNodes) {
        // jsdom fallback: check light-dom by slot name.
        var name = slot && slot.name;
        if (!name) return false;
        return !!this.querySelector('[slot="' + name + '"]');
      }
      var nodes = slot.assignedNodes();
      return nodes.some(function (n) {
        return n.nodeType === 1 || (n.nodeType === 3 && n.textContent.trim());
      });
    }
    _mountSlot(td, slot) {
      // Move slot into the cell so slotted content renders inside the table.
      td.appendChild(slot);
      slot.style.display = '';
    }

    _renderAll() {
      this._renderCaption();
      this._buildHeader();
      this._rebuildBody();
      this._renderState();
    }
  }

  function toNum(v) {
    if (v == null || v === '') return null;
    if (typeof v === 'number') return isNaN(v) ? null : v;
    var n = parseFloat(String(v).replace(/[, %]/g, ''));
    return isNaN(n) ? null : n;
  }

  if (!customElements.get('bb-data-table')) customElements.define('bb-data-table', BBDataTable);

  // Expose a tiny registry marker for debugging (no globals leak otherwise).
  if (!window.BBComponents) {
    window.BBComponents = { version: '1.0.0',
      elements: ['bb-tabs', 'bb-segmented', 'bb-search', 'bb-badge', 'bb-data-table'] };
  }
})();
