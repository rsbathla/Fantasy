const fs=require('fs'); const {JSDOM}=require('jsdom');
const {PerfTable,bindSortOnce}=require('./refactor/dashboard_render.optimized.js');
// real data from the live dashboard
const html=fs.readFileSync('command_center.html','utf8');
const D=JSON.parse(html.match(/const D=(\{[\s\S]*?\});\n/)[1]);
const players=D.dfs.players; const SRC=[['environment','Env'],['opportunity','Opp'],['efficiency','Eff'],['matchup','Mtch'],['role','Role']];
const dom=new JSDOM('<!doctype html><table><thead id=h></thead><tbody id=dt></tbody></table>');
const doc=dom.window.document; global.document=doc;
const esc=s=>String(s==null?'':s); const posb=p=>p; const hm=v=>'#0f0';
const tb=doc.getElementById('dt'), thead=doc.getElementById('h');
function now(){return Number(process.hrtime.bigint())/1e6;}

// ---------- CURRENT approach: full innerHTML rebuild + rebind every call ----------
let st={pos:'ALL',sort:'c',dir:-1,q:''};
function renderOLD(){
  let rows=players.filter(p=>(st.pos==='ALL'||p.p===st.pos)&&(!st.q||p.n.toLowerCase().includes(st.q)));
  rows.sort((a,b)=>{let va,vb;if(st.sort==='c'){va=a.c;vb=b.c;}else if(st.sort==='d'){va=a.d;vb=b.d;}else if(st.sort==='pw17'){va=a.pw17;vb=b.pw17;}else{va=(a.src[st.sort]==null?-1:a.src[st.sort]);vb=(b.src[st.sort]==null?-1:b.src[st.sort]);}return(va-vb)*st.dir;});
  let h=`<tr><th class="l" data-k="n">Player</th><th>Pos</th>`;
  SRC.forEach(s=>h+=`<th data-k="${s[0]}">${s[1]}</th>`);
  h+=`<th data-k="c">Cons</th><th data-k="d">Div</th><th data-k="pw17">W17 P</th><th class="l">Profile</th></tr>`;
  rows.forEach(p=>{h+=`<tr><td class="l"><b>${esc(p.n)}</b> <span>${p.t}</span></td><td>${posb(p.p)}</td>`;
    SRC.forEach(s=>{const v=p.src[s[0]];h+=`<td>`+((v==null)?'<span>–</span>':`<span style="background:${hm(v)}">${Math.round(v)}</span>`)+`</td>`;});
    h+=`<td><b>${p.c}</b></td><td>${p.d}</td><td>${p.pw17}%</td><td><span>${esc(p.prof||'')}</span></td></tr>`;});
  tb.innerHTML=h;
  tb.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{});
}

// ---------- OPTIMIZED approach: build once, reorder/toggle ----------
function buildRow(p){const tr=doc.createElement('tr');
  let h=`<td class="l"><b>${esc(p.n)}</b> <span>${p.t}</span></td><td>${posb(p.p)}</td>`;
  SRC.forEach(s=>{const v=p.src[s[0]];h+=`<td>`+((v==null)?'<span>–</span>':`<span>${Math.round(v)}</span>`)+`</td>`;});
  h+=`<td><b>${p.c}</b></td><td>${p.d}</td><td>${p.pw17}%</td><td><span>${esc(p.prof||'')}</span></td>`;
  tr.innerHTML=h; return tr;}
const cmp=(a,b,s)=>{let va,vb;if(s.sort==='c'){va=a.c;vb=b.c;}else if(s.sort==='d'){va=a.d;vb=b.d;}else if(s.sort==='pw17'){va=a.pw17;vb=b.pw17;}else if(s.sort==='n'){return a.n.localeCompare(b.n)*s.dir;}else{va=(a.src[s.sort]==null?-1:a.src[s.sort]);vb=(b.src[s.sort]==null?-1:b.src[s.sort]);}return(va-vb)*s.dir;};
const match=(d,s)=>(s.pos==='ALL'||d.p===s.pos)&&(!s.q||d.n.toLowerCase().includes(s.q));

function bench(label,fn,iter){const t0=now();for(let i=0;i<iter;i++)fn(i);return (now()-t0)/iter;}

// SORT benchmark: 40 sorts, alternating keys
const keys=['c','d','pw17','environment','matchup','role','n'];
let oMs=bench('old-sort',i=>{st.sort=keys[i%keys.length];st.dir=-1;renderOLD();},40);
// optimized: build once (not counted), then 40 sorts
const T=PerfTable(tb,players,{buildRow,cmp,match,state:{pos:'ALL',sort:'c',dir:-1,q:''}});
let nMs=bench('new-sort',i=>{T.state.sort=keys[i%keys.length];T.state.dir=-1;T.sortOnly();},40);

// SEARCH-keystroke benchmark: typing "puka" = 4 progressive renders
function typeOLD(){const q='puka';let ms=0;for(let i=1;i<=q.length;i++){st.q=q.slice(0,i);const t=now();renderOLD();ms+=now()-t;}return ms;}
function typeNEW(){const q='puka';let ms=0;for(let i=1;i<=q.length;i++){T.state.q=q.slice(0,i);const t=now();T.filterOnly();ms+=now()-t;}return ms;}
st.q='';let oType=typeOLD(); st.q='';
let nType=typeNEW();

console.log('rows:',players.length);
console.log(`SORT (avg per sort):   current=${oMs.toFixed(2)}ms   optimized=${nMs.toFixed(2)}ms   speedup=${(oMs/nMs).toFixed(1)}x`);
console.log(`SEARCH "puka" (4 keystrokes total): current=${oType.toFixed(2)}ms   optimized=${nType.toFixed(2)}ms   speedup=${(oType/nType).toFixed(1)}x`);
