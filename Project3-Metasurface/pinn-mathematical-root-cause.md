# Why the PINN fails: a mathematical root-cause analysis

## Executive conclusion

The failure is not explained by an incorrect PDE, a sign error, or a network that is simply too small to represent the response. The central mathematical problem is:

> **The PINN loss becomes least sensitive to amplitude error exactly where the physical response becomes most sensitive to geometry.**

For the OFF state, the boundary-value problem has a nearby complex pole. Its reflection response changes with geometry like \(D^{-2}\), while the curvature of the physics loss in the corresponding amplitude direction collapses like \(D^2\). The loss also averages over geometry and contains no derivative or other physical coupling in the geometry direction. Consequently, a narrow resonant region can remain badly wrong even when the global residual appears small.

The resulting causal chain is

\[
\text{nearby complex pole}
\rightarrow \text{sharp response in }d
\rightarrow \text{flat residual-loss direction}
\rightarrow \text{sparse/absent parameter constraints}
\rightarrow \text{over-smoothed PINN response}.
\]

Finite optimization budget and conflicting gradients across geometry regions then compound the structural problem.

This analysis concerns the project's synthetic finite-switch transmission-line analogue. It is not a claim about measured hardware or every PINN.

## 1. Exact reduction of the boundary-value problem

Let

\[
g=\gamma d,
\qquad
D_s(d)=\sinh g+(1+z_s)\cosh g,
\]

where \(d\) is the right-segment length and \(z_s\) is the state-dependent switch impedance.

The normalized right-segment equations are

\[
V_\xi+\gamma d I=0,
\qquad
I_\xi+\gamma d V=0,
\]

with the terminal condition

\[
V(1)=0.
\]

Every field of the form

\[
V(\xi)=A(d,s)\sinh(g(1-\xi)),
\qquad
I(\xi)=A(d,s)\cosh(g(1-\xi))
\]

satisfies both interior differential equations and the terminal short for **any** amplitude function \(A(d,s)\). Only the driven port condition determines that amplitude:

\[
V(0)+(1+z_s)I(0)=2.
\]

Substitution gives

\[
D_s(d)A(d,s)=2,
\qquad
A_*(d,s)=\frac{2}{D_s(d)}.
\]

This reduction exposes an important fact: the interior PDE residuals and terminal residual do not constrain the solution amplitude. The amplitude is fixed only by the port residual.

## 2. The OFF state has a nearby complex pole

The zeros of \(D_s(d)\) satisfy

\[
e^{2\gamma d}=-\frac{z_s}{2+z_s}.
\]

For the retained OFF-state impedance

\[
z_{\mathrm{off}}=0.02-4i
\]

and propagation constant

\[
\gamma=0.03+2\pi i,
\]

the relevant complex root is

\[
d_p=0.2131363+0.0100549i.
\]

The pole is not on the real axis, so the physical solution remains finite. It is nevertheless close enough to the real geometry interval to create a narrow resonant response. Along the real axis,

\[
\min |D_{\mathrm{off}}|=0.267656
\]

near

\[
d=0.213136.
\]

The exact local reflection is

\[
r(d)=1-I(0)
=\frac{\sinh(\gamma d)+(z_s-1)\cosh(\gamma d)}
       {\sinh(\gamma d)+(z_s+1)\cosh(\gamma d)}.
\]

Differentiating and using \(\cosh^2 g-\sinh^2 g=1\) gives

\[
\boxed{r'(d)=\frac{2\gamma}{D_s(d)^2}},
\]

and

\[
\boxed{
r''(d)=
-\frac{4\gamma^2[\cosh(\gamma d)+(1+z_s)\sinh(\gamma d)]}
       {D_s(d)^3}
}.
\]

Therefore:

- fixed-geometry residual-to-output amplification scales approximately as \(1/|D|\);
- geometry sensitivity scales as \(1/|D|^2\);
- geometry curvature scales as \(1/|D|^3\).

At the OFF-state resonance,

\[
\frac{1}{|D|}=3.736,
\qquad
|r'(d)|=175.4,
\qquad
|r''(d)|\approx 3.49\times10^4.
\]

The fixed-\(d\) problem is finite and only moderately ill-conditioned, but the map from geometry to reflection is extremely sharp. This distinction is essential: the difficult object is the *parameterized solution manifold*, not merely one spatial solve.

## 3. The physics-loss Hessian collapses at the resonance

The retained port loss is

\[
\mathcal L_{\mathrm{port}}
=\frac14|D_sA-2|^2.
\]

Perturb the exact amplitude by \(A=A_*+\delta A\). Because \(D_sA_*=2\),

\[
\boxed{
\mathcal L_{\mathrm{PINN}}
=\frac{|D_s|^2}{4}|\delta A|^2
}.
\]

In real and imaginary amplitude coordinates, the corresponding Hessian is

\[
H_{\mathrm{physics}}=\frac{|D_s|^2}{2}I.
\]

At \(d=0.213136\),

\[
\lambda_{\mathrm{physics}}=0.03582.
\]

By comparison, direct field fitting gives

\[
\mathcal L_{\mathrm{data}}=W(d)|\delta A|^2,
\]

where the retained 17-point spatial grid gives

\[
W(0.213136)\approx1.00003.
\]

Thus

\[
\lambda_{\mathrm{data}}\approx2.00006
\]

and

\[
\frac{\lambda_{\mathrm{data}}}{\lambda_{\mathrm{physics}}}
\approx55.84.
\]

Direct field training penalizes the resonant amplitude error about 56 times more strongly than the physics loss. The factor-of-four normalization on the port residual contributes to this weakening, but the fundamental collapse is the \(|D|^2\) dependence.

This is the core mathematical mismatch:

\[
\underbrace{|r'(d)|}_{\text{required response sharpness}}
\propto |D|^{-2},
\qquad
\underbrace{\lambda_{\mathrm{physics}}}_{\text{loss sensitivity}}
\propto |D|^2.
\]

The target becomes harder precisely where the loss becomes flatter.

## 4. The physics objective does not identify behavior between geometry nodes

The PDE contains derivatives with respect to the spatial coordinate \(\xi\), but no derivative with respect to \(d\). Suppose residuals are enforced at \(d_1,\ldots,d_N\). For any smooth field perturbation \(w\), define

\[
\widetilde u(\xi,d)
=u_*(\xi,d)+p(d)w(\xi,d),
\qquad
p(d)=\prod_{j=1}^N(d-d_j).
\]

At every sampled geometry \(d_j\), \(p(d_j)=0\). Consequently, the perturbed field has exactly the same sampled values, spatial derivatives, PDE residuals, and boundary residuals as \(u_*\), while it may be arbitrarily wrong between the sampled geometries.

Shared neural-network weights supply only an implicit smoothness preference. They do not create a missing physical equation in the \(d\) direction.

The original protocol excluded the entire interval

\[
0.195\le d\le0.222
\]

from residual training. Behavior in that interval was therefore structurally unidentifiable from the empirical physics objective.

The covered follow-up inserted 16 equally spaced geometries in this interval. However, the exact feasible screening interval is only approximately

\[
0.2066825\le d\le0.2089350,
\]

with width

\[
0.0022525.
\]

Only one of the 16 covered training geometries lies inside that decision-critical interval.

## 5. A small mean loss does not control the resonant tail

The fully covered physics continuation attains the global objective

\[
L_{\mathrm{global}}=1.3445\times10^{-3}.
\]

But the critical block-OFF cases constitute only

\[
\frac{16}{256\times2}=3.125\%
\]

of the geometry/state tasks. Their observed mean residual loss is

\[
L_{\mathrm{block,OFF}}=0.02659.
\]

This is fully compatible with the small global mean. A small average permits a much larger conditional error on a narrow subset.

The verified residual transport relation has the form

\[
|\Delta R(d)|\le G(d)\eta(d),
\]

where \(\eta^2\) is the continuous counterpart of the physics loss. Near the resonance, \(G\approx5.52\), so the attained local loss permits

\[
|\Delta R|
\lesssim 5.52\sqrt{0.02659}
\approx0.90.
\]

The observed median training reflection error is about \(0.79\), consistent with this bound.

To conservatively guarantee reflection error below \(0.03\), the local residual would need to satisfy approximately

\[
\eta^2
\lesssim
\left(\frac{0.03}{5.52}\right)^2
=2.95\times10^{-5}.
\]

That is roughly 900 times below the attained block-OFF loss. Therefore, the apparently small global objective is not small in the norm or region that controls the screening decision.

## 6. The trained networks visibly smooth away the resonance

Dense evaluation across the blocked interval gives:

| Model | Median block \( |dr/dd| \) | Maximum block \( |dr/dd| \) | Median dense-block reflection error |
|---|---:|---:|---:|
| Exact response | 120.98 | 175.41 | 0 |
| Original Adam PINN | 4.50 | 4.58 | 1.367 |
| Covered Adam PINN | 4.38 | 4.45 | 1.355 |
| Physics L-BFGS continuation | 42.07 | 50.74 | 0.768 |
| Supervised L-BFGS continuation | 126.33 | 187.92 | 0.0244 |

The Adam-trained PINNs are almost flat in the geometry direction. L-BFGS recovers part of the sharp response, but not enough. The same architecture trained on direct fields reproduces the exact slope closely.

This rules out a simple value-expressivity ceiling: the network can represent the sharp geometry response. It does not, by itself, prove equal derivative or Sobolev expressivity under the physics objective. Indeed, the accurate supervised model has a larger physics residual than the physics-trained model because accurate values and accurate learned spatial derivatives are different approximation requirements.

## 7. Shared-network gradient conflict compounds the loss mismatch

A read-only diagnostic froze the first two hidden layers of the fully covered physics model and differentiated the exactly quadratic final-layer loss for four task groups. The results were:

| Task group | Sampling frequency | Mean loss | Final-layer gradient norm |
|---|---:|---:|---:|
| Block OFF | 3.125% | 0.02659 | 0.12925 |
| Block ON | 3.125% | 0.000217 | 0.04667 |
| Outside OFF | 46.875% | 0.000848 | 0.01979 |
| Outside ON | 46.875% | 0.000233 | 0.01797 |

The block-OFF and outside-OFF gradient cosine is

\[
-0.416.
\]

Thus these groups locally prefer opposing parameter updates. After weighting by their sampling frequencies, approximately 51% of the component-gradient magnitude cancels. At the saved endpoint, a global steepest-descent step restricted to the final-layer subspace would actually increase the block-OFF loss while reducing the easier majority-region loss.

This is a local diagnostic rather than a complete Hessian proof, but it directly demonstrates that the shared network is solving a conflicting multi-task optimization problem.

## 8. Why exact boundary enforcement does not fully repair the model

The near-flat amplitude direction explains an important part of the soft-penalty failure, but it is not the only remaining difficulty. The hard-boundary experiment makes the driven port and terminal short exact, yet still produces large interior and reflection errors.

Exact endpoint enforcement removes one error channel but changes the trial-function representation and transfers the approximation burden into the interior PDE residual. The residual budget confirms that both boundary and interior contributions are material. Therefore, changing one boundary weight or enforcing one endpoint cannot resolve the geometry-sampling, shared-representation, and finite-optimization problems by itself.

## 9. Root-cause hierarchy

The evidence supports the following hierarchy:

1. **Physical source:** the OFF-state determinant has a nearby complex zero, producing a narrow real-axis resonance.
2. **Parameter sensitivity:** reflection slope and curvature scale as \(D^{-2}\) and \(D^{-3}\).
3. **Loss conditioning:** physics-loss curvature in the critical amplitude direction collapses as \(D^2\).
4. **Parameter non-identifiability:** the equations constrain \(\xi\), not behavior between sampled \(d\) values.
5. **Norm mismatch:** an unweighted mean residual does not control a tail screening metric such as \(R_{95}\) or feasible-design sensitivity.
6. **Gradient conflict:** the narrow resonant task competes with the much larger smooth region in the shared network.
7. **Finite optimization:** the L-BFGS loss was still decreasing when the 1,200-call cap interrupted the final line search.

The most precise root-cause statement is therefore:

> **A nearby complex pole creates a sharply curved geometry-to-solution map, while the PINN residual norm develops a near-null amplitude direction and controls only a geometry-averaged spatial residual at discrete geometry nodes. Finite-budget optimization consequently selects an over-smoothed, low-average-loss solution with a large resonant tail error.**

This is stronger and more specific than attributing the result generically to spectral bias. Spectral bias is a plausible description of the observed smoothing, but the nearby pole, \(D^2\) Hessian collapse, missing parameter-space constraint, and mean-versus-tail mismatch are directly derived and numerically verified here.

## Supporting project material

- Physics loss implementation: [code/switched_surrogate.py](code/switched_surrogate.py#L117)
- Controlled sampling/objective results: [gap-objective-findings.md](gap-objective-findings.md)
- Optimizer control: [optimizer-control-findings.md](optimizer-control-findings.md)
- Exact-boundary control: [hard-boundary-findings.md](hard-boundary-findings.md)
- Signed residual attribution: [residual-budget-findings.md](residual-budget-findings.md)
- Residual-to-reflection derivation: [residual-error-identity.md](residual-error-identity.md)
- Full report: [report.md](report.md)

The saved-weight audit independently reproduces 22,800 recorded state outputs to approximately \(1.5\times10^{-14}\), supporting the numerical values used in this diagnosis. The analysis does not claim a successful neural remedy, hardware validation, or a universal PINN failure mechanism.
