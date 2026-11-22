//! Atlas visual-knowledge domain schema (domains/atlas/schema.py).

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

const SCHEMA_VERSION: &str = "domains.atlas.visual-knowledge/v1";
const ENTITY_CATEGORIES: &[&str] = &[
    "anatomical-structure", "molecule", "protein", "cell-type", "component", "process",
    "function", "pathway", "person", "place", "other",
];
const RELATIONSHIP_TYPES: &[&str] = &[
    "activates", "inhibits", "projects-to", "receives-input-from", "produces", "regulates",
    "contains", "participates-in",
];

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn get(value: &Value, name: &str) -> Value {
    value.get(name).cloned().unwrap_or(Value::Null)
}

fn number(value: &Value, name: &str) -> f64 {
    value.get(name).and_then(Value::as_f64).unwrap_or(0.0)
}

fn checked_confidence(value: &Value, context: &str) -> Result<f64> {
    let Some(number) = value.as_f64() else {
        return Err(EngineError::new(format!("{context}: confidence must be a number in [0,1], got {value:?}"),
            "confidence must be a real number", "pass a number between 0 and 1"));
    };
    if !(0.0..=1.0).contains(&number) {
        return Err(EngineError::new(format!("{context}: confidence must be in [0,1], got {number}"),
            "confidence must be a real number", "pass a number between 0 and 1"));
    }
    Ok(number)
}

fn required(value: &Value, key: &str, context: &str) -> Result<Value> {
    value.get(key).cloned().ok_or_else(|| EngineError::new(
        format!("{context}: missing required key '{key}'"), "required fields must be present",
        format!("pass the {key} field")))
}

fn norm_name(name: &str) -> String {
    name.to_lowercase().trim().split_whitespace().collect::<Vec<_>>().join(" ")
}

fn bbox_from_grid(box_value: &Value) -> Result<Value> {
    let values: Vec<f64> = box_value.as_array().ok_or_else(|| EngineError::new(
        "box must have 4 entries", "a bounding box has four coordinates", "pass a 4-element array"))?
        .iter().map(|v| v.as_f64().unwrap_or(0.0)).collect();
    if values.len() != 4 {
        return Err(EngineError::new(format!("box must have 4 entries, got {values:?}"),
            "a bounding box has four coordinates", "pass a 4-element array"));
    }
    let clamped: Vec<f64> = values.iter().map(|v| v.max(0.0).min(1000.0) / 1000.0).collect();
    if !(clamped[0] < clamped[2] && clamped[1] < clamped[3]) {
        return Err(EngineError::new(format!("empty/inverted box {clamped:?}"),
            "box coordinates must form a non-empty rectangle", "pass x_min<x_max and y_min<y_max"));
    }
    Ok(json!({"x_min": clamped[0], "y_min": clamped[1], "x_max": clamped[2], "y_max": clamped[3]}))
}

fn entity(raw: &Value, context: &str, from_grid: bool) -> Result<Value> {
    let id = required(raw, "id", context)?.as_str().unwrap_or("").to_string();
    let name = required(raw, "name", context)?.as_str().unwrap_or("").to_string();
    if id.is_empty() || name.is_empty() {
        return Err(EngineError::new("entity id and name are required", "entities need stable identity",
            "pass id and name"));
    }
    let category = {
        let value = get(raw, "category").as_str().unwrap_or("other").to_string();
        value
    };
    if !ENTITY_CATEGORIES.contains(&category.as_str()) {
        return Err(EngineError::new(format!("unknown category '{category}'"),
            "categories are a closed vocabulary", "pass one of the declared categories"));
    }
    let bbox = if from_grid {
        raw.get("box").filter(|v| !v.is_null()).map(bbox_from_grid).transpose()?
    } else {
        raw.get("bbox").filter(|v| !v.is_null()).map(|v| v.clone())
    };
    let confidence = checked_confidence(&get(raw, "confidence"), context)?;
    Ok(json!({
        "id": id, "name": name, "category": category,
        "description": field(raw, "description"), "bbox": bbox,
        "source_evidence": field(raw, "source_evidence"), "confidence": confidence,
        "uncertainty": field(raw, "uncertainty"), "mask_ref": field(raw, "mask_ref"),
        "model_inferred": get(raw, "model_inferred").as_bool().unwrap_or(from_grid),
    }))
}

fn relationship(raw: &Value) -> Result<Value> {
    let source_id = required(raw, "source_id", "muse relationship")?.as_str().unwrap_or("").to_string();
    let target_id = required(raw, "target_id", "muse relationship")?.as_str().unwrap_or("").to_string();
    let rel_type = required(raw, "rel_type", "muse relationship")?.as_str().unwrap_or("").to_string();
    if !RELATIONSHIP_TYPES.contains(&rel_type.as_str()) {
        return Err(EngineError::new(format!("unknown relationship type '{rel_type}'"),
            "relationship types are a closed vocabulary", "pass one of the declared types"));
    }
    if source_id.is_empty() || target_id.is_empty() {
        return Err(EngineError::new("relationship endpoints are required", "endpoints identify entities",
            "pass source_id and target_id"));
    }
    if source_id == target_id {
        return Err(EngineError::new("self-relationships are not allowed", "a relation needs two entities",
            "choose a different target"));
    }
    let confidence = checked_confidence(&get(raw, "confidence"),
        &format!("relationship '{source_id}'->'{target_id}'"))?;
    Ok(json!({
        "source_id": source_id, "target_id": target_id, "rel_type": rel_type,
        "explanation": field(raw, "explanation"),
        "supporting_evidence": field(raw, "supporting_evidence"),
        "confidence": confidence,
        "provenance": ({ let value = field(raw, "provenance"); if value.is_empty() { "model".to_string() } else { value } }),
        "model_inferred": get(raw, "model_inferred").as_bool().unwrap_or(true),
    }))
}

fn analysis(entities: Vec<Value>, relationships: Vec<Value>, document_ref: &str,
            source_page: i64, figure_id: &str) -> Result<Value> {
    let ids: Vec<String> = entities.iter().map(|e| field(e, "id")).collect();
    if ids.iter().collect::<BTreeSet<_>>().len() != ids.len() {
        return Err(EngineError::new("duplicate entity ids", "entity ids must be unique", "deduplicate ids"));
    }
    let mut errors = Vec::new();
    for rel in &relationships {
        if !ids.contains(&field(rel, "source_id")) {
            errors.push(format!("relationship from unknown entity {}", field(rel, "source_id")));
        }
        if !ids.contains(&field(rel, "target_id")) {
            errors.push(format!("relationship to unknown entity {}", field(rel, "target_id")));
        }
    }
    if !errors.is_empty() {
        return Err(EngineError::new(errors.join("; "), "relationships must reference existing entities",
            "fix the endpoints"));
    }
    Ok(json!({
        "analysis_version": SCHEMA_VERSION,
        "document_ref": document_ref,
        "source_page": source_page,
        "figure_id": figure_id,
        "entities": entities,
        "relationships": relationships,
    }))
}

pub fn coerce_muse_payload(payload: &Value, document_ref: &str, source_page: i64, figure_id: &str) -> Result<Value> {
    let mut entities = Vec::new();
    for raw in payload.get("entities").and_then(Value::as_array).into_iter().flatten() {
        if !raw.is_object() {
            return Err(EngineError::new(format!("muse entity: expected object, got {raw:?}"),
                "entities must be JSON objects", "pass objects in the entities array"));
        }
        entities.push(entity(raw, &format!("muse entity {}", field(raw, "id")), true)?);
    }
    let mut relationships = Vec::new();
    for raw in payload.get("relationships").and_then(Value::as_array).into_iter().flatten() {
        relationships.push(relationship(raw)?);
    }
    analysis(entities, relationships, document_ref, source_page, figure_id)
}

pub fn merge_analyses(analyses: &[Value], document_ref: &str, figure_id: &str) -> Result<Value> {
    let mut normalized = Vec::new();
    for a in analyses {
        let mut entities = Vec::new();
        for raw in a.get("entities").and_then(Value::as_array).into_iter().flatten() {
            entities.push(entity(raw, &format!("entity {}", field(raw, "id")), false)?);
        }
        let mut relationships = Vec::new();
        for raw in a.get("relationships").and_then(Value::as_array).into_iter().flatten() {
            relationships.push(relationship(raw)?);
        }
        let mut value = a.clone();
        let object = value.as_object_mut().unwrap();
        object.insert("entities".to_string(), Value::Array(entities));
        object.insert("relationships".to_string(), Value::Array(relationships));
        normalized.push(value);
    }
    let analyses = &normalized;
    let mut by_name: BTreeMap<String, Value> = BTreeMap::new();
    let mut order: Vec<String> = Vec::new();
    for a in analyses {
        for raw in a.get("entities").and_then(Value::as_array).into_iter().flatten() {
            let key = norm_name(&field(raw, "name"));
            let merged = if let Some(old) = by_name.get(&key) {
                let description = if field(raw, "description").chars().count() > field(old, "description").chars().count() {
                    field(raw, "description")
                } else { field(old, "description") };
                let mut evidence = field(old, "source_evidence");
                let new_evidence = field(raw, "source_evidence");
                if !new_evidence.is_empty() && !evidence.contains(&new_evidence) {
                    evidence = if evidence.is_empty() { new_evidence }
                        else { format!("{evidence} | {new_evidence}").chars().take(2000).collect() };
                }
                let old_bbox = get(old, "bbox");
                let bbox = if old_bbox.is_null() { get(raw, "bbox") } else { old_bbox };
                let uncertainty = [field(old, "uncertainty"), field(raw, "uncertainty")]
                    .into_iter().filter(|s| !s.is_empty()).collect::<Vec<_>>().join("; ");
                let mask = if field(old, "mask_ref").is_empty() { field(raw, "mask_ref") } else { field(old, "mask_ref") };
                let mut value = old.clone();
                let object = value.as_object_mut().unwrap();
                object.insert("description".to_string(), json!(description));
                object.insert("source_evidence".to_string(), json!(evidence));
                object.insert("bbox".to_string(), bbox);
                object.insert("confidence".to_string(), json!(number(old, "confidence").max(number(raw, "confidence"))));
                object.insert("uncertainty".to_string(), json!(uncertainty.chars().take(500).collect::<String>()));
                object.insert("mask_ref".to_string(), json!(mask));
                object.insert("model_inferred".to_string(), json!(
                    get(old, "model_inferred").as_bool().unwrap_or(false)
                        && get(raw, "model_inferred").as_bool().unwrap_or(false)));
                value
            } else {
                order.push(key.clone());
                raw.clone()
            };
            by_name.insert(key, merged);
        }
    }
    let mut id_map: BTreeMap<String, String> = BTreeMap::new();
    for a in analyses {
        for raw in a.get("entities").and_then(Value::as_array).into_iter().flatten() {
            let surviving = by_name.get(&norm_name(&field(raw, "name"))).unwrap();
            id_map.insert(field(raw, "id"), field(surviving, "id"));
        }
    }
    let mut seen: BTreeSet<(String, String, String)> = BTreeSet::new();
    let mut rels = Vec::new();
    for a in analyses {
        for raw in a.get("relationships").and_then(Value::as_array).into_iter().flatten() {
            let source = id_map.get(&field(raw, "source_id")).cloned().unwrap_or_else(|| field(raw, "source_id"));
            let target = id_map.get(&field(raw, "target_id")).cloned().unwrap_or_else(|| field(raw, "target_id"));
            if source == target { continue; }
            let key = (source.clone(), target.clone(), field(raw, "rel_type"));
            if !seen.insert(key) { continue; }
            let mut rel = raw.clone();
            let object = rel.as_object_mut().unwrap();
            object.insert("source_id".to_string(), json!(source));
            object.insert("target_id".to_string(), json!(target));
            rels.push(rel);
        }
    }
    let mut entities = Vec::new();
    let mut final_id: BTreeMap<String, String> = BTreeMap::new();
    let mut used: BTreeSet<String> = BTreeSet::new();
    for key in &order {
        let entity = by_name[key].clone();
        let original = field(&entity, "id");
        let mut candidate = original.clone();
        let mut suffix = 2;
        while used.contains(&candidate) {
            candidate = format!("{original}-c{suffix}");
            suffix += 1;
        }
        used.insert(candidate.clone());
        final_id.entry(original).or_insert_with(|| candidate.clone());
        let mut value = entity;
        value.as_object_mut().unwrap().insert("id".to_string(), json!(candidate));
        entities.push(value);
    }
    for rel in &mut rels {
        let source = field(rel, "source_id");
        let target = field(rel, "target_id");
        let object = rel.as_object_mut().unwrap();
        object.insert("source_id".to_string(), json!(final_id.get(&source).cloned().unwrap_or(source)));
        object.insert("target_id".to_string(), json!(final_id.get(&target).cloned().unwrap_or(target)));
    }
    let doc_ref = if document_ref.is_empty() {
        analyses.first().map(|a| field(a, "document_ref")).unwrap_or_default()
    } else { document_ref.to_string() };
    analysis(entities, rels, &doc_ref, 0, figure_id)
}
