// Executes the real site/viewer.js against assets/results.json in a minimal DOM.
// Checks: per-design metric panels and ledger PASS/FAIL, bound slack arithmetic,
// the WebGL-failure fallback, and that the viewer's numbers agree with the
// generated report table. This is component evidence, not live-browser QA.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'assets/results.json'), 'utf8'));
const report = fs.readFileSync(path.join(root, 'report.md'), 'utf8');

let WEBGL = true;
const gl = new Proxy({}, { get: (_, k) => k === 'getShaderParameter' || k === 'getProgramParameter' ? () => true : String(k).startsWith('create') ? () => ({}) : () => {} });
class El {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.value = ''; this.style = {}; this.dataset = {}; this.className = ''; this.textContent = ''; this.innerHTML = ''; this.hidden = false; this.disabled = false; this.clientWidth = 600; this.clientHeight = 330; this.classList = { add: c => { this.className += ' ' + c; } }; }
  append(...x) { this.children.push(...x); } replaceChildren(...x) { this.children = x; }
  addEventListener() {} setAttribute(k, v) { this[k] = v; } focus() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: 600, height: 330 }; }
  getContext() { return WEBGL ? gl : null; }
  querySelector(sel) { return (this.q ??= {})[sel] ??= new El(sel); }
  get offsetWidth() { return 200; }
}
function run(webgl) {
  WEBGL = webgl; const ids = {};
  const document = {
    currentScript: { dataset: { results: 'assets/results.json' } },
    getElementById: id => ids[id] ??= new El(),
    createElement: t => new El(t),
    querySelectorAll: sel => sel === '[data-state]' ? (ids.__buttons ??= [0, 1].map(s => { const b = new El('button'); b.dataset.state = String(s); return b; })) : [],
    documentElement: { dataset: { theme: 'dark' } }, addEventListener() {}, hidden: false };
  const ctx = { document, window: { devicePixelRatio: 1 }, location: { search: '' }, URLSearchParams, performance: { now: () => 0 },
    fetch: async () => ({ ok: true, json: async () => data }), console, setInterval, clearInterval, Float32Array };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'site/viewer.js'), 'utf8'), ctx);
  return ids;
}
const tol = -1e-7;
const expectChecks = s => [...s.constraints, Math.min(...s.c) - .5, 2.5 - Math.max(...s.c)];

const ids = run(true);
setImmediate(() => {
  try {
    assert.equal(ids['load-message'].hidden, true, 'viewer should finish loading: ' + ids['load-message'].textContent);
    for (const [id, s] of [['initial-metrics', data.initial], ['final-metrics', data.nonlinear.final]]) {
      const rows = ids[id].children; assert.equal(rows.length, 8, id);
      assert.ok(Math.abs(Number(rows[0].children[1].textContent) - s.objective) < 5e-5, id + ' objective');
      expectChecks(s).forEach((g, i) => {
        assert.equal(rows[i + 2].children[2].textContent, g >= tol ? '✓ PASS' : '✗ FAIL', `${id} check ${i}`);
        assert.ok(Math.abs(Number(rows[i + 2].children[1].textContent) - g) < 5e-5 || Math.abs(g) < 1e-3, `${id} value ${i}`);
      });
    }
    const ledger = ids['metrics-body'].children; assert.equal(ledger.length, 9);
    ledger.forEach((r, i) => { assert.equal(r.children.length, 5); if (i >= 3) { const gi = expectChecks(data.initial)[i - 3], gf = expectChecks(data.nonlinear.final)[i - 3]; assert.equal(r.children[2].textContent, gi >= tol ? 'PASS' : '! FAIL'); assert.equal(r.children[4].textContent, gf >= tol ? 'PASS' : '! FAIL'); } });
    for (let j = 0; j < 20; j++) { const row = ids['bounds-body'].children[j], c = data.nonlinear.final.c[j]; assert.ok(Math.abs(Number(row.children[3].textContent) - (2.5 - c)) < 5.1e-5, 'upper slack subtracts loading'); }
    assert.match(ids['initial-status'].textContent, /✗ \d constraint/); assert.match(ids['final-status'].textContent, /✓ all constraints pass/);
    // report agreement: the generated report's results table carries the same values
    const row = name => report.split('\n').find(l => l.startsWith('| ' + name));
    const cells = l => l.split('|').slice(2, -1).map(x => parseFloat(x));
    const obj = cells(row('Objective $f$'));
    assert.ok(Math.abs(obj[0] - data.initial.objective) < 1e-5 && Math.abs(obj[1] - data.nonlinear.final.objective) < 1e-5, 'report objective');
    ['$g_1', '$g_2', '$g_3', '$g_4'].forEach((g, i) => {
      const v = cells(row(g)), vi = Number(ids['initial-metrics'].children[i + 2].children[1].textContent), vf = Number(ids['final-metrics'].children[i + 2].children[1].textContent);
      assert.ok(Math.abs(v[0] - vi) < 6e-5 && Math.abs(v[1] - vf) < 6e-5, 'report/viewer ' + g);
    });
    assert.ok(report.includes(`${data.nonlinear.final.phase_separation_degrees.toFixed(1)}°`), 'report phase');
    for (const name of ['index.md', 'preview.html']) assert.ok(fs.readFileSync(path.join(root, name), 'utf8').includes('Initial check'), name);
    const ids2 = run(false);
    setImmediate(() => {
      try {
        assert.match(ids2['viewer'].className, /no-webgl/); assert.equal(ids2['webgl-note'].hidden, false);
        assert.equal(ids2['final-metrics'].children.length, 8); assert.equal(ids2['metrics-body'].children.length, 9);
        console.log('PASS: viewer panels, ledger, bound slacks, text badges, report agreement and WebGL fallback.');
      } catch (e) { console.error(e); process.exitCode = 1; }
    });
  } catch (e) { console.error(e); process.exitCode = 1; }
});
