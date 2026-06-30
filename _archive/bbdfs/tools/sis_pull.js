/* SIS DataHub CFB — systematic puller (no clicking).
 * Paste into the SIS DataHub CFB tab console while logged in
 * (https://pro.sisdatahub.com/cfb/Leaders/Players), then call sisPull(...).
 *
 * How it works: the leaderboard's table POSTs the serialized query form
 * (form#querybuilder, ~685 fields) to ONE endpoint. We override just the fields we
 * care about, re-serialize, and POST with the OIDC bearer token from session storage.
 * The Totals/Rates/Value sub-tabs are client-side column views of the SAME response,
 * so one pull returns every stat.
 *
 * Endpoint : POST https://api.sportsinfosolutions.com/api/v1/cfb/players/query
 * Auth     : Authorization: Bearer <access_token from the oidc.user session entry>
 * Params   : MetricGroup, TimeFilters.SeasonFrom/To, PassingFilters.Schemes (+ any other filter field)
 */
(function () {
  const $ = window.jQuery;
  const EP = "https://api.sportsinfosolutions.com/api/v1/cfb/players/query";
  const MG = { passing: 1, rushing: 3, receiving: 5, passDef: 9, passRush: 10, runDef: 11 };
  const MAN = [0, 1, 5];      // Cover 0, Cover 1, Man Cover 2
  const ZONE = [2, 3, 4, 6];  // Cover 2, Cover 3, Cover 4, Cover 6

  function token() {
    for (const s of [sessionStorage, localStorage])
      for (let i = 0; i < s.length; i++) {
        try { const v = JSON.parse(s.getItem(s.key(i))); if (v && v.access_token) return v.access_token; } catch (e) {}
      }
    return null;
  }

  // sisPull({metricGroup, seasonFrom, seasonTo, schemes:[...]}) -> Promise<json>
  window.sisPull = function (ov) {
    ov = ov || {};
    return new Promise((res, rej) => {
      const form = $("form#querybuilder");
      const f = { mg: form.find('[name=MetricGroup]'), sf: form.find('[name="TimeFilters.SeasonFrom"]'),
                  st: form.find('[name="TimeFilters.SeasonTo"]'), sch: form.find('[name="PassingFilters.Schemes"]') };
      const old = { mg: f.mg.val(), sf: f.sf.val(), st: f.st.val(), sch: f.sch.map((i, e) => e.checked).get() };
      const restore = () => { f.mg.val(old.mg); f.sf.val(old.sf); f.st.val(old.st); f.sch.each(function (i) { this.checked = old.sch[i]; }); };
      if (ov.metricGroup != null) f.mg.val(String(ov.metricGroup));
      if (ov.seasonFrom != null) f.sf.val(String(ov.seasonFrom));
      if (ov.seasonTo != null) f.st.val(String(ov.seasonTo));
      if (ov.schemes) { const S = ov.schemes.map(String); f.sch.each(function () { this.checked = S.includes(this.value); }); }
      $.ajax({ url: EP, type: "POST", data: form.serialize(), headers: { Authorization: "Bearer " + token() } })
        .done(d => res(d)).fail(x => rej(x.status + " " + (x.responseText || "").slice(0, 120))).always(restore);
    });
  };

  // sisBatch([{name, metricGroup, seasonFrom, seasonTo, schemes}]) -> {name: json}  (polite 600ms gap)
  window.sisBatch = async function (jobs) {
    const out = {};
    for (const j of jobs) { try { out[j.name] = await window.sisPull(j); } catch (e) { out[j.name] = { error: String(e) }; } await new Promise(r => setTimeout(r, 600)); }
    return out;
  };

  // sisDownload(obj, "file.json") -> triggers a browser download (for manual use)
  window.sisDownload = function (obj, fname) {
    const b = new Blob([JSON.stringify(obj)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = fname || "sis.json"; a.click();
  };

  window.SIS = { EP, MG, MAN, ZONE };
  console.log("SIS puller ready. Example:\n  await sisPull({metricGroup:SIS.MG.receiving, seasonFrom:2025, seasonTo:2025, schemes:SIS.MAN})");
})();
