## Literature grounding and the model boundary

[Costa and Borgese (2021)](https://doi.org/10.1109/OJCOMS.2021.3092217) connect a grounded substrate transmission line with parallel patch and varactor impedances. This supports reduced reflection-circuit reasoning, but that topology differs from this study's arbitrary finite series switch.

[Wu et al. (2024)](https://doi.org/10.1049/mia2.12505) connect geometry and embedded RLC choices to phase-sensitive and less-sensitive regions. That supports investigating tunability; it does not diagnose a real device's failed geometries or identify them with this line's quarter-wave node.

The present model is a single-frequency causal analogue. Its line current is not an extracted copper surface-current distribution. The map from actual copper geometry, substrate, switch parasitics and periodic electromagnetic fields to the chosen line lengths and impedances is uncalibrated. No paper cited here makes this series topology a validated model of a real device's device. A literature-backed metasurface equivalent circuit would require its own topology and parameter mapping; we have not silently substituted one into the completed experiments.

[Krishnapriyan et al. (2021)](https://arxiv.org/abs/2109.01050) motivate separating training failure from representational capacity. Our exact-label comparison is an empirical diagnostic of the same architecture, not a proof of uniform representability.

[Rathore et al. (2024)](https://arxiv.org/abs/2402.01868) motivate scrutinizing optimizer behavior in PINNs. They do not establish our cause or promise that L-BFGS fixes it. Our matched gradient-call, runtime and terminal-iterate comparison retains its failed numerical gate and one-seed scope.

[Grossmann et al. (2024)](https://doi.org/10.1093/imamat/hxae011) distinguish solution cost from evaluating a learned solution. This motivates our separate training, reference and inference accounting. Our microsecond circuit baseline is not an expensive FEM or HFSS benchmark.

Three claims remain separate: the reduced equations are numerically and symbolically consistent; the analogue demonstrates weak and strong finite-switch influence; hardware transfer is unvalidated. The first two are supported here. The third needs real geometry, material and switch data with an independent electromagnetic comparison.

Primary sources consulted: Costa and Borgese, *Electromagnetic Model of Reflective Intelligent Surfaces*, IEEE OJCOMS 2, 1577-1589; Wu et al., *Embedded circuit analysis and design method for reconfigurable metasurface element*, IET MAP 18(11), 819-829; Krishnapriyan et al., *Characterizing Possible Failure Modes in Physics-Informed Neural Networks*; Rathore et al., *Challenges in Training PINNs: A Loss Landscape Perspective*; Grossmann et al., *Can physics-informed neural networks beat the finite element method?*, IMA J. Applied Mathematics 89(1), 143-174.
