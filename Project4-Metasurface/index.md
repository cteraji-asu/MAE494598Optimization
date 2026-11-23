---
layout: null
---
<!doctype html>
<html lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="MAE 494 Project 4: finite-element and adjoint design of a switched, nonlinearly loaded transmission line, with a live 3D comparison of the initial and optimized designs.">
<title>Project 4 · Designing a switched line for 180° reflection · MAE 494</title>
<meta name="color-scheme" content="dark light">
<script>try{var t=localStorage.getItem("p4-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t;}catch(e){}</script>
<link rel="stylesheet" href="site/styles.css">
<script>window.MathJax={tex:{inlineMath:[['\\(','\\)']],displayMath:[['\\[','\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']}};</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-chtml.js"></script>
</head>
<body><div class="shell">
<header class="masthead"><span>MAE 494/598 · Design optimization · Project 4</span><nav aria-label="Page sections"><a href="#viewer">3D comparison</a><a href="#report">Report</a><a href="assets/results.json">Data</a><button id="theme-toggle" class="theme-toggle" type="button" aria-pressed="true" aria-label="Dark mode">◐ Dark</button></nav></header>
<section class="hero"><div><div class="eyebrow">Project 3 extension · PDE-constrained design</div><h1>Make the two switch states reflect 180° apart.</h1><p class="lede">An RF wave enters a transmission line, passes a two-state switch and reflects from a short. Twenty loading cells are optimized with our own finite-element solver and adjoint gradients, so the ON and OFF reflections oppose each other while each keeps at least 80% amplitude and voltage exposure stays bounded.</p></div>
<aside class="technical-note"><strong>Read the 3D view in ten seconds</strong><p>Left: the starting line. Right: the optimized line. The wave enters at the <b>port</b> (left end), passes the <b>switch</b> (orange frame) and reflects from the <b>short</b> (dark plate). Ribbon height and shade show the solved voltage |V|. Block height shows the loading in each cell.</p></aside></section>

<section class="headline" aria-label="Headline results (from assets/results.json)"><div><span>Objective f (lower is better)</span><strong id="h-obj">—</strong><span>initial → optimized</span></div><div><span>ON/OFF phase separation</span><strong id="h-phase">—</strong><span>goal 180°</span></div><div><span>Constraints</span><strong id="h-feas">—</strong><span>initial → optimized</span></div><div><span>Model</span><strong id="h-model">—</strong><span>own P1 FE + adjoint, SLSQP</span></div></section>
<section id="viewer" class="viewer" aria-labelledby="viewer-title">
<div class="section-top"><div><h2 id="viewer-title">Initial versus optimized line</h2><p>Drag to orbit both views together (linked cameras); pinch or scroll to zoom. Hover, tap or press <kbd>[</kbd> <kbd>]</kbd> on a focused view to inspect an element. Arrow keys rotate, <kbd>+</kbd>/<kbd>−</kbd> zoom, <kbd>R</kbd> resets.</p></div><span class="tag">LINKED CAMERAS · COMMON SCALE</span></div>
<div id="load-message" role="status">Loading the saved finite-element results…</div>
<p id="webgl-note" class="warning" role="status" hidden></p>
<div class="toolbar" role="group" aria-label="Viewer controls">
<span class="seg" role="group" aria-label="Switch state"><span class="seg-label">Switch</span><button type="button" data-state="0" aria-pressed="true">ON</button><button type="button" data-state="1" aria-pressed="false">OFF</button></span>
<label>Right view <select id="design-mode"><option value="nonlinear">Optimized, nonlinear model (χ = 0.05)</option><option value="linear">Same design, linear model (χ = 0)</option></select></label>
<span class="spacer"></span><button id="reset-view" type="button" disabled>Reset view</button>
</div>
<div class="views">
<figure class="view" id="view-initial"><figcaption class="view-head"><strong>Initial · uniform loading c = 1</strong><span class="badge" id="initial-status"></span></figcaption><div class="canvas-wrap"><canvas tabindex="0" aria-label="Initial design in 3D. Arrow keys rotate, plus and minus zoom, square brackets step through elements."></canvas><div class="labels" aria-hidden="true"></div><div class="fallback"></div></div><table class="mini"><caption class="sr-only">Initial design: objective and constraints</caption><tbody id="initial-metrics"></tbody></table></figure>
<figure class="view" id="view-final"><figcaption class="view-head"><strong id="final-title">Optimized design, nonlinear model</strong><span class="badge" id="final-status"></span></figcaption><div class="canvas-wrap"><canvas tabindex="0" aria-label="Optimized design in 3D. Arrow keys rotate, plus and minus zoom, square brackets step through elements."></canvas><div class="labels" aria-hidden="true"></div><div class="fallback"></div></div><table class="mini"><caption class="sr-only">Selected design: objective and constraints</caption><tbody id="final-metrics"></tbody></table></figure>
</div>
<div id="tip" class="tip" role="tooltip" hidden></div>
<div class="viewer-foot">
<div class="legend"><strong>Voltage magnitude |V| / V<sub>incident</sub> (dimensionless)</strong><div class="scale" id="scale-bar"></div><div class="scale-labels" id="scale-ticks"></div><small id="scale-note"></small>
<p class="encodings"><b>Encodings, not dimensions:</b> the 1D line is extruded for display; block height ∝ loading c<sub>j</sub> (0.5–2.5); ribbon height and shade ∝ |V|. Dashed lines at the back: the RMS-voltage limit √1.6 (grey) and this design's RMS (teal; dark red with “✗” when over). The limit is on the spatial average, not a local ceiling.</p></div>
<figure class="phasor-box"><svg id="phasor" viewBox="0 0 160 160" role="img" aria-labelledby="phasor-caption"></svg><figcaption><strong>Reflected phasors R<sub>ON</sub>, R<sub>OFF</sub></strong><br><span id="phasor-caption"></span><br><small>Thin grey arrows: initial. Bold arrows: right view. Goal: opposite arrows (180°) outside the dashed 0.8 circle.</small></figcaption></figure>
<div class="changes"><strong>What changed</strong><ul id="what-changed"></ul></div>
</div>
<div class="timeline"><button id="step-back" type="button" aria-label="Previous iterate" disabled>◀</button><button id="play" type="button" aria-pressed="false" disabled>▶ Play optimization</button><button id="step-fwd" type="button" aria-label="Next iterate" disabled>▶︎|</button><label class="range"><span class="sr-only">Optimizer iterate</span><input id="iteration" type="range" min="0" max="0" value="0" disabled></label><output id="iteration-label">Final design</output><small>Replays the recorded SLSQP iterates of the selected run (fields re-solved at each iterate). It is not a time-domain wave animation.</small></div>
<div class="inspect-row"><label>Inspect element <select id="element-select"><option value="">none</option></select></label><div id="inspection" class="inspection" aria-live="polite">Point at, tap, or use [ and ] on a focused view to inspect a finite element.</div></div>
<details class="ledger"><summary>Full objective and constraint ledger (initial vs right view)</summary><div class="table-wrap"><table><thead><tr><th scope="col">Quantity</th><th scope="col">Initial</th><th scope="col">Initial check</th><th scope="col">Selected</th><th scope="col">Selected check</th></tr></thead><tbody id="metrics-body"></tbody></table></div><details class="bound-details"><summary>All 20 cell bounds</summary><div class="table-wrap"><table><thead><tr><th>Cell</th><th>Selected c</th><th>Lower slack</th><th>Upper slack</th><th>Check</th></tr></thead><tbody id="bounds-body"></tbody></table></div></details></details>
<noscript><p class="warning">The 3D viewer needs JavaScript. Every number it shows is also in the report tables below.</p></noscript>
</section>

<main class="report" id="report">
{% include_relative site/report-body.html %}
</main>
<footer class="footer">MAE 494 · Project 4 · <a href="assets/results.json">results.json</a> · <a href="code/run_design.py">design script</a> · <a href="https://github.com/cteraji-asu/MAE494598Optimization/tree/project4-domain-decomposed-design/Project4-Metasurface">source on GitHub</a><br>Synthetic reduced model; no rendered height is a fabricated dimension.</footer>
</div><script>(function(){var b=document.getElementById("theme-toggle"),r=document.documentElement;function sync(){var d=r.dataset.theme!=="light";b.setAttribute("aria-pressed",String(d));b.textContent=d?"◐ Dark":"◑ Light";}sync();b.addEventListener("click",function(){r.dataset.theme=r.dataset.theme==="light"?"dark":"light";try{localStorage.setItem("p4-theme",r.dataset.theme);}catch(e){}sync();document.dispatchEvent(new Event("themechange"));});})();</script>
<script src="site/viewer.js" data-results="assets/results.json" defer></script></body></html>
