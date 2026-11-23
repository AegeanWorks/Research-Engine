//! PNN CNS design-property rules (domains/pnn/rules.py).

use serde_json::{json, Value};

pub const CORE_CRITERIA: &[&str] = &["mw", "logp", "tpsa", "hbd", "hba", "rotatable_bonds"];
pub const HARD_REJECT_CRITERIA: &[&str] = &["logbb", "brain_plasma_ratio",
    "oral_bioavailability", "cyp3a4_inhibition", "herg_liability"];

fn num(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

fn optional(value: &Value, key: &str) -> Option<f64> {
    value.get(key).and_then(Value::as_f64)
}

fn g(value: f64) -> String {
    if value == 0.0 { return "0".to_string(); }
    let exponent = value.abs().log10().floor() as i32;
    let decimals = (5 - exponent).max(0) as usize;
    let rounded = format!("{:.*}", decimals, value);
    if rounded.contains('.') {
        rounded.trim_end_matches('0').trim_end_matches('.').to_string()
    } else { rounded }
}

fn result(name: &str, status: &str, score: f64, value: Option<f64>, detail: String) -> Value {
    json!({"name": name, "status": status, "score": score, "value": value, "detail": detail})
}

fn range(name: &str, value: f64, low: f64, high: f64, opt_low: f64, opt_high: f64, unit: &str) -> Value {
    if value < low || value > high {
        return result(name, "FAIL", 0.0, Some(value),
            format!("{}{unit} is outside {}-{}{unit}", g(value), g(low), g(high)));
    }
    let optimal = opt_low <= value && value <= opt_high;
    let target = if opt_low != low || opt_high != high {
        format!("{}-{}{unit}", g(opt_low), g(opt_high))
    } else { format!("<= {}{unit}", g(high)) };
    result(name, "PASS", if optimal { 1.0 } else { 0.7 }, Some(value),
        format!("{}{unit} is acceptable; optimal is {target}", g(value)))
}

fn ceiling(name: &str, value: f64, limit: f64, optimal: f64, unit: &str) -> Value {
    if value > limit {
        return result(name, "FAIL", 0.0, Some(value),
            format!("{}{unit} exceeds the limit of {}{unit}", g(value), g(limit)));
    }
    result(name, "PASS", if value <= optimal { 1.0 } else { 0.7 }, Some(value),
        format!("{}{unit} is within the limit of {}{unit} (optimal <= {}{unit})",
            g(value), g(limit), g(optimal)))
}

pub fn evaluate(compound: &Value) -> Vec<Value> {
    let mut out = vec![
        range("mw", num(compound, "mw"), 200.0, 450.0, 300.0, 400.0, " Da"),
        range("logp", num(compound, "logp"), 1.5, 3.5, 2.0, 3.0, ""),
        ceiling("tpsa", num(compound, "tpsa"), 70.0, 60.0, " A2"),
        ceiling("hbd", num(compound, "hbd"), 3.0, 3.0, ""),
        ceiling("hba", num(compound, "hba"), 7.0, 7.0, ""),
        ceiling("rotatable_bonds", num(compound, "rotatable_bonds"), 7.0, 7.0, ""),
    ];

    let pka = optional(compound, "pka");
    let charge = compound.get("charge").and_then(Value::as_str).unwrap_or("");
    let pka_result = match pka {
        None => result("pka", "UNKNOWN", 0.0, None, "no pKa supplied".to_string()),
        Some(pka) if charge == "basic" && !(7.0..=9.0).contains(&pka) =>
            result("pka", "FAIL", 0.0, Some(pka), "basic compound outside pKa 7-9".to_string()),
        Some(pka) if charge == "acidic" && !(3.0..=5.0).contains(&pka) =>
            result("pka", "FAIL", 0.0, Some(pka), "acidic compound outside pKa 3-5".to_string()),
        Some(pka) if charge != "basic" && charge != "acidic"
            && !((7.0..=9.0).contains(&pka) || (3.0..=5.0).contains(&pka)) =>
            result("pka", "FAIL", 0.0, Some(pka), "pKa outside 3-5 and 7-9".to_string()),
        Some(pka) => result("pka", "PASS", 1.0, Some(pka), "pKa fits the CNS window".to_string()),
    };
    out.push(pka_result);

    let charge_result = if charge.is_empty() {
        result("charge", "UNKNOWN", 0.0, None, "no ionization class supplied".to_string())
    } else if !["neutral", "basic", "acidic", "zwitterion"].contains(&charge) {
        result("charge", "UNKNOWN", 0.0, None, format!("unrecognized ionization class: {charge}"))
    } else if charge == "neutral" || charge == "basic" {
        result("charge", "PASS", 1.0, None, format!("{charge} at pH 7.4"))
    } else {
        result("charge", "PASS", 0.4, None, format!("{charge} is less favorable than neutral/basic"))
    };
    out.push(charge_result);

    let logbb = optional(compound, "logbb");
    out.push(match logbb {
        None => result("logbb", "UNKNOWN", 0.0, None, "no logBB supplied".to_string()),
        Some(value) if value < -1.0 => result("logbb", "FAIL", 0.0, Some(value),
            format!("logBB {} is below -1.0", g(value))),
        Some(value) => result("logbb", "PASS", if value >= -0.5 { 1.0 } else { 0.7 }, Some(value),
            format!("logBB {} (preferred >= -0.5)", g(value))),
    });

    let ratio = optional(compound, "brain_plasma_ratio");
    out.push(match ratio {
        None => result("brain_plasma_ratio", "UNKNOWN", 0.0, None, "no brain/plasma ratio supplied".to_string()),
        Some(value) if value < 0.1 => result("brain_plasma_ratio", "FAIL", 0.0, Some(value),
            format!("ratio {} is below 0.1", g(value))),
        Some(value) => result("brain_plasma_ratio", "PASS", if value >= 0.3 { 1.0 } else { 0.5 }, Some(value),
            format!("ratio {} (progression target >= 0.3)", g(value))),
    });

    let oral = optional(compound, "oral_bioavailability");
    out.push(match oral {
        None => result("oral_bioavailability", "UNKNOWN", 0.0, None, "no oral F supplied".to_string()),
        Some(value) => {
            let percent = if value <= 1.0 { value * 100.0 } else { value };
            if percent < 10.0 {
                result("oral_bioavailability", "FAIL", 0.0, Some(percent),
                    format!("oral F {}% is below 10%", g(percent)))
            } else {
                let score = if percent >= 20.0 { 1.0 } else if percent >= 15.0 { 0.7 } else { 0.4 };
                result("oral_bioavailability", "PASS", score, Some(percent),
                    format!("oral F {}% (progression target >= 20%)", g(percent)))
            }
        }
    });

    let cyp = optional(compound, "cyp3a4_inhibition");
    out.push(match cyp {
        None => result("cyp3a4_inhibition", "UNKNOWN", 0.0, None, "no CYP3A4 inhibition supplied".to_string()),
        Some(value) if value >= 50.0 => result("cyp3a4_inhibition", "FAIL", 0.0, Some(value),
            format!("{}% inhibition at 10 uM", g(value))),
        Some(value) => result("cyp3a4_inhibition", "PASS", if value < 30.0 { 1.0 } else { 0.7 }, Some(value),
            format!("{}% inhibition at 10 uM", g(value))),
    });

    let herg = optional(compound, "herg_liability");
    out.push(match herg {
        None => result("herg_liability", "UNKNOWN", 0.0, None, "no hERG liability supplied".to_string()),
        Some(value) if value >= 30.0 => result("herg_liability", "FAIL", 0.0, Some(value),
            format!("{}% hERG inhibition at 10 uM", g(value))),
        Some(value) => result("herg_liability", "PASS", if value < 10.0 { 1.0 } else { 0.7 }, Some(value),
            format!("{}% hERG inhibition", g(value))),
    });

    let ec50 = optional(compound, "pnn_ec50_nm");
    out.push(match ec50 {
        None => result("pnn_ec50_nm", "UNKNOWN", 0.0, None, "no PNN-softening EC50 supplied".to_string()),
        Some(value) if value >= 1000.0 => result("pnn_ec50_nm", "FAIL", 0.0, Some(value),
            format!("EC50 {} nM is above 1000 nM", g(value))),
        Some(value) => {
            let score = if value < 10.0 { 1.0 } else if value < 100.0 { 0.7 } else { 0.4 };
            result("pnn_ec50_nm", "PASS", score, Some(value),
                format!("EC50 {} nM (progression target < 100 nM)", g(value)))
        }
    });
    out
}

pub fn weight(criterion: &str) -> f64 {
    if CORE_CRITERIA.contains(&criterion) { 1.0 } else { 0.5 }
}
