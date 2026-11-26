const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const out='/mnt/project-files/server-settings-mockups/';
const list=(process.argv[2]||'picker:A:light,server:A:light,server:B:light,server:A:dark,sections:B:light').split(',').map(x=>x.split(':'));
for(const [s,v,t] of list)for(const [w,vp] of [['phone',{width:390,height:844}],['desktop',{width:1280,height:s==='inquiry'?1150:860}]]){
 if(s==='sections'&&w==='desktop')continue;
 const p=await b.newPage({viewport:vp,deviceScaleFactor:2});const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});await p.goto(`http://localhost:5199/ss-mock/index.html?s=${s}&v=${v}&t=${t}`);await p.waitForTimeout(1200);await p.screenshot({path:`${out}${s}-${v}-${w}-${t}.png`,fullPage:s!=='inquiry'});if(errs.length)console.log(s,v,w,errs);await p.close()}
await b.close()})();
