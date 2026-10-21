# Worked reference and PINN-error arithmetic

These are transparent derivations and arithmetic for a reader to reproduce by hand. They do not claim that a named team member has already performed or signed off a manual check. Numerical scripts cross-check the displayed arithmetic, rather than replacing it.

## Conventional reference at a lossless quarter-wave right segment

Use the separately declared lossless limit, $\gamma=i2\pi$, $d=0.25$, $a=0.11$, and the same finite switch and short in both states. This is not the default lossy training model.

Then $g=\gamma d=i\pi/2$, so $\sinh g=i$ and $\cosh g=0$. Substitution into the factorized reflection gives

$$
r_s=\frac{i+(z_s-1)0}{i+(z_s+1)0}=1,
\qquad R_s=e^{-2\gamma a}=e^{-i1.3823007676}.
$$

Thus $R_s=0.1873813146-0.9822872507i$, with $|R_s|=1$. Both states agree, because zero current at the switch makes a finite impedance change ineffective in this limit. This is a check of the equations, not an imposed half-turn between states.

## One saved PINN output-error value

Take primary seed 0, `test_blocked-0000`, OFF, the first blocked OFF row in the retained CSV. Selection is by file order, not largest error. Its default lossy-model geometry is $d=0.2002196706$, $a=0.1258368734$.

The independent reference and saved prediction in `outputs/switched-surrogate/pinn_seed-0_states.csv` are

$$
R=-0.9012054598+0.0922533169i,\qquad
\widehat R=-0.4184987096-0.7931354358i.
$$

Subtract components, then square and add:

$$
\Delta R=0.4827067502-0.8853887527i,
$$

$$
|\Delta R|=\sqrt{0.4827067502^2+0.8853887527^2}
=\sqrt{0.2330058067+0.7839132435}
=1.0084240428.
$$

The CSV records `complex_R_error=1.0084240428252733`. This is absolute complex reflection error at one port/state, not relative field L2. Independent NumPy evaluation of the saved weights and a separate 3-by-3 wave solve check the underlying numbers. A small magnitude error alone would miss the large phase/output error in this example.
