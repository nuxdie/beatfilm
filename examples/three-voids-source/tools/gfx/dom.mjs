// Headless-Chrome frame source for the DOM-based scenes. Never opens a window.
//   node dom.mjs frames <ID> <dur> <fps> <w> <h> '<params json>'      -> PNG stream on stdout
//   node dom.mjs plate  <ID> <out.png> <w> <h> <dsf> '<params json>'  -> one PNG + <out>.json (element rects)
import puppeteer from 'puppeteer-core';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const [mode, id, ...rest] = process.argv.slice(2);

async function open(w, h, dsf) {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome', headless: 'new',
    args: ['--headless=new', '--hide-scrollbars', '--disable-gpu', '--force-color-profile=srgb',
      '--font-render-hinting=none', '--disable-lcd-text', '--allow-file-access-from-files',
      '--host-resolver-rules=MAP * ~NOTFOUND', '--no-first-run', '--mute-audio'],
    defaultViewport: { width: w, height: h, deviceScaleFactor: dsf },
  });
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.join(here, 'scenes.html')).href, { waitUntil: 'load' });
  return { browser, page };
}
const write = (buf) => new Promise((res, rej) => process.stdout.write(buf, (e) => e ? rej(e) : res()));

if (mode === 'frames') {
  const [dur, fps, w, h, pj] = rest;
  const { browser, page } = await open(+w, +h, 1);
  await page.evaluate((i, d, p) => window.scene.setup(i, d, p), id, +dur, JSON.parse(pj || '{}'));
  const n = Math.round(+dur * +fps);
  let prev = null, buf = null, shots = 0;
  for (let i = 0; i < n; i++) {
    const key = await page.evaluate((t) => window.scene.frame(t), i / +fps);
    if (key !== prev || !buf) {
      buf = await page.screenshot({ type: 'png', optimizeForSpeed: true, captureBeyondViewport: false });
      prev = key; shots++;
    }
    await write(buf);
  }
  process.stderr.write(`[dom] ${id}: ${n} frames, ${shots} unique\n`);
  await browser.close();
} else if (mode === 'plate') {
  const [out, w, h, dsf, pj] = rest;
  const { browser, page } = await open(+w, +h, +dsf);
  const pp = JSON.parse(pj || '{}');
  await page.evaluate((i, p) => window.scene.setup(i, p._dur || 1, p), id, pp);
  await page.evaluate((t) => window.scene.frame(t), pp._t || 0);
  fs.writeFileSync(out, await page.screenshot({ type: 'png', captureBeyondViewport: false }));
  const rects = await page.evaluate(() => window.scene.rects(['#bubble', '#label', '#reply', '#p1', '#p2', '#p3', '#p4']));
  fs.writeFileSync(out + '.json', JSON.stringify(rects));
  await browser.close();
} else { console.error('usage: dom.mjs frames|plate ...'); process.exit(2); }
