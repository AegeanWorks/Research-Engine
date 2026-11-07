# Simulations — 1D Baseline and Bounded 3D Diagnostics

The 1D validation core is the baseline for every 3D run. The repository contains a bounded N=64 3D diagnostic (`make n64`) and a pre-registered production scan (`make production`); neither is a converged or stable-Hopfion result. Earlier lost-run values are not cited.

Earlier numbers from a lost script (\(|H|\approx0.16\), \(Z_3\approx0.72\) at \(N=36\)) are not reproduced and are explicitly excluded from the ledger and the paper.

## Required baselines for a production claim

`sims/core.py` implements the 1D baselines and `sims/core3d.py` the 3D energy. They must pass all of the following, each as an automated test in `tests/`:

1. **1D sine-Gordon kink.** PASS: profile and tension convergence at order ~2 (`tests/test_sim_core.py`).
2. **Gradient check.** PASS for the 1D sine-Gordon energy and for the full 3D \(E_2+E_4+Z_3\) energy (relative error < 1e-6; `tests/test_hopfion3d.py`).
3. **Monotone energy.** PASS for the 1D flow.
4. **Hopf-charge estimator.** PASS: preimage linking gives H=0.999958 at 400 samples (reflection flips sign; rotation/shear invariant), and the normalized grid Chern-Simons estimator gives 1.000000 at N=64. The two methods agree; baseline 4 passes.
5. **Derrick virial.** Scaling identity derived (`theory/derrick.py`); not yet checked on a relaxed 3D soliton.
6. **Rotor cross-check.** PASS: Fourier vs finite-difference spectra agree below 1e-3.
7. **Hessian.** PASS for the tangent-space operator: the matrix-free 3D Hessian agrees with the dense tangent Hessian at N=8 to \(1.3\times10^{-15}\). In 1D it is symmetric and stable; the translation mode is lifted by Dirichlet boundaries, so zero-mode counting is not exact.

## Production rules

- Convergence study in \(N\), \(dt\), and step count; report the residual force norm.
- At least 10 random seeds for any spontaneous-ordering claim; report mean, standard deviation, and the ordered fraction.
- Log the \(Z_3\) order parameter, Hopf charge, energy, residual force, and virial ratio per run, with config hash and git commit.
- Check the Hopf estimator at grid scale: the spectral Chern-Simons estimator is accurate for the smooth analytic map at \(N\ge32\), but it loses accuracy when the field develops features at the grid scale. A native estimate below 1 is not by itself evidence of a topological transition; check the pre-normalization norm and compare with a smoothed or upsampled field.
- Extract a mass matrix from a field-theory Hessian only after the baselines pass; report whether it is circulant and whether \(|c|/a\) emerges rather than being fitted.
- Scale to GPU only after the CPU core is validated; target \(N\ge64\) for \(|H|\ge1\) coexistence.

## Status

- 1D baselines 1, 2, 3, 6 pass; 5 is partial and 7 now passes for the 3D tangent-space operator; 4 passes (preimage and normalized grid agree).
- A single-seed N=32 3D pilot is not converged (force RMS 0.10 at 1200 steps) and is resolution-limited. A targeted N=64 diagnostic (`make n64`) is monotone but still not converged (force RMS 0.037 at 3600 steps). Its native H estimate falls below 0.8 as Z3 exceeds 0.6, but the same field has H close to 1 after Gaussian smoothing or spectral upsampling: the native drop is a grid-scale estimator artifact, not a topological transition. The normalized flow keeps the minimum pre-normalization norm at 1, and the boundary is fixed, so the smooth topology is preserved.
- The production scan (`make production`) runs at N=64 (3600 steps, 2x spectral upsampling to N=128, bounded within the 15-minute G-003 wall-clock limit) with a pre-registered acceptance rule and reports the native and upsampled H, Z3, force RMS, energy drift and field smoothness. See `results/hopfion3d_production.{json,md}` and `claims.md` for the current verdict.
- The N=96 resolution check (`make convergence`, ADR-002) compares N=64 and N=96 at 3000 steps and the same physical time. At N=96 the native H is 0.999942 and the upsampled H is 1.000000, but Z3 falls to 0.172071 and the force RMS is 0.01495; the N=64 Z3 order (0.60743 at 3600 steps) is not spatially converged. The check is not converged (|dH|=0.063, |dZ3|=0.356) and claim 15 remains UNVERIFIED. See `results/hopfion3d_convergence.{json,md}`.
- The N=64 dt check (`make temporal`, ADR-003) holds the grid fixed and compares 3000 steps at dt=5e-4 with 6000 at dt=2.5e-4 at t=1.5. The deltas are dH=-1.07e-4, dZ3=-4.6e-6, so the N=96 Z3 gap is spatial (or a longer-time effect), not a timestep artifact. See `results/hopfion3d_temporal.{json,md}`.
- The checkpointed N=96 extension (`make extend`, ADR-004) runs four 3000-step chunks to t=6.0, each under the 900 s cap. Z3 rises 0.172071, 0.333942, 0.477792, 0.598690 and crosses 0.5, but the native H falls to 0.972624, the max bond rises to 0.857 and the force RMS is \(1.075\times10^{-2}\). The final state fails H, force and resolution, so claim 15 remains UNVERIFIED. See `results/hopfion3d_extension.{json,md}`.
- The pure-FN N=64 candidate (`make purefn`, ADR-005) is the 1200-step \(\mu=0\) relax with H=0.999999932 and force RMS \(3.154\times10^{-3}\). Its tangent Hessian has 8 negative modes at N=64 (minimum \(-2.600799\)), so the candidate is a saddle (14e FALSIFIED) and 14b remains UNVERIFIED. See `results/hopfion_purefn_stability.{json,md}`.
- The saddle-escape search (`make escape`, ADR-006) perturbs the pure-FN candidate along its lowest tangent mode by 0.05 and 0.15 and relaxes for 600 steps. Both fields collapse to H=0.320365 and 0.237385 with max bond about 1.97, so neither passes the H>0.9 gate and no local minimum is found; 14b remains UNVERIFIED. See `results/hopfion_saddle_escape.{json,md}`.
- The box-length scan (`make lengthscan`, ADR-007) tests N=64 lengths 8, 10, 12 and 14. Every field keeps H>0.9 but every Hessian has 8 negative modes, with minima -1.469962, -2.600799, -4.223930 and -6.669667; the saddle is not a length-10 artifact and 14b remains UNVERIFIED. See `results/hopfion_length_scan.{json,md}`.
- The scale-stationary N=64 candidate has a dense-validated tangent Hessian with minimum eigenvalue \(-5.799863\) and eight negative modes (`make stability`). It is a saddle; 14d is FALSIFIED and no stable Hopfion is demonstrated.

## Known analytic obstacles (to be tested, not assumed away)

- A nematic director is headless (\(RP^2\)): \(\pi_1=Z_2\), \(\pi_2=Z\), \(\pi_3=Z\). A three-fold sector is not automatic.
- The rotor map with a real \(\cos3\phi\) potential has degenerate \(k=1,2\) sectors, so a naive three-eigenvalue map cannot produce three distinct lepton masses.
- Derrick scaling for the exact Lagrangian must be derived before any stable-Hopfion claim.
