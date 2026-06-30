const fs=require('fs'); const {JSDOM,VirtualConsole}=require('jsdom');
const html=fs.readFileSync('upside_cases.html','utf8');
const errs=[]; const vc=new VirtualConsole(); vc.on('jsdomError',e=>errs.push(e.message.split('\n')[0]));
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc});
setTimeout(()=>{
  const doc=dom.window.document;
  const list=doc.querySelectorAll('#list .prow').length;
  const detail=doc.getElementById('detail').innerHTML;
  const jserr=errs.filter(e=>!/Could not load|Not implemented|css/i.test(e));
  console.log('list rows rendered:',list);
  console.log('detail has narrative:', detail.includes('nar'));
  console.log('detail has "Booms when":', detail.includes('Booms when'));
  console.log('detail has "2025 proof":', detail.includes('2025 proof'));
  console.log('detail has ceiling skills:', detail.includes('Ceiling skills'));
  console.log('detail has split bars:', detail.includes('splits'));
  console.log('js errors:', jserr.length, jserr.slice(0,2).join(' || '));
  // simulate search
  const q=doc.getElementById('q'); q.value='gibbs'; q.dispatchEvent(new dom.window.Event('input'));
  setTimeout(()=>{
    console.log('after search "gibbs" rows:', doc.querySelectorAll('#list .prow').length);
    console.log(jserr.length===0 && list>300 ? 'PASS' : 'FAIL');
    process.exit(jserr.length===0&&list>300?0:1);
  },100);
},700);
