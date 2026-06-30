/* SIS DataHub — pull ALL rows past the ~200 cap. CFB or NFL.
 * This site keeps the auth token in memory (not storage) and the API uses wildcard CORS,
 * so we CAPTURE the page's own request (token + exact query body) and replay it bumped.
 *
 * USE:
 *   1) Logged in, on the report you want (NFL Pass Defense, season 2025).
 *   2) Paste this whole file in the console (F12 -> Console), Enter.
 *   3) Run:  sisArm()
 *   4) Trigger ONE report refresh so the page makes its API call:
 *        change the Season dropdown (e.g. 2025 -> 2024 -> back to 2025), or click Search/Apply/Run.
 *      You should see:  captured auth - ready
 *   5) Run:  await sisGo("nfl_pass_defense_2025.json")
 */
(function () {
  const NAMEY = /(take|pagesize|page_size|rowcount|maxrows|max_rows|displaylength|length|limit|top|rows|count)$/i;
  const SKIPY = /(skip|pageindex|pagenumber|start|^page)$/i;
  const isQuery = u => /\/players\/query/i.test(u || '');

  window.sisArm = function () {
    window.__sisCap = null;
    // ---- hook XHR (jQuery $.ajax uses XHR) ----
    const O = XMLHttpRequest.prototype.open, S = XMLHttpRequest.prototype.send, H = XMLHttpRequest.prototype.setRequestHeader;
    XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; this.__h = {}; return O.apply(this, arguments); };
    XMLHttpRequest.prototype.setRequestHeader = function (k, v) { try { this.__h[k] = v; } catch (e) {} return H.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function (b) {
      if (isQuery(this.__u)) {
        window.__sisCap = { url: this.__u, headers: this.__h || {}, body: (typeof b === 'string' ? b : null) };
        const a = this.__h && (this.__h.Authorization || this.__h.authorization);
        console.log('%ccaptured auth - ready', 'color:#5fd08a;font-weight:bold', '| token:', a ? 'yes' : 'NO', '| body:', b ? 'yes' : 'NO', '\nNow run: await sisGo("nfl_pass_defense_2025.json")');
      }
      return S.apply(this, arguments);
    };
    // ---- hook fetch too, just in case ----
    const F = window.fetch;
    window.fetch = function (u, init) {
      try {
        const url = (typeof u === 'string') ? u : (u && u.url);
        if (isQuery(url)) {
          const h = {}; const hh = (init && init.headers) || {};
          if (hh.forEach) hh.forEach((v, k) => h[k] = v); else Object.assign(h, hh);
          window.__sisCap = { url, headers: h, body: (init && typeof init.body === 'string') ? init.body : null };
          console.log('%ccaptured auth (fetch) - ready', 'color:#5fd08a;font-weight:bold');
        }
      } catch (e) {}
      return F.apply(this, arguments);
    };
    console.log('%cArmed.', 'color:#5fd08a;font-weight:bold', 'Now refresh the report ONCE (change the Season dropdown, or click Search/Apply). Watch for "captured auth - ready".');
  };

  function rowsOf(d) { if (Array.isArray(d)) return d; let b = []; if (d && typeof d === 'object') for (const k in d) if (Array.isArray(d[k]) && d[k].length >= b.length) b = d[k]; return b; }
  const sig = r => { try { return r.length + '|' + JSON.stringify(r[0]); } catch (e) { return ''; } };

  window.sisGo = async function (fname) {
    const cap = window.__sisCap;
    if (!cap || !cap.body) { console.error('Not captured yet. Run sisArm(), then refresh the report once (change Season / click Search).'); return; }
    const auth = cap.headers.Authorization || cap.headers.authorization;
    console.log('replaying captured request | token:', auth ? 'yes' : 'NO');
    function body(rows, skip) {
      const parts = cap.body.split('&').map(kv => {
        const name = decodeURIComponent(kv.split('=')[0] || '');
        if (NAMEY.test(name) && !SKIPY.test(name)) return kv.split('=')[0] + '=' + rows;
        if (SKIPY.test(name)) return kv.split('=')[0] + '=' + skip;
        return kv;
      });
      return parts.concat([`Take=${rows}`, `PageSize=${rows}`, `RowCount=${rows}`, `length=${rows}`, `Skip=${skip}`, `start=${skip}`]).join('&');
    }
    const post = async (b) => {
      const r = await fetch(cap.url, { method: 'POST', credentials: 'omit',
        headers: Object.assign({ 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }, auth ? { Authorization: auth } : {}), body: b });
      const t = await r.text(); if (!r.ok) throw new Error(r.status + ' ' + t.slice(0, 150));
      try { return JSON.parse(t); } catch (e) { throw new Error('non-JSON: ' + t.slice(0, 150)); }
    };
    let baseline; try { baseline = rowsOf(await post(cap.body)); } catch (e) { return console.error('replay failed ->', e.message); }
    const N = baseline.length; console.log('plain pull rows:', N);
    let big = []; try { big = rowsOf(await post(body(5000, 0))); } catch (e) { console.warn('bump error:', e.message); }
    console.log('bumped pull rows:', big.length);
    let all = big.length > N ? big : baseline.slice();
    if (big.length <= N) { console.log('paginating...'); let skip = N, last = sig(baseline), g = 0;
      while (g++ < 40) { let pg; try { pg = rowsOf(await post(body(5000, skip))); } catch (e) { break; } if (!pg.length || sig(pg) === last) break; last = sig(pg); all = all.concat(pg); skip += pg.length; await new Promise(x => setTimeout(x, 500)); } }
    const seen = new Set(); all = all.filter(x => { const k = JSON.stringify(x); return seen.has(k) ? false : (seen.add(k), true); });
    window.__sisLast = all; console.log('TOTAL unique rows:', all.length, '(baseline ' + N + ')');
    if (all.length) { const b = new Blob([JSON.stringify(all)], { type: 'application/json' }); const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = fname || 'sis.json'; a.click(); console.log(all.length > N ? 'DOWNLOADED (beat the cap)' : 'DOWNLOADED baseline only'); }
    return all;
  };
  console.log('SIS puller v3 ready. Steps:  sisArm()  ->  refresh the report once  ->  await sisGo("nfl_pass_defense_2025.json")');
})();
