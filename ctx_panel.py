#!/usr/bin/env python3
"""Shared 4-layer player-context drilldown — the SAME panel command_center uses, packaged so every
other dashboard can embed it with one call. Layers: ① situational splits + real NFL Pro EPA (+YoY),
② 2026 playcaller fit, ③ vacated/opportunity, ④ W15-17 matchup. Data: cc_context.json (keyed by
core.fn name). Wiring is by event-delegation: any element carrying data-ctx-name (and optional
data-ctx-pos) becomes a click-to-expand anchor — works for static rows AND JS-rendered DOM.

Usage in a builder:
    import ctx_panel
    html = html.replace('</head>', ctx_panel.css() + '</head>')
    html = html.replace('</body>', ctx_panel.script() + '</body>')   # injects blob + JS + auto-init
Then add data-ctx-name="<player>" (and data-ctx-pos="<POS>") to each clickable player element.
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))

def context_blob():
    p = os.path.join(HERE, 'cc_context.json')
    d = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    return json.dumps(d, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')

CSS = """<style id="ctxpanel-css">
.ctx-injected>td{padding:0!important;background:var(--ctx-bg,#0e1016)}
.ctxwrap{padding:10px 12px 14px;background:linear-gradient(180deg,rgba(28,32,48,.55),rgba(22,25,34,.96));border-top:1px solid #7aa2ff;border-bottom:2px solid #7aa2ff;box-sizing:border-box}
.ctx-injected.intable .ctxwrap{position:sticky;left:0;width:calc(100vw - 32px);max-width:1148px}
.ctxgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}@media(max-width:920px){.ctxgrid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.ctxgrid{grid-template-columns:1fr}}
.ctxcard{background:#1c2030;border:1px solid #262b3a;border-radius:9px;padding:9px 11px;min-width:0;color:#e7ebf3;font:12px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
.ctxcard h5{margin:0 0 7px;font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;color:#7aa2ff;display:flex;align-items:center;gap:5px;font-weight:700}
.ctxcard h5 .ln{font-size:8px;background:#161922;border:1px solid #262b3a;border-radius:4px;padding:0 4px;color:#697084}
.ctxkv{display:flex;justify-content:space-between;gap:8px;font-size:11.5px;padding:2px 0;border-bottom:1px dashed rgba(150,160,180,.10)}.ctxkv:last-child{border-bottom:0}
.ctxkv .k{color:#9aa3b6}.ctxkv .v{font-weight:600;font-family:ui-monospace,Menlo,Consolas,monospace;text-align:right;color:#e7ebf3}
.ctxkv .v.g{color:#37b87a}.ctxkv .v.b{color:#e0567a}.ctxkv .v.w{color:#e8a33d}
.ctxdial{display:inline-block;font-size:9px;font-weight:700;border-radius:4px;padding:1px 5px;margin:1px}.ctxdial.up{background:rgba(55,184,122,.18);color:#37b87a}.ctxdial.dn{background:rgba(224,86,122,.18);color:#e0567a}.ctxdial.nz{background:rgba(150,160,180,.12);color:#697084}
.ctxyoy{font-size:11px;margin-top:6px;padding-top:6px;border-top:1px solid #262b3a}
.ctxwk{display:flex;justify-content:space-between;font-size:11px;padding:2px 0}.ctxpill{font-size:9px;font-weight:700;border-radius:4px;padding:1px 6px;color:#0b0d12}
.ctxnote{font-size:10.5px;color:#9aa3b6;margin-top:6px;line-height:1.45}
.ctxempty{font-size:10.5px;color:#697084;font-style:italic;padding:4px 0}
.ctxcue{font-size:9.5px;font-weight:700;color:#37b87a;background:rgba(55,184,122,.13);border-radius:4px;padding:1px 6px;margin:1px;display:inline-block}
.ctxchip{display:inline-block;cursor:pointer;font-size:8.5px;font-weight:800;letter-spacing:.3px;color:#7aa2ff;background:rgba(122,162,255,.12);border:1px solid rgba(122,162,255,.32);border-radius:4px;padding:0 5px;margin-left:6px;vertical-align:middle;user-select:none;white-space:nowrap}
.ctxchip:hover{background:rgba(122,162,255,.26);color:#cfe0ff}
.ctxchip::before{content:"\\25B8 "}.ctxchip.ctx-open::before{content:"\\25BE "}.ctxchip.ctx-open{background:rgba(122,162,255,.28);color:#cfe0ff}
</style>"""

JS_CORE = r"""
(function(){
 var CTX = window.CCCTX || {};
 function key(n){return String(n==null?'':n).trim().toLowerCase().replace(/\s+(jr|sr|ii|iii|iv|v)\.?$/,'').replace(/\./g,'').replace(/'/g,'').replace(/-/g,' ').split(/\s+/).filter(Boolean).join(' ');}
 function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
 function f1(v){return v==null?'':(Math.round(v*100)/100).toFixed(2);}
 function f3(v){return v==null?'':(Math.round(v*1000)/1000).toFixed(3);}
 function g(v){return v==null?'':(Math.round(v)) ;}
 function kv(k,v,cls){return (v===''||v==null)?'':'<div class="ctxkv"><span class="k">'+k+'</span><span class="v '+(cls||'')+'">'+v+'</span></div>';}
 function dchip(lab,val){if(val==null)return '';var c=val>0?'up':val<0?'dn':'nz';var a=val>0?'▲':val<0?'▼':'•';return '<span class="ctxdial '+c+'">'+lab+' '+a+'</span>';}
 function mpill(v){if(v==null)return '<span style="color:#697084">–</span>';var h=Math.max(0,Math.min(120,(100-v)*1.2));return '<span class="ctxpill" style="background:hsl('+h+',58%,45%)">'+Math.round(v)+'</span>';}
 function cardSplits(s){
   if(!s)return '';var h='<div class="ctxcard"><h5>① Situational &amp; EPA <span class="ln">real</span></h5>';
   if(s.pos==='WR'||s.pos==='TE'||(s.pos==='RB'&&(s.rec_epa_route!=null||s.yprr_man!=null))){
     if(s.yprr_man!=null||s.yprr_zone!=null){h+=kv('YPRR man / zone',f1(s.yprr_man)+' / '+f1(s.yprr_zone));
       if(s.man_zone_delta!=null)h+=kv('man−zone Δ',(s.man_zone_delta>0?'+':'')+f1(s.man_zone_delta),s.man_zone_delta>0?'g':'b');}
     h+=kv('Rec EPA/route',f3(s.rec_epa_route),s.rec_epa_route>0?'g':s.rec_epa_route<0?'b':'');
     h+=kv('Avg separation',f1(s.rec_separation),s.rec_separation>=3?'g':'');
     h+=kv('YACOE/rec',f1(s.rec_yacoe),s.rec_yacoe>0?'g':'');
     h+=kv('CROE',f3(s.rec_croe),s.rec_croe>0?'g':s.rec_croe<0?'b':'');
     h+=kv('aDOT',f1(s.adot25));h+=kv('man route %',f1(s.man_route_sh));
   }
   if(s.pos==='QB'){
     h+=kv('EPA/dropback',f3(s.qb_epa_db),s.qb_epa_db>0.1?'g':s.qb_epa_db<0?'b':'');
     h+=kv('CPOE',f1(s.qb_cpoe),s.qb_cpoe>0?'g':s.qb_cpoe<0?'b':'');
     h+=kv('Time to throw',f1(s.qb_ttt));
     h+=kv('Pressure% faced',f1(s.qb_pressure_rate),s.qb_pressure_rate>35?'b':s.qb_pressure_rate<28?'g':'w');
     h+=kv('Sack% (FP)',f1(s.sack_pct25));h+=kv('aNY/A',f1(s.qb_anya));h+=kv('deep ball %',f1(s.deep_ball_sh));
     h+='<div class="ctxnote">EPA/DB is passing only — understates rushing QBs.</div>';
   }
   if(s.pos==='RB'){
     h+=kv('Rush EPA/att',f3(s.rush_epa_att),s.rush_epa_att>-0.02?'g':s.rush_epa_att<-0.12?'b':'');
     h+=kv('RYOE/att',f1(s.ryoe_att),s.ryoe_att>0.5?'g':s.ryoe_att<0?'b':'');
     h+=kv('zone / gap succ',(s.zone_succ!=null||s.gap_succ!=null)?(f1(s.zone_succ)+' / '+f1(s.gap_succ)):'');
     h+=kv('zone run %',f1(s.zone_run_sh));h+=kv('stuff %',f1(s.stuff_pct),s.stuff_pct>20?'b':'');
     h+=kv('top speed (20+)',s.rb_topspeed==null?'':Math.round(s.rb_topspeed));
     if(s.rb_rec_ypg!=null)h+=kv('rec yds/g',f1(s.rb_rec_ypg));
   }
   if(s.yoy){var d=s.yoy.delta;h+='<div class="ctxyoy"><span class="k" style="color:#697084">'+esc(s.yoy.label)+' — trajectory</span><div class="ctxkv" style="border:0"><span class="k">2024 → 2025</span><span class="v">'+f3(s.yoy.y2024)+' → '+f3(s.yoy.y2025)+' <span class="'+(d>0?'g':d<0?'b':'')+'">'+(d==null?'':(d>0?'▲+':'▼')+f3(Math.abs(d)))+'</span></span></div></div>';}
   return h+'</div>';
 }
 function cardScheme(sc){
   var h='<div class="ctxcard"><h5>② Playcaller fit <span class="ln">2026</span></h5>';
   if(!sc)return h+'<div class="ctxempty">Continuity team — no 2026 play-caller change tracked.</div></div>';
   h+='<div style="font-size:11.5px;font-weight:600;margin-bottom:5px">'+esc(sc.playcaller||'')+'</div>';
   var d=sc.dials||{};
   h+='<div style="margin:3px 0 5px">'+dchip('Mot',d.motion)+dchip('Vert',d.vertical)+dchip('Pass',d.passcatch)+dchip('Scr',d.scramble)+'</div>';
   if(sc.fit&&sc.fit.length)h+='<div style="margin:4px 0">'+sc.fit.map(function(c){return '<span class="ctxcue">'+esc(c)+'</span>';}).join('')+'</div>';
   if(sc.note)h+='<div class="ctxnote">'+esc(sc.note)+'</div>';
   return h+'</div>';
 }
 function cardOpp(o){
   var h='<div class="ctxcard"><h5>③ Opportunity / vacated</h5>';
   if(!o)return h+'<div class="ctxempty">no opportunity data</div></div>';
   h+=kv('route %',o.route_pct==null?'':f1(o.route_pct));
   h+=kv('alignment',o.align?esc(o.align)+(o.align_pct!=null?' ('+f1(o.align_pct)+'%)':''):'');
   h+=kv('target share',o.tgt_share==null?'':f1(o.tgt_share)+'%');
   h+=kv('team vacated tgt',o.team_vacated_tgt==null?'':f1(o.team_vacated_tgt)+'%',o.team_vacated_tgt>40?'g':'');
   if(o.self_moves&&o.self_moves.length){h+='<div class="ctxnote">';
     o.self_moves.forEach(function(m){var t=(m.tgts?m.tgts+' tgt':'')+(m.rush?((m.tgts?' / ':'')+m.rush+' rush'):'');
       h+='<div>'+(m.dir==='added'?'➕ brings':'➖ vacates')+' <b>'+t+'</b>'+(m.from&&m.to?(' ('+esc(m.from)+'→'+esc(m.to)+')'):'')+'</div>';});
     h+='</div>';}
   return h+'</div>';
 }
 function cardMatchup(m){
   var h='<div class="ctxcard"><h5>④ Playoff matchup <span class="ln">W15-17</span></h5>';
   if(!m||!m.weeks||!m.weeks.length)return h+'<div class="ctxempty">no W15-17 matchup</div></div>';
   var lab=m.metric==='run'?'Run-D':'Coverage';
   m.weeks.forEach(function(w){h+='<div class="ctxwk"><span class="k">W'+w.wk+' @ '+esc(w.opp)+'</span>'+mpill(w.val)+'</div>';});
   if(m.avg!=null){var soft=m.avg<40,tough=m.avg>65;
     h+='<div class="ctxkv" style="margin-top:4px;border-top:1px solid #262b3a;padding-top:5px"><span class="k">avg '+lab+' pctl</span><span class="v '+(soft?'g':tough?'b':'w')+'">'+m.avg+' '+(soft?'soft':tough?'tough':'avg')+'</span></div>';}
   h+='<div class="ctxnote">lower percentile = softer matchup (greener). Move-aware 2026 D.</div>';
   return h+'</div>';
 }
 function panelHTML(name,pos){
   var c=CTX[key(name)];
   if(!c)return '<div class="ctxwrap"><div class="ctxempty" style="padding:8px">No extended context for '+esc(name)+'.</div></div>';
   return '<div class="ctxwrap"><div class="ctxgrid">'+cardSplits(c.splits)+cardScheme(c.scheme)+cardOpp(c.opp)+cardMatchup(c.matchup)+'</div></div>';
 }
 function colcount(tr){var n=0;[].forEach.call(tr.children,function(td){n+=(td.colSpan||1);});return n||99;}
 function toggle(anchor){
   var name=anchor.getAttribute('data-ctx-name'), pos=anchor.getAttribute('data-ctx-pos')||(CTX[key(name)]&&CTX[key(name)].pos)||'';
   var row=anchor.closest('tr');
   if(row){
     var nx=row.nextElementSibling;
     if(nx&&nx.classList.contains('ctx-injected')){nx.parentNode.removeChild(nx);anchor.classList.remove('ctx-open');return;}
     var tr=document.createElement('tr');tr.className='ctx-injected intable';
     var td=document.createElement('td');td.colSpan=colcount(row);td.innerHTML=panelHTML(name,pos);
     tr.appendChild(td);row.parentNode.insertBefore(tr,row.nextSibling);anchor.classList.add('ctx-open');
   } else {
     var host=anchor.closest('[data-ctx-host]')||anchor;
     var sib=host.nextElementSibling;
     if(sib&&sib.classList.contains('ctx-injected')){sib.parentNode.removeChild(sib);anchor.classList.remove('ctx-open');return;}
     var div=document.createElement('div');div.className='ctx-injected';div.innerHTML=panelHTML(name,pos);
     host.parentNode.insertBefore(div,host.nextSibling);anchor.classList.add('ctx-open');
   }
 }
 document.addEventListener('click',function(e){
   if(e.target.closest('a,button,input,select,textarea,label,th'))return;
   var anchor=e.target.closest('[data-ctx-name]');
   if(!anchor)return;
   e.stopPropagation();
   toggle(anchor);
 },true);
 window.CTXPANEL={html:panelHTML,key:key,count:Object.keys(CTX).length};
 try{var n=Object.keys(CTX).length;var tag=document.getElementById('ctx-count');if(tag)tag.textContent=n;}catch(_){}
})();
"""

def css():
    return CSS

def script():
    return '<script id="ctxpanel-data">window.CCCTX=' + context_blob() + ';</script>\n<script id="ctxpanel-js">' + JS_CORE + '</script>'

def inject(html):
    """Inject CSS into <head> and the data+JS before </body>. Idempotent (skips if already present)."""
    if 'ctxpanel-css' not in html:
        if '</head>' in html:
            html = html.replace('</head>', css() + '\n</head>', 1)
        else:
            html = css() + html
    if 'ctxpanel-js' not in html:
        if '</body>' in html:
            html = html.replace('</body>', script() + '\n</body>', 1)
        else:
            html = html + script()
    return html

if __name__ == '__main__':
    print('cc_context players:', json.loads(context_blob().replace('\\u003c', '<')) and len(json.loads(context_blob().replace('\\u003c','<'))))
    print('css bytes:', len(css()), '| script bytes:', len(script()))
