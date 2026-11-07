# Madelung Fluid Dictionary

Quantum mechanics can be written exactly as a fluid. With

\[
\psi=\sqrt{\rho}\,e^{iS/\hbar},
\]

the Schrodinger equation splits into a continuity equation and an Euler
equation:

\[
\partial_t\rho+\partial_x(\rho v)=0,
\qquad
\partial_t v+v\partial_x v=-\frac{1}{m}\partial_x(V+Q),
\]

with the quantum pressure

\[
Q=-\frac{\hbar^2}{2m}\frac{\partial_x^2\sqrt{\rho}}{\sqrt{\rho}}.
\]

The velocity is \(v=\frac{\hbar}{m}\partial_x S\).

## What is established

- The dictionary is exact, not an approximation. The repository verifies it
  numerically: the free Gaussian density matches to \(8.8\times10^{-13}\), the
  harmonic-oscillator coherent state to \(1.2\times10^{-4}\), the continuity
  residual is \(3.3\times10^{-7}\), and the exact-Gaussian Euler core residual is
  \(6.1\times10^{-3}\) (`make madelung`, `results/madelung.{json,md}`).
- The only non-classical ingredient is \(Q\). A classical fluid with an
  ordinary pressure cannot reproduce it.

## What is not established

- \(Q\) is nonlocal and singular at nodes. The dictionary does not derive \(Q\)
  from a microphysical fluid, and it does not explain the Born rule or
  measurement.
- Calling the representation a fluid is a change of variables until a
  microphysical model supplies \(Q\).

## Candidate microphysical models

1. **Stochastic mechanics (Nelson).** Brownian motion with diffusion
   \(D=\hbar/(2m)\) produces an osmotic velocity and, with the mean
   acceleration, the quantum pressure. Test: simulate the stochastic paths and
   compare the stationary density with \(|\psi|^2\).
2. **Pilot wave / de Broglie-Bohm.** A particle is guided by \(v=\nabla S/m\);
   the Born rule is an equilibrium distribution. Test: trajectory statistics
   for a double slit or a harmonic oscillator.
3. **Walking droplets.** A bouncing droplet on a vibrating bath is a classical
   particle-wave system that shows quantum-like quantization and interference.
   Test: a 1D walker model and its orbit quantization.
4. **Superfluid vacuum.** \(Q\) arises from a subfluid pressure or condensate
   healing length. Test: the finite-correlation-length correction to the
   spectrum and its experimental bound.

## Falsifiable differences

A genuine fluid model should differ from exact quantum mechanics somewhere:

- a finite correlation length modifies the high-\(k\) dispersion;
- a stochastic noise spectrum adds a measurable decoherence rate;
- surface tension or compressibility changes the quantum pressure at short
  distances;
- a preferred frame or a finite sound speed breaks exact Lorentz invariance.

The next step is to choose one microphysical model and compute its leading
correction, rather than only re-expressing the Schrodinger equation.
