# Speaker notes by slide group

These notes follow the 13 core slide groups in the 40-beat Light Mode presentation. Each group contains several presenter-controlled animation holds. Let each animation finish, use the matching cue below, then advance within the same group.

## Central message

This project asks whether a physics-informed neural network can reliably screen a simplified two-state metasurface analogue. The conventional model verifies the physical mechanism, but the neural models fail in a deliberately withheld response region. Optimizer choice, training objective and sampling support affect the error, yet no tested intervention produces a deployable model. For this analogue, retain the conventional solver.

## Terms to keep consistent

- The full transmission-line and switch system is the simplified metasurface unit-cell analogue.
- The switch is the state-dependent tunable element. It has fixed finite ON and OFF impedances.
- The upstream distance is `a`; the distance from the switch to the short is `d`; total length is `L = a + d`.
- A design is feasible under the illustrative screen when phase separation is at least 165 degrees and minimum reflection magnitude is at least 0.8.
- A deployment gate is a model-level acceptance test across a cohort. It differs from the feasibility rule for one design.

## Slide group 1: Switch position and current participation

We represent a reconfigurable metasurface unit cell with a transmission line containing a finite electronic switch. The switch changes between two impedances. At the first location, current is near zero, so changing states barely changes the reflected wave.

As the switch moves to a location with more current, the ON and OFF reflections separate. At the representative strong-response geometry, the conventional model gives about 179.69 degrees of phase separation while the minimum reflection magnitude remains about 0.801. The physical lesson is that the switch only has strong influence when current participates at its location.

**Animation cues:** First identify the nearly overlapping current and reflection states. After the switch moves, call attention to the growing phase separation and retain both phase and magnitude in the discussion.

## Slide group 2: Reduced metasurface analogue

The real research problem concerns a three-dimensional reconfigurable metasurface. Our model keeps one mechanism from that system: a finite state-dependent impedance interacting with current. It omits copper topology, radiation, materials, periodic-cell coupling and the mapping to actual hardware.

The switch becomes an interface between two line segments. Current remains continuous, while the finite impedance creates the voltage jump `V_left - V_right = z_s I`. The ON and OFF states use different fixed values of `z_s`. The input provides the drive, and the right end has the same short termination in both states.

The result is a small model that we can solve, differentiate and verify. It is a causal analogue, not a calibrated model of the researcher's physical unit cell.

**Animation cues:** Begin with the conceptual array. As it reduces to one interface, explain the voltage jump. When the equations fill the screen, state what the model preserves and what still requires hardware validation.

## Slide group 3: Local physics residual

The PINN should satisfy the harmonic transmission-line equations throughout the right segment. The displayed relation is `V_xi + gamma d I = 0`. At one location, we compare the network or reference derivative with the derivative required by the equation.

These are complex phasors, so both real and imaginary components must agree. Moving the probe demonstrates that agreement at a single point is insufficient. A valid field must satisfy both coupled equations across the domain and also satisfy the interface and terminal conditions.

**Animation cues:** At the first probe position, describe the two complex arrows. As the probe moves, emphasize that the requirement applies continuously along space rather than only at the shown sample.

## Slide group 4: Geometry and reflection

The exact reflection separates into an upstream factor and a local switch response. The right-side length `d` controls the phase separation between ON and OFF states. The upstream length `a` applies a common phase rotation and attenuation, so it can affect the magnitude threshold without changing phase separation.

This distinction makes `d` the main response coordinate in the simplified problem. It also separates three questions that should not be mixed: whether the switch physically controls the wave, whether the equations amplify a residual and whether the neural network approximates the field accurately. A correlation among those quantities does not establish a unique training cause.

**Animation cues:** Follow the point as `d` changes on the phase curve. When `a` changes at fixed `d`, note that phase separation stays fixed. End by distinguishing physical controllability, error gain and neural error.

## Slide group 5: Conventional reference verification

Before evaluating the PINN, we verify the conventional reference. Doubling the spatial resolution from 16 to 512 intervals per segment steadily reduces the complex reflection error. The displayed error vector shrinks toward the exact result, consistent with second-order convergence.

An independent wave-amplitude solve agrees with the ABCD calculation to numerical precision. Power balance supplies another check. Together these results support the conventional solution within the synthetic line model. They do not validate a physical metasurface.

**Animation cues:** Read the interval count and reflection error as refinement proceeds. At the end, summarize the three checks without extending them to hardware.

## Slide group 6: PINN physics loss

For a saved PINN field, the local residual is the network derivative minus the value required by the differential equation. The physics objective squares both complex residuals and integrates them across the normalized coordinate. It also includes the driven-interface and terminal-short terms. No hidden reference-field loss appears in the PINN objective.

The same calculation applies to the coupled current equation. During training, all four sampled loss components decrease. A small sampled loss still does not prove that the field or reflected output is accurate between those samples. That is why the study separately evaluates held-out fields, boundary defects and design decisions.

**Animation cues:** Describe the voltage residual first. As the integration grows, explain how local error enters the loss. Repeat the idea for current. On the loss-history plot, finish with the distinction between low training loss and reliable output.

## Slide group 7: Complex-field visualization

The initial view emphasizes the real projection of the voltage field. A learned curve can look smooth and plausible from that angle. The field is a complex phasor, however, so the imaginary component carries equally important information.

As the camera rotates, the full complex disagreement becomes visible. A cross-section at one position represents a voltage phasor, not three-dimensional device geometry. The same learned and reference arrays remain on screen throughout the camera movement. Smoothness in one projection therefore cannot substitute for a complex-field error calculation.

**Animation cues:** Allow the audience to see the apparently smooth real projection. After the camera rotates, point to the separation in the imaginary direction. Follow the moving cross-section to reinforce the phasor interpretation.

## Slide group 8: Spatial error spectrum

We decompose the complex voltage error into spatial Fourier components. Each coefficient is a weighted sum of 128 error samples. At zero frequency, all weights equal one, so the coefficient measures the mean complex error. At higher frequencies, the weights rotate and the sample contributions can cancel.

The final comparison places held-out field error against the measured output-residual gain and shows a spatial spectrum for one fixed geometry. These diagnostics describe where error occurs and which spatial components remain. They do not prove spectral bias or identify the training-failure cause.

**Animation cues:** Explain the sample accumulation at zero frequency. When the frequency changes, highlight the rotating weights and cancellation. End by labeling the gain and spectrum as diagnostics rather than causal evidence.

## Slide group 9: Signed residual error budget

The verified residual identity transports field and boundary residuals to the reflected-wave error. We first accumulate the correctly weighted interior residual over the right segment. At the endpoint, the quadrature agrees with the independently verified interior term.

A complex transfer factor then rotates and scales that interior contribution. Finally, the drive, interior and short contributions add head-to-tail. Their complex sum matches the measured difference between predicted and reference reflection. Because these are signed complex vectors, a small total can hide larger terms that cancel.

This identity explains how a trained model's residual reaches the output. It does not explain why training produced that residual.

**Animation cues:** Follow the growing integral, then the complex rotation and scaling. As the final arrows appear, describe their signed vector sum and possible cancellation.

## Slide group 10: Exact boundary enforcement

This group tests whether forcing the endpoint conditions repairs the model. The raw network output does not automatically satisfy the terminal short or the driven interface. Subtracting `xi` times the raw terminal value forces `V(1)` to zero. A second correction enforces the driven condition.

Both endpoints now satisfy the required values exactly, but the interior field can still disagree with the reference. All six validation gates in the paired boundary study failed. Exact endpoint enforcement was insufficient at the fixed budget. The transformation also changes the trial representation, so this experiment does not isolate one original training cause.

**Animation cues:** Identify both raw endpoint defects. After each transformation, state which condition becomes exact. When the reference curve appears, direct attention to the remaining interior error and the failed gates.

## Slide group 11: Controlled diagnosis of objective, support and optimizer

The first control widens a missing-training interval around the difficult response region. Each physics-trained model is paired with a direct-reference model using the same network, starting weights, inputs, L-BFGS optimizer and 1,200 gradient calls. Field error increases as support is removed in both objective arms.

At full coverage, direct-reference training lowers median joint-field error by 27.63 times relative to the physics objective. The largest support gap raises the reference-trained error by 4.63 times. These results establish objective and support effects under the matched conditions.

They do not establish deployment success. All six blocked-cohort gates fail. Even the strongest supervised arm has `R95 = 0.04135`, above the 0.03 limit. In the separate optimizer control, L-BFGS reduces median physical-voltage error from 43.39 percent to 7.57 percent and improves 204 of 256 blocked state cases. Both optimizer arms still retain zero of eight feasible blocked designs.

The bounded conclusion is that optimizer, objective and support affect attained error. None of these comparisons identifies a unique cause or supplies a successful remedy.

**Animation cues:** On the first chart, compare matched objective pairs as the support gap grows. On the metric summary, separate the 27.63 and 4.63 error ratios from the deployment gate. On the optimizer chart, acknowledge the large numerical improvement before stating that the screening decision still fails.

## Slide group 12: Design screening and computational cost

The illustrative feasibility rule requires at least 165 degrees of phase separation and minimum reflection magnitude of 0.8. Near the current node, the switch has little influence, so the weak design fails the phase criterion. As the geometry moves into the strong-response region, the conventional reference becomes feasible while the saved neural model still rejects it.

Across the primary held-out cohorts, the PINNs retain all 21 feasible off-grid designs but none of the 10 feasible designs inside the blocked interval. The same blocked failure appears in all three seeds. In the fresh boundary control, all six validation gates fail. Its blocked final set contains no feasible cases, so sensitivity there is undefined.

For this analytic line model, the conventional factorized calculation is also faster per query than neural inference. Adding training creates no positive break-even query count. This cost result applies to these implementations only. It does not establish an HFSS, storage-workflow or hardware comparison.

**Animation cues:** Apply the two feasibility criteria to the weak design. After the geometry moves, contrast the reference and neural decisions. Then move from the representative example to the full cohorts. On the cost animation, state why the neural curve cannot overtake the conventional result here.

## Slide group 13: Recommendation and sources

The analogue establishes that finite-switch influence depends on current participation. It also shows that exact endpoints alone do not repair the tested PINN. The controlled comparisons identify effects from optimization, training objective and sampling support, but none produces a reliable replacement.

For this analogue, retain the conventional solver. The next useful step is to agree on a permitted unit-cell family, a realistic switch model and meaningful tolerances. Then reserve independent geometries near the response transition, compare methods against matched electromagnetic responses and measure solver, storage and workflow costs separately.

The physical argument draws on the team interview, transmission-line theory and metasurface equivalent-circuit literature. The diagnostic argument draws on PINN failure and cost-comparison literature. The report retains the full derivations, frozen protocols, source hashes and uncertainty limits.

**Closing line:** Within this synthetic analogue, the conventional solver remains the reliable and faster choice. Validation against real unit-cell data is the next step.

## Source anchors

- [`../../report.md`](../../report.md): full formulation, experiments, gates, limitations and recommendation
- [`../../PRESENTATION.md`](../../PRESENTATION.md): current deck, controls and validation status
- [`../../sources/interview/Post_Interview_Briefing.md`](../../sources/interview/Post_Interview_Briefing.md): researcher problem context
- [`../../literature-grounding.md`](../../literature-grounding.md): literature claims and model boundary
- [`beat-manifest.json`](beat-manifest.json): authoritative beat numbering and slide grouping
