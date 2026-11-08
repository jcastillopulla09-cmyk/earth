const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 2 });
  await p.route('**/upload.wikimedia.org/**', r => r.fulfill({ path: '/home/user/earth/The_Earth_seen_from_Apollo_17.jpg', contentType: 'image/jpeg' }));
  await p.goto('file:///home/user/earth/index.html');
  await p.waitForTimeout(800);
  await p.evaluate(() => document.querySelectorAll('.hero img').forEach(i => i.style.animation = 'none'));
  await p.screenshot({ path: process.argv[2] });
  await b.close();
})();
