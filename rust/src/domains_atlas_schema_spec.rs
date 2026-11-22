//! Generated Muse JSON schema, mirrored from domains/atlas/schema.py.
pub const MUSE_JSON_SCHEMA: &str = r#"{
  "name": "AtlasVisualKnowledge",
  "schema": {
    "additionalProperties": false,
    "properties": {
      "entities": {
        "items": {
          "additionalProperties": false,
          "properties": {
            "box": {
              "items": {
                "maximum": 1000,
                "minimum": 0,
                "type": "number"
              },
              "maxItems": 4,
              "minItems": 4,
              "type": "array"
            },
            "category": {
              "enum": [
                "anatomical-structure",
                "cell-type",
                "component",
                "function",
                "molecule",
                "other",
                "pathway",
                "person",
                "place",
                "process",
                "protein"
              ],
              "type": "string"
            },
            "confidence": {
              "maximum": 1,
              "minimum": 0,
              "type": "number"
            },
            "description": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "source_evidence": {
              "type": "string"
            },
            "uncertainty": {
              "type": "string"
            }
          },
          "required": [
            "id",
            "name",
            "category",
            "confidence"
          ],
          "type": "object"
        },
        "type": "array"
      },
      "relationships": {
        "items": {
          "additionalProperties": false,
          "properties": {
            "confidence": {
              "maximum": 1,
              "minimum": 0,
              "type": "number"
            },
            "explanation": {
              "type": "string"
            },
            "rel_type": {
              "enum": [
                "activates",
                "contains",
                "inhibits",
                "participates-in",
                "produces",
                "projects-to",
                "receives-input-from",
                "regulates"
              ],
              "type": "string"
            },
            "source_id": {
              "type": "string"
            },
            "supporting_evidence": {
              "type": "string"
            },
            "target_id": {
              "type": "string"
            }
          },
          "required": [
            "source_id",
            "target_id",
            "rel_type",
            "confidence"
          ],
          "type": "object"
        },
        "type": "array"
      }
    },
    "required": [
      "entities",
      "relationships"
    ],
    "type": "object"
  }
}"#;
