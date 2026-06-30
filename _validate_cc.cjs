// Headless validation of command_center.html via jsdom: load the page, let the inline
// script build all tables, assert the embedded __DATA__ counts + 0 uncaught errors.
const fs=require('fs'); const path=require('path'); const {JSDOM}=require('jsdom');
const file=path.join(__dirname,'command_center.html');
const html=fs.readFileSync(file,'utf-8');
const errors=[];
const vc=new (require('jsdom').VirtualConsole)();
vc.on('jsdomError',e=>errors.push(String(e&&e.stack||e)));
let dom;
try{
  dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
    beforeParse(w){ w.sendPrompt=()=>{}; }});
}catch(e){ console.error('JSDOM construct error:',e); process.exit(2); }
const w=dom.window, doc=w.document;
// 1) embedded __DATA__ must JSON.parse from the script source
const scripts=[...doc.querySelectorAll('script')].map(s=>s.textContent).join('\n');
const m=scripts.match(/const D=(\{[\s\S]*?\});\n/);
let D=null, parseOK=false;
if(m){ try{ D=JSON.parse(m[1]); parseOK=true; }catch(e){ errors.push('JSON.parse(__DATA__) failed: '+e); } }
else { errors.push('could not locate const D={...} payload'); }
// give the inline render functions a tick
setTimeout(()=>{
  const r={};
  r.fusion = D? D.fusion.length : -1;
  r.dfs    = D? D.dfs.players.length : -1;
  r.stacks = D? D.stacks.length : -1;
  r.personnel = D? Object.keys(D.personnel).length : -1;
  r.defense = D? D.defense.length : -1;
  // DOM render assertions: tables populated with rows
  const ft=doc.querySelectorAll('#ft tr').length;
  const dt=doc.querySelectorAll('#dt tr').length;
  const dft=doc.querySelectorAll('#dft tr').length;
  const persCards=doc.querySelectorAll('#perslist .card').length;
  const tabs=doc.querySelectorAll('.tabs .tab').length;
  console.log(JSON.stringify({counts:r,dom:{fusion_rows:ft,dfs_rows:dt,defense_rows:dft,pers_cards:persCards,tabs},
    json_parse_ok:parseOK,uncaught_errors:errors.length,errors:errors.slice(0,5)},null,2));
  // assertions (approx)
  const near=(a,b,tol)=>Math.abs(a-b)<=tol;
  const checks=[
    ['fusion≈371', near(r.fusion,371,5)],
    ['dfs≈371', near(r.dfs,371,5)],
    ['stacks≈15', near(r.stacks,15,3)],
    ['personnel≈32', near(r.personnel,32,1)],
    ['defense≈32', near(r.defense,32,0)],
    ['json_parse_ok', parseOK],
    ['0_uncaught_errors', errors.length===0],
    ['defense_tab_rendered', dft>=32],
    ['4_tabs', tabs===4],
    ['fusion_table_rendered', ft>=300],
    ['dfs_table_rendered', dt>=300],
  ];
  let fail=0;
  checks.forEach(([n,ok])=>{ if(!ok){fail++; console.error('FAIL:',n);} else console.log('PASS:',n);});
  console.log(fail===0?'\nVALIDATION: ALL PASS':('\nVALIDATION: '+fail+' FAILURES'));
  process.exit(fail===0?0:1);
},300);
