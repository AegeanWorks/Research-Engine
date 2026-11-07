# Literature Notes

Search date: 2026-10-25. This is a targeted check, not a systematic review. "Likely known" means a source already contains the result in recognisably equivalent form; it does **not** mean the source endorses the interpretation here.

## 1. Koide relation and circulant matrices

- **Y. Koide**, *Lett. Nuovo Cim.* **34**, 201 (1982); *Phys. Rev. D* **28**, 252 (1983). Original charged-lepton relation \(Q=2/3\).
- **C. A. Brannen**, *The Lepton Masses* (2006), `https://brannenworks.com/MASSES2.pdf` (unpublished preprint). Explicit Hermitian circulant
  \[
  \Gamma(\mu,\eta,\delta)=\mu\begin{pmatrix}1&\eta e^{i\delta}&\eta e^{-i\delta}\\ \eta e^{-i\delta}&1&\eta e^{i\delta}\\ \eta e^{i\delta}&\eta e^{-i\delta}&1\end{pmatrix},
  \]
  eigenvalues \(\mu(1+2\eta\cos(\delta+2\pi n/3))\), DFT eigenvectors, and the identification \(\lambda_n=\sqrt{m_n}\). Reports \(\eta^2=0.500003(23)\), \(\delta=0.2222220(19)\). **Consequence: claims 1a, 1c, 2a, 2b are likely known and are not novel here.**

- **Phase near-miss.** Brannen reports \(\delta=0.2222220(19)\), close to \(2/9\). Our PDG 2024 fit gives \(\delta=0.22222476\) rad mod \(2\pi/3\), and \(2/9\) is \(0.41\sigma\) away. A post-hoc search over rationals with denominator \(\le20\), rational multiples of \(\pi\) with denominator \(\le12\), and simple roots gives a look-elsewhere \(p=7.9\times10^{-4}\) over that prior. This is a near-miss, not evidence for a closed form; see `results/delta_search.json`.
- **Z.-z. Xing and H. Zhang**, *On the Koide-like Relations for the Running Masses of Charged Leptons, Neutrinos and Quarks*, arXiv:hep-ph/0602134. Shows \(Q_l(\mu)\ne2/3\) for running masses, with \(Q_l(M_Z)\approx0.66792\) using the one-loop QED pole-to-\(\overline{\rm MS}\) conversion; the discrepancy from the pole value is about \(0.2\%\). This is the key prior result for claim 3b/4.
- **Y. Sumino**, *Family gauge symmetry as an origin of Koide's mass formula and charged lepton spectrum*, JHEP **05** (2009) 075, arXiv:0812.2090. Discusses the QED correction that makes the pole-mass relation differ from the running-mass relation; the correction is about \(0.1\%\). The proposed family-gauge cancellation is a model, not a derivation of Z3.
- **Z.-z. Xing, H. Zhang, S. Zhou**, *Updated Values of Running Quark and Lepton Masses*, Phys. Rev. D **77**, 113016 (2008), arXiv:0712.1419. Running charged-lepton masses at \(M_Z\): \(m_e=0.486570161\) MeV, \(m_\mu=102.7181359\) MeV, \(m_\tau=1746.24\) MeV (one-loop QED conversion from pole masses).
- **G.-y. Huang and S. Zhou**, *Precise Values of Running Quark and Lepton Masses in the Standard Model*, Phys. Rev. D **103**, 016010 (2021), arXiv:2009.04851. Full-SM \(\overline{\rm MS}\) values used as initial conditions here: at \(M_Z\), \(m_e=0.48307\pm0.00045\) MeV, \(m_\mu=0.101766\pm0.000023\) GeV, \(m_\tau=1.72856\pm0.00028\) GeV; at \(10^{12}\) GeV, \(m_e=0.48388\pm0.00139\) MeV, \(m_\mu=0.101936\pm0.000277\) GeV, \(m_\tau=1.73194\pm0.00466\) GeV (Table 3).

**Novelty verdict for the Z3/Koide core:** the circulant algebra and the DFT eigenvectors are likely known (Brannen). The running-mass behaviour is known at the qualitative level (Xing-Zhang; Sumino). What is not established in the literature checked here is a dynamical derivation of the Z3 multiplet that fixes \(\eta=1/\sqrt2\). This project does not claim that derivation.

## 2. Neutrino and quark data

- **NuFit 5.2** (2022), with SK-atm: `http://www.nu-fit.org/sites/default/files/v52.tbl-parameters.pdf`. Used values: \(\Delta m^2_{21}=7.41\times10^{-5}\,{\rm eV}^2\), \(\Delta m^2_{31}=+2.507\times10^{-3}\,{\rm eV}^2\) (NO), \(\Delta m^2_{32}=-2.486\times10^{-3}\,{\rm eV}^2\) (IO), \(\theta_{12}=33.41^\circ\), \(\theta_{13}=8.58^\circ\), \(\theta_{23}=42.2^\circ\) (NO). The 3\(\sigma\) splitting corners are included in the scan. NuFit 5.3/6.0 shift the central values by less than 1%, which does not affect the negative result.
- **G.-y. Huang and S. Zhou**, Phys. Rev. D **103**, 016010 (2021), arXiv:2009.04851, Table II. Full-SM \(\overline{\rm MS}\) quark masses at \(M_Z\): \(m_t=168.26\) GeV, \(m_b=2.839\) GeV, \(m_c=0.620\) GeV, \(m_s=53.16\) MeV, \(m_d=2.67\) MeV, \(m_u=1.23\) MeV. The same table provides the five higher scales used in the scan.

**Neutrino verdict:** the maximum of \(Q_\nu\) over both orderings and \(0\le m_{\rm light}\le0.2\) eV is \(0.585612\) (NO at \(m_{\rm light}=0\)); the 3\(\sigma\) corner maximum is \(0.590606\). No scanned point reaches \(2/3\). This is a negative result for a direct Koide extension to neutrinos.

**Quark verdict:** at \(M_Z\), \(Q_U=0.887569\) and \(Q_D=0.748065\); over the six tabulated scales, \(Q_U\in[0.887569,0.892554]\) and \(Q_D\in[0.738535,0.748065]\). The direct extension is falsified. The values are scale-dependent and must not be quoted without their scale and scheme.

**PMNS caution:** a "circulant PMNS" is not a single model. If both mass matrices are circulant in the same basis, the prediction is no mixing; if only the neutrino matrix is circulant, the prediction is trimaximal mixing. Both branches are excluded, but only the second makes the original claim a \(\theta_{13}\) statement.

## 3. Standard-Model RGE

- **T. P. Cheng, E. Eichten, L.-F. Li**, *Higgs phenomenon in asymptotically free theories*, Phys. Rev. D **9**, 2259 (1974); **M. E. Machacek and M. T. Vaughn**, *Two-loop renormalization group equations in a general quantum field theory*, Nucl. Phys. B **222**, 83 (1983); B **236**, 221 (1984); B **249**, 70 (1985).
- **H. Arason et al.**, *Renormalization-group study of the standard model and its extensions: the standard model*, Phys. Rev. D **46**, 3945 (1992). Standard one- and two-loop SM RGEs and the coefficients used in F10.
- Cross-check in this repo: `phenomenology/rg.py` reproduces the published one-pass QED conversion (F9) to about \(2\times10^{-4}\), and the full-SM running of Huang-Zhou at the few-percent level in absolute masses (about 3% at \(10^8\) GeV and 5% at \(10^{12}\) GeV). The dimensionless \(Q\) computed from the published masses agrees with this one-loop run to about \(4\times10^{-5}\). The one-loop code is not a precision replacement for the three-loop literature.

## 4. Nematic / superfluid-vacuum / topological-defect prior art

These are identified for engagement, not yet used quantitatively. No claim in this repository depends on them.

- **P. G. de Gennes and J. Prost**, *The Physics of Liquid Crystals*, 2nd ed. (Oxford, 1993). Frank-Oseen free energy; the \(K_1=K_2=K_3\) one-constant approximation.
- **G. H. Derrick**, *Comments on nonlinear wave equations as models for elementary particles*, J. Math. Phys. **5**, 1252 (1964). Derrick scaling.
- **G. E. Volovik**, *The Universe in a Helium Droplet* (Oxford, 2003). Superfluid \(^3\)He as an analogue vacuum; topological defects and emergent gauge fields.
- **L. D. Faddeev and A. J. Niemi**, *Knots and particles*, Nature **387**, 58 (1997), arXiv:hep-th/9610193. Hopfion/skyrmion-type solitons in a unit vector field.
- **W. G. Unruh**, *Experimental black-hole evaporation?*, Phys. Rev. Lett. **46**, 1351 (1981).
- **C. Barcelo, S. Liberati, M. Visser**, *Analogue gravity*, Living Rev. Rel. **8**, 12 (2005), arXiv:gr-qc/0505065.
- **X.-G. Wen**, *Quantum Field Theory of Many-Body Systems* (Oxford, 2004). String-net / emergent gauge fields.

**Topology caution (claim 13).** A nematic director is headless, so the order-parameter space is \(RP^2\). Its homotopy groups are \(\pi_1(RP^2)=Z_2\), \(\pi_2(RP^2)=Z\), \(\pi_3(RP^2)=Z\). A three-fold sector is **not** automatic. The \(\cos3\phi\) term in the rotor is inserted by hand unless a natural extension (rank-3 order parameter, three coupled nematics, or a three-fold lattice) produces it. This is an open falsification target.

- **Hydrated electron**: absorption maximum about 720 nm (1.7 eV); E. J. Hart and M. Anbar, *The Hydrated Electron* (Wiley, 1970).
- **Hydrated-electron VDE**: vertical binding energy \(3.27\pm0.10\) eV for H\(_2\)O; Y. Tang, H. Shen, K. Sekiguchi, N. Kurahashi, T. Mizuno, Y.-I. Suzuki, T. Suzuki, *Phys. Chem. Chem. Phys.* **12**, 3653 (2010), DOI: 10.1039/b925741a.
- **Hydrated-electron temperature coefficients (claim-43 width comparator)**: spectrum measured 5-300 C; up to ~150 C, \(dE_{\max}/dT=-2.8\times10^{-3}\) eV/K and \(d(\delta E_{1/2})/dT=2\times10^{-4}\) eV/K where \(\delta E_{1/2}\) is stated as "the half-width of the spectrum" (FWHM vs HWHM ambiguous; both readings carried); H. Christensen and K. Sehested, *J. Phys. Chem.* **90:1** (1986), DOI: 10.1021/j100273a042.
- **Hydrated-electron band shape (claim-43 shape comparator)**: spectra resolved into two Gaussian bands plus a continuum tail; in water the first Gaussian half-width \(0.71\pm0.07\) eV, the second \(0.37\pm0.08\) eV, the tail \(\sim1.0\pm0.2\) eV; high-energy side \(A/A_{\max}\sim E^{-n}\) with \(n=4.4\) in water (not Gaussian); band is broad and asymmetric; F. Jou and G. R. Freeman, *Can. J. Chem.* **57**, 591 (1979). Subcritical spectra approximately Gaussian on the low-energy side and Lorentzian on the high-energy side; D. Bartels et al., *J. Phys. Chem. A* (2005, supercritical water pulse radiolysis). Observed bulk band "broad and highly asymmetric" with maximum 1.72 eV (Jou & Freeman); L. Turi et al., *JCTC* **20**, 4265 (2024) review.
- **Hydrated-electron side half-widths (claim-45 ratio comparator)**: Jou-Freeman temperature-dependent lineshape fits for bulk H2O, \(E_{\max}(T)=2.4506-0.0024T\) eV, red Gaussian HWHM \(G(T)=0.1517+0.00051T\) eV, blue Lorentzian HWHM \(L(T)=0.5124-0.00010T\) eV (T in K), as tabulated in the Coe et al. IRPC review (verified against its 210 K row: G=0.259, L=0.491, Emax=1.947 eV); at 26 C (Jou-Freeman Table 1 conditions, 299.15 K), G=0.3043, L=0.4825 eV. Definitions (blue=Lorentzian HWHM, red=Gaussian HWHM) per Bartels et al. D2O work; R. E. Bartels et al., *J. Phys. Chem. A* (2005, supercritical water pulse radiolysis).

## 5. Non-peer-reviewed material deliberately not used

- A 2026 vixra preprint and a 2026 Zenodo note on Koide RG running were found in search results. They are not peer-reviewed, their provenance is unclear, and their numerical claims were not reproduced here. They are **not** cited as evidence. Any two-loop drift number must be recomputed from a validated code before use.
