"""Deterministic statistics for recorded observations.

Standard library only, seeded, and reproducible. The engine records repeated measurements against a
claim, then reports the difference between a baseline and a treatment group with effect size, a
parametric test, a non-parametric test, and a percentile bootstrap interval. Agreement between the
two tests is reported rather than hidden: a significant t-test next to a non-significant rank test
is a fact about the data, not a formatting choice.
"""

from __future__ import annotations

import math
import random
from statistics import mean, variance
from typing import Dict, List, Sequence, Tuple

ALPHA = 0.05
MIN_GROUP = 3
DEFAULT_RESAMPLES = 2000
DEFAULT_SEED = 0
_EPS = 3.0e-12
_MAX_ITERATIONS = 300


def sample_sd(values: Sequence[float]) -> float:
    """Sample standard deviation; zero for fewer than two values."""
    return math.sqrt(variance(values)) if len(values) > 1 else 0.0


def cohens_d(baseline: Sequence[float], treatment: Sequence[float]) -> float:
    """Standardized mean difference using the pooled standard deviation."""
    if len(baseline) < 2 or len(treatment) < 2:
        return 0.0
    pooled = math.sqrt(
        ((len(baseline) - 1) * variance(baseline) + (len(treatment) - 1) * variance(treatment))
        / (len(baseline) + len(treatment) - 2)
    )
    if pooled == 0:
        return 0.0
    return (mean(treatment) - mean(baseline)) / pooled


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1.0e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, _MAX_ITERATIONS + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    """Two-sided p-value for a t statistic with the given degrees of freedom."""
    if df <= 0 or math.isnan(t):
        return 1.0
    if math.isinf(t):
        return 0.0
    x = df / (df + t * t)
    return min(max(_betai(df / 2.0, 0.5, x), 0.0), 1.0)


def welch_t(baseline: Sequence[float], treatment: Sequence[float]) -> Dict[str, float]:
    """Welch's unequal-variance t test, with the zero-variance case handled explicitly."""
    if len(baseline) < 2 or len(treatment) < 2:
        return {"t": 0.0, "df": 0.0, "p": 1.0}
    first = variance(baseline) / len(baseline)
    second = variance(treatment) / len(treatment)
    denominator = first + second
    if denominator == 0:
        difference = mean(treatment) - mean(baseline)
        return {"t": 0.0 if difference == 0 else math.copysign(math.inf, difference),
                "df": 0.0, "p": 1.0 if difference == 0 else 0.0}
    t = (mean(treatment) - mean(baseline)) / math.sqrt(denominator)
    df = denominator ** 2 / (
        first ** 2 / (len(baseline) - 1) + second ** 2 / (len(treatment) - 1)
    )
    return {"t": t, "df": df, "p": t_two_sided_p(t, df)}


def _ranks(values: Sequence[float]) -> Tuple[List[float], List[int]]:
    """Average ranks for ties, returning the ranks and the tie-group sizes."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    ties: List[int] = []
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            ranks[order[position]] = average
        if end > index:
            ties.append(end - index + 1)
        index = end + 1
    return ranks, ties


def _u_distribution(n1: int, n2: int) -> List[int]:
    """Counts of the U statistic under the null, by dynamic programming.

    `F(n1, n2, u) = F(n1 - 1, n2, u - n2) + F(n1, n2 - 1, u)`: each arrangement either places an
    item from the first group last (shifting U by n2) or from the second group last.
    """
    table = [[[0] * (n1 * n2 + 1) for _ in range(n2 + 1)] for _ in range(n1 + 1)]
    for first in range(n1 + 1):
        for second in range(n2 + 1):
            if first == 0 or second == 0:
                table[first][second][0] = 1
                continue
            for value in range(first * second + 1):
                count = 0
                shifted = value - second
                if shifted >= 0:
                    count += table[first - 1][second][shifted]
                count += table[first][second - 1][value]
                table[first][second][value] = count
    return table[n1][n2]


def _exact_u_two_sided_p(u1: float, n1: int, n2: int) -> float:
    """Exact two-sided p for the U statistic when the sample is small and untied."""
    counts = _u_distribution(n1, n2)
    total = math.comb(n1 + n2, n1)
    u1 = int(round(u1))
    lower = sum(counts[: u1 + 1])
    upper = sum(counts[u1:])
    return min(2.0 * min(lower, upper) / total, 1.0)


def mann_whitney(baseline: Sequence[float], treatment: Sequence[float]) -> Dict[str, float]:
    """Mann-Whitney U: exact for small untied samples, continuity-corrected asymptotic otherwise.

    The exact null distribution is used when it is cheap and valid (no ties, n1*n2 <= 400); ties
    make it invalid, so the tie-corrected normal approximation takes over and the chosen method is
    reported as `method`.
    """
    n1, n2 = len(baseline), len(treatment)
    if n1 == 0 or n2 == 0:
        return {"u": 0.0, "z": 0.0, "p": 1.0, "method": "empty"}
    combined = list(baseline) + list(treatment)
    ranks, ties = _ranks(combined)
    rank_sum = sum(ranks[:n1])
    u1 = rank_sum - n1 * (n1 + 1) / 2.0
    u = min(u1, n1 * n2 - u1)
    if not ties and n1 * n2 <= 400:
        return {
            "u": u,
            "z": 0.0,
            "p": _exact_u_two_sided_p(u1, n1, n2),
            "method": "exact",
        }
    total = n1 + n2
    tie_term = sum(size ** 3 - size for size in ties)
    sigma_squared = n1 * n2 / 12.0 * ((total + 1) - tie_term / (total * (total - 1)))
    if sigma_squared <= 0:
        return {"u": u, "z": 0.0, "p": 1.0, "method": "degenerate"}
    expected = n1 * n2 / 2.0
    correction = 0.5 if u1 > expected else -0.5 if u1 < expected else 0.0
    z = (u1 - expected - correction) / math.sqrt(sigma_squared)
    p = 2.0 * (0.5 * (1.0 - math.erf(abs(z) / math.sqrt(2.0))))
    return {"u": u, "z": z, "p": min(max(p, 0.0), 1.0), "method": "asymptotic"}


def bootstrap_ci(
    baseline: Sequence[float],
    treatment: Sequence[float],
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
) -> Dict[str, float]:
    """Percentile bootstrap interval for the difference in means, reproducibly seeded."""
    if not baseline or not treatment or resamples < 1:
        return {"low": 0.0, "high": 0.0, "resamples": 0, "seed": seed}
    generator = random.Random(seed)
    differences = []
    for _ in range(resamples):
        first = [generator.choice(baseline) for _ in baseline]
        second = [generator.choice(treatment) for _ in treatment]
        differences.append(mean(second) - mean(first))
    differences.sort()
    low_index = max(int(round(0.025 * (resamples - 1))), 0)
    high_index = min(int(round(0.975 * (resamples - 1))), resamples - 1)
    return {
        "low": differences[low_index],
        "high": differences[high_index],
        "resamples": resamples,
        "seed": seed,
    }


def linregress(xs: Sequence[float], ys: Sequence[float]) -> Dict[str, float]:
    """Least-squares slope, intercept, correlation and two-sided p for paired points."""
    pairs = [(x, y) for x, y in zip(xs, ys) if not (math.isnan(x) or math.isnan(y))]
    n = len(pairs)
    if n < 3:
        return {"slope": 0.0, "intercept": 0.0, "r": 0.0, "p": 1.0, "n": n}
    xs_clean = [pair[0] for pair in pairs]
    ys_clean = [pair[1] for pair in pairs]
    x_mean = mean(xs_clean)
    y_mean = mean(ys_clean)
    sxx = sum((x - x_mean) ** 2 for x in xs_clean)
    syy = sum((y - y_mean) ** 2 for y in ys_clean)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    if sxx == 0 or syy == 0:
        return {"slope": 0.0, "intercept": y_mean, "r": 0.0, "p": 1.0, "n": n}
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    r = sxy / math.sqrt(sxx * syy)
    degrees = n - 2
    if abs(r) >= 1.0:
        p = 0.0
    else:
        t = r * math.sqrt(degrees / (1.0 - r * r))
        p = t_two_sided_p(t, degrees)
    return {"slope": slope, "intercept": intercept, "r": r, "p": p, "n": n}


def compare_groups(
    baseline: Sequence[float],
    treatment: Sequence[float],
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
) -> dict:
    """Compare two recorded groups and state the result, the agreement and the caveats."""
    first = [float(value) for value in baseline]
    second = [float(value) for value in treatment]
    difference = mean(second) - mean(first) if first and second else 0.0
    parametric = welch_t(first, second)
    nonparametric = mann_whitney(first, second)
    interval = bootstrap_ci(first, second, seed=seed, resamples=resamples)
    warnings: List[str] = []
    if len(first) < MIN_GROUP or len(second) < MIN_GROUP:
        warnings.append(f"fewer than {MIN_GROUP} observations in a group")
    if sample_sd(first) == 0 and sample_sd(second) == 0:
        warnings.append("no variance in either group; the tests are degenerate")
    if nonparametric.get("method") == "asymptotic":
        warnings.append("rank test uses the normal approximation because of ties or sample size")
    significant = [parametric["p"] < ALPHA, nonparametric["p"] < ALPHA]
    if significant[0] != significant[1]:
        warnings.append("parametric and non-parametric tests disagree at alpha=0.05")
    return {
        "baseline": {
            "n": len(first),
            "mean": mean(first) if first else 0.0,
            "sd": sample_sd(first),
        },
        "treatment": {
            "n": len(second),
            "mean": mean(second) if second else 0.0,
            "sd": sample_sd(second),
        },
        "difference": difference,
        "cohens_d": cohens_d(first, second),
        "welch": parametric,
        "mann_whitney": nonparametric,
        "bootstrap": interval,
        "alpha": ALPHA,
        "tests_agree": significant[0] == significant[1],
        "significant": bool(significant[0] and significant[1]),
        "warnings": warnings,
    }
