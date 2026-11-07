"""Real Z3 rotor potential scan report (claim 19, ADR-010)."""

from __future__ import annotations

from domains.fluid_universe.theory.rotor_potential import scan

from .provenance import RESULTS_DIR, metadata, write_json, write_text_atomic


def run_rotor_potential_check(write: bool = True) -> dict:
    result = scan()
    config = {
        "mu": 1.0,
        "nus": [0.0, 1.0, 3.0, 10.0],
        "fluxes": "0.0 to 1.0 in 0.1 steps",
        "n_cutoff": 120,
        "convergence_n_cutoff": 240,
        "koide_target": result["koide_target"],
        "koide_tolerance": result["koide_tolerance"],
        "scope": "real Z3 rotor potential scan; sector energies as mass roots",
    }
    payload = {"meta": metadata(config), "result": result}
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RESULTS_DIR / "rotor_potential.json", payload)
        write_text_atomic(
            RESULTS_DIR / "rotor_potential.md", render_markdown(payload)
        )
    return payload


def render_markdown(payload: dict) -> str:
    result = payload["result"]
    best = result["best"]
    lines = [
        "# Real Z3 rotor potential scan (claim 19)",
        "",
        "Hamiltonian: H = (L-A)^2/(2I) + mu(1-cos 3phi) + nu(1-cos 6phi), "
        "with mu=1, I=1 and n_cut=120.",
        "",
        "## Maximum Koide Q by second harmonic",
        "",
        "| nu | max Q over flux |",
        "|---:|---:|",
    ]
    for nu, value in result["max_q_by_nu"].items():
        lines.append(f"| {nu} | {value:.6f} |")
    lines += [
        "",
        "## Best scan point",
        "",
        f"- nu={best['nu']:.3g}, flux={best['flux']:.3g}.",
        f"- Energies: "
        + ", ".join(f"{value:.6f}" for value in best["energies"])
        + ".",
        f"- Koide Q: {best['koide_q']:.6f} "
        f"(target {result['koide_target']:.6f}).",
        f"- Q at n_cut=240: {result['best_n_cutoff_q']:.6f}; "
        f"delta: {result['best_convergence_delta']:.3e}.",
        f"- Zero-flux real potential is degenerate: "
        f"**{result['zero_flux_degenerate']}**.",
        "",
        f"**Status: {result['status']}.**",
        "",
        result["note"],
        "",
        f"- Config SHA-256: `{payload['meta']['config_sha256']}`",
        f"- Git: `{payload['meta']['git']['commit']}` "
        f"(dirty={payload['meta']['git']['dirty']})",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_rotor_potential_check()
    print(result["result"]["status"])
