//! Nematic director topology and the Z3 question
//! (fluid_universe/theory/topology.py).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const HOMOTOPY: &[(&str, &str)] = &[("pi1", "Z2"), ("pi2", "Z"), ("pi3", "Z")];

fn py_bool(value: bool) -> &'static str {
    if value { "True" } else { "False" }
}

pub fn has_z3_factor() -> bool {
    HOMOTOPY.iter().any(|(_, value)| value.contains("Z3") || value.contains("Z_3"))
}

pub fn direct_result() -> Value {
    let homotopy: Value = Value::Object(HOMOTOPY.iter()
        .map(|(k, v)| (k.to_string(), Value::String((*v).to_string()))).collect());
    json!({
        "order_parameter_space": "RP^2",
        "homotopy": homotopy,
        "z3_factor_present": has_z3_factor(),
        "cos3phi_inserted_by_hand": true,
        "direct_claim": "Z3 is derived from nematic topology alone",
        "direct_claim_falsified": true,
        "reason": "The listed homotopy groups contain Z2 and Z, not Z3. A three-fold sector cannot be read off the RP^2 topology without extra structure.",
    })
}

pub fn extensions() -> Value {
    json!({
        "rank_three_order_parameter": {
            "z3_derived": false,
            "requires": "An explicit rank-3 tensor with a three-fold symmetric invariant. The Z3 is a property of the chosen invariant, not of RP^2.",
        },
        "three_coupled_nematics": {
            "z3_derived": false,
            "requires": "An S3 permutation symmetry of the three fields. Its Z3 subgroup is imposed by the coupling, so the symmetry is inserted.",
        },
        "three_fold_lattice": {
            "z3_derived": false,
            "requires": "A lattice with a three-fold axis. The lattice breaks continuous rotation and supplies the Z3 label; nematic topology alone does not.",
        },
    })
}

pub fn verdict() -> Value {
    json!({
        "13a_direct_z3_from_nematic_topology": false,
        "13b_natural_extension_yields_z3_without_insertion": false,
        "direct_claim_status": "FALSIFIED",
        "extensions_status": "UNVERIFIED (null for the three standard extensions)",
        "cos3phi_inserted_by_hand": true,
        "note": "The strong claim is false: RP^2 has no Z3 factor and the cos(3 phi) term is inserted. None of the three standard extensions produces Z3 without an explicit three-fold structure. A different, specified extension is not excluded, but it would have to be constructed and tested explicitly.",
        "direct": direct_result(),
        "extensions": extensions(),
    })
}

/// Render the claim-13 Markdown report from a payload containing verdict + meta.
pub fn render_markdown(payload: &Value) -> Result<String> {
    let v = payload.get("verdict").ok_or_else(|| EngineError::new(
        "payload must contain a 'verdict' object", "the report needs the topology verdict",
        "pass a payload object with verdict and meta"))?;
    let meta = payload.get("meta").ok_or_else(|| EngineError::new(
        "payload must contain a 'meta' object", "the report needs provenance metadata",
        "pass a payload object with verdict and meta"))?;
    let space = v.get("direct").and_then(|d| d.get("order_parameter_space")).and_then(Value::as_str)
        .unwrap_or("");
    let ext = v.get("extensions").ok_or_else(|| EngineError::new(
        "verdict must contain 'extensions'", "the report table needs the extension list",
        "pass a verdict with extensions"))?;
    let mut lines = vec![
        "# Nematic topology and Z3 (claim 13)".to_string(),
        String::new(),
        format!("Order-parameter space: {space}. Homotopy: {{'pi1': 'Z2', 'pi2': 'Z', 'pi3': 'Z'}}."),
        String::new(),
        "| extension | Z3 derived? | what it would require |".to_string(),
        "|---|---|---|".to_string(),
    ];
    if let Some(map) = ext.as_object() {
        for (name, item) in map {
            let derived = item.get("z3_derived").and_then(Value::as_bool).unwrap_or(false);
            let requires = item.get("requires").and_then(Value::as_str).unwrap_or("");
            lines.push(format!("| {name} | {} | {requires} |", py_bool(derived)));
        }
    }
    let a = v.get("13a_direct_z3_from_nematic_topology").and_then(Value::as_bool).unwrap_or(false);
    let b = v.get("13b_natural_extension_yields_z3_without_insertion").and_then(Value::as_bool).unwrap_or(false);
    let inserted = v.get("cos3phi_inserted_by_hand").and_then(Value::as_bool).unwrap_or(false);
    let note = v.get("note").and_then(Value::as_str).unwrap_or("");
    let sha = meta.get("config_sha256").and_then(Value::as_str).unwrap_or("");
    let git = meta.get("git").unwrap_or(&Value::Null);
    let commit = git.get("commit").and_then(Value::as_str).unwrap_or("");
    let dirty = git.get("dirty").and_then(Value::as_bool).unwrap_or(false);
    lines.extend([
        String::new(),
        format!("**Verdict:** direct Z3 from nematic topology: **{}**; standard extensions: **{}**. `cos(3 phi)` inserted by hand: **{}**.",
            py_bool(a), py_bool(b), py_bool(inserted)),
        String::new(),
        note.to_string(),
        String::new(),
        format!("- Config SHA-256: `{sha}`"),
        format!("- Git: `{commit}` (dirty={})", py_bool(dirty)),
        String::new(),
    ]);
    Ok(lines.join("\n"))
}
