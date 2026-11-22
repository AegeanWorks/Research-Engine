//! Deterministic statistics for recorded observations (engine/stats.py).
//!
//! Includes a port of CPython's MT19937 so `random.Random(seed).choice()`
//! produces the same bootstrap sample as the Python engine.

const ALPHA: f64 = 0.05;
const MIN_GROUP: usize = 3;
const EPS: f64 = 3.0e-12;
const MAX_ITERATIONS: usize = 300;

fn mean(values: &[f64]) -> f64 {
    if values.is_empty() { 0.0 } else { values.iter().sum::<f64>() / values.len() as f64 }
}

fn variance(values: &[f64]) -> f64 {
    if values.len() < 2 { return 0.0; }
    let m = mean(values);
    values.iter().map(|v| (v - m).powi(2)).sum::<f64>() / (values.len() - 1) as f64
}

pub fn sample_sd(values: &[f64]) -> f64 {
    if values.len() > 1 { variance(values).sqrt() } else { 0.0 }
}

pub fn cohens_d(baseline: &[f64], treatment: &[f64]) -> f64 {
    if baseline.len() < 2 || treatment.len() < 2 { return 0.0; }
    let pooled = (((baseline.len() - 1) as f64 * variance(baseline)
        + (treatment.len() - 1) as f64 * variance(treatment))
        / (baseline.len() + treatment.len() - 2) as f64).sqrt();
    if pooled == 0.0 { 0.0 } else { (mean(treatment) - mean(baseline)) / pooled }
}

fn betacf(a: f64, b: f64, x: f64) -> f64 {
    let tiny = 1.0e-30;
    let qab = a + b;
    let qap = a + 1.0;
    let qam = a - 1.0;
    let mut c: f64 = 1.0;
    let mut d: f64 = 1.0 - qab * x / qap;
    if d.abs() < tiny { d = tiny; }
    d = 1.0 / d;
    let mut h = d;
    for m in 1..=MAX_ITERATIONS {
        let m2 = 2.0 * m as f64;
        let mut aa = m as f64 * (b - m as f64) * x / ((qam + m2) * (a + m2));
        d = 1.0 + aa * d;
        if d.abs() < tiny { d = tiny; }
        c = 1.0 + aa / c;
        if c.abs() < tiny { c = tiny; }
        d = 1.0 / d;
        h *= d * c;
        aa = -(a + m as f64) * (qab + m as f64) * x / ((a + m2) * (qap + m2));
        d = 1.0 + aa * d;
        if d.abs() < tiny { d = tiny; }
        c = 1.0 + aa / c;
        if c.abs() < tiny { c = tiny; }
        d = 1.0 / d;
        let delta = d * c;
        h *= delta;
        if (delta - 1.0).abs() < EPS { break; }
    }
    h
}

fn betai(a: f64, b: f64, x: f64) -> f64 {
    if x <= 0.0 { return 0.0; }
    if x >= 1.0 { return 1.0; }
    let front = (libm::lgamma(a + b) - libm::lgamma(a) - libm::lgamma(b) + a * x.ln() + b * (1.0 - x).ln()).exp();
    if x < (a + 1.0) / (a + b + 2.0) {
        front * betacf(a, b, x) / a
    } else {
        1.0 - front * betacf(b, a, 1.0 - x) / b
    }
}

pub fn t_two_sided_p(t: f64, df: f64) -> f64 {
    if df <= 0.0 || t.is_nan() { return 1.0; }
    if t.is_infinite() { return 0.0; }
    let x = df / (df + t * t);
    betai(df / 2.0, 0.5, x).clamp(0.0, 1.0)
}

pub fn welch_t(baseline: &[f64], treatment: &[f64]) -> serde_json::Value {
    use serde_json::json;
    if baseline.len() < 2 || treatment.len() < 2 {
        return json!({"t": 0.0, "df": 0.0, "p": 1.0});
    }
    let first = variance(baseline) / baseline.len() as f64;
    let second = variance(treatment) / treatment.len() as f64;
    let denominator = first + second;
    if denominator == 0.0 {
        let difference = mean(treatment) - mean(baseline);
        let t = if difference == 0.0 { 0.0 } else { difference.signum() * f64::INFINITY };
        return json!({"t": t, "df": 0.0, "p": if difference == 0.0 { 1.0 } else { 0.0 }});
    }
    let t = (mean(treatment) - mean(baseline)) / denominator.sqrt();
    let df = denominator.powi(2)
        / (first.powi(2) / (baseline.len() - 1) as f64
            + second.powi(2) / (treatment.len() - 1) as f64);
    json!({"t": t, "df": df, "p": t_two_sided_p(t, df)})
}

fn ranks(values: &[f64]) -> (Vec<f64>, Vec<usize>) {
    let mut order: Vec<usize> = (0..values.len()).collect();
    order.sort_by(|a, b| values[*a].partial_cmp(&values[*b]).unwrap_or(std::cmp::Ordering::Equal));
    let mut result = vec![0.0; values.len()];
    let mut ties = Vec::new();
    let mut index = 0;
    while index < order.len() {
        let mut end = index;
        while end + 1 < order.len() && values[order[end + 1]] == values[order[index]] { end += 1; }
        let average = (index + end) as f64 / 2.0 + 1.0;
        for position in index..=end { result[order[position]] = average; }
        if end > index { ties.push(end - index + 1); }
        index = end + 1;
    }
    (result, ties)
}

fn u_distribution(n1: usize, n2: usize) -> Vec<u128> {
    let width = n1 * n2 + 1;
    let mut table = vec![vec![vec![0u128; width]; n2 + 1]; n1 + 1];
    for first in 0..=n1 {
        for second in 0..=n2 {
            if first == 0 || second == 0 { table[first][second][0] = 1; continue; }
            for value in 0..=first * second {
                let mut count = 0u128;
                if value >= second { count += table[first - 1][second][value - second]; }
                count += table[first][second - 1][value];
                table[first][second][value] = count;
            }
        }
    }
    table[n1][n2].clone()
}

pub fn mann_whitney(baseline: &[f64], treatment: &[f64]) -> serde_json::Value {
    use serde_json::json;
    let (n1, n2) = (baseline.len(), treatment.len());
    if n1 == 0 || n2 == 0 {
        return json!({"u": 0.0, "z": 0.0, "p": 1.0, "method": "empty"});
    }
    let mut combined = baseline.to_vec();
    combined.extend_from_slice(treatment);
    let (ranks, ties) = ranks(&combined);
    let rank_sum: f64 = ranks[..n1].iter().sum();
    let u1 = rank_sum - n1 as f64 * (n1 + 1) as f64 / 2.0;
    let u = u1.min(n1 as f64 * n2 as f64 - u1);
    if ties.is_empty() && n1 * n2 <= 400 {
        let counts = u_distribution(n1, n2);
        let total = binomial(n1 + n2, n1) as f64;
        let upper = u1.round() as usize;
        let lower_sum: f64 = counts[..=upper].iter().map(|v| *v as f64).sum();
        let upper_sum: f64 = counts[upper..].iter().map(|v| *v as f64).sum();
        let p = (2.0 * lower_sum.min(upper_sum) / total).min(1.0);
        return json!({"u": u, "z": 0.0, "p": p, "method": "exact"});
    }
    let total = n1 + n2;
    let tie_term: f64 = ties.iter().map(|size| (size.pow(3) - size) as f64).sum();
    let sigma_squared = n1 as f64 * n2 as f64 / 12.0
        * ((total + 1) as f64 - tie_term / (total * (total - 1)) as f64);
    if sigma_squared <= 0.0 {
        return json!({"u": u, "z": 0.0, "p": 1.0, "method": "degenerate"});
    }
    let expected = n1 as f64 * n2 as f64 / 2.0;
    let correction = if u1 > expected { 0.5 } else if u1 < expected { -0.5 } else { 0.0 };
    let z = (u1 - expected - correction) / sigma_squared.sqrt();
    let p = (1.0 - libm::erf(z.abs() / 2.0_f64.sqrt())).min(1.0).max(0.0);
    json!({"u": u, "z": z, "p": p, "method": "asymptotic"})
}

fn binomial(n: usize, k: usize) -> u128 {
    let k = k.min(n - k);
    let mut result = 1u128;
    for i in 1..=k { result = result * (n - k + i) as u128 / i as u128; }
    result
}

pub fn holm_adjust(p_values: &[f64]) -> Vec<serde_json::Value> {
    use serde_json::json;
    let mut order: Vec<usize> = (0..p_values.len()).collect();
    order.sort_by(|a, b| p_values[*a].partial_cmp(&p_values[*b]).unwrap_or(std::cmp::Ordering::Equal).then(a.cmp(b)));
    let mut adjusted = vec![0.0; p_values.len()];
    let mut ceiling: f64 = 0.0;
    for (rank, index) in order.iter().enumerate() {
        ceiling = ceiling.max(((p_values.len() - rank) as f64 * p_values[*index]).clamp(0.0, 1.0));
        adjusted[*index] = ceiling;
    }
    (0..p_values.len()).map(|i| json!({
        "index": i, "p": p_values[i], "holm_p": adjusted[i], "reject": adjusted[i] <= ALPHA,
    })).collect()
}

/// CPython MT19937, seeded and sampled exactly like `random.Random(seed)`.
pub struct PyRandom {
    state: [u32; 624],
    index: usize,
}

impl PyRandom {
    pub fn new(seed: i64) -> Self {
        let mut rng = Self { state: [0; 624], index: 624 };
        let mut words = Vec::new();
        let mut value = seed.unsigned_abs();
        loop {
            words.push((value & 0xffff_ffff) as u32);
            value >>= 32;
            if value == 0 { break; }
        }
        rng.init_by_array(&words);
        rng
    }

    fn init_genrand(&mut self, seed: u32) {
        self.state[0] = seed;
        for i in 1..624 {
            self.state[i] = 1812433253u32
                .wrapping_mul(self.state[i - 1] ^ (self.state[i - 1] >> 30))
                .wrapping_add(i as u32);
        }
        self.index = 624;
    }

    fn init_by_array(&mut self, key: &[u32]) {
        self.init_genrand(19650218);
        let mut i = 1usize;
        let mut j = 0usize;
        for _ in 0..624.max(key.len()) {
            self.state[i] = (self.state[i]
                ^ ((self.state[i - 1] ^ (self.state[i - 1] >> 30)).wrapping_mul(1664525)))
                .wrapping_add(key[j]).wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= 624 { self.state[0] = self.state[623]; i = 1; }
            if j >= key.len() { j = 0; }
        }
        for _ in 0..623 {
            self.state[i] = (self.state[i]
                ^ ((self.state[i - 1] ^ (self.state[i - 1] >> 30)).wrapping_mul(1566083941)))
                .wrapping_sub(i as u32);
            i += 1;
            if i >= 624 { self.state[0] = self.state[623]; i = 1; }
        }
        self.state[0] = 0x8000_0000;
    }

    pub fn next_u32(&mut self) -> u32 {
        if self.index >= 624 {
            for i in 0..624 {
                let y = (self.state[i] & 0x8000_0000)
                    | (self.state[(i + 1) % 624] & 0x7fff_ffff);
                let mut next = self.state[(i + 397) % 624] ^ (y >> 1);
                if y % 2 == 1 { next ^= 0x9908_b0df; }
                self.state[i] = next;
            }
            self.index = 0;
        }
        let mut y = self.state[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c_5680;
        y ^= (y << 15) & 0xefc6_0000;
        y ^= y >> 18;
        y
    }

    pub fn getrandbits(&mut self, k: u32) -> u64 {
        if k == 0 { return 0; }
        if k <= 32 { return (self.next_u32() >> (32 - k)) as u64; }
        let words = (k + 31) / 32;
        let mut result = 0u64;
        for i in 0..words {
            result |= (self.next_u32() as u64) << (32 * i);
        }
        result >> (words * 32 - k)
    }

    pub fn randbelow(&mut self, n: usize) -> usize {
        let k = (64 - (n as u64).leading_zeros()).max(1); // int.bit_length()
        loop {
            let r = self.getrandbits(k);
            if r < n as u64 { return r as usize; }
        }
    }

    pub fn choice<'a, T>(&mut self, values: &'a [T]) -> &'a T {
        &values[self.randbelow(values.len())]
    }
}

pub fn bootstrap_ci(baseline: &[f64], treatment: &[f64], seed: i64, resamples: usize) -> serde_json::Value {
    use serde_json::json;
    if baseline.is_empty() || treatment.is_empty() || resamples < 1 {
        return json!({"low": 0.0, "high": 0.0, "resamples": 0, "seed": seed});
    }
    let mut rng = PyRandom::new(seed);
    let mut differences = Vec::with_capacity(resamples);
    for _ in 0..resamples {
        let mut first = 0.0;
        for _ in 0..baseline.len() { first += *rng.choice(baseline); }
        let mut second = 0.0;
        for _ in 0..treatment.len() { second += *rng.choice(treatment); }
        differences.push(second / treatment.len() as f64 - first / baseline.len() as f64);
    }
    differences.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let round = |v: f64| -> usize { (v).round() as usize };
    let low = round(0.025 * (resamples - 1) as f64).max(0);
    let high = round(0.975 * (resamples - 1) as f64).min(resamples - 1);
    json!({"low": differences[low], "high": differences[high], "resamples": resamples, "seed": seed})
}

pub fn pearson(xs: &[f64], ys: &[f64]) -> serde_json::Value {
    use serde_json::json;
    let pairs: Vec<(f64, f64)> = xs.iter().zip(ys)
        .filter(|(x, y)| x.is_finite() && y.is_finite())
        .map(|(x, y)| (*x, *y)).collect();
    let n = pairs.len();
    if n < MIN_GROUP { return json!({"r": 0.0, "n": n}); }
    let xm = mean(&pairs.iter().map(|p| p.0).collect::<Vec<_>>());
    let ym = mean(&pairs.iter().map(|p| p.1).collect::<Vec<_>>());
    let sxx: f64 = pairs.iter().map(|p| (p.0 - xm).powi(2)).sum();
    let syy: f64 = pairs.iter().map(|p| (p.1 - ym).powi(2)).sum();
    if sxx == 0.0 || syy == 0.0 { return json!({"r": 0.0, "n": n}); }
    let sxy: f64 = pairs.iter().map(|p| (p.0 - xm) * (p.1 - ym)).sum();
    json!({"r": (sxy / (sxx * syy).sqrt()).clamp(-1.0, 1.0), "n": n})
}

pub fn linregress(xs: &[f64], ys: &[f64]) -> serde_json::Value {
    use serde_json::json;
    let pairs: Vec<(f64, f64)> = xs.iter().zip(ys)
        .filter(|(x, y)| x.is_finite() && y.is_finite())
        .map(|(x, y)| (*x, *y)).collect();
    let n = pairs.len();
    if n < 3 { return json!({"slope": 0.0, "intercept": 0.0, "r": 0.0, "p": 1.0, "n": n}); }
    let xm = mean(&pairs.iter().map(|p| p.0).collect::<Vec<_>>());
    let ym = mean(&pairs.iter().map(|p| p.1).collect::<Vec<_>>());
    let sxx: f64 = pairs.iter().map(|p| (p.0 - xm).powi(2)).sum();
    let syy: f64 = pairs.iter().map(|p| (p.1 - ym).powi(2)).sum();
    let sxy: f64 = pairs.iter().map(|p| (p.0 - xm) * (p.1 - ym)).sum();
    if sxx == 0.0 || syy == 0.0 {
        return json!({"slope": 0.0, "intercept": ym, "r": 0.0, "p": 1.0, "n": n});
    }
    let slope = sxy / sxx;
    let intercept = ym - slope * xm;
    let r = sxy / (sxx * syy).sqrt();
    let degrees = (n - 2) as f64;
    let p = if r.abs() >= 1.0 { 0.0 } else {
        t_two_sided_p(r * (degrees / (1.0 - r * r)).sqrt(), degrees)
    };
    json!({"slope": slope, "intercept": intercept, "r": r, "p": p, "n": n})
}

pub fn compare_groups(baseline: &[f64], treatment: &[f64], seed: i64, resamples: usize) -> serde_json::Value {
    use serde_json::json;
    let difference = if baseline.is_empty() || treatment.is_empty() { 0.0 }
        else { mean(treatment) - mean(baseline) };
    let parametric = welch_t(baseline, treatment);
    let nonparametric = mann_whitney(baseline, treatment);
    let interval = bootstrap_ci(baseline, treatment, seed, resamples);
    let mut warnings = Vec::new();
    if baseline.len() < MIN_GROUP || treatment.len() < MIN_GROUP {
        warnings.push(format!("fewer than {MIN_GROUP} observations in a group"));
    }
    if sample_sd(baseline) == 0.0 && sample_sd(treatment) == 0.0 {
        warnings.push("no variance in either group; the tests are degenerate".to_string());
    }
    if nonparametric.get("method").and_then(|v| v.as_str()) == Some("asymptotic") {
        warnings.push("rank test uses the normal approximation because of ties or sample size".to_string());
    }
    let pw = parametric.get("p").and_then(|v| v.as_f64()).unwrap_or(1.0);
    let mw = nonparametric.get("p").and_then(|v| v.as_f64()).unwrap_or(1.0);
    let significant = [pw < ALPHA, mw < ALPHA];
    if significant[0] != significant[1] {
        warnings.push("parametric and non-parametric tests disagree at alpha=0.05".to_string());
    }
    json!({
        "baseline": {"n": baseline.len(), "mean": mean(baseline), "sd": sample_sd(baseline)},
        "treatment": {"n": treatment.len(), "mean": mean(treatment), "sd": sample_sd(treatment)},
        "difference": difference,
        "cohens_d": cohens_d(baseline, treatment),
        "welch": parametric,
        "mann_whitney": nonparametric,
        "bootstrap": interval,
        "alpha": ALPHA,
        "tests_agree": significant[0] == significant[1],
        "significant": significant[0] && significant[1],
        "warnings": warnings,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn python_random_compatibility() {
        // Values produced by CPython 3.14: random.Random(0).getrandbits(32) x3
        let mut rng = PyRandom::new(0);
        let actual = [rng.next_u32(), rng.next_u32(), rng.next_u32()];
        assert_eq!(actual, [3626764237, 1654615998, 3255389356]);
    }

    #[test]
    fn python_statistics_compatibility() {
        let result = compare_groups(&[1.0, 2.0, 3.0], &[2.0, 3.0, 4.0], 0, 2000);
        let approx = |a: f64, b: f64| assert!((a - b).abs() < 1e-12, "{a} != {b}");
        approx(result["baseline"]["mean"].as_f64().unwrap(), 2.0);
        approx(result["cohens_d"].as_f64().unwrap(), 1.0);
        approx(result["welch"]["p"].as_f64().unwrap(), 0.2878641347266906);
        approx(result["mann_whitney"]["p"].as_f64().unwrap(), 0.36868826936178156);
        approx(result["bootstrap"]["low"].as_f64().unwrap(), -0.3333333333333335);
        approx(result["bootstrap"]["high"].as_f64().unwrap(), 2.333333333333333);
        let trend = linregress(&[1.0, 2.0, 3.0, 4.0], &[2.0, 4.0, 5.0, 7.0]);
        approx(trend["slope"].as_f64().unwrap(), 1.6);
        approx(trend["p"].as_f64().unwrap(), 0.007722123286332234);
    }

    #[test]
    fn python_choice_compatibility() {
        let values = [1.0, 2.0, 3.0, 4.0];
        let mut rng = PyRandom::new(0);
        let picked: Vec<f64> = (0..8).map(|_| *rng.choice(&values)).collect();
        assert_eq!(picked, [4.0, 4.0, 1.0, 3.0, 4.0, 4.0, 3.0, 4.0]);
        let values = [1.0, 2.0, 3.0];
        let mut rng = PyRandom::new(7);
        let picked: Vec<f64> = (0..5).map(|_| *rng.choice(&values)).collect();
        assert_eq!(picked, [2.0, 1.0, 2.0, 3.0, 1.0]);
    }
}
