//! CSV row contracts shared by the PNN Phase 2 command line tools
//! (domains/pnn/tables.py and curation.property_bin).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const PROPERTY_RANGES: &[(f64, f64)] = &[
    (200.0, 450.0), (1.5, 3.5), (0.0, 70.0), (0.0, 3.0), (0.0, 7.0), (0.0, 7.0),
];
pub const CURATED_FIELDS: &[&str] = &["compound_id", "name", "smiles", "source", "tier",
    "score", "mw", "logp", "tpsa", "hbd", "hba", "rotatable_bonds", "pka", "charge",
    "property_bin", "failed_criteria", "unknown_criteria"];
pub const SCREEN_FIELDS: &[&str] = &["compound_id", "name", "smiles", "tier", "score",
    "mw", "logp", "tpsa", "hbd", "hba", "rotatable_bonds", "pka", "charge", "logbb",
    "brain_plasma_ratio", "oral_bioavailability", "cyp3a4_inhibition", "herg_liability",
    "pnn_ec50_nm", "failed_criteria", "unknown_criteria"];

fn round_even(value: f64) -> f64 {
    let floor = value.floor();
    let fraction = value - floor;
    if fraction > 0.5 { floor + 1.0 }
    else if fraction < 0.5 { floor }
    else if (floor as i64) % 2 == 0 { floor }
    else { floor + 1.0 }
}

fn get<'a>(value: &'a Value, key: &str) -> &'a Value {
    value.get(key).unwrap_or(&Value::Null)
}

fn text(value: &Value) -> String {
    value.as_str().unwrap_or("").to_string()
}

fn optional(value: &Value) -> Value {
    if value.is_null() { Value::String(String::new()) } else { value.clone() }
}

fn compound_field(compound: &Value, key: &str) -> f64 {
    get(compound, key).as_f64().unwrap_or(0.0)
}

fn joined(items: &Value) -> String {
    items.as_array().map(|a| a.iter().map(|v| text(v))
        .collect::<Vec<_>>().join(";")).unwrap_or_default()
}

/// Bin the six core properties on a normalized 0..1 grid.
pub fn property_bin(compound: &Value, width: f64) -> Result<Vec<i64>> {
    if width <= 0.0 {
        return Err(EngineError::new("bin width must be positive",
            "a property bin needs a positive width", "pass width > 0"));
    }
    let bins = (round_even(1.0 / width).max(1.0)) as i64;
    let properties = ["mw", "logp", "tpsa", "hbd", "hba", "rotatable_bonds"];
    let mut cells = Vec::with_capacity(properties.len());
    for (key, (low, high)) in properties.iter().zip(PROPERTY_RANGES) {
        let normalized = ((compound_field(compound, key) - low) / (high - low))
            .min(1.0).max(0.0);
        cells.push(((normalized * bins as f64) as i64).min(bins - 1));
    }
    Ok(cells)
}

/// Return one ranked-screening row for a screened compound.
pub fn screen_row(result: &Value) -> Value {
    let compound = get(result, "compound");
    let score = get(result, "score").as_f64().unwrap_or(0.0);
    json!({
        "compound_id": text(get(compound, "compound_id")),
        "name": text(get(compound, "name")),
        "smiles": text(get(compound, "smiles")),
        "tier": text(get(result, "tier")),
        "score": format!("{score:.4}"),
        "mw": compound_field(compound, "mw"),
        "logp": compound_field(compound, "logp"),
        "tpsa": compound_field(compound, "tpsa"),
        "hbd": compound_field(compound, "hbd"),
        "hba": compound_field(compound, "hba"),
        "rotatable_bonds": compound_field(compound, "rotatable_bonds"),
        "pka": optional(get(compound, "pka")),
        "charge": text(get(compound, "charge")),
        "logbb": optional(get(compound, "logbb")),
        "brain_plasma_ratio": optional(get(compound, "brain_plasma_ratio")),
        "oral_bioavailability": optional(get(compound, "oral_bioavailability")),
        "cyp3a4_inhibition": optional(get(compound, "cyp3a4_inhibition")),
        "herg_liability": optional(get(compound, "herg_liability")),
        "pnn_ec50_nm": optional(get(compound, "pnn_ec50_nm")),
        "failed_criteria": joined(get(result, "failed_criteria")),
        "unknown_criteria": joined(get(result, "unknown_criteria")),
    })
}

/// Return one curated-library row, including source and property bin.
pub fn curated_row(candidate: &Value, width: f64) -> Result<Value> {
    let compound = get(candidate, "compound");
    let result = get(candidate, "result");
    let score = get(result, "score").as_f64().unwrap_or(0.0);
    let bins = property_bin(compound, width)?;
    let bin_label = bins.iter().map(|v| v.to_string()).collect::<Vec<_>>().join("-");
    Ok(json!({
        "compound_id": text(get(compound, "compound_id")),
        "name": text(get(compound, "name")),
        "smiles": text(get(compound, "smiles")),
        "source": text(get(candidate, "source")),
        "tier": text(get(result, "tier")),
        "score": format!("{score:.4}"),
        "mw": compound_field(compound, "mw"),
        "logp": compound_field(compound, "logp"),
        "tpsa": compound_field(compound, "tpsa"),
        "hbd": compound_field(compound, "hbd"),
        "hba": compound_field(compound, "hba"),
        "rotatable_bonds": compound_field(compound, "rotatable_bonds"),
        "pka": optional(get(compound, "pka")),
        "charge": text(get(compound, "charge")),
        "property_bin": bin_label,
        "failed_criteria": joined(get(result, "failed_criteria")),
        "unknown_criteria": joined(get(result, "unknown_criteria")),
    }))
}
