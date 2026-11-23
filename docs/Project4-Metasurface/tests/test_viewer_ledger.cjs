// Executes the actual viewer with a minimal DOM/WebGL fixture; not live-browser QA.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'assets/results.json'),'utf8'));
class Element { constructor(){this.children=[];this.value='nonlinear';this.style={};this.clientWidth=600;this.clientHeight=350;this.parentElement=this;this.textContent='';} append(x){this.children.push(x)} replaceChildren(){this.children=[]} get lastChild(){return this.children.at(-1)} addEventListener(){} getContext(){return gl} }
const gl=new Proxy({}, {get:(_,k)=>k==='getShaderParameter'||k==='getProgramParameter'?()=>true:k.startsWith('create')?()=>({}):()=>{}});
const elements={}; const document={currentScript:{dataset:{results:'assets/results.json'}},getElementById:id=>elements[id]??=new Element(),createElement:()=>new Element(),addEventListener(){}};
const context={document,fetch:async()=>({ok:true,json:async()=>data}),console,devicePixelRatio:1,ResizeObserver:class{observe(){}},setInterval,clearInterval,Float32Array};
vm.runInNewContext(fs.readFileSync(path.join(root,'site/viewer.js'),'utf8'),context);
setImmediate(()=>{try{
const rows=elements['metrics-body'].children;
assert.equal(rows.length,9);
for(let i=0;i<rows.length;i++){
 assert.equal(rows[i].children.length,5,'both designs need check columns');
 const initial=rows[i].children[2].textContent, selected=rows[i].children[4].textContent;
 if(i<3){assert.equal(initial,'reported');assert.equal(selected,'reported');continue;}
 const ci=[...data.initial.constraints,Math.min(...data.initial.c)-.5,2.5-Math.max(...data.initial.c)][i-3];
 const cf=[...data.nonlinear.final.constraints,Math.min(...data.nonlinear.final.c)-.5,2.5-Math.max(...data.nonlinear.final.c)][i-3];
 assert.equal(initial,ci>=-1e-7?'PASS':'! FAIL'); assert.equal(selected,cf>=-1e-7?'PASS':'! FAIL');
}
for(let j=0;j<20;j++){const row=elements['bounds-body'].children[j];const c=data.nonlinear.final.c[j];assert.ok(Math.abs(Number(row.children[3].textContent)-(2.5-c))<5.1e-5,'upper slack must subtract cell loading, within displayed rounding');}
for(const name of ['index.md','site/index.html','preview.html'])assert.ok(fs.readFileSync(path.join(root,name),'utf8').includes('Initial check'),name);
console.log('PASS: 9 real viewer ledger rows, both designs checked; all 3 page headers match.');
}catch(e){console.error(e);process.exitCode=1;}});
