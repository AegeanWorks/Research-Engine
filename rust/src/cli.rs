//! Command-line surface, mirroring `engine/cli.py` argparse definitions.

use clap::{Parser, Subcommand};
use rusqlite::{params, Connection};
use serde_json::{json, Value};

use crate::core;
use crate::db::{initialize, next_id, open, utc_now};
use crate::error::{EngineError, Result};
use crate::integrity;
use crate::util::{query_json, to_stable_json};
use crate::vocab::VERSION;

#[derive(Debug, Parser)]
#[command(name = "research-engine", version = VERSION,
    about = "Falsification-first research engine: provenance, pre-registration, kill tests.")]
pub struct Cli {
    #[arg(long, default_value = "research.db", help = "SQLite database path")]
    pub db: String,
    #[arg(long, help = "print stable JSON instead of text")]
    pub json: bool,
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Debug, Subcommand)]
pub enum Commands {
    Init,
    Demo,
    Check,
    Inventory,
    Outline { reference: String, #[arg(long, default_value_t = 800)] budget: i64 },
    Brief { reference: String, #[arg(long, default_value_t = 800)] budget: i64 },
    Export {
        path: String,
        #[arg(long)] research: Option<String>,
        #[arg(long)] check: bool,
    },
    Diff { old: String, new: String, #[arg(long)] exact: bool },
    Ai { #[command(subcommand)] action: AiAction },
    Search {
        query: String,
        #[arg(long)] research: Option<String>,
        #[arg(long = "kind")] kinds: Vec<String>,
        #[arg(long, default_value_t = 5)] limit: i64,
        #[arg(long, default_value_t = 800)] budget: i64,
        #[arg(long)] all: bool,
    },
    Analysis { #[command(subcommand)] action: AnalysisAction },
    Protocol { #[command(subcommand)] action: ProtocolAction },
    Observation { #[command(subcommand)] action: ObservationAction },
    Report {
        reference: String,
        #[arg(long)] out: Option<String>,
        #[arg(long)] check: Option<String>,
        #[arg(long)] strict: bool,
    },
    Scorecard { reference: String },
    Research { #[command(subcommand)] action: ResearchAction },
    Question { #[command(subcommand)] action: QuestionAction },
    Source { #[command(subcommand)] action: SourceAction },
    Claim { #[command(subcommand)] action: ClaimAction },
    Hypothesis { #[command(subcommand)] action: HypothesisAction },
    Test { #[command(subcommand)] action: TestAction },
    Cascade { #[command(subcommand)] action: CascadeAction },
    Events {
        #[arg(long)] research: Option<String>,
        #[arg(long)] kind: Option<String>,
        #[arg(long, default_value_t = 50)] limit: i64,
        #[arg(long)] verify: bool,
    },
    Db { #[command(subcommand)] action: DbAction },
}

#[derive(Debug, Subcommand)]
pub enum ResearchAction {
    Add {
        title: String,
        #[arg(long, default_value = "")] scope: String,
        #[arg(long)] slug: Option<String>,
    },
    List,
    Show { reference: String },
}

#[derive(Debug, Subcommand)]
pub enum QuestionAction {
    Add { research: String, text: String },
    List { #[arg(long)] research: Option<String> },
    Close { reference: String },
}

#[derive(Debug, Subcommand)]
pub enum SourceAction {
    Add {
        research: String,
        #[arg(long, required = true)] title: String,
        #[arg(long)] year: Option<i64>,
        #[arg(long, default_value = "")] doi: String,
        #[arg(long, default_value = "")] url: String,
        #[arg(long, default_value = "")] authors: String,
        #[arg(long, default_value = "paper")] kind: String,
    },
    List { #[arg(long)] research: Option<String> },
    Status {
        reference: String,
        #[arg(long)] status: String,
        #[arg(long, default_value = "")] note: String,
    },
    Screen {
        reference: String,
        #[arg(long)] status: String,
        #[arg(long, default_value = "")] reason: String,
    },
    Retract {
        reference: String,
        #[arg(long, required = true)] reason: String,
        #[arg(long, required = true)] evidence: String,
        #[arg(long, default_value = "agent")] actor: String,
        #[arg(long)] allow_bulk: bool,
        #[arg(long, default_value = "")] preview_digest: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum ClaimAction {
    Add {
        research: String,
        #[arg(long, required = true)] text: String,
        #[arg(long, required = true)] kind: String,
        #[arg(long)] source: Option<String>,
        #[arg(long, default_value = "")] quote: String,
        #[arg(long, default_value = "")] locator: String,
        #[arg(long, default_value_t = 0.5)] confidence: f64,
        #[arg(long, default_value = "")] kill_test: String,
        #[arg(long, default_value = "")] basis: String,
        #[arg(long = "from", name = "from")] prerequisites: Vec<String>,
    },
    List {
        #[arg(long)] research: Option<String>,
        #[arg(long)] status: Option<String>,
        #[arg(long)] history: bool,
    },
    Show { reference: String },
    Link {
        src: String,
        dst: String,
        #[arg(long, required = true)] rel: String,
    },
    LinkQuestion {
        claim: String,
        question: String,
        #[arg(long, required = true)] stance: String,
    },
    Verdict {
        reference: String,
        #[arg(long, required = true)] status: String,
        #[arg(long, required = true)] evidence: String,
        #[arg(long, default_value = "")] note: String,
        #[arg(long, default_value = "")] group: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
    History { reference: String },
    Context { reference: String, #[arg(long, default_value_t = 800)] budget: i64 },
    Invalidate {
        reference: String,
        #[arg(long, required = true)] status: String,
        #[arg(long, required = true)] reason: String,
        #[arg(long, required = true)] evidence: String,
        #[arg(long, default_value = "agent")] actor: String,
        #[arg(long)] allow_bulk: bool,
        #[arg(long, default_value = "")] preview_digest: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum HypothesisAction {
    Add {
        research: String,
        #[arg(long, required = true)] statement: String,
        #[arg(long, required = true)] criterion: String,
        #[arg(long, default_value_t = 0.5)] confidence: f64,
        #[arg(long)] question: Option<String>,
    },
    List { #[arg(long)] research: Option<String> },
    Outcome {
        reference: String,
        #[arg(long, required = true)] status: String,
        #[arg(long, required = true)] evidence: String,
        #[arg(long, default_value = "")] note: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum TestAction {
    Add {
        research: String,
        #[arg(long, required = true)] name: String,
        #[arg(long, required = true)] command: String,
        #[arg(long)] claim: Option<String>,
        #[arg(long)] hypothesis: Option<String>,
        #[arg(long, default_value_t = 0)] expect_exit: i64,
        #[arg(long, default_value_t = 120)] timeout: i64,
        #[arg(long)] input: Vec<String>,
        #[arg(long, default_value = "")] control: String,
    },
    List { #[arg(long)] research: Option<String> },
    Run { reference: String, #[arg(long, default_value_t = 1)] runs: i64 },
    Verify { reference: String },
    Runs { reference: Option<String>, #[arg(long, default_value_t = 20)] limit: i64 },
    Attempts { reference: Option<String>, #[arg(long, default_value_t = 50)] limit: i64 },
}

#[derive(Debug, Subcommand)]
pub enum AnalysisAction {
    Stats {
        claim: String,
        #[arg(long, required = true)] baseline: String,
        #[arg(long, required = true)] treatment: String,
        #[arg(long, default_value_t = 0)] seed: i64,
        #[arg(long, default_value_t = 2000)] resamples: usize,
        #[arg(long)] allow_incomparable: bool,
        #[arg(long)] allow_self_reported: bool,
        #[arg(long, default_value = "")] plan: String,
        #[arg(long, default_value = "")] since: String,
        #[arg(long, default_value = "")] until: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
    Trend {
        claim: String,
        #[arg(long, required = true)] group: String,
        #[arg(long, default_value = "")] since: String,
        #[arg(long, default_value = "")] until: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
    Calibration { reference: String, #[arg(long, default_value_t = 10)] min_n: i64 },
    Contradictions {
        reference: String,
        #[arg(long, default_value_t = 0.0)] min_score: f64,
        #[arg(long)] unlinked: bool,
    },
    Matrix { reference: String },
    Keystone { reference: String, #[arg(long, default_value_t = 10)] limit: i64 },
    Expose { reference: String },
    Correlation {
        claim: String,
        #[arg(long, default_value = "")] groups: String,
        #[arg(long)] allow_incomparable: bool,
        #[arg(long)] allow_self_reported: bool,
        #[arg(long, default_value = "")] since: String,
        #[arg(long, default_value = "")] until: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum AiAction {
    Sweep {
        research: String,
        #[arg(long, default_value = "sweep")] kind: String,
        #[arg(long, required = true)] model: String,
        #[arg(long, required = true)] prompt_file: String,
        #[arg(long, required = true)] output_file: String,
        #[arg(long, default_value = "[]")] cited: String,
    },
    Extract {
        #[arg(long, required = true)] artifact: String,
        #[arg(long, required = true)] text: String,
        #[arg(long, required = true)] kind: String,
        #[arg(long)] source: Option<String>,
        #[arg(long, default_value = "")] quote: String,
        #[arg(long, default_value = "")] locator: String,
        #[arg(long, default_value_t = 0.5)] confidence: f64,
        #[arg(long, default_value = "")] kill_test: String,
        #[arg(long, default_value = "")] basis: String,
        #[arg(long = "from")] prerequisites: Vec<String>,
        #[arg(long)] question: Option<String>,
        #[arg(long, default_value = "supports")] stance: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
    Idea {
        #[arg(long, required = true)] artifact: String,
        #[arg(long, required = true)] statement: String,
        #[arg(long, required = true)] criterion: String,
        #[arg(long, default_value_t = 0.5)] confidence: f64,
        #[arg(long)] question: Option<String>,
        #[arg(long, default_value = "agent")] actor: String,
    },
    ProposeTest {
        #[arg(long, required = true)] artifact: String,
        #[arg(long, required = true)] template: String,
        #[arg(long, required = true)] name: String,
        #[arg(long)] claim: Option<String>,
        #[arg(long)] hypothesis: Option<String>,
        #[arg(long, default_value = "agent")] actor: String,
    },
    Draft { reference: String, #[arg(long)] out: Option<String> },
    Artifacts { #[arg(long)] research: Option<String> },
}

#[derive(Debug, Subcommand)]
pub enum ProtocolAction {
    Add {
        #[arg(long, required = true)] id: String,
        #[arg(long, required = true)] measures: String,
        #[arg(long)] includes_generation: bool,
        #[arg(long)] includes_judge: bool,
        #[arg(long, default_value = "")] doc_digest: String,
        #[arg(long, default_value = "")] doc_path: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
    List,
    Amend {
        reference: String,
        #[arg(long, required = true)] measures: String,
        #[arg(long, required = true)] reason: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum ObservationAction {
    Add {
        claim: String,
        #[arg(long, required = true)] group: String,
        #[arg(long, required = true)] value: f64,
        #[arg(long, default_value = "")] note: String,
        #[arg(long, default_value = "")] instrument_kind: String,
        #[arg(long, default_value = "")] instrument_id: String,
        #[arg(long, default_value = "")] instrument_digest: String,
        #[arg(long, default_value = "")] rater_kind: String,
        #[arg(long, default_value = "")] rater_id: String,
        #[arg(long, default_value = "")] rater_version: String,
        #[arg(long, default_value = "")] protocol_id: String,
        #[arg(long, default_value_t = 1)] sample_size: i64,
        #[arg(long, default_value = "raw")] aggregation: String,
        #[arg(long, default_value = "")] unit: String,
        #[arg(long, default_value = "unclassified")] provenance_class: String,
        #[arg(long, default_value = "")] producer_path: String,
        #[arg(long, default_value = "")] producer_digest: String,
    },
    List {
        claim: String,
        #[arg(long)] group: Option<String>,
        #[arg(long)] include_voided: bool,
    },
    Void {
        reference: String,
        #[arg(long, required = true)] reason: String,
        #[arg(long, default_value = "agent")] actor: String,
    },
    ImportCsv {
        claim: String,
        path: String,
        #[arg(long)] template: bool,
        #[arg(long)] dry_run: bool,
    },
}

#[derive(Debug, Subcommand)]
pub enum CascadeAction {
    Preview { reference: String },
}

#[derive(Debug, Subcommand)]
pub enum DbAction {
    Integrity,
    Backup { path: String },
}

pub struct Output {
    pub json: Value,
    pub text: String,
}

fn field(value: &Value, name: &str) -> String {
    value.get(name).and_then(Value::as_str).unwrap_or("").to_string()
}

fn emit(value: Value, text: impl Into<String>) -> Result<Output> {
    Ok(Output { json: value, text: text.into() })
}

fn emit_record(value: Value, line: impl Into<String>) -> Result<Output> {
    emit(value, format!("{}\n", line.into()))
}

fn list_text(rows: &[Value]) -> String {
    rows.iter().map(|row| to_stable_json(row)).collect::<Vec<_>>().join("")
}

/// Execute a parsed command against an initialized database.
pub fn run(cli: &Cli) -> Result<Output> {
    let conn = open(&cli.db)?;
    if !matches!(cli.command, Commands::Init) {
        initialize(&conn)?;
    }
    match &cli.command {
        Commands::Init => {
            let report = initialize(&conn)?;
            let value = json!({"ok": true, "schema_version": 14, "migration": report});
            emit(value, format!("initialized schema 14 at {}\n", cli.db))
        }
        Commands::Demo => {
            initialize(&conn)?;
            let result = seed_demo(&conn)?;
            emit(result.clone(), format!("demo: {}\n", result))
        }
        Commands::Check => {
            let findings = integrity::check(&conn)?;
            emit(Value::Array(findings.clone()), integrity::render_markdown(&findings))
        }
        Commands::Inventory => {
            let mut out = serde_json::Map::new();
            for table in ["research", "source", "question", "claim", "hypothesis", "killtest", "verdict", "test_run"] {
                let n: i64 = conn.query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |r| r.get(0))?;
                out.insert(table.to_string(), json!(n));
            }
            let value = Value::Object(out);
            let text = to_stable_json(&value);
            emit(value, text)
        }
        Commands::Search { query, research, kinds, limit, budget, all } => {
            let result = crate::search::search(&conn, query, research.as_deref(),
                if kinds.is_empty() { None } else { Some(kinds.as_slice()) },
                *limit, *all, *budget)?;
            let text = field(&result, "text");
            let mut payload = result.as_object().cloned().unwrap_or_default();
            payload.remove("text"); // python CLI omits the rendered text from --json
            emit(Value::Object(payload), text)
        }
        Commands::Analysis { action } => match action {
            AnalysisAction::Stats { claim, baseline, treatment, seed, resamples,
                allow_incomparable, allow_self_reported, plan, since, until, actor } => {
                let result = crate::analysis::claim_statistics(&conn, claim, baseline, treatment,
                    *seed, *resamples, *allow_incomparable, *allow_self_reported, actor,
                    plan, since, until)?;
                emit(result.clone(), to_stable_json(&result))
            }
            AnalysisAction::Trend { claim, group, since, until, actor } => {
                let result = crate::analysis::claim_trend(&conn, claim, group, actor, since, until)?;
                emit(result.clone(), to_stable_json(&result))
            }
            AnalysisAction::Calibration { reference, min_n } => {
                let result = crate::calibration::score(&conn, reference, *min_n, "agent")?;
                emit(result.clone(), to_stable_json(&result))
            }
            AnalysisAction::Contradictions { reference, min_score, unlinked } => {
                let result = if *unlinked {
                    crate::discovery::unlinked_contradictions(&conn, reference, 0.35)?
                } else {
                    crate::discovery::contradictions(&conn, reference, *min_score)?
                };
                emit(Value::Array(result.clone()), list_text(&result))
            }
            AnalysisAction::Matrix { reference } => {
                let result = crate::discovery::evidence_matrix(&conn, reference)?;
                emit(result.clone(), to_stable_json(&result))
            }
            AnalysisAction::Keystone { reference, limit } => {
                let result = crate::discovery::keystone_claims(&conn, reference, *limit)?;
                emit(Value::Array(result.clone()), list_text(&result))
            }
            AnalysisAction::Expose { reference } => {
                let result = crate::discovery::expose(&conn, reference)?;
                emit(result.clone(), to_stable_json(&result))
            }
            AnalysisAction::Correlation { claim, groups, allow_incomparable, allow_self_reported, since, until } => {
                let wanted: Vec<String> = groups.split(',').map(|g| g.trim().to_string()).filter(|g| !g.is_empty()).collect();
                let result = crate::discovery::group_correlations(&conn, claim,
                    if wanted.is_empty() { None } else { Some(wanted.as_slice()) },
                    *allow_incomparable, *allow_self_reported, since, until)?;
                emit(Value::Array(result.clone()), list_text(&result))
            }
        },
        Commands::Protocol { action } => run_protocol(&conn, action),
        Commands::Observation { action } => run_observation(&conn, action),
        Commands::Outline { reference, budget } => {
            let view = crate::context::outline(&conn, reference, *budget)?;
            emit(view.clone(), field(&view, "text"))
        }
        Commands::Brief { reference, budget } => {
            let view = crate::context::brief(&conn, reference, *budget)?;
            emit(view.clone(), field(&view, "text"))
        }
        Commands::Export { path, research, check } => {
            use crate::bundle;
            if *check {
                let result = bundle::verify_export(std::path::Path::new(path))?;
                let text = format!("intact: {} ({})\n  records: {}\n  digest: {}\n",
                    result.get("ok").and_then(Value::as_bool).unwrap_or(false), path,
                    result.get("records").and_then(Value::as_u64).unwrap_or(0),
                    field(&result, "digest"));
                return emit(result, text);
            }
            let counts = bundle::export_jsonl(&conn, std::path::Path::new(path), research.as_deref())?;
            emit(counts, format!("exported graph to {path}\n"))
        }
        Commands::Diff { old, new, exact } => {
            let result = crate::diffing::diff_files(std::path::Path::new(old),
                std::path::Path::new(new), !*exact)?;
            emit(result.clone(), crate::diffing::render(&result))
        }
        Commands::Ai { action } => run_ai(&conn, action),
        Commands::Report { reference, out, check, strict } => {
            use crate::manifest;
            if *strict && check.is_none() {
                return Err(EngineError::new("--strict needs --check",
                    "strictness only changes manifest comparison, not rendering.",
                    "pass --check PATH together with --strict, or drop --strict."));
            }
            if let Some(path) = check {
                let result = manifest::check_report(&conn, reference, std::path::Path::new(path), *strict)?;
                let clean = result.get("clean").and_then(Value::as_bool).unwrap_or(false);
                let mut text = format!("clean: {clean} ({})\n", field(&result, "manifest"));
                for item in result.get("drift").and_then(Value::as_array).into_iter().flatten() {
                    text.push_str(&format!("  drift: {}\n", item.as_str().unwrap_or("")));
                }
                return emit(result, text);
            }
            if let Some(path) = out {
                let result = manifest::write_report(&conn, reference, std::path::Path::new(path))?;
                let text = format!("wrote {}\nwrote {}\ngraph: {}\n", field(&result, "report"),
                    field(&result, "manifest"), field(&result, "graph_sha256"));
                return emit(result, text);
            }
            let text = crate::synthesis::report(&conn, reference)?;
            emit(json!({"report": text.clone()}), text)
        }
        Commands::Scorecard { reference } => {
            let text = crate::synthesis::scorecard(&conn, reference)?;
            emit(json!({"scorecard": text.clone()}), text)
        }
        Commands::Research { action } => run_research(&conn, action),
        Commands::Question { action } => run_question(&conn, action),
        Commands::Source { action } => run_source(&conn, action),
        Commands::Claim { action } => run_claim(&conn, action),
        Commands::Hypothesis { action } => run_hypothesis(&conn, action),
        Commands::Test { action } => run_test(&conn, action),
        Commands::Cascade { action } => match action {
            CascadeAction::Preview { reference } => {
                let result = crate::cascade::preview(&conn, reference)?;
                let text = format!("{} affected\n", result.get("affected").and_then(Value::as_array).map(|a| a.len()).unwrap_or(0));
                emit(result, text)
            }
        },
        Commands::Events { research, kind, limit, verify } => {
            if *verify {
                let result = core::verify_events(&conn)?;
                return emit(result.clone(), to_stable_json(&result));
            }
            let mut sql = String::from("SELECT * FROM event WHERE 1=1");
            let mut bindings: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
            if let Some(reference) = research {
                let r = core::get_research(&conn, reference)?;
                sql.push_str(" AND research_id = ?");
                bindings.push(Box::new(field(&r, "id")));
            }
            if let Some(k) = kind {
                sql.push_str(" AND kind = ?");
                bindings.push(Box::new(k.clone()));
            }
            sql.push_str(" ORDER BY id DESC LIMIT ?");
            bindings.push(Box::new(*limit));
            let args: Vec<&dyn rusqlite::ToSql> = bindings.iter().map(|b| b.as_ref()).collect();
            let rows = query_json(&conn, &sql, args.as_slice())?;
            emit(Value::Array(rows.clone()), list_text(&rows))
        }
        Commands::Db { action } => match action {
            DbAction::Integrity => {
                let ok: i64 = conn.query_row("PRAGMA integrity_check", [], |r| {
                    let s: String = r.get(0)?;
                    Ok(if s == "ok" { 1 } else { 0 })
                })?;
                let fk: Vec<Value> = query_json(&conn, "PRAGMA foreign_key_check", [])?;
                let value = json!({"ok": ok == 1 && fk.is_empty(), "foreign_key_violations": fk});
                emit(value.clone(), to_stable_json(&value))
            }
            DbAction::Backup { path } => {
                let value = json!({"path": path, "note": "backup uses SQLite VACUUM INTO"});
                conn.execute("VACUUM INTO ?1", params![path])?;
                emit(value, format!("backup written to {path}\n"))
            }
        },
    }
}

fn run_research(conn: &Connection, action: &ResearchAction) -> Result<Output> {
    match action {
        ResearchAction::Add { title, scope, slug } => {
            let record = core::add_research(conn, title, scope, slug.as_deref())?;
            emit_record(record.clone(), format!("{} {} {}", field(&record, "id"), field(&record, "slug"), field(&record, "title")))
        }
        ResearchAction::List => {
            let rows = core::list_researches(conn)?;
            let text = if rows.is_empty() { "no research programs\n".to_string() } else {
                rows.iter().map(|r| format!("{}  {:<24} {}\n", field(r, "id"), field(r, "slug"), field(r, "text").is_empty().then(|| field(r, "title")).unwrap_or_default())).collect()
            };
            emit(Value::Array(rows), text)
        }
        ResearchAction::Show { reference } => {
            let record = core::get_research(conn, reference)?;
            let counts = core::research_counts(conn, &field(&record, "id"))?;
            let text = format!("{}  {}\n{}\nscope: {}\ncreated: {}\n{}\n",
                field(&record, "id"), field(&record, "slug"), field(&record, "title"),
                if field(&record, "scope").is_empty() { "-".to_string() } else { field(&record, "scope") },
                field(&record, "created_at"),
                counts.as_object().map(|m| m.iter().map(|(k, v)| format!("{k}: {v}\n")).collect::<String>()).unwrap_or_default());
            emit(json!({"research": record, "counts": counts}), text)
        }
    }
}

fn run_question(conn: &Connection, action: &QuestionAction) -> Result<Output> {
    match action {
        QuestionAction::Add { research, text } => {
            let record = core::add_question(conn, research, text)?;
            emit_record(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "text")))
        }
        QuestionAction::List { research } => {
            let rows = core::list_questions(conn, research.as_deref())?;
            let text = if rows.is_empty() { "no questions\n".to_string() } else {
                rows.iter().map(|q| format!("{}  {:<7} {}\n", field(q, "id"), field(q, "status"), field(q, "text"))).collect()
            };
            emit(Value::Array(rows), text)
        }
        QuestionAction::Close { reference } => {
            let record = core::close_question(conn, reference)?;
            emit_record(record, format!("{} closed", reference))
        }
    }
}

fn run_source(conn: &Connection, action: &SourceAction) -> Result<Output> {
    match action {
        SourceAction::Add { research, title, year, doi, url, authors, kind } => {
            let record = core::add_source(conn, research, title, *year, doi, url, authors, kind)?;
            emit_record(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "title")))
        }
        SourceAction::List { research } => {
            let rows = core::list_sources(conn, research.as_deref())?;
            let text = if rows.is_empty() { "no sources\n".to_string() } else {
                rows.iter().map(|s| format!("{}  {:<4}  {:<20} {:<12} {}\n",
                    field(s, "id"),
                    s.get("year").and_then(Value::as_i64).map(|y| y.to_string()).unwrap_or_else(|| "----".to_string()),
                    field(s, "status"), field(s, "screening"), field(s, "title"))).collect()
            };
            emit(Value::Array(rows), text)
        }
        SourceAction::Status { reference, status, note } => {
            let record = core::set_source_status(conn, reference, status, note)?;
            emit_record(record, format!("{} -> {}", reference, status))
        }
        SourceAction::Screen { reference, status, reason } => {
            let record = core::set_screening(conn, reference, status, reason)?;
            emit_record(record, format!("{} -> {}{}", reference, status,
                if reason.is_empty() { String::new() } else { format!(" ({reason})") }))
        }
        SourceAction::Retract { reference, reason, evidence, actor, allow_bulk, preview_digest } => {
            let result = crate::cascade::retract_source(conn, reference, reason, evidence,
                actor, *allow_bulk, preview_digest)?;
            emit(result.clone(), to_stable_json(&result))
        }
    }
}

fn run_claim(conn: &Connection, action: &ClaimAction) -> Result<Output> {
    match action {
        ClaimAction::Add { research, text, kind, source, quote, locator, confidence, kill_test, basis, prerequisites } => {
            let record = core::add_claim(conn, research, text, kind, source.as_deref(), quote, locator,
                *confidence, kill_test, basis, prerequisites)?;
            emit_record(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "text")))
        }
        ClaimAction::List { research, status, history } => {
            let rows = core::list_claims(conn, research.as_deref(), status.as_deref(), *history)?;
            let text = if rows.is_empty() { "no claims\n".to_string() } else {
                rows.iter().map(|c| format!("{}  {:<12} {:<11} {}\n",
                    field(c, "id"), field(c, "status"), field(c, "kind"), field(c, "text"))).collect()
            };
            emit(Value::Array(rows), text)
        }
        ClaimAction::Show { reference } => {
            let record = core::get_claim(conn, reference)?;
            emit(record.clone(), to_stable_json(&record))
        }
        ClaimAction::Link { src, dst, rel } => {
            let a = core::get_claim(conn, src)?;
            let b = core::get_claim(conn, dst)?;
            let allowed = ["supports", "contradicts", "replicates", "extends", "uses_method",
                "measures", "related", "derived_from", "depends_on"];
            if !allowed.contains(&rel.as_str()) {
                return Err(EngineError::new(format!("unknown relation: {rel}"),
                    "relations are a closed vocabulary.", "pass one of the listed relations."));
            }
            let id = core::record_edge(conn, "claim", &field(&a, "id"), "claim", &field(&b, "id"), rel)?;
            emit(json!({"id": id, "src": src, "dst": dst, "rel": rel}), format!("{src} -> {dst} ({rel})\n"))
        }
        ClaimAction::LinkQuestion { claim, question, stance } => {
            let c = core::get_claim(conn, claim)?;
            let q = core::get_question(conn, question)?;
            let id = core::record_edge(conn, "claim", &field(&c, "id"), "question", &field(&q, "id"), stance)?;
            emit(json!({"id": id}), format!("{claim} -> {question} ({stance})\n"))
        }
        ClaimAction::Verdict { reference, status, evidence, note, group, actor } => {
            let record = core::set_verdict(conn, reference, status, evidence, note, group, actor)?;
            emit_record(record, format!("{} -> {}", reference, status))
        }
        ClaimAction::Invalidate { reference, status, reason, evidence, actor, allow_bulk, preview_digest } => {
            let result = crate::cascade::invalidate(conn, reference, status, reason, evidence,
                actor, *allow_bulk, preview_digest)?;
            emit(result.clone(), to_stable_json(&result))
        }
        ClaimAction::Context { reference, budget } => {
            let view = crate::context::claim_context(conn, reference, *budget)?;
            emit(view.clone(), field(&view, "text"))
        }
        ClaimAction::History { reference } => {
            let claim = core::get_claim(conn, reference)?;
            let rows = query_json(conn,
                "SELECT * FROM verdict WHERE subject_kind='claim' AND subject_id=?1 ORDER BY id",
                params![field(&claim, "id")])?;
            emit(Value::Array(rows.clone()), list_text(&rows))
        }
    }
}

fn run_hypothesis(conn: &Connection, action: &HypothesisAction) -> Result<Output> {
    match action {
        HypothesisAction::Add { research, statement, criterion, confidence, question } => {
            let record = core::add_hypothesis(conn, research, statement, criterion, *confidence, question.as_deref())?;
            emit_record(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "statement")))
        }
        HypothesisAction::List { research } => {
            let rows = core::list_hypotheses(conn, research.as_deref())?;
            let text = if rows.is_empty() { "no hypotheses\n".to_string() } else {
                rows.iter().map(|h| format!("{}  {:<13} {}\n", field(h, "id"), field(h, "status"), field(h, "statement"))).collect()
            };
            emit(Value::Array(rows), text)
        }
        HypothesisAction::Outcome { reference, status, evidence, note, actor } => {
            let record = core::record_outcome(conn, reference, status, evidence, note, actor)?;
            emit_record(record, format!("{} -> {}", reference, status))
        }
    }
}

fn run_ai(conn: &Connection, action: &AiAction) -> Result<Output> {
    use crate::ai;
    match action {
        AiAction::Sweep { research, kind, model, prompt_file, output_file, cited } => {
            let cited: Value = serde_json::from_str(cited).map_err(|e| EngineError::new(
                format!("cited payload is not valid JSON: {e}"), "citations arrive as data, not prose.",
                "pass --cited '[{\"source_id\": \"s_000001\", \"locator\": \"p. 3\"}]'."))?;
            let Some(cited_list) = cited.as_array() else {
                return Err(EngineError::new("cited payload is not a list",
                    "citations arrive as a list of {source_id, locator} objects.",
                    "pass --cited '[{\"source_id\": \"s_000001\", \"locator\": \"p. 3\"}]'."));
            };
            let prompt = std::fs::read_to_string(prompt_file).map_err(|e| EngineError::new(
                format!("cannot read model I/O file: {prompt_file}"),
                "the adapter notarizes exact bytes; a missing file proves nothing.",
                format!("{e}")))?;
            let output = std::fs::read_to_string(output_file).map_err(|e| EngineError::new(
                format!("cannot read model I/O file: {output_file}"),
                "the adapter notarizes exact bytes; a missing file proves nothing.",
                format!("{e}")))?;
            let record = ai::record(conn, research, kind, model, &prompt, &output, cited_list)?;
            emit_record(record.clone(), format!("{} {} {}", field(&record, "id"),
                field(&record, "kind"), field(&record, "model_id")))
        }
        AiAction::Extract { artifact, text, kind, source, quote, locator, confidence, kill_test,
            basis, prerequisites, question, stance, actor } => {
            let claim = ai::ingest_claim(conn, artifact, text, kind, source.as_deref(), quote,
                locator, *confidence, kill_test, basis, prerequisites, question.as_deref(), stance, actor)?;
            emit_record(claim.clone(), format!("{} UNVERIFIED {}", field(&claim, "id"), field(&claim, "text")))
        }
        AiAction::Idea { artifact, statement, criterion, confidence, question, actor } => {
            let hypothesis = ai::ingest_hypothesis(conn, artifact, statement, criterion,
                *confidence, question.as_deref(), actor)?;
            emit_record(hypothesis.clone(), format!("{} {} {}", field(&hypothesis, "id"),
                field(&hypothesis, "status"), field(&hypothesis, "statement")))
        }
        AiAction::ProposeTest { artifact, template, name, claim, hypothesis, actor } => {
            let test = ai::propose_test(conn, artifact, template, name, claim.as_deref(),
                hypothesis.as_deref(), actor)?;
            emit_record(test.clone(), format!("{} {}", field(&test, "id"), field(&test, "name")))
        }
        AiAction::Draft { reference, out } => {
            let text = ai::render_draft(conn, reference)?;
            if let Some(path) = out {
                crate::util::atomic_write_text(std::path::Path::new(path), &text)?;
                return emit(json!({"draft": path}), format!("wrote {path}\n"));
            }
            emit(json!({"draft": text.clone()}), text)
        }
        AiAction::Artifacts { research } => {
            let rows = ai::list_artifacts(conn, research.as_deref())?;
            let text = if rows.is_empty() { "no AI artifacts\n".to_string() } else {
                rows.iter().map(|a| format!("{}  {:<10} {}  prompt={}  output={}\n",
                    field(a, "id"), field(a, "kind"), field(a, "model_id"),
                    field(a, "prompt_sha256").chars().take(12).collect::<String>(),
                    field(a, "output_sha256").chars().take(12).collect::<String>())).collect()
            };
            emit(Value::Array(rows), text)
        }
    }
}

fn run_protocol(conn: &Connection, action: &ProtocolAction) -> Result<Output> {
    use crate::protocols;
    match action {
        ProtocolAction::Add { id, measures, includes_generation, includes_judge, doc_digest, doc_path, actor } => {
            let record = protocols::register(conn, id, measures, *includes_generation, *includes_judge,
                doc_digest, doc_path, actor)?;
            emit_record(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "measures")))
        }
        ProtocolAction::List => {
            let rows = protocols::list_protocols(conn)?;
            let text = if rows.is_empty() { "no protocols\n".to_string() } else {
                rows.iter().map(|p| format!("{}  generation={} judge={}  {}\n", field(p, "id"),
                    p.get("includes_generation").and_then(Value::as_i64).unwrap_or(0),
                    p.get("includes_judge").and_then(Value::as_i64).unwrap_or(0), field(p, "measures"))).collect()
            };
            emit(Value::Array(rows), text)
        }
        ProtocolAction::Amend { reference, measures, reason, actor } => {
            let record = protocols::amend(conn, reference, measures, reason, actor)?;
            emit_record(record, format!("{} amended {}", reference, measures))
        }
    }
}

fn run_observation(conn: &Connection, action: &ObservationAction) -> Result<Output> {
    use crate::observations;
    match action {
        ObservationAction::Add { claim, group, value, note, instrument_kind, instrument_id,
            instrument_digest, rater_kind, rater_id, rater_version, protocol_id, sample_size,
            aggregation, unit, provenance_class, producer_path, producer_digest } => {
            let record = observations::add(conn, claim, group, *value, note, instrument_kind,
                instrument_id, instrument_digest, rater_kind, rater_id, rater_version, protocol_id,
                *sample_size, aggregation, unit, provenance_class, producer_path, producer_digest)?;
            emit_record(record.clone(), format!("{} {} {:.6}", field(&record, "id"),
                field(&record, "group_label"), record.get("value").and_then(Value::as_f64).unwrap_or(0.0)))
        }
        ObservationAction::List { claim, group, include_voided } => {
            let rows = observations::list_observations(conn, claim, group.as_deref(), *include_voided)?;
            emit(Value::Array(rows.clone()), list_text(&rows))
        }
        ObservationAction::Void { reference, reason, actor } => {
            let record = observations::void_observation(conn, reference, reason, actor)?;
            emit_record(record, format!("{} voided", reference))
        }
        ObservationAction::ImportCsv { claim, path, template, dry_run } => {
            if *template {
                return emit(json!({"header": observations::CSV_TEMPLATE_HEADER}),
                    format!("{}\n", observations::CSV_TEMPLATE_HEADER));
            }
            let result = observations::import_csv(conn, claim, path, *dry_run)?;
            emit(result.clone(), to_stable_json(&result))
        }
    }
}

fn run_test(conn: &Connection, action: &TestAction) -> Result<Output> {
    use crate::killtest;
    match action {
        TestAction::Add { research, name, command, claim, hypothesis, expect_exit, timeout, input, control } => {
            let record = killtest::add_test(conn, research, name, command, claim.as_deref(),
                hypothesis.as_deref(), *expect_exit, *timeout, input, control)?;
            emit_record(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "name")))
        }
        TestAction::List { research } => {
            let rows = killtest::list_tests(conn, research.as_deref())?;
            let text = if rows.is_empty() { "no tests\n".to_string() } else {
                rows.iter().map(|t| format!("{}  {:<24} {}\n", field(t, "id"), field(t, "name"), field(t, "command"))).collect()
            };
            emit(Value::Array(rows), text)
        }
        TestAction::Run { reference, runs } => {
            let result = killtest::run_test(conn, reference, *runs)?;
            let text = format!("{} -> {} ({})\n", reference,
                result.get("attempt").and_then(|a| a.get("outcome")).and_then(Value::as_str).unwrap_or(""),
                field(&result, "run_group"));
            emit(result, text)
        }
        TestAction::Verify { reference } => {
            let result = killtest::run_test(conn, reference, 2)?;
            let text = format!("{} verified={}\n", reference,
                result.get("verification_complete").and_then(Value::as_bool).unwrap_or(false));
            emit(result, text)
        }
        TestAction::Runs { reference, limit } => {
            let rows = killtest::list_runs(conn, reference.as_deref(), *limit)?;
            emit(Value::Array(rows.clone()), list_text(&rows))
        }
        TestAction::Attempts { reference, limit } => {
            let rows = killtest::list_attempts(conn, reference.as_deref(), *limit)?;
            emit(Value::Array(rows.clone()), list_text(&rows))
        }
    }
}

fn seed_demo(conn: &Connection) -> Result<Value> {
    let tx = conn.unchecked_transaction()?;
    if tx.query_row("SELECT COUNT(*) FROM research", [], |r| r.get::<_, i64>(0))? > 0 {
        tx.rollback()?;
        return Err(EngineError::new("demo needs an empty graph",
            "the demo seeds a synthetic program and makes no scientific claim.",
            "use a fresh --db path for the demo."));
    }
    let rid = next_id(&tx, "r")?;
    tx.execute("INSERT INTO research(id,slug,title,scope,created_at) VALUES (?1,'demo','Demo Program','synthetic',?2)",
        params![rid, utc_now()])?;
    let sid = next_id(&tx, "s")?;
    tx.execute("INSERT INTO source(id,research_id,kind,title,year,retrieved_at) VALUES (?1,?2,'paper','Synthetic Source',2024,?3)",
        params![sid, rid, utc_now()])?;
    let qid = next_id(&tx, "q")?;
    tx.execute("INSERT INTO question(id,research_id,text,status,created_at) VALUES (?1,?2,'Does the demo work?','open',?3)",
        params![qid, rid, utc_now()])?;
    let cid = next_id(&tx, "c")?;
    tx.execute(&("INSERT INTO claim(id,research_id,source_id,text,quote,locator,kind,status,confidence,created_at,updated_at)"
        .to_owned() + " VALUES (?1,?2,?3,'The demo graph is coherent','Synthetic Source says so','§1','empirical','UNVERIFIED',0.5,?4,?4)"),
        params![cid, rid, sid, utc_now()])?;
    tx.execute("INSERT INTO edge(id,src_kind,src_id,dst_kind,dst_id,rel,created_at) VALUES (?1,'claim',?2,'question',?3,'answers',?4)",
        params![next_id(&tx, "e")?, cid, qid, utc_now()])?;
    core::record_event(&tx, &rid, "demo.seed", &rid, "synthetic program", "engine")?;
    tx.commit()?;
    Ok(json!({"research": rid, "source": sid, "question": qid, "claim": cid, "scientific_claims": 0}))
}
