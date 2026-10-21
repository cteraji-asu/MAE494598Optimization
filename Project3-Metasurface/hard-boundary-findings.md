# Exact boundary enforcement is insufficient at this budget

Six fresh, paired fits compared soft penalties with exact endpoint enforcement. All six failed the unchanged validation gate. The hard transform made the driven boundary and short exact but left large interior and reflection error. Exact endpoint enforcement was insufficient to repair this model at the fixed budget. The transform also changes the trial-function representation, so this does not establish the original training-failure cause. It does not identify one remaining optimization cause.

The synthetic finite-switch line is a frequency-domain boundary-value analogue. These results do not reproduce or validate a real device's hardware.

## Prospective controls

Protocol SHA-256 `f72c20160f80341bb93cc8f849450798c49a39b22ff059e224c6aca37320e877`. Selected checkpoints were sealed before final reference access, seal SHA-256 `2f631b0d39ae183a26c19e9c955c5e29a7624c545f53ac84964f222280bce250`.
Same raw 3–64–64–4 tanh network, 4,676 parameters, seeds 0/1/2, identical paired initial weights and minibatch streams, covered 256 training geometries, 4,000 Adam gradient calls and cosine schedule per fit. No reference field or reflection label enters the training objective. Validation chooses among checkpoints every 500 steps, while every fit spends all 4,000 calls. Equal calls do not imply equal runtime.

The transform is $I=i$, $V=v-\xi v(1)-(1-\xi)[v(0)+(1+z_s)i(0)-2]$. Endpoint evaluations remain differentiable. This changes the trial-function representation as well as boundary enforcement. It does not isolate gradient imbalance.

The original 32+32 fresh blocked proposal could not freeze because only 61 separated candidates remained. It became 30 validation plus 30 final before fitting or reference-class inspection. Minimum separation stayed $2\times10^{-5}$. Off-block counts are 80 validation and 256 final.

## Final results

| Arm | Seed | Selected step | Fit seconds | Blocked max-state reflection error, 95th percentile | Blocked voltage relative L2, median | Max driven-boundary residual |
|---|---:|---:|---:|---:|---:|---:|
| soft | 0 | 4000 | 13.407 | 1.626839 | 44.17% | 0.203 |
| hard | 0 | 4000 | 14.250 | 1.642331 | 44.22% | 2.48e-16 |
| soft | 1 | 4000 | 13.296 | 1.637912 | 44.98% | 0.168 |
| hard | 1 | 4000 | 14.153 | 1.620761 | 43.58% | 4.58e-16 |
| soft | 2 | 4000 | 13.367 | 1.620636 | 44.10% | 0.188 |
| hard | 2 | 4000 | 14.136 | 1.620363 | 43.45% | 2.22e-16 |

All 30 new blocked final geometries are reference-infeasible at the illustrative phase≥165° and magnitude≥0.8 thresholds. Both arms classify all 30 as infeasible. Sensitivity is undefined, so the 100% specificity cannot demonstrate successful screening. Five cases are near the declared thresholds. No new class-enriched sample was added after seeing this result.

On the historical primary blocked cohort, every new arm/seed still misses all 10 feasible cases, with zero false feasible predictions among 150 infeasible cases. This is a previously inspected diagnostic cohort, not new final evidence.

Hard enforcement reduces terminal voltage to zero and driven-boundary/extraction disagreement to roundoff. It does not fix the final reflection tail or spatial field accuracy. Its maximum blocked power-balance defect is larger than the matched soft arm in every seed, so endpoint correctness does not imply energy consistency.

## Independent checks and cost

Saved state reflections were recomputed with standalone NumPy network algebra and an independent complex wave-system reference. Spatial derivatives were compared with NumPy finite differences. The exact residual transport identity was checked for every final state with quadrature. See results.json for maxima and counts.

Reflection-only hard inference uses the unchanged current output and one raw network pass. The conventional factorized reference remains faster for both single and batch queries. There is no positive break-even query count. Fit wall time includes validation as a subset. Reference generation occurs outside that fit timer. Total timed setup is fit wall time plus reference generation, without adding validation a second time.

## Decision

Keep the conventional model for this analogue. Use the verified signed residual budget to guide a separately frozen experiment only if the researcher needs this specific diagnostic. Do not claim Path C success, a unique PINN root cause, a full-wave speedup, or a hardware remedy. The current Path B evidence establishes a failure and shows exact endpoint enforcement was insufficient to repair this model at the fixed budget, while optimization, representation and sampling remain coupled alternatives.

Sources: [exact boundary trial functions](https://arxiv.org/abs/2104.08426), [derived error identity](residual-error-identity.md), [protocol](outputs/hard-boundary-control/frozen-protocol.json), [all six results](outputs/hard-boundary-control/results.json), [historical comparison](outputs/hard-boundary-control/historical-comparison.json).
