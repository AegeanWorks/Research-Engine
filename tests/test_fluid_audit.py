"""Fluid-universe audit primitives stay callable after the port."""

from __future__ import annotations

import math
import unittest

import numpy as np

from domains.fluid_universe.verification.audit import (
    circulant,
    fit_linear,
    q_from_ac,
    q_from_masses,
    roots_from_ac,
)


class FluidAuditPrimitiveTests(unittest.TestCase):
    def test_circulant_is_hermitian_and_has_the_analytic_roots(self) -> None:
        matrix = circulant(2.0, 1.0, 0.4)
        self.assertTrue((matrix == matrix.conj().T).all())
        observed = sorted(float(value.real) for value in np.linalg.eigvalsh(matrix))
        expected = sorted(float(value) for value in roots_from_ac(2.0, 1.0, 0.4))
        for left, right in zip(observed, expected):
            self.assertAlmostEqual(left, right, places=10)

    def test_koide_identity_and_inverse_fit(self) -> None:
        self.assertAlmostEqual(q_from_ac(1.0, 1.0 / math.sqrt(2.0)), 2.0 / 3.0, places=12)
        a, c, delta = fit_linear(roots_from_ac(2.0, 0.7, 0.3))
        self.assertAlmostEqual(a, 2.0, places=10)
        self.assertAlmostEqual(c, 0.7, places=10)
        self.assertAlmostEqual(delta, 0.3, places=10)

    def test_mass_definition_matches_the_square_root_convention(self) -> None:
        self.assertAlmostEqual(q_from_masses([1.0, 2.0, 3.0]), 6.0 / (1 + math.sqrt(2) + math.sqrt(3)) ** 2, places=12)
