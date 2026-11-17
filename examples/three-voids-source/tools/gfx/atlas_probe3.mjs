import puppeteer from 'puppeteer-core';
const b = await puppeteer.launch({executablePath: '/usr/bin/google-chrome', headless: 'new', args: ['--window-size=1920,1080']});
const p = await b.newPage(); await p.setViewport({width:1920,height:1080});
const urls = new Set();
p.on('request', r => { const u = r.url(); if (/AtlasTiles|api\//.test(u)) urls.add(u); });
const sleep = ms => new Promise(r=>setTimeout(r,ms));
for (const u of process.argv.slice(3)) {
  await p.goto(u, {waitUntil:'networkidle2', timeout: 60000}).catch(e=>console.log('goto', e.message));
  await sleep(7000); console.log('URL now', p.url(), '|', (await p.title()));
  await p.screenshot({path: `${process.argv[2]}/probe3_${u.replace(/\W+/g,'_').slice(-30)}.png`});
}
console.log([...urls].slice(0,80).join('\n'));
await b.close();
