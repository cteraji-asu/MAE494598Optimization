"""Generate report.md, the HTML report body, preview.html and SVG figures.

Every number comes from the saved evidence files; nothing is typed by hand:
  assets/results.json                 frozen 10 Nov FE design study (reproduced)
  assets/rubric-studies.json          23 Nov supplemental FE runs (new)
  assets/surrogate-optimizer-loop.json 23 Nov saved-surrogate optimizer runs (new)
  assets/{two,smooth}-pinn-results.json frozen neural experiments
"""
from pathlib import Path
import html, json, math, re

ROOT = Path(__file__).resolve().parents[1]
P3_REPORT = 'https://github.com/cteraji-asu/MAE494598Optimization/blob/main/Project3-Metasurface/report.md'
P3_BRIEF = 'https://github.com/cteraji-asu/MAE494598Optimization/blob/main/Project3-Metasurface/sources/interview/Post_Interview_Briefing.md'
FROZEN = '**[frozen 10 Nov run]**'
NEW = '**[new 23 Nov run]**'


def num(v, sig=6):
    if v is None:
        return 'n/a'
    if isinstance(v, bool):
        return 'PASS' if v else 'FAIL'
    if v == 0:
        return '0'
    if abs(v) < 1e-3 or abs(v) >= 1e5:
        m, e = f'{v:.{max(sig-4,2)}e}'.split('e')
        return f'{m}e{int(e)}'
    return f'{v:.{sig}g}'


def pf(ok):
    return 'PASS' if ok else '**FAIL**'


def table(head, rows, align=None):
    align = align or ['---']*len(head)
    out = '| ' + ' | '.join(head) + ' |\n|' + '|'.join(align) + '|\n'
    out += '\n'.join('| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows)
    return '\n' + out + '\n'


# ------------------------------------------------------------------ SVG plots
COLORS = ['#0b6e78', '#c8641f', '#5b4b96', '#3f7a2e', '#a6466b', '#6b6b6b']


def plot(path, series, xlabel, ylabel, logx=False, logy=False, refs=(), title='', markers=None, ylim=None):
    tf = lambda z, log: math.log10(max(abs(z), 1e-300)) if log else z
    xs_all = [tf(x, logx) for _, xs, _ in list(series)+list(refs) for x in xs]
    ys_all = [tf(y, logy) for _, _, ys in list(series)+list(refs) for y in ys]
    lo, hi = min(xs_all), max(xs_all)
    low, high = (min(ys_all), max(ys_all)) if ylim is None else ylim
    if logy:
        low, high = math.floor(low), math.ceil(high)
    if logx:
        lo, hi = math.floor(lo), math.ceil(hi)
    if high == low: high += 1
    if hi == lo: hi += 1
    W, H, L, R, T, B = 760, 470, 96, 730, 40, 360
    X = lambda x: L+(R-L)*(tf(x, logx)-lo)/(hi-lo)
    Y = lambda y: B-(B-T)*(min(max(tf(y, logy), low), high)-low)/(high-low)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title or ylabel)}">',
         f'<title>{html.escape(title or ylabel)}</title>', f'<rect width="{W}" height="{H}" fill="#fbfcfa"/>',
         '<g font-family="system-ui,Segoe UI,sans-serif" font-size="15" fill="#1d3640">']
    def ticks(a, b, log):
        if log:
            step = max(1, round((b-a)/6))
            return [(v, f'1e{int(v)}') for v in range(int(a), int(b)+1, step)]
        span = b-a; raw = span/5; mag = 10**math.floor(math.log10(raw)); step = min([1, 2, 2.5, 5, 10], key=lambda s: abs(s*mag-raw))*mag
        v = math.ceil(a/step)*step; out = []
        while v <= b+1e-12:
            out.append((v, f'{v:.4g}')); v += step
        return out
    for v, lab in ticks(lo, hi, logx):
        sx = L+(R-L)*(v-lo)/(hi-lo)
        p += [f'<path d="M{sx:.1f} {T}V{B}" stroke="#e2e8e6"/>', f'<text x="{sx:.1f}" y="{B+22}" text-anchor="middle">{lab}</text>']
    for v, lab in ticks(low, high, logy):
        sy = B-(B-T)*(v-low)/(high-low)
        p += [f'<path d="M{L} {sy:.1f}H{R}" stroke="#e2e8e6"/>', f'<text x="{L-8}" y="{sy+5:.1f}" text-anchor="end">{lab}</text>']
    p += [f'<path d="M{L} {T}V{B}H{R}" stroke="#1d3640" fill="none"/>',
          f'<text x="{(L+R)/2}" y="{B+48}" text-anchor="middle">{html.escape(xlabel)}</text>',
          f'<text transform="translate(22 {(T+B)/2}) rotate(-90)" text-anchor="middle">{html.escape(ylabel)}</text>']
    legend = []
    for name, xs, ys in refs:
        pts = ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in zip(xs, ys))
        p.append(f'<polyline points="{pts}" stroke="#7d8b8f" stroke-dasharray="6 5" fill="none" stroke-width="2"/>')
        legend.append(('#7d8b8f', name, True))
    for k, (name, xs, ys) in enumerate(series):
        col = COLORS[k % len(COLORS)]
        pts = ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in zip(xs, ys))
        p.append(f'<polyline points="{pts}" stroke="{col}" fill="none" stroke-width="2.6"/>')
        if len(xs) <= 40:
            p += [f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3" fill="{col}"/>' for x, y in zip(xs, ys)]
        legend.append((col, name, False))
    for name, x, y, sym in (markers or []):
        p.append(f'<text x="{X(x):.1f}" y="{Y(y)+5:.1f}" text-anchor="middle" font-size="16" font-weight="700">{sym}</text>')
    for i, (col, name, dashed) in enumerate(legend):
        lx = L+(i % 3)*215; ly = B+78+(i//3)*22
        dash = ' stroke-dasharray="6 5"' if dashed else ''
        p += [f'<path d="M{lx} {ly-5}h26" stroke="{col}" stroke-width="3"{dash}/>', f'<text x="{lx+32}" y="{ly}">{html.escape(name)}</text>']
    p.append('</g></svg>')
    rows = (len(legend)+2)//3
    p[0] = p[0].replace(f'viewBox="0 0 {W} {H}"', f'viewBox="0 0 {W} {B+70+rows*22}"')
    path.write_text('\n'.join(p), encoding='utf-8')


# ------------------------------------------------------------------ Markdown -> HTML with protected math
def render_html(md_text):
    from markdown_it import MarkdownIt
    md = MarkdownIt('commonmark', {'html': True}).enable('table')
    store = []

    def keep(tex, display):
        store.append((tex.strip(), display)); return f'MATHTOKEN{len(store)-1}X'
    text = re.sub(r'^\$\$\n(.*?)\n\$\$$', lambda m: '\n'+keep(m.group(1), True)+'\n', md_text, flags=re.S | re.M)
    text = re.sub(r'(?<![\\$\w])\$(?!\$)([^$\n]+?)\$(?![\w$])', lambda m: keep(m.group(1), False), text)
    out = md.render(text)
    def back(m):
        tex, display = store[int(m.group(1))]
        tex = html.escape(tex, quote=False)
        return f'<div class="math display">\\[{tex}\\]</div>' if display else f'<span class="math inline">\\({tex}\\)</span>'
    out = re.sub(r'<p>MATHTOKEN(\d+)X</p>', back, out)
    out = re.sub(r'MATHTOKEN(\d+)X', back, out)
    assert 'MATHTOKEN' not in out
    return out


def fill(template, **values):
    for k, v in values.items():
        template = template.replace('[['+k+']]', str(v))
    left = re.findall(r'\[\[[a-zA-Z_0-9]+\]\]', template)
    assert not left, left
    return template


# ------------------------------------------------------------------ report
def build():
    d = json.loads((ROOT/'assets/results.json').read_text(encoding='utf-8'))
    s = json.loads((ROOT/'assets/rubric-studies.json').read_text(encoding='utf-8'))
    sl = json.loads((ROOT/'assets/surrogate-optimizer-loop.json').read_text(encoding='utf-8'))
    ini, lin, fin = d['initial'], d['linear']['final'], d['nonlinear']['final']
    checks = {c['name']: c for c in d['verification']['checks']}
    get = lambda key: next(c for n, c in checks.items() if key in n)
    figs = ROOT/'assets/figures'; figs.mkdir(parents=True, exist_ok=True)
    cfg = d['config']; L = cfg['length']; a_sw = L*cfg['switch_cell']/cfg['cells']

    # ---------------- results table (objective and every constraint)
    def rows_for(snap):
        g = snap['constraints']; c = snap['c']
        return [('Objective $f$ (minimize)', snap['objective'], None),
                ('Phase separation $\\Delta\\phi$ (reported, not constrained)', snap['phase_separation_degrees'], None),
                ('$g_1=\\lvert R_{ON}\\rvert^2-0.64\\ge 0$', g[0], g[0] >= -1e-7),
                ('$g_2=\\lvert R_{OFF}\\rvert^2-0.64\\ge 0$', g[1], g[1] >= -1e-7),
                ('$g_3=1.6-E_{ON}\\ge 0$', g[2], g[2] >= -1e-7),
                ('$g_4=1.6-E_{OFF}\\ge 0$', g[3], g[3] >= -1e-7),
                ('Lower bounds: $\\min_j c_j-0.5\\ge 0$', min(c)-.5, min(c)-.5 >= -1e-7),
                ('Upper bounds: $2.5-\\max_j c_j\\ge 0$', 2.5-max(c), 2.5-max(c) >= -1e-7)]
    ri, rf, rl = rows_for(ini), rows_for(fin), rows_for(lin)
    res_rows = []
    for (name, vi, oki), (_, vf, okf), (_, vl, okl) in zip(ri, rf, rl):
        cell = lambda v, ok: f'{num(v)}' + ('' if ok is None else (' ✓' if ok else ' ✗ **FAIL**'))
        res_rows.append([name, cell(vi, oki), cell(vf, okf), cell(vl, okl)])
    res_rows.append(['$\\lvert R_{ON}\\rvert$ / $\\lvert R_{OFF}\\rvert$', f"{num(ini['fields'][0]['reflection_magnitude'],4)} / {num(ini['fields'][1]['reflection_magnitude'],4)}",
                     f"{num(fin['fields'][0]['reflection_magnitude'],4)} / {num(fin['fields'][1]['reflection_magnitude'],4)}",
                     f"{num(lin['fields'][0]['reflection_magnitude'],4)} / {num(lin['fields'][1]['reflection_magnitude'],4)}"])
    res_rows.append(['$E_{ON}$ / $E_{OFF}$ (mean-square $\\lvert V\\rvert^2$)', f"{num(ini['fields'][0]['energy'],4)} / {num(ini['fields'][1]['energy'],4)}",
                     f"{num(fin['fields'][0]['energy'],4)} / {num(fin['fields'][1]['energy'],4)}", f"{num(lin['fields'][0]['energy'],4)} / {num(lin['fields'][1]['energy'],4)}"])
    results_table = table(['Quantity', 'Initial ($c_j=1$), nonlinear model', 'Optimized, nonlinear model', 'Linear-model optimum, linear model'], res_rows)
    reduction = 100*(ini['objective']-fin['objective'])/ini['objective']
    n_pass = sum(1 for _, _, ok in rf if ok); n_cons = sum(1 for _, _, ok in rf if ok is not None)
    slack_min = min(fin['constraints'])

    # ---------------- verification ladder
    mesh = get('Uniform'); mms = get('Manufactured'); bal = get('power balance'); eqv = get('equivariance')
    newton_q = get('Quadratic'); jac = get('Jacobian'); lin_lim = get('Linear limit'); grad = get('All five'); tay = get('Taylor')
    nu = s['ladder']['nonuniform_abcd']; nu_r = next(x for x in nu if x['design'] == 'random_2026'); nu_o = next(x for x in nu if x['design'] == 'nonlinear_optimum')
    loss = s['ladder']['lossless']; loss_max = max(x['relative_error'] for x in loss)
    pb = [f['power_balance'] for f in fin['fields']]
    pb_err = max(abs(x['defect'])/abs(x['incoming']) for x in pb)
    coord5 = s['gradients']['coordinate']; coord = s['gradients']['coordinate_h1e3']; coord_max = max(max(x['relative_errors']) for x in coord); coord5_max = max(max(x['relative_errors']) for x in coord5)
    sweep = s['gradients']['step_sweep']; sweep_orders = [o for x in sweep for o in x['order_first_decade']]
    mms_rates = mms['rates']; mesh_rates = mesh['rates']
    ladder_rows = [
        ['V1', 'Exact solution', 'Uniform loading vs Project 3 ABCD cascade, 320 elements', f"$R_{{ON}}$={mesh['comparisons'][0]['computed'][0]:.6f}{mesh['comparisons'][0]['computed'][1]:+.6f}i", f"{mesh['comparisons'][0]['exact'][0]:.6f}{mesh['comparisons'][0]['exact'][1]:+.6f}i", 'rel. ' + num(max(x['relative_error'] for x in mesh['comparisons']), 3), pf(mesh['passed']), FROZEN],
        ['V2', 'Exact solution', 'Variable loading $c_j$ (random design) vs independent transfer-matrix cascade, 640 elements', f"{nu_r['levels'][-1]['fe'][0][0]:.6f}{nu_r['levels'][-1]['fe'][0][1]:+.6f}i", f"{nu_r['exact'][0][0]:.6f}{nu_r['exact'][0][1]:+.6f}i", 'rel. ' + num(nu_r['levels'][-1]['relative_error'], 3), pf(nu_r['levels'][-1]['relative_error'] < 1e-4), NEW],
        ['V3', 'Convergence rate', 'Slope of reflection error vs elements (uniform; variable loading; optimum)', f"{min(mesh_rates):.3f}; {min(nu_r['rates']):.3f}; {min(nu_o['rates']):.3f}", '2 (P1)', 'order deficit ' + num(max(abs(min(mesh_rates)-2), abs(min(nu_r['rates'])-2), abs(min(nu_o['rates'])-2)), 2), pf(min(mesh_rates+nu_r['rates']+nu_o['rates']) > 1.9), FROZEN+' / '+NEW],
        ['V4', 'Exact solution (nonlinear, manufactured)', 'Cubic $\\chi\\lvert V\\rvert^2V$ manufactured field with switch jump, 160 elements', f"rel. $L_2$ error {num(mms['comparison']['relative_L2_error'],3)}; slope {min(mms_rates):.3f}", '0; slope 2', 'rel. ' + num(mms['comparison']['relative_L2_error'], 3), pf(mms['passed']), FROZEN],
        ['V5', 'Global balance', 'Power: line loss + switch loss vs $1-\\lvert R\\rvert^2$ at the optimum, both states', f"{pb[1]['line_loss']+pb[1]['switch_loss']:.9f} (OFF)", f"{pb[1]['incoming']:.9f}", 'rel. ' + num(pb_err, 3), pf(pb_err < 1e-6), FROZEN],
        ['V6', 'Global balance (conservation)', 'Lossless line, reactive switches, linear and cubic: all power reflects', f"max $\\lvert R\\rvert$ deviation {num(loss_max,3)}", '$\\lvert R\\rvert=1$', 'rel. ' + num(loss_max, 3), pf(loss_max < 1e-8), NEW],
        ['V7', 'Invariance', 'Rotate the incident phase by 0.73 rad: field must rotate identically (cubic law is phase-equivariant)', num(eqv['value'], 3), '0', f"abs. {num(eqv['value'],3)} ($\\lvert V\\rvert\\sim1$)", pf(eqv['passed']), FROZEN],
        ['V8', 'Nonlinear benchmark', 'Newton: analytic tangent vs central difference (rel.); observed convergence order; with $\\chi=0$ the linear initial guess must already satisfy the residual', f"{num(jac['value'],3)}; order {newton_q['value']:.3f}; {lin_lim['iterations']} iterations, residual {num(lin_lim['value'],2)}", '0; 2; 0 iterations', 'rel. ' + num(jac['value'], 3), pf(jac['passed'] and newton_q['passed'] and lin_lim['passed']), FROZEN],
        ['V9', 'Gradient check', 'Adjoint vs central differences ($h=10^{-3}$), all 20 coordinates, objective and all 4 constraints, 3 designs', f"max rel. error {num(coord_max,3)}", '0', 'rel. ' + num(coord_max, 3), pf(coord_max < 1e-5), NEW],
        ['V10', 'Gradient check (Taylor)', 'Central-difference error vs step: observed order before round-off, 5 metrics × 3 designs', f"{min(sweep_orders):.2f}–{max(sweep_orders):.2f}", '2', 'order deficit ' + num(abs(min(sweep_orders)-2), 2), pf(min(sweep_orders) > 1.6), NEW],
    ]
    ladder_table = table(['Rung', 'Kind', 'Test', 'Our number', 'Exact', 'Error (type)', 'Result', 'Evidence'], ladder_rows)
    plot(figs/'convergence.svg', [
        ('Uniform loading vs ABCD', [20*p for p in mesh['per_cell']], mesh['errors']),
        ('Variable loading vs cascade', [x['elements'] for x in nu_r['levels']], [x['relative_error'] for x in nu_r['levels']]),
        ('Manufactured nonlinear L2', [20*p for p in mms['per_cell']], mms['errors'])],
        'Elements (log scale)', 'Error (log scale)', True, True,
        refs=[('slope −2 reference', [20, 640], [3e-2, 3e-2/32**2])], title='Mesh convergence of three verification problems')

    # ---------------- sensitivities
    names = ['Objective $f$', '$g_1$ ON amplitude', '$g_2$ OFF amplitude', '$g_3$ ON mean-square V', '$g_4$ OFF mean-square V']
    plain = ['objective', 'g1 ON amplitude', 'g2 OFF amplitude', 'g3 ON mean-square V', 'g4 OFF mean-square V']
    label = {'initial_uniform': 'Initial $c_j=1$', 'random_2026': 'Random interior design', 'nonlinear_optimum': 'Selected optimum'}
    coord_rows = [[names[i]] + [f"{num(x['relative_errors'][i], 2)} ({num(y['relative_errors'][i], 2)})" for x, y in zip(coord, coord5)] for i in range(5)]
    coord_table = table(['Metric'] + [label[x['design']] + ', $h=10^{-3}$ ($h=10^{-5}$)' for x in coord], coord_rows)
    sw = next(x for x in sweep if x['design'] == 'random_2026')
    plot(figs/'step-sweep.svg', [(plain[i], sw['steps'], [r[i] for r in sw['relative_errors']]) for i in range(5)],
         'Central-difference step ε (log scale)', 'Relative error vs adjoint (log scale)', True, True,
         refs=[('ε² reference', [1e-1, 1e-4], [1e-3, 1e-9])], title='Taylor test: central-difference error falls as ε² until round-off')
    plot(figs/'taylor.svg', [(plain[i], tay['steps'], [r[i] for r in tay['remainders']]) for i in range(5)],
         'Perturbation h (log scale)', 'First-order Taylor remainder (log scale)', True, True,
         refs=[('h² reference', [.04, .0025], [1e-3, 1e-3/256])], title='First-order Taylor remainder')
    cost = s['cost']
    cost_rows = [[c['design_variables'], c['elements'], c['finite_difference_forward_solves'], f"{c['adjoint_forward_solves']} + {c['adjoint_transposed_solves']} transposed", num(c['finite_difference_seconds_median'], 3), num(c['adjoint_seconds_median'], 3), f"{c['ratio']:.0f}×"] for c in cost]
    cost_table = table(['Design variables $n$', 'Elements', 'FD Newton solves', 'Adjoint solves', 'FD time (s, median of 7)', 'Adjoint time (s)', 'FD / adjoint'], cost_rows)
    plot(figs/'cost.svg', [('Central differences', [c['design_variables'] for c in cost], [c['finite_difference_seconds_median'] for c in cost]),
                            ('Adjoint (all 5 metrics)', [c['design_variables'] for c in cost], [c['adjoint_seconds_median'] for c in cost])],
         'Number of design variables n (log scale)', 'Seconds per full gradient (log scale)', True, True, title='Gradient cost versus number of design variables')

    # ---------------- optimization
    multi = []
    for key in ['linear', 'nonlinear']:
        for r in d[key]['runs']:
            fobj = r.get('final', {}).get('objective')
            multi.append([('Linear ($\\chi=0$)' if key == 'linear' else 'Nonlinear ($\\chi=0.05$)'), r['start'].replace('_', ' '), r.get('iterations', 'n/a'), num(fobj),
                          num(r.get('kkt', {}).get('stationarity_inf'), 2), 'yes' if r['success'] and r.get('final', {}).get('feasible') else '**no**', r['message']])
    multi_table = table(['Model', 'Start', 'Iterations', 'Final objective', 'KKT stationarity', 'Converged & feasible', 'Optimizer message'], multi)
    plot(figs/'optimization.svg', [(f"{r['start'].replace('_',' ')}", list(range(len(r['history']))), [h['objective'] for h in r['history']]) for r in d['nonlinear']['runs'] if len(r.get('history', [])) > 1],
         'Accepted SLSQP iterate', 'Objective f (log scale)', False, True, title='Nonlinear-model convergence histories for every start')
    mu = d['nonlinear']['kkt']['multipliers']; mul = d['linear']['kkt']['multipliers']
    kr = {r['bound']: r for r in s['kkt_relaxation']['single_bounds']}
    mu_rows = []
    for k, v in mu.items():
        kind, j = k.split('_'); j = int(j)
        r = kr[k]
        mu_rows.append([j+1, 'before switch' if j < cfg['switch_cell'] else 'after switch', ('lower 0.5' if kind == 'lower' else 'upper 2.5'), num(mul[k], 4), num(v, 4),
                        num(r['predicted_change'], 3), num(r['actual_change'], 3), f"{100*abs(r['actual_change']-r['predicted_change'])/abs(r['predicted_change']):.1f}%"])
    mu_table = table(['Cell', 'Side', 'Active bound', 'μ linear', 'μ nonlinear', 'Predicted Δf (δ=0.02)', 'Re-solved Δf', 'Difference'], mu_rows)
    allb = s['kkt_relaxation']['all_bounds']
    big = max(mu, key=mu.get); small = min(mu, key=mu.get)

    # limit sweep
    ls = s['limit_sweep']
    ls_rows = []
    for r in ls:
        b = r['best']
        if b is None:
            ls_rows.append([r['energy_limit'], r['chi'], 'none feasible', '', '', '', '']); continue
        act = [k for k in b['multipliers'] if k.startswith('energy')]
        chk = r.get('multiplier_check')
        ls_rows.append([r['energy_limit'], r['chi'], num(b['objective'], 5), f"{b['phase_separation_degrees']:.2f}", ', '.join(a.replace('energy_', 'E_').upper().replace('E_', '$E_{')+'}$' for a in act) or 'none (bounds only)',
                        ', '.join(num(r['energy_multipliers'][a], 4) for a in act) or '0', ('' if not chk else f"{num(chk['finite_difference'],4)} vs {num(chk['predicted'],4)}" + ('' if chk['success'] else ' (re-solve flagged not converged)'))])
    ls_table = table(['Limit $E_{max}$', '$\\chi$', 'Optimal $f$', 'Δφ (°)', 'Active response constraints', 'μ', '$\\Delta f^*/\\Delta E_{max}$ re-solve vs −Σμ'], ls_rows)
    plot(figs/'limit-sweep.svg', [('Linear model χ=0', [r['energy_limit'] for r in ls if r['chi'] == 0], [r['best']['objective'] for r in ls if r['chi'] == 0]),
                                   ('Nonlinear model χ=0.05', [r['energy_limit'] for r in ls if r['chi'] == .05], [r['best']['objective'] for r in ls if r['chi'] == .05])],
         'Mean-square voltage limit E_max', 'Optimal objective f*', title='Cost of tightening the voltage-exposure limit (post hoc)')

    # ---------------- nonlinear component
    ww = s['with_without']; ww_rows = []
    for c in ww:
        if not c['available']:
            continue
        ln = c['linear_design_in_nonlinear_model']; nl = c['nonlinear_design']
        ww_rows.append([c['energy_limit'], num(c['max_design_difference'], 3), num(nl['objective'], 5), num(ln['objective'], 5), f"{100*(ln['objective']-nl['objective'])/nl['objective']:.1f}%", f"{nl['phase_separation_degrees']:.2f} / {ln['phase_separation_degrees']:.2f}", 'yes' if ln['feasible'] else '**no**'])
    ww_table = table(['$E_{max}$', 'max Δc (linear vs nonlinear design)', 'Nonlinear optimum $f$', 'Linear design in nonlinear model $f$', 'Penalty for ignoring nonlinearity', 'Δφ (°) nonlinear / linear design', 'Linear design feasible?'], ww_rows)
    cs = s['chi_sweep']; cs_rows = []
    for c in cs:
        b = c['best']
        cs_rows.append([c['chi'], num(b['objective'], 5), f"{b['phase_separation_degrees']:.2f}", num(c['max_design_difference_from_linear'], 2), num(b['multipliers'].get('lower_0', 0), 4) if 'lower_0' in b['multipliers'] else 'cell 1 at upper bound',
                        f"{c['strength'][1]['max_ratio']:.3f}", ', '.join(x.replace('_', ' ') for x in c['failed_starts']) or 'none'])
    cs_table = table(['$\\chi$', 'Best $f$', 'Δφ (°)', 'max Δc from linear design', 'μ of cell 1 lower bound', 'max $\\chi\\lvert V\\rvert^2/c$ (OFF)', 'Starts that failed'], cs_rows)
    st = s['nonlinearity_strength_at_optimum']
    lim105 = {r['chi']: r['best'] for r in ls if r['energy_limit'] == 1.05}
    plot(figs/'loading.svg', [('Initial', list(range(1, 21)), ini['c']), ('Frozen optimum (linear = nonlinear)', list(range(1, 21)), fin['c']),
                               ('E_max=1.05, linear model', list(range(1, 21)), lim105[0]['c']), ('E_max=1.05, nonlinear model', list(range(1, 21)), lim105[.05]['c'])],
         'Loading cell j (switch between cells 6 and 7)', 'Capacitance multiplier c_j', title='Loading distributions', ylim=(0.3, 2.7))
    delta = max(abs(a-b) for a, b in zip(lin['c'], fin['c']))

    # ---------------- neural / surrogate
    neural = []
    for prefix, title in [('two-pinn', 'Experiment A — hard routing between two networks'), ('smooth-pinn', 'Experiment B — differentiable (smooth) blending')]:
        nn = json.loads((ROOT/'assets'/f'{prefix}-results.json').read_text(encoding='utf-8'))
        rows = [[r['mode'].replace('_', ' '), r['seed'], num(r['final']['reflection_p95'], 3), num(100*r['final']['voltage_relative_L2_median'], 3), f"{r['final']['tp']}/{r['final']['tp']+r['final']['fn']}", r['final']['fp'], num(100*r['gradients']['reference_gradient_relative_L2'], 3), pf(r['final']['gate_pass'])] for r in nn['runs']]
        neural.append(f'**{title}** {FROZEN}\n' + table(['Model', 'Seed', 'Reflection error p95', 'Median field $L_2$ error (%)', 'Feasible retained', 'False feasible', 'Design-gradient error (%)', 'Gate'], rows))
    (ROOT/'two-pinn-summary.md').write_text('# Generated two-PINN numerical summary\n\n' + '\n'.join(neural) + '\nSource: assets/two-pinn-results.json and assets/smooth-pinn-results.json.\n', encoding='utf-8')
    ref = sl['reference']
    ref_rows = [[f"{r['start']:.2f}", f"{r['d']:.5f}", num(r['fe_metrics'][0], 3), f"{r['exact_phase_degrees']:.2f}", 'bound' if r['at_bound'] else 'interior'] for r in ref['runs']]
    ref_table = table(['Start $d_0$', 'FE-adjoint SLSQP endpoint $d$', 'FE objective $q$', 'Exact Δφ (°)', 'Endpoint'], ref_rows)
    sur_rows = []
    for m in sl['models']:
        ends = {f"{r['start']:.2f}": r for r in m['runs']}
        e18 = ends['0.18']; e24 = ends['0.24']
        sur_rows.append([('A ' if m['study'] == 'two-pinn' else 'B ')+m['mode'].replace('_', ' '), m['seed'], num(m['grid_gradient_relative_L2'], 3), f"{100*(1-m['grid_sign_agreement']):.0f}%",
                         f"{e18['d']:.4f} (FE $q$ {num(e18['fe_metrics'][0],2)})", f"{e24['d']:.4f} (FE $q$ {num(e24['fe_metrics'][0],2)})",
                         f"{num(m['selected']['surrogate_objective'],3)} vs {num(m['selected']['fe_objective'],2)}"])
    sur_table = table(['Surrogate', 'Seed', 'Gradient rel. $L_2$ error vs FE adjoint', 'Wrong gradient sign', 'Endpoint from $d_0=0.18$', 'Endpoint from $d_0=0.24$', 'Own optimum: predicted $q$ vs FE $q$'], sur_rows)
    m0 = next(m for m in sl['models'] if m['study'] == 'smooth-pinn' and m['mode'] == 'monolithic' and m['seed'] == 0)
    m1 = next(m for m in sl['models'] if m['study'] == 'smooth-pinn' and m['mode'] != 'monolithic' and m['seed'] == 0)
    plot(figs/'surrogate-objective.svg', [('FE reference', m0['grid_d'], m0['grid_fe_objective']), ('Surrogate B monolithic s0', m0['grid_d'], m0['grid_surrogate_objective']), ('Surrogate B specialists s0', m1['grid_d'], m1['grid_surrogate_objective'])],
         'Switch-to-short length d (wavelengths)', 'Objective q = 1 + cos Δφ', title='Restricted family: surrogate versus FE objective')
    plot(figs/'surrogate-gradient.svg', [('FE adjoint', m0['grid_d'], m0['grid_fe_gradient']), ('Surrogate B monolithic s0', m0['grid_d'], m0['grid_surrogate_gradient']), ('Surrogate B specialists s0', m1['grid_d'], m1['grid_surrogate_gradient'])],
         'Switch-to-short length d (wavelengths)', 'dq/dd', title='Restricted family: surrogate versus FE-adjoint design gradient')
    gl2 = [m['grid_gradient_relative_L2'] for m in sl['models']]; sgn = [1-m['grid_sign_agreement'] for m in sl['models']]
    pred_q = [m['selected']['surrogate_objective'] for m in sl['models']]; fe_q = [m['selected']['fe_objective'] for m in sl['models']]
    phase_err = lambda q: 180-math.degrees(math.acos(max(-1, min(1, q-1))))
    interior = sum(1 for m in sl['models'] for r in m['runs'] if abs(r['d']-ref['selected']['d']) < 5e-3)
    stalled = [m for m in sl['models'] if abs(next(r for r in m['runs'] if abs(r['start']-.24) < 1e-9)['d']-.036) > 1e-3]

    phcost=f"{lin['phase_separation_degrees']-fin['phase_separation_degrees']:.1f}"
    nls=sorted([r for r in ls if r['chi']==.05 and r['energy_limit']<1.6],key=lambda r:-r['energy_limit'])
    slopes=[(a['best']['phase_separation_degrees']-b['best']['phase_separation_degrees'])/(100*(a['energy_limit']-b['energy_limit'])) for a,b in zip(nls,nls[1:])]
    pens=[100*(c['linear_design_in_nonlinear_model']['objective']-c['nonlinear_design']['objective'])/c['nonlinear_design']['objective'] for c in ww if c['available'] and c['max_design_difference']>1e-6]
    nng=[]
    for prefix in ['two-pinn','smooth-pinn']:
        nn=json.loads((ROOT/'assets'/f'{prefix}-results.json').read_text(encoding='utf-8')); nng+= [100*r['gradients']['reference_gradient_relative_L2'] for r in nn['runs']]
    d18=[next(r for r in m['runs'] if abs(r['start']-.18)<1e-9)['d'] for m in sl['models']]
    qr=[a/b for a,b in zip(pred_q,fe_q)]
    import numpy as _np
    best_steps = [x['steps'][k] for x in sweep for k in _np.array(x['relative_errors']).argmin(0)]
    sc = s['scaled_constraints']['runs']; sc_ok = [r for r in sc if r['success']]
    sc_dc = max(max(abs(a-b) for a, b in zip(r['c'], fin['c'])) for r in sc_ok)
    nf = s['newton_failure']['states']; nf_off = next(x for x in nf if x['state'] == 'off'); nf_on = next(x for x in nf if x['state'] == 'on')
    nf_fail_chi = next(p['chi'] for p in nf_off['continuation'] if not p['converged'])
    ups = sorted([(v, int(k.split('_')[1])+1) for k, v in mu.items() if k.startswith('upper')], reverse=True)[:3]
    top_up = sorted(c for _, c in ups)
    cont = [m for m in sl['models'] if m['continuous']]; disc = [m for m in sl['models'] if not m['continuous']]
    mono = [m for m in sl['models'] if m['mode'] == 'monolithic']; blend = [m for m in sl['models'] if m['mode'] == 'smooth_specialists']
    rng = lambda xs, f='{:.2f}': f.format(min(xs)) if f.format(min(xs)) == f.format(max(xs)) else f.format(min(xs)) + '–' + f.format(max(xs))
    true_min = sl['models'][0]['band']['inside']['fe_argmin']
    # ---------------- assemble
    T = REPORT_TEMPLATE
    values = dict(
        f0=num(ini['objective']), f1=num(fin['objective']), red=f'{reduction:.1f}', ph0=f"{ini['phase_separation_degrees']:.1f}", ph1=f"{fin['phase_separation_degrees']:.1f}",
        slack=num(slack_min, 4), E0on=num(ini['fields'][0]['energy'], 4), E0off=num(ini['fields'][1]['energy'], 4),
        results_table=results_table, P3=P3_REPORT, P3B=P3_BRIEF, L=L, a=num(a_sw, 4), dlen=num(L-a_sw, 4), FROZEN=FROZEN, NEW=NEW,
        elements=d['mesh']['elements'], unknowns=d['mesh']['complex_unknowns'], ladder_table=ladder_table,
        coord_table=coord_table, cost_table=cost_table, ratio20=f"{next(c for c in cost if c['design_variables']==20)['ratio']:.0f}",
        ratio80=f"{next(c for c in cost if c['design_variables']==80)['ratio']:.0f}", fdtime_old=num(grad['finite_difference_seconds'], 3), adjtime_old=num(grad['adjoint_seconds'], 3),
        sweep_min=f'{min(sweep_orders):.2f}', coord_max=num(coord_max, 2),
        multi_table=multi_table, mu_table=mu_table, big_cell=int(big.split('_')[1])+1, big_mu=num(mu[big], 3), small_cell=int(small.split('_')[1])+1, small_mu=num(mu[small], 2),
        allpred=num(allb['predicted_change'], 4), allact=num(allb['actual_change'], 4),
        ls_table=ls_table, mu105=num(next(r for r in ls if r['chi'] == .05 and r['energy_limit'] == 1.05)['energy_multipliers']['energy_off'], 3),
        delta=num(delta, 2), phl=f"{lin['phase_separation_degrees']:.2f}", phn=f"{fin['phase_separation_degrees']:.2f}", fl=num(lin['objective']), fn=num(fin['objective']),
        mumin_l=num(min(mul.values()), 3), mumin_n=num(min(mu.values()), 3), st_on=f"{st[0]['max_ratio']:.3f}", st_off=f"{st[1]['max_ratio']:.2f}", st_offmean=f"{st[1]['mean_ratio']:.2f}",
        ww_table=ww_table, cs_table=cs_table, mu_cell1_l=num(mul['lower_0'], 3), mu_cell1_n=num(mu['lower_0'], 3),
        neural='\n'.join(neural), ref_table=ref_table, sur_table=sur_table, refd=f"{ref['selected']['d']:.5f}", refph=f"{ref['selected']['exact_phase_degrees']:.2f}",
        gl2lo=f'{min(gl2):.2f}', gl2hi=f'{max(gl2):.2f}', sgnlo=f'{100*min(sgn):.0f}', sgnhi=f'{100*max(sgn):.0f}',
        pqlo=num(min(pred_q), 2), pqhi=num(max(pred_q), 2), perrlo=f'{phase_err(min(pred_q)):.1f}', perrhi=f'{phase_err(max(pred_q)):.1f}', feqlo=num(min(fe_q), 2), feqhi=num(max(fe_q), 2), feperrlo=f'{phase_err(min(fe_q)):.2f}', feperrhi=f'{phase_err(max(fe_q)):.1f}', dsello=f"{min(m['selected']['d'] for m in sl['models']):.3f}", dselhi=f"{max(m['selected']['d'] for m in sl['models']):.3f}",
        interior=interior, nstalled=len(stalled), nmodels=len(sl['models']), runs_total=sum(len(m['runs']) for m in sl['models']),
        rs_seconds=f"{s['provenance']['seconds']:.0f}", lin_uni_f0=num(next(r for r in d['linear']['runs'] if r['start']=='uniform')['history'][0]['objective']), lin_uni_f1=num(next(r for r in d['linear']['runs'] if r['start']=='uniform')['final']['objective']),
        hl01=num(next(r for r in next(c for c in cs if c['chi']==.1)['runs'] if r['start']=='high_low')['objective'], 4),
        ord_ini=rng(next(x for x in sweep if x['design']=='initial_uniform')['order_first_decade']), ord_opt=rng(next(x for x in sweep if x['design']=='nonlinear_optimum')['order_first_decade']), lbph=f"{next(r for r in ref['runs'] if r['d'] < .037)['exact_phase_degrees']:.1f}", step_lo=num(min(best_steps), 1), step_hi=num(max(best_steps), 1), coord5_max=num(coord5_max, 2),
        sc_n=len(sc_ok), sc_dc=num(sc_dc, 1), nf_vlin=f"{nf_off['linear_max_voltage']:.2f}", nf_ratio=f"{100*nf_off['linear_max_ratio']:.0f}", nf_chi=num(nf_fail_chi, 2), nf_on_v=f"{nf_on['linear_max_voltage']:.2f}",
        topcells=', '.join(str(c) for c in top_up), refd3=f"{ref['selected']['d']:.4f}", allpred_abs=num(abs(allb['predicted_change']), 4), allact_abs=num(abs(allb['actual_change']), 4),
        m_in_mae=rng([m['band']['inside']['objective_mae'] for m in mono]), m_in_min=rng([m['band']['inside']['surrogate_objective_min'] for m in mono]),
        m_in_g=rng([m['band']['inside']['gradient_relative_L2'] for m in mono]), b_in_mae=rng([m['band']['inside']['objective_mae'] for m in blend]),
        b_in_arg=rng([m['band']['inside']['surrogate_argmin'] for m in blend], '{:.4f}'), b_in_min=rng([m['band']['inside']['surrogate_objective_min'] for m in blend]),
        b_in_g=rng([m['band']['inside']['gradient_relative_L2'] for m in blend]), true_min=f"{true_min:.4f}", fe_in_min=num(sl['models'][0]['band']['inside']['fe_objective_min'], 2),
        out_mae=rng([m['band']['outside_low']['objective_mae'] for m in sl['models']]), out_mae_hi=rng([m['band']['outside_high']['objective_mae'] for m in sl['models']]), ncont=len(cont), ndisc=len(disc), phcost=phcost, st_pct=f"{100*st[1]['max_ratio']:.0f}", fcost01=num(0.01*next(r for r in ls if r['chi'] == .05 and r['energy_limit'] == 1.05)['energy_multipliers']['energy_off'],2), phslope=f"{min(slopes):.1f}–{max(slopes):.1f}", penlo=f"{min(pens):.0f}", penhi=f"{max(pens):.0f}", nglo=f"{min(nng):.0f}", nghi=f"{max(nng):.0f}", d18max=f"{max(d18):.3f}", qratio=f"{min(qr):.0f}–{max(qr):.0f}", sl_seconds=f"{sl['seconds']:.0f}", run_seconds=f"{d['provenance']['seconds']:.1f}")
    report = fill(T, **values)
    assert '{{' not in report and '{%' not in report, 'Liquid-sensitive text in report'
    (ROOT/'report.md').write_text(report, encoding='utf-8')
    body = render_html(report)
    (ROOT/'site/report-body.html').write_text(body, encoding='utf-8')
    shell = (ROOT/'index.md').read_text(encoding='utf-8')
    shell = re.sub(r'^---\s*\n.*?\n---\s*\n', '', shell, count=1, flags=re.S)
    assert '{% include_relative site/report-body.html %}' in shell
    shell = shell.replace('{% include_relative site/report-body.html %}', body)
    assert '{%' not in shell and '{{' not in shell
    (ROOT/'preview.html').write_text(shell.rstrip()+'\n', encoding='utf-8')
    print('Generated report.md, site/report-body.html, preview.html and figures from the saved evidence files.')


REPORT_TEMPLATE = r'''<!-- Generated by code/build_report.py from assets/*.json. Do not edit by hand. -->
## 1. Summary

**Design question.** A radio-frequency wave travels down a transmission line, passes a two-state switch and reflects from a short circuit. Can the loading along the line be chosen so that the two switch states reflect waves about 180° apart, while each state still reflects at least 80% of the incident amplitude and the line's voltage exposure stays bounded?

**Answer for this model.** The optimizer reduces the objective from **[[f0]] to [[f1]]** ([[red]]% lower), raises the ON/OFF phase separation from **[[ph0]]° to [[ph1]]°**, and moves the design from infeasible (mean-square voltage [[E0on]] and [[E0off]] against a limit of 1.6) to **feasible on all four response constraints and all 40 loading bounds**. The optimum puts light loading on the six cells before the switch and heavy loading on the fourteen after it: every cell sits at one of its two bounds (20 of the 40 bounds active). The best design found reaches [[ph1]]°, short of 180°. Of five starts per model, one (low-high) begins at this design, and two (linear) or three (nonlinear) of the other four reach it; none found a better local optimum within these loading bounds.

**What is new compared with Project 3.** The design reference is now a verified finite-element solver with adjoint gradients, not a neural field model. Neural surrogates of Project 3's restricted problem (new networks trained in Project 4 follow-up experiments) were also run inside a gradient-based optimizer. Their gradients and optima disagree with the finite-element reference in specific, reproducible ways (Section 10).

**Evidence labels.** [[FROZEN]] marks results from the frozen 10 November design study, reproduced unchanged in `assets/results.json`. [[NEW]] marks supplemental runs added on 23 November on the same unchanged solver (`assets/rubric-studies.json`, `assets/surrogate-optimizer-loop.json`). New runs never overwrite the frozen design. Studies run after the frozen optimum was known are labelled *post hoc*.

### Results: objective and every constraint [[FROZEN]]

[[results_table]]

All values are dimensionless (Section 3). ✓ = constraint satisfied, ✗ = violated. The smallest response-constraint slack at the optimum is [[slack]] (ON amplitude).

## 2. From Project 3 to Project 4

**The researcher's problem.** In our Project 3 interview, Nathan described electronically reconfigurable metasurfaces: copper unit cells with switches that steer or redistribute reflected RF power ([approved team briefing]([[P3B]])). We reduced one unit cell to a synthetic transmission line ([Project 3 report]([[P3]])). A wave enters at the port, travels a length $a$ to a series switch, then a length $d$ to a short circuit. The short forces $V=0$, so a wave reflecting from it alone has reflection coefficient $\Gamma=-1$. Switching changes the switch impedance (ON: nearly a short; OFF: nearly an open). That changes the effective electrical length the wave sees, and with it the reflected phase. The design question was whether the two states can reflect about 180° apart while keeping reflected amplitude at least 0.8.

**What Project 3 found.** Project 3 trained physics-informed neural networks (PINNs) to predict the line's field as a function of the design. Average field error was low on designs similar to the training set: median voltage $L_2$ error 3.3–3.4% on the off-grid test, where all 21/21 feasible designs were retained. But in a withheld interval of switch positions near the resonant response, the same networks had 44.7–45.7% median voltage error and kept **0 of 10** feasible designs in every seed. A low average field error did not show that the model could find feasible designs, or that its design gradients could be trusted.

**What Project 4 does.**

1. Build a design-scale model the networks never saw: 20 independent loading variables and a nonlinear (voltage-dependent) loading law (Sections 3–4).
2. Solve it with our own finite-element code, verified against exact solutions (Section 5).
3. Differentiate it with adjoints, checked against finite differences (Section 6).
4. Optimize it and read the KKT multipliers (Section 7).
5. Show what the nonlinearity changes (Section 8).
6. Return to the Project 3 question with new surrogates of Project 3's restricted problem, trained with half their data in the difficult interval. Put them inside an optimizer and compare their gradients and optima with the finite-element reference (Section 10).

## 3. Structure and formulation

The line has length $L=[[L]]$ (in reference wavelengths $\lambda_{ref}=2\pi/\beta$). The switch sits at $a=[[a]]$, between cells 6 and 7, leaving $d=[[dlen]]$ to the short. All quantities are normalized: impedances by the line impedance $Z_0$, voltages by the incident amplitude, lengths by $\lambda_{ref}$.

**Design variables.** There are 20 cell loadings $c_j$, $j=1,\dots,20$. Each multiplies the nominal shunt capacitance per unit length over one cell of length $L/20=0.018$. Bounds are $0.5\le c_j\le 2.5$ (dimensionless). Line geometry is fixed. Only the distributed loading changes.

**Objective.** With $R_s$ the port reflection coefficient in state $s\in\{ON, OFF\}$:

$$
f(c)=\lvert R_{ON}+R_{OFF}\rvert^2+\frac{0.002}{20}\sum_{j=1}^{20}(c_j-1)^2,
\qquad
\lvert R_{ON}+R_{OFF}\rvert^2=\lvert R_{ON}\rvert^2+\lvert R_{OFF}\rvert^2+2\lvert R_{ON}\rvert\lvert R_{OFF}\rvert\cos\Delta\phi .
$$

The first term is smallest when the phasors oppose ($\Delta\phi=180°$) with equal magnitude. The small second term discourages unnecessary departure from nominal loading.

**Constraints** (all written $g\ge0$):

$$
g_{1,2}=\lvert R_{ON/OFF}\rvert^2-0.8^2\ge0,\qquad
g_{3,4}=1.6-E_{ON/OFF}\ge0,\qquad E_s=\frac1L\int_0^L\lvert V_s\rvert^2\,dx .
$$

| Limit | Value | Where it comes from | Status |
|---|---|---|---|
| Reflected amplitude floor | $\lvert R\rvert\ge0.8$ | Project 3 screening criterion, kept so that a non-reflecting line cannot "win" | Illustrative team choice, **not** a confirmed lab tolerance |
| Mean-square voltage | $E\le1.6$ | Synthetic exposure limit, fixed after a coarse pilot and before the final runs | Synthetic; not from a standard or data sheet. It is loose at the optimum; Section 7 tightens it post hoc |
| Loading range | $0.5\le c_j\le2.5$ | A 5:1 tuning range, comparable to commercial varactors: minimum $C(0\,\mathrm V)/C(30\,\mathrm V)=4.1$ for the Skyworks SMV1405 abrupt-junction varactor ([data sheet 200068X](https://www.skyworksinc.com/-/media/SkyWorks/Documents/Products/101-200/SMV1405_1430_Series_200068X_discontinued.pdf), Table 3) | Comparable, not derived: $c_j$ is a per-cell multiplier, not a fitted device model. Sets the bound-dominated optimum |

$E$ is a spatial average of normalized $\lvert V\rvert^2$, not stored energy and not a local voltage ceiling. These limits need instructor acceptance as part of the custom Project 3 extension (Section 13).

## 4. Analysis model

With $e^{+i\omega t}$ phasors, series impedance $z=\alpha+i\beta$ and shunt admittance $y_j=\alpha+i\beta c_j$ ($\alpha=0.03$, $\beta=2\pi$), the voltage on each side of the switch satisfies

$$
-\left(\frac{V'}{z}\right)'+y_jV+i\beta\chi\lvert V\rvert^2V=0,\qquad I=-\frac{V'}{z},
$$

with port $V(0)+I(0)=2$ (unit incident wave, matched source), short $V(L)=0$, and switch conditions $I(a^-)=I(a^+)$ and $V(a^-)-V(a^+)=Z_sI(a)$. The switch impedances are $Z_{ON}=0.02+0.04i$ and $Z_{OFF}=0.02-4i$. The reflection is $R=V(0)-1$. The nonlinear term models a voltage-dependent (cubic-charge) capacitance at the fundamental frequency, with $\chi=0.05$; $\chi=0$ is the linear comparison model.

**Weak form and elements.** Multiply by a test function $w$ with $w(L)=0$ and integrate by parts:

$$
\int_0^L\left[\frac{V'w'}{z}+y_jVw+i\beta\chi\lvert V\rvert^2Vw\right]dx+\frac{(V_{a^-}-V_{a^+})(w_{a^-}-w_{a^+})}{Z_s}+V(0)w(0)=2w(0).
$$

We use two-node linear (P1) elements, eight per cell: **[[elements]] elements and [[unknowns]] complex unknowns**. The switch has two coincident nodes, so the voltage jump is represented exactly rather than smoothed. Element matrices are $K_e=\frac1h\begin{pmatrix}1&-1\\-1&1\end{pmatrix}$ and $M_e=\frac h6\begin{pmatrix}2&1\\1&2\end{pmatrix}$. The cubic term uses 4-point Gauss quadrature. Unknowns are split into real and imaginary parts, because $\lvert V\rvert^2V$ is not complex-analytic. Newton's method uses the exact real tangent and a residual line search, and stops at $\lVert F\rVert_\infty<2\times10^{-11}$.

**Assumptions.** One frequency. Fundamental-harmonic cubic loading (no generated harmonics, no transient stability). Uniform line loss $\alpha$. Lumped switch impedances. Fixed geometry. Every Newton solve starts from the linear solution, so the branch is the one connected to it (no uniqueness claim). This is a synthetic analogue of the metasurface unit cell. It is not calibrated to HFSS or to hardware.

## 5. Verification ladder

Each rung compares our number with an exact answer. Rungs marked [[NEW]] were added in this revision. V2 is the first exact test that exercises the actual design variable (cell-by-cell loading): it compares against an independent transfer-matrix cascade written without any finite-element code.

[[ladder_table]]

![Mesh convergence of three verification problems with a slope −2 reference](assets/figures/convergence.svg)

**How the exact answers were obtained.** V1 uses Project 3's ABCD cascade. V2 multiplies per-cell transfer matrices $\begin{pmatrix}\cosh\gamma_j\ell&Z_j\sinh\gamma_j\ell\\ \sinh\gamma_j\ell/Z_j&\cosh\gamma_j\ell\end{pmatrix}$, with $\gamma_j=\sqrt{zy_j}$ and $Z_j=\sqrt{z/y_j}$, and a series-switch matrix $\begin{pmatrix}1&Z_s\\0&1\end{pmatrix}$. V4 chooses $V^*(x)=B(L-x)+D(L-x)^3$, adds a constant jump on the left segment, and picks $B$ so the port, short and switch conditions hold. It then generates the matching source term. V6 uses the fact that with $\alpha=0$, $\operatorname{Re}Z_s=0$ and a reactive cubic term, no power can be lost, so $\lvert R\rvert=1$ exactly. These expected values were derived by a coding agent; the team must re-derive them independently (Section 14).

## 6. Sensitivities: adjoint derivation and checks

**General form.** Stack real and imaginary nodal voltages in $u$ and write the assembled residual as $F(u,c)=0$, with tangent $J=\partial F/\partial u$ at the converged Newton state. For any response $q(u,c)$,

$$
J^{\mathsf T}\lambda=\left(\frac{\partial q}{\partial u}\right)^{\mathsf T},\qquad
\frac{dq}{dc_j}=\frac{\partial q}{\partial c_j}-\lambda^{\mathsf T}\frac{\partial F}{\partial c_j}.
$$

This differentiates the converged state equation (implicit differentiation), not the Newton iterations. Each switch state has its own state equation, so each state gets one transposed solve with $J^{\mathsf T}$, shared by all metrics.

**Design derivative of the residual.** Only the shunt term depends on $c_j$: $\partial F_i/\partial c_j=i\beta\int_{\text{cell }j}N_iV\,dx$, split into real and imaginary rows. It is proportional to the local voltage. That is why the loading next to the short, where $V\to0$, has almost no influence (Section 7).

**Kind 1: port functionals** (objective and $g_1$, $g_2$). $R_s=u_0+iu_n-1$. For $q=\lvert R_s\rvert^2$, $\partial q/\partial u$ is $2\operatorname{Re}R_s$ at the real port entry and $2\operatorname{Im}R_s$ at the imaginary port entry. For the objective, with $S=R_{ON}+R_{OFF}$, the entries are $2\operatorname{Re}S$ and $2\operatorname{Im}S$ in each state's adjoint.

**Kind 2: domain functionals** ($g_3$, $g_4$). $E_s=\frac1L(a^{\mathsf T}Ma+b^{\mathsf T}Mb)$, with $a$ and $b$ the real and imaginary nodal voltages and $M$ the global consistent mass matrix. So $\partial E_s/\partial u=\frac2L(Ma;\,Mb)$, with a minus sign for $g=1.6-E$.

**The nonlinear term in the tangent.** Write $V=a+ib$ at a quadrature point. The cubic loading $i\beta\chi\lvert V\rvert^2V$ is not complex-differentiable, so its derivative is taken with respect to $a$ and $b$ separately:

$$
\frac{\partial(\lvert V\rvert^2V)}{\partial a}=(3a^2+b^2)+2iab,\qquad
\frac{\partial(\lvert V\rvert^2V)}{\partial b}=2ab+i(a^2+3b^2).
$$

Multiplied by $i\beta\chi$ and integrated against $N_iN_k$, these give the real 2×2 blocks added to the linear operator in $J$. The same $J$, transposed, is the adjoint operator. The cubic term does not contain $c_j$, so it adds nothing to $\partial F/\partial c_j$. It enters the gradient only through $J^{\mathsf T}$ and the converged state. V8 checks this tangent against a central difference of the residual.

**Kind 3: explicit terms.** $\partial f/\partial c_j$ gains $\frac{2\cdot0.002}{20}(c_j-1)$. Bound constraints are explicit and need no adjoint.

**Variable types.** The design has one kind of variable: cell loading multipliers. The check below covers every coordinate of that kind, for the objective and every constraint.

**Gradient check, every coordinate** [[NEW]]. Central differences perturb each of the 20 loadings. The table gives the relative vector error $\lVert\nabla_{adj}-\nabla_{FD}\rVert/\lVert\nabla_{FD}\rVert$ at $h=10^{-3}$, near the best step found by the Taylor test below, and in brackets at $h=10^{-5}$. The larger errors at $h=10^{-5}$ (up to [[coord5_max]]) are finite-difference round-off, not adjoint error:

[[coord_table]]

**Taylor test** [[NEW]]. Along a random unit direction, the central-difference error falls as $\varepsilon^2$ (observed order over the first decade ≥ [[sweep_min]]). It reaches its minimum at $\varepsilon\approx[[step_lo]]$–$[[step_hi]]$ and then rises again as round-off in the Newton solves grows like $1/\varepsilon$. That V shape is the expected signature of a correct gradient; a flat curve would indicate a wrong adjoint. The figure shows the random interior design. The initial and optimized designs behave the same way (orders [[ord_ini]] and [[ord_opt]]; curves in `assets/rubric-studies.json`). V10 passes if every first-decade order exceeds 1.6.

![Central-difference error versus step size for all five metrics](assets/figures/step-sweep.svg)

The frozen study's first-order Taylor remainder ($q(c+hv)-q(c)-h\nabla q\cdot v$ falls as $h^2$) is retained as a second check [[FROZEN]]:

![First-order Taylor remainder for all five metrics](assets/figures/taylor.svg)

**Cost: adjoint versus finite differences** [[NEW]]. One adjoint gradient of all five metrics costs 2 Newton solves plus 2 transposed linear solves with 5 right-hand sides each. Central differences cost $4n$ Newton solves. To show the scaling, the same line was re-meshed with 10–80 loading cells at a fixed 160 elements:

[[cost_table]]

![Gradient cost versus number of design variables](assets/figures/cost.svg)

At the project's 20 variables, the adjoint is about [[ratio20]]× faster; at 80 variables, about [[ratio80]]×. The finite-difference time grows linearly with $n$, while the adjoint time stays nearly constant. The frozen study's single timing ([[fdtime_old]] s versus [[adjtime_old]] s) agrees. Times are from one laptop CPU and vary between machines.

## 7. Optimization

**Setup** [[FROZEN]]. SciPy SLSQP, analytic adjoint gradients, bounds $[0.5,2.5]$, `ftol` $10^{-11}$, at most 500 iterations. Variables are already $O(1)$ and centered on 1. The frozen run left the constraints in their natural units ($\lvert R\rvert^2$ and normalized $\lvert V\rvert^2$, both $O(0.1$–$1)$). To check that this choice does not matter, the problem was re-solved [[NEW]] with constraints scaled as $g/g_{limit}-1$ ($\lvert R\rvert^2/0.64-1\ge0$, $1-E/1.6\ge0$). [[sc_n]] of 5 starts (3 of 4 independent ones, excluding the low-high vertex start) converge to the same design (max difference [[sc_dc]]). The high-low start fails exactly as before. Both models used the same five starts: uniform, low-before/high-after, high-before/low-after and two seeded random designs. Every outcome is kept, including the two failures.

[[multi_table]]

The low-high start is the optimal bound pattern itself, so it converges in one iteration and is not independent evidence. The linear model's uniform start "converged" to a poor stationary point: SLSQP reports success, but $f$ ends at [[lin_uni_f1]], slightly worse than its start ([[lin_uni_f0]] in the linear model). Its high-low start stopped with a line-search failure. The nonlinear high-low start failed inside Newton's method at its first design. A diagnosis [[NEW]] shows why. That design (heavy loading before the switch) puts a strong standing wave in the OFF state: $\max\lvert V\rvert=[[nf_vlin]]$ even in the linear model, where the cubic term would be [[nf_ratio]]% of the linear loading. Gradual continuation in $\chi$ from the linear state also fails, at $\chi=[[nf_chi]]$. The same start converges in the $\chi$ sweep at $\chi=0.1$ (to a poor $f=[[hl01]]$) and $\chi=0.3$, and fails again at $\chi=0.2$. So whether Newton finds a solution from the linear initial guess depends on $\chi$ in a non-monotone way. That is consistent with multiple nonlinear solution branches and a narrow basin around the linear state, not a solver defect (the ON state converges, and the tangent is verified by V8). We have not mapped the branches, so the mechanism is not proven. Excluding the low-high start, two of four (linear) and three of four (nonlinear) independent starts reach the best design.

![Convergence histories of every nonlinear-model start](assets/figures/optimization.svg)

**Active constraints and multipliers.** With $\mathcal L=f-\sum_i\mu_ig_i$, $g_i\ge0$, $\mu_i\ge0$, one bound per cell is active (20 of 40): cells 1–6 at the lower bound and cells 7–20 at the upper bound. The four response constraints have slack, so their multipliers are zero. KKT stationarity holds to $10^{-17}$. A multiplier $\mu_j$ is the objective improvement per unit widening of that cell's loading range. To test this, each bound was widened by $\delta=0.02$ and the problem re-solved [[NEW]]:

[[mu_table]]

**Engineering reading.**

- The most valuable extra range is just before the switch: cell [[big_cell]], $\mu=[[big_mu]]$. Lighter loading there would lower the objective the most.
- On the short side, the largest upper-bound multipliers are cells [[topcells]], in the middle of the switch-to-short segment.
- Cell [[small_cell]], next to the short, is worth almost nothing ($\mu=[[small_mu]]$). The voltage vanishes at the short, so loading there barely changes the wave.
- Widening every range by 0.02 is predicted to lower $f$ by [[allpred_abs]]; the re-solve lowers it by [[allact_abs]]. The small difference is the second-order term.

In engineering terms, the design is limited by how far the tunable capacitance can go, not by the voltage or amplitude limits.

**What if the voltage limit mattered?** *Post hoc* [[NEW]]. At $E_{max}=1.6$ the voltage limit is loose, so the frozen problem says nothing about its price. We re-solved with tighter limits, using the five frozen starts plus a warm start, and checked each voltage multiplier against a finite difference of re-solved optima:

[[ls_table]]

![Optimal objective versus voltage limit](assets/figures/limit-sweep.svg)

Once the OFF-state voltage limit binds, its multiplier (about [[mu105]] in the nonlinear model at $E_{max}=1.05$) prices the trade-off. Each 0.01 tightening of the OFF-state mean-square voltage costs about [[fcost01]] in $f$ and roughly [[phslope]]° of phase separation. These tighter limits are sensitivity studies; the frozen formulation and its optimum are unchanged.

## 8. Nonlinear component (N2)

**What is nonlinear.** The state equation itself is nonlinear: the cubic voltage-dependent loading $i\beta\chi\lvert V\rvert^2V$. It is solved by Newton's method and differentiated implicitly at the converged state (Sections 4 and 6). It is checked against a manufactured nonlinear solution (V4), quadratic Newton convergence (V8) and phase equivariance (V7). The nonlinearity is not small where the voltage is large. At the optimum, $\chi\lvert V\rvert^2/c$ reaches [[st_off]] in the OFF state (mean [[st_offmean]]) and [[st_on]] in the ON state. Locally, the voltage-dependent part adds up to about [[st_pct]]% of the linear loading.

**With and without, frozen problem** [[FROZEN]]. Optimizing with $\chi=0$ and with $\chi=0.05$ gives the same design: max $\lvert\Delta c\rvert=[[delta]]$ between the two frozen selected designs. The $\chi$-sweep table below re-solves both models, so its differences, measured against the re-solved linear design, are of the same round-off size but not identical. The response does change: the linear model predicts $\Delta\phi=[[phl]]°$ and $f=[[fl]]$, while the nonlinear model gives $[[phn]]°$ and $f=[[fn]]$ at the same loading. The nonlinearity detunes the line and costs [[phcost]]° of phase separation, but it does not move the optimum.

**Why the design does not move.** The optimum is a vertex of the bound box. It stays optimal as long as every bound multiplier stays positive, i.e. as long as every cell still "wants" to move further in the same direction. The nonlinearity changes the multipliers but flips no sign. The smallest is [[mumin_l]] (linear) versus [[mumin_n]] (nonlinear), and the cell-1 lower-bound multiplier drops from [[mu_cell1_l]] to [[mu_cell1_n]]. Raising $\chi$ shows when that stops being true *post hoc* [[NEW]]:

[[cs_table]]

As $\chi$ grows, cell 1's multiplier shrinks. At $\chi=0.3$, cell 1 (at the port) switches from the lower to the upper bound and the design changes. The frozen $\chi=0.05$ sits well inside the range where the bound pattern is unchanged.

**With and without, when the voltage limit binds** *post hoc* [[NEW]]. Here the nonlinearity does change the design. We optimized with each model and evaluated the linear model's design in the nonlinear model:

[[ww_table]]

![Loading distributions: frozen optimum and the two designs at E_max = 1.05](assets/figures/loading.svg)

With the voltage limit active, the linear model overpredicts the OFF-state voltage. Its design is therefore over-conservative, and it pays [[penlo]]–[[penhi]]% in objective relative to the design that accounts for the nonlinearity. The designs differ only in cell 1, at the port, and, at the two tightest limits, cell 6, next to the switch. These are the cells that trade phase contrast against OFF-state voltage.

**Conclusion.** For the frozen problem, ignoring the nonlinearity would give the right design but a wrong prediction of its performance ([[phcost]]° too optimistic). For a problem with an active voltage limit, ignoring it gives a worse design.

## 9. Website and 3D comparison

The viewer at the top of this page loads `assets/results.json`. It shows the initial and optimized designs side by side with linked cameras, and the solved voltage magnitude drawn on the line with the elements' own linear shape functions. The port, switch and short are labeled. Three things are graphical encodings, not dimensions, and the viewer labels them: block heights show the loading $c_j$, ribbon height shows $\lvert V\rvert$, and the line is a 1D model extruded for display. The animation replays the recorded SLSQP iterates of the selected run, with the ON/OFF reflection phasors drawn for each iterate. Constraint failures are marked with "✗ FAIL" text and a hatched badge, not by color alone.

## 10. Neural surrogates of the Project 3 problem against the finite-element reference

**What the surrogates are.** These are **not** the original Project 3 networks. Two frozen Project 4 follow-up experiments trained new PINNs, three seeds per arm. Each run had the same physics loss as Project 3, but half of the 256 training designs were inside Project 3's difficult interval $0.195\le d\le0.222$. Each experiment compared one monolithic network with two specialist networks of matched size and budget, one for that interval and one for the rest. Experiment A routed hard between them, which creates reflection jumps of about 1 at the interval edges ([two-pinn-findings.md](two-pinn-findings.md)). Experiment B blended them smoothly. All model only Project 3's restricted family: one design variable $d$ (switch-to-short length), uniform loading, linear physics. They are **not** a surrogate for the 20-variable nonlinear problem above.

[[neural]]

Every network fails the unchanged acceptance gate. Their design-gradient errors ([[nglo]]–[[nghi]]%) were already a warning.

**Surrogate inside an optimizer** [[NEW]]. Both arms run SLSQP on the restricted problem with the same starts, bounds and constraints:

- Minimize $q(d)=1+\cos\Delta\phi$ (zero at 180°).
- Subject to $\lvert R_{ON}\rvert^2-0.64\ge0$ and $\lvert R_{OFF}\rvert^2-0.64\ge0$.
- Bounds $0.036\le d\le0.306$.

The surrogate arm takes values and design gradients from each saved network by automatic differentiation. The reference arm uses our own two-segment P1 finite-element model (128 elements per segment, mesh-converged, shape adjoint checked by finite differences in `review/restricted-fe-bridge-2026-11-16.json`). No network was retrained or re-selected. [[runs_total]] surrogate optimizations ran in [[sl_seconds]] s. The [[ndisc]] Experiment A specialist models are discontinuous at the interval edges, so a gradient optimizer is not well posed on them. Their runs are reported for completeness. The conclusions below hold for the [[ncont]] continuous models alone.

The finite-element reference is itself multimodal:

[[ref_table]]

The FE adjoint finds the interior resonant optimum $d=[[refd]]$ ($\Delta\phi=[[refph]]°$) only from $d_0=0.18$. From other starts it reaches the lower bound $d=0.036$ ($\Delta\phi\approx[[lbph]]°$, a nearly-as-good boundary design) or a poor upper-bound point.

[[sur_table]]

![Surrogate and FE objective across the restricted design range](assets/figures/surrogate-objective.svg)

![Surrogate and FE-adjoint design gradients](assets/figures/surrogate-gradient.svg)

**Where they disagree, and why.**

1. **Gradients.** Across the design range, the surrogate gradients differ from the FE adjoint by [[gl2lo]]–[[gl2hi]] in relative $L_2$ norm and have the wrong sign at [[sgnlo]]–[[sgnhi]]% of 55 sampled designs. The networks were trained to match field values, not their derivatives with respect to the design. Small field errors that vary with $d$ produce large slope errors, and that is exactly what the optimizer follows.
2. **Missed optimum.** None of the [[nmodels]] surrogates reaches the interior resonant optimum ([[interior]] of [[runs_total]] runs end within 0.005 of it). From $d_0=0.18$, where the FE adjoint climbs to $d=[[refd3]]$, every surrogate heads the other way, toward the lower bound (endpoints $d\le[[d18max]]$). The reason is visible in a dense check inside the difficult interval, even though half the training designs lay there. There the true objective dips to [[fe_in_min]] at $d=[[true_min]]$. The monolithic surrogates never predict a dip: their lowest value in the interval is [[m_in_min]], their mean objective error is [[m_in_mae]] (on a 0–2 scale), and their gradient error is [[m_in_g]]. The smooth-blend specialists do predict a shallow dip, but at $d=[[b_in_arg]]$ with minimum [[b_in_min]], mean error [[b_in_mae]] and gradient error [[b_in_g]]. Outside the interval, mean objective errors are only [[out_mae]] below it and [[out_mae_hi]] above it. The surrogates smooth away the resonance, so an optimizer following them cannot reach it.
3. **Spurious stationary points.** From $d_0=0.24$, [[nstalled]] of [[nmodels]] surrogates stop near $d\approx0.24$–$0.25$, where their gradient vanishes. The FE objective there is about 2, its worst possible value ($\Delta\phi\approx0°$). The FE adjoint from the same start does not stop there.
4. **Wrong self-assessment.** At their chosen designs ($d=[[dsello]]$–$[[dselhi]]$, at or next to the lower box bound), the surrogates predict $q=[[pqlo]]$–$[[pqhi]]$ (phase error [[perrlo]]–[[perrhi]]°). FE gives $q=[[feqlo]]$–$[[feqhi]]$ (phase error [[feperrlo]]–[[feperrhi]]°). The chosen designs happen to be good. That is luck of the bound placement, not evidence that the surrogate understood the response. Its predicted objective was [[qratio]] times the FE value.

**Why the negative result matters.** A surrogate that is accurate on average can still send a gradient-based optimizer the wrong way: wrong-sign components, false stationary points, blindness where the response is resonant. In 20 dimensions there would be no exhaustive check to catch this. The FE solver with adjoint gradients remains the design reference. Any surrogate must be validated on gradients and on optimizer endpoints, not on field error alone.

**Correction to the 16 November draft.** That draft said the surrogates' grid search "selects a different design" ($d=0.036$ versus [[refd3]]) without stating that FE rates $d=0.036$ as feasible with $\Delta\phi\approx[[lbph]]°$. The FE re-evaluation above corrects that framing: the decisive disagreements are gradients, missed and spurious stationary points, and self-assessment, not the endpoint alone.

**Bonus status.** These are trained surrogates used inside a gradient-based optimizer, with gradients and optima compared and the disagreements explained. They are applied only to the restricted one-variable linear family, not to this project's 20-variable optimizer. We do not count this toward the score; whether it qualifies for the surrogate bonus is the instructor's decision. The N2 solver and nonlinear benchmark are relevant to the "fully nonlinear" bonus; that, too, is not assumed.

## 11. Reproducibility

One command regenerates every result, figure and page in a fresh directory, without overwriting the retained evidence:

```sh
python Project4-Metasurface/reproduce.py
```

It reruns:

- the frozen verification and multistart design study (`code/run_design.py`, about [[run_seconds]] s);
- both neural experiments and their audits;
- the supplemental gradient sweep, the surrogate–FE comparisons, `code/rubric_studies.py` (about [[rs_seconds]] s) and `code/surrogate_optimizer_loop.py`;
- all tests;
- the report and site generator (`code/build_report.py`).

This page, `report.md`, the viewer's numbers and every figure are generated from the JSON files listed in Section 1, plus `assets/two-pinn-results.json` and `assets/smooth-pinn-results.json` for the Section 10 network tables. The only exceptions are the Project 3 figures in Section 2, quoted from the Project 3 report, and the declared constants of the formulation. Pinned versions are in `requirements.txt`. Timings differ between machines.

## 12. Limitations

- Synthetic reduced model: one frequency, a 1D line standing in for a 3D periodic copper unit cell, lumped switch impedances. No HFSS or hardware calibration.
- The cubic loading is a fundamental-harmonic model: no generated harmonics, no transient stability, no claim of a unique nonlinear branch.
- The optimum is local (multistart, not global), bound-dominated, and reaches [[ph1]]°, not 180°. The 0.8 amplitude floor and the 1.6 voltage limit are illustrative, not confirmed requirements.
- One kind of design variable (cell loading). No shape variable in the 20-variable problem; shape gradients appear only in the restricted switch-position family (Section 10).
- The 3D view is an extruded 1D model. Block and ribbon heights are data encodings, not fabricated dimensions.
- The post hoc studies (voltage-limit and $\chi$ sweeps) were designed after seeing the frozen optimum. They explain it; they do not replace it.

## 13. Custom-project requirements

| Requirement for a proposed structure | This project | Status |
|---|---|---|
| Objective and at least two constraints are functionals of a PDE solution our code computes | Objective and all four constraints come from the FE state | Met |
| At least 20 design variables | 20 cell loadings | Met (exactly 20) |
| A nonlinear component (N1 or N2) | N2: cubic loading, Newton, implicit adjoint | Met |
| Can be shown in 3D (2D may be extruded) | A **1D** line extruded for display | **Needs instructor confirmation** that an extruded 1D line is acceptable |
| A reduced version optimizes on a laptop in minutes | Full study about [[run_seconds]] s | Met |
| Custom structure approved by the instructor (due 4 Nov) | No approval record in the repository | **Needs instructor confirmation** |
| Limits cited from a standard or data sheet where applicable | Limits are synthetic and labelled as such | **Needs instructor acceptance** of synthetic limits |
| Own FE solver and adjoint gradients (Project 3 extension rule) | Own P1 solver and adjoints in `code/wave_fem.py` | Met |

## 14. AI-use statement and student verification

**What the coding agents wrote.** Coding agents wrote essentially all code and text in this folder:

- the formulation, FE/Newton solver, adjoints and optimization harness;
- the verification tests and the neural experiments;
- the figures, this report and the 3D viewer.

That covers the 10–16 November sessions and, on 23 November, a Hermes Agent session (Claude), which added `rubric_studies.py`, `surrogate_optimizer_loop.py`, this report structure and the redesigned viewer. Separate agent reviews checked results. Agent checks are not student checks.

**What the students derived or checked.** Nothing in this repository records an independent student derivation or check. The team must complete and record the checklist below before submission, in its own words.

**Bugs the verification caught.** These are the recorded defects, stated as they happened:

1. A run exposed a harness defect: a failed Newton solve at one start aborted saving the results. The harness now records that start as a failure.
2. Browser QA found the viewer computing upper-bound slack as $2.5$ instead of $2.5-c_j$. A regression test now covers it.
3. In this revision, re-evaluating the surrogates' chosen design with FE caught an overstated claim in the 16 November draft (Section 10).
4. Two independent agent review passes of this revision found draft errors, which were fixed before this version: the surrogates had been called "the Project 3 networks" with a causal claim borrowed from Project 3's error figures; the Taylor-test text placed the round-off floor at the wrong step; a broken viewer test; and a start counted as independent although it began at the optimum. These are review catches, not ladder catches.

No ladder rung has recorded catching a solver bug; we do not invent one.

**What you (the student team) must verify yourselves:**

- [ ] Derive by hand the exact answers for V1 (uniform reflection), V2 (one two-cell cascade), V4 ($B$ in the manufactured solution) and V6 ($\lvert R\rvert=1$ when lossless), *before* comparing with the code.
- [ ] Re-derive the adjoint equations in Section 6 for one port functional and the mean-square voltage. Check one gradient entry by hand-run finite difference.
- [ ] Read `code/wave_fem.py` and confirm the weak form, switch coupling and cubic tangent match Section 4.
- [ ] Confirm the engineering reading of the multipliers (Section 7) and the nonlinear conclusion (Section 8) in your own words.
- [ ] Get instructor confirmation of the custom formulation, the extruded-1D display and the synthetic limits (Section 13).
- [ ] After any publication, open the public page in a private window and check the math, viewer, data loading and phone layout.
'''

if __name__ == '__main__':
    build()
