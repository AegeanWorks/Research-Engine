//! Generated MCP declarations, mirrored from studio/mcp.py.

pub const TOOLS_JSON: &str = r#"[
  {
    "description": "Search papers, claims and questions by phrase or multi-term overlap; returns compact refs, snippets and omitted counts under a token budget.",
    "inputSchema": {
      "properties": {
        "limit": {
          "default": 20,
          "type": "integer"
        },
        "min_confidence": {
          "type": "number"
        },
        "query": {
          "type": "string"
        },
        "stance": {
          "type": "string"
        },
        "tokens": {
          "default": 800,
          "type": "integer"
        },
        "year": {
          "type": "string"
        }
      },
      "required": [
        "query"
      ],
      "type": "object"
    },
    "name": "search"
  },
  {
    "description": "Search offline, arXiv, Crossref, OpenAlex, or EuropePMC catalogs and ingest papers.",
    "inputSchema": {
      "properties": {
        "ingest": {
          "default": true,
          "type": "boolean"
        },
        "limit": {
          "default": 10,
          "type": "integer"
        },
        "query": {
          "type": "string"
        },
        "source": {
          "default": "offline",
          "type": "string"
        }
      },
      "required": [
        "query"
      ],
      "type": "object"
    },
    "name": "discover_papers"
  },
  {
    "description": "Extract quote-backed claims and edges from one or all papers.",
    "inputSchema": {
      "properties": {
        "paper": {
          "type": "string"
        },
        "question": {
          "type": "string"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "extract_claims"
  },
  {
    "description": "Fetch one paper, claim or question with all attached edges.",
    "inputSchema": {
      "properties": {
        "ref": {
          "type": "string"
        }
      },
      "required": [
        "ref"
      ],
      "type": "object"
    },
    "name": "get_entity"
  },
  {
    "description": "List edges touching an entity, optionally filtered by kind.",
    "inputSchema": {
      "properties": {
        "kind": {
          "type": "string"
        },
        "ref": {
          "type": "string"
        }
      },
      "required": [
        "ref"
      ],
      "type": "object"
    },
    "name": "neighbors"
  },
  {
    "description": "Traverse the multi-hop neighborhood (depth 1-3) around an entity as compact refs and bare edges under a token budget; omitted nodes are reported.",
    "inputSchema": {
      "properties": {
        "depth": {
          "default": 1,
          "type": "integer"
        },
        "ref": {
          "type": "string"
        },
        "tokens": {
          "default": 800,
          "type": "integer"
        }
      },
      "required": [
        "ref"
      ],
      "type": "object"
    },
    "name": "subgraph"
  },
  {
    "description": "List findings connected to a claim, paper or question with the relation, reason and next-hop ref; snippets are budgeted and omissions reported.",
    "inputSchema": {
      "properties": {
        "limit": {
          "default": 10,
          "type": "integer"
        },
        "target": {
          "type": "string"
        },
        "tokens": {
          "default": 600,
          "type": "integer"
        }
      },
      "required": [
        "target"
      ],
      "type": "object"
    },
    "name": "related_findings"
  },
  {
    "description": "Cheap orientation map: counts, edge kinds, study-type mix and evidenced question refs, so an agent can choose where to expand next.",
    "inputSchema": {
      "properties": {
        "tokens": {
          "default": 400,
          "type": "integer"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "outline"
  },
  {
    "description": "Ingest one paper; duplicate DOIs, arXiv IDs and titles are merged.",
    "inputSchema": {
      "properties": {
        "abstract": {
          "type": "string"
        },
        "arxiv": {
          "type": "string"
        },
        "authors": {
          "type": "string"
        },
        "doi": {
          "type": "string"
        },
        "study_type": {
          "type": "string"
        },
        "tags": {
          "type": "string"
        },
        "title": {
          "type": "string"
        },
        "url": {
          "type": "string"
        },
        "venue": {
          "type": "string"
        },
        "year": {
          "type": "string"
        }
      },
      "required": [
        "title"
      ],
      "type": "object"
    },
    "name": "add_paper"
  },
  {
    "description": "Record a claim with the exact quote plus resolving locator that grounds it.",
    "inputSchema": {
      "properties": {
        "confidence": {
          "type": "number"
        },
        "locator": {
          "type": "string"
        },
        "paper": {
          "type": "string"
        },
        "quote": {
          "type": "string"
        },
        "stance": {
          "type": "string"
        },
        "text": {
          "type": "string"
        }
      },
      "required": [
        "paper",
        "text",
        "quote",
        "locator"
      ],
      "type": "object"
    },
    "name": "add_claim"
  },
  {
    "description": "Record a research question.",
    "inputSchema": {
      "properties": {
        "text": {
          "type": "string"
        }
      },
      "required": [
        "text"
      ],
      "type": "object"
    },
    "name": "add_question"
  },
  {
    "description": "Update a question status to open, answered or abandoned.",
    "inputSchema": {
      "properties": {
        "question": {
          "type": "string"
        },
        "status": {
          "type": "string"
        }
      },
      "required": [
        "question",
        "status"
      ],
      "type": "object"
    },
    "name": "set_question_status"
  },
  {
    "description": "Add a typed relation between two entities.",
    "inputSchema": {
      "properties": {
        "dst": {
          "type": "string"
        },
        "kind": {
          "type": "string"
        },
        "note": {
          "type": "string"
        },
        "src": {
          "type": "string"
        }
      },
      "required": [
        "src",
        "dst",
        "kind"
      ],
      "type": "object"
    },
    "name": "add_edge"
  },
  {
    "description": "Token-budgeted evidence pack for a question or search phrase.",
    "inputSchema": {
      "properties": {
        "target": {
          "type": "string"
        },
        "tokens": {
          "default": 2000,
          "type": "integer"
        }
      },
      "required": [
        "target"
      ],
      "type": "object"
    },
    "name": "brief"
  },
  {
    "description": "Markdown literature-review outline for a question or phrase.",
    "inputSchema": {
      "properties": {
        "target": {
          "type": "string"
        }
      },
      "required": [
        "target"
      ],
      "type": "object"
    },
    "name": "review"
  },
  {
    "description": "Consensus-scored scientific literature synthesis with clusters and BibTeX.",
    "inputSchema": {
      "properties": {
        "target": {
          "type": "string"
        },
        "tokens": {
          "default": 2500,
          "type": "integer"
        }
      },
      "required": [
        "target"
      ],
      "type": "object"
    },
    "name": "synthesize"
  },
  {
    "description": "Detect contradictions and related findings, rank keystone papers/claims, and build the Paper x Question matrix.",
    "inputSchema": {
      "properties": {
        "auto_link": {
          "default": false,
          "type": "boolean"
        },
        "limit": {
          "default": 10,
          "type": "integer"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "analyze_graph"
  },
  {
    "description": "Find opposing claims across shared questions or domain keywords.",
    "inputSchema": {
      "properties": {
        "auto_link": {
          "default": false,
          "type": "boolean"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "detect_contradictions"
  },
  {
    "description": "Export the graph to an atomic JSONL snapshot, BibTeX, GraphML, or Cytoscape file.",
    "inputSchema": {
      "properties": {
        "format": {
          "default": "jsonl",
          "enum": [
            "jsonl",
            "bibtex",
            "graphml",
            "cytoscape"
          ],
          "type": "string"
        },
        "path": {
          "type": "string"
        }
      },
      "required": [
        "path"
      ],
      "type": "object"
    },
    "name": "export_snapshot"
  },
  {
    "description": "Import a JSONL snapshot file idempotently.",
    "inputSchema": {
      "properties": {
        "path": {
          "type": "string"
        }
      },
      "required": [
        "path"
      ],
      "type": "object"
    },
    "name": "import_snapshot"
  },
  {
    "description": "Compare a JSONL snapshot against another snapshot or the live graph; reports added, removed and changed papers, questions, claims and edges.",
    "inputSchema": {
      "properties": {
        "new_path": {
          "type": "string"
        },
        "old_path": {
          "type": "string"
        }
      },
      "required": [
        "old_path"
      ],
      "type": "object"
    },
    "name": "diff_snapshot"
  },
  {
    "description": "Find the shortest chain of relations connecting two entities via BFS; returns the sequence of hops, node details and step-by-step reasoning narrative.",
    "inputSchema": {
      "properties": {
        "directed": {
          "default": false,
          "type": "boolean"
        },
        "dst": {
          "type": "string"
        },
        "edge_kinds": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "max_depth": {
          "default": 5,
          "type": "integer"
        },
        "src": {
          "type": "string"
        }
      },
      "required": [
        "src",
        "dst"
      ],
      "type": "object"
    },
    "name": "find_path"
  },
  {
    "description": "Formulate structured testable hypotheses from evidence matrix gaps and contradiction clusters.",
    "inputSchema": {
      "properties": {
        "limit": {
          "default": 5,
          "type": "integer"
        },
        "question": {
          "type": "string"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "propose_hypotheses"
  },
  {
    "description": "Record an auditable PRISMA 2020 screening decision for a paper.",
    "inputSchema": {
      "properties": {
        "notes": {
          "type": "string"
        },
        "paper_id": {
          "type": "string"
        },
        "reason": {
          "type": "string"
        },
        "status": {
          "enum": [
            "identified",
            "screened_in",
            "screened_out",
            "included",
            "excluded"
          ],
          "type": "string"
        }
      },
      "required": [
        "paper_id",
        "status"
      ],
      "type": "object"
    },
    "name": "screen_paper"
  },
  {
    "description": "Calculate PRISMA 2020 review attrition metrics, flow counts and optional SVG/Markdown representation.",
    "inputSchema": {
      "properties": {
        "format": {
          "default": "json",
          "enum": [
            "json",
            "markdown",
            "svg"
          ],
          "type": "string"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "get_prisma_flow"
  },
  {
    "description": "Assemble a high-density, token-bounded GraphRAG context pack for LLM reasoning.",
    "inputSchema": {
      "properties": {
        "format": {
          "default": "markdown",
          "enum": [
            "markdown",
            "json"
          ],
          "type": "string"
        },
        "max_tokens": {
          "default": 2000,
          "description": "Maximum token budget (default: 2000)",
          "type": "integer"
        },
        "targets": {
          "description": "Target question, paper or claim references, or search phrases",
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "get_context_pack"
  },
  {
    "description": "Calculate pooled effect sizes, Cochran's Q, I-squared, and ASCII/SVG forest plots.",
    "inputSchema": {
      "properties": {
        "format": {
          "default": "json",
          "enum": [
            "json",
            "ascii",
            "svg"
          ],
          "type": "string"
        },
        "model": {
          "default": "random",
          "enum": [
            "random",
            "fixed"
          ],
          "type": "string"
        },
        "question": {
          "description": "Optional question reference to auto-extract linked claims as studies",
          "type": "string"
        },
        "studies": {
          "description": "List of study objects with effect_size and se or ci bounds, or two-group parameters",
          "items": {
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [],
      "type": "object"
    },
    "name": "compute_meta_analysis"
  },
  {
    "description": "Entity and edge counts.",
    "inputSchema": {
      "properties": {},
      "required": [],
      "type": "object"
    },
    "name": "stats"
  }
]"#;

pub const RESOURCES_JSON: &str = r#"[
  {
    "description": "Counts of papers, claims, questions and typed edges.",
    "mimeType": "application/json",
    "name": "Graph Statistics",
    "uri": "lattice://stats"
  },
  {
    "description": "All tracked research questions and their status.",
    "mimeType": "application/json",
    "name": "Research Questions",
    "uri": "lattice://questions"
  },
  {
    "description": "Structured Paper x Question evidence matrix and coverage gaps.",
    "mimeType": "application/json",
    "name": "Paper x Question Evidence Matrix",
    "uri": "lattice://matrix"
  }
]"#;

pub const PROMPTS_JSON: &str = r#"[
  {
    "arguments": [
      {
        "description": "Question ID or scientific query",
        "name": "target",
        "required": true
      }
    ],
    "description": "Assemble a citation-checked scientific synthesis for a research question or query.",
    "name": "literature-synthesis"
  }
]"#;
