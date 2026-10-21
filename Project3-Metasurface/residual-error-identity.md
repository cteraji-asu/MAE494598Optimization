## Residual transport and reflection-error identity

This is a problem-specific derivation, not an identity quoted from the literature. It applies to the normalized right fields used by the retained networks. It does not identify line current with copper surface current.

Let $g=\gamma d$, $J=\begin{pmatrix}0&1\\1&0\end{pmatrix}$ and $u=(V,I)^T$. For a predicted field, define $f=u'+gJu$, $b_0=V(0)+(1+z_s)I(0)-2$ and $b_1=V(1)$. If $e=\widehat u-u_\mathrm{exact}$, then $e'=-gJe+f$. Variation of constants gives

$$
e(1)=e^{-gJ}e(0)+\int_0^1e^{-gJ(1-t)}f(t)\,dt.
$$

Writing $c=\cosh g$, $s=\sinh g$ and

$$
q=\int_0^1[\cosh(g(1-t))f_V(t)-\sinh(g(1-t))f_I(t)]\,dt,
$$

the two boundary equations are

$$
\begin{pmatrix}1&1+z_s\\c&-s\end{pmatrix}e(0)
=\begin{pmatrix}b_0\\b_1-q\end{pmatrix}.
$$

For $D=(1+z_s)c+s\ne0$, Cramer's rule yields $e_I(0)=(c b_0+q-b_1)/D$. Therefore the port reflection error is

$$
\Delta R=-e^{-2\gamma a}\frac{c b_0+q-b_1}{D}.
$$

The port, termination and interior contributions are complex signed quantities. Their magnitudes do not add in general, and cancellation can be substantial. Subtracting one contribution is an a posteriori counterfactual of this linear error equation, not a separately trained neural remedy or a free inference operation.

For the continuous counterpart of the retained physics loss, let

$$
\eta^2=\int_0^1(|f_V|^2+|f_I|^2)\,dt+|b_0|^2/4+|b_1|^2.
$$

Cauchy-Schwarz gives the absolute output-error bound

$$
|\Delta R|\le G\eta,\quad
G=\frac{|e^{-2\gamma a}|}{|D|}
\sqrt{4|c|^2+1+\int_0^1(|\cosh(g(1-t))|^2+|\sinh(g(1-t))|^2)\,dt}.
$$

This gain depends on the stated residual/boundary norm and reference plane. It is not a neural Hessian condition number and cannot be inferred from the training loss alone. The implementation must verify signs, reference normalization, chain rule, quadrature convergence and the exact bound on analytic perturbations and frozen network checkpoints before this derivation is used as evidence.

Stability-based error analysis is motivated by [Mishra and Molinaro](https://arxiv.org/abs/2006.16144); operator conditioning is discussed by [Liu et al.](https://arxiv.org/abs/2402.00531). Those sources motivate the diagnostic, not this particular formula or its empirical conclusion.
