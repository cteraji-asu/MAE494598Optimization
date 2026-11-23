/* Project 4 viewer. No third-party runtime; plain WebGL 1.
   Everything drawn comes from assets/results.json. The line is a 1D finite-
   element model extruded for display: block height encodes the loading c_j,
   ribbon height and colour encode the solved |V|. Complex P1 values are
   interpolated with the element shape functions before taking |V|, and no
   element bridges the voltage jump at the switch. */
'use strict';
(() => {
  const script = document.currentScript, $ = id => document.getElementById(id);
  const fmt = (n, d = 4) => Number.isFinite(n) ? (Math.abs(n) < 1e-3 && n !== 0 ? n.toExponential(2) : n.toFixed(d)) : '—';
  const TOL = -1e-7;
  let data, scaleMax = 2.5, state = 0, frame = 0, mode = 'nonlinear', playing = false, timer = null;
  let selected = null, at = .5, lastPointer = null;
  const camera = { yaw: -.42, pitch: .58, zoom: 1 };
  const views = [];

  // single-hue sequential scale (light → dark teal), never a rainbow
  // Theme palettes. Dark is the page default; the toggle in the header switches.
  const PAL = {
    light: { bg: [.985, .99, .99], lo: [.93, .96, .95], hi: [.02, .33, .40], sub: [[.86, .88, .87], [.74, .77, .77], [.80, .83, .83]], blk: [[.80, .85, .87], [.62, .69, .72], [.70, .76, .79]],
      dark: [[.27, .33, .37], [.18, .23, .26], [.22, .28, .31]], plate: [[.20, .24, .27], [.14, .17, .19], [.17, .21, .23]], arrow: [.15, .2, .23], edge: [.05, .22, .28], base: [.55, .6, .62], limit: [.35, .38, .4], rms: [.05, .35, .4], over: [.6, .12, .05], curtain: [.35, .62] },
    dark: { bg: [.075, .105, .125], lo: [.13, .2, .23], hi: [.55, .95, .92], sub: [[.2, .25, .28], [.15, .19, .21], [.17, .22, .25]], blk: [[.36, .43, .47], [.25, .31, .34], [.3, .36, .4]],
      dark: [[.72, .78, .8], [.55, .61, .64], [.63, .69, .72]], plate: [[.82, .86, .88], [.62, .67, .7], [.72, .77, .79]], arrow: [.85, .9, .92], edge: [.8, .97, .95], base: [.38, .45, .48], limit: [.62, .67, .7], rms: [.45, .9, .88], over: [1, .45, .3], curtain: [.45, .05] } };
  const theme = () => PAL[document.documentElement?.dataset?.theme === 'light' ? 'light' : 'dark'];
  const ramp = t => { t = Math.max(0, Math.min(1, t)); const { lo, hi } = theme(); return lo.map((a, i) => a + (hi[i] - a) * t); };
  const css = c => `rgb(${c.map(v => Math.round(v * 255)).join(',')})`;

  // ------------------------------------------------------------- data helpers
  const snapshotRight = () => mode === 'linear' ? data.linear.final : data.nonlinear.history[frame];
  const finalFrame = () => data.nonlinear.history.length - 1;
  const xp = x => (x / data.config.length - .5) * 3;           // model x (λ) → world
  const yField = v => .42 + .62 * v / scaleMax;                 // |V| → world height
  const limitRms = () => Math.sqrt(data.config.energy_limit);
  function checks(s) {
    const [lo, hi] = data.formulation.bounds, g = s.constraints;
    return [
      { key: 'g1', label: '|R_ON|² − 0.64', tex: 'g₁ ON amplitude', v: g[0] },
      { key: 'g2', label: '|R_OFF|² − 0.64', tex: 'g₂ OFF amplitude', v: g[1] },
      { key: 'g3', label: '1.6 − E_ON', tex: 'g₃ ON mean-square V', v: g[2] },
      { key: 'g4', label: '1.6 − E_OFF', tex: 'g₄ OFF mean-square V', v: g[3] },
      { key: 'lb', label: 'min c − 0.5', tex: 'lower bounds (20)', v: Math.min(...s.c) - lo },
      { key: 'ub', label: '2.5 − max c', tex: 'upper bounds (20)', v: hi - Math.max(...s.c) }];
  }
  const feasible = s => checks(s).every(c => c.v >= TOL);
  function voltageAt(s, e, t) {
    const [a, b] = data.mesh.edges[e], V = s.fields[state].voltage;
    return Math.hypot(V[a][0] * (1 - t) + V[b][0] * t, V[a][1] * (1 - t) + V[b][1] * t);
  }

  // ------------------------------------------------------------- projection
  function project(p, aspect) {
    const [x, y, z] = p, a = camera.yaw, b = camera.pitch;
    const xx = x * Math.cos(a) + z * Math.sin(a), zz = -x * Math.sin(a) + z * Math.cos(a);
    const s = Math.min(.54, 1.1 / aspect) * camera.zoom;          // isotropic: same pixels per unit in x and y
    return [xx * s, (y * Math.cos(b) - zz * Math.sin(b) - .42) * s * aspect, -(y * Math.sin(b) + zz * Math.cos(b)) * .15];
  }

  // ------------------------------------------------------------- WebGL view
  class View {
    constructor(root, side) {
      this.root = root; this.side = side; this.canvas = root.querySelector('canvas'); this.labels = root.querySelector('.labels');
      const g = this.canvas.getContext('webgl', { antialias: true, alpha: false });
      if (!g || new URLSearchParams(location.search).has('nowebgl')) throw Error('WebGL unavailable');
      this.gl = g;
      const sh = (type, src) => { const s = g.createShader(type); g.shaderSource(s, src); g.compileShader(s); if (!g.getShaderParameter(s, g.COMPILE_STATUS)) throw Error(g.getShaderInfoLog(s)); return s; };
      const p = g.createProgram();
      g.attachShader(p, sh(g.VERTEX_SHADER, 'attribute vec3 position;attribute vec3 color;varying vec3 col;void main(){gl_Position=vec4(position,1.0);col=color;}'));
      g.attachShader(p, sh(g.FRAGMENT_SHADER, 'precision mediump float;varying vec3 col;void main(){gl_FragColor=vec4(col,1.0);}'));
      g.linkProgram(p); if (!g.getProgramParameter(p, g.LINK_STATUS)) throw Error(g.getProgramInfoLog(p));
      g.useProgram(p); this.buf = g.createBuffer(); g.bindBuffer(g.ARRAY_BUFFER, this.buf);
      for (const [name, off] of [['position', 0], ['color', 12]]) { const i = g.getAttribLocation(p, name); g.enableVertexAttribArray(i); g.vertexAttribPointer(i, 3, g.FLOAT, false, 24, off); }
      g.enable(g.DEPTH_TEST); this.hit = [];
      this.bind();
    }
    bind() {
      const c = this.canvas; let start = null, moved = false, pinch = null; const pts = new Map();
      c.addEventListener('pointerdown', e => { pts.set(e.pointerId, [e.clientX, e.clientY]); start = [e.clientX, e.clientY]; moved = false; try { c.setPointerCapture(e.pointerId); } catch (_) { /* synthetic or released pointer */ } if (pts.size === 2) { const [p, q] = [...pts.values()]; pinch = Math.hypot(p[0] - q[0], p[1] - q[1]); } });
      c.addEventListener('pointermove', e => {
        if (pts.has(e.pointerId)) pts.set(e.pointerId, [e.clientX, e.clientY]);
        if (pts.size === 2 && pinch) { const [p, q] = [...pts.values()], dd = Math.hypot(p[0] - q[0], p[1] - q[1]); camera.zoom = Math.max(.6, Math.min(2.4, camera.zoom * dd / pinch)); pinch = dd; moved = true; renderAll(); return; }
        if (start && pts.size === 1) {
          const dx = e.clientX - start[0], dy = e.clientY - start[1];
          if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
          if (moved) { camera.yaw += dx * .008; camera.pitch = Math.max(.08, Math.min(1.35, camera.pitch + dy * .008)); start = [e.clientX, e.clientY]; renderAll(); }
        } else if (e.pointerType === 'mouse') this.pick(e, false);
      });
      const end = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null; if (start && !moved) this.pick(e, true); start = null; };
      c.addEventListener('pointerup', end); c.addEventListener('pointercancel', e => { pts.delete(e.pointerId); start = null; });
      c.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse' && !start) hideTip(); });
      c.addEventListener('wheel', e => { e.preventDefault(); camera.zoom = Math.max(.6, Math.min(2.4, camera.zoom * Math.exp(-e.deltaY * .001))); renderAll(); }, { passive: false });
      c.addEventListener('keydown', e => keyControl(e, this));
    }
    pick(e, sticky) {
      const r = this.canvas.getBoundingClientRect(), p = [e.clientX - r.left, e.clientY - r.top];
      let best = Infinity, hit = null;
      for (const h of this.hit) {
        const dx = h.b[0] - h.a[0], dy = h.b[1] - h.a[1], t = Math.max(0, Math.min(1, ((p[0] - h.a[0]) * dx + (p[1] - h.a[1]) * dy) / (dx * dx + dy * dy || 1)));
        const dist = Math.hypot(p[0] - h.a[0] - t * dx, p[1] - h.a[1] - t * dy); if (dist < best) { best = dist; hit = { e: h.e, t }; }
      }
      if (hit && best < (e.pointerType === 'touch' ? 40 : 26)) { selected = hit.e; at = hit.t; lastPointer = { view: this, x: p[0], y: p[1] }; showTip(); renderAll(); }
      else if (sticky) { selected = null; hideTip(); renderAll(); }
    }
    draw(snap) {
      const c = this.canvas, g = this.gl, dpr = Math.min(window.devicePixelRatio || 1, 2), w = c.clientWidth, h = c.clientHeight;
      if (!w || !h) return;
      if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
      const T = theme(); g.clearColor(...T.bg, 1); g.viewport(0, 0, c.width, c.height); g.clear(g.COLOR_BUFFER_BIT | g.DEPTH_BUFFER_BIT);
      const aspect = w / h, tri = [], lines = [];
      const P = p => project(p, aspect);
      const add = (dst, p, col) => dst.push(...P(p), ...col);
      const quad = (a, b, cc, d, col) => { for (const q of [a, b, cc, a, cc, d]) add(tri, q, col); };
      const line = (a, b, col) => { add(lines, a, col); add(lines, b, col); };
      const box = (x0, x1, y0, y1, z0, z1, top, side, front) => {
        quad([x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1], top);
        quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], front);
        quad([x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], front);
        quad([x1, y0, z0], [x1, y0, z1], [x1, y1, z1], [x1, y1, z0], side);
        quad([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], side);
      };
      const n = snap.c.length, Lm = data.config.length, xs = xp(Lm * data.config.switch_cell / n);
      // substrate strip
      box(-1.5, 1.5, -.035, 0, -.3, .3, ...T.sub);
      // loading blocks: height encodes c (labelled as an encoding, not a dimension)
      for (let j = 0; j < n; j++) {
        const x0 = xp(j * Lm / n) + .006, x1 = xp((j + 1) * Lm / n) - .006, y = .03 + .11 * snap.c[j];
        const sel = selected !== null && data.mesh.cell[selected] === j;
        box(x0, x1, 0, y, -.22, .22, ...(sel ? [[.98, .83, .62], [.86, .62, .38], [.92, .72, .50]] : T.blk));
      }
      // port: source block + incident arrow
      box(-1.72, -1.52, 0, .34, -.18, .18, ...T.dark);
      line([-1.5, .8, 0], [-1.15, .8, 0], T.arrow); line([-1.15, .8, 0], [-1.22, .84, 0], T.arrow); line([-1.15, .8, 0], [-1.22, .76, 0], T.arrow);
      // short: grounded plate
      box(1.5, 1.56, -.035, .9, -.32, .32, ...T.plate);
      // switch: frame straddling the gap
      for (const dz of [-.3, .3]) line([xs, 0, dz], [xs, 1.15, dz], [.55, .25, .05]);
      line([xs, 1.15, -.3], [xs, 1.15, .3], [.55, .25, .05]);
      box(xs - .025, xs + .025, 0, .2, -.26, .26, [.85, .55, .25], [.68, .38, .12], [.76, .46, .18]);
      // RMS reference (spatial average!): limit and this design's RMS, dashed along the back edge
      const yl = yField(limitRms()), ye = yField(Math.sqrt(snap.fields[state].energy));
      for (let k = 0; k < 30; k += 2) line([-1.5 + k * .1, yl, -.26], [-1.5 + (k + 1) * .1, yl, -.26], T.limit);
      const over = snap.fields[state].energy > data.config.energy_limit;
      for (let k = 0; k < 60; k += 2) line([-1.5 + k * .05, ye, -.26], [-1.5 + (k + 1) * .05, ye, -.26], over ? T.over : T.rms);
      // field ribbon with curtain, P1-interpolated, no element across the switch jump
      this.hit = []; const px = q => { const r = P(q); return [(r[0] + 1) * w / 2, (1 - r[1]) * h / 2]; };
      data.mesh.edges.forEach(([a, b], e) => {
        const x0 = xp(data.mesh.x[a]), x1 = xp(data.mesh.x[b]);
        this.hit.push({ e, a: px([x0, yField(voltageAt(snap, e, 0)), 0]), b: px([x1, yField(voltageAt(snap, e, 1)), 0]) });
        for (let k = 0; k < 4; k++) {
          const ta = k / 4, tb = (k + 1) / 4, xa = x0 + (x1 - x0) * ta, xb = x0 + (x1 - x0) * tb, va = voltageAt(snap, e, ta), vb = voltageAt(snap, e, tb);
          const ya = yField(va), yb = yField(vb), ca = ramp(va / scaleMax), cb = ramp(vb / scaleMax);
          for (const [q, col] of [[[xa, ya, -.15], ca], [[xb, yb, -.15], cb], [[xb, yb, .15], cb], [[xa, ya, -.15], ca], [[xb, yb, .15], cb], [[xa, ya, .15], ca]]) add(tri, q, col);
          const [cm, cc] = T.curtain, ka = ca.map(v => v * cm + cc), kb = cb.map(v => v * cm + cc);
          for (const [q, col] of [[[xa, .42, .15], ka], [[xb, .42, .15], kb], [[xb, yb, .15], kb], [[xa, .42, .15], ka], [[xb, yb, .15], kb], [[xa, ya, .15], ka]]) add(tri, q, col);
          line([xa, ya, .15], [xb, yb, .15], e === selected ? [.95, .45, .1] : T.edge);
        }
      });
      line([-1.5, .42, .15], [1.5, .42, .15], T.base);
      g.bindBuffer(g.ARRAY_BUFFER, this.buf);
      g.bufferData(g.ARRAY_BUFFER, new Float32Array(tri), g.DYNAMIC_DRAW); g.drawArrays(g.TRIANGLES, 0, tri.length / 6);
      g.bufferData(g.ARRAY_BUFFER, new Float32Array(lines), g.DYNAMIC_DRAW); g.drawArrays(g.LINES, 0, lines.length / 6);
      // HTML labels anchored to 3D points
      const anchors = [
        ['port', [-1.72, .36, 0], 'PORT · wave in, R out'],
        ['switch', [xs, 1.2, 0], `SWITCH · ${state ? 'OFF' : 'ON'}`],
        ['short', [1.53, .96, 0], 'SHORT · V = 0'],
        ['limit', [1.45, yl, -.26], `RMS limit √1.6`]];
      if (over) anchors.push(['over', [.75, ye, -.26], `✗ RMS ${fmt(Math.sqrt(snap.fields[state].energy), 2)} > limit`]);
      this.labels.replaceChildren(...anchors.map(([k, p, text]) => { const s = document.createElement('span'); s.className = 'tag3d ' + k; s.textContent = text; const [u, v] = px(p); s.style.left = u + 'px'; s.style.top = v + 'px'; return s; }));
    }
  }

  // ------------------------------------------------------------- 2D fallback (no WebGL)
  function fallback(root, snap) {
    const box = root.querySelector('.fallback'); if (!box) return;
    const W = 320, H = 150, pts = [];
    data.mesh.edges.forEach(([a, b], e) => { for (const t of [0, 1]) pts.push([(data.mesh.x[t ? b : a] / data.config.length) * W, H - 10 - (H - 30) * voltageAt(snap, e, t) / scaleMax]); });
    box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="|V| along the line"><path d="M0 ${H - 10}H${W}" stroke="#889"/><polyline fill="none" stroke="#0b6e78" stroke-width="2" points="${pts.map(p => p.map(v => v.toFixed(1)).join(',')).join(' ')}"/><text x="2" y="12" font-size="10">|V|/V<tspan baseline-shift="sub">inc</tspan> (max ${fmt(scaleMax, 1)})</text><text x="2" y="${H - 1}" font-size="10">port</text><text x="${W - 2}" y="${H - 1}" font-size="10" text-anchor="end">short</text></svg>`;
  }

  // ------------------------------------------------------------- panels
  function metricsPanel(el, s) {
    const rows = [[`Objective f`, fmt(s.objective), null], [`Phase separation Δφ`, s.phase_separation_degrees.toFixed(1) + '°', null], ...checks(s).map(c => [c.tex, fmt(c.v), c.v >= TOL])];
    el.replaceChildren(...rows.map(([k, v, ok]) => {
      const tr = document.createElement('tr'), a = document.createElement('th'), b = document.createElement('td'), c = document.createElement('td');
      a.scope = 'row'; a.textContent = k; b.textContent = v;
      c.textContent = ok === null ? '' : ok ? '✓ PASS' : '✗ FAIL'; c.className = ok === null ? '' : ok ? 'pass' : 'fail';
      tr.append(a, b, c); return tr;
    }));
  }
  function statusBadge(el, s) { const ok = feasible(s); el.textContent = ok ? '✓ all constraints pass' : `✗ ${checks(s).filter(c => c.v < TOL).length} constraint(s) fail`; el.className = 'badge ' + (ok ? 'pass' : 'fail'); }
  function phasor(svg, a, b) {
    const R = 62, cx = 80, cy = 80, arrow = (r, cls, txt) => {
      const x = cx + R * r[0], y = cy - R * r[1], ang = Math.atan2(cy - y, x - cx);
      const hx = x - 8 * Math.cos(ang - .4), hy = y + 8 * Math.sin(ang - .4), kx = x - 8 * Math.cos(ang + .4), ky = y + 8 * Math.sin(ang + .4);
      return `<g class="${cls}"><line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/><path d="M${x.toFixed(1)} ${y.toFixed(1)}L${hx.toFixed(1)} ${hy.toFixed(1)}L${kx.toFixed(1)} ${ky.toFixed(1)}Z"/><text x="${(cx + (R + 12) * r[0] / Math.hypot(...r)).toFixed(1)}" y="${(cy - (R + 12) * r[1] / Math.hypot(...r) + 4).toFixed(1)}">${txt}</text></g>`;
    };
    svg.innerHTML = `<circle cx="${cx}" cy="${cy}" r="${R}" class="ring"/><circle cx="${cx}" cy="${cy}" r="${R * .8}" class="floor"/><line x1="${cx - R - 4}" y1="${cy}" x2="${cx + R + 4}" y2="${cy}" class="axis"/><line x1="${cx}" y1="${cy - R - 4}" x2="${cx}" y2="${cy + R + 4}" class="axis"/>` +
      arrow(a.fields[0].reflection, 'init on', 'ON') + arrow(a.fields[1].reflection, 'init off', 'OFF') + arrow(b.fields[0].reflection, 'sel on', 'ON') + arrow(b.fields[1].reflection, 'sel off', 'OFF');
  }

  function changeSummary() {
    const fin = data.nonlinear.final, ini = data.initial, n = fin.c.length, k = data.config.switch_cell;
    const before = fin.c.slice(0, k), after = fin.c.slice(k);
    const span = v => { const lo = fmt(Math.min(...v), 2), hi = fmt(Math.max(...v), 2); return lo === hi ? lo : `${lo}–${hi}`; };
    $('what-changed').innerHTML = `<li><strong>Loading:</strong> cells 1–${k} (port → switch) c = 1.00 → ${span(before)}; cells ${k + 1}–${n} (switch → short) c = 1.00 → ${span(after)}.</li>` +
      `<li><strong>Phase separation:</strong> ${ini.phase_separation_degrees.toFixed(1)}° → ${fin.phase_separation_degrees.toFixed(1)}° (goal 180°).</li>` +
      `<li><strong>Mean-square voltage:</strong> ON ${fmt(ini.fields[0].energy, 2)} ✗ → ${fmt(fin.fields[0].energy, 2)} ✓, OFF ${fmt(ini.fields[1].energy, 2)} ✗ → ${fmt(fin.fields[1].energy, 2)} ✓ (limit 1.6).</li>` +
      `<li><strong>Objective:</strong> ${fmt(ini.objective)} → ${fmt(fin.objective)}; all 4 response constraints and 40 bounds pass.</li>`;
  }

  // ------------------------------------------------------------- tooltip / inspection
  function inspectText() {
    if (selected === null) return 'Point at, tap, or use [ and ] on a focused view to inspect a finite element.';
    const [a, b] = data.mesh.edges[selected], j = data.mesh.cell[selected], x = data.mesh.x[a] * (1 - at) + data.mesh.x[b] * at, s = snapshotRight();
    const side = j < data.config.switch_cell ? 'port side of switch' : 'short side of switch';
    return `Element ${selected + 1} of ${data.mesh.edges.length} · cell ${j + 1} (${side}) · x = ${fmt(x, 3)} λ\nInitial: c = ${fmt(data.initial.c[j], 2)}, |V| = ${fmt(voltageAt(data.initial, selected, at), 3)}\n${rightLabel()}: c = ${fmt(s.c[j], 2)}, |V| = ${fmt(voltageAt(s, selected, at), 3)}   (state ${state ? 'OFF' : 'ON'})`;
  }
  function showTip() {
    const t = $('tip'), text = inspectText(); $('inspection').textContent = text;
    if (!lastPointer) { t.hidden = true; return; }
    const r = lastPointer.view.canvas.getBoundingClientRect(), host = $('viewer').getBoundingClientRect();
    t.textContent = text; t.hidden = false;
    const left = Math.min(r.left - host.left + lastPointer.x + 12, host.width - t.offsetWidth - 8);
    t.style.left = Math.max(8, left) + 'px'; t.style.top = (r.top - host.top + lastPointer.y + 14) + 'px';
  }
  function hideTip() { $('tip').hidden = true; }
  function keyControl(e, view) {
    const k = e.key; let used = true;
    if (k === 'ArrowLeft') camera.yaw -= .1; else if (k === 'ArrowRight') camera.yaw += .1;
    else if (k === 'ArrowUp') camera.pitch = Math.min(1.35, camera.pitch + .08); else if (k === 'ArrowDown') camera.pitch = Math.max(.08, camera.pitch - .08);
    else if (k === '+' || k === '=') camera.zoom = Math.min(2.4, camera.zoom + .1); else if (k === '-') camera.zoom = Math.max(.6, camera.zoom - .1);
    else if (k === 'r' || k === 'R') resetCamera();
    else if (k === ']' || k === '[') { const n = data.mesh.edges.length; selected = selected === null ? 0 : (selected + (k === ']' ? 1 : n - 1)) % n; at = .5; const h = view.hit[selected]; lastPointer = { view, x: (h.a[0] + h.b[0]) / 2, y: (h.a[1] + h.b[1]) / 2 }; $('element-select').value = selected; showTip(); }
    else if (k === 'Escape') { selected = null; hideTip(); }
    else used = false;
    if (used) { e.preventDefault(); renderAll(); }
  }
  const resetCamera = () => { camera.yaw = -.42; camera.pitch = .58; camera.zoom = 1; };
  const rightLabel = () => mode === 'linear' ? 'Optimized design, linear model (χ = 0)' : frame === finalFrame() ? 'Optimized design, nonlinear model' : `Nonlinear iterate ${frame} of ${finalFrame()}`;

  // ------------------------------------------------------------- update
  function renderAll() {
    const right = snapshotRight();
    if (views.length) { views[0].draw(data.initial); views[1].draw(right); }
    else { fallback($('view-initial'), data.initial); fallback($('view-final'), right); }
    if (selected !== null) showTip();
  }
  function update() {
    const right = snapshotRight();
    $('final-title').textContent = rightLabel();
    statusBadge($('initial-status'), data.initial); statusBadge($('final-status'), right);
    metricsPanel($('initial-metrics'), data.initial); metricsPanel($('final-metrics'), right);
    phasor($('phasor'), data.initial, right);
    $('phasor-caption').textContent = `Δφ initial ${data.initial.phase_separation_degrees.toFixed(1)}° · ${mode === 'linear' ? 'linear model' : frame === finalFrame() ? 'optimized' : 'iterate ' + frame} ${right.phase_separation_degrees.toFixed(1)}°`;
    $('iteration-label').textContent = mode === 'linear' ? 'Linear-model prediction for the optimized design' : `Iteration ${frame} / ${finalFrame()} · f = ${fmt(right.objective)}`;
    for (const b of document.querySelectorAll('[data-state]')) b.setAttribute('aria-pressed', String(+b.dataset.state === state));
    ledger(right); renderAll();
  }
  function ledger(right) {
    const ini = data.initial, rows = [['Objective f (minimize)', ini.objective, right.objective, null], ['Reflection contrast |R_ON + R_OFF|²', ini.phase_objective, right.phase_objective, null], ['Phase separation Δφ (degrees)', ini.phase_separation_degrees, right.phase_separation_degrees, null]];
    checks(ini).forEach((c, i) => rows.push([`${c.tex}: ${c.label} ≥ 0`, c.v, checks(right)[i].v, true]));
    const body = $('metrics-body'); body.replaceChildren();
    for (const [name, a, b, isC] of rows) {
      const tr = document.createElement('tr');
      for (const [i, v] of [name, fmt(a), isC ? (a >= TOL ? 'PASS' : '! FAIL') : 'reported', fmt(b), isC ? (b >= TOL ? 'PASS' : '! FAIL') : 'reported'].entries()) {
        const td = document.createElement(i ? 'td' : 'th'); if (!i) td.scope = 'row'; td.textContent = v; if (isC && (i === 2 || i === 4)) td.className = v === 'PASS' ? 'pass' : 'fail'; tr.append(td);
      }
      body.append(tr);
    }
    const bb = $('bounds-body'); bb.replaceChildren();
    right.c.forEach((c, j) => { const tr = document.createElement('tr'), lo = c - data.formulation.bounds[0], hi = data.formulation.bounds[1] - c; for (const v of [j + 1, fmt(c), fmt(lo), fmt(hi), Math.min(lo, hi) >= TOL ? 'PASS' : '! FAIL']) { const td = document.createElement('td'); td.textContent = v; tr.append(td); } bb.append(tr); });
  }
  function stop() { playing = false; clearInterval(timer); $('play').textContent = '▶ Play optimization'; $('play').setAttribute('aria-pressed', 'false'); }
  function setFrame(f) { frame = Math.max(0, Math.min(finalFrame(), f)); $('iteration').value = frame; update(); }

  // ------------------------------------------------------------- init
  async function init() {
    const t0 = performance.now();
    try {
      const res = await fetch(script.dataset.results);
      if (!res.ok) throw Error(`Results could not load (HTTP ${res.status}). Serve the page over HTTP next to assets/results.json.`);
      data = await res.json();
      if (!data.mesh?.edges || !data.nonlinear?.history?.length) throw Error('Saved results are incomplete.');
      const snaps = [data.initial, ...data.nonlinear.history, data.nonlinear.final, data.linear.final];
      const vmax = Math.max(...snaps.flatMap(s => s.fields.flatMap(f => f.voltage_magnitude)));
      scaleMax = Math.ceil(vmax * 2) / 2; frame = finalFrame();
      const tickStep = scaleMax / 5; $('scale-ticks').replaceChildren(...[0, 1, 2, 3, 4, 5].map(k => { const s = document.createElement('span'); s.textContent = (k * tickStep).toFixed(1); return s; }));
      const paintScale = () => { $('scale-bar').style.background = `linear-gradient(90deg,${[0, .25, .5, .75, 1].map(t => css(ramp(t))).join(',')})`; };
      paintScale(); document.addEventListener('themechange', () => { paintScale(); renderAll(); });
      $('scale-note').textContent = `Common scale for both designs, both switch states and every iterate (solved maximum ${fmt(vmax, 3)}).`;
      changeSummary();
      { const ini = data.initial, fin = data.nonlinear.final, nf = s => checks(s).filter(c => c.v < TOL).length;
        $('h-obj').textContent = `${fmt(ini.objective, 2)} → ${fmt(fin.objective, 3)}`;
        $('h-phase').textContent = `${ini.phase_separation_degrees.toFixed(1)}° → ${fin.phase_separation_degrees.toFixed(1)}°`;
        $('h-feas').textContent = `${nf(ini) ? '✗ ' + nf(ini) + ' fail' : '✓'} → ${nf(fin) ? '✗ ' + nf(fin) + ' fail' : '✓ all pass'}`;
        $('h-model').textContent = `${data.config.cells} variables · ${data.mesh.elements} elements`; }
      for (let e = 0; e < data.mesh.edges.length; e++) { const o = document.createElement('option'); o.value = e; o.textContent = `${e + 1} (cell ${data.mesh.cell[e] + 1})`; $('element-select').append(o); }
      $('element-select').onchange = e => { selected = e.target.value === '' ? null : +e.target.value; at = .5; lastPointer = null; $('inspection').textContent = inspectText(); renderAll(); };
      try { views.push(new View($('view-initial'), 0), new View($('view-final'), 1)); }
      catch (err) { $('viewer').classList.add('no-webgl'); $('webgl-note').hidden = false; $('webgl-note').textContent = 'WebGL is not available in this browser, so the 3D views are replaced by 2D |V| profiles. All numbers, the phasor dial and the constraint ledger below are unaffected.'; }
      for (const b of document.querySelectorAll('[data-state]')) b.onclick = () => { state = +b.dataset.state; update(); };
      $('design-mode').onchange = e => { stop(); mode = e.target.value; const lin = mode === 'linear'; for (const id of ['play', 'iteration', 'step-back', 'step-fwd']) $(id).disabled = lin; update(); };
      const range = $('iteration'); range.max = finalFrame(); range.value = frame; range.oninput = e => { stop(); setFrame(+e.target.value); };
      $('step-back').onclick = () => { stop(); setFrame(frame - 1); }; $('step-fwd').onclick = () => { stop(); setFrame(frame + 1); };
      $('play').onclick = () => { if (playing) return stop(); if (frame >= finalFrame()) frame = 0; playing = true; $('play').textContent = '❚❚ Pause'; $('play').setAttribute('aria-pressed', 'true'); update(); timer = setInterval(() => { if (frame >= finalFrame()) return stop(); setFrame(frame + 1); }, 500); };
      $('reset-view').onclick = () => { resetCamera(); renderAll(); };
      for (const id of ['play', 'iteration', 'step-back', 'step-fwd', 'reset-view']) $(id).disabled = false;
      document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
      if (window.ResizeObserver) { const ro = new ResizeObserver(() => renderAll()); ro.observe($('view-initial')); ro.observe($('view-final')); }
      $('load-message').hidden = true; update();
      $('viewer').dataset.loadMs = String(Math.round(performance.now() - t0));
    } catch (error) {
      console.error(error); $('load-message').className = 'error'; $('load-message').textContent = error.message;
    }
  }
  init();
})();
