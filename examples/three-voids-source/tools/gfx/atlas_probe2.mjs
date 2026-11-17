import puppeteer from 'puppeteer-core';
const out = process.argv[2];
const b = await puppeteer.launch({executablePath: '/usr/bin/google-chrome', headless: 'new', args: ['--window-size=1920,1080']});
const p = await b.newPage(); await p.setViewport({width:1920,height:1080});
const urls = new Set();
p.on('request', r => { const u = r.url(); if (/blackportal/.test(u)) urls.add(u.replace(/t\.-?\d+\.-?\d+\.webp/,'t.X.Y.webp')); });
const sleep = ms => new Promise(r=>setTimeout(r,ms));
await p.goto('https://2b2tatlas.com/map', {waitUntil:'networkidle2', timeout: 90000}).catch(e=>console.log('goto', e.message));
await sleep(6000);
const btns = [[1876,130,'layers'],[1876,176,'history'],[1876,222,'search2'],[1876,374,'moon']];
for (const [x,y,n] of btns) { await p.mouse.click(x,y); await sleep(2500); await p.screenshot({path: `${out}/ui_${n}.png`}); await p.keyboard.press('Escape'); await sleep(500); }
await p.goto('https://2b2tatlas.com/maps', {waitUntil:'networkidle2', timeout: 60000}).catch(e=>console.log('goto', e.message));
await sleep(4000); await p.screenshot({path: `${out}/ui_maps.png`});
console.log(await p.evaluate(() => [...document.querySelectorAll('a')].map(a=>a.getAttribute('href')+' | '+a.innerText.trim().slice(0,40)).join('\n')));
console.log([...urls].join('\n'));
await b.close();
