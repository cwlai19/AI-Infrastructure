// Screenshot an artifact-style HTML fragment at laptop size, optionally running JS actions first.
// node tools/screenshot.js <page.html> <out.png> 'js1|js2'
const { chromium } = require('playwright');
(async () => {
  const [src, out, actions] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1320, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  const html = '<!doctype html><html><head><meta charset="utf-8"></head><body>' + require('fs').readFileSync(src, 'utf8') + '</body></html>';
  await p.setContent(html, { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
  for (const a of (actions || '').split('|').filter(Boolean)) { await p.evaluate(a); await p.waitForTimeout(200); }
  await p.screenshot({ path: out }); console.log('errors:', JSON.stringify(errs)); await b.close();
})();
