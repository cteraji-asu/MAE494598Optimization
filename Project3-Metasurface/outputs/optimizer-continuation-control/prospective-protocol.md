> Historical original request. The geometry-count blocker below was resolved by an approved pre-fit amendment. See frozen-protocol.json, freeze-receipt.json and results.json for the executable protocol and completed negative seed-0 pilot. The original request and audit remain intact.

# Prospective optimizer comparison

Status: blocked before fitting. No new optimizer run has started.

The comparison would fork covered PINN seeds 0, 1 and 2 from the retained reallocated coverage study. Both arms use the same 256 training geometries, paired switch states, deterministic 17-point spatial grid, architecture, normalization, initial weights and physics-only PDE voltage, PDE current, driven port divided by four and common short objective. Reference fields and labels must not enter either training closure.

The two arms are full-batch L-BFGS with the retained supervised continuation settings and full-batch Adam with fixed learning rate 0.0002. Each arm has a maximum of exactly 1,200 objective-plus-gradient evaluations, including line-search trials. The terminal accepted iterate is the endpoint. If the L-BFGS budget interrupts a line search, restore the last accepted iterate rather than an unaccepted trial. Early convergence must be reported explicitly. Count evaluations and accepted updates and report elapsed time. Equal calls do not imply equal runtime.

The requested fresh generator seed is 49420261023. Requested validation consists of 80 off-block and 80 blocked designs; holdout consists of 256 off-block and 256 blocked designs. Both states stay together. Blocked d remains [0.195, 0.222]. Every new d must be at least 0.00002 from all previous study and training d values and from every other new d. Hash the frozen protocol, initial weights and source before fitting.

Validation is diagnostic and gates repeats, never checkpoint selection. The existing numerical gate remains blocked validation reflection R95 at most 0.03, median field relative L2 at most 0.05, and clear-design sensitivity and specificity at least 0.90 with both classes present. Clear margins remain 2 degrees from 165 degrees and 0.01 from magnitude 0.8; retain phase masking. Repeat seeds 1 and 2 unchanged only if either seed 0 pilot arm meets this combined validation gate. Maximum six continuations, no tuning or sweeps. Evaluate dense held-out residuals at 128 midpoints and the retained physical diagnostics, reporting regions separately.

This is exploratory because earlier tests have been inspected. It isolates optimizer family conditional on a shared full-batch continuation. It does not isolate the full-batch change from earlier minibatch training. Similar improvement in both arms would not establish an L-BFGS-specific effect.

## Split feasibility blocker

The pre-fit audit found 768 distinct prior blocked d values. Removing the forbidden neighborhoods leaves 205 free intervals with total length 0.0026182176416944813. Even optimal packing permits at most 257 additional separated d values. The requested 80 + 256 = 336 blocked designs therefore cannot satisfy the specified separation rule.

No counts, thresholds or separation distances were changed. A revised blocked validation/holdout allocation is required before freezing an executable protocol and fitting. The exact prior values, free intervals, source hashes and upper-bound calculation are in split-admissibility-audit.json.
