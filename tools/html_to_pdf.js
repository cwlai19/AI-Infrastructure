// Print an HTML file to A4 PDF (and optionally a PNG preview).
// node tools/html_to_pdf.js <file.html> <out.pdf> [preview.png]
const { chromium } = require('playwright');
(async () => {
  const [src, out, png] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + src);
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
  if (png) { await page.setViewportSize({ width: 900, height: 1200 }); await page.screenshot({ path: png, fullPage: false }); }
  await browser.close();
})();
