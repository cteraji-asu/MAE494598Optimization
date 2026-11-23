# Viewer QA

Local URL: http://127.0.0.1:8765/Project4-Metasurface/site/

Tested in Chrome on 2026-11-10, with the generated `assets/results.json`.

- JavaScript syntax: `node --check Project4-Metasurface/site/viewer.js` passes.
- Desktop screenshot inspected and saved as `qa/desktop.png`.
- Phone viewport 390 × 844 inspected and saved as `qa/mobile.png`. Document width 375 px with 390 px viewport, no horizontal page overflow. Temporary viewport override reset afterward.
- ON and OFF switch states update field ribbons, reflection values and mean-square voltage values.
- OFF field has two separate traces at the duplicated switch coordinate. No mesh edge crosses the interface; the viewer uses the supplied mesh edges exclusively.
- Element selection tested at element 49, the first element on the switch's right side. Selector updates location, loading cell, capacitance and interpolated voltage in both designs.
- Playback advances recorded nonlinear iterates, confirmed from iteration 0 to 12. Pause stops it. Selecting the linear design disables nonlinear playback. It is labeled as optimization history, not physical time.
- Initial and selected constraint statuses use explicit text and symbols, not color alone. Mean-square voltage is a global average and is not depicted as a local over-limit color.
- Shared color scale includes both states and every stored nonlinear iterate. Complex real/imaginary P1 interpolation precedes magnitude. The shader interpolates the sampled sequential colors over six subdivisions per element.
- Full selected bound ledger includes both lower and upper slacks for each of 20 cells.
- Browser console inspection after final reload and interactions returned no errors or warnings.
- Screenshot critique corrected horizontal clipping and the orthographic depth sign before final captures.

Not verified here: GitHub Pages publication, Jekyll's deployed build, remote load time, physical phone touch input, hardware interpretation, numerical validity of the solver. The report generator and numerical checks have separate owners.

## Implementation notes

`index.md` is a complete HTML shell with Jekyll `layout: null`. It captures `report.md` with `include_relative`, then passes that capture through `markdownify`. This avoids relying on nested HTML Markdown parsing. Asset URLs are local to Project4-Metasurface. `site/index.html` is the standalone interactive preview; its report link points to the Jekyll page.

The viewer has no third-party JavaScript or CDN dependency. Canvas input shares one camera object across both views. Cell heights encode capacitance and the ribbon height encodes normalized voltage; neither height is a fabricated dimension.

## Full generated report preview QA

Retested `http://127.0.0.1:8765/Project4-Metasurface/preview.html` in Chrome on 2026-11-10 after the report generator added both neural tables and corrected plot margins/ticks.

- The full report renders as HTML, with no unexpanded Liquid tags. All nine report tables have matching header/body column counts, including the first response table with magnitude bars and both eight-column neural result tables.
- Unicode equations, Greek letters, subscripts/superscripts, integrals, inequalities and scientific notation were visually inspected. They display without a math CDN.
- All four SVG plots load: convergence, Taylor remainder, optimization history, and capacitance loading. Each was visually inspected on desktop and at 390 × 844. The original y-axis-title overlap was reported, fixed by the generator owner, and the corrected margin/scientific tick format was verified.
- Phone plot labels initially became too small. CSS now gives the plots a minimum 680 px width within scrollable figure paragraphs and a visible horizontal-swipe hint. Horizontal scrolling was exercised on the loading plot, exposing the far-right legend and cells. Tables also scroll independently, with numeric cells kept on one line.
- Final phone document width was 375 px with a 390 px viewport, including the expanded full report. No horizontal page overflow. Temporary viewport override reset afterward.
- Within the full preview, the linear comparison, OFF switch and reset controls were exercised. Linear comparison displays its re-evaluation status and disables history playback. Switching back to nonlinear works. No console errors or warnings were reported.
- Every local href/src target in the generated preview was checked against the filesystem and exists. The report jump link was clicked. External references were not revalidated in this UI pass.
- The mean-square voltage wording and same-design/no nonlinear redesign conclusion remain intact. No generator narrative was edited in this QA pass.

Additional actual screenshots in `site/qa/`:
- `report-convergence-desktop.png`: corrected convergence plot and report context.
- `report-neural-desktop.png`: hard-routing and overlap result tables.
- `report-taylor-mobile.png`: readable, horizontally scrollable Taylor plot.
- `report-table-mobile.png`: mobile neural result table and independent scrollbar.

This verifies the generated local full preview, not the deployed Jekyll site. GitHub Pages deployment, live Jekyll rendering, public/incognito availability and remote load time remain unverified.
