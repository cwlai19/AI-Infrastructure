// Open a standalone HTML file (as a user would) and screenshot it; prints map path count and JS errors.
// node tools/screenshot_file.js <file.html> <out.png>
const { chromium } = require('playwright');
(async () => {
  const [src, out] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1320, height: 1000 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('file://' + src, { waitUntil: 'networkidle' }); await p.waitForTimeout(800);
  console.log('paths:', await p.$$eval('svg path', x => x.length), 'errors:', JSON.stringify(errs));
  await p.screenshot({ path: out }); await b.close();
})();
