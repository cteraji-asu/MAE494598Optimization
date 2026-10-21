## Exploratory physics-only optimizer control

The supervised continuation weakened an architecture-only explanation, but added both labels and optimizer work. This follow-up changes optimizer family while holding the physics objective and full-batch continuation fixed. It is exploratory because prior tests were already inspected. It does not isolate the shared full-batch change from earlier minibatch training.

The protocol was frozen before reference class inspection, model evaluation or fitting. It starts both arms from identical covered PINN seed-0 weights with fresh optimizer state. Both use the same 256 reallocated training geometries, paired states, deterministic 17-point spatial grid, unchanged architecture, normalization and PDE(V) + PDE(I) + port/4 + short objective. No reference generator or labels are accessed inside either training closure. Four safeguard tests cover that separation, matched call caps, geometry separation and last-accepted restoration.

The original proposed 80 blocked validation plus 256 blocked holdout geometries could not meet the 0.00002 separation rule after all previous studies. A pre-fit interval audit gives an upper bound of 257 additional separated blocked values. The approved geometry-only amendment uses 64 blocked validation and 128 blocked holdout, plus the original 80 off-block validation and 256 off-block holdout. A 257-candidate admissible pool was constructed, shuffled with seed 49420261023, and allocated without class-based resampling. All new-to-prior and new-to-new d separations exceed 0.00002. The audit, amendment and hashes are retained rather than overwritten.

L-BFGS retains strong Wolfe line search, learning rate 1, history 50, inner max_iter 20 / max_eval 30 and tolerances 1e-9 / 1e-12. Adam uses fixed learning rate 0.0002. Each arm used exactly 1,200 full objective-plus-gradient evaluations, including line-search trials. These are equal calls, not equal wall time or accepted updates. L-BFGS made 1,095 accepted updates in 72.57 seconds and Adam made 1,200 in 70.60 seconds. The cap interrupted a final L-BFGS line search; the last accepted iterate was restored. Endpoints are terminal accepted weights, with no validation checkpoint selection. No arm converged early.

The unchanged combined numerical validation gate requires blocked R95 <= 0.03, median normalized joint right-field L2 <= 0.05, and clear validation sensitivity/specificity >= 0.90 with both classes present. Clear margins remain 2 degrees from 165 degrees and 0.01 from magnitude 0.8. The decision population matches the retained representability gate, all clear validation geometries; blocked clear decisions are also reported separately. R95 takes, for each geometry, the larger complex-reflection error across the two states, then the 95th percentile across geometries. This is distinct from median field error.

| Terminal seed-0 comparison | L-BFGS | Adam |
|---|---:|---:|
| Full objective + gradient evaluations | 1,200 | 1,200 |
| Blocked validation R95 | 1.07051 | 1.61571 |
| Blocked validation median normalized joint right-field L2 | 47.71% | 86.59% |
| All clear validation feasible retained | 6/12 | 6/12 |
| All clear validation infeasible rejected | 126/126 | 126/126 |
| Blocked clear validation feasible retained | 0/6 | 0/6 |
| Blocked holdout R95 | 1.07288 | 1.61203 |
| Blocked holdout median physical voltage relative L2 | 7.5747% | 43.3932% |
| Blocked holdout feasible retained | 0/8 | 0/8 |
| Blocked holdout infeasible rejected | 120/120 | 120/120 |
| Blocked clear holdout feasible retained | 0/2 | 0/2 |
| Maximum blocked holdout power-balance defect | 0.22737 | 0.06536 |

The physical voltage metric integrates squared complex voltage errors over both line segments, normalizes by the reference energy, and takes the median over 256 state cases. It is not the normalized joint right-field metric used by the existing validation gate. Nineteen blocked holdout designs are ambiguous; the full counts above retain them. The off-grid holdout has 36 feasible and 220 infeasible designs; both arms classify all of them correctly, including all 253 clear designs.

L-BFGS substantially reduces field and reflection error relative to Adam under this matched-call continuation. That establishes an optimizer-family effect conditional on this one seed and fixed full-batch pathway. It does not establish useful screening: both miss every feasible blocked holdout design, and both fail the unchanged validation gate. The predeclared rule therefore stops after seed 0, without repeats or tuning. Power consistency is not uniformly improved; L-BFGS has the larger blocked power defect, against incident power 0.5. Raw residuals, boundary defects, extraction disagreement, passivity checks and power defects are retained by region, including dense residuals at 128 held-out midpoints.

Independent NumPy forward evaluation and a separate wave solve verify another 2,112 reflection metrics and 2,064 selected field-reference rows. This follow-up narrows the diagnosis toward a training-pathway contribution without isolating a unique complete PINN cause. It is neither a successful Path C fix nor hardware validation.

Protocol SHA-256: `a8bac535c4c58bdb837dfeda38890ebd86e5413838e895096d136208032a56f9`. See `outputs/optimizer-continuation-control/` for the prospective request, infeasibility audit, amended frozen geometry-only protocol, start hashes, accepted-step logs, terminal weights, region summaries and independent verification. Completed outputs refuse automatic reruns.
