"""Statistics: values checked against an independent implementation, behaviour checked here."""

from __future__ import annotations

import math
import unittest

from engine.stats import (
    bootstrap_ci,
    cohens_d,
    compare_groups,
    linregress,
    mann_whitney,
    sample_sd,
    t_two_sided_p,
    welch_t,
)

A = [1.2, 1.4, 1.1, 1.3, 1.25, 1.35]
B = [1.9, 2.1, 2.0, 2.2, 1.95, 2.05]
X = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
Y = [2.0, 1.0, 4.0, 3.0, 6.0, 5.0]


class DistributionTests(unittest.TestCase):
    def test_sample_sd(self) -> None:
        self.assertEqual(sample_sd([5.0]), 0.0)
        self.assertAlmostEqual(sample_sd([1.0, 3.0]), math.sqrt(2.0), places=12)

    def test_t_p_value_matches_reference(self) -> None:
        self.assertAlmostEqual(t_two_sided_p(2.228, 10), 0.05001177181711132, places=10)

    def test_t_p_value_edges(self) -> None:
        self.assertEqual(t_two_sided_p(0.0, 10), 1.0)
        self.assertEqual(t_two_sided_p(math.inf, 10), 0.0)
        self.assertEqual(t_two_sided_p(2.0, 0), 1.0)


class TestTests(unittest.TestCase):
    def test_welch_matches_reference(self) -> None:
        result = welch_t(A, B)
        self.assertAlmostEqual(result["t"], 12.294017127971518, places=9)
        self.assertAlmostEqual(result["df"], 10.0, places=9)
        self.assertAlmostEqual(result["p"], 2.3258907980501515e-07, places=15)

    def test_welch_degenerate_group(self) -> None:
        result = welch_t([1.0], [2.0])
        self.assertEqual(result["p"], 1.0)

    def test_welch_zero_variance(self) -> None:
        same = welch_t([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
        self.assertEqual(same["p"], 1.0)
        different = welch_t([1.0, 1.0, 1.0], [2.0, 2.0, 2.0])
        self.assertEqual(different["p"], 0.0)

    def test_mann_whitney_exact_matches_reference(self) -> None:
        result = mann_whitney(A, B)
        self.assertEqual(result["method"], "exact")
        self.assertEqual(result["u"], 0.0)
        self.assertAlmostEqual(result["p"], 0.0021645021645021645, places=12)

    def test_mann_whitney_uses_asymptotic_with_ties(self) -> None:
        result = mann_whitney([1, 1, 2, 2], [2, 3, 3, 4])
        self.assertEqual(result["method"], "asymptotic")
        self.assertAlmostEqual(result["p"], 0.05150833604880684, places=10)

    def test_mann_whitney_empty(self) -> None:
        self.assertEqual(mann_whitney([], B)["p"], 1.0)

    def test_effect_size_matches_reference(self) -> None:
        self.assertAlmostEqual(cohens_d(A, B), 7.097954098256226, places=9)

    def test_effect_size_needs_two_values_per_group(self) -> None:
        self.assertEqual(cohens_d([1.0], [5.0]), 0.0)


class IntervalTests(unittest.TestCase):
    def test_bootstrap_is_seeded_and_reproducible(self) -> None:
        first = bootstrap_ci(A, B, seed=7, resamples=300)
        second = bootstrap_ci(A, B, seed=7, resamples=300)
        self.assertEqual(first, second)
        self.assertEqual(first["seed"], 7)
        self.assertEqual(first["resamples"], 300)

    def test_bootstrap_brackets_the_difference(self) -> None:
        result = bootstrap_ci(A, B, seed=0, resamples=400)
        self.assertLess(result["low"], result["high"])
        self.assertLess(result["low"], 0.77)
        self.assertGreater(result["high"], 0.77)

    def test_bootstrap_empty(self) -> None:
        self.assertEqual(bootstrap_ci([], B)["resamples"], 0)


class RegressionTests(unittest.TestCase):
    def test_linregress_matches_reference(self) -> None:
        result = linregress(X, Y)
        self.assertAlmostEqual(result["slope"], 0.8285714285714285, places=10)
        self.assertAlmostEqual(result["intercept"], 0.6, places=10)
        self.assertAlmostEqual(result["r"], 0.8285714285714285, places=10)
        self.assertAlmostEqual(result["p"], 0.04156268221574349, places=10)

    def test_linregress_too_few_points(self) -> None:
        self.assertEqual(linregress([1, 2], [1, 2])["p"], 1.0)

    def test_linregress_flat_line(self) -> None:
        self.assertEqual(linregress([1, 2, 3], [2, 2, 2])["slope"], 0.0)


class CompareTests(unittest.TestCase):
    def test_significant_difference_with_agreeing_tests(self) -> None:
        result = compare_groups(A, B, resamples=200)
        self.assertTrue(result["significant"])
        self.assertTrue(result["tests_agree"])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["mann_whitney"]["method"], "exact")

    def test_small_groups_warn(self) -> None:
        result = compare_groups([1.0, 2.0], [3.0, 4.0], resamples=100)
        self.assertTrue(any("fewer than" in warning for warning in result["warnings"]))

    def test_zero_variance_warns(self) -> None:
        result = compare_groups([1.0, 1.0, 1.0], [1.0, 1.0, 1.0], resamples=50)
        self.assertTrue(any("degenerate" in warning for warning in result["warnings"]))

    def test_ties_are_disclosed(self) -> None:
        result = compare_groups([1.0, 1.0, 2.0, 2.0], [2.0, 3.0, 3.0, 4.0], resamples=50)
        self.assertTrue(any("normal approximation" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
