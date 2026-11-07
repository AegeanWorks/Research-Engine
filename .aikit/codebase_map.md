# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `399`
- **Total Classes**: `290`
- **Total Top-Level Functions**: `1887`
- **Total Class Methods**: `1422`
- **Total Source Lines**: `86971`

---

## 📦 Modules & Exported Symbols

### [`adapters/__init__.py`](adapters/__init__.py)
> *Adapters that bind external research systems to the host.*

**Size**: `1` lines (`64` bytes)

---

### [`adapters/lattice/__init__.py`](adapters/lattice/__init__.py)
> *Lattice: a provenance-first research knowledge graph for humans and AI agents.*

**Size**: `6` lines (`111` bytes)

---

### [`adapters/lattice/__main__.py`](adapters/lattice/__main__.py)
> *Run the command-line interface with `python -m adapters.lattice`.*

**Size**: `8` lines (`172` bytes)

---

### [`adapters/lattice/analysis.py`](adapters/lattice/analysis.py)
> *Contradiction detection, related-finding links, keystone ranking and evidence matrices.*

**Size**: `897` lines (`36375` bytes)

**Classes:**
- `class ContradictionPair` - *An opposing pair of empirical claims sharing a research question or high domain keyword overlap.*
  - Method `.to_dict()` - *JSON-serializable representation.*
- `class RelatedPair` - *Two findings related by a shared research question or a domain-keyword overlap.*
  - Method `.to_dict()` - *JSON-serializable representation.*

**Functions:**
- `def _domain_keywords(text)` - *Extract informative domain keywords of length >= 4 from claim text.*
- `def _claim_question_map(repo)` - *Map bare claim IDs to bare question IDs linked via edges.*
- `def _find_or_create_contradicts_edge(repo, claim_a_id, claim_b_id, auto_link)` - *Return existing `contradicts` edge ID between two claims, or create one when `auto_link` is True.*
- `def detect_contradictions(repo, auto_link)` - *Detect pairs of opposing claims (`supports` vs `contradicts`) across questions or domain topics.*
- `def _connected_claim_pairs(repo)` - *Unordered bare claim-ID pairs that any claim-to-claim edge already joins.*
- `def find_related_findings(repo, claim_ids, limit_per_claim)` - *Detect findings sharing a research question or enough domain keywords to be related.*
- `def link_related_findings(repo, claim_ids, limit_per_claim)` - *Create `related` edges for detected finding pairs that are not linked yet.*
- `def _related_reason(entry)` - *Human-readable explanation of why a finding is related.*
- `def related_findings(repo, ref, limit)` - *Findings connected to a claim, paper or question, with reasons and next-hop references.*
- `def rank_influential_entities(repo, limit)` - *Rank keystone papers and claims by evidence centrality, citation degree, and confidence.*
- `def build_evidence_matrix(repo)` - *Build a Paper x Question evidence matrix highlighting stance cells and coverage gaps.*
- `def find_path(repo, src, dst, max_depth, directed, edge_kinds)` - *Find the shortest chain of relations connecting two entities via BFS.*
- `def _extract_variables_from_question(question)` - *Extract candidate independent and dependent variables from a question prompt.*
- `def propose_hypotheses(repo, question_ref, limit)` - *Synthesize evidence matrix gaps and contradiction clusters into testable hypotheses.*

---

### [`adapters/lattice/checks.py`](adapters/lattice/checks.py)
> *Integrity gate: every citation, endpoint, quote and support cycle is decidable locally.*

**Size**: `267` lines (`10956` bytes)

**Classes:**
- `class CheckIssue` - *One finding, tagged error or warning and named by a stable code.*
  - Method `.to_dict()` - *JSON-ready representation.*
- `class CheckReport` - *The gate's complete result; only errors block delivery.*
  - Property `.errors` - *Blocking findings.*
  - Property `.warnings` - *Non-blocking findings.*
  - Property `.passed` - *True when no blocking finding exists.*
  - Method `.to_dict()` - *JSON-ready representation used by the CLI and MCP clients.*

**Functions:**
- `def run_checks(repository)` - *Run every integrity check and return one report.*
- `def _check_schema(connection, report)` - *The database must declare this build's schema version.*
- `def _check_claims(connection, report)` - *Every claim needs assertion text, a quote, a locator and an existing paper.*
- `def _check_quote_drift(row, report)` - *The verbatim quote must still appear in its paper's stored title+abstract.*
- `def _check_locator_resolves(row, report)` - *The abstract/text locator family must resolve against the stored abstract.*
- `def _check_edges(connection, report)` - *Both endpoints of every edge must exist.*
- `def _check_duplicates(connection, report)` - *DOI, arXiv and normalized title/year duplicates are errors.*
- `def _check_support_cycles(connection, report)` - *Support and extension relations between claims must stay acyclic.*
- `def _cycles(graph)` - *Every distinct cycle reachable in a directed graph, each reported once.*
- `def _canonical_cycle(cycle)` - *A rotation-independent form so the same cycle is reported once.*
- `def _check_orphans(connection, report)` - *Warnings for questions without evidence and claims with no question link.*
- `def _exists(connection, ref)` - *Whether a reference's target row exists.*
- `def summarize(report)` - *Error and warning counts for a compact text report.*

---

### [`adapters/lattice/cli.py`](adapters/lattice/cli.py)
> *Command-line interface: ingest, assert, link, ask, brief, review, check and serve MCP.*

**Size**: `863` lines (`39111` bytes)

**Functions:**
- `def build_parser()` - *The complete command grammar.*
- `def main(argv)` - *Parse arguments, open the database and dispatch one command.*
- `def _emit(payload, lines, as_json)` - *Print either stable JSON or human text.*
- `def _run_init(args, repository)` - *Create the schema, which opening the database already did.*
- `def _run_ingest(args, repository)` - *Import every file and report created versus merged records.*
- `def _run_fetch(args, repository)` - *Discover candidate papers and optionally ingest them.*
- `def _run_extract(args, repository)` - *Extract quote-backed claims and question links from one or all papers.*
- `def _run_claim(args, repository)` - *Record one claim.*
- `def _run_question(args, repository)` - *Record one question.*
- `def _run_link(args, repository)` - *Record one typed edge.*
- `def _run_search(args, repository)` - *Search and print the three result sections.*
- `def _run_show(args, repository)` - *Show one entity and each attached edge.*
- `def _run_subgraph(args, repository)` - *Traverse and print the multi-hop neighborhood around an entity.*
- `def _run_path(args, repository)` - *Trace and print the shortest relation path between two entities.*
- `def _run_related(args, repository)` - *List findings connected to an entity, with the reason for each connection.*
- `def _run_outline(args, repository)` - *Print a cheap orientation index before an agent expands a reference.*
- `def _run_ask(args, repository)` - *Assemble and print evidence.*
- `def _run_brief(args, repository)` - *Print a token-budgeted evidence pack.*
- `def _run_review(args, repository)` - *Print or write a review outline.*
- `def _run_synthesize(args, repository)` - *Generate a consensus-scored scientific synthesis report.*
- `def _run_export(args, repository)` - *Export the graph to an atomic JSONL snapshot, BibTeX, GraphML, or Cytoscape file.*
- `def _run_import(args, repository)` - *Import a JSONL snapshot idempotently.*
- `def _run_diff(args, repository)` - *Diff snapshots, or a snapshot against the live graph; exit 1 when they differ.*
- `def _run_stats(args, repository)` - *Print counts and evidence health.*
- `def _run_check(args, repository)` - *Run the integrity gate and return 1 on any error.*
- `def _run_mcp(args, repository)` - *Serve MCP on stdio; stdout carries protocol messages only.*
- `def _run_web(args, repository)` - *Launch the Research Studio web UI, optionally seeding demo data or dumping HTML.*
- `def _run_analyze(args, repository)` - *Detect contradictions and related findings, rank keystones, and build the matrix.*
- `def _run_hypothesize(args, repository)` - *Propose testable research hypotheses based on contradictions and coverage gaps.*
- `def _run_screen(args, repository)` - *Record or query a screening decision for a paper.*
- `def _run_prisma(args, repository)` - *Generate PRISMA 2020 flow statistics and diagram.*
- `def _run_pack(args, repository)` - *Generate a token-bounded GraphRAG context pack for LLM agents.*
- `def _run_meta(args, repository)` - *Execute quantitative meta-analysis and render forest plot.*

---

### [`adapters/lattice/context.py`](adapters/lattice/context.py)
> *Token-budgeted context views for AI agents: peek, search, expand, drill down.*

**Size**: `549` lines (`22377` bytes)

**Classes:**
- `class ContextPack` - *Token-budgeted GraphRAG context pack for LLM reasoning and question-answering.*
  - Method `.to_dict()` - *JSON-ready representation.*

**Functions:**
- `def _budget(tokens)` - *Validate a token budget and return it as an integer.*
- `def _truncate(text, limit)` - *Collapse whitespace and shorten a value to `limit` characters.*
- `def _cost(item)` - *Estimated tokens of one JSON item.*
- `def _pack(items, tokens)` - *Keep as many leading items as fit, returning `(kept, omitted, used_tokens)`.*
- `def outline(repository, tokens)` - *A cheap orientation map: counts, edge kinds, study types and evidenced questions.*
- `def compact_search(result, tokens)` - *Search hits as short handles, split across papers, claims and questions.*
- `def compact_related(result, tokens)` - *Related-finding navigation as short snippets, reasons and next-hop refs.*
- `def compact_subgraph(result, tokens)` - *A subgraph as short node labels and bare edges, trimmed around a token budget.*
- `def _render_markdown_pack(targets, questions, claims, papers, contradictions, budget)`
- `def _render_json_pack(targets, questions, claims, papers, contradictions, budget)`
- `def build_context_pack(repository, targets, max_tokens, format)` - *Assemble a high-density, token-bounded GraphRAG context pack for AI agents.*

---

### [`adapters/lattice/database.py`](adapters/lattice/database.py)
> *SQLite connection, versioned schema and migration veil for the knowledge graph.*

**Size**: `228` lines (`9475` bytes)

**Functions:**
- `def utc_now()` - *An ISO-8601 UTC timestamp with a stable seconds precision.*
- `def open_database(path, read_only)` - *Open or create the database, verify its schema version and return it.*
- `def _verify_schema_read_only(connection)` - *Verify a read-only database is current without creating or migrating anything.*
- `def _ensure_schema(connection)` - *Create the schema once, migrate v1 and refuse a database from a newer version.*
- `def _set_schema_version(connection, version)` - *Persist the schema version after a fresh create or a completed migration.*
- `def _add_column_if_missing(connection, table, column, definition)` - *Add one column once, so an interrupted migration can be retried.*
- `def _migrate_v1_to_v2(connection)` - *Add searchable tags and study type, backfilling them for existing papers.*
- `def schema_version(connection)` - *The declared schema version, or 0 when the metadata row is missing.*

---

### [`adapters/lattice/diff.py`](adapters/lattice/diff.py)
> *Deterministic diffing between JSONL graph snapshots and the live repository.*

**Size**: `101` lines (`4335` bytes)

**Functions:**
- `def _index_records(records)` - *Key snapshot records by `(record_type, id)`; unknown record types are skipped.*
- `def _counts(records)` - *Per-type record counts keyed by plural table names.*
- `def _database_label(repository)` - *The repository's database file path, or `:memory:` for an in-memory graph.*
- `def diff_records(old_records, new_records)` - *Compare two snapshot record sets and report added, removed and changed entities.*
- `def diff_snapshots(old_path, new_path)` - *Diff two JSONL snapshot files: the baseline `old_path` against the newer `new_path`.*
- `def diff_snapshot(repository, path)` - *Diff a JSONL snapshot (baseline) against the live repository (current).*

---

### [`adapters/lattice/discovery.py`](adapters/lattice/discovery.py)
> *Pluggable automated literature discovery: arXiv, Crossref, OpenAlex, EuropePMC, and offline corpus.*

**Size**: `594` lines (`25133` bytes)

**Classes:**
- `class PaperCandidate` - *Immutable DTO returned by any literature discovery provider.*
  - Method `.to_metadata()` - *Dictionary ready for `Repository.add_paper`.*
  - Method `.to_dict()` - *JSON-serializable representation including discovery source.*
- `class LiteratureProvider` - *Contract layer for pluggable scientific literature search providers.*
  - Method `.search(query, limit)` - *Return up to `limit` candidate papers matching `query`.*
- `class ProviderRegistry` - *Registry layer mapping provider names to `LiteratureProvider` implementations.*
  - Method `.__init__()`
  - Method `.register(name, provider)` - *Register or replace a provider by lowercase key.*
  - Method `.get(name)` - *Look up a registered provider or raise `LatticeError`.*
  - Method `.names()` - *Sorted list of registered provider names.*
- `class ArxivProvider` - *Concrete provider querying the arXiv Atom API.*
  - Method `.__init__(fetcher, timeout)`
  - Method `.search(query, limit)` - *Search arXiv by query terms and parse Atom XML entries.*
- `class CrossrefProvider` - *Concrete provider querying the Crossref REST works endpoint.*
  - Method `.__init__(fetcher, timeout)`
  - Method `.search(query, limit)` - *Search Crossref works and normalize bibliographic items.*
- `class OpenAlexProvider` - *Concrete provider querying the OpenAlex works REST endpoint.*
  - Method `.__init__(fetcher, timeout)`
  - Method `.search(query, limit)` - *Search OpenAlex works and reconstruct inverted-index abstracts.*
- `class EuropePmcProvider` - *Concrete provider querying the EuropePMC biomedical REST API.*
  - Method `.__init__(fetcher, timeout)`
  - Method `.search(query, limit)` - *Search EuropePMC articles and extract biomedical metadata and abstracts.*
- `class OfflineCorpusProvider` - *Deterministic local provider over a curated seed catalog for offline/instant search.*
  - Method `.__init__(records)`
  - Method `.search(query, limit)` - *Rank local corpus records by token overlap with `query`.*
- `class DiscoveryService` - *Orchestration layer with constructor DI for discovering and ingesting papers.*
  - Method `.__init__(repository, registry)`
  - Method `.discover(query, source, limit, ingest)` - *Search one or comma-separated `source` providers and optionally ingest papers.*

**Functions:**
- `def _http_get(url, timeout)` - *Perform a bounded HTTP GET with a scholarly User-Agent header.*
- `def default_registry()` - *Create the default provider registry with offline, arXiv, Crossref, OpenAlex, and EuropePMC.*
- `def _dedupe_candidates(candidates)` - *Deduplicate candidate papers across providers by DOI, arXiv ID, or normalized title.*
- `def _reconstruct_inverted_abstract(inverted)` - *Reconstruct a plain-text abstract from an OpenAlex inverted index mapping.*
- `def _validate_search_args(query, limit)` - *Ensure a discovery query is non-empty and `limit` is positive.*
- `def _format_crossref_authors(authors)` - *Join Crossref author objects into `Given Family; Given Family`.*
- `def _extract_crossref_year(item)` - *Extract a 4-digit publication year from Crossref date-parts.*

---

### [`adapters/lattice/errors.py`](adapters/lattice/errors.py)
> *The one error type every layer raises, carrying the Error/Why/Fix triad.*

**Size**: `22` lines (`738` bytes)

**Classes:**
- `class LatticeError` - *A user-facing failure: what happened, why it matters and how to fix it.*
  - Method `.__init__(message, why, fix)`
  - Method `.render()` - *The full three-line report used by the CLI and the MCP server.*

**Functions:**
- `def fail(message, why, fix)` - *Raise a `LatticeError`; keeps call sites to one line.*

---

### [`adapters/lattice/extraction.py`](adapters/lattice/extraction.py)
> *Automated knowledge creation: extract quote-backed claims and question links from papers.*

**Size**: `222` lines (`8860` bytes)

**Classes:**
- `class ExtractionResult` - *Immutable summary of claims and edges extracted from a single paper.*
  - Method `.to_dict()` - *JSON-ready representation.*

**Functions:**
- `def split_empirical_sentences(text, prefix)` - *Split text into `(locator, sentence)` pairs, keeping sentences with empirical findings.*
- `def infer_stance(sentence)` - *Classify an empirical sentence as `supports`, `contradicts`, or `mentions`.*
- `def infer_confidence(sentence)` - *Assign a deterministic confidence weight in [0.55, 0.95] from evidential markers.*
- `def extract_from_paper(repository, paper_ref, question_ref, text)` - *Extract quote-backed claims from a paper and link them to matching or target questions.*
- `def extract_all(repository, question_ref)` - *Run claim and edge extraction across every ingested paper in the graph.*
- `def _is_empirical(sentence)` - *Whether a sentence carries quantitative or empirical indicators.*
- `def _matches_question(sentence, title, question_text)` - *Whether a claim sentence and its paper title share content keywords with a question.*
- `def _safe_add_edge(repository, src, dst, kind, note)` - *Add an edge if it does not already exist.*

---

### [`adapters/lattice/ingest.py`](adapters/lattice/ingest.py)
> *Parsers for the text bibliography formats lattice accepts, with no third-party dependencies.*

**Size**: `538` lines (`21014` bytes)

**Functions:**
- `def empty_record()` - *A record with every supported metadata field present.*
- `def _clean(value)` - *Collapse whitespace and strip one layer of surrounding delimiters.*
- `def _braced_span(text, start)` - *Index of the brace closing the one at `start`, or -1 when it is unbalanced.*
- `def _split_top_level(text)` - *Split a BibTeX field list on commas that are not inside braces or quotes.*
- `def parse_bibtex(text)` - *Parse one or more BibTeX entries into metadata records.*
- `def parse_ris(text)` - *Parse RIS records into metadata records.*
- `def parse_csv(text)` - *Parse a CSV with a header row naming any of the supported metadata fields.*
- `def parse_csl_json(text)` - *Parse one or more CSL-JSON items into metadata records.*
- `def parse_markdown(text, source_name)` - *Parse one Markdown note: YAML-like front matter, a heading or the filename as title.*
- `def parse_text(text, source_name)` - *Parse a plain-text note as one record titled by its filename.*
- `def parse_file(path)` - *Detect a file's format by suffix and parse it.*
- `def parse_paths(paths)` - *Parse every path in order and concatenate the records.*
- `def sync_article_from_neurocore(repository, article_data, auto_extract)` - *Sync a NeuroCore article dictionary into the Lattice graph.*

---

### [`adapters/lattice/inquiry.py`](adapters/lattice/inquiry.py)
> *Evidence-first question answering: `ask`, token-budgeted `brief` and `review` outlines.*

**Size**: `344` lines (`14639` bytes)

**Functions:**
- `def ask(repository, target, limit)` - *Return evidence for a question, or matching claims when the target is a search phrase.*
- `def brief(repository, target, tokens)` - *Pack the strongest evidence for an agent under a deterministic token budget.*
- `def review(repository, target)` - *A Markdown literature-review outline with every citation resolved in the graph.*
- `def _match_question(repository, target)` - *A question named by reference, exact text or unique substring.*
- `def _suggestions(repository, question, linked, limit)` - *Unlinked claims whose text matches a keyword from the question.*
- `def _keywords(text)` - *Distinct lowercase words of at least four letters, without common question words.*
- `def _question_header(evidence)` - *The fixed header of a question brief.*
- `def _claim_line(item)` - *One evidence line: claim, confidence, quote, locator and source.*
- `def _search_line(claim)` - *One search hit line with its grounding quote and locator.*
- `def _suggestion_lines(suggestions)` - *Unlinked claim candidates, one line each (pointers, never evidence).*
- `def _fits(lines, candidate, tokens)` - *Whether adding one line keeps the estimate under the budget.*
- `def _fit(lines, candidates, tokens)` - *Append candidate lines while the running estimate stays under the budget.*
- `def _citation_lines(repository, refs)` - *Resolved citation lines for paper references, in first-seen order.*
- `def _citation_short(paper)` - *A compact inline source label.*
- `def _question_review(evidence)` - *Render a question's evidence as a review outline.*
- `def _review_section(title, items)` - *One evidence section of a review outline.*
- `def _paper_refs(evidence)` - *Distinct paper references touched by evidence or search results.*
- `def _search_review(evidence)` - *Render matching papers and claims when the target is not a tracked question.*

---

### [`adapters/lattice/meta.py`](adapters/lattice/meta.py)
> *Quantitative meta-analysis engine: fixed/random effects pooling, Cochran's Q, I-squared, and Forest Plots.*

**Size**: `530` lines (`19971` bytes)

**Classes:**
- `class MetaStudy` - *An individual study effect size and standard error for quantitative pooling.*
  - Method `.to_dict()` - *JSON-ready representation.*
- `class MetaAnalysisResult` - *Consolidated quantitative meta-analysis statistical report.*
  - Method `.to_dict()` - *JSON-ready representation.*

**Functions:**
- `def _chi2_sf(x, df)` - *Survival function (p-value, 1 - CDF) for chi-square distribution with df degrees of freedom.*
- `def study_from_confidence_interval(id, label, effect_size, ci_lower, ci_upper, study_type)` - *Construct a MetaStudy from a point estimate and 95% confidence interval.*
- `def study_from_two_groups(id, label, n1, m1, sd1, n2, m2, sd2, study_type)` - *Compute Hedges' g standardized mean difference from two-arm trial statistics.*
- `def _coerce_study(item)` - *Convert a dictionary or MetaStudy instance into a normalized MetaStudy.*
- `def compute_meta_analysis(studies, model)` - *Execute fixed or DerSimonian-Laird random effects quantitative meta-analysis.*
- `def render_forest_ascii(result, width)` - *Format quantitative meta-analysis results as an aligned ASCII forest plot.*
- `def render_forest_svg(result, title)` - *Generate a publication-grade, self-contained SVG forest plot.*
- `def meta_analyze_question(repository, question_ref, model)` - *Execute quantitative meta-analysis on evidentiary claims connected to a question.*

---

### [`adapters/lattice/models.py`](adapters/lattice/models.py)
> *Value objects and the validation rules shared by storage, ingestion and queries.*

**Size**: `366` lines (`12975` bytes)

**Classes:**
- `class Paper` - *A source record: bibliographic metadata plus its stable identifier.*
  - Method `.to_dict()` - *JSON-ready representation.*
- `class Claim` - *One asserted statement tied to an exact source quote and locator.*
  - Method `.to_dict()` - *JSON-ready representation.*
- `class Question` - *A research question whose evidence is assembled from linked claims.*
  - Method `.to_dict()` - *JSON-ready representation.*
- `class Edge` - *A typed, directed relation between two entity references.*
  - Method `.to_dict()` - *JSON-ready representation, including resolved endpoint details when present.*

**Functions:**
- `def normalize_text(value)` - *Lowercase and collapse punctuation for identity comparisons.*
- `def normalize_tags(value)` - *Normalize comma- or semicolon-separated tags into one lowercase, deduplicated string.*
- `def derive_tags(title, abstract, limit)` - *Derive deterministic keyword tags, weighting title words over abstract words.*
- `def normalize_study_type(value)` - *Trim a study type and map common abbreviations to a canonical label.*
- `def infer_study_type(title, abstract)` - *Classify a paper by design markers in its title and abstract.*
- `def paper_id(title, doi, arxiv)` - *A stable identifier derived from DOI, then arXiv ID, then normalized title.*
- `def next_id(prefix, rows)` - *The next sequential identifier for a table whose ids share a prefix.*
- `def validate_stance(stance)` - *A claim stance must be one of `STANCES`.*
- `def parse_confidence(value)` - *Confidence is a number in [0, 1]; the default is 0.5.*
- `def validate_edge_kind(kind)` - *An edge kind must be one of `EDGE_KINDS`.*
- `def validate_locator(locator)` - *A claim locator must be a non-empty pointer to its source.*
- `def entity_type(ref)` - *The entity type named by a reference such as `claim:c_000001`.*
- `def validate_ref(ref)` - *Normalize `claim:c_000001` and reject malformed references.*
- `def bare_id(ref)` - *The identifier part of a reference.*
- `def estimate_tokens(text)` - *A deterministic, conservative token estimate used by `brief`.*

---

### [`adapters/lattice/repository.py`](adapters/lattice/repository.py)
> *The knowledge graph API: papers, claims, questions, typed edges and evidence queries.*

**Size**: `674` lines (`32623` bytes)

**Classes:**
- `class Repository` - *One connection's view of the graph; every write is committed before it returns.*
  - Method `.__init__(connection)`
  - Method `.add_paper(metadata)` - *Insert a paper, or merge missing metadata into the matching existing record.*
  - Method `.add_claim(paper, text, quote, locator, stance, confidence)` - *Record one claim with the exact source quote that grounds it.*
  - Method `.add_question(text)` - *Record a research question that evidence can later be linked to.*
  - Method `.add_edge(src, dst, kind, note)` - *Add a typed relation after checking both endpoints exist.*
  - Method `.get_paper(identifier)` - *A paper by bare id or reference.*
  - Method `.get_claim(identifier)` - *A claim by bare id or reference.*
  - Method `.get_question(identifier)` - *A question by bare id or reference.*
  - Method `.get(ref)` - *One entity and every edge attached to it.*
  - Method `.search(query, limit, stance, min_confidence, year)` - *Search papers, claims and questions by phrase or multi-term lexical overlap.*
  - Method `.search_literature(query, tags, study_type, year, limit)` - *Search papers by tags, words, sentences, study type or year.*
  - Method `.export_bibtex(query, tags, study_type, year)` - *Export papers matching filters as deterministic BibTeX entries.*
  - Method `.set_question_status(question, status)` - *Update a question's lifecycle status ('open', 'answered' or 'abandoned').*
  - Method `.subgraph(ref, depth)` - *Return the multi-hop neighborhood of nodes and edges around `ref`.*
  - Method `.neighbors(ref, kind)` - *Every edge touching `ref`, optionally narrowed to one kind.*
  - Method `.evidence(question)` - *Claims linked to a question, grouped by the stance of the link.*
  - Method `.stats()` - *Entity and edge counts plus evidence health for a quick orientation report.*
  - Method `._evidence_health(papers, claims)` - *Adoption metrics: claim density, question status mix, linkage, gaps and contest.*
  - Method `._resolve(value)` - *Accept a full reference or a bare id and return the validated reference.*
  - Method `._row(query, *args)` - *One row or None.*
  - Method `._ids(table)` - *Every id in a table, used to allocate the next sequential claim or question id.*
  - Method `._find_paper(metadata)` - *Find a duplicate by DOI, arXiv ID, or normalized title and year.*
  - Method `._merge_paper(existing, metadata)` - *Fill fields the existing record lacks; return the names that changed.*
  - Method `._claim_dict(claim)` - *A claim plus a compact citation summary of its paper.*
  - Method `._safe_summary(ref)` - *Summary of an entity, or a missing marker instead of raising.*
  - Method `._summary(ref)` - *A compact JSON representation of any entity, with paper context for claims.*
  - Method `._study_type(ref)` - *The study type behind a paper or claim, or every type linked to a question.*
  - Method `._log(action, payload)` - *Append an immutable audit event.*
  - Method `._search_papers(raw_query, terms, year, limit)` - *Rank papers by exact substring match first, then multi-term lexical overlap.*
  - Method `._search_claims(raw_query, terms, stance, min_confidence, year, limit)` - *Rank claims by phrase or multi-term overlap and apply optional filters.*
  - Method `._search_questions(raw_query, terms, limit)` - *Rank questions by phrase or multi-term overlap.*

**Functions:**
- `def _paper(row)` - *Map a papers row to its value object.*
- `def _claim(row)` - *Map a claims row to its value object.*
- `def _question(row)` - *Map a questions row to its value object.*
- `def _edge(row)` - *Map an edges row to its value object.*
- `def _lexical_score(needle, terms, blob, primary)` - *Compute a deterministic relevance score combining exact substring and multi-term hits.*
- `def _normalize_doi(value)` - *Strip resolver prefixes and lowercase a DOI.*
- `def _normalize_arxiv(value)` - *Strip the arXiv prefix from an identifier.*

---

### [`adapters/lattice/screening.py`](adapters/lattice/screening.py)
> *PRISMA 2020 systematic review screening workflow and flow diagram generation.*

**Size**: `359` lines (`14172` bytes)

**Classes:**
- `class ScreeningDecision` - *An auditable screening outcome for a source paper.*
  - Method `.to_dict()` - *JSON-ready representation.*
- `class PrismaFlow` - *Standardized counts and reason breakdowns across PRISMA 2020 review phases.*
  - Method `.to_dict()` - *JSON-ready representation.*

**Functions:**
- `def record_screening_decision(repository, paper_id, status, reason, notes)` - *Record or update a screening decision for a paper in the knowledge graph.*
- `def get_screening_decision(repository, paper_id)` - *Retrieve the current screening decision for a paper, if recorded.*
- `def list_screening_decisions(repository, status)` - *List recorded screening decisions, optionally filtered by status.*
- `def compute_prisma_flow(repository)` - *Compute aggregate counts and exclusion reasons adhering to the PRISMA 2020 statement.*
- `def render_prisma_markdown(flow)` - *Format PRISMA 2020 metrics as a structured Markdown flow report.*
- `def render_prisma_svg(flow)` - *Generate a publication-grade PRISMA 2020 vector flowchart in SVG.*

---

### [`adapters/lattice/snapshots.py`](adapters/lattice/snapshots.py)
> *Portable JSONL graph snapshots with atomic write and idempotent merge import.*

**Size**: `441` lines (`17590` bytes)

**Functions:**
- `def collect_repository_records(repository)` - *Every paper, question, claim and edge as a snapshot record, in stable export order.*
- `def read_snapshot_records(path)` - *Read a JSONL snapshot file into validated records.*
- `def export_snapshot(repository, path)` - *Write all papers, questions, claims and edges to a portable JSONL file atomically.*
- `def export_bibtex_file(repository, path)` - *Write papers in the graph to a BibTeX file atomically.*
- `def _add_graphml_data(elem, key, value)`
- `def export_graphml_string(repository)` - *Generate standard GraphML XML string representing the evidence graph.*
- `def export_graphml_file(repository, path)` - *Write graph in GraphML XML format atomically.*
- `def export_cytoscape_data(repository)` - *Generate Cytoscape.js elements dictionary for graph visualization.*
- `def export_cytoscape_file(repository, path)` - *Write graph in Cytoscape.js JSON format atomically.*
- `def import_snapshot(repository, path)` - *Import a JSONL snapshot idempotently, remapping entity references as needed.*
- `def _parse_jsonl(lines, label)` - *Parse non-empty JSONL lines and verify each is an object.*
- `def _import_question(repository, record)` - *Find an existing question with the same text or create it.*
- `def _import_claim(repository, record, paper_map)` - *Find an existing claim on the target paper or create it.*
- `def _import_edge(repository, record, paper_map, claim_map, question_map)` - *Remap endpoints and insert the edge if not already present.*
- `def _remap_ref(ref, paper_map, claim_map, question_map)` - *Translate an exported entity reference to its imported identifier.*

---

### [`adapters/lattice/start.py`](adapters/lattice/start.py)
> *Start file launcher for the ported Lattice Research Studio and CLI.*

**Size**: `34` lines (`1114` bytes)

**Functions:**
- `def _with_project_db(argv)` - *Use the project-local database unless the caller explicitly chose one.*
- `def start(argv)` - *Launch the Lattice Web Research Studio by default, or forward custom CLI arguments.*

---

### [`adapters/lattice/synthesis.py`](adapters/lattice/synthesis.py)
> *Scientific literature synthesis engine: consensus scoring, thematic clustering, and BibTeX.*

**Size**: `319` lines (`13256` bytes)

**Classes:**
- `class SynthesisReport` - *Immutable structured synthesis for AI agents and human literature reviews.*
  - Method `.to_dict()` - *JSON-serializable representation.*

**Functions:**
- `def compute_consensus(supporting, contradicting, neutral)` - *Compute a confidence-weighted consensus score in [-1.0, 1.0] and classification label.*
- `def cluster_claims(claims)` - *Group claims into thematic clusters by dominant domain keyword.*
- `def format_bibtex(papers)` - *Format paper dictionaries as deterministic BibTeX entries.*
- `def synthesize(repository, target, tokens)` - *Produce a token-bounded, citation-checked scientific synthesis for a question or query.*
- `def _dominant_theme(text)` - *Select the most informative domain keyword from a claim sentence.*
- `def _inline_citation(paper)` - *Format `Author (Year) [p_xxx]` for inline evidence attribution.*
- `def _collect_bibliography(repository, claims, extra_papers)` - *Collect unique resolved paper records referenced by claims or search results.*
- `def _build_follow_up_queries(query_text, consensus, suggestions, bibliography)` - *Generate actionable follow-up scientific queries for AI agents.*
- `def _render_markdown(query_text, mode, consensus, clusters, gaps, follow_ups, bibliography, tokens)` - *Render a deterministic, token-bounded Markdown literature synthesis report.*

---

### [`adapters/lattice/ui_inventory.py`](adapters/lattice/ui_inventory.py)
> *Print Lattice's UI inventory, one entry per line.*

**Size**: `116` lines (`4543` bytes)

**Classes:**
- `class SurfaceParser` - *Collects identified elements, click handlers, roles and live regions of the studio.*
  - Method `.__init__()`
  - Method `.handle_starttag(tag, attrs)`

**Functions:**
- `def html_entries(html)` - *Identified elements, click handlers, roles and live regions of the studio page.*
- `def token_entries(html)` - *Theme custom properties the studio's embedded stylesheet declares.*
- `def route_entries(source)` - *The GET and POST routes the web dispatcher answers, parsed from its source.*
- `def _studio_html(root)` - *The exact HTML the studio serves, imported from the package rather than re-parsed.*
- `def inventory(root)` - *Every inventory entry of the studio surface, sorted and deduplicated.*
- `def main(argv)` - *Write the inventory to stdout; exit 1 when the surface has no entries at all.*

---

### [`domains/__init__.py`](domains/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`domains/atlas/__init__.py`](domains/atlas/__init__.py)
> *Atlas — interactive visual knowledge platform for learning material.*

**Size**: `4` lines (`158` bytes)

---

### [`domains/atlas/app.py`](domains/atlas/app.py)
> *Atlas standalone application entry point.*

**Size**: `984` lines (`51816` bytes)

**Classes:**
- `class Handler`
  - Method `.get_store()`
  - Method `.log_message(fmt, *args)`
  - Method `.do_GET()`
  - Method `._serve_file(path)`
  - Method `.do_POST()`

**Functions:**
- `def _json(handler, obj, status)`
- `def honest_error(exc)` - *Every failure is a message with the reason, never a silent nothing.*
- `def _parse_multipart(body, content_type)` - *Minimal single-file multipart/form-data parser (stdlib only).*
- `def _merge_frame_analyses(analyses, document_ref, figure_id)` - *Merge per-frame visual analyses, namespacing ids per frame (f0-, f1-...).*
- `def _entity_kwargs(d)`
- `def auto_create_model(store, config, source, note, figure_id, use_wonder, muse_provider, crop)` - *One drop → one model, from anything: image, PDF, book, text, link,*
- `def list_models(store)` - *Every model Atlas holds — the machine-visible model index.*
- `def describe_model(data)` - *One model as plain text an AI (or person) can read in a glance.*
- `def api_contract()` - *Versioned machine contract so AI agents can drive Atlas autonomously.*
- `def main(argv)`

---

### [`domains/atlas/cli.py`](domains/atlas/cli.py)
> *Atlas headless CLI — AI agents and scripts drive Atlas without a browser.*

**Size**: `312` lines (`12613` bytes)

**Functions:**
- `def cmd_create(args)`
- `def cmd_models(args)`
- `def cmd_show(args)`
- `def cmd_learn(args)`
- `def cmd_deck(args)`
- `def cmd_obj(args)`
- `def cmd_summary(args)`
- `def cmd_agent(args)` - *One command proving an AI can drive Atlas: fixture model, summary,*
- `def cmd_materials(args)`
- `def cmd_batch(args)`
- `def cmd_quality(args)`
- `def cmd_video(args)`
- `def main(argv)`

---

### [`domains/atlas/config.py`](domains/atlas/config.py)
> *Atlas configuration. Environment-based, no credentials in code or logs.*

**Size**: `83` lines (`3210` bytes)

**Classes:**
- `class AtlasConfig` - *Resolved entirely from environment + explicit overrides.*
  - Method `.from_env(**overrides)`
  - Property `.has_api_key`
  - Method `.redacted()` - *Safe for logs: never includes the key.*

**Functions:**
- `def _env(*names, default)`

---

### [`domains/atlas/demo/__init__.py`](domains/atlas/demo/__init__.py)
> *Atlas demo fixtures (source media stays external).*

**Size**: `1` lines (`57` bytes)

---

### [`domains/atlas/demo/basal_ganglia_demo.py`](domains/atlas/demo/basal_ganglia_demo.py)
> *End-to-end P0 demo: import -> figure -> Muse -> SAM -> overlay -> recall.*

**Size**: `105` lines (`5044` bytes)

**Functions:**
- `def run_fixture(data_dir)`
- `def run_live(image, note, data_dir, use_wonder)`
- `def main(argv)`

---

### [`domains/atlas/demo/basal_ganglia_fixture.py`](domains/atlas/demo/basal_ganglia_fixture.py)
> *Basal-ganglia direct/indirect pathway fixture (properly licensed schematic).*

**Size**: `81` lines (`5199` bytes)

---

### [`domains/atlas/doc_text.py`](domains/atlas/doc_text.py)
> *Atlas document-text extraction — fully in-project, no external dependency.*

**Size**: `204` lines (`7403` bytes)

**Functions:**
- `def _extract_text_from_pdf_reader(reader, log_callback)`
- `def extract_text_from_pdf(file_path, log_callback)`
- `def extract_text_from_pdf_bytes(data, log_callback)`
- `def pdf_page_count(file_path)`
- `def _extract_text_from_docx(file_path)`
- `def _extract_text_from_pptx(file_path)`
- `def _extract_text_from_txt(file_path)`
- `def _extract_text_from_transcript(file_path)` - *Lean VTT/SRT/JSON transcript reader (caption context for figures).*
- `def _transcript_json_to_text(data)`
- `def extract_text_from_document(file_path, log_callback)` - *Dispatch over PDF/DOCX/PPTX/TXT/VTT/SRT/JSON.*

---

### [`domains/atlas/flashcards.py`](domains/atlas/flashcards.py)
> *Flashcard decks from the validated model — recall distinct from quizzes.*

**Size**: `91` lines (`4022` bytes)

**Functions:**
- `def build_deck(analysis, dedupe)` - *Analysis → {"cards": [...], "deduped": n}. Deterministic order.*
- `def _cell(text)`
- `def to_anki_tsv(deck)` - *Deck → Anki-importable TSV: front, back (+ detail + evidence).*

---

### [`domains/atlas/ingestion.py`](domains/atlas/ingestion.py)
> *Atlas document + figure ingestion.*

**Size**: `123` lines (`4889` bytes)

**Classes:**
- `class FigureCrop`
  - Method `.to_dict()`

**Functions:**
- `def _sha256_file(path)`
- `def _check_ext(path)`
- `def import_document(source_path, data_dir, source_page)` - *Copy the original into Atlas storage and record provenance (never mutates source).*
- `def _validate_crop(crop)`
- `def select_figure(image_path, crop_rel, data_dir, document_ref, source_page)` - *Manual figure selection: crop an image region, preserve original + coordinates.*
- `def detect_figures(_image_path)` - *P1 hook: automatic figure detection. MVP raises explicitly instead of guessing.*

---

### [`domains/atlas/learning.py`](domains/atlas/learning.py)
> *Visual learning interactions — spatial recall distinct from flashcards.*

**Size**: `122` lines (`5179` bytes)

**Functions:**
- `def _entities(analysis)`
- `def _relationships(analysis)`
- `def spatial_recall_challenge(analysis, seed)` - *Hide labels; ask the user to identify a highlighted structure.*
- `def pathway_tracing_challenge(analysis, seed)` - *Order a connected chain of entities; user traces the pathway.*
- `def visual_identification_challenge(analysis, seed)`
- `def relationship_recall_challenge(analysis, seed)`
- `def grade(challenge, user_answer)`

---

### [`domains/atlas/materials.py`](domains/atlas/materials.py)
> *Study-material generators: every format from the same validated model.*

**Size**: `637` lines (`29732` bytes)

**Functions:**
- `def _names(analysis)`
- `def _font(size)` - *Turkish-capable truetype font: Pillow's bundled fonts miss Latin*
- `def _wrap(draw, text, font, max_width)` - *Greedy word-wrap to a pixel width (Pillow has no textbox).*
- `def _layout(analysis)` - *Entity id → canvas rect (uses the figure box, else a grid fallback).*
- `def _fit_frame(rects)` - *Vertically center poster content in the usable frame.*
- `def _overlaps(a, b)`
- `def _clamp_box(x, y, w, h)`
- `def _declutter(rects, max_passes)` - *Spread overlapping poster boxes apart (the poster is a derivation;*
- `def diagram_svg(analysis)` - *Study diagram as SVG: labeled boxes + directional arrows.*
- `def diagram_png(analysis)` - *Same schematic rasterized with Pillow (text may wrap, never invented).*
- `def tour_3d(analysis)` - *Ordered stops through the 3D stack, bottom layer first.*
- `def _spoken_relation(r, names)` - *Audible relationship: type + target + the model's own explanation.*
- `def _spoken_out(r, names)` - *Entity-segment form: relation + target + explanation (no repeated source).*
- `def _spoken_in(r, names)` - *Incoming-relation form: rel_type + this entity + explanation.*
- `def podcast_script(analysis, max_segments)` - *Two-host conversational walkthrough, TTS-ready segments + duration.*
- `def _mmss(total_seconds)`
- `def podcast_markdown(script)`
- `def _ffmpeg_exe()`
- `def video_slideshow(analysis, outdir, fps, seconds_per_scene)` - *Model → narrated-caption MP4 study video (title, entity spotlights, outro).*
- `def question_bank(analysis)` - *Every generatable question with its answer + evidence (worksheet source).*
- `def questions_markdown(bank)`

---

### [`domains/atlas/models3d.py`](domains/atlas/models3d.py)
> *3D from 2D knowledge: isometric view + printable OBJ export (stdlib only).*

**Size**: `104` lines (`4651` bytes)

**Functions:**
- `def iso_project(x, y, z)` - *Isometric 2D projection of a 3D point (all inputs in model units).*
- `def layer_of(category)`
- `def iso_view(analysis, depth)` - *Entities with boxes → isometric polygons for the 2.5D canvas view.*
- `def _cuboid(center, size)`
- `def export_obj(analysis, depth)` - *Validated analysis → Wavefront OBJ text (cuboid per located entity).*

---

### [`domains/atlas/muse_provider.py`](domains/atlas/muse_provider.py)
> *Meta Muse provider (Spark default, Wonder for complex reasoning).*

**Size**: `221` lines (`10957` bytes)

**Classes:**
- `class MuseProvider` - *Replaceable Meta API adapter with timeouts, retries, safe errors.*
  - Method `.__init__(config, transport, use_wonder)`
  - Property `.model`
  - Method `._http_post(payload)`
  - Method `.analyze_text(text, note, document_ref, figure_id)` - *Text source (book, article, transcript, PDF) → knowledge, no boxes.*
  - Method `.analyze_long_text(text, note, document_ref, figure_id)` - *Whole books, not just the first 12k chars: chunk, analyze, merge.*
  - Method `.polish_summary(brief)` - *Rewrite an extractive brief as flowing prose (needs key).*
  - Method `._extract_content(response)`
  - Method `.analyze_figure(image_path, note, document_ref, source_page, figure_id)`
  - Method `.disclosure()`

**Functions:**
- `def build_request(image_b64, mime, note, model)`

---

### [`domains/atlas/offline.py`](domains/atlas/offline.py)
> *Offline extractive fallback: real learning models with no API key.*

**Size**: `134` lines (`5735` bytes)

**Functions:**
- `def _sentences(text)`
- `def _slug(term)`
- `def _filename_terms(path)`
- `def build_offline_analysis(text, document_ref, figure_id, source_kind, max_entities)` - *Keyphrase-frequency text → validated VisualAnalysis (no network, no key).*
- `def offline_text_for_source(bundle, note)` - *Context text for image/video sources: note + filename terms.*

---

### [`domains/atlas/quality.py`](domains/atlas/quality.py)
> *Automatic quality analysis for every generated artifact (0-100 each).*

**Size**: `605` lines (`30469` bytes)

**Functions:**
- `def _result(score, checks, issues)`
- `def _check(name, ok, detail)`
- `def flashcard_quality(deck, analysis)` - *Coverage, clarity, grounding, and duplication of a flashcard deck.*
- `def infographic_quality(svg, analysis)` - *The study diagram: labels, overlap, legibility, arrow validity.*
- `def podcast_quality(script, analysis)` - *Coverage, duration sanity, structure, and density of the audio script.*
- `def model3d_quality(obj_text, analysis)` - *OBJ validity: groups, vertex/face math, bounds, naming, NaNs.*
- `def video_quality_mp4(path)` - *Technical quality of a rendered study MP4 (container, size, duration).*
- `def _luminance(path)`
- `def ahash(path)` - *Perceptual hash: identical/near-identical frames share a hash.*
- `def _hamming(a, b)`
- `def frame_sharpness(path)` - *Laplacian variance: motion blur and flat cards score near zero.*
- `def frames_quality(paths, blank_ceiling, low_detail_warn, dup_bits)` - *Score extracted video frames; pick the ones worth analyzing.*
- `def _mp4_duration(path)`
- `def tour_quality(tour, analysis)` - *Ordered 3D-layer walkthrough: every stop names a known entity.*
- `def questions_quality(bank, analysis)` - *Question bank: every entity and relationship gets asked, with answers.*
- `def summary_quality(brief, analysis)` - *Extractive study brief: counts match the model, pathways traced.*
- `def learn_quality(analysis)` - *All four learn modes build and grade correctly on this model.*
- `def quality_report(analysis, artifacts)` - *Score the requested artifacts; overall = mean of what was assessed.*

---

### [`domains/atlas/sam_provider.py`](domains/atlas/sam_provider.py)
> *SAM 3.1 segmentation integration.*

**Size**: `145` lines (`6583` bytes)

**Classes:**
- `class Segmentation`
- `class SamProvider`
  - Method `.__init__(config, transport)`
  - Method `._http_post(payload)`
  - Method `.segment(image_path, prompt, entity_id, fallback_box)` - *Segment one entity. Short noun phrase required (e.g. 'striatum').*
  - Method `.disclosure()`

**Functions:**
- `def _scan_box(raw)` - *Best-effort: first [x1,y1,x2,y2] int quad inside the 0..1000 grid.*
- `def _scan_file_id(raw)`

---

### [`domains/atlas/schema.py`](domains/atlas/schema.py)
> *Versioned structured scientific visual-knowledge schema.*

**Size**: `376` lines (`16166` bytes)

**Classes:**
- `class BoundingBox` - *Normalized box: (0,0) top-left, (1,1) bottom-right.*
  - Method `.__post_init__()`
  - Method `.to_grid1000()` - *Meta perception-grounding grid (0..1000). Docs: divide by 10 for CSS %.*
  - Method `.from_grid1000(box)`
- `class VisualEntity`
  - Method `.__post_init__()`
  - Method `.to_dict()`
- `class VisualRelationship`
  - Method `.__post_init__()`
  - Method `.to_dict()`
- `class VisualAnalysis` - *One analyzed figure crop. Entities + relationships share IDs by construction.*
  - Method `.validate()`
  - Method `.to_dict()`
  - Method `.from_dict(raw)`

**Functions:**
- `def _check_norm(value, name)`
- `def _req(mapping, key, ctx)` - *Required key with context — malformed payloads raise ValueError, never KeyError.*
- `def _checked_confidence(value, ctx)` - *Confidence must be a real number in [0,1] — bool/str rejected like bad boxes.*
- `def _norm_name(name)`
- `def merge_analyses(analyses, document_ref, figure_id)` - *Merge chunk analyses: entities by normalized name, rels remapped + deduped.*
- `def muse_json_schema()` - *JSON Schema sent as response_format.json_schema so Muse output parses first try.*
- `def coerce_muse_payload(payload, document_ref, source_page, figure_id)` - *Validate raw Muse JSON (0..1000 boxes) into a versioned VisualAnalysis.*

---

### [`domains/atlas/selftest.py`](domains/atlas/selftest.py)
> *Atlas offline self-test: one command proves the app works, no key, no browser.*

**Size**: `157` lines (`6649` bytes)

**Classes:**
- `class _FakeMuse`
  - Method `.analyze_figure(image_path, note, document_ref, source_page, figure_id)`
  - Method `.analyze_text(text, note, document_ref, figure_id)`

**Functions:**
- `def run(data_dir)`
- `def main(argv)`

---

### [`domains/atlas/sources.py`](domains/atlas/sources.py)
> *Universal source ingestion: link, YouTube, book (EPUB), video, and files.*

**Size**: `307` lines (`12919` bytes)

**Classes:**
- `class _TextExtractor` - *Collect readable text; drop scripts, styles, nav boilerplate.*
  - Method `.__init__()`
  - Method `.handle_starttag(tag, attrs)`
  - Method `.handle_endtag(tag)`
  - Method `.handle_data(data)`
  - Method `.text()`

**Functions:**
- `def html_to_text(markup)`
- `def fetch_url_text(url, timeout)` - *Fetch a web article into {title, text, url}. Textual content only.*
- `def youtube_video_id(url)`
- `def is_youtube_url(url)`
- `def youtube_transcript(url, timeout)` - *Public captions of a YouTube video via its player response (no API key).*
- `def epub_text(path)` - *EPUB book → {title, text, chapters} in spine order (XHTML chapters).*
- `def _ffmpeg_exe()` - *System ffmpeg, else the bundled imageio-ffmpeg binary (pip installable).*
- `def render_pdf_page(path, page, outdir, dpi)` - *PDF page → PNG still (needs optional PyMuPDF: pip install PyMuPDF).*
- `def video_frames(path, outdir, max_frames)` - *Video → up to max_frames stills (system or bundled imageio-ffmpeg).*
- `def chunk_text(text, limit)` - *Split long text into ≤limit chunks at paragraph boundaries (books).*
- `def trim_text(text, limit)`
- `def ingest_any(source)` - *Any supported source → normalized bundle with FULL text for the pipeline.*

---

### [`domains/atlas/store.py`](domains/atlas/store.py)
> *Atomic JSON persistence for Atlas-only data.*

**Size**: `107` lines (`3975` bytes)

**Classes:**
- `class AtlasStore`
  - Method `.__init__(data_dir)`
  - Method `.analysis_path(figure_id)`
  - Method `.save_analysis(figure_id, analysis)`
  - Method `.load_analysis(figure_id)`
  - Method `.corrections_path()`
  - Method `.add_correction(entry)`
  - Method `.load_corrections()`
  - Method `.cache_path()`
  - Method `.cache_key(*parts)`
  - Method `.cache_get(key)`
  - Method `.cache_put(key, value)`

**Functions:**
- `def _atomic_write_json(path, obj)`
- `def _read_json(path, default, tolerant)`

---

### [`domains/atlas/summaries.py`](domains/atlas/summaries.py)
> *Auto study material: summaries generated from the validated model.*

**Size**: `90` lines (`4043` bytes)

**Functions:**
- `def _names(analysis)`
- `def pathway_chains(analysis, max_depth)` - *Maximal directional chains (no revisits) over the relationship graph.*
- `def extractive_summary(analysis)` - *Deterministic study brief: overview, entities, pathways, stats.*

---

### [`domains/atlas/text_backend.py`](domains/atlas/text_backend.py)
> *Atlas document-text backend — fully in-project, no external project needed.*

**Size**: `49` lines (`1689` bytes)

**Classes:**
- `class DocumentText`

**Functions:**
- `def extract_text(source_path, log_callback)` - *Extract text with the in-project backend.*
- `def describe_integration()`
- `def read_image_bytes(image_path)`

---

### [`domains/fluid_universe/__init__.py`](domains/fluid_universe/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`domains/fluid_universe/claims.py`](domains/fluid_universe/claims.py)
> *Fluid-universe claim ledger and scorecard compatibility.*

**Size**: `152` lines (`4739` bytes)

**Classes:**
- `class ClaimRecord`
- `class ScorecardRow`

**Functions:**
- `def _cells(line)` - *Split a Markdown table row on unescaped pipes.*
- `def _clean(value)`
- `def split_status(value)` - *Return the base status and the parenthesised qualifier, if any.*
- `def _is_separator(cells)`
- `def parse_claim_table(text)` - *Parse the six-column claim ledger table.*
- `def parse_scorecard(text)` - *Parse the three-column one-line scorecard table.*
- `def compare_ledger_and_scorecard(claims, rows)` - *Report claims whose ledger and scorecard statuses disagree or are missing.*
- `def load_claims(root)` - *Read the external claims.md; the file is referenced, never copied.*
- `def load_scorecard(root)` - *Read the external SCORECARD.md.*

---

### [`domains/fluid_universe/phenomenology/__init__.py`](domains/fluid_universe/phenomenology/__init__.py)
> *Phenomenology: PDG input, circulant fit, and one-loop SM running.*

**Size**: `1` lines (`72` bytes)

---

### [`domains/fluid_universe/phenomenology/coherent_fluid_report.py`](domains/fluid_universe/phenomenology/coherent_fluid_report.py)
> *Moving-center Gaussian reduction report (claim 23, ADR-014).*

**Size**: `157` lines (`5285` bytes)

**Functions:**
- `def _energy_drift(result)`
- `def _zero_crossings(times, values)`
- `def run_coherent_fluid_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/convergence_report.py`](domains/fluid_universe/phenomenology/convergence_report.py)
> *Resolution report for claim 15: N=64 versus N=96 at the same physical time.*

**Size**: `166` lines (`5701` bytes)

**Functions:**
- `def _run(n, deadline)`
- `def run_convergence_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/delta_search.py`](domains/fluid_universe/phenomenology/delta_search.py)
> *Search for a closed form of the circulant phase delta, with a stated prior.*

**Size**: `185` lines (`6508` bytes)

**Functions:**
- `def rational_candidates()`
- `def pi_candidates()`
- `def simple_candidates()`
- `def all_candidates()`
- `def search(delta, sigma)`
- `def run_delta_search(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/excited_fluid_report.py`](domains/fluid_universe/phenomenology/excited_fluid_report.py)
> *First-excited-state node report (claim 24, ADR-015).*

**Size**: `146` lines (`4817` bytes)

**Functions:**
- `def run_excited_fluid_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/extension_report.py`](domains/fluid_universe/phenomenology/extension_report.py)
> *Checkpointed N=96 extension for claim 15 (ADR-004).*

**Size**: `223` lines (`7448` bytes)

**Functions:**
- `def _checkpoint(chunk)`
- `def _write_npy_atomic(path, array)`
- `def _load_state()`
- `def _save_state(state)`
- `def run_next_chunk(write)`
- `def render_markdown(state)`
- `def _format_projection(steps, time_value)`
- `def main(argv)`

---

### [`domains/fluid_universe/phenomenology/field_variation_report.py`](domains/fluid_universe/phenomenology/field_variation_report.py)
> *Unstructured 1D fixed-endpoint-density G-M field variation (claim 58, ADR-050).*

**Size**: `390` lines (`14276` bytes)

**Functions:**
- `def _analytic_bridge_rho(problem)`
- `def _field_action_on_rho(problem, rho)`
- `def run_field_variation_check(write)`
- `def _classical_transport_action(s0, sT, horizon_T, omega, mass)` - *Closed-form nu = 0 Gaussian transport action.*
- `def _verdict_note(status)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/fit.py`](domains/fluid_universe/phenomenology/fit.py)
> *PDG pole-mass fit of the Hermitian circulant parametrisation.*

**Size**: `228` lines (`8114` bytes)

**Classes:**
- `class PoleMass`

**Functions:**
- `def load_pole_masses(path)`
- `def _summary(values)`
- `def _circular_mean(angles)`
- `def fit_point(masses_MeV)`
- `def run_fit(n_mc, seed, write)`
- `def render_markdown(payload)`
- `def main()`

---

### [`domains/fluid_universe/phenomenology/gaussian_bridge_report.py`](domains/fluid_universe/phenomenology/gaussian_bridge_report.py)
> *Fixed-endpoint Gaussian bridge check (claim 54, ADR-046).*

**Size**: `175` lines (`6494` bytes)

**Functions:**
- `def run_gaussian_bridge_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/gaussian_fluid_report.py`](domains/fluid_universe/phenomenology/gaussian_fluid_report.py)
> *Gaussian Madelung reduction report (claim 22, ADR-013).*

**Size**: `155` lines (`5316` bytes)

**Functions:**
- `def _period(result, width)`
- `def run_gaussian_fluid_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hopf_report.py`](domains/fluid_universe/phenomenology/hopf_report.py)
> *Hopf estimator validation result payload.*

**Size**: `66` lines (`2443` bytes)

**Functions:**
- `def run_hopf_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hopf_resolution_report.py`](domains/fluid_universe/phenomenology/hopf_resolution_report.py)
> *Hopf estimator resolution report.*

**Size**: `47` lines (`1532` bytes)

**Functions:**
- `def run_hopf_resolution_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hopfion3d_n64_report.py`](domains/fluid_universe/phenomenology/hopfion3d_n64_report.py)
> *Targeted N=64 diagnostic for the 3D E2+E4+Z3 pilot.*

**Size**: `104` lines (`3772` bytes)

**Functions:**
- `def run_n64_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hopfion3d_report.py`](domains/fluid_universe/phenomenology/hopfion3d_report.py)
> *3D pilot report for the E2+E4+Z3 model.*

**Size**: `83` lines (`3122` bytes)

**Functions:**
- `def run_hopfion3d_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hopfion_report.py`](domains/fluid_universe/phenomenology/hopfion_report.py)
> *Static finite-energy H=1 configuration report.*

**Size**: `61` lines (`2238` bytes)

**Functions:**
- `def run_hopfion_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hopfion_scale_report.py`](domains/fluid_universe/phenomenology/hopfion_scale_report.py)
> *Report for the damped scale-iteration candidate.*

**Size**: `71` lines (`2465` bytes)

**Functions:**
- `def run_scale_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hydrogen_fluid_report.py`](domains/fluid_universe/phenomenology/hydrogen_fluid_report.py)
> *Hydrogen 1s Madelung reduction report (claim 25, ADR-016).*

**Size**: `128` lines (`4527` bytes)

**Functions:**
- `def run_hydrogen_fluid_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/hydrogen_vortex_report.py`](domains/fluid_universe/phenomenology/hydrogen_vortex_report.py)
> *Hydrogen 2p vortex identification report (claim 26, ADR-017).*

**Size**: `123` lines (`4328` bytes)

**Functions:**
- `def run_hydrogen_vortex_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/length_scan_report.py`](domains/fluid_universe/phenomenology/length_scan_report.py)
> *Box-length scan of the pure-FN N=64 candidate (ADR-007, claim 14b).*

**Size**: `183` lines (`6492` bytes)

**Functions:**
- `def run_length_scan(write)`
- `def render_markdown(result)`

---

### [`domains/fluid_universe/phenomenology/lv_bounds.py`](domains/fluid_universe/phenomenology/lv_bounds.py)
> *Residual anisotropy and Lorentz-violation bounds (claims 11-12).*

**Size**: `105` lines (`3935` bytes)

**Functions:**
- `def run_lorentz_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/madelung_report.py`](domains/fluid_universe/phenomenology/madelung_report.py)
> *Madelung fluid dictionary report (claim 20, ADR-011).*

**Size**: `160` lines (`5092` bytes)

**Functions:**
- `def _grid()`
- `def run_madelung_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/nelson_closure_report.py`](domains/fluid_universe/phenomenology/nelson_closure_report.py)
> *Osmotic-closure no-go check (claim 48, ADR-040).*

**Size**: `155` lines (`5703` bytes)

**Functions:**
- `def run_nelson_closure_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/nelson_report.py`](domains/fluid_universe/phenomenology/nelson_report.py)
> *Nelson stochastic kinematics report (claim 21, ADR-012).*

**Size**: `136` lines (`4437` bytes)

**Functions:**
- `def run_nelson_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/neutrinos.py`](domains/fluid_universe/phenomenology/neutrinos.py)
> *Neutrino Koide ratio scan.*

**Size**: `242` lines (`8674` bytes)

**Classes:**
- `class NuFitParameters`

**Functions:**
- `def load_parameters(path)`
- `def masses_normal(m_light, dm21_sq, dm31_sq_no)` - *Return (m1, m2, m3) for normal ordering, m_light = m1.*
- `def masses_inverted(m_light, dm21_sq, dm31_sq_io)` - *Return (m1, m2, m3) for inverted ordering, m_light = m3.*
- `def q_nu(masses)`
- `def scan_ordering(ordering, params, m_light_max, points)`
- `def corner_max(ordering, params)` - *Maximum Q at m_light = 0 over the 3-sigma corners of the splittings.*
- `def run_neutrino_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/node_defect_report.py`](domains/fluid_universe/phenomenology/node_defect_report.py)
> *Two-branch defect representation check (claim 46, ADR-038).*

**Size**: `146` lines (`5271` bytes)

**Functions:**
- `def run_node_defect_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/pmns.py`](domains/fluid_universe/phenomenology/pmns.py)
> *What a minimal circulant lepton sector predicts for PMNS mixing.*

**Size**: `143` lines (`5592` bytes)

**Functions:**
- `def dft_matrix()`
- `def angles_from_pmns(U)` - *Standard three-neutrino angles in degrees from |U|.*
- `def run_pmns_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/predictions.py`](domains/fluid_universe/phenomenology/predictions.py)
> *Search for a genuinely new prediction beyond Q=2/3 (claim 16).*

**Size**: `112` lines (`3965` bytes)

**Functions:**
- `def run_prediction_audit(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/production_report.py`](domains/fluid_universe/phenomenology/production_report.py)
> *Production claim-15 report: resolved Hopf charge and Z3 order.*

**Size**: `218` lines (`7926` bytes)

**Functions:**
- `def run_production_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/provenance.py`](domains/fluid_universe/phenomenology/provenance.py)
> *Small reproducibility helpers: git state, versions, config hashes.*

**Size**: `80` lines (`2510` bytes)

**Functions:**
- `def git_state()`
- `def package_versions()`
- `def config_hash(payload)`
- `def metadata(config)`
- `def write_text_atomic(path, text)` - *Write a generated file atomically (temp file + fsync + replace).*
- `def write_json(path, payload)`

---

### [`domains/fluid_universe/phenomenology/purefn_stability_report.py`](domains/fluid_universe/phenomenology/purefn_stability_report.py)
> *Pure-Faddeev-Niemi N=64 candidate Hessian (ADR-005, claims 14b/14d).*

**Size**: `156` lines (`5298` bytes)

**Functions:**
- `def run_purefn_check(write)`
- `def render_markdown(result)`

---

### [`domains/fluid_universe/phenomenology/quarks.py`](domains/fluid_universe/phenomenology/quarks.py)
> *Quark Koide ratios from the full-SM MS-bar masses of Huang & Zhou (2021).*

**Size**: `154` lines (`5316` bytes)

**Classes:**
- `class QuarkRow`

**Functions:**
- `def load_rows(path)`
- `def q_up(row)`
- `def q_down(row)`
- `def run_quark_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/radial_node_report.py`](domains/fluid_universe/phenomenology/radial_node_report.py)
> *Hydrogen-2s radial-node representation check (claim 47, ADR-039).*

**Size**: `167` lines (`5902` bytes)

**Functions:**
- `def run_radial_node_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/rg.py`](domains/fluid_universe/phenomenology/rg.py)
> *One-loop Standard-Model running of charged-lepton Yukawa couplings.*

**Size**: `495` lines (`17586` bytes)

**Classes:**
- `class InitialState`
  - Method `.vector()`

**Functions:**
- `def yukawa_from_mass(mass_GeV, v_GeV)`
- `def initial_state(masses_GeV, m_top_GeV, m_bottom_GeV)`
- `def _split(state)` - *Return y_e, y_mu, y_tau, y_t, y_b, g1, g2, g3 from log-state.*
- `def rhs(_t, state)` - *One-loop SM RHS for log(yukawas) and log(gauge couplings).*
- `def _rhs_ratio_only(_t, state)` - *RHS with only the generation-dependent (3/2) y_k^2 term.*
- `def run_system(initial, scale_max, rtol, atol)`
- `def run_ratio_only(initial, scale_max)`
- `def observables_from_yukawas(y)` - *Q, r, delta and masses from the three positive Yukawa eigenvalues.*
- `def convert_pole_to_msbar_explicit(m_pole_GeV, mu_GeV, alpha_mu)` - *Published one-pass QED conversion used by Xing & Zhang (2006).*
- `def convert_pole_to_msbar(m_pole_GeV, mu_GeV, alpha_mu)` - *Self-consistent one-loop QED pole-to-MSbar conversion by fixed point.*
- `def _literature_check(sol)`
- `def run_rg(write)`
- `def render_markdown(payload)`
- `def main()`

---

### [`domains/fluid_universe/phenomenology/rotor_potential_report.py`](domains/fluid_universe/phenomenology/rotor_potential_report.py)
> *Real Z3 rotor potential scan report (claim 19, ADR-010).*

**Size**: `77` lines (`2539` bytes)

**Functions:**
- `def run_rotor_potential_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/run_all.py`](domains/fluid_universe/phenomenology/run_all.py)
> *Regenerate every result file from scratch.*

**Size**: `555` lines (`26574` bytes)

**Functions:**
- `def rotor_payload()`
- `def render_rotor_markdown(payload)`
- `def extra_summary(delta, fo, derrick)`
- `def negatives_summary(topology, reduction, predictions)`
- `def lorentz_summary(lorentz)`
- `def sim_summary(sim)`
- `def hopf_summary(hopf)`
- `def hopfion_summary(payload)`
- `def hopfion3d_summary(payload)`
- `def hopf_resolution_summary(payload)`
- `def build_summary(fit, rg, rotor, neutrino, quarks, pmns)`
- `def main()`

---

### [`domains/fluid_universe/phenomenology/saddle_escape_report.py`](domains/fluid_universe/phenomenology/saddle_escape_report.py)
> *Saddle-escape search from the pure-FN N=64 candidate (ADR-006, claim 14b).*

**Size**: `205` lines (`7102` bytes)

**Functions:**
- `def _relax(field, steps, deadline)`
- `def run_escape_check(write)`
- `def render_markdown(result)`

---

### [`domains/fluid_universe/phenomenology/sim_report.py`](domains/fluid_universe/phenomenology/sim_report.py)
> *Result payload for the 1D simulation baseline.*

**Size**: `162` lines (`6309` bytes)

**Functions:**
- `def run_1d_baseline(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/stability_report.py`](domains/fluid_universe/phenomenology/stability_report.py)
> *Report for the validated tangent-space Hessian of the scale candidate.*

**Size**: `87` lines (`3381` bytes)

**Functions:**
- `def run_stability_report(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/temporal_report.py`](domains/fluid_universe/phenomenology/temporal_report.py)
> *Temporal-check report for claim 15: N=64 at two timesteps, same physical time.*

**Size**: `159` lines (`5395` bytes)

**Functions:**
- `def _run(steps, dt, deadline)`
- `def run_temporal_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/two_state_report.py`](domains/fluid_universe/phenomenology/two_state_report.py)
> *Shared-lambda two-state Marcus assignment (claim 44, ADR-036).*

**Size**: `164` lines (`6592` bytes)

**Functions:**
- `def run_two_state_comparison(temperature_k, write)` - *Compare the shared-lambda equal-width prediction vs the observed ratio.*
- `def run_two_state_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/uv_checks.py`](domains/fluid_universe/phenomenology/uv_checks.py)
> *Reproducible UV-track checks: Frank-Oseen modes and Derrick scaling.*

**Size**: `187` lines (`7274` bytes)

**Functions:**
- `def run_frank_oseen_check(write)`
- `def render_frank_oseen(payload)`
- `def run_derrick_check(write)`
- `def render_derrick(payload)`

---

### [`domains/fluid_universe/phenomenology/uv_negatives.py`](domains/fluid_universe/phenomenology/uv_negatives.py)
> *Result payloads for the topology, reduction, and prediction negatives.*

**Size**: `63` lines (`2247` bytes)

**Functions:**
- `def run_topology_check(write)`
- `def run_reduction_check(write)`

---

### [`domains/fluid_universe/phenomenology/variational_center_report.py`](domains/fluid_universe/phenomenology/variational_center_report.py)
> *Co-emergence of Newtonian center and Ermakov width (claim 53, ADR-045).*

**Size**: `161` lines (`5879` bytes)

**Functions:**
- `def run_variational_center_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/variational_dynamics_report.py`](domains/fluid_universe/phenomenology/variational_dynamics_report.py)
> *Variational dynamics reproduces Ermakov (claim 51, ADR-043).*

**Size**: `145` lines (`5285` bytes)

**Functions:**
- `def run_variational_dynamics_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/variational_saddle_report.py`](domains/fluid_universe/phenomenology/variational_saddle_report.py)
> *2D Ritz saddle check (claim 50, ADR-042).*

**Size**: `157` lines (`5759` bytes)

**Functions:**
- `def run_variational_saddle_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/variational_width_report.py`](domains/fluid_universe/phenomenology/variational_width_report.py)
> *Gaussian Ritz width-selection check (claim 49, ADR-041).*

**Size**: `147` lines (`5391` bytes)

**Functions:**
- `def run_variational_width_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/vortex_cascade_report.py`](domains/fluid_universe/phenomenology/vortex_cascade_report.py)
> *One-parameter vortex hierarchy report (claim 18, ADR-009).*

**Size**: `88` lines (`3193` bytes)

**Functions:**
- `def load_lepton_masses()`
- `def run_cascade_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/vortex_core_report.py`](domains/fluid_universe/phenomenology/vortex_core_report.py)
> *HO-1 finite-core node probe (claim 60, ADR-054).*

**Size**: `172` lines (`6034` bytes)

**Functions:**
- `def run_vortex_core_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/vortex_loop_report.py`](domains/fluid_universe/phenomenology/vortex_loop_report.py)
> *2p core-threading loop probe (claim 61, ADR-056).*

**Size**: `154` lines (`5722` bytes)

**Functions:**
- `def run_vortex_loop_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/vortex_spectrum_report.py`](domains/fluid_universe/phenomenology/vortex_spectrum_report.py)
> *Vortex-knot mass spectrum report (claim 17, ADR-008).*

**Size**: `110` lines (`3813` bytes)

**Functions:**
- `def load_lepton_masses()`
- `def run_vortex_spectrum(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_absorption_report.py`](domains/fluid_universe/phenomenology/water_absorption_report.py)
> *Bound-free absorption in the finite spherical well (claim 34, ADR-025).*

**Size**: `138` lines (`5781` bytes)

**Functions:**
- `def run_water_absorption_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_analogue_report.py`](domains/fluid_universe/phenomenology/water_analogue_report.py)
> *Shallow-water acoustic horizon report (claim 27, ADR-018).*

**Size**: `109` lines (`3772` bytes)

**Functions:**
- `def run_water_analogue_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_born_cavity_report.py`](domains/fluid_universe/phenomenology/water_born_cavity_report.py)
> *Self-consistent Born cavity synthesis (claim 39, ADR-030).*

**Size**: `141` lines (`6015` bytes)

**Functions:**
- `def run_water_born_cavity_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_dispersive_report.py`](domains/fluid_universe/phenomenology/water_dispersive_report.py)
> *Dispersive shallow-water horizon report (claim 29, ADR-020).*

**Size**: `108` lines (`3620` bytes)

**Functions:**
- `def run_water_dispersive_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_electron_report.py`](domains/fluid_universe/phenomenology/water_electron_report.py)
> *Hydrated-electron cavity scale report (claim 32, ADR-023).*

**Size**: `103` lines (`4059` bytes)

**Functions:**
- `def run_water_electron_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_lineshape_report.py`](domains/fluid_universe/phenomenology/water_lineshape_report.py)
> *Fixed-lambda cavity-Marcus line-shape prediction (claim 43, ADR-034).*

**Size**: `260` lines (`11288` bytes)

**Functions:**
- `def run_water_lineshape_comparison(write)` - *Compare the fixed-lambda prediction against citable observed shape.*
- `def run_water_lineshape_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_marcus_report.py`](domains/fluid_universe/phenomenology/water_marcus_report.py)
> *Marcus band width from the water reorganization energy (claim 40, ADR-031).*

**Size**: `123` lines (`4808` bytes)

**Functions:**
- `def run_water_marcus_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_pressure_report.py`](domains/fluid_universe/phenomenology/water_pressure_report.py)
> *Self-consistent finite-well pressure balance (claim 37, ADR-028).*

**Size**: `139` lines (`5705` bytes)

**Functions:**
- `def run_water_pressure_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_rays_report.py`](domains/fluid_universe/phenomenology/water_rays_report.py)
> *Radial ray report at the shallow-water horizon (claim 30, ADR-021).*

**Size**: `159` lines (`5190` bytes)

**Functions:**
- `def run_water_rays_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_reorganization_report.py`](domains/fluid_universe/phenomenology/water_reorganization_report.py)
> *Water reorganization and the VDE-optical difference (claim 38, ADR-029).*

**Size**: `140` lines (`5833` bytes)

**Functions:**
- `def run_water_reorganization_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_scattering_report.py`](domains/fluid_universe/phenomenology/water_scattering_report.py)
> *1D water-wave scattering report (claim 31, ADR-022).*

**Size**: `116` lines (`3724` bytes)

**Functions:**
- `def run_water_scattering_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_softwall_report.py`](domains/fluid_universe/phenomenology/water_softwall_report.py)
> *Soft-wall cavity and the hard VDE depth bound (claim 36, ADR-027).*

**Size**: `155` lines (`6536` bytes)

**Functions:**
- `def run_water_softwall_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_temperature_report.py`](domains/fluid_universe/phenomenology/water_temperature_report.py)
> *Temperature-dependent Born cavity (claim 41, ADR-032).*

**Size**: `186` lines (`8220` bytes)

**Functions:**
- `def run_water_temperature_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_twocomponent_report.py`](domains/fluid_universe/phenomenology/water_twocomponent_report.py)
> *Two-component band-model comparison (claim 45, ADR-037).*

**Size**: `116` lines (`4205` bytes)

**Functions:**
- `def run_water_twocomponent_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_validity_report.py`](domains/fluid_universe/phenomenology/water_validity_report.py)
> *Capillary validity report for the shallow-water horizon (claim 28, ADR-019).*

**Size**: `116` lines (`4337` bytes)

**Functions:**
- `def _row(flow_rate)`
- `def run_water_validity_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_vde_report.py`](domains/fluid_universe/phenomenology/water_vde_report.py)
> *VDE and 1.7 eV absorption constrain the finite well (claim 35, ADR-026).*

**Size**: `150` lines (`6409` bytes)

**Functions:**
- `def run_water_vde_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/water_well_report.py`](domains/fluid_universe/phenomenology/water_well_report.py)
> *Finite spherical well for the hydrated electron (claim 33, ADR-024).*

**Size**: `169` lines (`7087` bytes)

**Functions:**
- `def run_water_well_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/widened_ritz_report.py`](domains/fluid_universe/phenomenology/widened_ritz_report.py)
> *Ritz-widened squared-Hermite trial BVP (claim 59, ADR-051).*

**Size**: `360` lines (`12658` bytes)

**Functions:**
- `def _analytic_bridge_J(problem)`
- `def run_widened_ritz_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/yasue_action_report.py`](domains/fluid_universe/phenomenology/yasue_action_report.py)
> *Pinned-endpoint Yasue-bridge action stationarity (claim 57, ADR-049).*

**Size**: `298` lines (`11042` bytes)

**Functions:**
- `def run_yasue_action_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/yasue_bridge_report.py`](domains/fluid_universe/phenomenology/yasue_bridge_report.py)
> *Pinned-endpoint Yasue bridge: the c<0 Pinney analytic family (claim 56, ADR-048).*

**Size**: `322` lines (`11716` bytes)

**Functions:**
- `def _load_arc_profile()`
- `def run_yasue_bridge_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/yasue_center_report.py`](domains/fluid_universe/phenomenology/yasue_center_report.py)
> *Yasue center-width discriminator (claim 55, ADR-047).*

**Size**: `233` lines (`8580` bytes)

**Functions:**
- `def run_yasue_center_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/phenomenology/yasue_dynamics_report.py`](domains/fluid_universe/phenomenology/yasue_dynamics_report.py)
> *Yasui dynamical discriminator check (claim 52, ADR-044).*

**Size**: `167` lines (`6076` bytes)

**Functions:**
- `def run_yasue_dynamics_check(write)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/sims/__init__.py`](domains/fluid_universe/sims/__init__.py)
> *Simulation package: validated 1D core and bounded 3D diagnostics.*

**Size**: `1` lines (`72` bytes)

---

### [`domains/fluid_universe/sims/convergence.py`](domains/fluid_universe/sims/convergence.py)
> *Resolution comparison for the claim-15 production scan (ADR-002).*

**Size**: `218` lines (`8429` bytes)

**Functions:**
- `def _require_same_problem(low, high)`
- `def compare_scans(low, high)` - *Compare a coarse and a fine production payload at the same physical time.*
- `def compare_temporal(coarse, fine)` - *Compare two N=64 payloads at the same physical time but different dt.*
- `def summarize_trend(rows, z3_target, force_tol)` - *Summarise a multi-chunk trend and project the two claim-15 thresholds.*

---

### [`domains/fluid_universe/sims/core.py`](domains/fluid_universe/sims/core.py)
> *Validated 1D core for the Z3 sine-Gordon sector.*

**Size**: `210` lines (`6846` bytes)

**Functions:**
- `def grid(length, n)`
- `def potential(phi, mu)`
- `def potential_prime(phi, mu)`
- `def potential_second(phi, mu)`
- `def analytic_kink(x, mu, x0)`
- `def kink_tension(mu)`
- `def energy(phi, dx, mu)`
- `def force(phi, dx, mu)` - *- (1/dx) dE/dphi on interior nodes; boundaries are fixed.*
- `def gradient_error(phi, dx, mu, eps)` - *Max relative error between the analytic force and a central difference.*
- `def gradient_flow(phi, dx, mu, dt, steps)` - *Explicit Euler flow dphi/dt = force; boundaries fixed.*
- `def relax_kink(phi, dx, mu, tolerance)` - *Minimise the discrete energy on interior nodes (L-BFGS-B).*
- `def hessian(phi, dx, mu)` - *Hessian of E/dx on interior nodes (Dirichlet boundaries).*
- `def kink_convergence(mu, length, sizes)`
- `def rotor_crosscheck()`

---

### [`domains/fluid_universe/sims/core3d.py`](domains/fluid_universe/sims/core3d.py)
> *3D JAX pilot: E2 + Skyrme E4 + a Z3 azimuthal potential.*

**Size**: `221` lines (`7785` bytes)

**Functions:**
- `def normalize(field)`
- `def energy_terms(field, dx, mu, K, kappa)`
- `def energy(field, dx, K, kappa, mu)`
- `def z3_order(field)`
- `def relax(field, dx, mu, steps, dt, K, kappa, fix_boundary)`
- `def gradient_check(n, length, mu, eps)`
- `def convergence_scan(n, length, mu, steps_values, dt)` - *Show that the N=32 pilot is not converged in step count.*
- `def pilot_scan(n, length, mu_values, steps, dt)`

---

### [`domains/fluid_universe/sims/production.py`](domains/fluid_universe/sims/production.py)
> *Production scan for claim 15: E2 + Skyrme E4 + Z3 potential.*

**Size**: `299` lines (`11563` bytes)

**Functions:**
- `def spectral_upsample(field, factor)` - *Band-limited upsampling of a periodic real field by an integer factor.*
- `def field_metrics(field, dx, mu, upsample_factor)` - *Energy, topology and smoothness of one field.*
- `def run_stage(field, dx, mu, steps, dt, deadline)` - *Relax for ``steps`` steps and record the smallest pre-normalization norm.*
- `def run_production(n, length, mu, steps, dt, seed, perturbation, upsample_factor, chunk, max_wall_seconds, initial_field, return_field)` - *Run one deterministic production scan and apply the acceptance criteria.*

---

### [`domains/fluid_universe/sims/scale_iteration.py`](domains/fluid_universe/sims/scale_iteration.py)
> *Damped scale iteration toward a stationary Faddeev-Niemi Hopfion.*

**Size**: `95` lines (`3528` bytes)

**Functions:**
- `def rescale_field(field, dx, length, scale)`
- `def run_scale_iteration(n, length, iterations, steps, dt)`

---

### [`domains/fluid_universe/sims/stability.py`](domains/fluid_universe/sims/stability.py)
> *Tangent-space Hessian of the 3D Faddeev-Niemi + Z3 energy.*

**Size**: `381` lines (`13756` bytes)

**Functions:**
- `def tangent_basis(field)` - *Return two orthonormal tangent vectors at every interior site.*
- `def build_candidate(n, length, iterations, steps, dt)` - *Damped scale iteration, returning the snapshot with the smallest |virial|.*
- `def _dense_tangent_hessian(field, dx, e1, e2)` - *Dense Hessian of the energy restricted to the tangent basis (N<=8 only).*
- `def tangent_operator(field, dx, e1, e2)` - *Matrix-free Hessian on the two-dimensional tangent space of each site.*
- `def validate_operator(n, length, steps, dt, k)` - *Compare the matrix-free operator with the dense tangent Hessian.*
- `def hessian_spectrum(field, dx, k, e1, e2)` - *Low-lying eigenvalues of the tangent-space Hessian.*
- `def classify_escape(attempts, note)` - *Summarise a saddle-escape search without promoting beyond one grid.*
- `def hessian_modes(field, dx, k, e1, e2)` - *Lowest tangent eigenpairs, with each eigenvector mapped back to a field.*
- `def normalize_mode(mode)` - *Scale a tangent mode to unit RMS over the interior.*
- `def perturb_along_mode(field, mode, amplitude)` - *Add a normalized tangent mode and renormalize every site.*
- `def classify_candidate(validation, spectrum)` - *Classify one candidate's Hessian without overstating the result.*
- `def run_stability_check(n, length, iterations, steps, dt, k, validate_n)` - *Build the scale-stationary candidate and compute its tangent Hessian.*

---

### [`domains/fluid_universe/sims/water_scattering.py`](domains/fluid_universe/sims/water_scattering.py)
> *1D shallow-water wave scattering at an acoustic horizon (claim 31, ADR-022).*

**Size**: `146` lines (`4959` bytes)

**Functions:**
- `def horizon_flow(x, c, length)`
- `def uniform_flow(x, c, fraction)`
- `def initial_packet(x, center, width, c, depth)`
- `def sponge_profile(x, length, fraction)`
- `def energy_density(eta, u, depth, gravity)`
- `def simulate(flow, n, length, depth, center, width, t_max, dt, sponge_fraction, sponge_strength, gravity)`

---

### [`domains/fluid_universe/theory/__init__.py`](domains/fluid_universe/theory/__init__.py)
> *Exact theory utilities for the Z3/Koide core.*

**Size**: `1` lines (`52` bytes)

---

### [`domains/fluid_universe/theory/circulant.py`](domains/fluid_universe/theory/circulant.py)
> *Exact algebra of the Hermitian 3x3 circulant mass matrix.*

**Size**: `172` lines (`5563` bytes)

**Functions:**
- `def circulant_matrix(a, c, delta)` - *Return the Hermitian circulant M = circ(a, c e^{i delta}, c e^{-i delta}).*
- `def eigenvalues(a, c, delta)` - *Signed eigenvalues of the Hermitian circulant, in the k = 0,1,2 order.*
- `def dft_vectors()` - *Columns are the three DFT eigenvectors v_k, each normalised to unit norm.*
- `def q_signed(x)` - *Q for signed square roots: sum(x^2) / (sum(x))^2.*
- `def q_masses(m)` - *Physical Koide Q for positive masses.*
- `def q_physical_from_roots(x)` - *Physical Q when x are signed square roots: sum(x^2) / (sum(|x|))^2.*
- `def q_from_ac(a, c)` - *The algebraic identity Q = 1/3 + 2 c^2 / (3 a^2).*
- `def extract_ac_delta(x)` - *Inverse DFT: return (a, c, delta) from three signed roots x_k.*
- `def fit_masses(m)` - *Fit (a, c, delta) to positive masses and return Q, r, delta, residuals.*
- `def koide_tau_prediction(m_e, m_mu)` - *Solve Q=2/3 for m_tau given m_e and m_mu.*
- `def _sympy_symbols()`
- `def circulant_symbolic()` - *Return (M, a, c, delta) as sympy objects.*
- `def eigenvalues_symbolic()`
- `def q_identity_symbolic()` - *Return the expression Q_signed - (1/3 + 2c^2/(3a^2)); simplifies to 0.*

---

### [`domains/fluid_universe/theory/derrick.py`](domains/fluid_universe/theory/derrick.py)
> *Derrick scaling for the exact Frank-Oseen + Skyrme + Z3 energy.*

**Size**: `128` lines (`4684` bytes)

**Functions:**
- `def exponents(d)`
- `def scaling_energy(lambda_, e2, e4, potential, d)`
- `def virial(e2, e4, potential, d)`
- `def second_derivative(e2, e4, potential, d)`
- `def stationary_scale_squared(e2, e4, potential, d)` - *Return lambda^2 at the stationary point for d=3, or None if none exists.*
- `def scaling_minimum(e2, e4, potential)`
- `def stable_region(k, kappa, mu)` - *Necessary conditions for a stable scaling soliton in d=3.*
- `def symbolic_virial()` - *Verify d/dlambda E(lambda) at lambda=1 equals the virial expression.*

---

### [`domains/fluid_universe/theory/excited_fluid.py`](domains/fluid_universe/theory/excited_fluid.py)
> *First excited state in the Madelung fluid (claim 24, ADR-015).*

**Size**: `79` lines (`2609` bytes)

**Functions:**
- `def _sigma(omega, hbar, mass)`
- `def excited_density(x, omega, hbar, mass)`
- `def excited_wavefunction(x, omega, hbar, mass)`
- `def excited_quantum_pressure_regular(x, omega, hbar, mass)` - *Regular part of Q away from the node; at x=0 the limit is returned.*
- `def phase_slip(psi)`
- `def phase_gradient_max(psi, dx)`
- `def scaling_slope(dx_values, maxima)`

---

### [`domains/fluid_universe/theory/field_variation.py`](domains/fluid_universe/theory/field_variation.py)
> *Unstructured 1D fixed-endpoint-density G-M field variation (claim 58, ADR-050).*

**Size**: `273` lines (`10018` bytes)

**Classes:**
- `class FieldProblem` - *Discrete G-M field action with exact flux elimination.*
  - Method `.__init__(nx, nt, nu, omega, mass, x_lim, s0_factor)`
  - Method `.unpack(phi)`
  - Method `.action_and_gradient(phi)`
  - Method `._dT(g_dr, dx)` - *Exact transpose of the central/one-sided difference operator.*
  - Method `.optimize(start, maxiter)`

**Functions:**
- `def diffusivity(hbar, mass)`
- `def horizon(omega)`
- `def endpoint_densities(s0, sT, xc)`
- `def bridge_widths(t, s0, omega)` - *Analytic G-M primary-branch widths for the (s0 -> sigma_q) ends.*
- `def start_fields(kind, nt_interior, xc, dx, rho0, rhoT, sq)` - *Initial interior densities (mass-1 normalized slices).*

---

### [`domains/fluid_universe/theory/frank_oseen.py`](domains/fluid_universe/theory/frank_oseen.py)
> *Linearised Frank-Oseen director modes.*

**Size**: `143` lines (`4577` bytes)

**Functions:**
- `def elastic_matrix(kx, ky, kz, k1, k2, k3)` - *2x2 elastic matrix for the two transverse director components.*
- `def dispersion(kx, ky, kz, k1, k2, k3, rho)` - *omega^2 for the two transverse modes; rho is the effective inertia.*
- `def equal_constant_dispersion(k, K, rho)` - *omega for K1=K2=K3=K: omega = sqrt(K/rho) |k|.*
- `def anisotropy(direction, k1, k2, k3, rho)` - *Fractional split of the two omega^2 values at unit |k|.*
- `def modes()` - *Mode counting and the photon question.*
- `def symbolic_elastic_matrix()` - *Sympy Hessian of the quadratic form; equals the numeric matrix.*
- `def symbolic_matches_numeric()`

---

### [`domains/fluid_universe/theory/gaussian_bridge.py`](domains/fluid_universe/theory/gaussian_bridge.py)
> *Fixed-endpoint Gaussian transport bridge (claim 54, ADR-046).*

**Size**: `365` lines (`12777` bytes)

**Functions:**
- `def diffusivity(hbar, mass)`
- `def horizon(omega)`
- `def pinney_coeffs(s0, sT, horizon_T, omega, hbar, mass)` - *Solve A (pinned start), then the quadratic for B, then C.*
- `def pinney_path(coeffs, t_values, omega)`
- `def jacobi_first_zero(sigma_of_t, omega, hbar, mass, t_end, n)` - *First conjugate zero of u'' + Q(t) u = 0 along a bridge path.*
- `def newton_bridge(start_kind, omega, hbar, mass, n, steps)` - *Discrete-EL Newton solve with pinned endpoint densities.*
- `def _discrete_residual(interior, omega, hbar, mass, dt, s0, sT)`
- `def analytic_action(coeffs, omega, hbar, mass, n)` - *High-accuracy quadrature of the continuous action on a Pinney path.*
- `def discrete_action(full_path, omega, hbar, mass, dt)` - *Same midpoint discrete action the Newton solver extremizes.*
- `def match_to_branches(newton_interior, grid, branches, omega)` - *Max-abs deviation of a Newton result from each analytic branch.*
- `def bridge_scales()` - *Collect the fixed-endpoint bridge bundle (no verdict).*
- `def scaling_bundle()` - *omega = 2 mirror of the base bundle (same gates, rescaled horizon).*

---

### [`domains/fluid_universe/theory/gaussian_fluid.py`](domains/fluid_universe/theory/gaussian_fluid.py)
> *Gaussian reduction of the Madelung fluid (claim 22, ADR-013).*

**Size**: `204` lines (`5881` bytes)

**Functions:**
- `def quantum_width(omega, hbar, mass)`
- `def effective_potential(sigma, omega, hbar, mass)`
- `def energy(sigma, sigma_dot, omega, hbar, mass)`
- `def ermakov_rhs(sigma, sigma_dot, omega, hbar, mass)`
- `def simulate(sigma0, sigma_dot0, omega, duration, hbar, mass, dt)`
- `def coherent_rhs(state, omega, hbar, mass)` - *RHS for (x0, v0, sigma, sigma_dot) of the displaced Gaussian.*
- `def coherent_energy(state, omega, hbar, mass)`
- `def simulate_coherent(x0, v0, sigma0, sigma_dot0, omega, duration, hbar, mass, dt)`

---

### [`domains/fluid_universe/theory/hopf.py`](domains/fluid_universe/theory/hopf.py)
> *Hopf-charge estimators for the analytic H=1 map.*

**Size**: `287` lines (`10923` bytes)

**Functions:**
- `def hopf_map(x, y, z)`
- `def _target_of_quaternion(q)`
- `def _jacobian(q)`
- `def fiber_curve(base, samples, dphi)` - *Trace one fiber on S^3 by integrating the null space of dn, then stereographically project.*
- `def linking_number(curve_a, curve_b)` - *Gauss linking integral for two closed curves.*
- `def _bases()`
- `def preimage_charge(samples)`
- `def target_pair_charge(samples)`
- `def reflection_charge(samples)`
- `def rotation_charge(samples)`
- `def shear_charge(samples)`
- `def compactified_field(n, length, reflect)` - *Analytic map with a smooth vacuum window at the box boundary.*
- `def spectral_derivatives(field, dx)` - *Return [d_x field, d_y field, d_z field] with spectral derivatives.*
- `def chern_simons_charge(field, dx)` - *Normalized Chern-Simons charge for a compactified unit-vector field.*
- `def grid_charge(n, length, reflect)` - *Normalized grid Chern-Simons integral for the analytic H=1 map.*
- `def resolution_study(sizes, length)` - *Grid Chern-Simons charge vs resolution for the analytic H=1 map.*
- `def validate()`

---

### [`domains/fluid_universe/theory/hopfion.py`](domains/fluid_universe/theory/hopfion.py)
> *Finite-energy H=1 configuration for the Faddeev-Niemi energy.*

**Size**: `79` lines (`2939` bytes)

**Functions:**
- `def energies(n, length, K, kappa)`
- `def scaling_study(sizes, length)`

---

### [`domains/fluid_universe/theory/hydrogen_fluid.py`](domains/fluid_universe/theory/hydrogen_fluid.py)
> *Hydrogen 1s Madelung reduction (claim 25, ADR-016).*

**Size**: `95` lines (`2630` bytes)

**Functions:**
- `def bohr_radius(hbar, mass, coupling)`
- `def ground_energy(radius, hbar, mass)`
- `def hydrogen_density(r, radius)`
- `def quantum_pressure(r, radius, hbar, mass)`
- `def coulomb_potential(r, coupling)`
- `def force_balance(r, radius, hbar, mass, coupling)` - *V + Q - mu; zero when radius is the Bohr radius.*
- `def si_values()`

---

### [`domains/fluid_universe/theory/hydrogen_radial_nodes.py`](domains/fluid_universe/theory/hydrogen_radial_nodes.py)
> *Hydrogen-2s radial-node two-branch representation (claim 47, ADR-039).*

**Size**: `151` lines (`5140` bytes)

**Functions:**
- `def radial_10(r, radius)` - *Hydrogen 1s radial function, normalized as int r^2 R^2 dr = 1.*
- `def radial_20(r, radius)` - *Hydrogen 2s radial function, normalized as int r^2 R^2 dr = 1.*
- `def radial_probability_20(r, radius)`
- `def branch_split_20(r, radius)` - *Exact two-branch split of R_20; residual is zero by construction.*
- `def node_position(radius)` - *Analytic nodal-shell radius (zero of the 2 - r/a0 factor).*
- `def phase_slip_20(r, radius)` - *Phase jump across the shell from the sign of R_20 (0 or pi).*
- `def overlap_10_20(radius)` - *1s-2s radial overlap integral (analytic: 0 for n != n').*
- `def norm_20(radius)`
- `def peak_radii_20(radius)` - *Analytic probability-peak radii (3 +- sqrt(5)) * a0.*
- `def balance_preserved()` - *Frozen 1s/2p numbers recomputed through the shared modules.*
- `def representation_scales()` - *Collect the representation correspondence bundle (no verdict).*

---

### [`domains/fluid_universe/theory/hydrogen_vortex.py`](domains/fluid_universe/theory/hydrogen_vortex.py)
> *Hydrogen 2p vortex identification (claim 26, ADR-017).*

**Size**: `79` lines (`2246` bytes)

**Functions:**
- `def radial_2p(r, radius)` - *Hydrogen 2p radial function R_21(r), normalized as int r^2 R^2 dr = 1.*
- `def radial_probability(r, radius)`
- `def most_probable_radius(radius)`
- `def azimuthal_velocity(r, theta, m, hbar, mass)`
- `def circulation(m, hbar, mass)`
- `def loop_circulation(r, theta, m, hbar, mass, samples)`
- `def angular_momentum(m, hbar)`

---

### [`domains/fluid_universe/theory/lorentz.py`](domains/fluid_universe/theory/lorentz.py)
> *Linearised director dispersion and the emergent-metric question (claims 11-12).*

**Size**: `185` lines (`6318` bytes)

**Functions:**
- `def elastic_matrix(k, k1, k2, k3)`
- `def speeds(direction, k1, k2, k3, rho)`
- `def residual_anisotropy(k1, k2, k3, rho, n_samples, seed)` - *Sample directions on the sphere and return the max fractional speed split.*
- `def axis_speeds(k1, k2, k3, rho)`
- `def verdict(k1, k2, k3)`
- `def conditional_bound(k1, k2, k3)`

---

### [`domains/fluid_universe/theory/madelung.py`](domains/fluid_universe/theory/madelung.py)
> *Madelung fluid dictionary for the Schrodinger equation (claim 20, ADR-011).*

**Size**: `194` lines (`6131` bytes)

**Functions:**
- `def _wave_numbers(n, dx)`
- `def _derivative(values, k)`
- `def split_step(psi, potential, dt, steps, dx, hbar, mass)` - *Strang split-step integration of the equivalent Schrodinger equation.*
- `def fluid_fields(psi, dx, hbar, mass)` - *Return density, velocity and quantum pressure of a wavefunction.*
- `def free_gaussian_density(x, t, sigma, hbar, mass)`
- `def coherent_state_density(x, t, x0, omega, hbar, mass)`
- `def continuity_residual(psi0, psi1, dt, dx, hbar, mass)`
- `def free_gaussian_fields(x, t, sigma, hbar, mass)` - *Exact density, velocity and quantum pressure of a free Gaussian.*
- `def euler_residual_fields(rho0, v0, q0, rho1, v1, q1, dt, dx, potential, mass, density_floor)` - *Relative Euler residual on the core where the density is resolved.*

---

### [`domains/fluid_universe/theory/nelson.py`](domains/fluid_universe/theory/nelson.py)
> *Nelson stochastic kinematics for the quantum fluid (claim 21, ADR-012).*

**Size**: `122` lines (`4055` bytes)

**Functions:**
- `def ground_state_width(omega, hbar, mass)`
- `def ground_state_density(x, omega, hbar, mass)`
- `def osmotic_velocity(rho, dx, hbar, mass)`
- `def simulate_ou(particles, omega, hbar, mass, dt, steps, seed)` - *Euler-Maruyama for dX = -omega X dt + sqrt(hbar/m) dW.*
- `def free_packet_drift(x, t, sigma, hbar, mass)` - *Forward drift b_+ = v + D d_x ln(rho) for the free Gaussian.*
- `def simulate_free_packet(particles, t, sigma, hbar, mass, steps, seed)`
- `def histogram_density(samples, bins, span)`
- `def l1_error(density, exact, width)`

---

### [`domains/fluid_universe/theory/nelson_closure.py`](domains/fluid_universe/theory/nelson_closure.py)
> *Osmotic-closure no-go at PDE level (claim 48, ADR-040).*

**Size**: `196` lines (`6993` bytes)

**Functions:**
- `def trial_gaussian(x, sigma_sq)`
- `def trial_bimodal(x)`
- `def fp_residual(rho, dx, diffusion)` - *Stationary FP residual for self-consistent osmotic drift.*
- `def interior_mask(x, length)`
- `def residual_scaling()` - *Max-abs residual vs dx for Gaussian probes and one bimodal probe.*
- `def frozen_drift_sigma_map()` - *One frozen-drift reconstruction step per trial width.*
- `def ou_free_packet_instances()` - *OU ground state and free packet satisfy the identity trivially.*
- `def closure_scales()` - *Collect the no-go correspondence bundle (no verdict).*

---

### [`domains/fluid_universe/theory/node_defect.py`](domains/fluid_universe/theory/node_defect.py)
> *Two-branch defect representation of nodal states (claim 46, ADR-038).*

**Size**: `152` lines (`5203` bytes)

**Functions:**
- `def branch_split(x, omega, hbar, mass)` - *Exact two-branch split of the first-excited state.*
- `def branch_regular_pressure_match(x, omega, hbar, mass)` - *Regular quantum pressure evaluated branch-wise away from node.*
- `def node_scaling()` - *Phase-gradient maximum scaling over the frozen grid set.*
- `def vortex_gate()` - *Frozen 2p vortex numbers, recomputed from the existing module.*
- `def representation_scales()` - *Collect the representation correspondence bundle (no verdict).*

---

### [`domains/fluid_universe/theory/reduction.py`](domains/fluid_universe/theory/reduction.py)
> *Dimensional reduction and the effective moment of inertia (claim 6b).*

**Size**: `118` lines (`4335` bytes)

**Functions:**
- `def wall_tension(mu)`
- `def wall_lower_bound_2d(mu, length_y)`
- `def moment_power(alpha)` - *Power of r in the 2D moment integrand for rho ~ r^-alpha.*
- `def moment_finite(alpha)`
- `def moment_log_divergent(alpha)`
- `def moment_numeric(alpha, r_min, r_max)` - *2*pi int rho r^3 dr for rho = r^-alpha on [r_min, r_max].*
- `def moment_profile(profile, r_max, points)` - *Numerical 2*pi int_0^rmax profile(r) r^3 dr; profile must be regular at 0.*
- `def verdict(stated_alpha)`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/theory/rotor.py`](domains/fluid_universe/theory/rotor.py)
> *Quantum rotor H = L^2/(2I) + mu (1 - cos 3 phi) and its spectra.*

**Size**: `177` lines (`6143` bytes)

**Classes:**
- `class RotorSpectrum`
  - Method `.lowest(sector, count)`

**Functions:**
- `def sector_matrix(I, mu, sector, n_cutoff)` - *Dense Hamiltonian in the truncated sector n = sector + 3j, |n| <= n_cutoff.*
- `def spectrum(I, mu, n_cutoff)` - *Low-lying levels in each of the three Fourier sectors.*
- `def convergence(I, mu, cutoffs)`
- `def free_rotor_levels(sector, count, I)` - *Exact mu=0 levels n^2/(2I) in sector n = sector + 3j.*
- `def grid_spectrum(I, mu, n_grid, count)` - *Finite-difference cross-check on a periodic grid phi_j = 2 pi j / N.*
- `def mode_map(sector_energies)` - *The prompt's naive map a=(l0+2 l1)/3, c=(l1-l0)/3.*
- `def implied_roots(sector_energies)` - *Roots generated by the circulant map from three sector levels.*
- `def parity_obstruction()` - *State the exact degeneracy argument and return it as data.*
- `def domain_wall_tension(mu)` - *Analytic tension T = (8/3) sqrt(mu) of the 1-cos(3 phi) wall.*
- `def domain_wall_tension_quad(mu)` - *Numerical quadrature of int_0^{2pi/3} sqrt(2 mu (1-cos 3 phi)) dphi.*

---

### [`domains/fluid_universe/theory/rotor_potential.py`](domains/fluid_universe/theory/rotor_potential.py)
> *Real Z3 rotor potential scan (claim 19, ADR-010).*

**Size**: `122` lines (`4130` bytes)

**Functions:**
- `def sector_matrix(mu, nu, flux, sector, n_cutoff, inertia)`
- `def sector_energies(mu, nu, flux, n_cutoff, inertia)`
- `def scan(mu, nus, fluxes, n_cutoff)`

---

### [`domains/fluid_universe/theory/topology.py`](domains/fluid_universe/theory/topology.py)
> *Topology of a nematic director and the Z3 question.*

**Size**: `113` lines (`4186` bytes)

**Functions:**
- `def has_z3_factor()` - *True only if one of the listed homotopy groups has a Z3 factor.*
- `def direct_result()`
- `def extensions()`
- `def verdict()`
- `def render_markdown(payload)`

---

### [`domains/fluid_universe/theory/two_state_marcus.py`](domains/fluid_universe/theory/two_state_marcus.py)
> *Shared-lambda two-state Marcus assignment (claim 44, ADR-036).*

**Size**: `94` lines (`3661` bytes)

**Functions:**
- `def shared_lambda_widths(temperature_k)` - *Predicted component widths for two Marcus states sharing lambda.*
- `def component_ratio()` - *Observed Jou-Freeman component widths and their ratio.*
- `def kill_thresholds()` - *Frozen kill threshold inherited from ADR-034 (never tuned here).*
- `def two_state_scales(temperature_k)` - *Collect the shared-lambda prediction and the observed ratio.*

---

### [`domains/fluid_universe/theory/variational_center.py`](domains/fluid_universe/theory/variational_center.py)
> *Co-emergence of Newtonian center and Ermakov width (claim 53, ADR-045).*

**Size**: `260` lines (`8576` bytes)

**Functions:**
- `def diffusivity(hbar, mass)`
- `def horizon(omega)`
- `def width_fixed_point(omega, hbar, mass)`
- `def mu_acceleration(mu, omega)`
- `def sigma_acceleration(s, omega, hbar, mass)`
- `def discrete_el_system(interior, omega, hbar, mass, dt, mu_end, s_end)` - *Discrete Euler-Lagrange residuals for the (mu, sigma) pair.*
- `def newton_pair(mu0, s0_factor, omega, hbar, mass, n, steps)` - *Joint Newton solve on the discrete EL system from a constant start.*
- `def _period_from_crossings(times)`
- `def release_pair(mu0, s0_factor, omega, hbar, mass, dt, t_end)` - *Joint Verlet release; per-leg zero crossings give both periods.*
- `def term_match()` - *Sigma-leg term match vs ermakov_rhs; mu-leg analytic identity.*
- `def dynamics_scales()` - *Collect the co-emergence bundle (no verdict).*

---

### [`domains/fluid_universe/theory/variational_dynamics.py`](domains/fluid_universe/theory/variational_dynamics.py)
> *Variational dynamics reproduces Ermakov (claim 51, ADR-043).*

**Size**: `271` lines (`8986` bytes)

**Functions:**
- `def diffusivity(hbar, mass)`
- `def horizon(omega)`
- `def grid(n, omega)`
- `def acceleration(s, omega, hbar, mass)` - *Ermakov acceleration nu^2/s^3 - omega^2*s (V1 re-derives).*
- `def repulsion_term(s, omega, hbar, mass)`
- `def confining_term(s, omega, hbar, mass)`
- `def discrete_el_residual(interior, omega, hbar, mass, dt, endpoint)` - *Discrete Euler-Lagrange residuals (midpoint Lagrangian).*
- `def newton_extremum(start_factor, omega, hbar, mass, n, steps)` - *Newton on the discrete EL system from a constant-path start.*
- `def release_period(factor, omega, hbar, mass)` - *Verlet release from width*factor; interpolated zero-crossing period.*
- `def term_match()` - *Variational acceleration vs Ermakov RHS, whole and per-term.*
- `def dynamics_scales()` - *Collect the dynamics correspondence bundle (no verdict).*

---

### [`domains/fluid_universe/theory/variational_saddle.py`](domains/fluid_universe/theory/variational_saddle.py)
> *Ritz saddle: G-M stationary point in (s, c) (claim 50, ADR-042).*

**Size**: `263` lines (`8550` bytes)

**Functions:**
- `def diffusivity(hbar, mass)`
- `def action_gm_2d(s, c, omega, hbar, mass)`
- `def action_yasui_2d(s, c, omega, hbar, mass)`
- `def grad_gm_2d(s, c, omega, hbar, mass)`
- `def hess_gm_2d(s, c, omega, hbar, mass)`
- `def extremum_sc(omega, hbar, mass)` - *Analytic stationary point (s*, c*) = (nu/omega, 0).*
- `def newton_refine_s(s0, c_fixed, omega, hbar, mass, steps)` - *1D Newton on dJ/ds = 0 at fixed c (definite: maximum in s).*
- `def newton_refine_c(c0, s_fixed, omega, hbar, mass, steps)` - *1D Newton on dJ/dc = 0 at fixed s (definite: minimum in c).*
- `def conditional_extremum(s_values, c_values, omega, hbar, mass)` - *Saddle signature on the grid: max over s at c = 0, min over c.*
- `def yasui_scan(s_values, omega, hbar, mass)` - *Yasui derivative sign over the frozen grid (must stay negative).*
- `def saddle_scales()` - *Collect the saddle correspondence bundle (no verdict).*

---

### [`domains/fluid_universe/theory/variational_width.py`](domains/fluid_universe/theory/variational_width.py)
> *Gaussian Ritz width-selection: G-M vs Yasui (claim 49, ADR-041).*

**Size**: `209` lines (`7480` bytes)

**Functions:**
- `def diffusivity(hbar, mass)`
- `def action_gm(s2, omega, hbar, mass)`
- `def action_yasui(s2, omega, hbar, mass)`
- `def d_action_gm(s2, omega, hbar, mass)`
- `def d_action_yasui(s2, omega, hbar, mass)`
- `def d2_action_gm_s2(s2, omega, hbar, mass)` - *Curvature with respect to s2 (gate variable): -m*nu^2/s2^3.*
- `def d2_action_gm_sigma(sigma, omega, hbar, mass)` - *Curvature with respect to sigma (record only): -3m*nu^2/s^4-m*w^2.*
- `def extremum_s2(omega, hbar, mass)` - *Analytic G-M maximizer s2 = nu/omega with nu = hbar/(2*mass).*
- `def newton_refine(start, omega, hbar, mass, steps)` - *Newton iterations on dJ_G/d(s2) = 0 from a grid argmax start.*
- `def grid_maximum(s2_values, omega, hbar, mass)` - *Grid argmax of J_G plus Newton refinement (not single parabola).*
- `def yasui_monotone(s2_values, omega, hbar, mass)` - *Yasui derivative sign over the frozen grid (must stay negative).*
- `def ermakov_cross_check()` - *Independent argmin of V(sigma) vs analytic G-M maximizer.*
- `def selection_scales()` - *Collect the Ritz correspondence bundle (no verdict).*

---

### [`domains/fluid_universe/theory/vortex_cascade.py`](domains/fluid_universe/theory/vortex_cascade.py)
> *One-parameter vortex/eddy hierarchy test (claim 18, ADR-009).*

**Size**: `126` lines (`4429` bytes)

**Functions:**
- `def geometric_spectrum(ratio, generations)`
- `def power_law_spectrum(exponent, generations)`
- `def solve_power_for_koide(target, lower, upper)` - *Bisection for the power p with Koide Q = target.*
- `def _summary(name, observed, predicted, parameter)`
- `def run_hypotheses(observed)`

---

### [`domains/fluid_universe/theory/vortex_core.py`](domains/fluid_universe/theory/vortex_core.py)
> *HO-1 finite-core node probe (claim 60, ADR-054).*

**Size**: `95` lines (`3613` bytes)

**Functions:**
- `def core_radius()` - *Pre-registered core radius eps0 = 0.1 * a0 (predicted, not fit).*
- `def ho_sigma(omega, hbar, mass)`
- `def core_norm(eps, sigma)` - *Exact L2 norm squared of (x+i*eps)*exp(-x^2/2s^2): s*sqrt(pi)*(s^2/2+eps^2).*
- `def core_density(x, eps, sigma)`
- `def core_phase(x, eps)` - *Phase arg(x + i*eps); singular arg(x) at eps = 0.*
- `def core_velocity(x, eps, hbar, mass)` - *v = (hbar/m) dS/dx with S = arg(x+i*eps): v = -(hbar/m)*eps/(x^2+eps^2).*
- `def core_q_zero(eps, sigma, hbar, mass)` - *Analytic Q at x=0: -hbar^2/2m * (1/eps^2 - 1/sigma^2). eps > 0 required.*
- `def fd_q_zero(eps, n, length, sigma)` - *Second-order central FD Q at x=0 from sqrt(rho); N-convergence probe.*

---

### [`domains/fluid_universe/theory/vortex_loop.py`](domains/fluid_universe/theory/vortex_loop.py)
> *2p core-threading loop probe (claim 61, ADR-056).*

**Size**: `84` lines (`3303` bytes)

**Functions:**
- `def core_scale()` - *Pre-registered core scale delta0 = 0.1 * a0 (predicted, never scanned).*
- `def blob_fraction(r, delta)` - *Analytic loop fraction r^2/(r^2+delta^2) for the blob kernel.*
- `def blob_loop(r, delta, gamma)` - *Circulation on loop radius r for blob-capped velocity.*
- `def blob_umax(delta, gamma)` - *Finite cap: max of r/(r^2+delta^2) is 1/2delta at r=delta.*
- `def floor_vmax(n, length)` - *Constructional divergence: vmax = 1/r_min, r_min = dx/2, hbar=m=1.*
- `def numeric_blob_loop(r, delta, samples, gamma)` - *Own trapezoid quadrature of the blob field (no project imports).*

---

### [`domains/fluid_universe/theory/vortex_particles.py`](domains/fluid_universe/theory/vortex_particles.py)
> *Thin-filament vortex-knot mass hypothesis (claim 17, ADR-008).*

**Size**: `136` lines (`5174` bytes)

**Functions:**
- `def torus_knot(n, radius, tube, samples)` - *Closed T(2,n) curve and its chord vectors.*
- `def knot_length(points)`
- `def biot_savart_energy(points, core)` - *Regularized thin-filament energy proxy at a fixed core radius.*
- `def koide_q(values)`
- `def mass_hypothesis(observed, knots, core, relative_tolerance, koide_tolerance)` - *Test m proportional to the knot energy against the observed masses.*

---

### [`domains/fluid_universe/theory/water_absorption.py`](domains/fluid_universe/theory/water_absorption.py)
> *Bound-free absorption in the finite spherical well (claim 34, ADR-025).*

**Size**: `346` lines (`11792` bytes)

**Functions:**
- `def _j1(x)`
- `def _y1(x)`
- `def _j1_prime(x)`
- `def _y1_prime(x)`
- `def bound_state(radius_m, depth_ev, grid)` - *Return the normalized 1s state of the finite well.*
- `def _dipole_from_state(state, photon_ev, grid)`
- `def dipole_integral(radius_m, depth_ev, photon_ev, points)` - *Radial dipole integral for the 1s -> p continuum, in atomic units.*
- `def _oscillator_from_state(state, photon_ev, grid)`
- `def oscillator_strength(radius_m, depth_ev, photon_ev, points)` - *Oscillator strength at a photon energy, in atomic units.*
- `def oscillator_sum_rule(radius_m, depth_ev, grid, points, max_ev)` - *Integrate the continuum oscillator strength from threshold to max_ev.*
- `def peak_absorption(radius_m, depth_ev, grid, points)` - *Locate the continuum absorption peak for one well.*
- `def required_extra_depth(radius_m, target_ev, grid, points)` - *Depth beyond Born needed to put the continuum peak at target_ev.*
- `def absorption_scales()` - *Collect the bound-free scales used by the report and the tests.*

---

### [`domains/fluid_universe/theory/water_analogue.py`](domains/fluid_universe/theory/water_analogue.py)
> *Shallow-water acoustic horizon (claim 27, ADR-018).*

**Size**: `145` lines (`4294` bytes)

**Functions:**
- `def sound_speed(depth, gravity)`
- `def flow_velocity(r, flow_rate, depth, gravity)`
- `def horizon_radius(flow_rate, depth, gravity)`
- `def surface_gravity(flow_rate, depth, gravity)`
- `def hawking_temperature(kappa)`
- `def acoustic_metric(r, flow_rate, depth, gravity)`
- `def lab_scales(depth, flow_rate, gravity)`
- `def capillary_length(gamma, density, gravity)`
- `def capillary_ratio(horizon_radius_value, length)`
- `def long_wavelength_min_flow(depth, gravity, gamma, density, ratio)`
- `def validity(depth, flow_rate, gamma, density, gravity, ratio)`

---

### [`domains/fluid_universe/theory/water_born_cavity.py`](domains/fluid_universe/theory/water_born_cavity.py)
> *Self-consistent Born cavity synthesis (claim 39, ADR-030).*

**Size**: `112` lines (`3959` bytes)

**Functions:**
- `def born_cavity_energy(radius_m)` - *E_1s(R, Born(R)) plus the surface energy, or None if unbound.*
- `def born_cavity_equilibrium(lower_m, upper_m)` - *Minimize the Born cavity energy over the radius.*
- `def born_cavity_scales()` - *Collect the Born cavity and the water reorganization synthesis.*

---

### [`domains/fluid_universe/theory/water_dispersive.py`](domains/fluid_universe/theory/water_dispersive.py)
> *Dispersive shallow-water horizon (claim 29, ADR-020).*

**Size**: `118` lines (`3489` bytes)

**Functions:**
- `def dispersion(k, depth, gamma, density, gravity)`
- `def group_velocity(k, depth, gamma, density, gravity)`
- `def horizon_wavenumber(omega, depth, gamma, density, gravity, maximum)`
- `def dispersive_horizon(omega, flow_rate, depth, gamma, density, gravity)`
- `def capillary_frequency(depth, gamma, density, gravity)`

---

### [`domains/fluid_universe/theory/water_electron.py`](domains/fluid_universe/theory/water_electron.py)
> *Hydrated-electron cavity scale from water properties (claim 32, ADR-023).*

**Size**: `95` lines (`3077` bytes)

**Functions:**
- `def screened_bohr_radius(epsilon_r)`
- `def screened_energy_ev(epsilon_r)`
- `def capillary_cavity_radius(gamma, mass, hbar)`
- `def capillary_cavity_energy_ev(gamma, mass, hbar)`
- `def infinite_well_gap_ev(radius, mass, hbar)` - *Ground-state energy of an infinite spherical well, not the s->p gap.*
- `def well_radius_for_gap(energy_ev, mass, hbar)` - *Radius where the infinite-well ground-state energy equals energy_ev.*
- `def hydrated_scales()`

---

### [`domains/fluid_universe/theory/water_lineshape.py`](domains/fluid_universe/theory/water_lineshape.py)
> *Fixed-lambda cavity-Marcus line-shape prediction (claim 43, ADR-034).*

**Size**: `92` lines (`3313` bytes)

**Functions:**
- `def gaussian_moments()` - *Exact symmetry facts for a Gaussian band (no inputs, no fit).*
- `def predicted_widths()` - *Absolute Marcus widths at 0 C and 45 C from fixed inputs only.*
- `def kill_thresholds()` - *Pre-registered kill thresholds for a future comparator (data only).*
- `def lineshape_scales()` - *Collect the fixed-lambda prediction and its kill thresholds.*

---

### [`domains/fluid_universe/theory/water_marcus.py`](domains/fluid_universe/theory/water_marcus.py)
> *Marcus band width from the water reorganization energy (claim 40, ADR-031).*

**Size**: `63` lines (`2235` bytes)

**Functions:**
- `def marcus_width_ev(lambda_ev, temperature_k)` - *Classical Marcus Gaussian FWHM in eV.*
- `def gaussian_line_shape(energy_ev, center_ev, fwhm_ev)` - *Normalized Gaussian value at energy_ev.*
- `def marcus_scales()` - *Collect the Marcus widths and the reference comparison.*

---

### [`domains/fluid_universe/theory/water_observed_shape.py`](domains/fluid_universe/theory/water_observed_shape.py)
> *Observed hydrated-electron band-shape comparator data (claim 43, ADR-035).*

**Size**: `160` lines (`6873` bytes)

**Functions:**
- `def observed_width_change_ev(span_k)` - *Observed half-width change over a temperature span.*
- `def shape_evidence()` - *Observed shape facts that a single symmetric Gaussian must meet.*
- `def observed_scales()` - *Collect the observed comparator numbers in one payload.*
- `def jou_freeman_side_widths(temperature_k)` - *Observed red/blue side half-widths from the Jou-Freeman fits.*

---

### [`domains/fluid_universe/theory/water_pressure.py`](domains/fluid_universe/theory/water_pressure.py)
> *Self-consistent finite-well pressure balance (claim 37, ADR-028).*

**Size**: `123` lines (`4157` bytes)

**Functions:**
- `def surface_energy_ev(radius_m)` - *Surface energy 4 pi gamma R^2, in eV.*
- `def total_energy_ev(radius_m, depth_ev)` - *Finite-well 1s plus surface energy, or None if the well is unbound.*
- `def equilibrium_radius(depth_ev, lower_m, upper_m)` - *Radius minimizing the finite-well plus surface energy.*
- `def vde_matched_depth(binding_ev)` - *Depth whose pressure-balanced cavity has the requested 1s binding.*
- `def pressure_scales()` - *Collect the pressure-balanced scan and the VDE-matched point.*

---

### [`domains/fluid_universe/theory/water_rays.py`](domains/fluid_universe/theory/water_rays.py)
> *Radial rays at the shallow-water acoustic horizon (claim 30, ADR-021).*

**Size**: `82` lines (`2568` bytes)

**Functions:**
- `def outgoing_speed(r, flow_rate, depth, gravity)`
- `def ingoing_speed(r, flow_rate, depth, gravity)`
- `def peeling_rate(flow_rate, depth, gravity)`
- `def analytic_outgoing_time(r, r0, horizon, speed)`
- `def integrate_outgoing(r0, r_end, flow_rate, depth, gravity, dt)`

---

### [`domains/fluid_universe/theory/water_reorganization.py`](domains/fluid_universe/theory/water_reorganization.py)
> *Water reorganization and the VDE-optical difference (claim 38, ADR-029).*

**Size**: `112` lines (`4102` bytes)

**Functions:**
- `def _dielectric_contrast(epsilon_s, epsilon_opt)`
- `def reorganization_energy_ev(radius_m, epsilon_s, epsilon_opt)` - *Solvent reorganization energy for a cavity of radius R, in eV.*
- `def radius_for_difference(difference_ev, epsilon_s, epsilon_opt)` - *Radius whose reorganization energy equals difference_ev.*
- `def reorganization_scales()` - *Collect the capillary, required and pressure-balanced comparisons.*

---

### [`domains/fluid_universe/theory/water_softwall.py`](domains/fluid_universe/theory/water_softwall.py)
> *Soft-wall cavity and the hard VDE depth bound (claim 36, ADR-027).*

**Size**: `212` lines (`6865` bytes)

**Functions:**
- `def woods_saxon_level(radius_m, depth_ev, diffuseness_m, angular_momentum, grid, r_max_m)` - *Lowest bound radial eigenvalue of the Woods-Saxon well, in eV.*
- `def depth_for_binding(radius_m, diffuseness_m, binding_ev, grid)` - *Well depth giving a 1s binding of binding_ev for a soft wall.*
- `def cavity_for_observables(diffuseness_m, binding_ev, gap_ev, grid)` - *Woods-Saxon cavity satisfying the VDE and the 1.7 eV gap.*
- `def softwall_scales()` - *Collect the hard depth bound and the Woods-Saxon scan.*

---

### [`domains/fluid_universe/theory/water_temperature.py`](domains/fluid_universe/theory/water_temperature.py)
> *Temperature-dependent Born cavity (claim 41, ADR-032).*

**Size**: `162` lines (`6079` bytes)

**Functions:**
- `def water_dielectric_constant(temperature_c)` - *Static dielectric constant of water, 0-100 C.*
- `def water_surface_tension(temperature_c)` - *Surface tension of water in N/m, 0-100 C.*
- `def _born_depth_ev(radius_m, epsilon_s)`
- `def _surface_energy_ev(radius_m, gamma)`
- `def _reorganization_ev(radius_m, epsilon_s)`
- `def born_cavity_at_temperature(temperature_c)` - *Self-consistent Born cavity at a water temperature.*
- `def temperature_scales()` - *Collect the 0-45 C scan and the observed-shift comparison.*

---

### [`domains/fluid_universe/theory/water_twocomponent.py`](domains/fluid_universe/theory/water_twocomponent.py)
> *Zero-free-parameter two-component band model (claim 45, ADR-037).*

**Size**: `92` lines (`3628` bytes)

**Functions:**
- `def twocomponent_scales(temperature_k)` - *Fixed-input two-component prediction plus observed side widths.*

---

### [`domains/fluid_universe/theory/water_vde.py`](domains/fluid_universe/theory/water_vde.py)
> *VDE and 1.7 eV absorption constrain the finite well (claim 35, ADR-026).*

**Size**: `141` lines (`4874` bytes)

**Functions:**
- `def depth_for_binding(radius_m, binding_ev)` - *Well depth that gives a 1s binding energy of binding_ev.*
- `def _gap_at_radius(radius_m, binding_ev)`
- `def cavity_for_observables(binding_ev, gap_ev)` - *Finite well satisfying the VDE and the 1.7 eV 1s->1p gap.*
- `def vde_scales()` - *Collect the two-observable inversion and the capillary comparison.*

---

### [`domains/fluid_universe/theory/water_well.py`](domains/fluid_universe/theory/water_well.py)
> *Finite spherical well for the hydrated electron (claim 33, ADR-024).*

**Size**: `325` lines (`10958` bytes)

**Functions:**
- `def born_depth_ev(radius_m, epsilon_r)` - *Born solvation depth of a spherical cavity, in eV.*
- `def threshold_depth_ev(radius_m)` - *Well depth at which the 1p state reaches the continuum (kappa = pi).*
- `def infinite_well_transition_ev(radius_m)` - *Infinite-well 1s -> 1p level spacing, in eV.*
- `def _dimensionless_depth(radius_m, depth_ev)`
- `def _state_energy_ev(u, radius_m, depth_ev)`
- `def _f0(u, kappa)`
- `def _f1(u, kappa)`
- `def _bisect(function, lower, upper, kappa)`
- `def _well_1s_root(kappa)`
- `def _well_1p_root(kappa)`
- `def well_roots(radius_m, depth_ev)` - *Return the 1s/1p roots and energies for a finite spherical well.*
- `def _threshold_radius_m()` - *Radius where the Born depth equals the 1p threshold depth.*
- `def _threshold_gap_ev(radius_m)`
- `def _max_born_gap_ev()`
- `def _infinite_radius_for_transition(energy_ev)`
- `def required_depth_ev(radius_m, target_ev)` - *Depth needed for an s->p gap of target_ev, or None if unreachable.*
- `def minimum_required_depth(target_ev)` - *Minimum depth over radii that yields an s->p gap of target_ev.*
- `def well_scales()` - *Collect the finite-well scales used by the report and the tests.*

---

### [`domains/fluid_universe/theory/widened_ritz.py`](domains/fluid_universe/theory/widened_ritz.py)
> *Ritz-widened squared-Hermite trial BVP (claim 59, ADR-051).*

**Size**: `375` lines (`14176` bytes)

**Classes:**
- `class WidenedProblem` - *Squared-Hermite Ritz BVP with exact mass normalization.*
  - Method `.__init__(k_max, nx, nt, nu, omega, mass, x_lim, s0_factor)`
  - Method `.n_vars()`
  - Method `.unpack(params)`
  - Method `.build_rho(fields)`
  - Method `.action_and_gradient(params)`
  - Method `.start_vector(kind)`
  - Method `.solve(kind, maxiter)`
  - Method `.refine(x0, maxiter)`
  - Method `.newton_polish(x0, h, steps, tol)` - *Dense Newton with finite-difference Hessian (R4 pattern).*
  - Method `._finish(x, res)`

**Functions:**
- `def _dT_adj(g, dx)` - *Exact transpose of the central/one-sided difference operator.*
- `def diffusivity(hbar, mass)`
- `def horizon(omega)`
- `def hermite_basis(y, k_max)` - *Probabilists' Hermite He_0..He_k via recurrence.*
- `def bridge_widths(t_values, s0, omega)` - *Analytic G-M primary-branch widths for the (s0 -> sigma_q) ends.*

---

### [`domains/fluid_universe/theory/yasue_action.py`](domains/fluid_universe/theory/yasue_action.py)
> *Pinned-endpoint Yasue-bridge action stationarity (claim 57, ADR-049).*

**Size**: `135` lines (`3958` bytes)

**Functions:**
- `def yasue_discrete_action(full_path, omega, hbar, mass, nu, dt)` - *Midpoint discrete Yasue action (own density: +m*nu^2/2mid^2).*
- `def yasue_analytic_action(coeffs, omega, hbar, mass, nu, horizon_T, n)` - *High-accuracy quadrature of the continuous Yasue action on a branch.*
- `def classical_bridge_action(a, omega, mass)` - *Closed-form nu = 0 fixed-endpoint action J = -m*w*a^2*alpha.*
- `def variation_probe(base_path, horizon_T, bump_kind)` - *Discrete Yasue J along base + lam*amp*bump (own bump family).*
- `def probe_slope(base_path, bump, omega, hbar, mass, nu, dt, lam, amp)`

---

### [`domains/fluid_universe/theory/yasue_bridge.py`](domains/fluid_universe/theory/yasue_bridge.py)
> *Pinned-endpoint Yasue bridge: the c<0 Pinney analytic family (claim 56, ADR-048).*

**Size**: `298` lines (`9476` bytes)

**Functions:**
- `def diffusivity(hbar, mass)`
- `def horizon(omega)`
- `def pinney_coeffs_yasue(s0, sT, horizon_T, omega, hbar, mass, nu)` - *Solve the c<0 endpoint algebra. Returns (branches, disc_norm).*
- `def pinney_path(coeffs, t_values, omega)`
- `def fd_ode_residual(coeffs, omega, hbar, mass, horizon_T, nu, n)` - *8th-order finite-difference check of s_ddot + nu^2/s^3 + w^2 s = 0.*
- `def _discrete_residual_width(interior, omega, hbar, mass, nu, dt, s0, sT)`
- `def newton_width(s0, sT, horizon_T, omega, hbar, mass, nu, n, steps, starts)` - *Width-only BVP Newton solves from the given starts (Yasue sign).*
- `def attribution_diff(analytic, recorded)`
- `def jacobi_first_zero_yasue(t_values, s_values, omega, nu, n)` - *First conjugate zero of u'' + Q u = 0 with Yasue Q = -3nu^2/s^4 + w^2.*
- `def nu_limit_bridge(alpha_T)` - *Closed-form nu=0 fixed-endpoint bridge (classical bank).*

---

### [`domains/fluid_universe/theory/yasue_center.py`](domains/fluid_universe/theory/yasue_center.py)
> *Yasue center-width discriminator: collapse under Yasue, co-emergence under G-M (claim 55, ADR-047).*

**Size**: `452` lines (`16054` bytes)

**Functions:**
- `def diffusivity(hbar, mass)`
- `def horizon(omega)`
- `def width_fixed_point(omega, hbar, mass)`
- `def mu_acceleration(mu, omega)`
- `def sigma_acceleration_gm(s, omega, hbar, mass)`
- `def yasue_acceleration(s, omega, hbar, mass)` - *Yasue width acceleration: -nu^2/s^3 - omega^2*s < 0 for all s > 0.*
- `def sigma_acceleration_yasue(s, omega, hbar, mass)`
- `def discrete_el_system_yasue(interior, omega, hbar, mass, dt, mu_end, s_end)` - *Discrete Euler-Lagrange residuals for the (mu, sigma) pair under Yasue.*
- `def static_residuals(omega, hbar, mass, n)` - *Discrete Yasue EL residual at the G-M stationary path (0, sigma_q).*
- `def newton_attempt_yasue(mu0, s0_factor, omega, hbar, mass, n, steps)` - *Bounded Newton solve on the Yasue discrete EL system.*
- `def _period_from_crossings(times)`
- `def release_pair_yasue(mu0, s0_factor, omega, hbar, mass, dt, t_end, floor)` - *Joint Verlet release under Yasue: classical center, collapsing width.*
- `def term_match()` - *Width-leg sign split + shared center leg, term by term.*
- `def yasue_scales()` - *Collect the discriminator bundle (no verdict).*

---

### [`domains/fluid_universe/theory/yasue_dynamics.py`](domains/fluid_universe/theory/yasue_dynamics.py)
> *Yasui dynamical discriminator: collapse vs G-M oscillation (claim 52, ADR-044).*

**Size**: `174` lines (`6044` bytes)

**Functions:**
- `def yasue_acceleration(s, omega, hbar, mass)`
- `def yasue_release(factor, omega, hbar, mass, floor, dt, t_end)` - *Velocity-Verlet release from rest; stops at the floor.*
- `def quadrature_mild_crossing(factor, omega, hbar, mass)` - *Energy-integral time from release to sigma = 0.5.*
- `def yasue_scales()` - *Collect the discriminator correspondence bundle (no verdict).*

---

### [`domains/fluid_universe/verification/__init__.py`](domains/fluid_universe/verification/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`domains/fluid_universe/verification/audit.py`](domains/fluid_universe/verification/audit.py)
> *Independent verification of every claim marked PROVEN, VERIFIED, or NUMERIC.*

**Size**: `4292` lines (`170752` bytes)

**Classes:**
- `class Audit`
  - Method `.record(claim, passed, detail, expected, observed)`
  - Property `.failed`

**Functions:**
- `def circulant(a, c, delta)`
- `def roots_from_ac(a, c, delta)`
- `def q_from_roots(x)`
- `def q_from_masses(m)`
- `def q_from_ac(a, c)`
- `def fit_linear(x)` - *Independent least-squares/inverse of x_k = a + 2u cos(theta_k) - 2v sin(theta_k).*
- `def load_results(name)`
- `def provenance()` - *Minimal, independent provenance block (no project imports).*
- `def write_atomic(path, text)`
- `def audit_algebra(audit)`
- `def audit_fit(audit)`
- `def y0_vector()`
- `def independent_rhs(_t, s)`
- `def independent_solution(method)`
- `def q_from_yukawas(y)`
- `def audit_rg(audit)`
- `def rotor_levels(I, mu, sector, n_max)`
- `def audit_rotor(audit)`
- `def audit_neutrinos_quarks(audit)`
- `def audit_delta_modes_derrick(audit)`
- `def audit_negatives(audit)`
- `def audit_lorentz(audit)`
- `def audit_hopf(audit)`
- `def audit_hopfion3d(audit)`
- `def audit_hopf_resolution(audit)`
- `def audit_n64(audit)`
- `def audit_scale(audit)`
- `def audit_stability(audit)`
- `def audit_purefn(audit)`
- `def audit_escape(audit)`
- `def audit_lengthscan(audit)`
- `def audit_vortex(audit)`
- `def audit_cascade(audit)`
- `def audit_rotor_potential(audit)`
- `def audit_madelung(audit)`
- `def audit_nelson(audit)`
- `def audit_gaussian_fluid(audit)`
- `def audit_coherent_fluid(audit)`
- `def audit_excited_fluid(audit)`
- `def audit_hydrogen_fluid(audit)`
- `def audit_hydrogen_vortex(audit)`
- `def audit_water_analogue(audit)`
- `def audit_water_validity(audit)`
- `def audit_water_dispersive(audit)`
- `def audit_water_rays(audit)`
- `def audit_water_scattering(audit)`
- `def audit_water_electron(audit)`
- `def audit_water_well(audit)`
- `def audit_water_absorption(audit)`
- `def audit_water_vde(audit)`
- `def audit_water_softwall(audit)`
- `def audit_water_pressure(audit)`
- `def audit_water_reorganization(audit)`
- `def audit_water_born_cavity(audit)`
- `def audit_water_marcus(audit)`
- `def audit_water_temperature(audit)`
- `def audit_water_temperature_residual(audit)`
- `def audit_water_lineshape(audit)`
- `def audit_two_state(audit)`
- `def audit_water_twocomponent(audit)`
- `def audit_node_defect(audit)`
- `def audit_radial_node(audit)`
- `def audit_nelson_closure(audit)`
- `def audit_variational_width(audit)`
- `def audit_variational_saddle(audit)`
- `def audit_variational_dynamics(audit)`
- `def audit_yasue_dynamics(audit)`
- `def audit_variational_center(audit)`
- `def audit_gaussian_bridge(audit)`
- `def audit_yasue_center(audit)`
- `def audit_yasue_bridge(audit)`
- `def audit_yasue_action(audit)`
- `def audit_field_variation(audit)`
- `def audit_widened_ritz(audit)`
- `def audit_vortex_core(audit)`
- `def audit_vortex_loop(audit)`
- `def audit_production(audit)`
- `def audit_convergence(audit)`
- `def audit_temporal(audit)`
- `def audit_extension(audit)`
- `def audit_docs(audit)`
- `def run(write, tag)`
- `def render(payload)`
- `def main()`

---

### [`domains/fluid_universe/verification/compare.py`](domains/fluid_universe/verification/compare.py)
> *Compare two independent verification runs.*

**Size**: `226` lines (`8572` bytes)

**Functions:**
- `def _load(tag, root)`
- `def _digest(payload)`
- `def compare(tags, root)`
- `def _write(name, text, root)`
- `def render(payload)`
- `def main()`

---

### [`domains/fluid_universe/verification/fingerprint.py`](domains/fluid_universe/verification/fingerprint.py)
> *Stable fingerprints for the two-run claim audit.*

**Size**: `221` lines (`5874` bytes)

**Functions:**
- `def default_root()` - *Locate the external fluid-universe checkout next to the host project.*
- `def _source_files(root)`
- `def _digest(files, root)`
- `def source_fingerprint(root)`
- `def results_fingerprint(root)`
- `def fingerprints(root)`

---

### [`domains/fluid_universe/verification/verify.py`](domains/fluid_universe/verification/verify.py)
> *Run the full claim-verification workflow in separate processes.*

**Size**: `70` lines (`2385` bytes)

**Functions:**
- `def _run(module, *args)`
- `def main()`

---

### [`domains/obezite/atif.py`](domains/obezite/atif.py)
> *İddia atıfı çıkarıcı — künye gürültüsünü ayıklayarak.*

**Size**: `68` lines (`1747` bytes)

**Functions:**
- `def atiflar(bagli_sutun)` - *Bağlı sütunundan iddia numaralarını çıkar (künye gürültüsü ayıklanmış).*

---

### [`domains/obezite/backfill.py`](domains/obezite/backfill.py)
> *Backfill script for claims 482-597.*

**Size**: `291` lines (`5469` bytes)

**Functions:**
- `def mevcut_iddialar()`
- `def turdan_iddialar(tur_no)`
- `def main()`

---

### [`domains/obezite/claim_index.py`](domains/obezite/claim_index.py)
> *Create claim cross-reference index mapping claim → VA report, hipotez kartı, tur.*

**Size**: `383` lines (`7669` bytes)

**Functions:**
- `def parse_claims_from_file(filepath)` - *Parse claims from a file, returning list of (claim_id, bağlı_col).*
- `def categorize_reference(ref)` - *Categorize a reference string into type.*
- `def main()`

---

### [`domains/obezite/cokus.py`](domains/obezite/cokus.py)
> *cokus.py — ÇÖKÜŞ ÇAĞLAYANI DENETİMİ (T209, iddia 806) · kontrol.ps1 §13*

**Size**: `129` lines (`5207` bytes)

**Functions:**
- `def satirlar()`
- `def serh_var(satir)` - *Şerh YALNIZ Durum veya Aleyhte veri sütununda sayılır (bkz. başlık: daraltma).*
- `def analiz()`
- `def main()`

---

### [`domains/obezite/dedup.py`](domains/obezite/dedup.py)
> *Deduplicate defter claims across chunk files and CURUTULMUS.*

**Size**: `247` lines (`5255` bytes)

**Functions:**
- `def parse_claims_from_file(filepath)` - *Parse all claim lines from a file, returning list of (claim_id, line, line_num).*
- `def get_all_lines(filepath)` - *Get all lines from a file.*
- `def write_lines(filepath, lines)` - *Write lines to a file.*
- `def main()`

---

### [`domains/obezite/sentez.py`](domains/obezite/sentez.py)
> *Sentez projections: the claim register and file inventory are derived from the canonical*

**Size**: `264` lines (`10051` bytes)

**Functions:**
- `def split_fields(line)` - *A markdown table row as cells; `\|` stays inside a cell.*
- `def macro_bucket(verdict)` - *Group the ledger's free-text verdict into six auditable buckets.*
- `def grade_bucket(grade)`
- `def source_identity(source)`
- `def star_count(claim)`
- `def parse_claims(text)`
- `def summarize(claims)`
- `def count_rows(summary)`
- `def atomic_write(path, content, encoding)`
- `def csv_text(fieldnames, rows)`
- `def register_text(claims)`
- `def inventory_rows(root)`
- `def inventory_text(rows)`
- `def generate(root, with_inventory)`
- `def main(argv)`

---

### [`domains/obezite/split.py`](domains/obezite/split.py)
**Size**: `62` lines (`2271` bytes)

---

### [`domains/obezite/split_range.py`](domains/obezite/split_range.py)
> *Split iddia-defteri.md by claim range (500 claims per file).*

**Size**: `255` lines (`5910` bytes)

**Functions:**
- `def parse_claims(lines)` - *Parse claims from the markdown table lines.*
- `def main()`

---

### [`domains/obezite/uret.py`](domains/obezite/uret.py)
> *uret.py — TÜRETİLMİŞ DOSYA ÜRETİCİSİ (T209, iddia 804)*

**Size**: `490` lines (`10385` bytes)

**Functions:**
- `def oku(p)`
- `def chunk_adi(n)`
- `def bol(satirlar)` - *Kayıpsız bölme: her satır, önceki son iddia numarasının chunk'ına gider.*
- `def banner(ad, alt, ust, adet)`
- `def uret(satirlar)` - *Üretilecek dosyaları {ad: metin} olarak döndür.*
- `def govde_dogrula(satirlar, kutular, sira, onsoz)` - *KAYIPSIZLIK TESTİ — çok-küme korunumu (bkz. modül başlığı: neden 'birebir' değil).*
- `def main()`

---

### [`domains/pnn/__init__.py`](domains/pnn/__init__.py)
> *Phase 2-5 discovery, preclinical and translational pipeline for PNN.*

**Size**: `130` lines (`4319` bytes)

**Functions:**
- `def __getattr__(name)`
- `def __dir__()`

---

### [`domains/pnn/__main__.py`](domains/pnn/__main__.py)
> *Run the PNN screening pipeline as `python -m pnn`.*

**Size**: `6` lines (`137` bytes)

---

### [`domains/pnn/assay.py`](domains/pnn/assay.py)
> *Phase 3 in vitro assay ingestion, hit qualification, and reporting for PNN.*

**Size**: `525` lines (`21705` bytes)

**Classes:**
- `class AssayError` - *Raised when in vitro assay data is malformed or violates contract.*
- `class DegradationResult`
- `class PermeabilityResult`
- `class CytotoxicityResult`
- `class QualifiedHit`
  - Method `.as_row()`

**Functions:**
- `def _parse_float(val, field_name, row_id)`
- `def load_degradation_data(path)` - *Ingest PNN degradation assay CSV.*
- `def load_permeability_data(path)` - *Ingest BBB permeability assay CSV (PAMPA / MDCK-MDR1).*
- `def load_cytotoxicity_data(path)` - *Ingest CellTiter-Glo cytotoxicity counter-screen CSV.*
- `def qualify_leads(degradation, permeability, cytotoxicity, ec50_ceiling_nm, max_deg_floor_pct, pampa_pe_floor, mdck_efflux_ceiling, min_selectivity_index)` - *Qualify leads against Phase 3 in vitro degradation, permeability, and safety criteria.*
- `def render_assay_report(hits, criteria)` - *Render a comprehensive Phase 3 in vitro qualification Markdown report.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/bioisostere.py`](domains/pnn/bioisostere.py)
> *Bioisosteric replacement and metabolic soft-spot optimization engine for PNN.*

**Size**: `542` lines (`20149` bytes)

**Classes:**
- `class BioisostereError` - *Raised when compound SMILES or bioisosteric transformation rules are invalid.*
- `class BioisostereRule`
- `class GeneratedAnalog`
  - Method `.as_row()`

**Functions:**
- `def _ring_label_occurrences(smiles)` - *Count single-digit and %nn ring labels in a SMILES string (label -> occurrences).*
- `def _ring_labels_balanced(smiles)` - *Return True when every ring label is opened and closed (even occurrence count).*
- `def _free_ring_label(parent_smiles)`
- `def _replacement_token(parent_smiles, rule)` - *Return the replacement, renumbering its ring labels away from the parent's labels.*
- `def _target_variants(motif)` - *Yield the motif with any ring labels relabelled, so a literal motif matches equivalent ring numbering.*
- `def _safe_match(smiles, rule)` - *Find the first motif occurrence that can be replaced without splitting a ring context.*
- `def generate_bioisosteres(parent_id, smiles, mw, logp, tpsa, hbd, hba, rotb, pka)` - *Apply rule-based bioisosteric transformations to generate virtual lead analogs.*
- `def render_bioisostere_report(analogs, parent_id)` - *Render a bioisostere generation and optimization Markdown report.*
- `def _parse_opt_float(val)` - *Parse optional numeric float string, returning None for empty or non-numeric cells.*
- `def _safe_cell(value)` - *Return a stripped string for a CSV cell that may be None.*
- `def run_bioisostere_pipeline(compounds_path, target_parent_id)` - *Load parent compound and generate bioisosteric analogs across all rules.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/cli.py`](domains/pnn/cli.py)
> *Command-line entry point for the PNN Phase 2 screening pipeline.*

**Size**: `91` lines (`3406` bytes)

**Functions:**
- `def build_parser()`
- `def _filter(results, min_tier)`
- `def _report(results, kept, source, out)`
- `def _failure(what, why, fix)`
- `def main(argv)`

---

### [`domains/pnn/compounds.py`](domains/pnn/compounds.py)
> *Compound records and CSV ingestion for the PNN screening pipeline.*

**Size**: `234` lines (`8036` bytes)

**Classes:**
- `class CompoundError` - *Raised when input cannot be interpreted as a compound record.*
- `class Compound` - *One candidate with the properties the screening rules consume.*

**Functions:**
- `def normalize_field(name)` - *Map one CSV header to its canonical field name, or None when the column is not used.*
- `def _number(value, field, where)`
- `def _optional_number(values, field, where)`
- `def _charge(raw)`
- `def _build_compound(values, where)`
- `def parse_compounds(rows, source, allow_duplicates)` - *Turn raw CSV rows into compound records; raise CompoundError on the first bad row.*
- `def load_compounds(path, allow_duplicates)` - *Read a UTF-8 CSV file and return its compound records.*

---

### [`domains/pnn/curate.py`](domains/pnn/curate.py)
> *Command-line merge and diversity curation of PNN compound libraries.*

**Size**: `114` lines (`4217` bytes)

**Functions:**
- `def _positive_int(text)`
- `def _bin_width(text)`
- `def build_parser()`
- `def _failure(what, why, fix)`
- `def main(argv)`

---

### [`domains/pnn/curation.py`](domains/pnn/curation.py)
> *Merge, deduplicate and diversify compound libraries for PNN Phase 2.*

**Size**: `170` lines (`6038` bytes)

**Classes:**
- `class CurationError` - *Raised when libraries cannot be merged or curated safely.*
- `class Candidate` - *A compound with its source file and screening verdict.*

**Functions:**
- `def _preference(candidate)`
- `def _merge(left, right)` - *Keep the better record, filling a blank SMILES/name from the other source.*
- `def prepare_candidates(inputs)` - *Screen every input compound while keeping its source provenance.*
- `def deduplicate(candidates)` - *Collapse duplicate IDs first, then exact non-empty SMILES strings.*
- `def property_bin(compound, width)` - *Bin the six core properties on a normalized 0..1 grid.*
- `def _validate(min_tier, per_bin, bin_width, max_compounds)`
- `def curate(candidates, min_tier, per_bin, bin_width, max_compounds)` - *Filter by tier, cap each property bin, then apply the global size limit.*

---

### [`domains/pnn/docking.py`](domains/pnn/docking.py)
> *Docking-score ingestion and consensus ranking for PNN Phase 2.*

**Size**: `273` lines (`10305` bytes)

**Classes:**
- `class DockingError` - *Raised when docking input cannot be interpreted.*
- `class DockingScore` - *One docking result for one compound against one target.*
- `class DockingRank` - *A docking score with its normalized consensus quality.*
- `class CompoundRank` - *The best target row for one compound and how many targets it reached.*

**Functions:**
- `def _token(name)`
- `def _field(name)`
- `def _number(raw, field, where)`
- `def _optional(values, field, where)`
- `def _build(values, where)`
- `def parse_docking_scores(rows, source)` - *Turn raw CSV rows into docking records; refuse duplicates and unusable rows.*
- `def load_docking_scores(path)` - *Read a UTF-8 docking CSV.*
- `def load_screen_table(path)` - *Read the screening ranked CSV into a compound_id keyed table.*
- `def filter_scores(scores, max_rmsd, min_vina)` - *Drop rows without Vina or outside the optional RMSD/Vina limits.*
- `def normalize_scores(scores)` - *Scale each scoring method to 0..1 and combine available methods by weight.*
- `def aggregate_best(ranks)` - *Keep each compound's highest-consensus target and count its docked targets.*

---

### [`domains/pnn/dynamics.py`](domains/pnn/dynamics.py)
> *Molecular Dynamics (MD) trajectory and contact stability analyzer for PNN.*

**Size**: `586` lines (`25668` bytes)

**Classes:**
- `class DynamicsError` - *Raised when MD trajectory data or parameters are malformed.*
- `class TrajectoryPoint` - *A single snapshot / frame in an MD simulation trajectory.*
- `class TrajectoryAnalysis` - *Comprehensive statistical and structural analysis of an MD trajectory.*
  - Method `.as_dict()`
  - Method `.as_row()`

**Functions:**
- `def _fmt(value, spec)`
- `def _display(value, spec)`
- `def _calc_stats(values)` - *Calculate mean, standard deviation, and maximum of the supplied (non-None) values.*
- `def _parse_optional_float(raw, label, row_idx)`
- `def load_trajectory_csv(path)` - *Load MD trajectory snapshots from a CSV file; absent optional columns stay unmeasured.*
- `def analyze_trajectory(points, compound_id, target_id)` - *Analyze MD frames; metrics absent from the input stay unmeasured and block a stability verdict.*
- `def generate_trajectory_svg(analysis, points, width, height)` - *Generate a clean SVG chart displaying MD trajectory RMSD over simulation time.*
- `def render_trajectory_report(analysis)` - *Render a Markdown report documenting the MD trajectory stability analysis.*
- `def run_dynamics_pipeline(trajectory_path, compound_id, target_id, out_dir)` - *Execute the MD trajectory stability workflow, optionally writing reports and charts.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/ind.py`](domains/pnn/ind.py)
> *Allometric human clinical dose projection and IND regulatory dossier compiler for PNN.*

**Size**: `597` lines (`25593` bytes)

**Classes:**
- `class IndError` - *Raised when clinical projection inputs violate regulatory or pharmacological contracts.*
- `class HumanDoseProjection`
  - Method `.as_row()`

**Functions:**
- `def _fmt(value, spec)`
- `def _display(value, spec)`
- `def calculate_allometric_scaling(animal_dose_mg_kg, mouse_cl_l_h_kg, mouse_vd_l_kg, noael_mg_kg, noael_km, mouse_weight_kg, human_weight_kg, km_human, safety_factor)` - *Compute FDA / ICH allometric scaling parameters from measured mouse PK and NOAEL data.*
- `def _project_one(cid, name, info, safety_factor, human_weight_kg)`
- `def project_clinical_candidates(compounds, preclinical_data, lead_id, safety_factor, human_weight_kg)` - *Calculate clinical dose projections from measured preclinical data only.*
- `def render_ind_dossier(projections, lead_id, criteria)` - *Render an IND nomination dossier; absent values are shown as UNMEASURED, never filled in.*
- `def _parse_opt_float(val)` - *Parse an optional numeric float string, returning None for empty or non-numeric cells.*
- `def _as_paths(compounds_path)`
- `def load_candidate_records(compounds_path, candidates_path, tox_path)` - *Load compound records and measured preclinical exposures for allometric scaling.*
- `def compile_ind_dossier(lead_id, compounds_path, candidates_path, tox_path, extra_pk)` - *Compile human dose projections and the IND dossier from measured inputs only.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/mpo.py`](domains/pnn/mpo.py)
> *Phase 5 Multiparametric Optimization (MPO) and candidate profiling engine for PNN.*

**Size**: `472` lines (`19413` bytes)

**Classes:**
- `class MpoError` - *Raised when MPO input data is invalid or missing required metrics.*
- `class MpoProfile`
  - Method `.as_row()`

**Functions:**
- `def _ramp_desirability(val, low, high, increasing)` - *Calculate linear ramp desirability between low and high bounds.*
- `def calculate_cns_mpo(mw, logp, tpsa, hbd, pka, logd)` - *Calculate Pfizer CNS MPO score (0.0 to 6.0) from physicochemical properties.*
- `def profile_candidate(compound_id, name, mw, logp, tpsa, hbd, pka, ec50_nm, brain_kp, oral_f_pct, selectivity_index)` - *Calculate CNS MPO, multi-domain desirability functions, and identify optimization liabilities.*
- `def render_mpo_report(profiles)` - *Render comprehensive Phase 5 Lead Optimization & MPO Profiling markdown report.*
- `def _parse_opt_float(val)` - *Parse optional numeric float string, returning None for empty or non-numeric cells.*
- `def _safe_cell(value)` - *Return a stripped string for a CSV cell that may be None.*
- `def run_mpo_analysis(compounds_path, candidates_path, assays_path)` - *Ingest datasets, compute MPO and composite desirability, and generate profiles.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/pathway.py`](domains/pnn/pathway.py)
> *Hypothalamic circuit, perineuronal net turnover, and dosing dynamics simulator for PNN.*

**Size**: `422` lines (`17610` bytes)

**Classes:**
- `class PathwayError` - *Raised when simulation parameters are physically invalid or malformed.*
- `class SimulationPoint`
  - Method `.as_row()`
- `class RegimenSummary`
  - Method `.as_row()`

**Functions:**
- `def _get_dosing_times(regimen, duration_h)` - *Return schedule of dose administration times in hours.*
- `def simulate_circuit_dynamics(compound_id, dose_mg_kg, regimen, duration_days, dt_h, half_life_h, cmax_per_dose, ec50_nm, mw)` - *Run an explicit forward-Euler integration of hypothalamic circuit dynamics.*
- `def render_pathway_report(summary, sample_points)` - *Render comprehensive markdown simulation report for dosing regimen.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/pipeline.py`](domains/pnn/pipeline.py)
> *Command-line end-to-end Phase 2 lead selection for the PNN project.*

**Size**: `137` lines (`4489` bytes)

**Functions:**
- `def _positive_int(text)`
- `def _bin_width(text)`
- `def build_parser()`
- `def _failure(what, why, fix)`
- `def main(argv)`

---

### [`domains/pnn/preclinical.py`](domains/pnn/preclinical.py)
> *Phase 4 in vivo pharmacokinetics (PK), pharmacodynamics (PD), and preclinical candidate selection for PNN.*

**Size**: `558` lines (`24181` bytes)

**Classes:**
- `class PreclinicalError` - *Raised when in vivo preclinical data is malformed or violates contract.*
- `class ConcentrationPoint`
- `class PkProfile`
- `class PdOutcome`
- `class PreclinicalCandidate`
  - Method `.as_row()`

**Functions:**
- `def _parse_num(val, field_name, row_id)`
- `def calculate_nca(points, dose_mg_kg, compound_id, route, tissue)` - *Perform non-compartmental pharmacokinetic analysis (NCA) on concentration-time points.*
- `def load_pk_data(path)` - *Ingest concentration-time series CSV and calculate NCA PK profiles.*
- `def load_pd_data(path)` - *Ingest in vivo pharmacodynamic (PD) and metabolic outcomes CSV.*
- `def evaluate_candidates(pk_profiles, pd_outcomes, min_kp_brain, min_oral_f_pct, min_wfa_reduction_pct, min_itt_improvement_pct)` - *Triage compounds against preclinical PK exposure and PD metabolic criteria.*
- `def render_preclinical_report(candidates, criteria)` - *Render a comprehensive Phase 4 in vivo preclinical qualification report.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/rank.py`](domains/pnn/rank.py)
> *Command-line consensus ranking of docking results for PNN Phase 2.*

**Size**: `245` lines (`8401` bytes)

**Classes:**
- `class ShortlistRow` - *One ranked compound ready for CSV output.*
  - Method `.as_row()`

**Functions:**
- `def _property_score(info)`
- `def _selected(best, screen, min_tier)` - *Filter aggregated compounds by screening evidence and sort them by consensus.*
- `def build_shortlist(scores, screen, min_tier, max_rmsd, min_vina)` - *Return shortlist rows and a summary of what each filter removed.*
- `def build_parser()`
- `def _failure(what, why, fix)`
- `def main(argv)`

---

### [`domains/pnn/reports.py`](domains/pnn/reports.py)
> *Atomic CSV, JSON and text report writers shared by the PNN command line tools.*

**Size**: `68` lines (`2038` bytes)

**Functions:**
- `def _open_temp(path)`
- `def _finish(path, handle)`
- `def write_csv(path, fieldnames, rows)` - *Write `rows` as CSV to a temporary file, then replace `path` atomically.*
- `def write_json(path, report)` - *Write `report` as JSON to a temporary file, then replace `path` atomically.*
- `def write_text(path, text)` - *Write `text` to a temporary file, then replace `path` atomically.*

---

### [`domains/pnn/rules.py`](domains/pnn/rules.py)
> *Property rules that turn the PNN BBB/CNS design criteria into verdicts.*

**Size**: `219` lines (`7784` bytes)

**Classes:**
- `class CriterionResult` - *One rule's verdict for one compound.*

**Functions:**
- `def _range(name, value, low, high, optimal_low, optimal_high, unit)`
- `def _ceiling(name, value, limit, optimal, unit)`
- `def _physicochemical(compound)`
- `def _pka(compound)`
- `def _charge(compound)`
- `def _logbb(compound)`
- `def _brain_plasma(compound)`
- `def _oral_bioavailability(compound)`
- `def _cyp3a4(compound)`
- `def _herg(compound)`
- `def _pnn_ec50(compound)`
- `def evaluate(compound)` - *Return every rule verdict for `compound` in a stable order.*
- `def weight(criterion_name)` - *Core design properties outweigh optional measured/ADMET properties.*

---

### [`domains/pnn/runner.py`](domains/pnn/runner.py)
> *One-click turnkey discovery pipeline runner for PNN.*

**Size**: `540` lines (`21304` bytes)

**Classes:**
- `class RunnerError` - *Raised when one-click pipeline runner cannot execute or find input data.*
- `class RunSummary`

**Functions:**
- `def is_daily_timepoint(time_h, period_h, tolerance_h)` - *Return True when a simulation time falls on a whole-day boundary.*
- `def execute_turnkey_pipeline(vendor_csv, repurposing_csv, docking_csv, degradation_csv, permeability_csv, cytotoxicity_csv, pk_csv, pd_csv, out_dir, min_tier, emit_root, tox_csv, safety_pharm_csv)` - *Execute complete end-to-end PNN discovery workflow from libraries to interactive studio.*
- `def print_run_banner(summary)` - *Print terminal summary banner for turnkey runner.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/safety.py`](domains/pnn/safety.py)
> *IND-enabling safety pharmacology and repeat-dose toxicology assessment for PNN.*

**Size**: `644` lines (`26843` bytes)

**Classes:**
- `class SafetyError` - *Raised when safety pharmacology or toxicology data is malformed or violates contract.*
- `class ToxStudy`
- `class SafetyPharm`
- `class SafetyAssessment`
  - Method `.as_row()`

**Functions:**
- `def _normalize(name)`
- `def _species_key(species)`
- `def _parse_required_float(value, field_name, row_id)`
- `def _parse_optional_float(value, field_name, row_id)`
- `def _parse_optional_bool(value, field_name, row_id)`
- `def _check_percent(value, field_name, row_id)`
- `def load_tox_studies(path)` - *Ingest repeat-dose toxicology studies with NOAEL/LOAEL and target-organ findings.*
- `def load_safety_pharmacology(path)` - *Ingest ICH S7A/S7B safety pharmacology and genotoxicity panel results.*
- `def noael_hed_mg_kg(noael_mg_kg, species, human_km)` - *Convert a species NOAEL to a human equivalent dose using its body-surface-area factor.*
- `def most_sensitive_study(studies)` - *Return the study with the lowest NOAEL human equivalent dose.*
- `def _genotoxicity(safety_pharm)`
- `def assess_safety(tox_studies, safety_pharm, safety_factor, herg_margin_min, herg_margin_fail, cyp_inhibition_max_pct, cyp_inhibition_caution_pct, human_weight_kg)` - *Assess each compound against IND-enabling toxicology and safety pharmacology criteria.*
- `def render_safety_report(assessments, criteria)` - *Render a Markdown IND-enabling safety package summary.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/sar.py`](domains/pnn/sar.py)
> *Structure-Activity Relationship (SAR) and Bemis-Murcko scaffold decomposition for PNN.*

**Size**: `772` lines (`29999` bytes)

**Classes:**
- `class SarError` - *Raised when SAR data is malformed or violates scientific contract.*
- `class CompoundSar`
  - Method `.as_row()`
- `class ScaffoldCluster`
  - Method `.as_row()`

**Functions:**
- `def parse_smiles_graph(smiles)` - *Parse SMILES into an atom list and adjacency graph.*
- `def find_biconnected_blocks(n, adj)` - *Hopcroft-Tarjan algorithm to find all biconnected components (cycle systems).*
- `def serialize_subgraph_smiles(atoms, adj, nodes)` - *Serialize an induced subgraph of atoms into a SMILES string.*
- `def _identify_scaffold_name(atoms, cycle_blocks, linkers)` - *Identify recognizable chemotype descriptor for Bemis-Murcko framework.*
- `def extract_scaffold(smiles)` - *Decompose a SMILES into Bemis-Murcko framework SMILES, chemotype name, and R-group substituents.*
- `def load_compounds(path)` - *Load compound property records from CSV.*
- `def load_docking_scores(path)` - *Load multi-target or single-target docking scores (consensus or best affinity).*
- `def load_assay_potencies(path)` - *Load in vitro assay EC50 potencies.*
- `def _parse_opt_float(val)` - *Parse optional numeric float string, returning None for empty or non-numeric cells.*
- `def load_preclinical_exposures(path)` - *Load in vivo preclinical exposures (brain_plasma_ratio, oral_bioavailability_pct).*
- `def analyze_sar(compound_records, docking_scores, assay_potencies, preclinical_exposures)` - *Decompose compounds into Bemis-Murcko scaffolds and perform SAR activity clustering.*
- `def render_sar_report(compounds, clusters)` - *Render a comprehensive Structure-Activity Relationship (SAR) markdown report.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/screen.py`](domains/pnn/screen.py)
> *Tiering and ranking for the PNN Phase 2 property screen.*

**Size**: `79` lines (`3049` bytes)

**Classes:**
- `class ScreenResult` - *A compound, its verdicts, and the resulting triage tier.*
  - Method `.failed_criteria()`
  - Method `.unknown_criteria()`

**Functions:**
- `def _weighted_score(criteria)`
- `def _tier(criteria, score)`
- `def evaluate_compound(compound)` - *Evaluate every rule for one compound and assign its tier.*
- `def screen_compounds(compounds)` - *Evaluate and rank compounds by tier, then score (highest first), then ID.*
- `def summarize(results)` - *Count tiers and report the scored average, including rejected compounds.*

---

### [`domains/pnn/selection.py`](domains/pnn/selection.py)
> *End-to-end Phase 2 lead selection for the PNN project.*

**Size**: `336` lines (`12882` bytes)

**Classes:**
- `class PipelineError` - *Raised when a Phase 2 run cannot produce a defensible lead set.*
- `class LeadSelection` - *The selected compounds and the audit counts for one Phase 2 run.*
- `class LeadRun` - *A completed run: selected compounds, written artifacts and the manifest.*

**Functions:**
- `def _digest(path)` - *Return the SHA-256 hex digest of a file without loading it whole.*
- `def _load_inputs(paths)`
- `def _screen_table(results)`
- `def select_leads(inputs, docking, min_tier, per_bin, bin_width, max_compounds, max_rmsd, min_vina)` - *Curate, screen and rank one lead set from compound and docking CSVs.*
- `def _options(min_tier, per_bin, bin_width, max_compounds, max_rmsd, min_vina)`
- `def _manifest(selection, outputs, options)`
- `def render_lead_report(selection, options, top_n)` - *Render a comprehensive Markdown lead report honoring G-001, G-002, and G-003.*
- `def run_pipeline(inputs, docking, out_dir, min_tier, per_bin, bin_width, max_compounds, max_rmsd, min_vina, top_n_report)` - *Run the three Phase 2 stages and write their artifacts, report and manifest.*

---

### [`domains/pnn/studio.py`](domains/pnn/studio.py)
> *Interactive Lead & Assay Visualization Studio and Standalone HTML Dashboard for PNN.*

**Size**: `1322` lines (`53893` bytes)

**Classes:**
- `class StudioError` - *Raised when studio inputs are malformed or missing required data.*
- `class StudioCompound`

**Functions:**
- `def _get_val(obj, key, default)` - *Extract a field from either a dict/mapping or an object attribute with fallback.*
- `def _get_field(obj, keys, default)` - *Extract first non-empty field matching one of several alias keys.*
- `def _normalize_cns_axis(val, optimal_center, half_width)`
- `def generate_radar_svg(compounds, width, height)` - *Generate SVG radar chart for CNS drug-likeness physicochemical properties.*
- `def generate_docking_heatmap_svg(compounds, targets, cell_w, cell_h)` - *Generate multi-target docking affinity heatmap in SVG.*
- `def generate_pk_curve_svg(compounds, width, height)` - *Generate in vivo pharmacokinetic concentration-time profiles SVG.*
- `def _safe_cell(value)` - *Return a stripped string for a CSV cell that may be None.*
- `def _parse_required_float(raw, field, compound_id)` - *Parse a required numeric studio field, raising StudioError on missing data.*
- `def _parse_required_int(raw, field, compound_id)` - *Parse a required integer studio field, raising StudioError on missing data.*
- `def _parse_circuit_points(simulation_points)` - *(time_h, pnn_pct, akt_pct) for every complete, numeric simulation row, time-sorted.*
- `def generate_circuit_dynamics_svg(simulation_points, width, height)` - *Generate SVG time-course chart for hypothalamic circuit dynamics (PNN turnover vs pAKT restoration).*
- `def render_studio_html(compounds, radar_svg, heatmap_svg, pk_svg, circuit_svg, circuit_points, dossier_data, safety_data, targets_data, wave_ledger, wave_highlights)` - *Render full standalone HTML5 studio dashboard.*
- `def _parse_opt_float(val)` - *Parse optional numeric float string, returning None for empty or non-numeric cells.*
- `def load_studio_data(compounds_path, docking_path, assays_path, pk_path, preclinical_candidates_path)` - *Assemble all project datasets into StudioCompound instances.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/tables.py`](domains/pnn/tables.py)
> *CSV row contracts shared by the PNN Phase 2 command line tools.*

**Size**: `108` lines (`3053` bytes)

**Functions:**
- `def _optional(value)`
- `def curated_row(candidate, width)` - *Return one curated-library row, including source and property bin.*
- `def screen_row(result)` - *Return one ranked-screening row for a screened compound.*

---

### [`domains/pnn/target.py`](domains/pnn/target.py)
> *Target receptor profiles, binding-pocket invariants and Vina grid generation for PNN.*

**Size**: `313` lines (`12212` bytes)

**Classes:**
- `class TargetProfile` - *Molecular target profile defining receptor invariants and docking grid coordinates.*

**Functions:**
- `def get_target(target_id)` - *Retrieve a target profile by case-insensitive ID or alias.*
- `def list_targets()` - *Return all registered PNN target profiles.*
- `def generate_vina_config(profile, receptor_pdbqt, out_pdbqt, exhaustiveness, num_modes, energy_range)` - *Format AutoDock Vina grid parameter configuration text.*
- `def build_parser()`
- `def main(argv)`

---

### [`domains/pnn/waves.py`](domains/pnn/waves.py)
> *Wave-ledger aggregation: search-wave CSVs plus obtainability proofs into report artifacts.*

**Size**: `298` lines (`11835` bytes)

**Classes:**
- `class WaveLedgerError` - *Raised when wave-ledger inputs cannot be read or parsed.*
- `class WaveRow`
  - Method `.as_row()`
- `class WaveHighlight`
  - Method `.as_row()`

**Functions:**
- `def _wave_number_from_filename(filename)`
- `def _count_wave_compounds(path)` - *Count data rows in a wave screening CSV (header excluded).*
- `def _classify_proof_row(entry_id, note)` - *Return (wave, kind, serial, kill_count) for one obtainability_proofs row id.*
- `def collect_wave_ledger(waves_dir, proofs_path)` - *Aggregate per-wave compound counts plus shortlist/park/kill tags.*
- `def render_wave_ledger_markdown(rows, highlights)` - *Render the wave ledger as a Markdown report section.*
- `def render_wave_section(rows, highlights)` - *Render the wave ledger as a standalone studio HTML panel section.*

---

### [`engine/__init__.py`](engine/__init__.py)
> *Research Engine: provenance-backed claims, pre-registered hypotheses, executable kill tests.*

**Size**: `3` lines (`122` bytes)

---

### [`engine/__main__.py`](engine/__main__.py)
> *Entry point for `python -m engine`.*

**Size**: `6` lines (`128` bytes)

---

### [`engine/ai.py`](engine/ai.py)
> *AI provenance adapter: notarize model I/O, ingest UNVERIFIED claims, propose template tests.*

**Size**: `507` lines (`19242` bytes)

**Functions:**
- `def actor_for(model_id)` - *Attribution for AI-proximate actions: the model, not the default agent.*
- `def _to_artifact(row)`
- `def _validate_cited(cited)` - *Check citation shape only; existence is enforced at ingest and by AI-001.*
- `def _cited_entries(artifact)` - *Parse the stored cited payload; shape was checked at record time.*
- `def _ensure_cited_resolve(conn, artifact, source_ref)` - *Fail closed when a cited source cannot be resolved in-program.*
- `def _resolve_actor(artifact, actor)` - *Default AI-proximate actions to the model identity.*
- `def record_artifact(conn, research_ref, kind, model_id, prompt_text, output_text, cited)` - *Notarize one model invocation: hashes in, raw text never stored.*
- `def get_artifact(conn, ref)` - *Fetch one AI artifact by identifier.*
- `def list_artifacts(conn, research_ref)` - *List AI artifacts, optionally filtered by program.*
- `def ingest_claim(conn, artifact_ref, text, kind, source_ref, quote, locator, confidence, kill_test, basis, prerequisites, question_ref, stance, actor)` - *Enter one AI-proposed claim as UNVERIFIED, or refuse it loudly.*
- `def ingest_hypothesis(conn, artifact_ref, statement, criterion, confidence, question_ref, actor)` - *Pre-register one AI-proposed hypothesis from an idea artifact.*
- `def propose_test(conn, artifact_ref, template, name, claim_ref, hypothesis_ref, actor)` - *Bind a fixed-template kill test to a claim or hypothesis.*
- `def fetch_external(*args, **kwargs)` - *Refusing stub for the external-API adapter: this build is local-only.*
- `def render_draft(conn, research_ref)` - *Assemble an article draft from surviving claims only. Never upgrades a verdict.*

---

### [`engine/amendments.py`](engine/amendments.py)
> *Append-only amendment ledger: every correction keeps its before and after.*

**Size**: `100` lines (`3118` bytes)

**Functions:**
- `def _to_amendment(row)`
- `def record_amendment(conn, subject_kind, subject_id, field, before, after, reason, actor)` - *Append one correction; the reason is mandatory and the past is kept.*
- `def list_amendments(conn, subject_kind, subject_id)` - *Amendments in record order, optionally filtered to one corrected record.*

---

### [`engine/analysis.py`](engine/analysis.py)
> *Discovery and ranking over the graph: contradictions, coverage, keystones.*

**Size**: `904` lines (`37096` bytes)

**Functions:**
- `def _negated(text)` - *Whether an assertion carries an explicit negation marker.*
- `def polarity_mismatch(left, right)` - *Exactly one of two assertions is negated: an advisory-only polarity bit.*
- `def keywords(text)` - *Content words of an assertion, lowercased and de-duplicated.*
- `def overlap(left, right)` - *Jaccard overlap of two keyword sets, 0.0 when either is empty.*
- `def _pair_score(first, second)`
- `def contradictions(conn, research_ref, min_score)` - *Pairs of supporting and contradicting claims attached to the same question.*
- `def unlinked_contradictions(conn, research_ref, min_score)` - *Claims that contradict each other by keyword overlap but have no `contradicts` edge.*
- `def evidence_matrix(conn, research_ref)` - *Sources x questions: how many claims each source contributes to each question.*
- `def keystone_claims(conn, research_ref, limit)` - *Claims that the rest of the graph leans on, by transitive dependents and inbound edges.*
- `def expose(conn, claim_ref)` - *What a claim would take down with it, plus what cites it.*
- `def _parse_time_bound(value, name)` - *Validate a `--since`/`--until` bound and normalize it to second-resolution UTC ISO.*
- `def _group_provenance(conn, claim_id, label, since, until)` - *Protocols, instruments and units recorded for one observation group.*
- `def _comparability(baseline, treatment, allow_incomparable, allow_self_reported)` - *Whether two groups measure the same quantity under the same procedure.*
- `def claim_statistics(conn, claim_ref, baseline, treatment, seed, resamples, allow_incomparable, allow_self_reported, actor, plan_ref, since, until)` - *Compare two observation groups of a claim and record that the comparison happened.*
- `def observation_summary(conn, claim_ref)` - *Per-group counts and basic summaries for one claim.*
- `def claim_trend(conn, claim_ref, group, actor, since, until)` - *Fit a least-squares trend over a group's observations in recording order.*
- `def group_correlations(conn, claim_ref, groups, allow_incomparable, allow_self_reported, since, until)` - *Advisory pairwise Pearson correlations between a claim's observation groups.*
- `def batch_statistics(conn, research_ref, baseline, treatment, seed, resamples, allow_incomparable, allow_self_reported, actor, since, until, holm)` - *Compare one baseline/treatment pair across every claim in a program.*

---

### [`engine/artifacts.py`](engine/artifacts.py)
> *Artifact I/O: timestamps, output digests and atomic file replacement.*

**Size**: `51` lines (`1755` bytes)

**Functions:**
- `def utc_now()` - *Return a second-resolution UTC timestamp in ISO-8601 form.*
- `def digest(kind, payload)` - *Domain-separated digest: the artifact kind is hashed before the payload.*
- `def sha256_text(value)` - *Hash extracted output so reproducibility is checked without storing it all.*
- `def atomic_write_text(path, text)` - *Write UTF-8 text through a flushed temp file and an atomic replace.*

---

### [`engine/attempts.py`](engine/attempts.py)
> *Append-only attempt ledger for kill-test executions.*

**Size**: `131` lines (`4781` bytes)

**Functions:**
- `def _to_attempt(row)`
- `def record(conn, test_id, run_group, outcome, reason)` - *Append one attempt; a replaceable outcome requires a recorded reason.*
- `def authoritative(conn, test_id, command_sha256, code_sha256, inputs_sha256)` - *The earliest non-replaceable attempt bound to the current command, code and inputs.*
- `def for_group(conn, test_id, run_group)` - *The attempt recorded for one run group, if any.*
- `def list_attempts(conn, test_ref, limit)` - *Attempts for one test or all tests, newest sequence first.*

---

### [`engine/bundle.py`](engine/bundle.py)
> *Portable JSONL export of the evidence graph, and a digest of its content.*

**Size**: `285` lines (`10458` bytes)

**Functions:**
- `def _rows(conn, table, research_id)`
- `def export_records(conn, research_ref)` - *Return the ordered graph records and their per-table counts.*
- `def evidence_records(records)` - *Drop the audit log from the digest input.*
- `def content_records(records)` - *Semantic projection of a record set: run allocation artefacts are dropped.*
- `def _digest(records, kind)`
- `def graph_sha256(conn, research_ref)` - *Exact digest of every evidence record, including run bookkeeping; excludes the audit log.*
- `def content_sha256(conn, research_ref)` - *Digest of the graph's content, stable across a pure re-verification.*
- `def export_jsonl(conn, path, research_ref)` - *Write the graph as deterministic JSONL lines, atomically.*
- `def verify_export(path)` - *Check a snapshot against the digest it carries in its own meta line.*

---

### [`engine/calibration.py`](engine/calibration.py)
> *Hypothesis calibration: score preregistered confidence against recorded outcomes.*

**Size**: `184` lines (`7018` bytes)

**Functions:**
- `def _clip(probability)` - *Keep log loss finite without turning a certain prediction into a free pass.*
- `def _bin_index(probability)` - *Return the fixed reliability bin for one probability, including exactly 1.0.*
- `def summary(conn, research_ref, min_resolved)` - *Compute the calibration scorecard for one program without writing anything.*
- `def score(conn, research_ref, min_resolved, actor)` - *Score one program and append the calibration run to the event log.*

---

### [`engine/cascade.py`](engine/cascade.py)
> *Transitive invalidation: when a premise collapses, everything built on it collapses too.*

**Size**: `379` lines (`14497` bytes)

**Functions:**
- `def _plan_digest(conn, claim_ids, source_ids)` - *Bind exactly the rows an action will retire: any change breaks the digest.*
- `def _retraction_targets(conn, source)` - *The source plus every live twin row sharing its normalized DOI work.*
- `def dependents(conn, claim_id)` - *Return every claim that structurally depends on this claim, by depth.*
- `def preview(conn, ref)` - *Show what a collapse or retraction would retire without writing anything.*
- `def _preview_retraction(conn, ref)`
- `def _retraction_plan(conn, targets)` - *Claim ids plus display entries a retraction would read.*
- `def invalidate(conn, claim_ref, status, reason, evidence, actor, allow_bulk, preview_digest)` - *Record a failed root claim, then invalidate every dependent in one transaction.*
- `def retract_source(conn, ref, reason, evidence, actor, allow_bulk, preview_digest)` - *Retract a source and retire every empirical claim that cites it.*

---

### [`engine/claims.py`](engine/claims.py)
> *Claims: the unit of knowledge, with provenance and an append-only verdict history.*

**Size**: `588` lines (`23083` bytes)

**Functions:**
- `def _to_claim(row)`
- `def _validate_confidence(value)`
- `def add_claim(conn, research_ref, text, kind, source_ref, quote, locator, confidence, kill_test, basis, prerequisites, revision_of, revision_reason)` - *Record a claim; empirical claims must carry a verbatim quote and a locator.*
- `def get_claim(conn, ref)` - *Fetch one claim by identifier.*
- `def list_claims(conn, research_ref, status, include_superseded)` - *List claims, optionally filtered by program and verdict; hide superseded heads by default.*
- `def revision_chain(conn, ref)` - *The full revision chain, oldest first, with a cycle guard.*
- `def revise_claim(conn, ref, text, reason, source_ref, quote, locator, confidence, kill_test, basis, prerequisites, actor)` - *Append a revised claim, mark the old one superseded, and move its edges to the head.*
- `def current_groups_for_claim(conn, claim_id)` - *Verified run groups, bound to the current code and inputs, for a claim's tests.*
- `def set_verdict(conn, claim_ref, status, evidence, note, actor, evidence_group)` - *Append a verdict; promotion needs a kill test, evidence, and current numeric proof.*
- `def prerequisites(conn, claim_id)` - *Return the claims this claim structurally depends on.*
- `def link_claims(conn, src_ref, dst_ref, rel)` - *Add a typed claim-to-claim edge; dependency edges make invalidation transitive.*
- `def record_edge(conn, src_kind, src_id, dst_kind, dst_id, rel)` - *Insert one typed edge, returning the existing id when the edge is already present.*
- `def list_edges(conn, subject_ref)` - *Return every edge touching a claim, in either direction.*
- `def link_to_question(conn, claim_ref, question_ref, stance)` - *Attach a claim to a question with a stance used by the consensus score.*
- `def iter_edges(conn)` - *Yield every edge for audits that need the whole graph.*

---

### [`engine/cli.py`](engine/cli.py)
> *Command-line surface: one entry point for every engine mechanic.*

**Size**: `1464` lines (`72945` bytes)

**Functions:**
- `def _build_parser()`
- `def _emit(payload, as_json, text)`
- `def _records_payload(rows)`
- `def _need_budget(value, command)`
- `def _cmd_research(conn, args)`
- `def _cmd_question(conn, args)`
- `def _cmd_source(conn, args)`
- `def _cmd_protocol(conn, args)`
- `def _cmd_observation(conn, args)`
- `def _cmd_claim(conn, args)`
- `def _cmd_hypothesis(conn, args)`
- `def _cmd_test(conn, args)`
- `def _ensure_outside_repo(path_str)` - *Refuse model I/O files that live inside the project checkout.*
- `def _cmd_ai(conn, args)`
- `def main(argv)` - *Parse one command, open the database, and dispatch it.*

---

### [`engine/context.py`](engine/context.py)
> *Token-budgeted views: the same graph, measured in tokens for an agent reader.*

**Size**: `192` lines (`7536` bytes)

**Classes:**
- `class View` - *A rendered, bounded view of one program.*
  - Method `.to_dict()`

**Functions:**
- `def estimate_tokens(text)` - *A stable, provider-agnostic estimate: roughly four characters per token.*
- `def _clip(text, width)` - *Shorten one safe line without exceeding the width.*
- `def pack(lines, budget)` - *Fit lines into a budget, always keeping the first, and count what was dropped.*
- `def _render(lines, budget)`
- `def _status_counts(conn, research_id)`
- `def outline(conn, research_ref, budget)` - *One line per question, hypothesis and test, with counts instead of text.*
- `def brief(conn, research_ref, budget)` - *Per question: consensus, the strongest support, and the strongest contradiction.*
- `def claim_brief(conn, claim_ref, budget)` - *One claim, its provenance, its premises and its verdicts, bounded.*

---

### [`engine/database.py`](engine/database.py)
> *SQLite connection, schema versioning and atomic transactions.*

**Size**: `557` lines (`21352` bytes)

**Functions:**
- `def connect(path)` - *Open a database with durability pragmas suitable for a state file.*
- `def _ensure_indexes(conn)` - *Create indexes that depend on migrated columns; safe to run after every migration.*
- `def _add_missing_columns(conn, version)` - *Apply the additive column migrations for one older schema version.*
- `def initialize(conn)` - *Create the schema, migrate an older one, and refuse a future version.*
- `def _count_unbound_numeric(conn)` - *Numeric claims whose promotion verdict predates evidence binding.*
- `def transaction(conn)` - *Run a write atomically; nested calls join the outer transaction.*
- `def next_id(conn, prefix)` - *Allocate a readable, gap-free identifier inside the current transaction.*

---

### [`engine/demo.py`](engine/demo.py)
> *A self-contained demonstration of every engine mechanic in under ten seconds.*

**Size**: `153` lines (`5481` bytes)

**Functions:**
- `def seed_demo(conn)` - *Create one synthetic program that exercises provenance, tests, and cascade.*

---

### [`engine/diffing.py`](engine/diffing.py)
> *Snapshot comparison: what changed between two exported graphs.*

**Size**: `123` lines (`4746` bytes)

**Functions:**
- `def load_jsonl(path)` - *Read an export, dropping its meta line; a malformed file is refused.*
- `def _key(record)` - *Identity of a record: its id, or a digest of a projection that has no id.*
- `def _strip(record)`
- `def _index(records, semantic)` - *Index records by type and identity, optionally collapsing run churn.*
- `def diff_records(old, new, semantic)` - *Compare two record sets and classify added, removed and changed records.*
- `def diff_files(old, new, semantic)` - *Compare two exported snapshots.*
- `def render(result)` - *Render a diff as a compact, deterministic report.*

---

### [`engine/duplicates.py`](engine/duplicates.py)
> *Duplicate-source detection by normalized DOI and title.*

**Size**: `134` lines (`4517` bytes)

**Functions:**
- `def normalize_doi(value)` - *Strip resolver prefixes and case-fold a DOI so two spellings compare equal.*
- `def normalize_title(value)` - *Fold accents, case and punctuation while keeping letters from every script.*
- `def _group(items, reason, key)`
- `def duplicate_sources(conn, research_ref, limit)` - *Return groups of sources that share a DOI, a normalized title/year, or a title variant.*

---

### [`engine/errors.py`](engine/errors.py)
> *Error types that carry a cause and a concrete repair step (Why/Fix triad).*

**Size**: `35` lines (`1015` bytes)

**Classes:**
- `class EngineError` - *A user-facing failure with a reason and a repair step.*
  - Method `.__init__(message, why, fix)`
  - Method `.render()`
- `class NotFound` - *A referenced record does not exist.*
  - Method `.__init__(kind, ref)`

---

### [`engine/events.py`](engine/events.py)
> *Append-only event log for actions that are not verdicts.*

**Size**: `283` lines (`9637` bytes)

**Classes:**
- `class Event`

**Functions:**
- `def event_hash_for(event)` - *The tamper-evident digest of one event, chained to its predecessor.*
- `def _stored_tip(conn, research_id)`
- `def verify_ledger(conn, research_id)` - *Replay one program's event chain; every break is an (event id, reason) pair.*
- `def _to_event(row)`
- `def record(conn, kind, subject, detail, research_id, actor, parent_id)` - *Append one event. Callers run inside their own write transaction.*
- `def list_events(conn, research_ref, kind, limit)` - *Recent events, newest first, optionally filtered by program and kind.*
- `def count(conn)` - *Total recorded events.*
- `def _one_event(conn, ref)`
- `def event_path(conn, ref)` - *The causal chain from the root event to one event, root first.*
- `def event_tree(conn, ref)` - *A root event and its descendants, breadth-first with a depth per event.*

---

### [`engine/evidence.py`](engine/evidence.py)
> *Evidence identity: which verified run groups are valid for a test right now.*

**Size**: `221` lines (`8354` bytes)

**Functions:**
- `def test_inputs(test)` - *The canonical declared input names of a test.*
- `def binding(test)` - *The identity a run must carry to count as evidence now.*
- `def _groups(conn, test_id, exact, current)` - *Verified main-role groups for one test, newest first, optionally binding-filtered.*
- `def verified_groups(conn, test_id)` - *Every historical main-role group that passed twice with identical output.*
- `def current_verified_groups(conn, test, current)` - *Every main-role group valid for the current code, inputs and command, newest first.*
- `def current_verified_group(conn, test)` - *The newest group valid for the current binding, if any.*
- `def control_state(conn, test, group)` - *Whether the declared control was falsified in one run group.*
- `def authoritative_attempt(conn, test)` - *The earliest non-replaceable attempt bound to the test's current identity.*
- `def authoritative_group(conn, test)` - *The authoritative group when that attempt is also a currently verified group.*
- `def authority_blocked(conn, test)` - *The reason a later pass cannot be promoted, when the authority is a subject failure.*
- `def _claim_tests(conn, claim_id)`
- `def claim_groups(conn, claim_id)` - *Current verified groups across every test bound to a claim.*
- `def claim_authority_blocked(conn, claim_id)` - *The first subject-failure authority across a claim's tests, if any.*
- `def claim_has_historical_evidence(conn, claim_id)` - *Whether any test bound to a claim ever produced a verified group.*
- `def claim_tests(conn, claim_id)` - *Every test bound to a claim.*

---

### [`engine/hypotheses.py`](engine/hypotheses.py)
> *Pre-registered hypotheses and their outcomes (the K13 discipline).*

**Size**: `249` lines (`9334` bytes)

**Functions:**
- `def _to_hypothesis(row)`
- `def add_hypothesis(conn, research_ref, statement, criterion, confidence, question_ref)` - *Pre-register a prediction before any outcome is known.*
- `def get_hypothesis(conn, ref)` - *Fetch one hypothesis by identifier.*
- `def list_hypotheses(conn, research_ref)` - *List hypotheses, optionally filtered by program.*
- `def record_outcome(conn, hypothesis_ref, outcome, evidence, note, actor)` - *Close a pre-registered hypothesis with an evidence-backed outcome.*
- `def amend_hypothesis(conn, hypothesis_ref, reason, statement, criterion, actor)` - *Correct a pre-registered hypothesis; the original registration is kept.*
- `def preregistration_card(conn, hypothesis_ref)` - *Render the pre-registration card an agent writes before searching.*

---

### [`engine/information.py`](engine/information.py)
> *Cheap information-quality checks over stored claim quotes.*

**Size**: `62` lines (`2271` bytes)

**Functions:**
- `def normalize(text)` - *Fold case and punctuation so two quotes compare on their words.*
- `def content_terms(text)` - *Words that carry information, excluding the small English stopword set.*
- `def restates_question(quote, questions)` - *Whether the quote is a substring of a question it is supposed to answer.*
- `def duplicate_quote(quote, other_quotes)` - *Whether the same quote already supports another claim in the same program.*
- `def stopword_only(quote)` - *Whether the quote has no content terms at all.*
- `def quote_classes(quote, questions, other_quotes)` - *Return the stable, additive information classes of one quote.*

---

### [`engine/integrity.py`](engine/integrity.py)
> *Graph integrity: provenance, evidence paths, dependency acyclicity and stale dependents.*

**Size**: `934` lines (`35534` bytes)

**Functions:**
- `def _finding(code, severity, subject, message, fix)`
- `def _entity(conn, kind, ref)`
- `def _cycles(conn, relations)`
- `def _missing_inputs(tests)` - *Declared input files that no longer exist, resolved exactly like the fingerprint.*
- `def _quote_quality(conn)` - *Warn when a live quote restates a question, duplicates another quote, or is empty.*
- `def check(conn)` - *Return every integrity finding; an empty list means the graph is coherent.*
- `def has_errors(findings)` - *Return True when at least one finding blocks a verdict.*
- `def render_markdown(findings)` - *Render findings as a compact audit table.*
- `def render_json(findings)` - *Render findings as stable machine-readable JSON.*
- `def findings_for_research(conn, research_id)` - *Findings attributable to one program: its own records, edges and the program itself.*

---

### [`engine/killtests.py`](engine/killtests.py)
> *Executable kill tests: two agreeing runs, bound to code, inputs and command.*

**Size**: `405` lines (`14976` bytes)

**Functions:**
- `def _to_test(row)`
- `def _to_run(row)`
- `def add_test(conn, research_ref, name, command, claim_ref, hypothesis_ref, expect_exit, timeout_seconds, inputs, control_command)` - *Register an executable test bound to a claim, a hypothesis, its inputs and a control.*
- `def get_test(conn, ref)` - *Fetch one test by identifier.*
- `def list_tests(conn, research_ref)` - *List tests, optionally filtered by program.*
- `def _terminate_tree(process)` - *Kill the process and its children without leaking a detached tree.*
- `def _run_once(command, timeout_seconds)` - *Run one command in the project root and capture a deterministic fingerprint.*
- `def _classify_attempt(results, control, runs, before, after)` - *Classify one execution into the attempt vocabulary, conservatively.*
- `def run_test(conn, test_ref, runs)` - *Run a test one or more times, plus its negative control, recording each run's identity.*
- `def _execute(conn, test, command, group, runs, role, tag_prefix, current, commit, dirty, runtime)` - *Execute one command `runs` times and persist every run under its role.*
- `def _summarise_control(results, expect_exit)` - *A control is falsified when every repetition fails the expectation identically.*
- `def verify_test(conn, test_ref)` - *Run a test twice in separate processes; disagreement or drift is a failure.*
- `def list_runs(conn, test_ref, limit)` - *List recent runs, optionally for one test.*

---

### [`engine/maintenance.py`](engine/maintenance.py)
> *Database maintenance: integrity verification and a crash-safe backup.*

**Size**: `109` lines (`4245` bytes)

**Functions:**
- `def integrity_check(conn)` - *Run SQLite's own checks plus a few facts a reviewer wants before archiving.*
- `def _refuse_if_exists(target, because)` - *Refuse to clobber an existing backup target.*
- `def backup(conn, destination)` - *Copy the live database through SQLite's backup API and verify the copy.*

---

### [`engine/manifest.py`](engine/manifest.py)
> *Generated-report manifests and drift detection.*

**Size**: `172` lines (`6698` bytes)

**Functions:**
- `def license_block()` - *Identify the terms the generated artifact is offered under, by id and text digest.*
- `def manifest_path(report_path)` - *The sidecar path for a report, accepting a report or a manifest path.*
- `def build_manifest(conn, research_ref, text)` - *Describe one generated report: schema, digests, counts, findings and limits.*
- `def write_report(conn, research_ref, path)` - *Write the report and its manifest atomically; return both paths and the digests.*
- `def _load_manifest(sidecar)` - *Read a manifest and refuse an unknown schema.*
- `def check_report(conn, research_ref, path, strict)` - *Compare a committed report and its manifest with the current graph.*

---

### [`engine/markdown.py`](engine/markdown.py)
> *Markdown-safe rendering of untrusted text.*

**Size**: `46` lines (`1727` bytes)

**Functions:**
- `def sanitize(text, width)` - *Collapse to one safe line: no control characters, no newlines, capped width.*
- `def cell(text, width)` - *A Markdown table cell: sanitized, with pipe and backtick escaped.*
- `def bullet(text, width)` - *One list or heading fragment: sanitized, with backticks escaped.*
- `def code(text, width)` - *A fenced inline code fragment safe for a single-line context.*

---

### [`engine/merging.py`](engine/merging.py)
> *Claim merging: one survivor, every edge repointed, duplicates retired.*

**Size**: `151` lines (`5780` bytes)

**Functions:**
- `def merge_claims(conn, keep_ref, drop_refs, note, actor)` - *Keep one claim, repoint edges from the duplicates, and retire the duplicates.*

---

### [`engine/migrations.py`](engine/migrations.py)
> *Migration harness for lattice and N1 source databases.*

**Size**: `604` lines (`20896` bytes)

**Classes:**
- `class MigrationReport` - *What one inspection or application observed and inserted.*
  - Method `.as_dict()`

**Functions:**
- `def _file_digest(path)`
- `def _read_only(path)` - *Open a source database with SQLite's read-only URI mode.*
- `def _table_count(conn, table)`
- `def _inspect(path, source, tables)`
- `def inspect_lattice(path)` - *Describe a lattice database without writing to it.*
- `def inspect_n1(path)` - *Describe an N1 database without writing to it.*
- `def inspect_research(path)` - *Describe a host research database without writing to it.*
- `def inspect_tree(path, source, suffixes, excluded_dirs)` - *Fingerprint a source tree and count files by suffix.*
- `def inspect_obezite(path)` - *Describe the obezite Markdown claim ledger without writing to it.*
- `def applied_migrations(conn)` - *List migration runs in application order.*
- `def _refuse_repeat(conn, source, digest)`
- `def _year(value)`
- `def _text(value)`
- `def _claim_kind(row)`
- `def _as_date(value)`
- `def _as_timestamp(value)`
- `def _lattice_rows(path)`
- `def _n1_rows(path)`
- `def _lattice_screening(screening_rows)`
- `def _record_migration(conn, report, mapping)`
- `def migrate_lattice(conn, research_ref, path, dry_run)` - *Import a lattice snapshot into one host program without touching the source.*
- `def migrate_n1(conn, research_ref, path, dry_run)` - *Import an N1 snapshot into one host program without touching the source.*

---

### [`engine/models.py`](engine/models.py)
> *Frozen domain records and the engine's closed vocabularies.*

**Size**: `279` lines (`6107` bytes)

**Classes:**
- `class Research`
- `class Source`
- `class Question`
- `class Claim`
- `class Hypothesis`
- `class KillTest`
- `class TestRun`
- `class Attempt`
  - Method `.to_dict()`
- `class AIArtifact`
- `class Observation`
- `class Protocol`
- `class Finding`
- `class AnalysisPlan`
- `class Amendment`

---

### [`engine/observations.py`](engine/observations.py)
> *Recorded observations: the raw measurements a numeric claim is computed from.*

**Size**: `483` lines (`18632` bytes)

**Classes:**
- `class _DryRunComplete` - *Carry validated counts out of a rolled-back dry-run transaction.*
  - Method `.__init__(imported, skipped)`

**Functions:**
- `def _to_observation(row)`
- `def add_observation(conn, claim_ref, group_label, value, note, at, instrument_kind, instrument_id, instrument_digest, rater_kind, rater_id, rater_version, protocol_id, sample_size, aggregation, unit, provenance_class, producer_path, producer_digest)` - *Record one measurement in a named group; non-finite values are refused.*
- `def get_observation(conn, ref)` - *Fetch one observation by identifier.*
- `def list_observations(conn, claim_ref, group_label, include_voided)` - *Observations of a claim, oldest first, excluding voided rows by default.*
- `def void_observation(conn, ref, reason, actor)` - *Retire a measurement without deleting it; the reason stays in the record.*
- `def group_values(conn, claim_ref)` - *Non-voided values per group, in insertion order.*
- `def group_values_window(conn, claim_ref, since, until)` - *Non-voided values per group in insertion order, optionally bounded by record time.*
- `def import_observations_csv(conn, claim_ref, path, actor, dry_run)` - *Bulk-record measurements from a CSV file with per-row error isolation.*

---

### [`engine/packs.py`](engine/packs.py)
> *Domain-pack registry: declared boundaries, never cross-domain imports.*

**Size**: `142` lines (`4889` bytes)

**Classes:**
- `class Pack`

**Functions:**
- `def _to_pack(row)`
- `def register_pack(conn, name, version, api_version, data_root, manifest_sha256, status)` - *Register one domain pack; the name is the isolation boundary.*
- `def get_pack(conn, name)`
- `def list_packs(conn)`
- `def set_pack_status(conn, name, status)` - *Enable or disable a pack without deleting its registration.*

---

### [`engine/plans.py`](engine/plans.py)
> *Pre-registered analysis plans: comparisons declare their prediction first.*

**Size**: `119` lines (`4189` bytes)

**Functions:**
- `def _to_plan(row)`
- `def add_plan(conn, claim_ref, baseline, treatment, prediction, actor)` - *Pre-register what a comparison is expected to show, before it runs.*
- `def get_plan(conn, ref)` - *Fetch one analysis plan by identifier.*
- `def list_plans(conn, claim_ref)` - *Plans in record order, optionally filtered to one claim.*
- `def match_plan(conn, claim_id, baseline, treatment)` - *Plans preregistered for exactly this claim and group pair.*

---

### [`engine/protocols.py`](engine/protocols.py)
> *Measurement protocol registry.*

**Size**: `188` lines (`6814` bytes)

**Functions:**
- `def _to_protocol(row)`
- `def register_protocol(conn, protocol_id, measures, includes_generation, includes_judge, doc_digest, doc_path, actor)` - *Register an immutable protocol id; re-registering the same id is refused.*
- `def get_protocol(conn, ref)` - *Fetch one registered protocol by id.*
- `def amend_protocol(conn, ref, measures, reason, actor)` - *Correct a protocol's measures text; the pin and digest never move.*
- `def list_protocols(conn)` - *Every registered protocol, oldest id first.*

---

### [`engine/provenance.py`](engine/provenance.py)
> *Workspace provenance: the code and input identity a test run or report is bound to.*

**Size**: `187` lines (`6107` bytes)

**Classes:**
- `class Fingerprint` - *Identity of the engine code and the declared inputs.*
  - Method `.to_dict()`

**Functions:**
- `def _digest(entries)` - *Hash `(name, kind, content)` triples with length prefixes.*
- `def code_sha256()` - *Hash the engine package; the test harness and prose are deliberately excluded.*
- `def _inside(path)`
- `def _name_for(path, raw)` - *A stable name: project-relative when possible, otherwise the raw declaration.*
- `def _expand(raw)` - *Expand one declaration into canonical names, deterministically.*
- `def resolve_inputs(paths)` - *Canonical, sorted, de-duplicated input names for a declaration list.*
- `def inputs_sha256(paths)` - *Hash declared inputs; an absent declaration hashes as a distinct typed marker.*
- `def fingerprint(inputs)` - *Compute the current code and input fingerprint.*
- `def git_state()` - *Return `(commit, dirty)`; a missing repository reports `no-git` and dirty.*
- `def environment()` - *Runtime identity recorded for diagnosis, not used for binding.*
- `def provenance(inputs)` - *One block combining binding data with diagnostic metadata.*

---

### [`engine/questions.py`](engine/questions.py)
> *Research questions that collect supporting and contradicting claims.*

**Size**: `73` lines (`2726` bytes)

**Functions:**
- `def _to_question(row)`
- `def add_question(conn, research_ref, text)` - *Add an open question to a program.*
- `def get_question(conn, ref)` - *Fetch one question by identifier.*
- `def list_questions(conn, research_ref)` - *List questions, optionally filtered by program.*
- `def close_question(conn, ref)` - *Mark a question resolved without deleting its evidence.*

---

### [`engine/researches.py`](engine/researches.py)
> *Research programs: the top-level containers the engine is asked to investigate.*

**Size**: `92` lines (`3486` bytes)

**Functions:**
- `def _slugify(conn, title)`
- `def _to_research(row)`
- `def create_research(conn, title, scope, slug)` - *Create a research program with a stable, unique slug.*
- `def get_research(conn, ref)` - *Resolve a program by identifier or slug.*
- `def list_researches(conn)` - *List programs in creation order.*
- `def research_counts(conn, research_id)` - *Return the record counts that summarise a program.*

---

### [`engine/screening.py`](engine/screening.py)
> *Source screening and the PRISMA flow.*

**Size**: `114` lines (`4319` bytes)

**Functions:**
- `def set_screening(conn, ref, status, reason, actor)` - *Record one screening decision; an out-status always carries a reason.*
- `def prisma_flow(conn, research_ref)` - *Counts and exclusion reasons across the review phases.*
- `def unscreened_sources(conn, research_ref)` - *Sources still in the identified state, oldest first.*

---

### [`engine/search.py`](engine/search.py)
> *Deterministic lexical search over the recorded graph.*

**Size**: `226` lines (`8252` bytes)

**Functions:**
- `def _terms(query)` - *Case-folded query terms, de-duplicated and stripped of one-character noise.*
- `def _score(needle, terms, blob, primary)` - *Phrase-first relevance: exact phrase, primary field, then matched terms.*
- `def _snippet(text, needle, terms, width)` - *A one-line window around the earliest match, with visible cut marks.*
- `def _fields(kind, row)` - *Primary and supporting text for one record, in match-priority order.*
- `def _rows(conn, kind, research_id, include_superseded)` - *Program-scoped rows for one kind, in stable identifier order.*
- `def search(conn, query, research_ref, kinds, limit, include_superseded, budget)` - *Rank one query across the graph and return matches with a matched-field snippet.*

---

### [`engine/sources.py`](engine/sources.py)
> *Bibliographic sources: the only place literature text may enter the graph.*

**Size**: `173` lines (`6090` bytes)

**Functions:**
- `def _to_source(row)`
- `def add_source(conn, research_ref, title, year, doi, url, authors, kind, arxiv, venue, abstract, tags, study_type)` - *Register a source; claims cannot cite it before it exists.*
- `def get_source(conn, ref)` - *Fetch one source by identifier.*
- `def list_sources(conn, research_ref)` - *List sources, optionally filtered by program.*
- `def set_source_status(conn, ref, status, note, actor)` - *Change a source's evidence status without deleting the record.*

---

### [`engine/stats.py`](engine/stats.py)
> *Deterministic statistics for recorded observations.*

**Size**: `358` lines (`13460` bytes)

**Functions:**
- `def sample_sd(values)` - *Sample standard deviation; zero for fewer than two values.*
- `def cohens_d(baseline, treatment)` - *Standardized mean difference using the pooled standard deviation.*
- `def _betacf(a, b, x)` - *Continued fraction for the incomplete beta function (modified Lentz).*
- `def _betai(a, b, x)` - *Regularized incomplete beta I_x(a, b).*
- `def t_two_sided_p(t, df)` - *Two-sided p-value for a t statistic with the given degrees of freedom.*
- `def welch_t(baseline, treatment)` - *Welch's unequal-variance t test, with the zero-variance case handled explicitly.*
- `def _ranks(values)` - *Average ranks for ties, returning the ranks and the tie-group sizes.*
- `def _u_distribution(n1, n2)` - *Counts of the U statistic under the null, by dynamic programming.*
- `def _exact_u_two_sided_p(u1, n1, n2)` - *Exact two-sided p for the U statistic when the sample is small and untied.*
- `def mann_whitney(baseline, treatment)` - *Mann-Whitney U: exact for small untied samples, continuity-corrected asymptotic otherwise.*
- `def holm_adjust(p_values)` - *Holm step-down adjustment for a family of p-values, in standard-library code.*
- `def bootstrap_ci(baseline, treatment, seed, resamples)` - *Percentile bootstrap interval for the difference in means, reproducibly seeded.*
- `def pearson(xs, ys)` - *Pearson product-moment correlation for paired samples, stdlib-only.*
- `def linregress(xs, ys)` - *Least-squares slope, intercept, correlation and two-sided p for paired points.*
- `def compare_groups(baseline, treatment, seed, resamples)` - *Compare two recorded groups and state the result, the agreement and the caveats.*

---

### [`engine/synthesis.py`](engine/synthesis.py)
> *Evidence synthesis: weighted consensus, contradiction pairs, and generated reports.*

**Size**: `479` lines (`19723` bytes)

**Functions:**
- `def stance_claims(conn, question_id)`
- `def consensus(conn, question_ref)` - *Confidence-weighted support minus contradiction in [-1, 1].*
- `def coverage(conn, question_ref)` - *Tested fraction and source breadth behind a question's stances.*
- `def consensus_display(conn, question_ref)` - *The reportable consensus: a number with coverage, or an explicit refusal.*
- `def _contradictions(conn, question_id)`
- `def _provenance_cell(conn, row)`
- `def _verdict_count(conn, research_id)` - *Verdicts adjudicating this program's claims or hypotheses.*
- `def report(conn, research_ref)` - *Render a full, reproducible research report from the graph.*
- `def scorecard(conn, research_ref)` - *Render one line per claim, ordered by status then identifier.*
- `def claim_detail(conn, claim_ref)` - *Render one claim with provenance, dependencies, verdicts and linked tests.*
- `def inventory(conn)` - *Return engine-wide counts used by the CLI overview.*

---

### [`experiments/__init__.py`](experiments/__init__.py)
> *N1 experiment records and baseline-vs-intervention analysis.*

**Size**: `37` lines (`801` bytes)

---

### [`experiments/analysis.py`](experiments/analysis.py)
> *Baseline-vs-intervention analysis for N1 experiment records.*

**Size**: `249` lines (`8938` bytes)

**Functions:**
- `def _start_date(value)`
- `def _days(value, field)`
- `def _summary(rows)`
- `def _trend(rows)`
- `def _window_warnings(baseline, intervention, baseline_days, intervention_days)`
- `def analyze_baseline_vs_intervention(conn, research_ref, metric_name, start_date, baseline_days, intervention_days)` - *Compare one metric before and after the declared intervention start.*
- `def analyze_multiple_metrics(conn, research_ref, metric_names, start_date, baseline_days, intervention_days)` - *Analyze several metrics and report the multiple-comparison risk as a global warning.*

---

### [`experiments/importer.py`](experiments/importer.py)
> *CSV import for N1 metric entries, using the host experiment model.*

**Size**: `58` lines (`2146` bytes)

**Functions:**
- `def import_metrics_csv(conn, research_ref, path, intervention_ref)` - *Import ``date,metric_name,value[,note]`` rows; bad rows are counted, not fatal.*

---

### [`experiments/models.py`](experiments/models.py)
> *Experiment records: N1 interventions, metric definitions, measurements and events.*

**Size**: `413` lines (`13219` bytes)

**Classes:**
- `class Intervention`
- `class MetricDefinition`
- `class MetricEntry`
- `class EventEntry`

**Functions:**
- `def _date(value, field)`
- `def _timestamp(value)`
- `def _finite(value)`
- `def _intervention(conn, research_id, ref)`
- `def add_intervention(conn, research_ref, name, start_date, projected_end_date, end_date, dosage, notes)`
- `def add_metric_definition(conn, research_ref, name, description, unit)`
- `def add_metric(conn, research_ref, metric_name, date_value, value, intervention_ref, note)`
- `def add_event(conn, research_ref, event_name, timestamp, severity, notes, intervention_ref)`
- `def _rows(conn, sql, params)`
- `def list_interventions(conn, research_ref)`
- `def list_metric_definitions(conn, research_ref)`
- `def list_metrics(conn, research_ref, metric_name, intervention_ref)`
- `def list_events(conn, research_ref)`

---

### [`studio/__init__.py`](studio/__init__.py)
> *Studio surfaces: web, MCP and HTTP API.*

**Size**: `1` lines (`46` bytes)

---

### [`studio/api.py`](studio/api.py)
> *Stable public Python surface for host integrations such as neurocore.*

**Size**: `361` lines (`9724` bytes)

**Functions:**
- `def _question_key(value)` - *Normalize `question:q_000001` or `q_000001` to the bare identifier.*
- `def get_evidence_matrix(repository, question_ids)` - *The Paper x Question matrix, optionally narrowed to selected research questions.*
- `def get_hypothesis_evidence(repository, question_id)` - *Evidence grouped by role (supports, contradicts, answers, other) for one question.*

---

### [`studio/client.py`](studio/client.py)
> *Turnkey client facade for AI hosts: own one connection, call MCP-parity tools.*

**Size**: `400` lines (`18428` bytes)

**Classes:**
- `class LatticeClient` - *A synchronous, context-managed graph client with MCP tool parity.*
  - Method `.__init__(db_path, read_only)`
  - Property `.repository` - *The underlying repository for advanced writable callers.*
  - Method `.__enter__()`
  - Method `.__exit__(exc_type, exc, traceback)`
  - Method `.close()` - *Close the owned connection; safe to call more than once.*
  - Method `._ensure_open()`
  - Method `.tool_schemas()` - *The MCP tool declarations, filtered to the read-only set when requested.*
  - Method `.resource_schemas()` - *A deep copy of the advertised MCP resource declarations.*
  - Method `.prompt_schemas()` - *A deep copy of the advertised MCP prompt declarations.*
  - Method `.read_resource(uri)` - *Read one advertised resource such as `lattice://stats`.*
  - Method `.get_prompt(name, arguments)` - *Render one advertised prompt with its arguments.*
  - Method `.call_tool(name, arguments, **kwargs)` - *Run one MCP tool by name; arguments may be a mapping plus keyword overrides.*
  - Method `.search(query, limit, stance, min_confidence, year, tokens)`
  - Method `.discover_papers(query, source, limit, ingest)`
  - Method `.extract_claims(paper, question)`
  - Method `.get_entity(ref)`
  - Method `.neighbors(ref, kind)`
  - Method `.subgraph(ref, depth, tokens)`
  - Method `.related_findings(target, limit, tokens)`
  - Method `.outline(tokens)`
  - Method `.add_paper(metadata)`
  - Method `.add_claim(paper, text, quote, locator, stance, confidence)`
  - Method `.add_question(text)`
  - Method `.set_question_status(question, status)`
  - Method `.add_edge(src, dst, kind, note)`
  - Method `.ask(target, limit)` - *Evidence-first question answering, including search mode outside MCP.*
  - Method `.brief(target, tokens)`
  - Method `.review(target)`
  - Method `.synthesize(target, tokens)`
  - Method `.analyze_graph(auto_link, limit)`
  - Method `.detect_contradictions(auto_link)`
  - Method `.export_snapshot(path)`
  - Method `.export_graphml(path)` - *Export the evidence graph in standard GraphML XML format.*
  - Method `.export_cytoscape(path)` - *Export the evidence graph in Cytoscape.js JSON format.*
  - Method `.sync_article(article_data, auto_extract)` - *Sync a NeuroCore or external article dict into the evidence graph.*
  - Method `.import_snapshot(path)`
  - Method `.diff_snapshot(old_path, new_path)` - *Diff a baseline snapshot against another snapshot or the live graph.*
  - Method `.find_path(src, dst, max_depth, directed, edge_kinds)` - *Find the shortest chain of relations connecting two entities via BFS.*
  - Method `.propose_hypotheses(question, limit)` - *Formulate testable hypotheses from evidence gaps and contradiction clusters.*
  - Method `.screen_paper(paper_id, status, reason, notes)` - *Record an auditable PRISMA 2020 screening decision for a paper.*
  - Method `.get_prisma_flow(format)` - *Get PRISMA 2020 review attrition metrics and flow diagram.*
  - Method `.get_context_pack(targets, max_tokens, format)` - *Generate a token-bounded GraphRAG context pack for LLM reasoning.*
  - Method `.compute_meta_analysis(studies, question, model, format)` - *Execute quantitative meta-analysis and generate forest plot.*
  - Method `.stats()`
- `class AsyncLatticeClient` - *An asyncio facade that serializes the sync client on one dedicated thread.*
  - Method `.__init__(db_path, read_only)`
  - Method `async def .__aenter__()`
  - Method `async def .__aexit__(exc_type, exc, traceback)`
  - Method `async def .close()` - *Close the owned connection and stop the worker thread.*
  - Method `._ensure_open()`
  - Property `.repository` - *The repository is sync-only; exposing it would cross the worker thread.*
  - Method `async def ._run(func, *args, **kwargs)`
  - Method `async def .tool_schemas()`
  - Method `async def .resource_schemas()`
  - Method `async def .prompt_schemas()`
  - Method `async def .read_resource(uri)`
  - Method `async def .get_prompt(name, arguments)`
  - Method `async def .call_tool(name, arguments, **kwargs)`
  - Method `.__getattr__(name)`

---

### [`studio/mcp.py`](studio/mcp.py)
> *A dependency-free MCP stdio server exposing the graph as JSON-RPC tools.*

**Size**: `540` lines (`27270` bytes)

**Functions:**
- `def _tool(name, description, properties, required)` - *An MCP tool declaration with a JSON Schema for its arguments.*
- `def handle_message(repository, message)` - *Dispatch one JSON-RPC message; notifications return None.*
- `def _call_tool(repository, request_id, params)` - *Run one MCP tool call and wrap the result as text content.*
- `def read_resource(repository, uri)` - *Return the payload for one advertised resource URI.*
- `def get_prompt(repository, name, arguments)` - *Render one advertised prompt into MCP message content.*
- `def _read_resource(repository, request_id, params)` - *Return an MCP resource payload by URI.*
- `def _get_prompt(repository, request_id, params)` - *Render a structured scientific synthesis prompt for an AI agent.*
- `def dispatch_tool(repository, name, arguments)` - *Map a tool name to its repository, discovery, extraction or synthesis operation.*
- `def _text(arguments, name)` - *A required string argument.*
- `def _int(arguments, name, default)` - *An optional integer argument that fails with the Error/Why/Fix triad.*
- `def _result(request_id, result)` - *A JSON-RPC success response.*
- `def _error(request_id, code, message)` - *A JSON-RPC error response.*
- `def serve(repository, stdin, stdout)` - *Serve newline-delimited JSON-RPC until the input stream closes.*

---

### [`studio/web.py`](studio/web.py)
> *Zero-dependency web server and human-friendly Research Studio UI for Lattice.*

**Size**: `2438` lines (`100831` bytes)

**Classes:**
- `class WebResponse` - *Immutable HTTP response returned by `dispatch_web_request`.*

**Functions:**
- `def dispatch_web_request(repository, method, path, body)` - *Route an HTTP method and path to the UI or JSON API without network sockets.*
- `def _dispatch_post(repository, route, payload)` - *Handle JSON POST routes for mutations, discovery, extraction, and demo seeding.*
- `def _build_overview(repository)` - *Assemble full workspace state for the Human UI dashboard.*
- `def _handle_search(repository, query)` - *Run filtered search from query parameters.*
- `def _handle_literature(repository, query)` - *Search the literature by tags, words, sentences, study type and year.*
- `def _handle_subgraph(repository, query)` - *Run multi-hop subgraph traversal from query parameters.*
- `def _handle_path(repository, query)` - *Run relation path search between two entities from query parameters.*
- `def _handle_hypothesize(repository, query)` - *Propose structured testable hypotheses from query parameters.*
- `def _handle_synthesize(repository, query)` - *Run scientific literature synthesis from query parameters.*
- `def _handle_export_bibtex(repository, query)` - *Export papers matching query parameters as BibTeX.*
- `def _build_matrix_bundle(repository)` - *Assemble the Paper x Question evidence matrix, contradictions, and keystone ranking.*
- `def _handle_ingest_text(repository, payload)` - *Parse raw bibliography or note text (BibTeX, RIS, CSV, Markdown, text) and ingest into the graph.*
- `def _export_jsonl_string(repository)` - *Serialize all graph entities and edges as portable JSONL text.*
- `def _seed_demo(repository)` - *Populate the built-in seed corpus, create research questions, and extract claims.*
- `def _first(query, key)` - *First query parameter value or empty string.*
- `def _parse_json_body(body)` - *Parse an optional JSON request body into a dictionary.*
- `def _json_response(status, payload)` - *Serialize a dictionary as an application/json `WebResponse`.*
- `def serve_web(db_path, host, port, open_browser, once)` - *Run the local HTTP server for the Lattice Research Studio UI.*

---

### [`tests/__init__.py`](tests/__init__.py)
> *Regression shield for the research engine.*

**Size**: `1` lines (`49` bytes)

---

### [`tests/atlas/__init__.py`](tests/atlas/__init__.py)
> *Ported Atlas pack contract tests.*

**Size**: `1` lines (`40` bytes)

---

### [`tests/atlas/test_3d_flashcards.py`](tests/atlas/test_3d_flashcards.py)
> *3D export + flashcard decks (0.7.0 slice).*

**Size**: `122` lines (`4755` bytes)

**Functions:**
- `def _analysis()`
- `def test_iso_view_layers_and_skips()`
- `def test_iso_skips_boxless_entities()`
- `def test_obj_export_counts_and_groups()`
- `def test_obj_refuses_geometryless_model()`
- `def test_deck_covers_entities_and_relations(tmp_path)`
- `def test_deck_empty_refuses_anki()`
- `def test_cli_deck_and_obj(tmp_path, capsys)`
- `def test_model3d_and_flashcards_endpoints(tmp_path)`

---

### [`tests/atlas/test_autonomy.py`](tests/atlas/test_autonomy.py)
> *Upload, auto-create, models index, contract, CLI (0.5.0 autonomy slice).*

**Size**: `282` lines (`12736` bytes)

**Classes:**
- `class _FakeMuse`
  - Method `.analyze_figure(*a, **k)`
  - Method `.analyze_text(text, note, document_ref, figure_id)`
- `class _BoxlessMuse`
  - Method `.analyze_figure(*a, **k)`
- `class _RetryMuse` - *Boxless first pass, grounded retry — like a hesitant live model.*
  - Method `.__init__()`
  - Method `.analyze_figure(image_path, note, **k)`

**Functions:**
- `def _serve(tmp_path)`
- `def _post(port, path, obj)`
- `def _multipart(field, filename, data, boundary)`
- `def test_upload_then_auto_create_lists_model(tmp_path)`
- `def test_auto_create_from_url_and_epub_upload(tmp_path, monkeypatch)`
- `def test_video_without_boxes_warns_text_only(tmp_path, monkeypatch)`
- `def test_video_retries_for_grounding(tmp_path, monkeypatch)`
- `def test_upload_rejects_empty_and_missing_file(tmp_path)`
- `def test_cli_models_and_learn_offline(tmp_path, capsys)`

---

### [`tests/atlas/test_cli_video.py`](tests/atlas/test_cli_video.py)
> *CLI video regression: `video` must render (or refuse honestly), never NameError.*

**Size**: `36` lines (`1321` bytes)

**Functions:**
- `def _save(tmp_path, figure_id)`
- `def test_video_renders_offline_model(tmp_path)`
- `def test_video_unknown_figure_id_refuses_honestly(tmp_path, capsys)`

---

### [`tests/atlas/test_contract.py`](tests/atlas/test_contract.py)
> *Contract coverage: every GET endpoint the machine contract promises exists.*

**Size**: `55` lines (`2369` bytes)

**Functions:**
- `def test_every_contracted_get_endpoint_responds(tmp_path)`

---

### [`tests/atlas/test_cycle2_regressions.py`](tests/atlas/test_cycle2_regressions.py)
> *Cycle-2 regression tests for bugs found in review.*

**Size**: `74` lines (`3157` bytes)

**Functions:**
- `def test_spatial_recall_options_carry_ids()`
- `def test_select_figure_rejects_pdf_with_guidance(tmp_path)`
- `def test_muse_refuses_oversize_image(tmp_path)`
- `def test_figure_select_returns_display_url(tmp_path)`

---

### [`tests/atlas/test_demo_inline_downloads.py`](tests/atlas/test_demo_inline_downloads.py)
> *Demo inline downloads: browser-only fixture must download without a model.*

**Size**: `81` lines (`3723` bytes)

**Functions:**
- `def _post(port, path, obj)`
- `def test_inline_download_routes_serve_fixture(tmp_path)`
- `def test_demo_figure_id_still_404s_on_get(tmp_path)` - *Pins the browser-only contract: GET ?figure_id=demo is not a model.*

---

### [`tests/atlas/test_demo_integrity.py`](tests/atlas/test_demo_integrity.py)
> *Demo-data integrity: every committed real analysis and artifact stays valid.*

**Size**: `65` lines (`2436` bytes)

**Functions:**
- `def _load(name)`
- `def test_all_committed_analyses_validate()`
- `def test_tsvs_are_anki_shaped()`
- `def test_svgs_parse_and_objs_hold_cuboid_invariant()`
- `def test_report_covers_every_committed_analysis()`

---

### [`tests/atlas/test_frames.py`](tests/atlas/test_frames.py)
> *Frame quality: blank cards, duplicates, sharpness (my own viewing, automated).*

**Size**: `75` lines (`2852` bytes)

**Functions:**
- `def _img(path, color, size, noise)`
- `def test_blank_and_duplicate_frames_filtered(tmp_path)`
- `def test_low_detail_flagged_but_kept(tmp_path)`
- `def test_sharpness_orders_detail(tmp_path)`
- `def test_real_mp4_frames_analyzed()`

---

### [`tests/atlas/test_ingestion.py`](tests/atlas/test_ingestion.py)
**Size**: `32` lines (`1094` bytes)

**Functions:**
- `def _make_image(path, size)`
- `def test_import_and_select_figure(tmp_path)`
- `def test_bad_crop_rejected(tmp_path)`

---

### [`tests/atlas/test_learning_store_demo.py`](tests/atlas/test_learning_store_demo.py)
**Size**: `66` lines (`2925` bytes)

**Functions:**
- `def test_learning_modes_deterministic()`
- `def test_deck_dedupes_merged_frames()`
- `def test_spatial_recall_prefers_located_entities()`
- `def test_store_keeps_corrections_separate(tmp_path)`
- `def test_end_to_end_demo_fixture(tmp_path)`

---

### [`tests/atlas/test_materials.py`](tests/atlas/test_materials.py)
> *Materials: diagrams, 3D tours, podcast scripts, question banks (0.10.0).*

**Size**: `240` lines (`10811` bytes)

**Functions:**
- `def _analysis()`
- `def test_diagram_svg_valid_and_complete()`
- `def test_declutter_spreads_overlaps_deterministically()`
- `def test_diagram_large_text_only_grid_has_no_overlaps()`
- `def test_font_prefers_turkish_capable_truetype(tmp_path)`
- `def _two_layer_analysis()`
- `def test_diagram_poster_has_header_legend_footer()`
- `def test_brand_assets_name_the_right_project()`
- `def test_video_frames_carry_scene_counter_and_progress()`
- `def test_podcast_segments_carry_monotonic_timestamps()`
- `def test_diagram_png_opens()`
- `def test_tour_orders_layers()`
- `def test_podcast_single_entity_has_no_dangling_walk()`
- `def test_podcast_covers_entities_and_times()`
- `def test_question_bank_answers()`
- `def test_material_endpoints_and_cli(tmp_path)`
- `def test_cli_materials(tmp_path, capsys)`

---

### [`tests/atlas/test_offline_fallback.py`](tests/atlas/test_offline_fallback.py)
> *Offline no-key path: every drop becomes a real, honestly-labelled model.*

**Size**: `114` lines (`4965` bytes)

**Functions:**
- `def test_offline_builder_validates()`
- `def test_auto_create_text_without_key_uses_offline(tmp_path)`
- `def test_auto_create_image_without_key_uses_offline(tmp_path)`
- `def test_keyless_live_call_still_refuses()`
- `def test_honest_error_names_cause_and_fix()`
- `def test_extended_quality_covers_new_materials()`
- `def _break_ffmpeg(monkeypatch, mode)` - *Simulate a machine whose ffmpeg is unusable, three ways.*
- `def test_broken_ffmpeg_refuses_with_cause_and_fix(monkeypatch, mode, tmp_path)`

---

### [`tests/atlas/test_providers.py`](tests/atlas/test_providers.py)
**Size**: `78` lines (`3360` bytes)

**Functions:**
- `def _muse_transport(payload)`
- `def _sam_transport(payload)`
- `def test_muse_provider_mock(tmp_path)`
- `def test_sam_scans_raw_before_fallback(tmp_path)`
- `def test_polish_summary_bans_machine_tokens(tmp_path)`
- `def test_sam_bbox_fallback(tmp_path)`

---

### [`tests/atlas/test_quality_video.py`](tests/atlas/test_quality_video.py)
> *Automatic video + quality analysis (goal slice).*

**Size**: `123` lines (`5414` bytes)

**Functions:**
- `def _analysis()`
- `def _tiny()`
- `def _deck()`
- `def test_flashcard_quality_perfect_and_broken()`
- `def test_infographic_quality_spots_problems()`
- `def test_podcast_and_model3d_quality()`
- `def test_video_render_and_quality(tmp_path)`
- `def test_quality_and_video_endpoints_and_cli(tmp_path)`

---

### [`tests/atlas/test_schema.py`](tests/atlas/test_schema.py)
**Size**: `56` lines (`2521` bytes)

**Functions:**
- `def test_bbox_validation()`
- `def test_entity_relationship_validation()`
- `def test_analysis_rejects_dangling_relationship()`
- `def test_person_place_categories_accepted()`
- `def test_coerce_muse_payload()`

---

### [`tests/atlas/test_scope.py`](tests/atlas/test_scope.py)
> *Scope guard: Atlas is learning material, easy drag-and-drop (not figures-only).*

**Size**: `39` lines (`1327` bytes)

**Functions:**
- `def _read(rel)`
- `def test_readme_hero_is_learning_material()`
- `def test_readme_documents_drag_and_drop()`
- `def test_package_docstring_is_learning_material()`
- `def test_workspace_sub_is_learning_material()`

---

### [`tests/atlas/test_segment_loop.py`](tests/atlas/test_segment_loop.py)
> *Attach-mask endpoint + /masks/ serving tests (segmentation loop).*

**Size**: `88` lines (`3667` bytes)

**Functions:**
- `def _serve(tmp_path)`
- `def _post(port, path, obj)`
- `def _analysis()`
- `def test_attach_mask_flow_and_traversal_guard(tmp_path)`

---

### [`tests/atlas/test_sources.py`](tests/atlas/test_sources.py)
> *Universal ingestion: every source becomes learning material.*

**Size**: `365` lines (`15754` bytes)

**Classes:**
- `class _FakeResp`
  - Method `.__init__(data, ctype)`
  - Method `.read(n)`
  - Method `.__enter__()`
  - Method `.__exit__(*a)`
- `class _FakeMuseBoth`
  - Method `.analyze_text(text, note, document_ref, figure_id)`
  - Method `.analyze_figure(*a, **k)`

**Functions:**
- `def test_html_to_text_drops_boilerplate()`
- `def test_fetch_url_text_and_plain(monkeypatch)`
- `def test_youtube_transcript_parses_captions(monkeypatch)`
- `def _write_epub(path)`
- `def test_epub_text_in_spine_order(tmp_path)`
- `def test_video_without_any_ffmpeg_is_honest(tmp_path, monkeypatch)`
- `def test_video_frames_roundtrip_with_bundled_ffmpeg(tmp_path)`
- `def test_trim_text_marks_truncation()`
- `def test_coerce_allows_boxless_text_entities()`
- `def test_analyze_text_roundtrip()`
- `def test_auto_create_from_text_and_image(tmp_path)`
- `def test_scanned_pdf_error_names_pages(tmp_path)`
- `def test_pdf_render_needs_fitz_or_renders(tmp_path, monkeypatch)`
- `def test_cli_batch_reports_mixed_folder(tmp_path, capsys)`
- `def test_import_reports_pdf_pages(tmp_path)`
- `def test_chunk_text_respects_paragraphs()`
- `def test_merge_analyses_dedupes_and_remaps()`
- `def test_analyze_long_text_chunks_and_merges()`
- `def test_merge_disambiguates_reused_chunk_ids()`
- `def test_merge_frames_namespaces_ids()`

---

### [`tests/atlas/test_stage3_batch2_fixes.py`](tests/atlas/test_stage3_batch2_fixes.py)
> *Stage 3 batch 2 — failing-first guards for verified deferred findings.*

**Size**: `81` lines (`3302` bytes)

**Functions:**
- `def test_report_uses_supplied_flashcards_alias()`
- `def test_post_invalid_json_reports_parse_error(tmp_path)`
- `def test_schema_missing_keys_raise_valueerror()`

---

### [`tests/atlas/test_stage3_batch3_fixes.py`](tests/atlas/test_stage3_batch3_fixes.py)
> *Stage 3 batch 3 — failing-first guards for verified deferred findings.*

**Size**: `103` lines (`3928` bytes)

**Functions:**
- `def test_pathway_empty_model_raises()`
- `def test_confidence_rejects_str_and_bool()`
- `def _http_post_cases(monkeypatch, provider_mod, make_provider)`
- `def test_http_no_retry_on_400_retries_on_reset_muse(monkeypatch)`
- `def test_http_no_retry_on_400_retries_on_reset_sam(monkeypatch)`
- `def test_markdown_podcast_scored_gracefully()`

---

### [`tests/atlas/test_stage3_batch4_fixes.py`](tests/atlas/test_stage3_batch4_fixes.py)
> *Stage 3 batch 4 — failing-first guards for verified deferred findings.*

**Size**: `100` lines (`3968` bytes)

**Functions:**
- `def test_weird_svg_scores_not_crashes()`
- `def test_learn_bad_mode_400(tmp_path)`
- `def test_video_outdir_reuse_clean(tmp_path)`
- `def test_parallel_rel_question_ids_unique()`

---

### [`tests/atlas/test_stage3_swarm_fixes.py`](tests/atlas/test_stage3_swarm_fixes.py)
> *Stage 3 swarm fixes — failing-first guards for verified true findings.*

**Size**: `61` lines (`2249` bytes)

**Functions:**
- `def test_sam_disclosure_exists()`
- `def test_cache_key_no_concat_collision()`
- `def test_trim_text_custom_limit_message()`
- `def test_ingestion_allows_text_formats()`
- `def test_parallel_rels_unique_card_ids()`
- `def test_model3d_quality_sanitized_ids()`

---

### [`tests/atlas/test_static_wiring.py`](tests/atlas/test_static_wiring.py)
> *Static UI wiring: every element id the workspace JS touches must exist in HTML.*

**Size**: `35` lines (`1587` bytes)

**Functions:**
- `def test_every_js_referenced_id_exists_in_html()`
- `def test_static_assets_referenced_exist()`

---

### [`tests/atlas/test_study_pack.py`](tests/atlas/test_study_pack.py)
> *Auto summaries + study pack (0.8.0 slice).*

**Size**: `203` lines (`9601` bytes)

**Functions:**
- `def _analysis()`
- `def test_extractive_summary_covers_model()`
- `def test_pathway_chains_terminate_on_cycles()`
- `def test_polish_summary_roundtrip()`
- `def test_summary_arrow_format_and_hub_cap()`
- `def test_podcast_trims_big_models_with_note()`
- `def test_podcast_density_survives_many_explained_relations()`
- `def test_question_bank_covers_isolated_undescribed_entities()`
- `def test_pathways_capped_with_total()`
- `def test_podcast_coverage_respects_trim_scope()`
- `def test_selftest_passes_offline(tmp_path)`
- `def test_state_and_text_digest(tmp_path)`
- `def test_summary_endpoint_offline_and_keyless(tmp_path)`

---

### [`tests/atlas/test_vendored_text.py`](tests/atlas/test_vendored_text.py)
> *Vendored text extraction + standalone adapter tests (no sibling needed).*

**Size**: `93` lines (`3570` bytes)

**Functions:**
- `def test_txt_and_markdown_dispatch(tmp_path)`
- `def test_srt_transcript_cleaned(tmp_path)`
- `def test_json_transcript_segments(tmp_path)`
- `def test_unsupported_and_audio_errors(tmp_path)`
- `def test_pdf_empty_raises_honestly(tmp_path)`
- `def test_adapter_standalone(tmp_path)`
- `def test_external_project_env_is_ignored(tmp_path, monkeypatch)`
- `def test_providers_refuse_without_key_and_never_touch_network(tmp_path)`

---

### [`tests/atlas/test_wave1_honest_edges.py`](tests/atlas/test_wave1_honest_edges.py)
> *Wave-1 honest-error edges: non-dict entities and wrong-type podcast payloads.*

**Size**: `38` lines (`1566` bytes)

**Functions:**
- `def test_from_dict_non_dict_entity_raises_valueerror()`
- `def test_coerce_non_dict_entity_raises_valueerror()`
- `def test_quality_wrong_type_podcast_scores_zero()`

---

### [`tests/atlas/test_wave2_deck_size.py`](tests/atlas/test_wave2_deck_size.py)
> *Wave-2 regression guard: unreviewably large decks flag but don't block.*

**Size**: `27` lines (`877` bytes)

**Functions:**
- `def _cards(n)`
- `def test_large_deck_flags_but_scores_75()`
- `def test_small_deck_stays_100()`

---

### [`tests/atlas/test_wave3_tour_wrap.py`](tests/atlas/test_wave3_tour_wrap.py)
> *Wave-3 regression guards: tour duration gate and unbreakable-token split.*

**Size**: `46` lines (`1543` bytes)

**Functions:**
- `def _valid_tour(n)`
- `def test_long_tour_flags_duration_only()`
- `def test_short_tour_stays_100()`
- `def test_unbreakable_token_splits_to_frame()`

---

### [`tests/atlas/test_wave4_poster_fit.py`](tests/atlas/test_wave4_poster_fit.py)
> *Wave-4 regression guard: poster vertical centering holds the frame.*

**Size**: `27` lines (`896` bytes)

**Functions:**
- `def test_top_heavy_content_centers()`
- `def test_empty_is_noop()`
- `def test_clamp_holds_frame()`

---

### [`tests/atlas/test_wave5_honest_floors.py`](tests/atlas/test_wave5_honest_floors.py)
> *Wave-5 regression guards: boxless honesty and quality floors.*

**Size**: `29` lines (`1100` bytes)

**Functions:**
- `def test_boxless_spatial_refuses_with_text_route()`
- `def test_weakest_and_floor_surface_weak_artifact()`

---

### [`tests/lattice/__init__.py`](tests/lattice/__init__.py)
> *Ported lattice contract tests.*

**Size**: `1` lines (`37` bytes)

---

### [`tests/lattice/test_analysis.py`](tests/lattice/test_analysis.py)
> *Unit tests for scientific contradiction detection, keystone centrality, and evidence matrix analysis.*

**Size**: `400` lines (`20399` bytes)

**Classes:**
- `class TestAnalysis` - *Verify contradiction detection, keystone entity ranking, and Paper x Question evidence matrix.*
  - Method `.setUp()`
  - Method `._seed_conflicting_graph()`
  - Method `.test_detect_contradictions_and_idempotent_auto_link()`
  - Method `.test_find_and_link_related_findings_is_deterministic_and_idempotent()`
  - Method `.test_related_link_requires_question_or_two_shared_keywords()`
  - Method `.test_related_linking_skips_opposing_and_already_connected_pairs()`
  - Method `.test_related_linking_caps_links_per_claim()`
  - Method `.test_related_findings_navigates_claim_paper_and_question()`
  - Method `.test_related_findings_navigation_works_before_linking()`
  - Method `.test_rank_influential_entities_returns_keystone_papers_and_claims()`
  - Method `.test_build_evidence_matrix_identifies_cells_and_coverage_gaps()`
  - Method `.test_find_path_direct_and_multihop()`
  - Method `.test_find_path_directed_vs_undirected()`
  - Method `.test_find_path_edge_kind_filter()`
  - Method `.test_find_path_disconnected_and_depth_limits()`
  - Method `.test_find_path_invalid_entities_raise()`
  - Method `.test_propose_hypotheses_contested_question()`
  - Method `.test_propose_hypotheses_coverage_gap()`
  - Method `.test_propose_hypotheses_all_and_limits()`

---

### [`tests/lattice/test_api.py`](tests/lattice/test_api.py)
> *Unit tests for the public `lattice.api` integration surface.*

**Size**: `369` lines (`14244` bytes)

**Classes:**
- `class PublicApiTests` - *Verify the facade stays complete, inert at import time and faithful.*
  - Method `.setUp()`
  - Method `.test_every_expected_symbol_is_exported()`
  - Method `.test_all_is_sorted_unique_and_resolves()`
  - Method `.test_every_public_definition_is_exported()`
  - Method `.test_reexports_are_the_original_objects()`
  - Method `.test_design_aliases_resolve_to_canonical_functions()`
  - Method `.test_get_hypothesis_evidence_returns_the_question_bundle()`
  - Method `.test_get_evidence_matrix_filters_by_hypothesis_ids()`
  - Method `.test_single_string_question_id_filters_like_a_list()`
  - Method `.test_invalid_question_identifiers_raise()`
  - Method `.test_invalid_selection_never_builds_the_matrix()`
  - Method `.test_get_evidence_matrix_filters_out_unlinked_questions()`
  - Method `.test_sync_article_from_neurocore_creates_paper_and_claims()`
  - Method `.test_sync_article_with_related_hypotheses()`

**Functions:**
- `def _definition_names(nodes)` - *Public names bound by top-level statements, including conditional blocks.*
- `def public_definitions(module_name)` - *Every public top-level name a surfaced module defines, from its AST.*

---

### [`tests/lattice/test_checks.py`](tests/lattice/test_checks.py)
> *The integrity gate catches broken provenance, endpoints, duplicates and cycles.*

**Size**: `101` lines (`4907` bytes)

**Classes:**
- `class CheckTests` - *Each test injects one defect into an otherwise clean graph.*
  - Method `.setUp()`
  - Method `.test_clean_graph_passes()`
  - Method `.test_warning_for_unlinked_claim()`
  - Method `.test_cycle_is_an_error()`
  - Method `.test_missing_endpoint_is_an_error()`
  - Method `.test_empty_quote_is_an_error()`
  - Method `.test_doi_duplicate_is_an_error()`
  - Method `.test_question_without_evidence_is_a_warning()`
  - Method `.test_missing_locator_is_an_error()`
  - Method `.test_drifted_quote_is_an_error()`
  - Method `.test_rotted_abstract_locator_is_an_error()`
  - Method `.test_reject_claim_without_locator_at_write_time()`

---

### [`tests/lattice/test_cli.py`](tests/lattice/test_cli.py)
> *End-to-end command contracts without spawning subprocesses.*

**Size**: `382` lines (`16916` bytes)

**Classes:**
- `class CliTests` - *Drive the real parser and handlers against a temporary database.*
  - Method `.setUp()`
  - Method `.run_cli(*arguments)`
  - Method `.ingest_fixture()`
  - Method `.test_related_command_reports_and_links_findings()`
  - Method `.test_init_is_idempotent()`
  - Method `.test_ingest_question_claim_link_ask()`
  - Method `.test_json_output()`
  - Method `.test_brief_and_review_file()`
  - Method `.test_check_passes_and_reports()`
  - Method `.test_user_error_prints_triad()`
  - Method `.test_search_and_stats()`
  - Method `.test_fetch_extract_synthesize_subgraph_and_snapshots()`
  - Method `.test_web_subcommand_demo_and_dump_html()`
  - Method `.test_outline_command_reports_a_cheap_index()`
  - Method `.test_compact_token_views_for_related_subgraph_and_search()`
  - Method `.test_analyze_subcommand()`
  - Method `.test_start_file_default_and_forwarding()`
  - Method `.test_cli_path_command()`
  - Method `.test_cli_hypothesize_command()`
  - Method `.test_cli_screen_and_prisma_commands()`
  - Method `.test_cli_pack_command()`
  - Method `.test_cli_meta_command()`

---

### [`tests/lattice/test_client.py`](tests/lattice/test_client.py)
> *Tests for the turnkey client facade used by AI hosts.*

**Size**: `354` lines (`17643` bytes)

**Classes:**
- `class LatticeClientTests` - *Verify lifecycle, tool parity, convenience methods and failure modes.*
  - Method `.setUp()`
  - Method `.test_context_manager_owns_and_closes_the_connection()`
  - Method `.test_close_is_idempotent()`
  - Method `.test_write_and_read_flow()`
  - Method `.test_synthesis_and_brief()`
  - Method `.test_tool_schemas_match_mcp_and_are_copies()`
  - Method `.test_call_tool_matches_mcp_tool_names()`
  - Method `.test_unknown_tool_raises_lattice_error()`
  - Method `.test_missing_argument_raises_lattice_error()`
  - Method `.test_non_mapping_arguments_raise_lattice_error()`
  - Method `.test_non_string_tool_names_raise_lattice_error()`
- `class AsyncLatticeClientTests` - *Verify the async facade serializes work on its dedicated thread.*
  - Method `async def .asyncSetUp()`
  - Method `async def .asyncTearDown()`
  - Method `async def .test_async_write_and_read_flow()`
  - Method `async def .test_async_schemas_and_call_tool()`
  - Method `async def .test_async_context_manager_closes()`
  - Method `async def .test_async_rejects_sync_repository_access()`
- `class ClientSafetyTests` - *Verify read-only policy, path validation, metadata parity and full tool coverage.*
  - Method `.test_invalid_database_paths_raise()`
  - Method `.test_whitespace_memory_sentinel_is_normalized()`
  - Method `.test_read_only_requires_an_existing_database()`
  - Method `.test_read_only_client_reads_existing_database()`
  - Method `.test_read_only_filters_schemas_and_blocks_writes()`
  - Method `.test_resource_and_prompt_parity()`
  - Method `.test_every_tool_executes_and_serializes()`
  - Method `.test_export_graphml_and_cytoscape_and_sync_article()`
- `class AsyncClientSafetyTests` - *Verify the read-only policy survives the async facade.*
  - Method `async def .test_async_read_only_filters_and_blocks_writes()`

**Functions:**
- `def seed(client)` - *Create one question, paper, claim and support edge through the client.*

---

### [`tests/lattice/test_context.py`](tests/lattice/test_context.py)
> *Unit tests for the token-budgeted, RLM-style AI context views.*

**Size**: `230` lines (`11094` bytes)

**Classes:**
- `class ContextViewTests` - *Verify compact payloads, truncation, omission counts and the budget floor.*
  - Method `.setUp()`
  - Method `.test_outline_reports_counts_questions_and_study_types()`
  - Method `.test_outline_omits_questions_over_a_small_budget()`
  - Method `.test_compact_search_truncates_items_and_reports_omissions()`
  - Method `.test_compact_related_drops_full_text_but_keeps_reasons_and_refs()`
  - Method `.test_compact_subgraph_keeps_only_edges_between_kept_nodes()`
  - Method `.test_budgets_below_the_floor_fail_with_the_triad()`
  - Method `.test_build_context_pack_markdown_and_json()`
  - Method `.test_build_context_pack_compaction_and_defaults()`
  - Method `.test_build_context_pack_with_contradictions()`

---

### [`tests/lattice/test_database.py`](tests/lattice/test_database.py)
> *Schema migration from the first release keeps an existing graph usable.*

**Size**: `148` lines (`5392` bytes)

**Classes:**
- `class MigrationTests` - *A version 1 database gains the literature metadata columns without losing papers.*
  - Method `.setUp()`
  - Method `.test_v1_database_migrates_tags_and_study_type()`
- `class ReadOnlyDatabaseTests` - *A read-only open neither creates, migrates nor writes the database.*
  - Method `.setUp()`
  - Method `.test_missing_database_is_not_created()`
  - Method `.test_invalid_paths_raise_lattice_error()`
  - Method `.test_whitespace_memory_sentinel_is_normalized()`
  - Method `.test_existing_database_is_current_and_query_only()`
  - Method `.test_in_memory_read_only_is_query_only()`
  - Method `.test_v1_database_is_not_migrated_read_only()`

---

### [`tests/lattice/test_diff.py`](tests/lattice/test_diff.py)
> *Tests for graph snapshot diffing: record comparison, snapshot pairs and live-repository diffs.*

**Size**: `193` lines (`9460` bytes)

**Classes:**
- `class DiffRecordsTests` - *The pure record comparison behind every diff entry point.*
  - Method `.test_reports_added_removed_changed_and_unchanged()`
  - Method `.test_created_at_differences_are_not_changes()`
  - Method `.test_identical_records_in_any_order_report_no_differences()`
- `class SnapshotDiffTests` - *Diff exported snapshot files and snapshots against the live repository.*
  - Method `.setUp()`
  - Method `.test_diff_snapshots_between_two_files()`
  - Method `.test_diff_snapshot_against_live_repository()`
  - Method `.test_diff_snapshot_identical_to_repository_reports_nothing()`
  - Method `.test_diff_missing_snapshot_file_fails()`
- `class DiffCliTests` - *The `diff` command against a temporary database file.*
  - Method `.setUp()`
  - Method `.run_cli(*arguments)`
  - Method `.test_diff_against_unchanged_graph_exits_zero()`
  - Method `.test_diff_against_changed_graph_exits_one_and_reports()`
  - Method `.test_diff_between_two_snapshot_files()`
  - Method `.test_diff_missing_snapshot_fails()`

**Functions:**
- `def seed_graph(repository)` - *One paper, claim, question and edge as a diffing baseline.*

---

### [`tests/lattice/test_discovery.py`](tests/lattice/test_discovery.py)
> *Tests for pluggable automated literature discovery (arXiv, Crossref, and offline corpus).*

**Size**: `228` lines (`9613` bytes)

**Classes:**
- `class DiscoveryTests` - *Verify the 4-layer discovery boundary: DTOs, registry, providers, and service DI.*
  - Method `.setUp()`
  - Method `.test_paper_candidate_is_frozen_and_converts_to_metadata()`
  - Method `.test_registry_registers_and_resolves_providers()`
  - Method `.test_arxiv_provider_parses_atom_xml()`
  - Method `.test_crossref_provider_parses_json_and_strips_jats_tags()`
  - Method `.test_openalex_provider_reconstructs_inverted_index_abstract()`
  - Method `.test_europepmc_provider_parses_biomedical_results()`
  - Method `.test_offline_provider_searches_curated_seed_catalog()`
  - Method `.test_discovery_service_ingests_and_deduplicates_across_federated_sources()`
  - Method `.test_non_integer_limit_fails_with_lattice_error()`

---

### [`tests/lattice/test_extraction.py`](tests/lattice/test_extraction.py)
> *Tests for automated knowledge creation and claim extraction from ingested papers.*

**Size**: `114` lines (`5341` bytes)

**Classes:**
- `class ExtractionTests` - *Verify deterministic sentence splitting, stance/confidence scoring, and claim/edge creation.*
  - Method `.setUp()`
  - Method `.test_split_empirical_sentences_handles_abbreviations_and_decimals()`
  - Method `.test_infer_stance_and_confidence()`
  - Method `.test_extract_from_paper_creates_claims_and_links_question()`
  - Method `.test_extract_from_paper_links_related_findings_automatically()`
  - Method `.test_extract_all_processes_every_paper_and_auto_matches_questions()`
  - Method `.test_extract_from_missing_paper_raises_lattice_error()`

---

### [`tests/lattice/test_hardening.py`](tests/lattice/test_hardening.py)
> *Wave 21 hardening: bool-safe integer triads and brief provenance.*

**Size**: `80` lines (`4021` bytes)

**Classes:**
- `class HardeningTests`
  - Method `.setUp()`
  - Method `.test_brief_question_mode_carries_locator()`
  - Method `.test_bool_integers_fail_with_lattice_error()`
  - Method `.test_string_integers_fail_with_lattice_error()`

---

### [`tests/lattice/test_ingest.py`](tests/lattice/test_ingest.py)
> *Format parsers stay dependency-free and deterministic.*

**Size**: `243` lines (`9924` bytes)

**Classes:**
- `class BibtexTests` - *BibTeX braces, authors and identifiers.*
  - Method `.test_two_entries()`
  - Method `.test_unbalanced_braces_fail()`
  - Method `.test_keywords_and_study_type_fields()`
- `class RisTests` - *RIS tag handling.*
  - Method `.test_single_record()`
  - Method `.test_keywords_and_study_type_tags()`
- `class CsvTests` - *CSV headers map to metadata fields case-insensitively.*
  - Method `.test_header_mapping()`
  - Method `.test_keyword_and_study_type_aliases()`
- `class CslJsonTests` - *CSL-JSON bibliography parsing.*
  - Method `.test_parse_csl_json_array()`
  - Method `.test_parse_csl_json_single_object()`
  - Method `.test_parse_csl_json_wrapped_items()`
  - Method `.test_parse_csl_json_invalid()`
- `class MarkdownTests` - *Front matter and heading fallbacks.*
  - Method `.test_front_matter()`
  - Method `.test_heading_and_filename_fallbacks()`
  - Method `.test_front_matter_carries_tags_and_study_type()`
- `class FileTests` - *Suffix dispatch and readable failures.*
  - Method `.setUp()`
  - Method `.write(name, content)`
  - Method `.test_plain_text()`
  - Method `.test_parse_paths()`
  - Method `.test_csl_json_file()`
  - Method `.test_unsupported_suffix()`
  - Method `.test_binary_pdf_gets_the_conversion_recipe()`
  - Method `.test_text_disguised_as_pdf_also_gets_the_recipe()`

---

### [`tests/lattice/test_inquiry.py`](tests/lattice/test_inquiry.py)
> *Ask, brief and review are deterministic and never invent a citation.*

**Size**: `84` lines (`3768` bytes)

**Classes:**
- `class InquiryTests` - *A small graph with one supporting, one contradicting and one unrelated claim.*
  - Method `.setUp()`
  - Method `.test_ask_question()`
  - Method `.test_ask_by_text()`
  - Method `.test_ask_search_mode()`
  - Method `.test_brief_contains_sections_and_citations()`
  - Method `.test_brief_respects_tight_budget()`
  - Method `.test_brief_rejects_tiny_budget()`
  - Method `.test_review_markdown()`
  - Method `.test_review_search_mode()`
  - Method `.test_suggestions_exclude_linked_claims()`

---

### [`tests/lattice/test_mcp.py`](tests/lattice/test_mcp.py)
> *MCP JSON-RPC contracts and stdio framing.*

**Size**: `268` lines (`13363` bytes)

**Classes:**
- `class McpTests` - *Call the protocol handler directly; no sockets or spawns.*
  - Method `.setUp()`
  - Method `.call(method, params, request_id)`
  - Method `.tool(name, arguments)`
  - Method `.test_initialize()`
  - Method `.test_tools_list()`
  - Method `.test_related_findings_tool_navigates_and_links()`
  - Method `.test_add_question_and_search()`
  - Method `.test_search_budget_omits_lower_ranked_hits()`
  - Method `.test_outline_tool_returns_a_cheap_index()`
  - Method `.test_add_claim_reports_missing_paper()`
  - Method `.test_unknown_method()`
  - Method `.test_invalid_request()`
  - Method `.test_notification_has_no_response()`
  - Method `.test_stdio_serves_one_message()`
  - Method `.test_stdio_reports_parse_error()`
  - Method `.test_discover_extract_synthesize_and_subgraph_tools()`
  - Method `.test_resources_and_prompts_endpoints()`
  - Method `.test_dispatch_tool_rejects_non_object_arguments()`
  - Method `.test_dispatch_tool_rejects_non_string_names()`
  - Method `.test_non_object_params_are_rejected()`
  - Method `.test_dispatch_tool_integer_coercion_fails_with_lattice_error()`
  - Method `.test_analyze_and_contradictions_tools_and_matrix_resource()`

---

### [`tests/lattice/test_meta.py`](tests/lattice/test_meta.py)
> *Unit tests for quantitative meta-analysis, effect sizes and forest plots.*

**Size**: `133` lines (`5927` bytes)

**Classes:**
- `class MetaAnalysisTests` - *Verify statistical pooling, heterogeneity metrics and forest plot renderers.*
  - Method `.test_fixed_effect_pooling_and_heterogeneity()`
  - Method `.test_random_effects_pooling()`
  - Method `.test_study_from_confidence_interval()`
  - Method `.test_study_from_two_groups()`
  - Method `.test_render_forest_ascii()`
  - Method `.test_render_forest_svg()`
  - Method `.test_meta_analyze_question()`
  - Method `.test_meta_analyze_question_reversed_edge_and_deduplication()`

---

### [`tests/lattice/test_models.py`](tests/lattice/test_models.py)
> *Identity, validation and budget helpers.*

**Size**: `110` lines (`3594` bytes)

**Classes:**
- `class IdentityTests` - *Stable identifiers make dedupe and citations reproducible.*
  - Method `.test_doi_wins_over_title()`
  - Method `.test_arxiv_is_next()`
  - Method `.test_title_normalization()`
  - Method `.test_empty_identity_is_refused()`
  - Method `.test_bare_id()`
- `class ValidationTests` - *User input fails with the triad instead of a traceback.*
  - Method `.test_stance_accepts_case()`
  - Method `.test_stance_rejects_unknown()`
  - Method `.test_confidence_range()`
  - Method `.test_edge_kind()`
  - Method `.test_reference_forms()`
  - Method `.test_tokens_are_positive()`
- `class LiteratureMetadataTests` - *Study types and tags are normalized deterministically from paper metadata.*
  - Method `.test_study_type_inference()`
  - Method `.test_tag_normalization_and_derivation()`

---

### [`tests/lattice/test_repository.py`](tests/lattice/test_repository.py)
> *Graph writes, dedupe, references, search and evidence grouping.*

**Size**: `205` lines (`9828` bytes)

**Classes:**
- `class RepositoryTests` - *Every test gets a fresh in-memory graph.*
  - Method `.setUp()`
  - Method `.paper(title, **values)`
  - Method `.test_paper_dedupe_by_doi()`
  - Method `.test_paper_dedupe_by_normalized_title_and_year()`
  - Method `.test_merge_fills_missing_metadata()`
  - Method `.test_claim_requires_quote()`
  - Method `.test_claim_ids_are_sequential()`
  - Method `.test_question_and_edges()`
  - Method `.test_duplicate_edge_is_refused()`
  - Method `.test_self_edge_is_refused()`
  - Method `.test_missing_reference_is_refused()`
  - Method `.test_search_across_entities()`
  - Method `.test_paper_stores_tags_and_infers_study_type()`
  - Method `.test_literature_search_matches_tags_words_sentences_and_study_type()`
  - Method `.test_evidence_groups_and_gaps()`
  - Method `.test_stats_and_event_log()`
  - Method `.test_stats_reports_evidence_health()`
  - Method `.test_stats_on_an_empty_graph_report_zero_health()`
  - Method `.test_neighbors_filter_by_kind()`
  - Method `.test_export_bibtex()`

---

### [`tests/lattice/test_screening.py`](tests/lattice/test_screening.py)
> *Unit tests for PRISMA 2020 systematic review screening and flow generation.*

**Size**: `122` lines (`5360` bytes)

**Classes:**
- `class ScreeningTests` - *Test paper screening decisions, validation, and PRISMA 2020 flow computation.*
  - Method `.setUp()`
  - Method `.test_record_and_get_screening_decision()`
  - Method `.test_record_exclusion_with_reason()`
  - Method `.test_invalid_status_raises_error()`
  - Method `.test_invalid_paper_id_raises_error()`
  - Method `.test_compute_prisma_flow()`
  - Method `.test_render_prisma_markdown()`
  - Method `.test_render_prisma_svg()`

---

### [`tests/lattice/test_snapshots.py`](tests/lattice/test_snapshots.py)
> *Tests for knowledge interaction: multi-term search, subgraphs, question status, and snapshots.*

**Size**: `210` lines (`9418` bytes)

**Classes:**
- `class InteractionAndSnapshotTests` - *Verify multi-term search, subgraph traversal, question status, and JSONL snapshot I/O.*
  - Method `.setUp()`
  - Method `.test_multi_term_search_and_filters()`
  - Method `.test_subgraph_traverses_multi_hop_neighborhood()`
  - Method `.test_set_question_status_updates_and_validates()`
  - Method `.test_export_and_import_snapshot_roundtrip_is_idempotent()`
  - Method `.test_export_graphml_generates_valid_xml_with_keys_and_elements()`
  - Method `.test_export_cytoscape_generates_valid_elements()`

---

### [`tests/lattice/test_synthesis.py`](tests/lattice/test_synthesis.py)
> *Tests for scientific literature synthesis: consensus scoring, thematic clusters, and BibTeX.*

**Size**: `121` lines (`5170` bytes)

**Classes:**
- `class SynthesisTests` - *Verify consensus scoring, thematic clustering, follow-up queries, and BibTeX generation.*
  - Method `.setUp()`
  - Method `.test_compute_consensus_handles_support_contradiction_and_empty()`
  - Method `.test_synthesize_question_produces_structured_ai_pack_and_markdown()`
  - Method `.test_synthesize_search_phrase_and_bibtex_formatting()`
  - Method `.test_synthesize_rejects_tiny_token_budget()`

---

### [`tests/lattice/test_ui_inventory.py`](tests/lattice/test_ui_inventory.py)
> *The UI inventory proof covers the studio's controls, handlers, routes and theme tokens.*

**Size**: `38` lines (`1510` bytes)

**Classes:**
- `class InventoryTest`
  - Method `.test_the_inventory_names_controls_handlers_routes_and_tokens()`
  - Method `.test_the_studio_page_and_panels_are_part_of_the_surface()`

---

### [`tests/lattice/test_web.py`](tests/lattice/test_web.py)
> *Tests for the web-based human UI and JSON API dispatcher (zero sockets).*

**Size**: `364` lines (`16345` bytes)

**Classes:**
- `class WebInterfaceTests` - *Verify HTML rendering and REST API handlers via pure request dispatch.*
  - Method `.setUp()`
  - Method `.request_json(method, path, payload)`
  - Method `.test_index_serves_self_contained_human_ui()`
  - Method `.test_index_has_guided_cold_start_and_compact_actions()`
  - Method `.test_link_related_endpoint_and_map_legend()`
  - Method `.test_demo_seed_and_overview_workflow()`
  - Method `.test_create_entities_and_synthesize_via_web_api()`
  - Method `.test_discover_extract_and_search_endpoints()`
  - Method `.test_ingest_text_matrix_contradictions_and_export()`
  - Method `.test_literature_search_ui_graph_and_api()`
  - Method `.test_validation_error_and_not_found()`
  - Method `.test_api_outline_endpoint()`
  - Method `.test_api_export_bibtex_endpoint()`
  - Method `.test_api_export_graphml_endpoint()`
  - Method `.test_api_export_cytoscape_endpoint()`
  - Method `.test_api_path_endpoint()`
  - Method `.test_api_hypothesize_endpoint()`
  - Method `.test_csl_json_ingest_and_visual_controls()`
  - Method `.test_api_prisma_and_screen_endpoints()`
  - Method `.test_api_meta_and_pack_endpoints()`

---

### [`tests/pnn/__init__.py`](tests/pnn/__init__.py)
> *Ported PNN pack contract tests.*

**Size**: `1` lines (`38` bytes)

---

### [`tests/pnn/test_assay.py`](tests/pnn/test_assay.py)
> *Unit and CLI tests for Phase 3 in vitro assay ingestion and hit qualification.*

**Size**: `185` lines (`6950` bytes)

**Classes:**
- `class AssayTest`
  - Method `.setUp()`
  - Method `.run_cli(*argv)`
  - Method `.test_load_degradation_data()`
  - Method `.test_load_degradation_invalid_numeric_raises()`
  - Method `.test_load_permeability_and_cytotoxicity()`
  - Method `.test_qualify_leads_classifications()`
  - Method `.test_qualify_leads_untested_safety_yields_qualified_lead()`
  - Method `.test_render_assay_report_contains_guideline_and_tables()`
  - Method `.test_cli_execution_success()`
  - Method `.test_cli_failure_triad_on_missing_file()`

---

### [`tests/pnn/test_bioisostere.py`](tests/pnn/test_bioisostere.py)
> *Unit tests for bioisosteric replacement and metabolic soft-spot optimizer.*

**Size**: `164` lines (`6048` bytes)

**Classes:**
- `class TestBioisostere`
  - Method `.test_generate_bioisosteres()`
  - Method `.test_ring_label_parser_ignores_isotope_brackets()`
  - Method `.test_replacement_does_not_split_ring_context()`
  - Method `.test_property_deltas_match_rule_table()`
  - Method `.test_cyclopropyl_delta_is_not_a_rotatable_increase()`
  - Method `.test_run_bioisostere_pipeline_missing_file_raises()`
  - Method `.test_run_bioisostere_pipeline_vendor_lib()`
  - Method `.test_short_trailing_row_is_skipped()` - *Short CSV rows without SMILES are skipped, not crashed on.*
  - Method `.test_render_bioisostere_report()`
  - Method `.test_bioisostere_cli()`

---

### [`tests/pnn/test_cli.py`](tests/pnn/test_cli.py)
> *Integration tests for the `python -m pnn` CLI contract.*

**Size**: `84` lines (`3727` bytes)

**Classes:**
- `class CliTest`
  - Method `.setUp()`
  - Method `.run_main(*argv)`
  - Method `.read_rows(path)`
  - Method `.test_writes_ranked_csv_and_json_summary()`
  - Method `.test_min_tier_filters_lower_tiers_and_rejects()`
  - Method `.test_invalid_input_returns_one_with_a_remediation_triad()`
  - Method `.test_missing_input_returns_one()`
  - Method `.test_help_exits_zero_and_unknown_flag_exits_two()`

---

### [`tests/pnn/test_curation.py`](tests/pnn/test_curation.py)
> *Unit and CLI tests for compound-library curation.*

**Size**: `181` lines (`6942` bytes)

**Classes:**
- `class DeduplicationTest`
  - Method `.test_duplicate_id_keeps_the_better_candidate()`
  - Method `.test_better_record_keeps_smiles_from_the_other_source()`
  - Method `.test_same_id_with_different_smiles_is_refused()`
  - Method `.test_same_smiles_with_different_ids_is_collapsed()`
  - Method `.test_blank_smiles_do_not_collapse_distinct_ids()`
  - Method `.test_prepare_candidates_keeps_sources()`
- `class CurationTest`
  - Method `.test_tier_filter_removes_rejected_candidates()`
  - Method `.test_per_bin_cap_keeps_one_best_per_property_cell()`
  - Method `.test_max_compounds_truncates_and_reports()`
  - Method `.test_property_bin_is_deterministic()`
  - Method `.test_invalid_bin_width_is_refused()`
- `class CurateCliTest`
  - Method `.setUp()`
  - Method `.run_main(*argv)`
  - Method `.read_rows(path)`
  - Method `.test_merges_deduplicates_and_filters()`
  - Method `.test_conflicting_id_returns_one()`
  - Method `.test_no_eligible_compounds_returns_one()`

**Functions:**
- `def compound(compound_id, smiles, **overrides)`
- `def candidate(compound_id, source, smiles, **overrides)`

---

### [`tests/pnn/test_docking.py`](tests/pnn/test_docking.py)
> *Unit tests for docking ingestion and consensus normalization.*

**Size**: `113` lines (`4478` bytes)

**Classes:**
- `class DockingIngestionTest`
  - Method `.test_aliases_units_and_optional_columns()`
  - Method `.test_row_needs_a_score()`
  - Method `.test_row_needs_target()`
  - Method `.test_duplicate_compound_target_is_refused()`
  - Method `.test_non_finite_score_is_refused()`
  - Method `.test_negative_rmsd_is_refused()`
- `class ConsensusTest`
  - Method `.test_vina_only_is_normalized_to_zero_and_one()`
  - Method `.test_multiple_methods_are_weighted_and_coverage_is_reported()`
  - Method `.test_best_target_is_kept_and_targets_are_counted()`
  - Method `.test_filters_drop_missing_vina_and_limit_breakers()`

---

### [`tests/pnn/test_dynamics.py`](tests/pnn/test_dynamics.py)
> *Unit tests for MD trajectory and contact stability analyzer.*

**Size**: `145` lines (`6276` bytes)

**Classes:**
- `class TestDynamics`
  - Method `.test_load_trajectory_csv()`
  - Method `.test_load_trajectory_missing_raises()`
  - Method `.test_analyze_trajectory_stable()`
  - Method `.test_analyze_trajectory_unstable_drift()`
  - Method `.test_generate_trajectory_svg()`
  - Method `.test_render_trajectory_report()`
  - Method `.test_run_dynamics_pipeline_and_cli()`
  - Method `.test_missing_optional_columns_produce_insufficient_evidence()`
  - Method `.test_partial_evidence_keeps_verdict_but_flags_gaps()`

---

### [`tests/pnn/test_ind.py`](tests/pnn/test_ind.py)
> *Unit tests for human allometric dose projection and IND regulatory dossier generator.*

**Size**: `216` lines (`8723` bytes)

**Classes:**
- `class TestIndProjection`
  - Method `.test_calculate_allometric_scaling()`
  - Method `.test_allometric_scaling_rejects_missing_measurements()`
  - Method `.test_project_clinical_candidates_with_complete_evidence()`
  - Method `.test_missing_evidence_is_never_invented()`
  - Method `.test_lead_is_nominated_first()`
  - Method `.test_dossier_marks_unmeasured_and_omits_claims()`
  - Method `.test_load_candidate_records_ignores_pk_timecourse_without_measurements()`
  - Method `.test_tox_path_supplies_most_sensitive_noael()`
  - Method `.test_compile_ind_dossier_uses_measured_candidates()`
- `class TestIndCli`
  - Method `.test_ind_cli()`

---

### [`tests/pnn/test_mpo.py`](tests/pnn/test_mpo.py)
**Size**: `132` lines (`4795` bytes)

**Classes:**
- `class TestMpoCalculations`
  - Method `.test_cns_mpo_optimal_properties()`
  - Method `.test_cns_mpo_penalized_properties()`
  - Method `.test_profile_development_candidate()`
  - Method `.test_profile_deprioritized_liability_detection()`
- `class TestMpoAnalysisAndCLI`
  - Method `.test_missing_compounds_raises()`
  - Method `.test_short_row_raises_mpo_error()` - *Short CSV rows raise MpoError, not AttributeError.*
  - Method `.test_run_mpo_analysis_valid()`
  - Method `.test_render_mpo_report()`
  - Method `.test_cli_execution_success()`

---

### [`tests/pnn/test_pathway.py`](tests/pnn/test_pathway.py)
> *Unit tests for hypothalamic circuit dynamics and dosing simulator.*

**Size**: `141` lines (`5225` bytes)

**Classes:**
- `class TestPathwaySimulator`
  - Method `.test_simulate_circuit_dynamics_pulsatile()`
  - Method `.test_simulate_circuit_dynamics_continuous()`
  - Method `.test_regimen_variations()`
  - Method `.test_invalid_parameters_raise()`
  - Method `.test_untreated_baseline_has_no_restoration_or_weight_loss()`
  - Method `.test_continuous_regimen_is_flagged_for_plasticity_risk()`
  - Method `.test_render_pathway_report()`
  - Method `.test_pathway_cli()`

---

### [`tests/pnn/test_pipeline.py`](tests/pnn/test_pipeline.py)
> *Unit and CLI integration tests for the end-to-end Phase 2 lead selection pipeline.*

**Size**: `206` lines (`8201` bytes)

**Classes:**
- `class PipelineTest`
  - Method `.setUp()`
  - Method `.read_rows(path)`
  - Method `.run_cli(*argv)`
  - Method `.test_select_leads_end_to_end()`
  - Method `.test_select_leads_raises_on_empty_input()`
  - Method `.test_select_leads_raises_when_curation_empties_set()`
  - Method `.test_select_leads_raises_when_no_shortlist_survives()`
  - Method `.test_render_lead_report_guidelines_and_evidence()`
  - Method `.test_run_pipeline_produces_all_artifacts_and_hashed_manifest()`
  - Method `.test_cli_execution_success()`
  - Method `.test_cli_execution_failure_triad()`
  - Method `.test_cli_help()`

---

### [`tests/pnn/test_preclinical.py`](tests/pnn/test_preclinical.py)
**Size**: `224` lines (`8597` bytes)

**Classes:**
- `class TestPreclinicalNCA`
  - Method `.test_nca_empty_points_raises()`
  - Method `.test_nca_trapezoidal_auc_exact()`
  - Method `.test_nca_terminal_elimination_and_clearance()`
- `class TestPreclinicalDataIngestion`
  - Method `.test_load_pk_data_missing_file_raises()`
  - Method `.test_load_pk_data_missing_columns_raises()`
  - Method `.test_load_pk_data_invalid_numeric_raises()`
  - Method `.test_load_pd_data_valid()`
- `class TestPreclinicalCandidateEvaluation`
  - Method `.setUp()`
  - Method `.test_evaluate_clinical_candidate()`
  - Method `.test_evaluate_insufficient_brain_penetration()`
  - Method `.test_render_preclinical_report()`
- `class TestPreclinicalCLI`
  - Method `.test_cli_execution_success()`

---

### [`tests/pnn/test_rank.py`](tests/pnn/test_rank.py)
> *Unit and CLI tests for the docking consensus shortlist.*

**Size**: `158` lines (`6554` bytes)

**Classes:**
- `class ShortlistTest`
  - Method `.test_tier_filter_and_consensus_order()`
  - Method `.test_rmsd_filter_removes_a_target_row()`
  - Method `.test_vina_filter_removes_weak_rows()`
  - Method `.test_compound_missing_from_screen_is_skipped()`
  - Method `.test_docking_only_mode_has_no_tier()`
- `class RankCliTest`
  - Method `.setUp()`
  - Method `.run_main(*argv)`
  - Method `.read_rows(path)`
  - Method `.test_cli_writes_shortlist_and_json()`
  - Method `.test_cli_returns_one_when_filters_remove_everything()`
  - Method `.test_cli_returns_one_for_invalid_docking()`
  - Method `.test_screen_table_loader_reads_tier_and_score()`
  - Method `.test_module_entry_point_runs_main()`

**Functions:**
- `def screen_table()`
- `def scores()`

---

### [`tests/pnn/test_rules.py`](tests/pnn/test_rules.py)
> *Unit tests for the property rules (PRINCIPLE-014: failing-first boundaries).*

**Size**: `89` lines (`3394` bytes)

**Classes:**
- `class PropertyRuleTest`
  - Method `.test_ideal_compound_passes_every_rule()`
  - Method `.test_molecular_weight_boundaries()`
  - Method `.test_tpsa_and_rotor_ceilings()`
  - Method `.test_missing_optional_properties_are_unknown()`
  - Method `.test_basic_pka_outside_window_fails()`
  - Method `.test_unrecognized_charge_is_unknown()`
  - Method `.test_oral_bioavailability_accepts_fraction_and_percent()`
  - Method `.test_hard_liabilities_fail()`

**Functions:**
- `def ideal(**overrides)`
- `def by_name(compound)`

---

### [`tests/pnn/test_run.py`](tests/pnn/test_run.py)
**Size**: `131` lines (`6074` bytes)

**Classes:**
- `class TestTurnkeyRunner`
  - Method `.test_missing_vendor_library_raises()`
  - Method `.test_execute_turnkey_pipeline_success()`
  - Method `.test_runner_cli_execution_no_browser()`
  - Method `.test_daily_timepoint_tolerance()`
  - Method `.test_runner_cli_execution_auto_opens_browser(mock_open)`

---

### [`tests/pnn/test_safety.py`](tests/pnn/test_safety.py)
> *Unit tests for the IND-enabling safety pharmacology and toxicology package.*

**Size**: `301` lines (`13166` bytes)

**Classes:**
- `class TestSafetyIngestion`
  - Method `.test_missing_tox_file_raises()`
  - Method `.test_missing_tox_columns_raises()`
  - Method `.test_unknown_species_raises()`
  - Method `.test_non_positive_noael_raises()`
  - Method `.test_loael_below_noael_raises()`
  - Method `.test_invalid_duration_raises()`
  - Method `.test_load_valid_tox_rows()`
  - Method `.test_pharm_duplicate_compound_raises()`
  - Method `.test_pharm_invalid_boolean_raises()`
  - Method `.test_pharm_percent_out_of_range_raises()`
  - Method `.test_pharm_missing_compound_id_raises()`
- `class TestSafetyAssessment`
  - Method `._safe_pharm(compound_id)`
  - Method `._tox(compound_id)`
  - Method `.test_safe_compound_projection_and_status()`
  - Method `.test_most_sensitive_species_is_selected_by_hed_not_raw_noael()`
  - Method `.test_dog_wins_when_its_hed_is_lower()`
  - Method `.test_most_sensitive_study_helper_ranks_on_hed()`
  - Method `.test_missing_tox_study_is_caution()`
  - Method `.test_missing_safety_pharmacology_is_caution()`
  - Method `.test_positive_genotoxicity_fails()`
  - Method `.test_narrow_herg_margin_fails()`
  - Method `.test_cyp3a4_ceiling_fails()`
  - Method `.test_marginal_herg_and_cyp_are_caution()`
  - Method `.test_invalid_thresholds_raise()`
  - Method `.test_report_includes_matrix_and_limits()`
- `class TestSafetyCli`
  - Method `.test_cli_requires_an_input()`
  - Method `.test_cli_missing_file_returns_error()`
  - Method `.test_cli_writes_csv_json_and_report()`

---

### [`tests/pnn/test_sar.py`](tests/pnn/test_sar.py)
**Size**: `138` lines (`5468` bytes)

**Classes:**
- `class TestSarSmilesScaffolding`
  - Method `.test_parse_empty_smiles_raises()`
  - Method `.test_parse_unmatched_parens_raises()`
  - Method `.test_acyclic_molecule_scaffold()`
  - Method `.test_monocyclic_benzene_scaffold()`
  - Method `.test_bemis_murcko_extraction_multiring()`
- `class TestSarAnalysisAndClustering`
  - Method `.test_load_compounds_missing_file_raises()`
  - Method `.test_analyze_sar_scaffold_clustering()`
  - Method `.test_render_sar_report()`
- `class TestSarCLI`
  - Method `.test_cli_execution_success()`

---

### [`tests/pnn/test_screen.py`](tests/pnn/test_screen.py)
> *Unit tests for tiering, ranking and CSV ingestion.*

**Size**: `167` lines (`6551` bytes)

**Classes:**
- `class TierTest`
  - Method `.test_complete_ideal_compound_is_tier_a()`
  - Method `.test_property_only_compound_cannot_be_tier_a()`
  - Method `.test_acceptable_compound_is_tier_b()`
  - Method `.test_two_core_failures_are_tier_c()`
  - Method `.test_three_core_failures_are_rejected()`
  - Method `.test_hard_liability_rejects_even_an_optimal_profile()`
- `class RankingTest`
  - Method `.test_ranking_orders_by_tier_then_score()`
- `class CsvIngestionTest`
  - Method `.setUp()`
  - Method `.write_csv(text)`
  - Method `.test_aliases_and_blank_optionals_are_supported()`
  - Method `.test_duplicate_ids_are_refused()`
  - Method `.test_bad_number_names_the_row()`
  - Method `.test_missing_field_is_refused()`
  - Method `.test_non_finite_number_is_refused()`
  - Method `.test_negative_property_is_refused()`
  - Method `.test_fractional_count_is_refused()`
  - Method `.test_missing_file_is_refused()`
  - Method `.test_header_only_file_is_refused()`
  - Method `.test_non_utf8_file_is_refused()`

**Functions:**
- `def ideal(compound_id, **overrides)`
- `def acceptable(compound_id, **overrides)`

---

### [`tests/pnn/test_studio.py`](tests/pnn/test_studio.py)
**Size**: `429` lines (`18633` bytes)

**Classes:**
- `class TestStudioRendering`
  - Method `.setUp()`
  - Method `.test_generate_radar_svg()`
  - Method `.test_generate_docking_heatmap_svg()`
  - Method `.test_generate_pk_curve_svg()`
  - Method `.test_render_studio_html()`
  - Method `.test_generate_circuit_dynamics_svg()`
  - Method `.test_render_studio_html_with_translational_panels()`
- `class TestStudioAccessibility` - *The dashboard is read by assistive technology, not only by eye.*
  - Method `.setUp()`
  - Method `.assert_labelled(svg, stem)`
  - Method `.test_svg_charts_expose_accessible_names()`
  - Method `.test_empty_circuit_charts_keep_accessible_names()`
  - Method `.test_tables_have_captions_and_column_scopes()`
  - Method `.test_charts_expose_data_tables()`
  - Method `.test_circuit_chart_exposes_data_table()`
  - Method `.test_chart_labels_use_white_background_contrast()` - *The SVGs sit on a white wrapper; every label clears 4.5:1 there.*
  - Method `.test_chart_series_use_dash_patterns_and_radar_legend()`
  - Method `.test_page_has_main_landmark_and_skip_link()`
- `class TestStudioDataLoader`
  - Method `.test_missing_compounds_file_raises()`
  - Method `.test_missing_docking_stays_missing()` - *Absent docking evidence must not be synthesized (ADR-010/ADR-013).*
  - Method `.test_malformed_numeric_raises_studio_error()` - *Empty required physicochemical cells raise StudioError, not ValueError.*
  - Method `.test_short_row_none_cells_raise_studio_error()` - *Short CSV rows (None cells) raise StudioError instead of AttributeError.*
  - Method `.test_load_studio_data_valid()`
- `class TestStudioCLI`
  - Method `.test_cli_execution_success()`
  - Method `.test_cli_execution_with_translational_flags()`
  - Method `.test_cli_missing_translational_files_error()`
- `class TestFieldExtraction`
  - Method `.test_get_val_with_mapping()`
  - Method `.test_get_val_with_object()`
  - Method `.test_get_field_aliases()`

---

### [`tests/pnn/test_target.py`](tests/pnn/test_target.py)
> *Unit and CLI tests for target receptor profiles and Vina grid generation.*

**Size**: `129` lines (`4865` bytes)

**Classes:**
- `class TargetProfileTest`
  - Method `.setUp()`
  - Method `.run_cli(*argv)`
  - Method `.test_list_targets_contains_primary_receptors()`
  - Method `.test_get_target_case_insensitive()`
  - Method `.test_get_target_unknown_raises_key_error()`
  - Method `.test_generate_vina_config_format()`
  - Method `.test_cli_list()`
  - Method `.test_cli_show_success_and_failure()`
  - Method `.test_cli_config_export_to_file()`
  - Method `.test_aggrecanase_targets_present()`
  - Method `.test_adamts4_target_profile()`
  - Method `.test_mmp9_target_profile()`

---

### [`tests/pnn/test_waves.py`](tests/pnn/test_waves.py)
**Size**: `88` lines (`3348` bytes)

**Classes:**
- `class TestWaveLedger`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `.test_collect_counts()`
  - Method `.test_markdown_report()`
  - Method `.test_html_section()`
  - Method `.test_missing_inputs_yield_empty_ledger()`
  - Method `.test_unreadable_wave_file_raises_actionable_error()`
  - Method `.test_stray_byte_does_not_break_ledger()`

---

### [`tests/support.py`](tests/support.py)
> *Shared fixtures: a fresh in-memory database per test.*

**Size**: `64` lines (`2181` bytes)

**Classes:**
- `class DatabaseCase` - *Give each test an isolated schema and connection.*
  - Method `.setUp()`
  - Method `.add_research(title)`
  - Method `.add_source(research, title)`
  - Method `.add_empirical(research, text)`

**Functions:**
- `def memory_connection()` - *Return an initialized in-memory connection for direct module tests.*
- `def force_numeric(conn, claim_id, group)` - *Write a NUMERIC state directly, simulating a record that predates the promotion gate.*

---

### [`tests/test_ai.py`](tests/test_ai.py)
> *AI integration: provenance at birth, fabricated citations die, novelty can survive.*

**Size**: `417` lines (`16243` bytes)

**Classes:**
- `class ArtifactTests`
  - Method `.test_schema_carries_ai_artifact_table()`
  - Method `.test_record_hashes_only_never_raw_text()`
  - Method `.test_record_refuses_empty_model_or_payload()`
  - Method `.test_external_fetch_always_refuses()`
- `class IngestTests`
  - Method `._extraction(research, cited)`
  - Method `.test_extract_enters_unverified_with_link()`
  - Method `.test_fabricated_source_is_refused_and_flagged()`
  - Method `.test_cited_divergence_is_refused_and_flagged()`
  - Method `.test_source_outside_cited_list_is_refused()`
  - Method `.test_ingest_defaults_actor_to_model()`
  - Method `.test_wrong_kind_from_wrong_artifact_is_refused()`
  - Method `.test_idea_preregisters_hypothesis()`
- `class KillTestAdapterTests`
  - Method `.test_free_form_template_is_refused()`
  - Method `.test_template_probe_verifies_like_a_human_test()`
  - Method `.test_tampered_template_command_trips_ai003()`
  - Method `.test_ai_proven_without_a_run_trips_ai002()`
- `class BoundaryTests`
  - Method `.test_no_network_imports_anywhere_in_the_engine()`
  - Method `.test_ai_module_never_calls_verdict_paths()`
  - Method `.test_model_io_inside_repo_is_refused()`
  - Method `.test_model_io_outside_repo_is_allowed()`
- `class DraftTests`
  - Method `._surviving_claim(research)`
  - Method `.test_draft_carries_kill_test_receipts()`
  - Method `.test_draft_withholds_unverified_claims()`
  - Method `.test_draft_refuses_a_failing_gate()`

---

### [`tests/test_analysis.py`](tests/test_analysis.py)
> *Discovery: contradictions, coverage matrix, keystone ranking, exposure.*

**Size**: `185` lines (`8910` bytes)

**Classes:**
- `class KeywordTests`
  - Method `.test_stopwords_are_removed()`
  - Method `.test_overlap_is_jaccard()`
  - Method `.test_negation_is_visible_despite_stopwords()`
- `class AnalysisTests`
  - Method `.setUp()`
  - Method `.test_contradictions_pair_within_a_question()`
  - Method `.test_contradictions_are_ranked_by_score()`
  - Method `.test_min_score_filters()`
  - Method `.test_contradiction_pairs_carry_the_polarity_bit()`
  - Method `.test_unlinked_proposals_carry_the_polarity_bit()`
  - Method `.test_pairings_ignore_withdrawn_and_superseded_claims()`
  - Method `.test_claims_on_different_questions_are_not_paired()`
  - Method `.test_unlinked_score_uses_both_confidences()`
  - Method `.test_unlinked_contradictions_skip_recorded_edges()`
  - Method `.test_matrix_counts_claims_per_source_and_question()`
  - Method `.test_matrix_ignores_assumed_claims()`
  - Method `.test_keystone_ranks_by_downstream_and_inbound()`
  - Method `.test_expose_lists_dependents_and_inbound()`

---

### [`tests/test_atlas_pack.py`](tests/test_atlas_pack.py)
> *Atlas pack contract for the host unittest gate.*

**Size**: `55` lines (`2527` bytes)

**Classes:**
- `class AtlasPackTests`
  - Method `.setUp()`
  - Method `.test_fixture_analysis_validates_and_builds_a_deck()`
  - Method `.test_offline_fallback_quotes_its_source()`
  - Method `.test_store_keeps_model_output_and_corrections_separate()`
  - Method `.test_text_ingestion_keeps_a_digest()`

---

### [`tests/test_attempts.py`](tests/test_attempts.py)
> *Attempt authority: the earliest non-replaceable attempt wins.*

**Size**: `218` lines (`8803` bytes)

**Classes:**
- `class AttemptAuthorityTests`
  - Method `.setUp()`
  - Method `.test_duplicate_attempt_is_an_engine_error()`
  - Method `.test_attempt_for_a_missing_test_is_not_found()`
  - Method `._insert_group(group, passed, values, outputs)`
  - Method `._record(group, outcome, reason)`
  - Method `.test_earliest_completed_attempt_wins()`
  - Method `.test_infra_failure_is_replaceable()`
  - Method `.test_subject_failure_blocks_a_later_pass()`
  - Method `.test_indeterminate_is_replaceable()`
  - Method `.test_stale_binding_is_ignored()`
  - Method `.test_legacy_group_without_an_attempt_still_counts()`
  - Method `.test_replaceable_outcome_requires_a_reason()`
  - Method `.test_attempts_are_sequenced_and_listed()`
  - Method `.test_completed_attempt_promotes()`
  - Method `.test_real_subject_failure_records_an_attempt_and_blocks()`
  - Method `.test_single_run_is_indeterminate()`
  - Method `.test_control_that_does_not_fail_is_indeterminate()`
  - Method `.test_a_new_test_after_a_subject_failure_warns()`

---

### [`tests/test_audit_fixes.py`](tests/test_audit_fixes.py)
> *Regression tests for defects found in the T-004 audit.*

**Size**: `126` lines (`5788` bytes)

**Classes:**
- `class RunIdentityTests`
  - Method `.test_projected_runs_carry_distinct_stable_ids()`
  - Method `.test_semantic_index_does_not_collapse_runs()`
  - Method `.test_a_changed_run_is_reported_by_identity()`
- `class ContradictionScopeTests`
  - Method `.test_the_same_pair_on_two_questions_is_reported_twice()`
- `class MergeFollowThroughTests`
  - Method `.setUp()`
  - Method `.test_tests_follow_the_survivor()`
  - Method `.test_merging_into_a_retired_survivor_is_refused()`
  - Method `.test_a_test_left_on_a_retired_claim_warns()`
- `class ScopedAuditTests`
  - Method `.test_outline_counts_only_its_own_program()`

---

### [`tests/test_bundle.py`](tests/test_bundle.py)
> *JSONL export is complete, scoped and deterministic in order.*

**Size**: `185` lines (`7822` bytes)

**Classes:**
- `class BundleTests`
  - Method `.setUp()`
  - Method `.test_export_writes_meta_first_and_every_record()`
  - Method `.test_scoped_export_excludes_other_programs()`
  - Method `.test_export_replaces_the_file_atomically()`
  - Method `.test_export_includes_observations_and_events()`
  - Method `.test_observation_changes_the_digests()`
  - Method `.test_generation_events_do_not_change_the_digests()`
  - Method `.test_export_verifies_its_own_digest()`
  - Method `.test_a_tampered_record_is_detected()`
  - Method `.test_a_legacy_export_without_a_digest_is_refused()`
  - Method `.test_a_count_mismatch_is_reported()`
  - Method `.test_a_non_ascii_digest_is_reported_not_crashed()`
  - Method `.test_a_non_object_line_is_reported_not_crashed()`
  - Method `.test_an_unsupported_schema_is_reported_not_trusted()`
  - Method `.test_a_non_numeric_record_count_is_handled()`

---

### [`tests/test_calibration.py`](tests/test_calibration.py)
> *Hypothesis calibration: recorded confidence is scored against recorded outcomes.*

**Size**: `121` lines (`5590` bytes)

**Classes:**
- `class CalibrationTests`
  - Method `.add_outcome(research, confidence, status, text)`
  - Method `.test_min_resolved_must_be_a_positive_integer()`
  - Method `.test_brier_log_loss_and_coverage()`
  - Method `.test_reliability_bins_separate_direction()`
  - Method `.test_empty_program_is_undefined_not_zero()`
  - Method `.test_small_resolved_set_is_flagged()`
  - Method `.test_one_sided_outcomes_cannot_measure_discrimination()`
  - Method `.test_score_appends_an_event_and_report_shows_the_score()`
  - Method `.test_minimum_resolved_set_must_be_positive()`

---

### [`tests/test_cascade.py`](tests/test_cascade.py)
> *A collapsed premise invalidates every dependent transitively.*

**Size**: `155` lines (`7049` bytes)

**Classes:**
- `class CascadeTests`
  - Method `._chain()`
  - Method `.test_collapse_traverses_depends_on_edges()`
  - Method `.test_dependents_are_transitive_and_ordered_by_depth()`
  - Method `.test_preview_writes_nothing()`
  - Method `.test_collapse_invalidates_every_dependent()`
  - Method `.test_retracted_dependent_is_not_rewritten()`
  - Method `.test_falsified_dependent_keeps_its_primary_failure()`
  - Method `.test_bulk_collapse_is_refused_without_override()`
  - Method `.test_collapse_requires_evidence()`
  - Method `.test_collapse_requires_reason_and_failed_status()`
  - Method `.test_stale_preview_digest_is_refused()`
  - Method `.test_current_preview_digest_allows_collapse()`
  - Method `.test_preview_digest_binds_new_dependents()`

---

### [`tests/test_claims.py`](tests/test_claims.py)
> *Provenance requirements and the append-only verdict lifecycle.*

**Size**: `226` lines (`9687` bytes)

**Classes:**
- `class ClaimTests`
  - Method `.test_empirical_claim_needs_source_quote_and_locator()`
  - Method `.test_derived_claim_needs_a_basis_or_premise()`
  - Method `.test_quote_is_refused_for_non_empirical_claims()`
  - Method `.test_confidence_bounds_are_enforced()`
  - Method `.test_source_must_share_the_program()`
  - Method `.test_prerequisites_create_dependency_edges()`
  - Method `.test_verdict_requires_evidence()`
  - Method `.test_promotion_requires_a_kill_test()`
  - Method `.test_verdict_history_preserves_previous_status()`
  - Method `.test_same_status_is_refused()`
  - Method `.test_promotion_blocked_by_failed_premise()`
  - Method `.test_links_are_typed_and_directional()`
  - Method `.test_list_filters_by_status()`
  - Method `.test_failed_claim_cannot_be_promoted_in_place()`
  - Method `.test_failed_claim_can_move_to_another_failed_status()`
  - Method `.test_revision_of_must_exist_in_the_same_program()`
  - Method `.test_revise_refuses_itself_as_a_prerequisite()`
  - Method `.test_record_edge_validates_its_endpoints()`
  - Method `.test_record_edge_validates_the_relation()`

---

### [`tests/test_cli.py`](tests/test_cli.py)
> *The CLI surface: JSON output, exit codes and the error triad.*

**Size**: `628` lines (`25692` bytes)

**Classes:**
- `class CliTests`
  - Method `.setUp()`
  - Method `.run_cli(*args)`
  - Method `.test_init_and_demo()`
  - Method `.test_demo_passes_integrity_gate()`
  - Method `.test_error_triad_on_missing_quote()`
  - Method `.test_report_and_scorecard()`
  - Method `.test_search_command()`
  - Method `.test_source_duplicates_command()`
  - Method `.test_calibration_command()`
  - Method `.test_kill_test_verify_exit_code()`
  - Method `.test_export_writes_a_file()`
  - Method `.test_missing_database_record_exits_one()`
  - Method `.test_report_check_ignores_reverification()`
  - Method `.test_source_status_and_retraction_from_the_cli()`
  - Method `.test_inventory_reports_provenance()`
  - Method `.test_verdict_group_flag_is_accepted()`
  - Method `.test_outline_and_brief_respect_the_budget()`
  - Method `.test_analysis_commands()`
  - Method `.test_diff_command_exit_codes()`
  - Method `.test_claim_merge_and_context()`
  - Method `.test_claim_revision_commands()`
  - Method `.test_screening_and_prisma()`
  - Method `.test_events_are_listed()`
  - Method `.test_event_tree_and_path()`
  - Method `.test_db_integrity_and_backup()`
  - Method `.test_negative_control_through_the_cli()`
  - Method `.test_observations_and_statistics()`
  - Method `.test_observation_errors_use_the_triad()`
  - Method `.test_analysis_trend()`
  - Method `.test_export_check_detects_tampering()`
  - Method `.test_export_check_refuses_a_research_filter()`
  - Method `.test_export_check_fails_on_an_unsupported_schema()`
  - Method `.test_closed_vocabularies_are_rejected_by_the_parser()`
  - Method `.test_retracted_status_points_at_retract()`
  - Method `.test_non_positive_budgets_are_refused()`
  - Method `.test_demo_failure_reports_the_error_triad()`
  - Method `.test_events_tree_refuses_list_filters()`
  - Method `.test_strict_needs_check()`
  - Method `.test_check_json_is_stable_machine_output()`
  - Method `.test_report_scorecard_card_evaluate_once()`
  - Method `.test_protocol_add_doc_path_mismatch_is_refused()`
  - Method `.test_bulk_invalidate_needs_allow_bulk()`
  - Method `.test_events_verify_reports_a_healthy_ledger()`
  - Method `.test_analysis_plan_is_cited_by_stats()`
  - Method `.test_amend_commands_correct_live_records()`
  - Method `.test_stale_preview_digest_is_refused()`
  - Method `.test_main_module_import_has_no_side_effects()`

---

### [`tests/test_context.py`](tests/test_context.py)
> *Token-budgeted views: estimation, packing and omission accounting.*

**Size**: `87` lines (`3067` bytes)

**Classes:**
- `class TokenTests`
  - Method `.test_estimate_is_character_quarters()`
  - Method `.test_pack_keeps_the_first_line_even_when_over_budget()`
  - Method `.test_pack_keeps_everything_that_fits()`
  - Method `.test_pack_rejects_a_non_positive_budget()`
- `class ViewTests`
  - Method `.setUp()`
  - Method `.test_outline_lists_questions_hypotheses_tests_and_audit()`
  - Method `.test_outline_reports_omissions()`
  - Method `.test_brief_shows_support_and_contradiction()`
  - Method `.test_views_are_deterministic()`
  - Method `.test_default_budget_is_positive()`
  - Method `.test_claim_view_carries_provenance_and_verdicts()`
  - Method `.test_budget_is_respected()`

---

### [`tests/test_controls.py`](tests/test_controls.py)
> *Negative controls: a test must be able to fail before its pass is evidence.*

**Size**: `167` lines (`7133` bytes)

**Classes:**
- `class ControlTests`
  - Method `.setUp()`
  - Method `._script(name, code)`
  - Method `._test(control)`
  - Method `.test_control_runs_are_stored_with_their_role()`
  - Method `.test_a_control_that_passes_blocks_verification()`
  - Method `.test_an_irreproducible_control_blocks_verification()`
  - Method `.test_absence_of_a_control_is_reported_but_not_blocking()`
  - Method `.test_editing_the_control_retires_the_evidence()`
  - Method `.test_control_state_reports_absence_explicitly()`
  - Method `.test_outline_counts_the_program_screening()`
  - Method `.test_adding_a_control_later_clears_the_error()`
  - Method `.test_single_control_run_is_not_falsified_or_reproducible()`
  - Method `.test_control_state_single_run_is_not_reproducible()`
  - Method `.test_binding_runs_single_source_of_truth()`

---

### [`tests/test_diffing.py`](tests/test_diffing.py)
> *Snapshot diff: semantic by default, exact on request.*

**Size**: `119` lines (`4724` bytes)

**Classes:**
- `class DiffTests`
  - Method `.setUp()`
  - Method `.test_identical_exports_have_no_differences()`
  - Method `.test_a_new_claim_is_added()`
  - Method `.test_semantic_mode_ignores_run_churn()`
  - Method `.test_a_changed_status_is_reported()`
  - Method `.test_missing_snapshot_is_reported()`
  - Method `.test_malformed_snapshot_is_reported()`
  - Method `.test_non_object_snapshot_line_is_reported()`
  - Method `.test_render_lists_each_change()`
  - Method `.test_a_second_run_with_the_same_identity_cannot_mask_a_change()`

---

### [`tests/test_docs.py`](tests/test_docs.py)
> *Documentation and project memory stay discoverable and within budget.*

**Size**: `107` lines (`3880` bytes)

**Classes:**
- `class DocsTests`
  - Method `.test_readme_has_the_cold_start_contract()`
  - Method `.test_architecture_and_mechanics_documents_exist()`
  - Method `.test_project_memory_declares_the_test_command()`
  - Method `.test_readme_tree_names_real_modules()`
  - Method `.test_readme_documents_the_current_schema_and_gates()`
  - Method `.test_architecture_documents_binding_and_digests()`

---

### [`tests/test_domain_isolation.py`](tests/test_domain_isolation.py)
> *Domain packs stay isolated: no pack imports another pack or a studio surface.*

**Size**: `54` lines (`2101` bytes)

**Classes:**
- `class DomainIsolationTests`
  - Method `.test_no_pack_imports_another_pack()`
  - Method `.test_no_pack_imports_a_surface_or_adapter()`
  - Method `.test_engine_does_not_import_a_pack_or_surface()`

**Functions:**
- `def _imports(path)`

---

### [`tests/test_duplicates.py`](tests/test_duplicates.py)
> *Duplicate sources: DOI and title normalization, scope, and the integrity warning.*

**Size**: `93` lines (`4413` bytes)

**Classes:**
- `class NormalizationTests`
  - Method `.test_doi_resolver_prefix_and_case_are_folded()`
  - Method `.test_title_folds_accents_case_and_punctuation()`
- `class DuplicateSourceTests`
  - Method `.test_doi_duplicates_are_grouped_with_the_lowest_id_kept()`
  - Method `.test_title_year_duplicates_are_grouped()`
  - Method `.test_same_title_different_year_is_only_a_variant()`
  - Method `.test_programs_are_never_grouped_together()`
  - Method `.test_limit_keeps_the_total_visible()`
  - Method `.test_integrity_warns_on_doi_title_year_and_variants()`

---

### [`tests/test_errors.py`](tests/test_errors.py)
> *NotFound fixes must point at real CLI verbs.*

**Size**: `33` lines (`1023` bytes)

**Classes:**
- `class NotFoundTests`
  - Method `.test_fix_points_at_a_real_cli_verb()`

---

### [`tests/test_events.py`](tests/test_events.py)
> *Event log: append-only record of actions that are not verdicts.*

**Size**: `190` lines (`8353` bytes)

**Classes:**
- `class EventTests`
  - Method `.test_record_and_list_newest_first()`
  - Method `.test_filters_by_kind_and_research()`
  - Method `.test_detail_is_flattened()`
  - Method `.test_nested_events_form_a_tree_and_path()`
  - Method `.test_orphan_parent_is_refused()`
  - Method `.test_cross_program_parent_is_refused()`
  - Method `.test_tree_rejects_a_non_root()`
  - Method `.test_source_status_is_recorded()`
  - Method `.test_screening_is_recorded()`
  - Method `.test_merge_is_recorded_once()`
  - Method `.test_report_generation_is_recorded()`
  - Method `.test_migration_records_an_event()`
  - Method `.test_chain_links_each_event_to_its_predecessor()`
  - Method `.test_tampered_middle_row_breaks_the_chain()`
  - Method `.test_extending_a_broken_tip_is_refused()`
  - Method `.test_legacy_unhashed_rows_are_grandfathered()`

---

### [`tests/test_experiments.py`](tests/test_experiments.py)
> *N1 experiment records and baseline-vs-intervention analysis on the host core.*

**Size**: `186` lines (`6704` bytes)

**Classes:**
- `class ExperimentModelTests`
  - Method `.test_intervention_round_trip()`
  - Method `.test_metric_definition_is_unique_per_program()`
  - Method `.test_metric_entry_links_intervention_and_validates_finite_value()`
  - Method `.test_event_severity_is_bounded()`
  - Method `.test_intervention_from_another_program_is_refused()`
  - Method `.test_csv_import_counts_good_and_bad_rows()`
- `class ExperimentAnalysisTests`
  - Method `._rows(research, values, start_day, metric)`
  - Method `.test_baseline_and_intervention_windows()`
  - Method `.test_insufficient_data_returns_counts_not_an_exception()`
  - Method `.test_multiple_metric_warning_above_three()`

---

### [`tests/test_fluid_rigor.py`](tests/test_fluid_rigor.py)
> *Fluid-universe rigor contracts: fingerprints, two-run compare and claim statuses.*

**Size**: `156` lines (`6560` bytes)

**Classes:**
- `class FingerprintTests`
  - Method `.test_source_and_result_digests_change_with_content()`
  - Method `.test_excluded_directories_do_not_enter_the_digest()`
- `class CompareTests`
  - Method `._fixture(root, fingerprint, left, right)`
  - Method `.test_two_agreeing_runs_are_accepted()`
  - Method `.test_disagreeing_runs_are_refused()`
  - Method `.test_stale_fingerprint_is_refused()`
  - Method `.test_identical_tags_are_refused()`
- `class ClaimCompatibilityTests`
  - Method `.test_ledger_parses_qualifiers_and_escaped_pipes()`
  - Method `.test_scorecard_parses_and_reports_mismatches()`
  - Method `.test_unknown_status_is_refused()`

**Functions:**
- `def _root(case)`
- `def _run(tag, fingerprint, checks)`

---

### [`tests/test_golden.py`](tests/test_golden.py)
> *Golden run: the whole command surface, end to end, in a fresh database.*

**Size**: `205` lines (`9926` bytes)

**Classes:**
- `class GoldenRunTests`
  - Method `.setUp()`
  - Method `.run_cli(*args)`
  - Method `.must(*args)`
  - Method `.test_every_command_composes()`

---

### [`tests/test_hypotheses.py`](tests/test_hypotheses.py)
> *Pre-registration precedes outcomes and cards carry the falsification criterion.*

**Size**: `83` lines (`3827` bytes)

**Classes:**
- `class HypothesisTests`
  - Method `.test_criterion_is_required()`
  - Method `.test_registration_is_immediate_and_card_is_rendered()`
  - Method `.test_outcome_requires_evidence_and_closes_once()`
  - Method `.test_unknown_outcome_is_refused()`
  - Method `.test_statement_correction_keeps_registration_and_logs()`
  - Method `.test_amendment_needs_a_reason_and_a_live_record()`

---

### [`tests/test_information.py`](tests/test_information.py)
> *Cheap information-quality checks over stored claim quotes.*

**Size**: `57` lines (`2046` bytes)

**Classes:**
- `class InformationTests`
  - Method `.test_normalize_folds_case_and_punctuation()`
  - Method `.test_restates_question_exact_and_substring()`
  - Method `.test_restates_question_needs_two_content_terms()`
  - Method `.test_duplicate_quote_is_case_and_punctuation_insensitive()`
  - Method `.test_stopword_only_quote_has_no_content_terms()`
  - Method `.test_quote_classes_are_stable_and_additive()`
  - Method `.test_distinct_quote_has_no_classes()`

---

### [`tests/test_inputs.py`](tests/test_inputs.py)
> *Declared inputs: glob expansion, directory refusal, absence and collision safety.*

**Size**: `70` lines (`2844` bytes)

**Classes:**
- `class InputTests`
  - Method `.setUp()`
  - Method `.test_glob_expands_to_each_matching_file()`
  - Method `.test_glob_result_tracks_content()`
  - Method `.test_a_new_file_matching_the_glob_changes_the_digest()`
  - Method `.test_unmatched_glob_is_recorded_and_changes_when_files_appear()`
  - Method `.test_directory_input_is_refused()`
  - Method `.test_absent_file_does_not_collide_with_the_word_missing()`
  - Method `.test_declarations_are_deduplicated_and_sorted()`
  - Method `.test_directory_contents_are_not_silently_ignored()`

---

### [`tests/test_integrity.py`](tests/test_integrity.py)
> *Every integrity rule must detect the corruption it names.*

**Size**: `462` lines (`21009` bytes)

**Classes:**
- `class IntegrityTests`
  - Method `._clean_program()`
  - Method `.test_clean_program_has_no_errors()`
  - Method `.test_missing_provenance_is_detected()`
  - Method `.test_quote_restating_a_question_warns()`
  - Method `.test_duplicate_quote_warns()`
  - Method `.test_stopword_only_quote_warns()`
  - Method `.test_distinct_quote_does_not_warn()`
  - Method `.test_source_without_identifier_is_detected()`
  - Method `.test_promoted_claim_needs_kill_test()`
  - Method `.test_numeric_claim_needs_two_run_test()`
  - Method `.test_failed_status_needs_evidence()`
  - Method `.test_hypothesis_outcome_needs_verdict()`
  - Method `.test_dependency_cycle_is_detected()`
  - Method `.test_mutual_support_cycle_is_flagged()`
  - Method `.test_support_ring_is_flagged()`
  - Method `.test_one_way_support_is_not_a_cycle()`
  - Method `.test_dangling_and_self_edges_are_detected()`
  - Method `.test_cross_program_edge_is_detected()`
  - Method `.test_stale_dependent_is_detected()`
  - Method `.test_both_failed_is_not_a_stale_dependent()`
  - Method `.test_title_variant_duplicate_warns()`
  - Method `.test_corrupt_schema_ledger_is_an_error()`
  - Method `.test_rendered_table_escapes_untrusted_text()`
  - Method `.test_gaps_and_duplicates_are_warnings()`
  - Method `.test_empty_program_warns()`
  - Method `.test_renderers_are_stable()`
  - Method `.test_stale_numeric_evidence_is_detected()`
  - Method `.test_missing_evidence_volume_reports_once()`
  - Method `.test_small_stale_set_keeps_per_claim_findings()`
  - Method `.test_retracted_source_blocks_a_live_claim()`
  - Method `.test_expression_of_concern_is_a_warning()`
  - Method `.test_unknown_is_recorded_with_a_reason()`
  - Method `.test_unknown_without_a_reason_warns()`
  - Method `.test_unknown_is_not_a_failure_state()`
  - Method `.test_promotion_is_blocked_by_an_unknown_premise()`
  - Method `.test_out_of_order_hypothesis_outcome_is_scoped_to_its_hypothesis()`

**Functions:**
- `def codes(findings)`

---

### [`tests/test_killtests.py`](tests/test_killtests.py)
> *Kill tests: binding, two-run agreement, expected exits and bounded teardown.*

**Size**: `168` lines (`7490` bytes)

**Classes:**
- `class KillTestTests`
  - Method `.setUp()`
  - Method `._script(name, body)`
  - Method `.test_test_must_be_bound_to_a_target()`
  - Method `.test_two_runs_agree_and_record_a_verified_group()`
  - Method `.test_disagreeing_runs_fail_reproducibility()`
  - Method `.test_expected_exit_code_is_honoured()`
  - Method `.test_ordinary_failure_is_reported()`
  - Method `.test_timeout_kills_the_command_and_fails()`
  - Method `.test_binding_matches_after_verification()`
  - Method `.test_editing_the_command_invalidates_the_binding()`
  - Method `.test_editing_expect_exit_invalidates_the_binding()`
  - Method `.test_editing_timeout_invalidates_the_binding()`
  - Method `.test_changing_a_declared_input_invalidates_the_binding()`
  - Method `.test_run_records_the_binding_and_git_state()`

---

### [`tests/test_maintenance.py`](tests/test_maintenance.py)
> *Database maintenance: integrity verification and verified backups.*

**Size**: `166` lines (`7202` bytes)

**Classes:**
- `class MaintenanceTests`
  - Method `.setUp()`
  - Method `.test_integrity_reports_ok_and_counts()`
  - Method `.test_integrity_detects_a_foreign_key_violation()`
  - Method `.test_backup_produces_a_readable_copy()`
  - Method `.test_backup_refuses_to_overwrite()`
  - Method `.test_backup_leaves_no_temporary_file()`
  - Method `.test_connect_uses_a_lock_wait_timeout()`
  - Method `.test_locked_database_reports_an_engine_error()`
  - Method `.test_backup_preserves_the_journal_mode()`
  - Method `.test_backup_refuses_an_open_write_transaction()`
  - Method `.test_counts_cover_edges_and_ai_artifacts()`
  - Method `.test_version_skew_fails_the_gate()`
  - Method `.test_corrupt_version_fails_closed()`
  - Method `.test_backup_target_guard_refuses_existing_paths()`
  - Method `.test_backup_of_a_database_with_events_copies_them()`

---

### [`tests/test_manifest.py`](tests/test_manifest.py)
> *Generated report manifests and drift detection.*

**Size**: `190` lines (`8101` bytes)

**Classes:**
- `class ManifestTests`
  - Method `.setUp()`
  - Method `.test_write_report_creates_report_and_manifest()`
  - Method `.test_check_passes_on_an_unchanged_graph()`
  - Method `.test_graph_change_is_reported_as_drift()`
  - Method `.test_missing_manifest_is_an_error()`
  - Method `.test_unknown_manifest_schema_is_refused()`
  - Method `.test_manifest_identifies_the_license()`
  - Method `.test_license_change_is_reported_as_drift()`
  - Method `.test_report_prints_its_limits()`
  - Method `.test_reverification_does_not_report_content_drift()`
  - Method `.test_strict_check_reports_record_churn()`
  - Method `.test_tampered_counts_are_reported()`
  - Method `.test_another_program_does_not_dirty_a_committed_report()`
  - Method `.test_strict_check_passes_right_after_generation()`
  - Method `.test_tampered_report_body_is_drift()`
  - Method `.test_missing_report_file_is_drift()`

---

### [`tests/test_markdown.py`](tests/test_markdown.py)
> *Untrusted text: control characters, newlines and table syntax must not escape a cell.*

**Size**: `50` lines (`1645` bytes)

**Classes:**
- `class SanitizeTests`
  - Method `.test_newlines_collapse()`
  - Method `.test_control_characters_are_removed()`
  - Method `.test_heading_injection_cannot_survive()`
  - Method `.test_width_is_respected_and_marked()`
  - Method `.test_zero_width_means_no_cap()`
- `class CellTests`
  - Method `.test_pipe_is_escaped()`
  - Method `.test_backtick_is_escaped()`
  - Method `.test_backslash_is_escaped_first()`
  - Method `.test_cell_is_a_single_line()`
  - Method `.test_bullet_and_code_are_single_line()`

---

### [`tests/test_measurements.py`](tests/test_measurements.py)
> *Measurement provenance and protocol comparability.*

**Size**: `253` lines (`11173` bytes)

**Classes:**
- `class MeasurementTests`
  - Method `.setUp()`
  - Method `._kwargs(protocol, instrument, digest, unit)`
  - Method `._add(group, value, **overrides)`
  - Method `.test_protocol_registration_is_immutable()`
  - Method `.test_doc_path_digest_mismatch_is_refused()`
  - Method `.test_doc_path_only_pins_computed_digest()`
  - Method `.test_missing_doc_path_is_refused()`
  - Method `.test_measures_correction_preserves_digest_and_logs()`
  - Method `.test_protocol_amendment_needs_a_reason()`
  - Method `.test_observation_round_trips_provenance()`
  - Method `.test_incomplete_provenance_is_refused()`
  - Method `.test_unknown_protocol_is_refused()`
  - Method `.test_unknown_aggregation_is_refused()`
  - Method `.test_legacy_observation_warns()`
  - Method `.test_same_protocol_is_comparable()`
  - Method `.test_different_protocols_are_refused()`
  - Method `.test_incomparable_can_be_allowed_with_a_warning()`
  - Method `.test_different_instruments_are_refused()`
  - Method `.test_different_units_are_refused()`
  - Method `.test_mixed_provenance_in_one_group_is_refused()`
  - Method `.test_self_reported_requires_a_producer_path()`
  - Method `.test_unknown_provenance_class_is_refused()`
  - Method `.test_self_reported_comparison_is_refused()`
  - Method `.test_mixed_self_reported_group_is_refused()`
  - Method `.test_self_reported_measurements_are_separated_in_the_report()`
  - Method `.test_integrity_flags_unclassified_and_self_reported()`

---

### [`tests/test_merging.py`](tests/test_merging.py)
> *Merging duplicates: survivor, repointed edges, retired duplicates, history kept.*

**Size**: `139` lines (`6172` bytes)

**Classes:**
- `class MergeTests`
  - Method `.setUp()`
  - Method `.test_merge_retires_the_duplicate_and_keeps_history()`
  - Method `.test_edges_are_repointed_to_the_survivor()`
  - Method `.test_dependency_edges_survive_and_feed_the_survivor()`
  - Method `.test_merge_clears_the_duplicate_warning()`
  - Method `.test_self_merge_is_refused()`
  - Method `.test_empty_duplicate_list_is_refused()`
  - Method `.test_retired_duplicate_is_refused()`
  - Method `.test_cross_program_merge_is_refused()`
  - Method `.test_falsified_survivor_and_duplicate_are_refused()`
  - Method `.test_observations_and_artifacts_follow_the_survivor()`
  - Method `.test_already_repointed_edges_are_not_double_counted()`
  - Method `.test_linking_two_merged_claims_does_not_leave_a_self_edge()`

---

### [`tests/test_migration.py`](tests/test_migration.py)
> *Schema migration: an older database is repaired, not rejected or wiped.*

**Size**: `275` lines (`11484` bytes)

**Classes:**
- `class MigrationTests`
  - Method `._old_database()`
  - Method `.test_version_one_database_is_migrated_in_place()`
  - Method `.test_existing_rows_are_preserved()`
  - Method `.test_migration_creates_the_attempt_table()`
  - Method `.test_migration_adds_the_claim_revision_columns()`
  - Method `.test_migration_adds_observation_provenance_columns()`
  - Method `.test_migration_creates_the_protocol_table()`
  - Method `.test_migration_adds_event_nesting_columns()`
  - Method `.test_migration_is_idempotent()`
  - Method `.test_future_version_is_refused_without_changes()`
  - Method `.test_future_version_is_refused_before_creating_tables()`
  - Method `.test_fresh_database_declares_the_current_version()`
  - Method `.test_verdict_gains_the_evidence_group_column()`
  - Method `.test_migration_reports_the_unbound_numeric_claims()`
  - Method `.test_version_two_database_gains_only_the_verdict_column()`
  - Method `.test_observation_table_exists_after_migration()`
  - Method `.test_version_four_database_gains_the_observation_table()`

---

### [`tests/test_migration_harness.py`](tests/test_migration_harness.py)
> *Migration harness: inspect first, then apply a source fixture without losing provenance.*

**Size**: `228` lines (`10199` bytes)

**Classes:**
- `class MigrationHarnessTests`
  - Method `._lattice()`
  - Method `._n1()`
  - Method `.test_lattice_inspect_is_read_only_and_counts_rows()`
  - Method `.test_lattice_dry_run_writes_nothing()`
  - Method `.test_lattice_apply_preserves_paper_fields_provenance_and_screening()`
  - Method `.test_lattice_apply_is_recorded_once()`
  - Method `.test_n1_manifest_and_apply_link_metrics_to_interventions()`
  - Method `.test_golden_both_sources_share_one_program()`
  - Method `.test_inspect_tree_counts_and_fingerprints_files()`
  - Method `.test_inspect_obezite_counts_verified_and_backfill()`
  - Method `.test_inspect_research_reads_a_host_database()`

**Functions:**
- `def _fixture(sql, name)`

---

### [`tests/test_models.py`](tests/test_models.py)
> *Vocabularies are closed and records are immutable.*

**Size**: `53` lines (`1607` bytes)

**Classes:**
- `class ModelTests`
  - Method `.test_status_vocabulary_is_closed()`
  - Method `.test_dependency_relations_are_explicit()`
  - Method `.test_claim_is_frozen()`

---

### [`tests/test_n1_ports.py`](tests/test_n1_ports.py)
> *N1 suitable ports: provenance-gated correlation, batch stats-all, CSV import.*

**Size**: `327` lines (`14588` bytes)

**Classes:**
- `class PearsonTests`
  - Method `.test_perfect_correlation()`
  - Method `.test_anticorrelation()`
  - Method `.test_degenerate_variance_yields_zero()`
  - Method `.test_fewer_than_three_pairs_yields_zero()`
- `class CorrelationTests`
  - Method `._claim_with_groups()`
  - Method `.test_correlated_groups_rank_first()`
  - Method `.test_truncation_is_reported()`
  - Method `.test_incomparable_protocols_are_recorded_not_raised()`
  - Method `.test_fewer_than_two_groups_refused()`
- `class BatchStatisticsTests`
  - Method `._claim(research, baseline, treatment)`
  - Method `.test_errors_are_isolated_per_claim()`
  - Method `.test_many_claims_warn()`
- `class CsvImportTests`
  - Method `._write_csv(rows)`
  - Method `.test_valid_rows_import_and_bad_rows_skip()`
  - Method `.test_missing_header_refused()`
  - Method `.test_alternate_group_header_accepted()`
- `class TemplateTests`
  - Method `.test_header_names_required_columns_first()`
- `class WindowTests`
  - Method `._window_claim()`
  - Method `.test_window_filters_by_record_time()`
  - Method `.test_invalid_bound_refused()`
  - Method `.test_non_utc_offset_normalized_to_utc()`
  - Method `.test_batch_rejects_bad_bounds_loudly()`
  - Method `.test_correlation_respects_window()`
  - Method `.test_trend_respects_window()`
- `class DryRunTests`
  - Method `.test_dry_run_writes_nothing()`
- `class HolmTests`
  - Method `.test_holm_table_opt_in()`

---

### [`tests/test_obezite_ledger.py`](tests/test_obezite_ledger.py)
> *Obezite claim-ledger tooling: parsing, buckets and projections on a fixture.*

**Size**: `78` lines (`3496` bytes)

**Classes:**
- `class LedgerParsingTests`
  - Method `.test_claims_are_parsed_with_buckets_and_source_identity()`
  - Method `.test_summary_separates_verified_and_backfill()`
  - Method `.test_bucket_helpers_are_stable()`
  - Method `.test_projections_are_generated_from_an_external_root()`
- `class LedgerChunkingTests`
  - Method `.test_chunk_names_follow_the_500_claim_window()`
  - Method `.test_split_is_lossless_and_routes_by_claim_number()`
  - Method `.test_generated_chunks_keep_every_line()`

---

### [`tests/test_observations.py`](tests/test_observations.py)
> *Observations: raw values, their voiding, and the statistics projection over them.*

**Size**: `244` lines (`11825` bytes)

**Classes:**
- `class ObservationTests`
  - Method `.setUp()`
  - Method `.test_values_are_recorded_in_order()`
  - Method `.test_non_finite_values_are_refused()`
  - Method `.test_non_numeric_values_are_refused()`
  - Method `.test_sample_size_must_be_a_positive_integer()`
  - Method `.test_invalid_group_is_refused()`
  - Method `.test_groups_are_lowercased()`
  - Method `.test_void_retires_without_deleting()`
  - Method `.test_void_requires_a_reason_and_happens_once()`
  - Method `.test_void_is_logged()`
  - Method `.test_statistics_compare_the_groups()`
  - Method `.test_missing_group_lists_available_groups()`
  - Method `.test_statistics_are_logged_and_clear_the_warning()`
  - Method `.test_summary_and_detail()`
  - Method `.test_voided_values_are_excluded_from_statistics()`
  - Method `.test_trend_is_fitted_over_recording_order()`
  - Method `.test_trend_needs_a_group()`
  - Method `.test_short_series_warns_instead_of_pretending()`
  - Method `.test_summary_reports_median_and_mad()`
  - Method `.test_more_than_two_groups_warns_about_uncorrected_comparison()`
  - Method `.test_more_than_two_groups_reports_a_holm_family()`
  - Method `.test_group_labels_are_case_insensitive()`
  - Method `.test_a_group_cannot_be_compared_with_itself()`
  - Method `.test_too_few_resamples_are_refused()`
  - Method `.test_trend_labels_are_case_insensitive()`
  - Method `.test_new_observations_after_a_run_warn_again()`
  - Method `.test_a_void_after_a_run_warns_again()`
  - Method `.test_a_short_trend_says_it_is_insufficient()`
  - Method `.test_a_claim_whose_observations_were_all_voided_does_not_warn()`

---

### [`tests/test_packs.py`](tests/test_packs.py)
> *Domain-pack registry: an isolated pack is declared, not imported across domains.*

**Size**: `54` lines (`1889` bytes)

**Classes:**
- `class PackRegistryTests`
  - Method `.test_register_and_read_a_pack()`
  - Method `.test_duplicate_pack_is_refused()`
  - Method `.test_invalid_api_version_is_refused()`
  - Method `.test_invalid_manifest_digest_is_refused()`
  - Method `.test_pack_data_root_is_a_reference_not_a_copy()`

---

### [`tests/test_plans.py`](tests/test_plans.py)
> *Analysis plans are preregistered; unmatched comparisons read as exploratory.*

**Size**: `101` lines (`3941` bytes)

**Classes:**
- `class PlanTests`
  - Method `._planned_claim()`
  - Method `.test_plan_registers_before_data_is_seen()`
  - Method `.test_plan_needs_a_prediction_and_two_groups()`
  - Method `.test_cited_plan_is_recorded_on_the_comparison()`
  - Method `.test_uncited_comparison_with_plans_is_exploratory()`
  - Method `.test_plan_must_match_the_compared_pair()`
  - Method `.test_plan_belongs_to_one_claim()`

---

### [`tests/test_promotion.py`](tests/test_promotion.py)
> *Promotion gate: a NUMERIC verdict must cite a current, verified run group.*

**Size**: `94` lines (`4148` bytes)

**Classes:**
- `class PromotionTests`
  - Method `.setUp()`
  - Method `._verified_test()`
  - Method `.test_numeric_without_a_test_is_refused()`
  - Method `.test_numeric_derives_the_current_group()`
  - Method `.test_explicit_group_is_recorded()`
  - Method `.test_unknown_group_is_refused()`
  - Method `.test_promotion_on_a_changed_command_is_detected()`
  - Method `.test_proven_promotion_needs_no_group()`

---

### [`tests/test_provenance.py`](tests/test_provenance.py)
> *Workspace provenance: code and input identity used to bind evidence.*

**Size**: `91` lines (`3447` bytes)

**Classes:**
- `class ProvenanceTests`
  - Method `.test_code_digest_is_stable_and_shaped()`
  - Method `.test_inputs_digest_tracks_content()`
  - Method `.test_missing_input_hashes_distinctly()`
  - Method `.test_input_order_does_not_matter()`
  - Method `.test_fingerprint_combines_code_and_inputs()`
  - Method `.test_git_state_reports_a_pair()`
  - Method `.test_environment_names_runtime()`
  - Method `.test_provenance_block_has_binding_and_diagnostics()`

---

### [`tests/test_research.py`](tests/test_research.py)
> *Program creation, slug resolution and counts.*

**Size**: `45` lines (`1739` bytes)

**Classes:**
- `class ResearchTests`
  - Method `.test_create_and_resolve_by_slug()`
  - Method `.test_duplicate_slug_is_suffixed()`
  - Method `.test_invalid_slug_is_refused()`
  - Method `.test_missing_program_is_reported()`
  - Method `.test_counts_include_open_questions()`
  - Method `.test_counts_require_an_existing_program()`

---

### [`tests/test_revisions.py`](tests/test_revisions.py)
> *Claim revisions: the head carries the edges, the old claim stays as history.*

**Size**: `171` lines (`6027` bytes)

**Classes:**
- `class RevisionTests`
  - Method `.setUp()`
  - Method `._revise(**overrides)`
  - Method `.test_revision_marks_the_old_claim_and_starts_unverified()`
  - Method `.test_default_list_hides_superseded_and_history_includes_it()`
  - Method `.test_revision_chain_is_oldest_first()`
  - Method `.test_edges_move_to_the_head()`
  - Method `.test_an_empirical_revision_still_needs_a_quote()`
  - Method `.test_a_revision_needs_a_reason()`
  - Method `.test_a_superseded_claim_cannot_be_revised_again()`
  - Method `.test_a_test_on_a_superseded_claim_warns()`
  - Method `.test_a_superseded_claim_refuses_a_new_verdict()`
  - Method `.test_a_superseded_claim_refuses_a_new_observation()`
  - Method `.test_a_superseded_claim_refuses_a_new_test()`
  - Method `.test_a_superseded_claim_refuses_a_new_prerequisite()`
  - Method `.test_a_superseded_claim_refuses_new_links()`

---

### [`tests/test_schema_v14.py`](tests/test_schema_v14.py)
> *Schema 14: lattice paper fields, N1 experiment tables and the pack registry.*

**Size**: `107` lines (`3743` bytes)

**Classes:**
- `class Schema14MigrationTests`
  - Method `._v13()`
  - Method `.test_version_13_source_gains_paper_columns_and_keeps_rows()`
  - Method `.test_version_14_creates_experiment_and_pack_tables()`
- `class PaperFieldTests`
  - Method `.test_source_round_trips_paper_metadata()`

---

### [`tests/test_screening.py`](tests/test_screening.py)
> *Screening decisions and the PRISMA flow.*

**Size**: `85` lines (`3747` bytes)

**Classes:**
- `class ScreeningTests`
  - Method `.setUp()`
  - Method `.test_new_sources_are_identified()`
  - Method `.test_vocabularies_are_closed()`
  - Method `.test_out_status_defaults_to_other_reason()`
  - Method `.test_reason_is_required_to_be_known()`
  - Method `.test_reason_is_cleared_for_an_in_status()`
  - Method `.test_unknown_status_and_repeat_are_refused()`
  - Method `.test_prisma_counts_and_fraction()`
  - Method `.test_excluded_source_citing_claim_warns()`
  - Method `.test_included_source_does_not_warn()`

---

### [`tests/test_search.py`](tests/test_search.py)
> *Deterministic lexical search: phrase ranking, snippets, scope and budget.*

**Size**: `129` lines (`5971` bytes)

**Classes:**
- `class SearchTests`
  - Method `.add_assumption(research, text, basis)`
  - Method `.test_phrase_beats_scattered_terms()`
  - Method `.test_case_and_punctuation_are_folded()`
  - Method `.test_all_four_kinds_are_searched()`
  - Method `.test_research_filter_excludes_other_programs()`
  - Method `.test_superseded_claims_are_hidden_unless_requested()`
  - Method `.test_snippet_reports_the_matching_field()`
  - Method `.test_budget_reports_omitted_lines()`
  - Method `.test_result_limit_is_per_kind()`
  - Method `.test_repeat_is_deterministic()`
  - Method `.test_invalid_inputs_are_refused()`

---

### [`tests/test_sources_questions.py`](tests/test_sources_questions.py)
> *Source identifiers and question lifecycle.*

**Size**: `63` lines (`2639` bytes)

**Classes:**
- `class SourceQuestionTests`
  - Method `.test_source_requires_an_identifier()`
  - Method `.test_source_accepts_doi_or_url()`
  - Method `.test_source_rejects_bad_kind_and_year()`
  - Method `.test_question_closes_without_deleting()`
  - Method `.test_source_year_must_be_an_integer()`
  - Method `.test_double_close_is_refused()`
  - Method `.test_empty_question_is_refused()`

---

### [`tests/test_sources_retraction.py`](tests/test_sources_retraction.py)
> *Source status and retraction cascade.*

**Size**: `257` lines (`11450` bytes)

**Classes:**
- `class SourceStatusTests`
  - Method `.test_downgrade_requires_a_note()`
  - Method `.test_unknown_status_and_repeat_are_refused()`
  - Method `.test_direct_retracted_status_routes_through_retraction()`
  - Method `.test_retraction_path_retires_and_refuses_repeats()`
  - Method `.test_retraction_requires_a_reason()`
  - Method `.test_retraction_requires_evidence()`
  - Method `.test_retraction_ignores_superseded_claims()`
  - Method `.test_retraction_retires_claims_and_dependents()`
  - Method `.test_retracting_twice_is_refused()`
  - Method `.test_claims_are_left_alone_when_already_failed()`
  - Method `.test_retracted_source_is_clean_after_cascade()`
  - Method `.test_retraction_covers_twin_doi_rows()`
  - Method `.test_bulk_retraction_is_refused_without_override()`
  - Method `.test_bulk_retraction_counts_transitive_dependents()`
  - Method `.test_stale_retract_preview_is_refused()`
  - Method `.test_reinstatement_requires_a_note_and_keeps_claim_verdicts()`

---

### [`tests/test_stats.py`](tests/test_stats.py)
> *Statistics: values checked against an independent implementation, behaviour checked here.*

**Size**: `162` lines (`6501` bytes)

**Classes:**
- `class DistributionTests`
  - Method `.test_sample_sd()`
  - Method `.test_t_p_value_matches_reference()`
  - Method `.test_t_p_value_edges()`
- `class TestTests`
  - Method `.test_welch_matches_reference()`
  - Method `.test_welch_degenerate_group()`
  - Method `.test_welch_zero_variance()`
  - Method `.test_mann_whitney_exact_matches_reference()`
  - Method `.test_mann_whitney_uses_asymptotic_with_ties()`
  - Method `.test_mann_whitney_empty()`
  - Method `.test_effect_size_matches_reference()`
  - Method `.test_effect_size_needs_two_values_per_group()`
- `class IntervalTests`
  - Method `.test_bootstrap_is_seeded_and_reproducible()`
  - Method `.test_bootstrap_brackets_the_difference()`
  - Method `.test_bootstrap_empty()`
- `class RegressionTests`
  - Method `.test_linregress_matches_reference()`
  - Method `.test_linregress_ignores_non_finite_points()`
  - Method `.test_linregress_too_few_points()`
  - Method `.test_linregress_flat_line()`
- `class HolmTests`
  - Method `.test_holm_adjusts_step_down()`
  - Method `.test_holm_enforces_monotonicity()`
  - Method `.test_holm_empty()`
  - Method `.test_holm_rejects_at_the_boundary()`
- `class CompareTests`
  - Method `.test_significant_difference_with_agreeing_tests()`
  - Method `.test_small_groups_warn()`
  - Method `.test_zero_variance_warns()`
  - Method `.test_ties_are_disclosed()`

---

### [`tests/test_synthesis.py`](tests/test_synthesis.py)
> *Consensus weighting and generated reports.*

**Size**: `202` lines (`9381` bytes)

**Classes:**
- `class SynthesisTests`
  - Method `._question_with_opposition()`
  - Method `.test_consensus_weights_status_and_confidence()`
  - Method `.test_uncovered_question_reports_insufficient_instead_of_a_number()`
  - Method `.test_single_tested_stance_cannot_crown_a_claim()`
  - Method `.test_single_source_cannot_crown_a_claim()`
  - Method `.test_covered_question_displays_its_consensus()`
  - Method `.test_report_contains_evidence_and_contradictions()`
  - Method `.test_report_without_any_verdict_is_refused()`
  - Method `.test_empty_program_still_renders_scaffolding()`
  - Method `.test_report_pairs_answers_with_contradictions()`
  - Method `.test_scorecard_orders_failed_claims_first()`
  - Method `.test_claim_detail_shows_verdict_history()`
  - Method `.test_untrusted_text_cannot_break_a_table()`
  - Method `.test_inventory_counts_every_table()`
  - Method `.test_report_excludes_another_programs_findings()`
  - Method `.test_report_lists_measurements_and_the_last_run()`

---
