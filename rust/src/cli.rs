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
    Run { #[command(subcommand)] action: RunAction },
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
pub enum RunAction {
    /// One integrated analysis using the engine's important capabilities.
    Analyze { #[arg(long, required = true)] input: String },
    /// Execute one retained capability through the unified engine entry point.
    Execute { capability: String, #[arg(long, required = true)] input: String },
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
pub enum PnnSarAction {
    Scaffold { smiles: String },
    Graph { smiles: String },
    Blocks { smiles: String },
}

#[derive(Debug, Subcommand)]
pub enum PnnDynamicsAction {
    Analyze {
        #[arg(long, required = true)] points: String,
        #[arg(long, default_value = "PNN-Compound")] compound: String,
        #[arg(long, default_value = "PTPsigma")] target: String,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnIndAction {
    Scale {
        animal_dose: f64, mouse_cl: f64, mouse_vd: f64, noael: f64,
        #[arg(long, default_value_t = 3.0)] noael_km: f64,
        #[arg(long, default_value_t = 0.020)] mouse_weight: f64,
        #[arg(long, default_value_t = 60.0)] human_weight: f64,
        #[arg(long, default_value_t = 37.0)] km_human: f64,
        #[arg(long, default_value_t = 10.0)] safety_factor: f64,
    },
    Project {
        #[arg(long, required = true)] compounds: String,
        #[arg(long)] preclinical: Option<String>,
        #[arg(long)] lead_id: Option<String>,
        #[arg(long, default_value_t = 10.0)] safety_factor: f64,
        #[arg(long, default_value_t = 60.0)] human_weight: f64,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnPreclinicalAction {
    Nca {
        #[arg(long, required = true)] points: String,
        #[arg(long)] dose: f64,
        #[arg(long, default_value = "C1")] compound: String,
        #[arg(long, default_value = "PO")] route: String,
        #[arg(long, default_value = "plasma")] tissue: String,
    },
    Run {
        #[arg(long, required = true)] pk: String,
        #[arg(long)] pd: Option<String>,
        #[arg(long, default_value_t = 0.30)] min_kp: f64,
        #[arg(long, default_value_t = 20.0)] min_f: f64,
        #[arg(long, default_value_t = 15.0)] min_wfa: f64,
        #[arg(long, default_value_t = 20.0)] min_itt: f64,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnAssayAction {
    Qualify {
        #[arg(long, required = true)] degradation: String,
        #[arg(long)] permeability: Option<String>,
        #[arg(long)] cytotoxicity: Option<String>,
        #[arg(long, default_value_t = 10000.0)] ec50_ceiling: f64,
        #[arg(long, default_value_t = 20.0)] max_deg_floor: f64,
        #[arg(long, default_value_t = 50.0)] min_si: f64,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnPathwayAction {
    Simulate {
        #[arg(long, default_value = "PNN-101")] compound: String,
        #[arg(long, default_value_t = 10.0)] dose: f64,
        #[arg(long, default_value = "INTERMITTENT_PULSATILE")] regimen: String,
        #[arg(long, default_value_t = 14)] days: i64,
        #[arg(long, default_value_t = 0.25)] dt: f64,
        #[arg(long, default_value_t = 3.2)] half_life: f64,
        #[arg(long, default_value_t = 32.5)] cmax: f64,
        #[arg(long, default_value_t = 24.0)] ec50: f64,
        #[arg(long, default_value_t = 349.46)] mw: f64,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnTargetAction {
    List,
    Show { target_id: String },
    Config {
        target_id: String,
        #[arg(long, default_value = "receptor.pdbqt")] receptor: String,
        #[arg(long, default_value = "docked_output.pdbqt")] out: String,
        #[arg(long, default_value_t = 8)] exhaustiveness: i64,
        #[arg(long, default_value_t = 9)] num_modes: i64,
        #[arg(long, default_value_t = 3)] energy_range: i64,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnMpoAction {
    Ramp { val: f64, low: f64, high: f64, #[arg(long, default_value_t = true, action = clap::ArgAction::Set)] increasing: bool },
    Score { mw: f64, logp: f64, tpsa: f64, hbd: f64, #[arg(long)] pka: Option<f64>, #[arg(long)] logd: Option<f64> },
    Profile { #[arg(long, required = true)] compound: String },
    Report { #[arg(long, required = true)] profiles: String },
    Rows { #[arg(long, required = true)] profiles: String },
}

#[derive(Debug, Subcommand)]
pub enum LeadSelectionAction {
    Report {
        #[arg(long, required = true)] inputs: String,
        #[arg(long, required = true)] docking: String,
        #[arg(long, default_value = "B")] min_tier: String,
        #[arg(long, default_value_t = 25)] per_bin: usize,
        #[arg(long, default_value_t = 0.1)] bin_width: f64,
        #[arg(long)] max_compounds: Option<usize>,
        #[arg(long)] max_rmsd: Option<f64>,
        #[arg(long)] min_vina: Option<f64>,
        #[arg(long, default_value_t = 25)] top_n: usize,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnCurateAction {
    Run {
        #[arg(long, required = true)] inputs: String,
        #[arg(long, required = true)] out: String,
        #[arg(long)] json_path: Option<String>,
        #[arg(long, default_value = "B")] min_tier: String,
        #[arg(long, default_value_t = 25)] per_bin: usize,
        #[arg(long, default_value_t = 0.1)] bin_width: f64,
        #[arg(long)] max_compounds: Option<usize>,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnRankAction {
    Build {
        #[arg(long, required = true)] rows: String,
        #[arg(long)] screen: Option<String>,
        #[arg(long, default_value = "B")] min_tier: String,
        #[arg(long)] max_rmsd: Option<f64>,
        #[arg(long)] min_vina: Option<f64>,
    },
}

#[derive(Debug, Subcommand)]
pub enum PredictionsAction {
    Candidates,
    Verdict,
    Render { #[arg(long, required = true)] payload: String },
}

#[derive(Debug, Subcommand)]
pub enum WaterLineshapeAction {
    Moments,
    Widths,
    Thresholds,
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum WaterTemperatureAction {
    Dielectric { temperature_c: f64 },
    Tension { temperature_c: f64 },
    Cavity { temperature_c: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum WaterMarcusAction {
    Width { #[arg(long, default_value_t = 1.6171325440878093)] lambda_ev: f64, #[arg(long, default_value_t = 300.0)] temperature_k: f64 },
    Line { energy_ev: f64, center_ev: f64, fwhm_ev: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum BornCavityAction {
    Energy { radius_m: f64 },
    Equilibrium { #[arg(long, default_value_t = 1.8e-10)] lower_m: f64, #[arg(long, default_value_t = 4.0e-10)] upper_m: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum WaterReorganizationAction {
    Contrast { #[arg(long, default_value_t = 78.4)] epsilon_s: f64, #[arg(long, default_value_t = 1.78)] epsilon_opt: f64 },
    Energy { radius_m: f64, #[arg(long, default_value_t = 78.4)] epsilon_s: f64, #[arg(long, default_value_t = 1.78)] epsilon_opt: f64 },
    Radius { difference_ev: f64, #[arg(long, default_value_t = 78.4)] epsilon_s: f64, #[arg(long, default_value_t = 1.78)] epsilon_opt: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum WaterPressureAction {
    Surface { radius_m: f64 },
    Total { radius_m: f64, depth_ev: f64 },
    Equilibrium { depth_ev: f64, #[arg(long, default_value_t = 1.5e-10)] lower_m: f64, #[arg(long, default_value_t = 6.0e-10)] upper_m: f64 },
    VdeMatched { #[arg(long, default_value_t = 3.27)] binding_ev: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum NodeDefectAction {
    Split { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] omega: f64 },
    Pressure { #[arg(long, required = true)] xs: String },
    Scaling,
    Vortex,
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum HydrogenVortexAction {
    Radial { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] radius: f64 },
    Probability { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] radius: f64 },
    MostProbable { #[arg(long, default_value_t = 1.0)] radius: f64 },
    Azimuthal { r: f64, theta: f64, m: i64 },
    Circulation { m: i64 },
    Loop { r: f64, theta: f64, m: i64, #[arg(long, default_value_t = 4000)] samples: usize },
    AngularMomentum { m: i64 },
    Norm { #[arg(long, default_value_t = 1.0)] radius: f64 },
}

#[derive(Debug, Subcommand)]
pub enum ObservedShapeAction {
    Width { #[arg(long, default_value_t = 45.0)] span_k: f64 },
    Evidence,
    Scales,
    SideWidths { #[arg(long, default_value_t = 299.15)] temperature_k: f64 },
}

#[derive(Debug, Subcommand)]
pub enum VortexParticlesAction {
    Koide { #[arg(long, required = true)] xs: String },
    Length { n: i64, #[arg(long, default_value_t = 400)] samples: usize },
    Energy { n: i64, #[arg(long, default_value_t = 0.1)] core: f64, #[arg(long, default_value_t = 400)] samples: usize },
    Hypothesis {
        #[arg(long, required = true)] masses: String,
        #[arg(long, default_value = "[3,5,7]")] knots: String,
        #[arg(long, default_value_t = 0.1)] core: f64,
        #[arg(long, default_value_t = 0.1)] relative_tolerance: f64,
        #[arg(long, default_value_t = 0.01)] koide_tolerance: f64,
    },
}

#[derive(Debug, Subcommand)]
pub enum VortexCascadeAction {
    Koide { #[arg(long, required = true)] xs: String },
    Geometric { ratio: f64, #[arg(long, default_value_t = 3)] generations: usize },
    Power { exponent: f64, #[arg(long, default_value_t = 3)] generations: usize },
    Solve { #[arg(long, default_value_t = 2.0 / 3.0)] target: f64, #[arg(long, default_value_t = 0.0)] lower: f64, #[arg(long, default_value_t = 50.0)] upper: f64 },
    Hypotheses { #[arg(long, required = true)] masses: String },
}

#[derive(Debug, Subcommand)]
pub enum WaterRaysAction {
    Outgoing { r: f64, #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Ingoing { r: f64, #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Peeling { #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Time { r: f64, r0: f64, horizon: f64, speed: f64 },
    Integrate { r0: f64, r_end: f64, #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64, #[arg(long, default_value_t = 1e-5)] dt: f64 },
}

#[derive(Debug, Subcommand)]
pub enum ExcitedFluidAction {
    Width { #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    Density { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    Wavefunction { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    Pressure { #[arg(long, required = true)] xs: String, #[arg(long, default_value_t = 1.0)] omega: f64, #[arg(long, default_value_t = 1.0)] hbar: f64, #[arg(long, default_value_t = 1.0)] mass: f64 },
    PhaseSlip { #[arg(long, required = true)] xs: String },
    PhaseGradient { #[arg(long, required = true)] xs: String, #[arg(long)] dx: f64 },
    ScalingSlope { #[arg(long, required = true)] dxs: String, #[arg(long, required = true)] maxima: String },
}

#[derive(Debug, Subcommand)]
pub enum TwoStateMarcusAction {
    Width { #[arg(long, default_value_t = 1.6171325440878093)] lambda_ev: f64, #[arg(long, default_value_t = 300.0)] temperature_k: f64 },
    Shared { #[arg(long, default_value_t = 300.0)] temperature_k: f64 },
    Ratio,
    Thresholds,
    Scales { #[arg(long, default_value_t = 300.0)] temperature_k: f64 },
}

#[derive(Debug, Subcommand)]
pub enum WaterDispersiveAction {
    Dispersion { k: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Group { k: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Wavenumber { omega: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64, #[arg(long, default_value_t = 1e5)] maximum: f64 },
    Horizon { omega: f64, #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Capillary { #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
}

#[derive(Debug, Subcommand)]
pub enum WaterVdeAction {
    Depth { radius_m: f64, binding_ev: f64 },
    Cavity { #[arg(long, default_value_t = 3.27)] binding_ev: f64, #[arg(long, default_value_t = 1.7)] gap_ev: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum WaterElectronAction {
    ScreenedRadius { #[arg(long, default_value_t = 78.4)] epsilon_r: f64 },
    ScreenedEnergy { #[arg(long, default_value_t = 78.4)] epsilon_r: f64 },
    CavityRadius,
    CavityEnergy,
    WellGap { radius: f64 },
    RadiusForGap { energy_ev: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum WaterWellAction {
    Born { radius_m: f64, #[arg(long, default_value_t = 78.4)] epsilon_r: f64 },
    Threshold { radius_m: f64 },
    Infinite { radius_m: f64 },
    Roots { radius_m: f64, depth_ev: f64 },
    Required { radius_m: f64, #[arg(long, default_value_t = 1.7)] target_ev: f64 },
    Minimum { #[arg(long, default_value_t = 1.7)] target_ev: f64 },
    Scales,
}

#[derive(Debug, Subcommand)]
pub enum PnnReportsAction {
    Csv { #[arg(long, required = true)] path: String, #[arg(long, required = true)] fieldnames: String, #[arg(long, required = true)] rows: String },
    Json { #[arg(long, required = true)] path: String, #[arg(long, required = true)] report: String },
    Text { #[arg(long, required = true)] path: String, #[arg(long, required = true)] text: String },
}

#[derive(Debug, Subcommand)]
pub enum WaterAnalogueAction {
    Speed { #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Flow { r: f64, #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Radius { #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Gravity { #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Temperature { kappa: f64 },
    Metric { r: f64, #[arg(long)] flow_rate: f64, #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Lab { #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = 1e-3)] flow_rate: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Capillary { #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64 },
    Ratio { radius: f64, length: f64 },
    MinFlow { #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64, #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = 10.0)] ratio: f64 },
    Validity { #[arg(long, default_value_t = 0.1)] depth: f64, #[arg(long, default_value_t = 1e-3)] flow_rate: f64, #[arg(long, default_value_t = 0.0728)] gamma: f64, #[arg(long, default_value_t = 998.0)] density: f64, #[arg(long, default_value_t = crate::domains_fluid_water_analogue::GRAVITY)] gravity: f64, #[arg(long, default_value_t = 10.0)] ratio: f64 },
}

#[derive(Debug, Subcommand)]
pub enum PnnCurationAction {
    Prepare { #[arg(long, required = true)] inputs: String },
    Dedupe { #[arg(long, required = true)] candidates: String },
    Curate {
        #[arg(long, required = true)] candidates: String,
        #[arg(long, default_value = "B")] min_tier: String,
        #[arg(long, default_value_t = 25)] per_bin: usize,
        #[arg(long, default_value_t = 0.1)] bin_width: f64,
        #[arg(long)] max_compounds: Option<usize>,
    },
}

#[derive(Debug, Subcommand)]
pub enum PnnTablesAction {
    Bin { #[arg(long, required = true)] compound: String, #[arg(long, default_value_t = 0.1)] width: f64 },
    Screen { #[arg(long, required = true)] results: String },
    Curated { #[arg(long, required = true)] candidates: String, #[arg(long, default_value_t = 0.1)] width: f64 },
    Fields,
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
    if !matches!(cli.command, Commands::Run { .. } | Commands::Init) {
        initialize(&conn)?;
    }
    match &cli.command {
        Commands::Run { action } => match action {
            RunAction::Execute { capability, input } => {
                let input: Value = serde_json::from_str(input).map_err(|e| EngineError::new(
                    format!("invalid capability input: {e}"), "input must be a JSON object",
                    "pass an object with capability-specific fields"))?;
                let value = crate::engine::execute(capability, &input)?;
                let stable = to_stable_json(&value);
                emit(value, stable)
            }
            RunAction::Analyze { input } => {
                let input: Value = serde_json::from_str(input).map_err(|e| EngineError::new(
                    format!("invalid analysis input: {e}"), "input must be a JSON object",
                    "pass an object with a compound and optional tox_studies/bridge"))?;
                let analysis = crate::engine::analyze(&input)?;
                let report = crate::engine::render_report(&analysis);
                let value = json!({"analysis": analysis, "report": report});
                let stable = to_stable_json(&value);
                emit(value, stable)
            }
        },
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
