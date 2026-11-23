# Two PINNs improve some errors but do not pass the design gate

The two-specialist experiment improves reflection and physical-voltage errors in all three paired seeds. It does not produce a dependable design surrogate. Every model fails the frozen acceptance gate, and the hard switch between specialists creates new discontinuities. Keep the conventional solver for this analogue and the separate nonlinear FE/adjoint model for Project 4's optimization core.

## What was actually tested

The user's proposed spatial split is sensible when one neural field must cross a physical jump. Project 3 already avoids that problem. Its finite switch is represented through its interface conditions, its upstream segment is propagated analytically, and its neural model learns only the normalized right-segment field. The known physical jump does not lie inside that learned spatial domain.

The remaining steep response is in the parameter d, the right-segment length. Historical P3 studies identified the difficult interval [0.195, 0.222]. We therefore tested parameter-domain specialists rather than unnecessarily replacing an exact upstream solution with a second neural approximation:

- Monolithic arm: one 3-64-64-4 tanh network, 4,676 parameters.
- Two-specialist arm: two 3-44-44-4 tanh networks, 4,672 total parameters. One covers d in [0.195, 0.222], the other covers its complement. Inputs to the narrow specialist rescale that interval to [-1,1]. The complementary specialist retains the full-domain normalization.
- Both predict real and imaginary voltage and current from local right coordinate, d, and switch state. The original physical equations, loss, synthetic impedances and lossy propagation remain unchanged.
- The loss is the mean of squared complex residuals for V_xi+gamma*d*I, I_xi+gamma*d*V, the driven interface divided by four, and the short-circuit voltage. No reference labels enter either training objective.

This is a joint intervention in specialization and input scaling, not an isolated causal test of decomposition. It is not an XPINN with interface continuity penalties, an overlapping mixture, or a proof that every two-network architecture fails. No post-result repair or wider search was performed.

## Frozen evidence and fair-budget limits

The protocol was written at 2026-11-10 18:47:11 UTC, before any fitting or new validation/final reference access. Its SHA-256 is `04b4fb04d5abdf79aef5f6d6190ea5af8733c8ffe6972a5987af2710ae7cb0f8`. All six terminal weight sets were sealed before evaluating new validation/final references. Their combined hash is `3f86bacad58826f0dad5855f77e0c169e62b04e5d3bde74a136b8c0aacb3eb2f`.

There are 256 training, 128 validation and 320 final geometries. Half of each set lies in the difficult interval. New d values are separated from one another and all d values in historical P3 frozen protocols by at least 1e-8. This is fresh stratified interpolation evidence, not a new untouched problem or a blocked-extrapolation test. Close training neighbors are permitted. Historical locations informed the experiment; historical cohorts are not presented as new final evidence.

Each arm uses seeds 0/1/2, 4,000 Adam updates, cosine learning rate 0.002 to 0.0002, float64 and one CPU thread. Every update samples 16 geometries per region, four spatial points each, and both states. Paired arms receive the same geometry/spatial stream. Each fit uses 1,024,000 interior point-state residual evaluations plus 2,048,000 endpoint point-state evaluations. Both specialist parameter blocks are updated each iteration. We report every terminal model; validation does not select a seed or checkpoint.

Total capacity differs by four parameters, or 0.086%. Updates and points match exactly; FLOPs and runtime do not. A single active network's affine layers use 4,544 multiplications per point in the monolithic arm and 2,244 in the specialist arm, excluding biases, nonlinearities, derivatives and routing. A specialist only handles half the training points. This study is not an equal-FLOP claim. Routing and extra graph overhead can outweigh the smaller matrices. Initial weights cannot be paired identically across different architectures.

## Fresh final results

Reflection error is the 95th percentile over designs of the maximum two-state absolute complex error. Voltage error integrates the physical two-segment field in physical distance, including the analytic left field and the right field's incident-amplitude scaling, then takes the median across state cases.

| Arm | Seed | Fit seconds | Reflection p95 | Physical voltage median relative L2 | Feasible retained |
|---|---:|---:|---:|---:|---:|
| Monolithic | 0 | 17.85 | 1.4908 | 5.48% | 0/24 |
| Two specialists | 0 | 23.86 | 1.0908 | 4.17% | 2/24 |
| Monolithic | 1 | 17.71 | 1.4756 | 4.61% | 7/24 |
| Two specialists | 1 | 24.11 | 1.1403 | 3.87% | 10/24 |
| Monolithic | 2 | 17.78 | 1.4112 | 4.53% | 0/24 |
| Two specialists | 2 | 23.99 | 1.1730 | 4.46% | 0/24 |

All arms have zero false feasible predictions among 296 infeasible cases. The physical thresholds stay at phase separation >=165 degrees and minimum reflection magnitude >=0.8. The acceptance gate requires reflection p95 <=0.03, median voltage error <=0.05, sensitivity and specificity >=0.9, with both classes present. Every final and validation gate fails.

Median field error hides a poor tail. Specialist voltage-error p95 remains 72.7%-76.0%; monolithic p95 is 84.3%-89.3%. Some predicted reflection magnitudes exceed one, despite the passive reference. The results support a modest error reduction under this budget, not reliable screening. Three seeds are too few for broad statistical claims.

## Gradients, routing and a restricted design audit

At fixed L=0.36, the smooth objective is 1+Re(R_off*conj(R_on))/(|R_off||R_on|), with a target of zero at 180 degrees. Autodifferentiation through each fitted model agrees with its finite-difference derivative to at worst 1.23e-7 on 293 applicable final geometries. That checks implementation, not physical gradient accuracy. Relative L2 errors against conventional objective gradients are 95.1%-95.6% for monolithic models and 85.6%-90.7% for specialists. Halving the reference difference step changes its gradient by only 7.60e-9 in relative L2.

Hard routing creates reflection jumps of 1.006-1.028 at d=0.195 and 0.881-0.921 at d=0.222. Monolithic differences across the same 2e-9 interval are about 2.5e-8. Specialist one-sided reflection-derivative differences are 8.26-12.36. The true physical family is smooth at these artificial boundaries. A classical derivative is not defined across the specialist jumps. These models should not be dropped into a gradient optimizer as globally differentiable surrogates.

A separately declared 10,001-point constrained grid audit at L=0.36 searches d in [0.036,0.306], using predicted minimum magnitude >=0.8. This is a restricted one-dimensional grid comparison, not the Project 4 FE adjoint optimizer or a continuous global certificate. The conventional grid optimum is d=0.208422, phase separation 179.9405 degrees, minimum magnitude 0.800510, and objective 5.3901e-7. Five surrogate runs select d=0.036, which is reference-feasible with phase 179.4663 degrees and magnitude 0.942854. Monolithic seed 2 selects d=0.040914, also reference-feasible, with phase 176.2454 degrees. Thus this particular search does find feasible alternatives, but it does not recover the conventional grid optimum or establish reliable gradients. The grid was not used to fit or select a model.

## Cost and checks

The conventional comparator is the vectorized, nonsingular sinh/cosh expression, not a Python loop over scalar solves. Twenty-one warmed repeats measure two-state reflection-only evaluation; neural inference uses no unused spatial derivatives. Median timings are:

| Designs per batch | Conventional | Monolithic range | Two-specialist range |
|---:|---:|---:|---:|
| 1 | 16.5 microseconds | 247.9-252.4 microseconds | 281.3-356.9 microseconds |
| 320 | 58.3 microseconds | 972.9-1076.0 microseconds | 1175.3-1188.9 microseconds |
| 10,001 | 2.06 milliseconds | 25.61-26.31 milliseconds | 19.42-20.65 milliseconds |

Training cost is additional. Neither arm has a positive inference-only break-even query count against this baseline at the measured batch sizes. Fit timers exclude subsequent reference evaluation. Timings describe this implementation on one CPU, with normal machine noise, not a controlled hardware comparison or an HFSS speedup.

The factorized baseline agrees with the independent P3 complex wave-system solve within 7.06e-15 across all 640 final states. Seven tests pass, covering capacity, analytic reference, spatial derivatives, design autodiff, thresholds, prospective separation/hashes, and independent NumPy forward replay of every saved final reflection. The result file retains all weights and per-design reflection/classification results. No student manual derivation, contribution, or review is asserted.

## Reproduce

From the repository root, use Python with NumPy and CPU PyTorch. The executed environment has NumPy and PyTorch versions recorded in the result JSON. No SciPy or runtime download is needed for this supporting study.

Run tests against the committed evidence:

```powershell
python -m unittest discover -s Project4-Metasurface/tests -p test_two_pinn.py -v
```

Reproduce fitting in a NEW folder so the original evidence is not overwritten:

```powershell
python Project4-Metasurface/code/two_pinn_study.py --output Project4-Metasurface/assets/two-pinn-reproduction --freeze-only
python Project4-Metasurface/code/two_pinn_study.py --output Project4-Metasurface/assets/two-pinn-reproduction
python Project4-Metasurface/code/two_pinn_audit.py --output Project4-Metasurface/assets/two-pinn-reproduction
```

The script refuses to overwrite completed results or run changed source against an existing freeze. Reproduction timing and timestamp hashes will differ. The supplementary audit only reads trained weights and writes derivative checks; it never changes the training plan.

Sources and artifacts: [P3 formulation](../Project3-Metasurface/report.md), [P3 hard-boundary results](../Project3-Metasurface/hard-boundary-findings.md), [P3 coverage/objective diagnosis](../Project3-Metasurface/gap-objective-findings.md), [frozen protocol](assets/two-pinn-protocol.json), [freeze receipt](assets/two-pinn-freeze-receipt.json), [checkpoint seal](assets/two-pinn-checkpoint-seal.json), [all results and weights](assets/two-pinn-results.json), [derivative audit](assets/two-pinn-derivative-audit.json), [experiment code](code/two_pinn_study.py), [audit code](code/two_pinn_audit.py), [tests](tests/test_two_pinn.py).

This synthetic single-frequency experiment supports the portfolio's investigation, not a hardware claim, a full-wave acceleration claim, fulfillment of the >=20-variable FE optimization requirement, or an automatic bonus-credit claim.

## Follow-on continuity repair

A second experiment addressed the hard-routing flaw with a differentiable logistic blend trained through the blended PDE residual. Six newly initialized fits used fresh training/validation/final designs, with the first experiment treated as historical. The smooth model removes the artificial jumps and reduces reflection p95 relative to its new matched monolithic control, but every gate still fails. Its physical objective-gradient error is 106%-109%, so smoothness does not establish gradient usefulness. All original evidence above remains unchanged. See [the complete smooth-blend follow-on](smooth-pinn-findings.md) for its frozen plan, all six results, exact budgets, continuity/gradient checks and reproduction commands.
