//! Compound records and CSV ingestion for the PNN screening pipeline
//! (domains/pnn/compounds.py).

use std::collections::BTreeMap;
use std::sync::OnceLock;

use serde_json::Value;

use crate::error::{EngineError, Result};

const REQUIRED: &[&str] = &["compound_id", "mw", "logp", "tpsa", "hbd", "hba", "rotatable_bonds"];
const OPTIONAL_NUMERIC: &[&str] = &["pka", "logbb", "brain_plasma_ratio",
    "oral_bioavailability", "cyp3a4_inhibition", "herg_liability", "pnn_ec50_nm"];
const ALL_FIELDS: &[&str] = &["compound_id", "mw", "logp", "tpsa", "hbd", "hba",
    "rotatable_bonds", "pka", "logbb", "brain_plasma_ratio", "oral_bioavailability",
    "cyp3a4_inhibition", "herg_liability", "pnn_ec50_nm", "name", "smiles", "charge"];
const WHOLE_NUMBER: &[&str] = &["hbd", "hba", "rotatable_bonds"];
const NON_NEGATIVE: &[&str] = &["mw", "tpsa", "hbd", "hba", "rotatable_bonds",
    "brain_plasma_ratio", "oral_bioavailability", "cyp3a4_inhibition", "herg_liability",
    "pnn_ec50_nm"];

fn aliases() -> &'static BTreeMap<&'static str, &'static str> {
    static MAP: OnceLock<BTreeMap<&'static str, &'static str>> = OnceLock::new();
    MAP.get_or_init(|| [
        ("id", "compound_id"), ("compound", "compound_id"), ("compoundid", "compound_id"),
        ("molecule", "compound_id"), ("moleculeid", "compound_id"),
        ("molecularweight", "mw"), ("molweight", "mw"), ("mwda", "mw"),
        ("clogp", "logp"), ("logp", "logp"), ("xlogp", "logp"),
        ("polararea", "tpsa"), ("psa", "tpsa"), ("tpsaa2", "tpsa"),
        ("hbonddonors", "hbd"), ("hbdcount", "hbd"), ("donors", "hbd"),
        ("hbondacceptors", "hba"), ("hbacount", "hba"), ("acceptors", "hba"),
        ("rotors", "rotatable_bonds"), ("numrotatablebonds", "rotatable_bonds"),
        ("rotatablebonds", "rotatable_bonds"),
        ("logbb", "logbb"), ("bbratio", "brain_plasma_ratio"), ("braintoplasma", "brain_plasma_ratio"),
        ("brainplasmaratio", "brain_plasma_ratio"), ("brainplasma", "brain_plasma_ratio"),
        ("oralbioavailability", "oral_bioavailability"), ("oralf", "oral_bioavailability"),
        ("bioavailability", "oral_bioavailability"), ("fpercent", "oral_bioavailability"),
        ("cyp3a4", "cyp3a4_inhibition"), ("cyp3a4inhibition", "cyp3a4_inhibition"),
        ("cyp3a4inhibitionpercent", "cyp3a4_inhibition"),
        ("herg", "herg_liability"), ("herginhibition", "herg_liability"), ("hergliability", "herg_liability"),
        ("pnnec50", "pnn_ec50_nm"), ("ec50nm", "pnn_ec50_nm"),
        ("pnnsofteningec50nm", "pnn_ec50_nm"),
    ].into_iter().collect())
}

fn canonical_by_token() -> &'static BTreeMap<&'static str, &'static str> {
    static MAP: OnceLock<BTreeMap<&'static str, &'static str>> = OnceLock::new();
    MAP.get_or_init(|| ALL_FIELDS.iter().map(|field| {
        let token: String = field.chars().filter(|c| c.is_alphanumeric()).flat_map(char::to_lowercase).collect();
        let leaked: &'static str = Box::leak(token.into_boxed_str());
        (leaked, *field)
    }).collect())
}

fn charge_aliases() -> &'static BTreeMap<&'static str, &'static str> {
    static MAP: OnceLock<BTreeMap<&'static str, &'static str>> = OnceLock::new();
    MAP.get_or_init(|| [
        ("neutral", "neutral"), ("neutralion", "neutral"), ("basic", "basic"),
        ("weaklybasic", "basic"), ("base", "basic"), ("acidic", "acidic"), ("acid", "acidic"),
        ("zwitterion", "zwitterion"), ("zwitterionic", "zwitterion"),
    ].into_iter().collect())
}

fn token(name: &str) -> String {
    name.trim().chars().filter(|c| c.is_alphanumeric()).flat_map(char::to_lowercase).collect()
}

/// Map one CSV header to its canonical field name, or None when unused.
pub fn normalize_field(name: &str) -> Option<&'static str> {
    let canonical = token(name);
    if let Some(value) = aliases().get(canonical.as_str()) { return Some(*value); }
    if let Some(value) = canonical_by_token().get(canonical.as_str()) { return Some(*value); }
    match canonical.as_str() {
        "compoundname" => Some("name"),
        "canonicalsmiles" => Some("smiles"),
        "ionization" | "ionclass" => Some("charge"),
        _ => None,
    }
}

fn number(raw: &str, field: &str, where_: &str) -> Result<f64> {
    let text = raw.trim().replace(',', "");
    let value: f64 = text.parse().map_err(|_| EngineError::new(
        format!("{where_}: field '{field}' is not a number: {raw:?}"),
        "compound fields must be numeric", "pass a finite number"))?;
    if !value.is_finite() {
        return Err(EngineError::new(format!("{where_}: field '{field}' must be finite, got {raw:?}"),
            "non-finite compound values are not comparable", "pass a finite number"));
    }
    if NON_NEGATIVE.contains(&field) && value < 0.0 {
        return Err(EngineError::new(format!("{where_}: field '{field}' must not be negative, got {raw:?}"),
            "this compound field cannot be negative", "pass a non-negative number"));
    }
    if WHOLE_NUMBER.contains(&field) && value.fract() != 0.0 {
        return Err(EngineError::new(format!("{where_}: field '{field}' must be a whole number, got {raw:?}"),
            "counts must be whole numbers", "pass an integer"));
    }
    Ok(value)
}

fn optional_number(values: &BTreeMap<String, String>, field: &str, where_: &str) -> Result<Option<f64>> {
    let raw = values.get(field).map(String::as_str).unwrap_or("").trim();
    if raw.is_empty() { Ok(None) } else { Ok(Some(number(raw, field, where_)?)) }
}

fn charge(raw: &str) -> String {
    let canonical = token(raw);
    charge_aliases().get(canonical.as_str()).map(|v| (*v).to_string())
        .unwrap_or_else(|| raw.trim().to_lowercase())
}

fn build_compound(values: &BTreeMap<String, String>, where_: &str) -> Result<Value> {
    let get = |key: &str| values.get(key).map(String::as_str).unwrap_or("").trim().to_string();
    let compound_id = get("compound_id");
    if compound_id.is_empty() {
        return Err(EngineError::new(format!("{where_}: field 'compound_id' must not be empty"),
            "a compound needs an identifier", "add a compound_id column"));
    }
    let missing: Vec<&str> = REQUIRED.iter().copied()
        .filter(|field| get(field).is_empty()).collect();
    if !missing.is_empty() {
        return Err(EngineError::new(
            format!("{where_}: missing required field(s): {}", missing.join(", ")),
            "a compound needs all six physicochemical descriptors", "add the missing columns"));
    }
    let mut out = serde_json::Map::new();
    out.insert("compound_id".into(), Value::String(compound_id));
    out.insert("name".into(), Value::String(get("name")));
    out.insert("smiles".into(), Value::String(get("smiles")));
    out.insert("charge".into(), Value::String(charge(&get("charge"))));
    for field in &REQUIRED[1..] {
        let raw = get(field);
        out.insert((*field).into(), Value::from(number(&raw, field, where_)?));
    }
    for field in OPTIONAL_NUMERIC {
        out.insert((*field).into(), Value::from(optional_number(values, field, where_)?));
    }
    Ok(Value::Object(out))
}

pub fn parse_compounds(rows: &[BTreeMap<String, String>], source: &str,
                       allow_duplicates: bool) -> Result<Vec<Value>> {
    let mut compounds = Vec::new();
    let mut seen: BTreeMap<String, usize> = BTreeMap::new();
    for (index, raw) in rows.iter().enumerate() {
        let where_ = format!("{source} row {}", index + 2);
        let mut values = BTreeMap::new();
        for (key, value) in raw {
            if let Some(field) = normalize_field(key) {
                values.insert(field.to_string(), value.trim().to_string());
            }
        }
        let compound = build_compound(&values, &where_)?;
        let id = compound.get("compound_id").and_then(Value::as_str).unwrap_or("").to_string();
        if !allow_duplicates {
            if let Some(first) = seen.get(&id) {
                return Err(EngineError::new(
                    format!("{where_}: duplicate compound_id '{id}' (first seen on row {first})"),
                    "each compound must have a unique identifier", "remove the duplicate row"));
            }
            seen.insert(id, index + 2);
        }
        compounds.push(compound);
    }
    Ok(compounds)
}

pub fn array(values: Vec<Value>) -> Value {
    Value::Array(values)
}
