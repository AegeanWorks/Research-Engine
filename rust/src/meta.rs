//! Quantitative meta-analysis (adapters/lattice/meta.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const Z: f64 = 1.959964;

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number(value: &Value, name: &str) -> f64 {
    value.get(name).and_then(Value::as_f64).unwrap_or(0.0)
}

fn round_to(value: f64, decimals: i32) -> f64 {
    let factor = 10f64.powi(decimals);
    let scaled = value * factor;
    let floor = scaled.floor();
    let fraction = scaled - floor;
    let rounded = if (fraction - 0.5).abs() < 1e-12 {
        if (floor as i64) % 2 == 0 { floor } else { floor + 1.0 }
    } else { scaled.round() };
    rounded / factor
}

fn chi2_sf(x: f64, df: i64) -> f64 {
    if df <= 0 || x <= 0.0 { return 1.0; }
    let a = df as f64 / 2.0;
    let z = x / 2.0;
    let t0 = (-z + a * z.ln() - libm::lgamma(a + 1.0)).exp();
    let mut term = t0;
    let mut total = term;
    for n in 1..300 {
        term *= z / (a + n as f64);
        total += term;
        if term < 1e-15 * total { break; }
    }
    (1.0f64 - total).clamp(0.0f64, 1.0f64)
}

pub fn study_from_ci(id: &str, label: &str, effect: f64, lower: f64, upper: f64,
                     study_type: &str) -> Result<Value> {
    if upper < lower {
        return Err(EngineError::new("invalid confidence interval", "ci_upper must be greater than ci_lower", "pass valid interval bounds"));
    }
    let mut se = (upper - lower) / (2.0 * Z);
    if se <= 0.0 { se = 1e-6; }
    Ok(study(id, label, effect, se, lower, upper, study_type))
}

fn study(id: &str, label: &str, effect: f64, se: f64, lower: f64, upper: f64, study_type: &str) -> Value {
    json!({
        "id": id.trim(),
        "label": if label.trim().is_empty() { id.trim() } else { label.trim() },
        "effect_size": round_to(effect, 4),
        "se": round_to(se, 4),
        "ci_lower": round_to(lower, 4),
        "ci_upper": round_to(upper, 4),
        "weight": 0.0,
        "study_type": if study_type.trim().is_empty() { "General Study" } else { study_type.trim() },
    })
}

pub fn study_from_groups(id: &str, label: &str, n1: i64, m1: f64, sd1: f64,
                         n2: i64, m2: f64, sd2: f64, study_type: &str) -> Result<Value> {
    if n1 <= 1 || n2 <= 1 {
        return Err(EngineError::new("sample size too small", "each arm requires at least 2 participants", "provide n >= 2"));
    }
    if sd1 <= 0.0 || sd2 <= 0.0 {
        return Err(EngineError::new("invalid standard deviation", "standard deviations must be strictly positive", "provide sd > 0"));
    }
    let df = n1 + n2 - 2;
    let mut sd_pooled = (((n1 - 1) as f64 * sd1.powi(2) + (n2 - 1) as f64 * sd2.powi(2)) / df as f64).sqrt();
    if sd_pooled <= 0.0 { sd_pooled = 1e-6; }
    let cohen_d = (m1 - m2) / sd_pooled;
    let j = 1.0 - (3.0 / (4.0 * (n1 + n2) as f64 - 9.0));
    let g = cohen_d * j;
    let variance = (n1 + n2) as f64 / (n1 * n2) as f64 + g.powi(2) / (2.0 * (n1 + n2) as f64);
    let se = variance.sqrt();
    Ok(study(id, label, g, se, g - Z * se, g + Z * se,
        if study_type.trim().is_empty() { "Randomized Controlled Trial" } else { study_type.trim() }))
}

fn coerce_study(item: &Value) -> Result<Value> {
    if !item.is_object() {
        return Err(EngineError::new("invalid study specification", "each study must be a dictionary or MetaStudy", "pass study objects"));
    }
    let s_id = {
        let value = field(item, "id");
        let value = if value.is_empty() { field(item, "paper_id") } else { value };
        let value = if value.is_empty() { field(item, "label") } else { value };
        if value.is_empty() { "study".to_string() } else { value }
    };
    let label = {
        let value = field(item, "label");
        if value.is_empty() { field(item, "title") } else { value }
    };
    let label = if label.is_empty() { s_id.clone() } else { label };
    let study_type = field(item, "study_type");
    let study_type = if study_type.is_empty() { "General Study".to_string() } else { study_type };

    if item.get("n1").is_some() && item.get("m1").is_some() && item.get("sd1").is_some() {
        return study_from_groups(&s_id, &label,
            item.get("n1").and_then(Value::as_i64).unwrap_or(0), number(item, "m1"), number(item, "sd1"),
            item.get("n2").and_then(Value::as_i64).unwrap_or(0), number(item, "m2"), number(item, "sd2"),
            &study_type);
    }
    let effect = if item.get("effect_size").is_some() { number(item, "effect_size") } else { number(item, "effect") };
    let (se, lower, upper) = if item.get("se").is_some() {
        let mut se = number(item, "se");
        if se <= 0.0 { se = 1e-6; }
        let lower = if item.get("ci_lower").is_some() { number(item, "ci_lower") } else { effect - Z * se };
        let upper = if item.get("ci_upper").is_some() { number(item, "ci_upper") } else { effect + Z * se };
        (se, lower, upper)
    } else if item.get("ci_lower").is_some() && item.get("ci_upper").is_some() {
        let lower = number(item, "ci_lower");
        let upper = number(item, "ci_upper");
        let mut se = (upper - lower) / (2.0 * Z);
        if se <= 0.0 { se = 1e-6; }
        (se, lower, upper)
    } else {
        let conf = if item.get("confidence").is_some() { number(item, "confidence") } else { 0.7 };
        let se = (0.05f64).max(round_to(1.0 - conf * 0.8, 3));
        (se, effect - Z * se, effect + Z * se)
    };
    Ok(study(&s_id, &label, effect, se, lower, upper, &study_type))
}

pub fn compute_meta_analysis(studies: &[Value], model: &str) -> Result<Value> {
    if studies.is_empty() {
        return Err(EngineError::new("no studies provided for meta-analysis", "meta-analysis requires at least 1 study", "pass a non-empty sequence of studies"));
    }
    let model_name = model.trim().to_lowercase();
    if model_name != "fixed" && model_name != "random" {
        return Err(EngineError::new(format!("unknown meta-analysis model '{model}'"), "model must be 'fixed' or 'random'", "choose model='fixed' or model='random'"));
    }
    let parsed: Vec<Value> = studies.iter().map(coerce_study).collect::<Result<Vec<_>>>()?;
    let k = parsed.len();
    let variances: Vec<f64> = parsed.iter().map(|s| (number(s, "se").powi(2)).max(1e-8)).collect();
    let fixed_weights: Vec<f64> = variances.iter().map(|v| 1.0 / v).collect();
    let mut sum_w_fixed: f64 = fixed_weights.iter().sum();
    if sum_w_fixed <= 0.0 { sum_w_fixed = 1e-8; }
    let fixed_effect: f64 = fixed_weights.iter().zip(&parsed)
        .map(|(w, s)| w * number(s, "effect_size")).sum::<f64>() / sum_w_fixed;

    let (cochran_q, df, i_squared, tau_squared, p_value) = if k >= 2 {
        let q: f64 = fixed_weights.iter().zip(&parsed)
            .map(|(w, s)| w * (number(s, "effect_size") - fixed_effect).powi(2)).sum();
        let degrees = (k - 1) as i64;
        let i2 = if q > 0.0 { ((q - degrees as f64) / q * 100.0).max(0.0) } else { 0.0 };
        let sum_sq_w: f64 = fixed_weights.iter().map(|w| w.powi(2)).sum();
        let denom = sum_w_fixed - sum_sq_w / sum_w_fixed;
        let tau2 = if denom > 0.0 { ((q - degrees as f64) / denom).max(0.0) } else { 0.0 };
        (q, degrees, i2, tau2, chi2_sf(q, degrees))
    } else { (0.0, 0, 0.0, 0.0, 1.0) };

    let (pooled_effect, pooled_se, weights) = if model_name == "random" {
        let weights: Vec<f64> = variances.iter().map(|v| 1.0 / (v + tau_squared)).collect();
        let mut sum_w: f64 = weights.iter().sum();
        if sum_w <= 0.0 { sum_w = 1e-8; }
        let effect = weights.iter().zip(&parsed).map(|(w, s)| w * number(s, "effect_size"))
            .sum::<f64>() / sum_w;
        (effect, (1.0 / sum_w).sqrt(), weights.iter().map(|w| w / sum_w * 100.0).collect::<Vec<_>>())
    } else {
        (fixed_effect, (1.0 / sum_w_fixed).sqrt(),
            fixed_weights.iter().map(|w| w / sum_w_fixed * 100.0).collect::<Vec<_>>())
    };

    let weighted: Vec<Value> = parsed.iter().zip(weights.iter()).map(|(s, pct)| {
        let mut value = s.clone();
        value.as_object_mut().unwrap().insert("weight".to_string(), json!(round_to(*pct, 2)));
        value
    }).collect();

    Ok(json!({
        "model": model_name,
        "pooled_effect": round_to(pooled_effect, 4),
        "pooled_se": round_to(pooled_se, 4),
        "pooled_ci_lower": round_to(pooled_effect - Z * pooled_se, 4),
        "pooled_ci_upper": round_to(pooled_effect + Z * pooled_se, 4),
        "cochran_q": round_to(cochran_q, 3),
        "df": df,
        "p_value": round_to(p_value, 4),
        "i_squared": round_to(i_squared, 1),
        "tau_squared": round_to(tau_squared, 4),
        "studies": weighted,
    }))
}

pub fn render_forest_ascii(result: &Value, width: usize) -> String {
    let studies = result.get("studies").and_then(Value::as_array).cloned().unwrap_or_default();
    let mut all_low: Vec<f64> = studies.iter().map(|s| number(s, "ci_lower")).collect();
    let mut all_high: Vec<f64> = studies.iter().map(|s| number(s, "ci_upper")).collect();
    all_low.push(number(result, "pooled_ci_lower"));
    all_high.push(number(result, "pooled_ci_upper"));
    let val_min = all_low.iter().copied().fold(f64::INFINITY, f64::min);
    let val_max = all_high.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let axis_min = (-0.1f64).min(val_min - 0.1);
    let axis_max = (0.1f64).max(val_max + 0.1);
    let span = if axis_max - axis_min <= 0.0 { 1.0 } else { axis_max - axis_min };
    let col = |value: f64| -> usize {
        let index = (((value - axis_min) / span) * (width - 1) as f64) as i64;
        index.max(0).min(width as i64 - 1) as usize
    };
    let zero_col = col(0.0);
    let header = format!("{:<26} {:<20} {:<8} Forest Plot ({:.1} to {:.1})",
        "Study", "Effect [95% CI]", "Weight", axis_min, axis_max);
    let divider = "-".repeat(header.len() + width - 15);
    let mut lines = vec![header, divider.clone()];
    for study in &studies {
        let c_low = col(number(study, "ci_lower"));
        let c_high = col(number(study, "ci_upper"));
        let c_mid = col(number(study, "effect_size"));
        let mut chars = vec![' '; width];
        chars[zero_col] = '|';
        for index in c_low..=c_high {
            if chars[index] == ' ' { chars[index] = '-'; }
        }
        chars[c_low] = '[';
        chars[c_high] = ']';
        chars[c_mid] = '#';
        let label = field(study, "label");
        let short_label: String = if label.chars().count() > 26 {
            format!("{}...", label.chars().take(23).collect::<String>())
        } else { label };
        let ci = format!("{:+.2} [{:+.2}, {:+.2}]", number(study, "effect_size"),
            number(study, "ci_lower"), number(study, "ci_upper"));
        let weight = format!("{:5.1}%", number(study, "weight"));
        lines.push(format!("{short_label:<26} {ci:<20} {weight:<8} {}", chars.iter().collect::<String>()));
    }
    lines.push(divider.clone());
    let p_low = col(number(result, "pooled_ci_lower"));
    let p_high = col(number(result, "pooled_ci_upper"));
    let p_mid = col(number(result, "pooled_effect"));
    let mut summary = vec![' '; width];
    summary[zero_col] = '|';
    for index in p_low..=p_high {
        if summary[index] == ' ' { summary[index] = '='; }
    }
    summary[p_low] = '<';
    summary[p_high] = '>';
    summary[p_mid] = 'D';
    let model = field(result, "model");
    let capital = {
        let mut chars = model.chars();
        match chars.next() {
            Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
            None => String::new(),
        }
    };
    let sum_ci = format!("{:+.2} [{:+.2}, {:+.2}]", number(result, "pooled_effect"),
        number(result, "pooled_ci_lower"), number(result, "pooled_ci_upper"));
    lines.push(format!("{:<26} {:<20} {:<8} {}",
        format!("Pooled ({capital})"), sum_ci, "100.0%", summary.iter().collect::<String>()));
    lines.push(format!(
        "Heterogeneity: Q = {:.2} (df = {}, p = {:.3}), I² = {:.1}%, τ² = {:.3}",
        number(result, "cochran_q"),
        result.get("df").and_then(Value::as_i64).unwrap_or(0),
        number(result, "p_value"), number(result, "i_squared"), number(result, "tau_squared")));
    lines.join("\n")
}
