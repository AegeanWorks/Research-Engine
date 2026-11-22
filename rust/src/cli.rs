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
    Experiment { #[command(subcommand)] action: ExperimentAction },
    Lattice { #[command(subcommand)] action: LatticeAction },
    LatticeRepo { #[command(subcommand)] action: LatticeRepoAction },
    LatticeSnap { #[command(subcommand)] action: LatticeSnapAction },
    Meta { #[command(subcommand)] action: MetaAction },
    LatticeQuery { #[command(subcommand)] action: LatticeQueryAction },
    Discovery { #[command(subcommand)] action: DiscoveryAction },
    Studio { #[command(subcommand)] action: StudioAction },
    Mcp { message: String },
    Web { method: String, path: String, #[arg(long, default_value = "")] body: String },
    Atlas { #[command(subcommand)] action: AtlasAction },
    PnnSafety { #[arg(long, required = true)] tox: String, #[arg(long, default_value = "{}")] pharm: String },
    Client { #[command(subcommand)] action: ClientAction },
    FluidBridge { #[command(subcommand)] action: FluidBridgeAction },
    FluidFrankOseen { #[command(subcommand)] action: FluidFrankOseenAction },
    FluidVortexCore { #[command(subcommand)] action: FluidVortexCoreAction },
    HydrogenRadial { #[command(subcommand)] action: HydrogenRadialAction },
    FluidTopology { #[command(subcommand)] action: FluidTopologyAction },
    FluidCirculant { #[command(subcommand)] action: FluidCirculantAction },
    FluidReduction { #[command(subcommand)] action: FluidReductionAction },
    FluidVariationalWidth { #[command(subcommand)] action: FluidVariationalWidthAction },
    FluidNelsonClosure { #[command(subcommand)] action: FluidNelsonClosureAction },
    FluidConvergence { #[command(subcommand)] action: FluidConvergenceAction },
    Obezite { #[command(subcommand)] action: ObeziteAction },
    PnnRules { #[command(subcommand)] action: PnnRulesAction },
    PnnDocking { #[command(subcommand)] action: PnnDockingAction },
    PnnCompounds { #[command(subcommand)] action: PnnCompoundsAction },
    PnnScreen { #[command(subcommand)] action: PnnScreenAction },
    Providers { #[command(subcommand)] action: ProvidersAction },
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
pub enum ProvidersAction {
    Url { source: String, query: String, #[arg(long, default_value_t = 10)] limit: i64 },
    Parse { source: String, #[arg(long, required = true)] payload_file: String, #[arg(long, default_value_t = 10)] limit: i64 },
}

#[derive(Debug, Subcommand)]
pub enum PnnRulesAction {
    Evaluate { #[arg(long, required = true)] compound: String },
    Weight { criterion: String },
}

#[derive(Debug, Subcommand)]
pub enum PnnScreenAction {
    Evaluate { #[arg(long, required = true)] compound: String },
    Rank { #[arg(long, required = true)] compounds: String },
    Summary { #[arg(long, required = true)] compounds: String },
}

#[derive(Debug, Subcommand)]
pub enum PnnCompoundsAction {
    Parse {
        #[arg(long, required = true)] rows: String,
        #[arg(long, default_value = "input")] source: String,
        #[arg(long, default_value_t = false)] allow_duplicates: bool,
    },
    Field { name: String },
}

#[derive(Debug, Subcommand)]
pub enum PnnDockingAction {
    /// Parse raw docking rows from a JSON file into score records.
    Parse { #[arg(long, required = true)] rows: String, #[arg(long, default_value = "input")] source: String },
    /// Parse, filter, normalize and aggregate docking rows into per-compound best targets.
    Rank {
        #[arg(long, required = true)] rows: String,
        #[arg(long)] max_rmsd: Option<f64>,
        #[arg(long)] min_vina: Option<f64>,
    },
}

#[derive(Debug, Subcommand)]
pub enum ObeziteAction {
    Atiflar { text: String },
    Dedupe {
        #[arg(long, required = true)] chunks: String,
        #[arg(long, required = true)] retracted: String,
        #[arg(long, required = true)] archive: String,
        #[arg(long, required = true)] updated: String,
        #[arg(long, default_value = "")] stamp: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum FluidBridgeAction {
    Diffusivity { hbar: f64, mass: f64 },
    Horizon { omega: f64 },
    Coeffs { s0: f64, st: f64, horizon_t: f64, omega: f64, hbar: f64, mass: f64 },
    Path { #[arg(long)] coeffs: String, #[arg(long)] times: String, #[arg(long)] omega: f64 },
}

#[derive(Debug, Subcommand)]
pub enum FluidConvergenceAction {
    Scan { #[arg(long, required = true)] low: String, #[arg(long, required = true)] high: String },
    Temporal { #[arg(long, required = true)] coarse: String, #[arg(long, required = true)] fine: String },
    Trend {
        #[arg(long, required = true)] rows: String,
        #[arg(long, default_value_t = 0.5)] z3_target: f64,
        #[arg(long, default_value_t = 0.01)] force_tol: f64,
    },
}

#[derive(Debug, Subcommand)]
pub enum FluidNelsonClosureAction {
    Osmotic { #[arg(long, required = true)] xs: String, #[arg(long)] dx: f64 },
    FpResidual { #[arg(long, required = true)] xs: String, #[arg(long)] dx: f64, #[arg(long, default_value_t = 0.5)] diffusion: f64 },
    ResidualScaling,
    SigmaMap,
    Instances,
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum FluidVariationalWidthAction {
    Diffusivity { #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    ActionGm { s2: f64, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    ActionYasui { s2: f64, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    DGm { s2: f64, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    DYasui { s2: f64, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    D2S2 { s2: f64, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    D2Sigma { sigma: f64, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    Extremum { #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    Newton { start: f64, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64, #[arg(long, default_value_t = 8)] steps: usize },
    GridMax { #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    YasuiMonotone { #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    Ermakov,
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum FluidReductionAction {
    Tension { mu: f64 },
    Lower { mu: f64, length_y: f64 },
    Power { alpha: f64 },
    Finite { alpha: f64 },
    LogDivergent { alpha: f64 },
    Numeric { alpha: f64, #[arg(long, default_value_t = 1.0)] r_min: f64, #[arg(long, default_value_t = 1.0e4)] r_max: f64 },
    Verdict { #[arg(long, default_value_t = 4.0)] alpha: f64 },
    Render { #[arg(long, required = true)] payload: String },
}

#[derive(Debug, Subcommand)]
pub enum FluidTopologyAction {
    Direct,
    Extensions,
    Verdict,
    Render { #[arg(long, required = true)] payload: String },
}

#[derive(Debug, Subcommand)]
pub enum FluidCirculantAction {
    Matrix { #[arg(long)] a: f64, #[arg(long)] c: f64, #[arg(long)] delta: f64 },
    Eigenvalues { #[arg(long)] a: f64, #[arg(long)] c: f64, #[arg(long)] delta: f64 },
    Dft,
    QSigned { #[arg(long, required = true)] xs: String },
    QMasses { #[arg(long, required = true)] xs: String },
    QPhysical { #[arg(long, required = true)] xs: String },
    QFromAc { #[arg(long)] a: f64, #[arg(long)] c: f64 },
    Extract { #[arg(long, required = true)] xs: String },
    Fit { #[arg(long, required = true)] xs: String },
    Koide { #[arg(long)] me: f64, #[arg(long)] mmu: f64 },
}

#[derive(Debug, Subcommand)]
pub enum HydrogenRadialAction {
    Radial10 { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] radius: f64 },
    Radial20 { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] radius: f64 },
    Probability { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] radius: f64 },
    Branch { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] radius: f64 },
    Phase { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] radius: f64 },
    Node { #[arg(long, default_value_t = 1.0)] radius: f64 },
    Overlap { #[arg(long, default_value_t = 1.0)] radius: f64 },
    Norm { #[arg(long, default_value_t = 1.0)] radius: f64 },
    Peaks { #[arg(long, default_value_t = 1.0)] radius: f64 },
    Balance,
    Circulation { r: f64, theta: f64, m: i64, #[arg(long, default_value_t = 4000)] samples: usize },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum FluidVortexCoreAction {
    Radius,
    Sigma { #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    Norm { eps: f64, sigma: f64 },
    Density { eps: f64, sigma: f64, #[arg(long, required = true)] xs: String },
    Phase { eps: f64, #[arg(long, required = true)] xs: String },
    Velocity { eps: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64, #[arg(long, required = true)] xs: String },
    QZero { eps: f64, #[arg(long, default_value_t = 1.0)] sigma: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    FdQ { eps: f64, n: usize, #[arg(long, default_value_t = crate::domains_fluid_vortex_core::GRID_LENGTH)] length: f64, #[arg(long, default_value_t = 1.0)] sigma: f64 },
}

#[derive(Debug, Subcommand)]
pub enum FluidFrankOseenAction {
    Matrix { kx: f64, ky: f64, kz: f64, k1: f64, k2: f64, k3: f64 },
    Dispersion { kx: f64, ky: f64, kz: f64, k1: f64, k2: f64, k3: f64, #[arg(long, default_value_t = 1.0)] rho: f64 },
    Equal { k: f64, k_const: f64, #[arg(long, default_value_t = 1.0)] rho: f64 },
    Anisotropy { dx: f64, dy: f64, dz: f64, k1: f64, k2: f64, k3: f64, #[arg(long, default_value_t = 1.0)] rho: f64 },
    Modes,
}

#[derive(Debug, Subcommand)]
pub enum ClientAction {
    ToolSchemas { #[arg(long)] read_only: bool },
    ResourceSchemas,
    PromptSchemas,
    Call {
        name: String,
        #[arg(long, default_value = "{}")] arguments: String,
        #[arg(long, default_value = "{}")] kwargs: String,
        #[arg(long)] read_only: bool,
    },
    ReadResource { uri: String },
}

#[derive(Debug, Subcommand)]
pub enum AtlasAction {
    Coerce {
        #[arg(long, required = true)] payload: String,
        #[arg(long, default_value = "")] document_ref: String,
        #[arg(long, default_value_t = 0)] source_page: i64,
        #[arg(long, default_value = "")] figure_id: String,
    },
    Merge { #[arg(long, required = true)] analyses: String },
    Schema,
}

#[derive(Debug, Subcommand)]
pub enum StudioAction {
    Matrix { #[arg(long, default_value = "")] questions: String },
    Evidence { reference: String },
}

#[derive(Debug, Subcommand)]
pub enum DiscoveryAction {
    Providers,
    Offline { query: String, #[arg(long, default_value_t = 10)] limit: i64 },
    Discover {
        query: String,
        #[arg(long, default_value = "offline")] source: String,
        #[arg(long, default_value_t = 10)] limit: i64,
        #[arg(long)] no_ingest: bool,
    },
    CrossrefAuthors { authors: String },
    CrossrefYear { item: String },
    InvertedAbstract { inverted: String },
}

#[derive(Debug, Subcommand)]
pub enum LatticeQueryAction {
    Outline { #[arg(long, default_value_t = 400)] tokens: i64 },
    Contradictions { #[arg(long)] auto_link: bool },
    CompactSearch { query: String, #[arg(long, default_value_t = 20)] limit: i64, #[arg(long, default_value_t = 800)] tokens: i64 },
    ContextPack {
        #[arg(long, default_value = "")] targets: String,
        #[arg(long, default_value_t = 2000)] max_tokens: i64,
        #[arg(long, default_value = "markdown")] format: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum MetaAction {
    StudyCi {
        id: String, label: String, effect: f64, lower: f64, upper: f64,
        #[arg(long, default_value = "General Study")] study_type: String,
    },
    StudyGroups {
        id: String, label: String, n1: i64, m1: f64, sd1: f64, n2: i64, m2: f64, sd2: f64,
        #[arg(long, default_value = "Randomized Controlled Trial")] study_type: String,
    },
    Analyze { #[arg(long, required = true)] studies: String, #[arg(long, default_value = "random")] model: String },
    Forest {
        #[arg(long, required = true)] studies: String,
        #[arg(long, default_value = "random")] model: String,
        #[arg(long, default_value_t = 40)] width: usize,
    },
}

#[derive(Debug, Subcommand)]
pub enum LatticeSnapAction {
    Records,
    Export { path: String },
    Bibtex,
    Cytoscape,
    Graphml,
}

#[derive(Debug, Subcommand)]
pub enum LatticeRepoAction {
    PaperAdd {
        #[arg(long, required = true)] title: String,
        #[arg(long, default_value = "")] authors: String,
        #[arg(long, default_value = "")] year: String,
        #[arg(long, default_value = "")] venue: String,
        #[arg(long, default_value = "")] doi: String,
        #[arg(long, default_value = "")] arxiv: String,
        #[arg(long, default_value = "")] url: String,
        #[arg(long, default_value = "")] abstract_text: String,
        #[arg(long, default_value = "")] tags: String,
        #[arg(long, default_value = "")] study_type: String,
    },
    ClaimAdd {
        paper: String,
        #[arg(long, required = true)] text: String,
        #[arg(long, required = true)] quote: String,
        #[arg(long, default_value = "")] locator: String,
        #[arg(long, default_value = "mentions")] stance: String,
        #[arg(long, default_value_t = 0.5)] confidence: f64,
    },
    QuestionAdd { text: String },
    EdgeAdd { src: String, dst: String, #[arg(long, required = true)] kind: String, #[arg(long, default_value = "")] note: String },
    Get { reference: String },
    Search { query: String, #[arg(long, default_value_t = 20)] limit: i64 },
    Stats,
}

#[derive(Debug, Subcommand)]
pub enum LatticeAction {
    Normalize { text: String },
    Tags { text: String },
    DeriveTags { title: String, #[arg(long, default_value = "")] abstract_text: String, #[arg(long, default_value_t = 6)] limit: i64 },
    StudyType { text: String },
    InferStudy { title: String, #[arg(long, default_value = "")] abstract_text: String },
    PaperId { title: String, #[arg(long, default_value = "")] doi: String, #[arg(long, default_value = "")] arxiv: String },
    ParseBibtex { text: String },
    ParseRis { text: String },
    ParseCsv { text: String },
    ParseCsl { text: String },
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
pub enum ExperimentAction {
    InterventionAdd {
        research: String, name: String, start: String,
        #[arg(long, default_value = "")] projected: String,
        #[arg(long, default_value = "")] end: String,
        #[arg(long, default_value = "")] dosage: String,
        #[arg(long, default_value = "")] notes: String,
    },
    MetricDefAdd {
        research: String, name: String,
        #[arg(long, default_value = "")] description: String,
        #[arg(long, default_value = "")] unit: String,
    },
    MetricAdd {
        research: String, metric: String, date: String, value: f64,
        #[arg(long, default_value = "")] intervention: String,
        #[arg(long, default_value = "")] note: String,
    },
    EventAdd {
        research: String, name: String, timestamp: String,
        #[arg(long)] severity: Option<i64>,
        #[arg(long, default_value = "")] notes: String,
        #[arg(long, default_value = "")] intervention: String,
    },
    List { research: String, #[arg(long, default_value = "metric")] kind: String },
    Analyze {
        research: String, metric: String, start: String,
        #[arg(long, default_value_t = 14)] baseline_days: i64,
        #[arg(long, default_value_t = 14)] intervention_days: i64,
    },
    Correlation { research: String, #[arg(long, default_value = "")] metrics: String },
    Multi {
        research: String,
        #[arg(long, required = true)] metrics: String,
        start: String,
        #[arg(long, default_value_t = 14)] baseline_days: i64,
        #[arg(long, default_value_t = 14)] intervention_days: i64,
    },
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
    if !matches!(cli.command, Commands::Init | Commands::Lattice { .. }
        | Commands::LatticeRepo { .. } | Commands::LatticeSnap { .. } | Commands::Meta { .. }
        | Commands::LatticeQuery { .. } | Commands::Discovery { .. } | Commands::Studio { .. }
        | Commands::Mcp { .. } | Commands::Web { .. } | Commands::Atlas { .. }
        | Commands::PnnSafety { .. } | Commands::Client { .. }
        | Commands::FluidBridge { .. } | Commands::FluidFrankOseen { .. }
        | Commands::FluidVortexCore { .. } | Commands::HydrogenRadial { .. }
        | Commands::FluidTopology { .. } | Commands::FluidCirculant { .. }
        | Commands::FluidReduction { .. } | Commands::FluidVariationalWidth { .. }
        | Commands::FluidNelsonClosure { .. } | Commands::FluidConvergence { .. }
        | Commands::Obezite { .. }
        | Commands::PnnRules { .. } | Commands::PnnDocking { .. }
        | Commands::PnnCompounds { .. } | Commands::PnnScreen { .. } | Commands::Providers { .. }) {
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
        Commands::Experiment { action } => run_experiment(&conn, action),
        Commands::Lattice { action } => run_lattice(action),
        Commands::LatticeRepo { action } => run_lattice_repo(&cli.db, action),
        Commands::PnnScreen { action } => {
            use crate::domains_pnn_screen as screen;
            fn compound(raw: &str) -> Result<Value> {
                serde_json::from_str(raw).map_err(|e| EngineError::new(
                    format!("invalid compound JSON: {e}"), "compound must be a JSON object",
                    "pass an object with the PNN physicochemical fields"))
            }
            fn compounds(raw: &str) -> Result<Vec<Value>> {
                serde_json::from_str(raw).map_err(|e| EngineError::new(
                    format!("invalid compounds JSON: {e}"), "compounds must be a JSON array",
                    "pass an array of compound objects"))
            }
            match action {
                PnnScreenAction::Evaluate { compound: raw } => {
                    let value = screen::evaluate_compound(&compound(raw)?);
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                PnnScreenAction::Rank { compounds: raw } => {
                    let value = Value::Array(screen::screen_compounds(&compounds(raw)?));
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                PnnScreenAction::Summary { compounds: raw } => {
                    let value = screen::summarize(&screen::screen_compounds(&compounds(raw)?));
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
            }
        }
        Commands::PnnCompounds { action } => {
            use crate::domains_pnn_compounds as compounds;
            match action {
                PnnCompoundsAction::Parse { rows, source, allow_duplicates } => {
                    let rows: Vec<std::collections::BTreeMap<String, String>> =
                        serde_json::from_str(rows).map_err(|e| EngineError::new(
                            format!("invalid rows JSON: {e}"), "rows must be an array of string maps",
                            "pass an array of objects with string values"))?;
                    let values = compounds::parse_compounds(&rows, source, *allow_duplicates)?;
                    let value = compounds::array(values.clone());
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                PnnCompoundsAction::Field { name } => {
                    let value = compounds::normalize_field(name).unwrap_or("");
                    emit(json!({"field": value}), format!("{value}\n"))
                }
            }
        }
        Commands::PnnDocking { action } => {
            use crate::domains_pnn_docking as docking;
            fn read_rows(path: &str) -> Result<Vec<std::collections::BTreeMap<String, String>>> {
                let text = std::fs::read_to_string(path).map_err(|e| EngineError::new(
                    format!("cannot read docking rows: {e}"),
                    "the rows file must be a readable UTF-8 JSON array of string maps",
                    "pass a readable JSON file"))?;
                serde_json::from_str(&text).map_err(|e| EngineError::new(
                    format!("invalid docking rows JSON: {e}"),
                    "each row must be an object of string values",
                    "pass an array of string-keyed objects"))
            }
            match action {
                PnnDockingAction::Parse { rows, source } => {
                    let rows = read_rows(rows)?;
                    let scores = docking::parse_rows(&rows, source)?;
                    emit(Value::Array(scores.clone()), to_stable_json(&Value::Array(scores)))
                }
                PnnDockingAction::Rank { rows, max_rmsd, min_vina } => {
                    let rows = read_rows(rows)?;
                    let scores = docking::parse_rows(&rows, "input")?;
                    let (kept, dropped) = docking::filter_scores(&scores, *max_rmsd, *min_vina);
                    let ranks = docking::normalize_scores(&kept);
                    let aggregated = docking::aggregate_best(&ranks);
                    let aggregated_json = Value::Object(aggregated.into_iter().map(|(k, v)| (k, v)).collect());
                    let out = json!({
                        "scores": scores,
                        "kept": kept.len(),
                        "dropped": dropped,
                        "ranks": ranks,
                        "aggregated": aggregated_json,
                    });
                    let stable = to_stable_json(&out);
                    emit(out, stable)
                }
            }
        }
        Commands::Providers { action } => {
            use crate::lattice_providers as providers;
            match action {
                ProvidersAction::Url { source, query, limit } => {
                    let value = providers::query_url(source, query, *limit)?;
                    emit(json!({"url": value.clone()}), format!("{value}\n"))
                }
                ProvidersAction::Parse { source, payload_file, limit } => {
                    let payload = std::fs::read_to_string(payload_file).map_err(|e| EngineError::new(
                        format!("cannot read payload: {e}"), "the provider fixture must be a readable UTF-8 file",
                        "pass a readable payload file"))?;
                    let rows = providers::parse(source, &payload, *limit)?;
                    emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
                }
            }
        }
        Commands::PnnRules { action } => match action {
            PnnRulesAction::Evaluate { compound } => {
                let value: Value = serde_json::from_str(compound).map_err(|e| EngineError::new(
                    format!("invalid compound JSON: {e}"), "compound must be a JSON object.",
                    "pass an object with mw, logp, tpsa, hbd, hba and rotatable_bonds."))?;
                let rows = crate::domains_pnn_rules::evaluate(&value);
                emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
            }
            PnnRulesAction::Weight { criterion } => {
                let value = crate::domains_pnn_rules::weight(criterion);
                emit(json!({"value": value}), format!("{value}\n"))
            }
        },
        Commands::Obezite { action } => {
            use crate::domains_obezite as obezite;
            match action {
                ObeziteAction::Atiflar { text } => {
                    let ids: Vec<Value> = obezite::atiflar(text).into_iter().map(Value::from).collect();
                    emit(Value::Array(ids.clone()), to_stable_json(&Value::Array(ids)))
                }
                ObeziteAction::Dedupe { chunks, retracted, archive, updated, stamp } => {
                    let list: Vec<std::path::PathBuf> = chunks.split(',').map(|p| std::path::PathBuf::from(p.trim()))
                        .filter(|p| !p.as_os_str().is_empty()).collect();
                    let result = obezite::deduplicate(&list, std::path::Path::new(retracted),
                        std::path::Path::new(archive), std::path::Path::new(updated), stamp)?;
                    emit(result.clone(), to_stable_json(&result))
                }
            }
        }
        Commands::FluidConvergence { action } => {
            use crate::domains_fluid_convergence as conv;
            fn payload(raw: &str, name: &str) -> Result<Value> {
                serde_json::from_str(raw).map_err(|e| EngineError::new(
                    format!("invalid {name} JSON: {e}"), "the convergence payload must be a JSON object",
                    &format!("pass a JSON object for {name}")))
            }
            match action {
                FluidConvergenceAction::Scan { low, high } => {
                    let low = payload(low, "low")?;
                    let high = payload(high, "high")?;
                    let value = conv::compare_scans(&low, &high)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidConvergenceAction::Temporal { coarse, fine } => {
                    let coarse = payload(coarse, "coarse")?;
                    let fine = payload(fine, "fine")?;
                    let value = conv::compare_temporal(&coarse, &fine)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidConvergenceAction::Trend { rows, z3_target, force_tol } => {
                    let rows: Vec<Value> = serde_json::from_str(rows).map_err(|e| EngineError::new(
                        format!("invalid rows JSON: {e}"), "rows must be a JSON array of objects",
                        "pass an array of row objects"))?;
                    let value = conv::summarize_trend(&rows, *z3_target, *force_tol)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
            }
        }
        Commands::FluidNelsonClosure { action } => {
            use crate::domains_fluid_nelson_closure as nc;
            fn xs(raw: &str) -> Result<Vec<f64>> {
                serde_json::from_str(raw).map_err(|e| EngineError::new(
                    format!("invalid xs JSON: {e}"), "xs must be a JSON array of numbers",
                    "pass an array of numbers"))
            }
            match action {
                FluidNelsonClosureAction::Osmotic { xs: raw, dx } => {
                    let value = Value::Array(nc::osmotic_velocity(&xs(raw)?, *dx)?
                        .into_iter().map(Value::from).collect());
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidNelsonClosureAction::FpResidual { xs: raw, dx, diffusion } => {
                    let value = Value::Array(nc::fp_residual(&xs(raw)?, *dx, *diffusion)?
                        .into_iter().map(Value::from).collect());
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidNelsonClosureAction::ResidualScaling => {
                    let value = nc::residual_scaling()?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidNelsonClosureAction::SigmaMap => {
                    let value = nc::frozen_drift_sigma_map()?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidNelsonClosureAction::Instances => {
                    let value = nc::ou_free_packet_instances()?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidNelsonClosureAction::Scales => {
                    let value = nc::closure_scales()?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
            }
        }
        Commands::FluidVariationalWidth { action } => {
            use crate::domains_fluid_variational_width as vw;
            macro_rules! scalar {
                ($expr:expr) => {{
                    let value = $expr?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }};
            }
            macro_rules! bundle {
                ($expr:expr) => {{
                    let value = $expr?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }};
            }
            match action {
                FluidVariationalWidthAction::Diffusivity { hbar, mass } => scalar!(vw::diffusivity(*hbar, *mass)),
                FluidVariationalWidthAction::ActionGm { s2, omega, hbar, mass } =>
                    scalar!(vw::action_gm(*s2, *omega, *hbar, *mass)),
                FluidVariationalWidthAction::ActionYasui { s2, omega, hbar, mass } =>
                    scalar!(vw::action_yasui(*s2, *omega, *hbar, *mass)),
                FluidVariationalWidthAction::DGm { s2, omega, hbar, mass } =>
                    scalar!(vw::d_action_gm(*s2, *omega, *hbar, *mass)),
                FluidVariationalWidthAction::DYasui { s2, omega, hbar, mass } =>
                    scalar!(vw::d_action_yasui(*s2, *omega, *hbar, *mass)),
                FluidVariationalWidthAction::D2S2 { s2, omega, hbar, mass } =>
                    scalar!(vw::d2_action_gm_s2(*s2, *omega, *hbar, *mass)),
                FluidVariationalWidthAction::D2Sigma { sigma, omega, hbar, mass } =>
                    scalar!(vw::d2_action_gm_sigma(*sigma, *omega, *hbar, *mass)),
                FluidVariationalWidthAction::Extremum { omega, hbar, mass } =>
                    scalar!(vw::extremum_s2(*omega, *hbar, *mass)),
                FluidVariationalWidthAction::Newton { start, omega, hbar, mass, steps } =>
                    scalar!(vw::newton_refine(*start, *omega, *hbar, *mass, *steps)),
                FluidVariationalWidthAction::GridMax { omega, hbar, mass } => {
                    let grid = vw::grid_s2();
                    let value = vw::grid_maximum(&grid, *omega, *hbar, *mass)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidVariationalWidthAction::YasuiMonotone { omega, hbar, mass } => {
                    let grid = vw::grid_s2();
                    let value = vw::yasui_monotone(&grid, *omega, *hbar, *mass)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidVariationalWidthAction::Ermakov => bundle!(vw::ermakov_cross_check()),
                FluidVariationalWidthAction::Scales => bundle!(vw::selection_scales()),
            }
        }
        Commands::FluidReduction { action } => {
            use crate::domains_fluid_reduction as red;
            macro_rules! scalar {
                ($expr:expr) => {{
                    let value = $expr?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }};
            }
            match action {
                FluidReductionAction::Tension { mu } => scalar!(red::wall_tension(*mu)),
                FluidReductionAction::Lower { mu, length_y } => scalar!(red::wall_lower_bound_2d(*mu, *length_y)),
                FluidReductionAction::Power { alpha } => {
                    let value = red::moment_power(*alpha);
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidReductionAction::Finite { alpha } => {
                    let value = red::moment_finite(*alpha);
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidReductionAction::LogDivergent { alpha } => {
                    let value = red::moment_log_divergent(*alpha);
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidReductionAction::Numeric { alpha, r_min, r_max } =>
                    scalar!(red::moment_numeric(*alpha, *r_min, *r_max)),
                FluidReductionAction::Verdict { alpha } => {
                    let value = red::verdict(*alpha);
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidReductionAction::Render { payload } => {
                    let payload: Value = serde_json::from_str(payload).map_err(|e| EngineError::new(
                        format!("invalid payload JSON: {e}"), "payload must be a JSON object",
                        "pass a JSON object with verdict, wall_tension, lower_bound_example and meta"))?;
                    let markdown = red::render_markdown(&payload)?;
                    emit(json!({"markdown": markdown.clone()}), format!("{markdown}\n"))
                }
            }
        }
        Commands::FluidTopology { action } => {
            use crate::domains_fluid_topology as topo;
            match action {
                FluidTopologyAction::Direct => {
                    let value = topo::direct_result();
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidTopologyAction::Extensions => {
                    let value = topo::extensions();
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidTopologyAction::Verdict => {
                    let value = topo::verdict();
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidTopologyAction::Render { payload } => {
                    let payload: Value = serde_json::from_str(payload).map_err(|e| EngineError::new(
                        format!("invalid payload JSON: {e}"), "payload must be a JSON object",
                        "pass a JSON object with verdict and meta"))?;
                    let markdown = topo::render_markdown(&payload)?;
                    emit(json!({"markdown": markdown.clone()}), format!("{markdown}\n"))
                }
            }
        }
        Commands::FluidCirculant { action } => {
            use crate::domains_fluid_circulant as circ;
            fn complex_matrix(m: [[(f64, f64); 3]; 3]) -> Value {
                Value::Array(m.iter().map(|row| Value::Array(row.iter().map(|(re, im)|
                    json!([re, im])).collect())).collect())
            }
            fn xs(raw: &str) -> Result<Vec<f64>> {
                serde_json::from_str(raw).map_err(|e| EngineError::new(
                    format!("invalid xs JSON: {e}"), "xs must be a JSON array of numbers",
                    "pass an array of three numbers"))
            }
            macro_rules! scalar {
                ($expr:expr) => {{
                    let value = $expr?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }};
            }
            match action {
                FluidCirculantAction::Matrix { a, c, delta } => {
                    let value = complex_matrix(circ::circulant_matrix(*a, *c, *delta));
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidCirculantAction::Eigenvalues { a, c, delta } => {
                    let value = Value::Array(circ::eigenvalues(*a, *c, *delta)
                        .into_iter().map(Value::from).collect());
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidCirculantAction::Dft => {
                    let value = complex_matrix(circ::dft_vectors());
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidCirculantAction::QSigned { xs: raw } => {
                    let value = circ::q_signed(&xs(raw)?);
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidCirculantAction::QMasses { xs: raw } => {
                    let value = circ::q_masses(&xs(raw)?);
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidCirculantAction::QPhysical { xs: raw } => {
                    let value = circ::q_physical_from_roots(&xs(raw)?);
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidCirculantAction::QFromAc { a, c } => {
                    let value = circ::q_from_ac(*a, *c);
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidCirculantAction::Extract { xs: raw } => {
                    let (a, c, delta) = circ::extract_ac_delta(&xs(raw)?)?;
                    let value = json!({"a": a, "c": c, "delta": delta});
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidCirculantAction::Fit { xs: raw } => {
                    let value = circ::fit_masses(&xs(raw)?)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidCirculantAction::Koide { me, mmu } => scalar!(circ::koide_tau_prediction(*me, *mmu)),
            }
        }
        Commands::HydrogenRadial { action } => {
            use crate::domains_hydrogen_radial as hr;
            macro_rules! scalar {
                ($expr:expr) => {{
                    let value = $expr?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }};
            }
            macro_rules! curve {
                ($expr:expr) => {{
                    let value = hr::json_array($expr?);
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }};
            }
            match action {
                HydrogenRadialAction::Radial10 { xs, radius } => {
                    let xs = hr::parse_grid(xs)?;
                    curve!(hr::radial_10(&xs, *radius))
                }
                HydrogenRadialAction::Radial20 { xs, radius } => {
                    let xs = hr::parse_grid(xs)?;
                    curve!(hr::radial_20(&xs, *radius))
                }
                HydrogenRadialAction::Probability { xs, radius } => {
                    let xs = hr::parse_grid(xs)?;
                    curve!(hr::radial_probability_20(&xs, *radius))
                }
                HydrogenRadialAction::Branch { xs, radius } => {
                    let xs = hr::parse_grid(xs)?;
                    let value = hr::branch_split_20(&xs, *radius)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                HydrogenRadialAction::Phase { xs, radius } => {
                    let xs = hr::parse_grid(xs)?;
                    scalar!(hr::phase_slip_20(&xs, *radius))
                }
                HydrogenRadialAction::Node { radius } => scalar!(hr::node_position(*radius)),
                HydrogenRadialAction::Overlap { radius } => scalar!(hr::overlap_10_20(*radius)),
                HydrogenRadialAction::Norm { radius } => scalar!(hr::norm_20(*radius)),
                HydrogenRadialAction::Peaks { radius } => {
                    let (inner, outer) = hr::peak_radii_20(*radius)?;
                    let value = json!({"inner": inner, "outer": outer});
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                HydrogenRadialAction::Balance => curve!(hr::balance_residuals()),
                HydrogenRadialAction::Circulation { r, theta, m, samples } =>
                    scalar!(hr::loop_circulation(*r, *theta, *m, *samples)),
                HydrogenRadialAction::Scales => {
                    let value = hr::representation_scales()?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
            }
        }
        Commands::FluidVortexCore { action } => {
            use crate::domains_fluid_vortex_core as vc;
            macro_rules! scalar {
                ($expr:expr) => {{
                    let value = $expr?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }};
            }
            match action {
                FluidVortexCoreAction::Radius => scalar!(vc::core_radius()),
                FluidVortexCoreAction::Sigma { omega, hbar, mass } => scalar!(vc::ho_sigma(*omega, *hbar, *mass)),
                FluidVortexCoreAction::Norm { eps, sigma } => scalar!(vc::core_norm(*eps, *sigma)),
                FluidVortexCoreAction::QZero { eps, sigma, hbar, mass } =>
                    scalar!(vc::core_q_zero(*eps, *sigma, *hbar, *mass)),
                FluidVortexCoreAction::FdQ { eps, n, length, sigma } =>
                    scalar!(vc::fd_q_zero(*eps, *n, *length, *sigma)),
                FluidVortexCoreAction::Density { eps, sigma, xs } => {
                    let xs = vc::parse_xs(xs)?;
                    let value = vc::json_array(vc::core_density(&xs, *eps, *sigma)?);
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidVortexCoreAction::Phase { eps, xs } => {
                    let xs = vc::parse_xs(xs)?;
                    let value = vc::json_array(vc::core_phase(&xs, *eps)?);
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidVortexCoreAction::Velocity { eps, hbar, mass, xs } => {
                    let xs = vc::parse_xs(xs)?;
                    let value = vc::json_array(vc::core_velocity(&xs, *eps, *hbar, *mass)?);
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
            }
        }
        Commands::FluidFrankOseen { action } => {
            use crate::domains_fluid_frank_oseen as fo;
            match action {
                FluidFrankOseenAction::Matrix { kx, ky, kz, k1, k2, k3 } => {
                    let m = fo::elastic_matrix(*kx, *ky, *kz, *k1, *k2, *k3);
                    let value = json!([m[0], m[1]]);
                    emit(value.clone(), to_stable_json(&value))
                }
                FluidFrankOseenAction::Dispersion { kx, ky, kz, k1, k2, k3, rho } => {
                    let values = fo::dispersion(*kx, *ky, *kz, *k1, *k2, *k3, *rho)?;
                    let value = Value::Array(values.iter().copied().map(Value::from).collect());
                    emit(value.clone(), to_stable_json(&value))
                }
                FluidFrankOseenAction::Equal { k, k_const, rho } => {
                    let value = fo::equal_constant_dispersion(*k, *k_const, *rho)?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidFrankOseenAction::Anisotropy { dx, dy, dz, k1, k2, k3, rho } => {
                    let value = fo::anisotropy([*dx, *dy, *dz], *k1, *k2, *k3, *rho)?;
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
                FluidFrankOseenAction::Modes => {
                    let value = fo::modes();
                    let stable = to_stable_json(&value);
                    emit(value, stable)
                }
            }
        }
        Commands::FluidBridge { action } => {
            use crate::domains_fluid_bridge as bridge;
            match action {
                FluidBridgeAction::Diffusivity { hbar, mass } => {
                    let value = bridge::diffusivity(*hbar, *mass)?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidBridgeAction::Horizon { omega } => {
                    let value = bridge::horizon(*omega)?;
                    emit(json!({"value": value}), format!("{value}\n"))
                }
                FluidBridgeAction::Coeffs { s0, st, horizon_t, omega, hbar, mass } => {
                    let rows = bridge::pinney_coeffs(*s0, *st, *horizon_t, *omega, *hbar, *mass)?;
                    emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
                }
                FluidBridgeAction::Path { coeffs, times, omega } => {
                    let coeff: Value = serde_json::from_str(coeffs).map_err(|e| EngineError::new(
                        format!("invalid coeffs JSON: {e}"), "coeffs must be a JSON object.", "pass A/B/C numbers."))?;
                    let list: Vec<f64> = serde_json::from_str(times).map_err(|e| EngineError::new(
                        format!("invalid times JSON: {e}"), "times must be a JSON array of numbers.", "pass a JSON array."))?;
                    let values: Vec<Value> = bridge::pinney_path(&coeff, &list, *omega)
                        .into_iter().map(Value::from).collect();
                    emit(Value::Array(values.clone()), to_stable_json(&Value::Array(values)))
                }
            }
        }
        Commands::Client { action } => {
            use crate::studio_client as client;
            let conn = crate::lattice_repo::open(&cli.db)?;
            match action {
                ClientAction::ToolSchemas { read_only } => {
                    let result = client::tool_schemas(*read_only);
                    emit(result.clone(), to_stable_json(&result))
                }
                ClientAction::ResourceSchemas => {
                    let result = client::resource_schemas();
                    emit(result.clone(), to_stable_json(&result))
                }
                ClientAction::PromptSchemas => {
                    let result = client::prompt_schemas();
                    emit(result.clone(), to_stable_json(&result))
                }
                ClientAction::Call { name, arguments, kwargs, read_only } => {
                    let args: Value = serde_json::from_str(arguments).map_err(|e| EngineError::new(
                        format!("invalid arguments JSON: {e}"), "arguments must be a JSON object.",
                        "pass a JSON object."))?;
                    let extra: Value = serde_json::from_str(kwargs).map_err(|e| EngineError::new(
                        format!("invalid kwargs JSON: {e}"), "kwargs must be a JSON object.",
                        "pass a JSON object."))?;
                    let result = client::call_tool(&conn, *read_only, name, &args, &extra)?;
                    emit(result.clone(), to_stable_json(&result))
                }
                ClientAction::ReadResource { uri } => {
                    let result = client::read_resource(&conn, uri)?;
                    emit(result.clone(), to_stable_json(&result))
                }
            }
        }
        Commands::PnnSafety { tox, pharm } => {
            use crate::domains_pnn_safety as safety;
            let studies: Vec<Value> = serde_json::from_str(tox).map_err(|e| EngineError::new(
                format!("invalid tox JSON: {e}"), "tox studies must be a JSON array.",
                "pass a JSON array of study objects."))?;
            let pharm_value: Value = serde_json::from_str(pharm).map_err(|e| EngineError::new(
                format!("invalid pharm JSON: {e}"), "pharm map must be a JSON object.",
                "pass a JSON object keyed by compound id."))?;
            let assessments = safety::assess(&studies, Some(&pharm_value), 10.0, 30.0, 10.0,
                50.0, 30.0, 60.0)?;
            let report = safety::render_report(&assessments, &json!({}));
            emit(json!({"assessments": assessments, "report": report}), report)
        }
        Commands::Atlas { action } => match action {
            AtlasAction::Coerce { payload, document_ref, source_page, figure_id } => {
                let value: Value = serde_json::from_str(payload).map_err(|e| EngineError::new(
                    format!("invalid payload JSON: {e}"), "Muse payload must be a JSON object.",
                    "pass a JSON object with entities and relationships."))?;
                let result = crate::domains_atlas::coerce_muse_payload(&value, document_ref, *source_page, figure_id)?;
                emit(result.clone(), to_stable_json(&result))
            }
            AtlasAction::Merge { analyses } => {
                let list: Vec<Value> = serde_json::from_str(analyses).map_err(|e| EngineError::new(
                    format!("invalid analyses JSON: {e}"), "analyses must be a JSON array.",
                    "pass a JSON array of VisualAnalysis objects."))?;
                let result = crate::domains_atlas::merge_analyses(&list, "", "")?;
                emit(result.clone(), to_stable_json(&result))
            }
            AtlasAction::Schema => {
                let result: Value = serde_json::from_str(crate::domains_atlas_schema_spec::MUSE_JSON_SCHEMA)
                    .unwrap_or(Value::Null);
                emit(result.clone(), to_stable_json(&result))
            }
        },
        Commands::Web { method, path, body } => {
            let conn = crate::lattice_repo::open(&cli.db)?;
            let response = crate::studio_web::dispatch_web_request(&conn, method, path,
                if body.is_empty() { None } else { Some(body.as_str()) })?;
            emit(response.clone(), field(&response, "body"))
        }
        Commands::Mcp { message } => {
            let conn = crate::lattice_repo::open(&cli.db)?;
            let request: Value = serde_json::from_str(message).map_err(|e| EngineError::new(
                format!("invalid JSON-RPC message: {e}"), "MCP messages must be JSON objects.",
                "pass a JSON object such as {\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}."))?;
            match crate::studio_mcp::handle_message(&conn, &request) {
                Some(response) => emit(response.clone(), to_stable_json(&response)),
                None => emit(Value::Null, String::new()),
            }
        }
        Commands::Studio { action } => {
            use crate::studio_api;
            let lattice = crate::lattice_repo::open(&cli.db)?;
            match action {
                StudioAction::Matrix { questions } => {
                    let list: Vec<String> = questions.split(',').map(|q| q.trim().to_string()).filter(|q| !q.is_empty()).collect();
                    let result = studio_api::get_evidence_matrix(&lattice, if list.is_empty() { None } else { Some(list.as_slice()) })?;
                    emit(result.clone(), to_stable_json(&result))
                }
                StudioAction::Evidence { reference } => {
                    let result = studio_api::question_evidence(&lattice, reference)?;
                    emit(result.clone(), to_stable_json(&result))
                }
            }
        }
        Commands::Discovery { action } => {
            use crate::lattice_discovery as discovery;
            match action {
                DiscoveryAction::Providers => {
                    let names = discovery::provider_names();
                    emit(Value::Array(names.iter().cloned().map(Value::String).collect()),
                        format!("{}\n", names.join(", ")))
                }
                DiscoveryAction::Offline { query, limit } => {
                    let rows = discovery::offline_search(query, *limit)?;
                    emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
                }
                DiscoveryAction::Discover { query, source, limit, no_ingest } => {
                    let conn = crate::lattice_repo::open(&cli.db)?;
                    let result = discovery::discover(&conn, query, source, *limit, !*no_ingest)?;
                    emit(result.clone(), to_stable_json(&result))
                }
                DiscoveryAction::CrossrefAuthors { authors } => {
                    let list: Vec<Value> = serde_json::from_str(authors).map_err(|e| EngineError::new(
                        format!("invalid authors JSON: {e}"), "authors must be a JSON array of objects.",
                        "pass a JSON array such as [{\"family\":\"Lovelace\",\"given\":\"Ada\"}]."))?;
                    let value = discovery::format_crossref_authors(&list);
                    emit(json!({"value": value.clone()}), format!("{}\n", value))
                }
                DiscoveryAction::CrossrefYear { item } => {
                    let value_obj: Value = serde_json::from_str(item).map_err(|e| EngineError::new(
                        format!("invalid item JSON: {e}"), "item must be a JSON object.", "pass a JSON object."))?;
                    let value = discovery::extract_crossref_year(&value_obj);
                    emit(json!({"value": value.clone()}), format!("{}\n", value))
                }
                DiscoveryAction::InvertedAbstract { inverted } => {
                    let value_obj: Value = serde_json::from_str(inverted).map_err(|e| EngineError::new(
                        format!("invalid inverted index JSON: {e}"), "the index must be a JSON object.", "pass a JSON object."))?;
                    let value = discovery::reconstruct_inverted_abstract(&value_obj);
                    emit(json!({"value": value.clone()}), format!("{}\n", value))
                }
            }
        }
        Commands::LatticeQuery { action } => {
            use crate::lattice_query;
            let lattice = crate::lattice_repo::open(&cli.db)?;
            match action {
                LatticeQueryAction::Outline { tokens } => {
                    let result = lattice_query::outline(&lattice, *tokens)?;
                    emit(result.clone(), to_stable_json(&result))
                }
                LatticeQueryAction::Contradictions { auto_link } => {
                    let result = lattice_query::detect_contradictions(&lattice, *auto_link)?;
                    emit(Value::Array(result.clone()), to_stable_json(&Value::Array(result)))
                }
                LatticeQueryAction::CompactSearch { query, limit, tokens } => {
                    let found = crate::lattice_repo::search(&lattice, query, *limit)?;
                    let result = lattice_query::compact_search(&found, *tokens)?;
                    emit(result.clone(), to_stable_json(&result))
                }
                LatticeQueryAction::ContextPack { targets, max_tokens, format } => {
                    let list: Vec<String> = targets.split(',').map(|t| t.trim().to_string()).filter(|t| !t.is_empty()).collect();
                    let result = lattice_query::build_context_pack(&lattice, &list, *max_tokens, format)?;
                    emit(result.clone(), field(&result, "content"))
                }
            }
        }
        Commands::Meta { action } => match action {
            MetaAction::StudyCi { id, label, effect, lower, upper, study_type } => {
                let result = crate::meta::study_from_ci(id, label, *effect, *lower, *upper, study_type)?;
                emit(result.clone(), to_stable_json(&result))
            }
            MetaAction::StudyGroups { id, label, n1, m1, sd1, n2, m2, sd2, study_type } => {
                let result = crate::meta::study_from_groups(id, label, *n1, *m1, *sd1, *n2, *m2, *sd2, study_type)?;
                emit(result.clone(), to_stable_json(&result))
            }
            MetaAction::Analyze { studies, model } => {
                let list: Vec<Value> = serde_json::from_str(studies).map_err(|e| EngineError::new(
                    format!("invalid studies JSON: {e}"), "studies must be a JSON array of study objects.",
                    "pass --studies '[{\"id\":\"s1\",\"effect_size\":0.5,\"se\":0.2}]'."))?;
                let result = crate::meta::compute_meta_analysis(&list, model)?;
                emit(result.clone(), to_stable_json(&result))
            }
            MetaAction::Forest { studies, model, width } => {
                let list: Vec<Value> = serde_json::from_str(studies).map_err(|e| EngineError::new(
                    format!("invalid studies JSON: {e}"), "studies must be a JSON array of study objects.",
                    "pass --studies '[{\"id\":\"s1\",\"effect_size\":0.5,\"se\":0.2}]'."))?;
                let result = crate::meta::compute_meta_analysis(&list, model)?;
                let text = crate::meta::render_forest_ascii(&result, *width);
                emit(json!({"text": text.clone()}), text)
            }
        },
        Commands::LatticeSnap { action } => {
            use crate::lattice_snapshots as snaps;
            let lattice = crate::lattice_repo::open(&cli.db)?;
            match action {
                LatticeSnapAction::Records => {
                    let rows = snaps::collect_records(&lattice)?;
                    emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
                }
                LatticeSnapAction::Export { path } => {
                    let result = snaps::export_snapshot(&lattice, std::path::Path::new(path))?;
                    emit(result.clone(), to_stable_json(&result))
                }
                LatticeSnapAction::Bibtex => {
                    let text = snaps::format_bibtex(&lattice)?;
                    emit(json!({"text": text.clone()}), text)
                }
                LatticeSnapAction::Cytoscape => {
                    let result = snaps::cytoscape_data(&lattice)?;
                    emit(result.clone(), to_stable_json(&result))
                }
                LatticeSnapAction::Graphml => {
                    let text = snaps::graphml_string(&lattice)?;
                    emit(json!({"text": text.clone()}), text)
                }
            }
        }
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

fn run_lattice_repo(db: &str, action: &LatticeRepoAction) -> Result<Output> {
    use crate::lattice_repo;
    let conn = lattice_repo::open(db)?;
    match action {
        LatticeRepoAction::PaperAdd { title, authors, year, venue, doi, arxiv, url,
            abstract_text, tags, study_type } => {
            let mut metadata = std::collections::BTreeMap::new();
            for (key, value) in [("title", title.as_str()), ("authors", authors), ("year", year),
                ("venue", venue), ("doi", doi), ("arxiv", arxiv), ("url", url),
                ("abstract", abstract_text), ("tags", tags), ("study_type", study_type)] {
                metadata.insert(key.to_string(), value.to_string());
            }
            let (record, created) = lattice_repo::add_paper(&conn, &metadata)?;
            let line = format!("{} {} {}", field(&record, "id"),
                if created { "added" } else { "merged" }, field(&record, "title"));
            emit(json!({"paper": record, "created": created}), line)
        }
        LatticeRepoAction::ClaimAdd { paper, text, quote, locator, stance, confidence } => {
            let record = lattice_repo::add_claim(&conn, paper, text, quote, locator, stance, *confidence)?;
            emit(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "text")))
        }
        LatticeRepoAction::QuestionAdd { text } => {
            let record = lattice_repo::add_question(&conn, text)?;
            emit(record.clone(), format!("{} {}", field(&record, "id"), field(&record, "text")))
        }
        LatticeRepoAction::EdgeAdd { src, dst, kind, note } => {
            let record = lattice_repo::add_edge(&conn, src, dst, kind, note)?;
            emit(record.clone(), to_stable_json(&record))
        }
        LatticeRepoAction::Get { reference } => {
            let result = lattice_repo::get(&conn, reference)?;
            emit(result.clone(), to_stable_json(&result))
        }
        LatticeRepoAction::Search { query, limit } => {
            let result = lattice_repo::search(&conn, query, *limit)?;
            emit(result.clone(), to_stable_json(&result))
        }
        LatticeRepoAction::Stats => {
            let result = lattice_repo::stats(&conn)?;
            emit(result.clone(), to_stable_json(&result))
        }
    }
}

fn run_lattice(action: &LatticeAction) -> Result<Output> {
    use crate::lattice;
    match action {
        LatticeAction::Normalize { text } => emit(json!({"value": lattice::normalize_text(text)}),
            format!("{}\n", lattice::normalize_text(text))),
        LatticeAction::Tags { text } => emit(json!({"value": lattice::normalize_tags(text)}),
            format!("{}\n", lattice::normalize_tags(text))),
        LatticeAction::DeriveTags { title, abstract_text, limit } => {
            let value = lattice::derive_tags(title, abstract_text, *limit)?;
            emit(json!({"value": value.clone()}), format!("{}\n", value))
        }
        LatticeAction::StudyType { text } => emit(json!({"value": lattice::normalize_study_type(text)}),
            format!("{}\n", lattice::normalize_study_type(text))),
        LatticeAction::InferStudy { title, abstract_text } => {
            let value = lattice::infer_study_type(title, abstract_text);
            emit(json!({"value": value.clone()}), format!("{}\n", value))
        }
        LatticeAction::PaperId { title, doi, arxiv } => {
            let value = lattice::paper_id(title, doi, arxiv)?;
            emit(json!({"value": value.clone()}), format!("{}\n", value))
        }
        LatticeAction::ParseBibtex { text } => {
            let rows = lattice::parse_bibtex(text)?;
            emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
        }
        LatticeAction::ParseRis { text } => {
            let rows = lattice::parse_ris(text);
            emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
        }
        LatticeAction::ParseCsv { text } => {
            let rows = lattice::parse_csv(text)?;
            emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
        }
        LatticeAction::ParseCsl { text } => {
            let rows = lattice::parse_csl_json(text)?;
            emit(Value::Array(rows.clone()), to_stable_json(&Value::Array(rows)))
        }
    }
}

fn run_experiment(conn: &Connection, action: &ExperimentAction) -> Result<Output> {
    use crate::experiments;
    match action {
        ExperimentAction::InterventionAdd { research, name, start, projected, end, dosage, notes } => {
            let row = experiments::add_intervention(conn, research, name, start,
                Some(projected), Some(end), dosage, notes)?;
            emit(row.clone(), to_stable_json(&row))
        }
        ExperimentAction::MetricDefAdd { research, name, description, unit } => {
            let row = experiments::add_metric_definition(conn, research, name, description, unit)?;
            emit(row.clone(), to_stable_json(&row))
        }
        ExperimentAction::MetricAdd { research, metric, date, value, intervention, note } => {
            let row = experiments::add_metric(conn, research, metric, date, *value,
                Some(intervention), note)?;
            emit(row.clone(), to_stable_json(&row))
        }
        ExperimentAction::EventAdd { research, name, timestamp, severity, notes, intervention } => {
            let row = experiments::add_event(conn, research, name, timestamp, *severity, notes,
                Some(intervention))?;
            emit(row.clone(), to_stable_json(&row))
        }
        ExperimentAction::List { research, kind } => {
            let rows = match kind.as_str() {
                "intervention" => experiments::list_rows(conn, "experiment_intervention", Some(research), "start_date, id")?,
                "metricdef" => experiments::list_rows(conn, "experiment_metric_definition", Some(research), "name")?,
                "event" => experiments::list_rows(conn, "experiment_event", Some(research), "timestamp, id")?,
                _ => experiments::list_metrics(conn, Some(research), None)?,
            };
            emit(Value::Array(rows.clone()), list_text(&rows))
        }
        ExperimentAction::Analyze { research, metric, start, baseline_days, intervention_days } => {
            let result = experiments::analyze_baseline_vs_intervention(conn, research, metric,
                start, *baseline_days, *intervention_days)?;
            emit(result.clone(), to_stable_json(&result))
        }
        ExperimentAction::Correlation { research, metrics } => {
            let list: Vec<String> = metrics.split(',').map(|m| m.trim().to_string()).filter(|m| !m.is_empty()).collect();
            let result = experiments::correlation_matrix(conn, research, if list.is_empty() { None } else { Some(list.as_slice()) })?;
            emit(result.clone(), to_stable_json(&result))
        }
        ExperimentAction::Multi { research, metrics, start, baseline_days, intervention_days } => {
            let list: Vec<String> = metrics.split(',').map(|m| m.trim().to_string()).filter(|m| !m.is_empty()).collect();
            let result = experiments::analyze_multiple_metrics(conn, research, &list, start,
                *baseline_days, *intervention_days)?;
            emit(result.clone(), to_stable_json(&result))
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
