// One backup page per presenter hold. The separate study/rehearsal guides stay intact.
import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');const dest=path.join(root,'presentation/rehearsal-2026-10-30-light');
const {chromium}=await import('playwright');
const manifest=JSON.parse(await fs.readFile(path.join(dest,'beat-manifest.json'),'utf8'));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
let html='<html><head><meta charset="utf-8"><style>@page{size:1280px 720px;margin:0}body{margin:0;background:#FAFAF7}img{width:1280px;height:720px;display:block;break-after:page}img:last-child{break-after:auto}</style></head><body>';
for(const beat of manifest.beats){const bytes=await fs.readFile(path.join(dest,beat.keyframe));html+=`<img src="data:image/png;base64,${bytes.toString('base64')}" alt="${esc(beat.label)}">`;}
html+='</body></html>';await fs.writeFile(path.join(dest,'light-backup.html'),html);
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? {executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE} : {})});
const page=await browser.newPage();const requests=[];await page.route(/^https?:/,route=>{requests.push(route.request().url());return route.abort();});
await page.setContent(html);await page.pdf({path:path.join(dest,'MAE494-Project3-Light-Mode-backup.pdf'),preferCSSPageSize:true,printBackground:true});await browser.close();
if(requests.length)throw Error('Unexpected external request');console.log(JSON.stringify({backup_pages:manifest.beats.length,external_requests:requests,study_guide_modified:false}));
