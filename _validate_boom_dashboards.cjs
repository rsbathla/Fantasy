const fs=require('fs'); const {JSDOM,VirtualConsole}=require('jsdom');
const files=[
  ['decision_dashboard.html', ['Boom%','boom_badge'], ['🚀','ceil']],
  ['command_center.html',     ['boommk'],             ['🚀','ceil']],
  ['team_dashboard.html',     ['boom model','boom'],  ['ceil','FA']],
  ['team_scout.html',         ['boom'],               ['ceil','FA']],
];
(async()=>{
 let allok=true;
 for(const [f,srcNeed,domNeed] of files){
   const html=fs.readFileSync(f,'utf8');
   const errs=[]; const vc=new VirtualConsole();
   vc.on('jsdomError',e=>errs.push(e.message.split('\n')[0]));
   const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
     beforeParse(w){w.requestAnimationFrame=cb=>setTimeout(cb,0);}});
   await new Promise(r=>setTimeout(r,700));
   const body=dom.window.document.body.innerHTML;
   const srcHas=srcNeed.some(s=>html.includes(s));
   const domHas=domNeed.some(s=>body.includes(s));
   const jserr=errs.filter(e=>!/Could not load img|Not implemented|css/i.test(e));
   const ok=srcHas&&jserr.length===0;
   allok=allok&&ok;
   console.log(`${ok?'PASS':'FAIL'}  ${f}`);
   console.log(`      source marks: ${srcHas} | dom marks rendered: ${domHas} | js errors: ${jserr.length}`);
   if(jserr.length) console.log('      ERR: '+jserr.slice(0,2).join(' || '));
   dom.window.close();
 }
 console.log(allok?'\nALL DASHBOARDS OK':'\nSOME FAILED');
 process.exit(allok?0:1);
})();
