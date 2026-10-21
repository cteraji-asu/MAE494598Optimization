# Recommendation memo

To the research collaborator, identity withheld pending permission
From Team 6, MAE494/598 design optimization
21 October 2026
Draft for team review. Unsent.

Our finite-switch transmission-line analogue tests one proposed current-participation mechanism while keeping the geometry and circuit synthetic. It is not a calibrated model of your unit cell. A finite switch has little influence near a current node and a strong influence elsewhere; independent conventional calculations support this within the analogue.

The primary neural models retain 21/21 feasible off-grid designs but miss all 10 feasible designs in a withheld interval, across three seeds. Our 165-degree phase cutoff and 0.8 magnitude floor are illustrative, not your confirmed tolerances.

Controlled follow-ups identify bounded causes of attained numerical error. With identical starting weights, inputs, physics objective and 1,200 gradient calls, L-BFGS reduces median blocked physical-voltage error from 43.39% to 7.57% relative to Adam, yet both still miss every feasible blocked design. A separate matched-objective study finds that increasing a nested missing-training interval increases field error for both physics and direct-reference training. At full coverage, reference training fits much better fields with the same network and optimizer. These results show optimizer, objective and coverage dependence. They do not uniquely explain the entire original failure.

All six exact-boundary validation gates and all six new gap/objective blocked-cohort gates fail. All three new supervised off-grid arms pass their off-grid gates. Exact endpoints do not ensure accurate interiors or useful decisions. The fresh boundary-control blocked set contains no feasible cases, so sensitivity there is undefined. Negative results and false feasible decisions remain visible.

Keep the conventional solver for this analogue: its measured query cost is lower than neural inference, so there is no positive training break-even. We have not benchmarked your full-wave solver or storage workflow.

For follow-on work, agree on useful tolerances and a permitted small unit-cell family, then reserve independent geometries near response transitions. Compare interpolation and neural methods against conventional responses, reporting both discarded feasible and promoted infeasible cases. Time solver work, storage and orchestration separately. Hardware validation is needed for a hardware claim, not for the course's allowed synthetic study.
