/* Load components-demo.html in jsdom with a VirtualConsole; assert 0 errors.
 * Relative ./bb-components.js + ./bb-components.css are inlined so the REAL
 * file contents are exercised (jsdom does not fetch file:// subresources). */
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const dir = __dirname;
let html = fs.readFileSync(path.join(dir, 'components-demo.html'), 'utf-8');
const js  = fs.readFileSync(path.join(dir, 'bb-components.js'), 'utf-8');
const css = fs.readFileSync(path.join(dir, 'bb-components.css'), 'utf-8');

// Inline the external script (keep it a classic inline script).
html = html.split('<script src="./bb-components.js"></script>')
           .join('<script>\n' + js + '\n</script>');
// Inline the stylesheet.
html = html.split('<link rel="stylesheet" href="./bb-components.css">')
           .join('<style>\n' + css + '\n</style>');

const errors = [];
const warnings = [];
const vc = new VirtualConsole();
vc.on('jsdomError', function (e) { errors.push('jsdomError: ' + String((e && e.stack) || e)); });
vc.on('error', function () { errors.push('console.error: ' + Array.prototype.join.call(arguments, ' ')); });
vc.on('warn', function () { warnings.push('console.warn: ' + Array.prototype.join.call(arguments, ' ')); });

let dom;
try {
  dom = new JSDOM(html, {
    runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.sendPrompt = function () {}; }
  });
} catch (e) {
  console.error('CONSTRUCT ERROR:', e);
  process.exit(2);
}

setTimeout(function () {
  const doc = dom.window.document;
  // Sanity: did the demo actually wire up?
  const main = doc.getElementById('mainTable');
  const rows = main && main.shadowRoot ? main.shadowRoot.querySelectorAll('tbody tr:not(.state):not(.skel)').length : -1;
  const tabs = doc.getElementById('demoTabs');
  const tablist = tabs && tabs.shadowRoot ? !!tabs.shadowRoot.querySelector('[role="tablist"]') : false;

  console.log('Demo wired: mainTable rows =', rows, ', tablist present =', tablist);
  console.log('Uncaught/jsdom errors:', errors.length);
  console.log('Console warnings:', warnings.length);
  if (errors.length) { errors.slice(0, 8).forEach(function (e) { console.error('  ' + e); }); }
  if (warnings.length) { warnings.slice(0, 8).forEach(function (e) { console.error('  ' + e); }); }

  let fail = 0;
  function ok(n, c) { if (c) console.log('PASS: ' + n); else { fail++; console.error('FAIL: ' + n); } }
  ok('demo loaded with 0 uncaught errors', errors.length === 0);
  ok('mainTable rendered 13 data rows', rows === 13);
  ok('tabs rendered tablist', tablist === true);
  console.log(fail === 0 ? '\nDEMO CHECK: ALL PASS' : '\nDEMO CHECK: ' + fail + ' FAIL');
  process.exit(fail === 0 ? 0 : 1);
}, 200);
