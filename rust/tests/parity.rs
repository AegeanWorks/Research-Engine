//! Core contract tests for the Rust engine.
//!
//! Each test builds a fresh schema-14 graph and checks the invariants the Python
//! engine enforces: provenance rules, append-only verdicts, a verifiable event
//! ledger and cross-implementation readability.

use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

use research_engine::core;
use research_engine::db::{initialize, open};
use research_engine::error::EngineError;
use research_engine::integrity;
use research_engine::vocab::SCHEMA_VERSION;
use serde_json::Value;

static COUNTER: AtomicUsize = AtomicUsize::new(0);

fn temp_db(name: &str) -> PathBuf {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let mut path = std::env::temp_dir();
    path.push(format!("re-rust-{name}-{}-{n}.db", std::process::id()));
    let _ = std::fs::remove_file(&path);
    let _ = std::fs::remove_file(path.with_extension("db-wal"));
    let _ = std::fs::remove_file(path.with_extension("db-shm"));
    path
}

fn field(row: &serde_json::Value, key: &str) -> String {
    row.get(key).and_then(serde_json::Value::as_str).unwrap_or("").to_string()
}

#[test]
fn init_writes_schema_14() {
    let path = temp_db("schema");
    let conn = open(path.to_str().unwrap()).unwrap();
    assert!(initialize(&conn).unwrap().is_none());
    let version: i64 = conn.query_row("SELECT version FROM schema_meta", [], |r| r.get(0)).unwrap();
    assert_eq!(version, SCHEMA_VERSION);
    let tables: i64 = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        [], |r| r.get(0)).unwrap();
    assert_eq!(tables, 25, "schema has {tables} tables, expected the 25 v14 tables");
}

#[test]
fn core_lifecycle_is_coherent() {
    let path = temp_db("lifecycle");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();

    let research = core::add_research(&conn, "Fluid Universe", "replication", None).unwrap();
    let source = core::add_source(&conn, &field(&research, "id"), "Nature 2024", Some(2024), "10.1/x", "", "", "paper").unwrap();
    let question = core::add_question(&conn, &field(&research, "id"), "Is it reproducible?").unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Effect measured", "empirical",
        Some(&field(&source, "id")), "we observed 3.2", "p4", 0.5, "python -c pass", "", &[]).unwrap();
    let verdict = core::set_verdict(&conn, &field(&claim, "id"), "PROVEN", "verified group", "", "", "agent").unwrap();

    assert_eq!(field(&verdict, "status"), "PROVEN");
    let findings = integrity::check(&conn).unwrap();
    assert!(!integrity::has_errors(&findings), "unexpected findings: {findings:?}");
    let ledger = core::verify_events(&conn).unwrap();
    assert_eq!(ledger.get("ok").and_then(|v| v.as_bool()), Some(true));
    assert_eq!(field(&question, "status"), "open");
}

#[test]
fn empirical_provenance_gate_refuses_missing_quote() {
    let path = temp_db("provenance");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Gate", "", None).unwrap();
    let source = core::add_source(&conn, &field(&research, "id"), "Web source", None, "", "https://x", "", "paper").unwrap();
    let error: EngineError = core::add_claim(&conn, &field(&research, "id"), "Bad claim", "empirical",
        Some(&field(&source, "id")), "", "", 0.5, "", "", &[]).unwrap_err();
    assert_eq!(error.what, "empirical claim has no quote or locator");
    assert!(!error.why.is_empty() && !error.fix.is_empty());
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM claim", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
}

#[test]
fn verdict_is_append_only() {
    let path = temp_db("verdicts");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Corrections", "", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Correct me", "derived",
        None, "", "", 0.5, "", "because", &[]).unwrap();
    core::set_verdict(&conn, &field(&claim, "id"), "PROVEN", "first", "", "", "agent").unwrap();
    core::set_verdict(&conn, &field(&claim, "id"), "FALSIFIED", "second", "", "", "agent").unwrap();
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM verdict WHERE subject_kind='claim'", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 2, "a correction must be a new verdict, never an edit");
    let previous: String = conn.query_row(
        "SELECT previous_status FROM verdict ORDER BY id DESC LIMIT 1", [], |r| r.get(0)).unwrap();
    assert_eq!(previous, "PROVEN");
}

#[test]
fn cascade_invalidates_dependents() {
    let path = temp_db("cascade");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Cascade", "", None).unwrap();
    let root = core::add_claim(&conn, &field(&research, "id"), "root", "derived",
        None, "", "", 0.5, "", "premise", &[]).unwrap();
    let dependent = core::add_claim(&conn, &field(&research, "id"), "dependent", "derived",
        None, "", "", 0.5, "", "", &[field(&root, "id")]).unwrap();
    let preview = research_engine::cascade::preview(&conn, &field(&root, "id")).unwrap();
    assert_eq!(preview.get("affected").and_then(|v| v.as_array()).map(|a| a.len()), Some(1));
    let digest = field(&preview, "digest");
    let result = research_engine::cascade::invalidate(&conn, &field(&root, "id"), "FALSIFIED",
        "bad premise", "run x", "agent", false, &digest).unwrap();
    assert_eq!(result.get("affected").and_then(|v| v.as_array()).map(|a| a.len()), Some(1));
    let dependent = core::get_claim(&conn, &field(&dependent, "id")).unwrap();
    assert_eq!(field(&dependent, "status"), "INVALIDATED");
    let n: i64 = conn.query_row("SELECT COUNT(*) FROM invalidation", [], |r| r.get(0)).unwrap();
    assert_eq!(n, 1);
}

#[test]
fn report_numbers_come_from_the_graph() {
    let path = temp_db("report");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Report Program", "scope", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Measured claim", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();
    core::set_verdict(&conn, &field(&claim, "id"), "PROVEN", "evidence", "", "", "agent").unwrap();
    let report = research_engine::synthesis::report(&conn, &field(&research, "id")).unwrap();
    assert!(report.contains("- claims: 1"));
    assert!(report.contains("_No questions recorded._"));
    assert!(report.contains("_No hypotheses pre-registered._"));
    assert!(report.contains("no hand-written numbers"));
    let scorecard = research_engine::synthesis::scorecard(&conn, &field(&research, "id")).unwrap();
    assert!(scorecard.contains("| PROVEN |"));
}

#[test]
fn protocols_and_observations_enforce_provenance() {
    let path = temp_db("observations");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Measurements", "", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Measured", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();

    let protocol = research_engine::protocols::register(&conn, "accuracy_at_1", "top-1 accuracy",
        false, false, "", "", "agent").unwrap();
    assert_eq!(field(&protocol, "id"), "accuracy_at_1");
    assert!(research_engine::protocols::register(&conn, "accuracy_at_1", "duplicate",
        false, false, "", "", "agent").is_err());

    let ob = research_engine::observations::add(&conn, &field(&claim, "id"), "Baseline", 1.5,
        "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").unwrap();
    assert_eq!(field(&ob, "group_label"), "baseline");
    assert!(research_engine::observations::add(&conn, &field(&claim, "id"), "bad group", 1.0,
        "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").is_err());
    assert!(research_engine::observations::add(&conn, &field(&claim, "id"), "x", f64::NAN,
        "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").is_err());

    let amended = research_engine::protocols::amend(&conn, "accuracy_at_1", "top-1 accuracy v2", "clarify", "agent").unwrap();
    assert_eq!(field(&amended, "measures"), "top-1 accuracy v2");
    let findings = integrity::check(&conn).unwrap();
    let codes: Vec<&str> = findings.iter().map(|f| f.get("code").and_then(Value::as_str).unwrap_or("")).collect();
    assert!(codes.contains(&"OBS-001"), "missing OBS-001 in {codes:?}");
    assert!(codes.contains(&"OBS-002"));
    assert!(codes.contains(&"OBS-003"));
}

#[test]
fn analysis_stats_and_trend_record_evidence() {
    let path = temp_db("analysis");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Analysis", "", None).unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "Compared", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();
    for value in [1.0, 2.0, 3.0, 4.0] {
        research_engine::observations::add(&conn, &field(&claim, "id"), "baseline", value,
            "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").unwrap();
    }
    for value in [2.0, 4.0, 5.0, 7.0] {
        research_engine::observations::add(&conn, &field(&claim, "id"), "treatment", value,
            "", "", "", "", "", "", "", "", 1, "raw", "", "unclassified", "", "").unwrap();
    }
    let stats = research_engine::analysis::claim_statistics(&conn, &field(&claim, "id"),
        "baseline", "treatment", 0, 2000, false, false, "agent", "", "", "").unwrap();
    assert_eq!(stats.get("claim").and_then(Value::as_str), Some(field(&claim, "id").as_str()));
    assert_eq!(stats.get("baseline").and_then(|b| b.get("n")).and_then(Value::as_u64), Some(4));
    assert!(stats.get("comparability").is_some());
    let trend = research_engine::analysis::claim_trend(&conn, &field(&claim, "id"),
        "baseline", "agent", "", "").unwrap();
    assert_eq!(trend.get("group").and_then(Value::as_str), Some("baseline"));
    let events: i64 = conn.query_row(
        "SELECT COUNT(*) FROM event WHERE kind IN ('claim.stats','claim.trend')", [], |r| r.get(0)).unwrap();
    assert_eq!(events, 2);
}

#[test]
fn search_is_phrase_first_and_program_scoped() {
    let path = temp_db("search");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Search Program", "", None).unwrap();
    core::add_source(&conn, &field(&research, "id"), "Quantum Paper", Some(2024), "", "", "", "paper").unwrap();
    core::add_question(&conn, &field(&research, "id"), "Is quantum effect real?").unwrap();
    core::add_claim(&conn, &field(&research, "id"), "Quantum effect measured", "derived",
        None, "", "", 0.5, "", "quantum basis", &[]).unwrap();
    let result = research_engine::search::search(&conn, "quantum", None, None, 5, false, 800).unwrap();
    let hits = result.get("counts").unwrap();
    assert_eq!(hits["claim"]["hits"], 1);
    assert_eq!(hits["source"]["hits"], 1);
    assert_eq!(hits["question"]["hits"], 1);
    for hit in result.get("results").unwrap().as_array().unwrap() {
        assert_eq!(hit.get("score").and_then(Value::as_i64), Some(153));
    }
    assert!(result.get("text").and_then(Value::as_str).unwrap().contains("SEARCH \"quantum\""));
    let scoped = research_engine::search::search(&conn, "quantum", Some(&field(&research, "id")), None, 5, false, 800).unwrap();
    assert_eq!(scoped.get("research").and_then(Value::as_str), Some(field(&research, "id").as_str()));
}

#[test]
fn fluid_convergence_diagnostics() {
    use research_engine::domains_fluid_convergence as conv;
    let metric = |h: f64, h_up: f64, z3: f64, force: f64, bond: f64| serde_json::json!({
        "H": h, "H_upsampled": h_up, "Z3": z3, "force_rms": force, "max_bond": bond,
    });
    let payload = |n: i64, steps: i64, dt: f64, m: Value| serde_json::json!({
        "n": n, "length": 20.0, "mu": 0.5, "steps": steps, "dt": dt,
        "final": m, "verdict": {"claim_15_status": "UNVERIFIED"},
    });
    let low = payload(64, 1000, 0.01, metric(0.92, 0.99, 0.48, 0.02, 0.31));
    let high = payload(128, 1000, 0.01, metric(0.97, 1.002, 0.505, 0.015, 0.29));
    let scan = conv::compare_scans(&low, &high).unwrap();
    assert_eq!(scan.get("n_low").and_then(Value::as_i64), Some(64));
    assert_eq!(scan.get("n_high").and_then(Value::as_i64), Some(128));
    assert_eq!(scan.get("claim_15_status").and_then(Value::as_str), Some("UNVERIFIED"));
    let coarse = payload(64, 1000, 0.02, metric(0.90, 0.98, 0.47, 0.03, 0.35));
    let fine = payload(64, 2000, 0.01, metric(0.96, 1.001, 0.502, 0.02, 0.30));
    let temporal = conv::compare_temporal(&coarse, &fine).unwrap();
    assert_eq!(temporal.get("n").and_then(Value::as_i64), Some(64));
    assert!((temporal.get("physical_time").and_then(Value::as_f64).unwrap() - 20.0).abs() < 1e-12);
    let rows = vec![
        serde_json::json!({"steps": 100, "t": 1.0, "Z3": 0.10, "force_rms": 0.09}),
        serde_json::json!({"steps": 200, "t": 2.0, "Z3": 0.22, "force_rms": 0.07}),
        serde_json::json!({"steps": 400, "t": 4.0, "Z3": 0.46, "force_rms": 0.03}),
    ];
    let trend = conv::summarize_trend(&rows, 0.5, 0.01).unwrap();
    assert_eq!(trend.get("rows").and_then(Value::as_u64), Some(3));
    assert_eq!(trend.get("z3_monotone").and_then(Value::as_bool), Some(true));
    assert_eq!(trend.get("claim_15_status").and_then(Value::as_str), Some(""));
    assert!(conv::compare_scans(&high, &low).is_err());
    assert!(conv::compare_temporal(&low, &high).is_err());
    assert!(conv::summarize_trend(&rows[..1], 0.5, 0.01).is_err());
}

#[test]
fn fluid_osmotic_closure_no_go() {
    use research_engine::domains_fluid_nelson_closure as nc;
    let values = vec![1.0, 2.0, 4.0, 8.0];
    let g = nc::gradient(&values, 2.0).unwrap();
    assert_eq!(g.len(), values.len());
    assert!((g[0] - 0.5).abs() < 1e-12);
    assert!((g[1] - 0.75).abs() < 1e-12);
    assert!((nc::trapezoid(&values, &[0.0, 2.0, 4.0, 6.0]) - 21.0).abs() < 1e-12);
    let xs = vec![-2.0, -1.0, 0.0, 1.0, 2.0];
    let rho = vec![0.1, 0.2, 0.4, 0.2, 0.1];
    assert_eq!(nc::osmotic_velocity(&rho, 1.0).unwrap().len(), xs.len());
    assert_eq!(nc::fp_residual(&rho, 1.0, 0.5).unwrap().len(), xs.len());
    assert!(nc::fp_residual(&rho, 0.0, 0.5).is_err());
    assert!(nc::gradient(&[], 1.0).unwrap().is_empty());
    assert!(nc::polyfit_slope(&[1.0], &[2.0]).is_err());
    let scaling = nc::residual_scaling().unwrap();
    let rows = scaling.get("rows").unwrap().as_object().unwrap();
    assert_eq!(rows.len(), 6);
    assert!(rows.contains_key("gauss_1.0"));
    assert!(rows.contains_key("gauss_2.0"));
    assert!(!nc::frozen_drift_sigma_map().unwrap().get("entries").unwrap().as_array().unwrap().is_empty());
    assert!(nc::ou_free_packet_instances().unwrap().get("free_drift_at_zero").is_some());
    assert!(nc::closure_scales().unwrap().get("stationary_map").is_some());
}

#[test]
fn fluid_variational_width_selection() {
    use research_engine::domains_fluid_variational_width as vw;
    assert!((vw::diffusivity(1.0, 1.0).unwrap() - 0.5).abs() < 1e-12);
    assert!((vw::extremum_s2(1.0, 1.0, 1.0).unwrap() - 0.5).abs() < 1e-12);
    let gm = vw::action_gm(0.5, 1.0, 1.0, 1.0).unwrap();
    assert!(gm > vw::action_gm(0.4, 1.0, 1.0, 1.0).unwrap());
    assert!(gm > vw::action_gm(0.6, 1.0, 1.0, 1.0).unwrap());
    assert!(vw::d_action_yasui(0.5, 1.0, 1.0, 1.0).unwrap() < 0.0);
    assert!((vw::d2_action_gm_s2(0.5, 1.0, 1.0, 1.0).unwrap() + 2.0).abs() < 1e-12);
    let refined = vw::newton_refine(0.6, 1.0, 1.0, 1.0, 8).unwrap();
    assert!((refined - 0.5).abs() < 1e-12);
    assert!(vw::grid_s2().len() == 2001);
    let peak = vw::grid_maximum(&vw::grid_s2(), 1.0, 1.0, 1.0).unwrap();
    assert!((peak.get("grid_argmax").and_then(Value::as_f64).unwrap() - 0.5).abs() < 0.002);
    let yasui = vw::yasui_monotone(&vw::grid_s2(), 1.0, 1.0, 1.0).unwrap();
    assert_eq!(yasui.get("all_negative").and_then(Value::as_bool), Some(true));
    let scales = vw::selection_scales().unwrap();
    assert_eq!(scales.get("base").unwrap().get("omega").and_then(Value::as_f64), Some(1.0));
    assert!(vw::action_gm(0.0, 1.0, 1.0, 1.0).is_err());
}

#[test]
fn fluid_reduction_moment_audit() {
    use research_engine::domains_fluid_reduction as red;
    assert!((red::wall_tension(1.0).unwrap() - 8.0 / 3.0).abs() < 1e-12);
    assert!((red::wall_lower_bound_2d(1.0, 2.0).unwrap() - 16.0 / 3.0).abs() < 1e-12);
    assert_eq!(red::moment_power(4.0), -1.0);
    assert!(!red::moment_finite(4.0));
    assert!(red::moment_log_divergent(4.0));
    assert!(red::moment_finite(5.0));
    let log_value = red::moment_numeric(4.0, 1.0, 1.0e4).unwrap();
    assert!((log_value - 2.0 * std::f64::consts::PI * 1.0e4_f64.ln()).abs() < 1e-9);
    assert!(red::moment_numeric(2.0, 1.0, 1.0e4).unwrap() > log_value);
    assert!(red::moment_numeric(4.0, 1.0, 1.0).is_err());
    let v = red::verdict(4.0);
    assert_eq!(v.get("stated_tail_status").and_then(Value::as_str), Some("log-divergent"));
    assert_eq!(v.get("6b_iii_moment_finite_for_stated_profile").and_then(Value::as_bool), Some(false));
    let payload = serde_json::json!({
        "wall_tension": 8.0 / 3.0, "lower_bound_example": 16.0 / 3.0,
        "verdict": v,
        "meta": {"config_sha256": "abc", "git": {"commit": "def", "dirty": false}},
    });
    let markdown = red::render_markdown(&payload).unwrap();
    assert!(markdown.contains("# Dimensional reduction and moment of inertia (claim 6b)"));
    assert!(markdown.contains("T = 2.666666666667."));
    assert!(markdown.contains("(dirty=False)"));
    assert!(red::render_markdown(&serde_json::json!({})).is_err());
    assert!(red::wall_tension(-1.0).is_err());
}

#[test]
fn fluid_topology_z3_audit() {
    use research_engine::domains_fluid_topology as topo;
    assert!(!topo::has_z3_factor());
    let direct = topo::direct_result();
    assert_eq!(direct.get("order_parameter_space").and_then(Value::as_str), Some("RP^2"));
    let verdict = topo::verdict();
    assert_eq!(verdict.get("direct_claim_status").and_then(Value::as_str), Some("FALSIFIED"));
    let payload = serde_json::json!({
        "verdict": verdict,
        "meta": {"config_sha256": "abc", "git": {"commit": "def", "dirty": true}},
    });
    let markdown = topo::render_markdown(&payload).unwrap();
    assert!(markdown.contains("# Nematic topology and Z3 (claim 13)"));
    assert!(markdown.contains("| three_fold_lattice | False |"));
    assert!(markdown.contains("(dirty=True)"));
    assert!(topo::render_markdown(&serde_json::json!({})).is_err());
}

#[test]
fn fluid_circulant_mass_matrix() {
    use research_engine::domains_fluid_circulant as circ;
    let values = circ::eigenvalues(1.2, 0.35, 0.4);
    assert_eq!(values.len(), 3);
    assert!((values.iter().sum::<f64>() - 3.6).abs() < 1e-12);
    let dft = circ::dft_vectors();
    assert!((dft[0][0].0 - 1.0 / 3.0_f64.sqrt()).abs() < 1e-12);
    let (a, c, delta) = circ::extract_ac_delta(&[1.0, 2.0, 3.0]).unwrap();
    assert!((a - 2.0).abs() < 1e-12);
    assert!(c >= 0.0);
    assert!(delta >= 0.0 && delta < std::f64::consts::PI * 2.0);
    assert!(circ::extract_ac_delta(&[1.0, 2.0]).is_err());
    let fit = circ::fit_masses(&[0.511, 105.7, 1776.9]).unwrap();
    assert!(fit.get("max_abs_residual").and_then(Value::as_f64).unwrap() < 1e-6);
    assert_eq!(fit.get("all_roots_positive").and_then(Value::as_bool), Some(true));
    assert!(circ::fit_masses(&[-1.0]).is_err());
    assert!((circ::koide_tau_prediction(0.511, 105.7).unwrap() - 1776.9).abs() < 5.0);
}

#[test]
fn hydrogen_radial_two_branch_representation() {
    use research_engine::domains_hydrogen_radial as hr;
    let xs = vec![0.0, 1.0, 2.0, 4.0];
    let r10 = hr::radial_10(&xs, 1.0).unwrap();
    let r20 = hr::radial_20(&xs, 1.0).unwrap();
    assert!(r10[0] > r10[3]);
    assert!(r20[0] > 0.0 && r20[3] < 0.0);
    assert!((hr::node_position(1.0).unwrap() - 2.0).abs() < 1e-12);
    assert!((hr::phase_slip_20(&xs, 1.0).unwrap() - std::f64::consts::PI).abs() < 1e-12);
    let branch = hr::branch_split_20(&xs, 1.0).unwrap();
    assert_eq!(branch.get("identity_residual").and_then(Value::as_f64), Some(0.0));
    assert!((hr::norm_20(1.0).unwrap() - 1.0).abs() < 1e-9);
    assert!(hr::overlap_10_20(1.0).unwrap().abs() < 1e-9);
    let (inner, outer) = hr::peak_radii_20(1.0).unwrap();
    assert!(inner < outer);
    assert!(hr::balance_residuals().unwrap().iter().all(|v| v.abs() < 1e-12));
    assert!((hr::loop_circulation(2.0, std::f64::consts::FRAC_PI_2, 1, 4000).unwrap()
        - 2.0 * std::f64::consts::PI).abs() < 1e-12);
    let scales = hr::representation_scales().unwrap();
    assert_eq!(scales.get("radius").and_then(Value::as_f64), Some(1.0));
    assert!(hr::radial_10(&xs, 0.0).is_err());
}

#[test]
fn fluid_vortex_core_probe() {
    use research_engine::domains_fluid_vortex_core as vc;
    assert!((vc::core_radius().unwrap() - 0.1).abs() < 1e-12);
    assert!((vc::ho_sigma(1.0, 1.0, 1.0).unwrap() - 1.0).abs() < 1e-12);
    assert!((vc::core_norm(0.0, 2.0).unwrap() - 2.0 * std::f64::consts::PI.sqrt() * 2.0).abs() < 1e-12);
    let xs = vec![-2.0, -1.0, 0.0, 1.0, 2.0];
    let density = vc::core_density(&xs, 0.1, 1.0).unwrap();
    assert_eq!(density.len(), xs.len());
    assert!(density.iter().all(|v| *v >= 0.0));
    let phase = vc::core_phase(&xs, 0.1).unwrap();
    assert!(phase[0] > phase[4]);
    let velocity = vc::core_velocity(&xs, 0.1, 1.0, 1.0).unwrap();
    assert!(velocity.iter().all(|v| v.is_finite()));
    assert!(vc::core_q_zero(0.1, 1.0, 1.0, 1.0).unwrap() < 0.0);
    assert!(vc::fd_q_zero(0.1, 64, 20.0, 1.0).unwrap() < 0.0);
    assert!(vc::core_norm(-0.1, 1.0).is_err());
    assert!(vc::fd_q_zero(0.0, 64, 20.0, 1.0).is_err());
}

#[test]
fn fluid_frank_oseen_dispersion() {
    use research_engine::domains_fluid_frank_oseen as fo;
    let matrix = fo::elastic_matrix(1.0, 2.0, 3.0, 1.2, 0.8, 1.5);
    assert_eq!(matrix[0][1], matrix[1][0]);
    let values = fo::dispersion(1.0, 2.0, 3.0, 1.2, 0.8, 1.5, 1.3).unwrap();
    assert!(values[0] <= values[1]);
    assert!(values.iter().all(|v| v.is_finite()));
    assert!(fo::dispersion(1.0, 2.0, 3.0, 1.0, 1.0, 1.0, 0.0).is_err());
    let omega = fo::equal_constant_dispersion(3.0, 2.0, 1.0).unwrap();
    assert!((omega - 3.0 * 2.0_f64.sqrt()).abs() < 1e-12);
    let a = fo::anisotropy([1.0, 2.0, 2.0], 1.2, 0.8, 1.5, 1.0).unwrap();
    assert!(a.get("fractional_split").and_then(Value::as_f64).unwrap() >= 0.0);
    assert!(fo::anisotropy([0.0, 0.0, 0.0], 1.0, 1.0, 1.0, 1.0).is_err());
    assert_eq!(fo::modes().get("can_be_photon").and_then(Value::as_bool), Some(false));
}

#[test]
fn fixed_lambda_lineshape() {
    use research_engine::domains_fluid_water_lineshape as wl;
    let moments = wl::gaussian_moments();
    assert_eq!(moments["skewness"].as_f64(), Some(0.0));
    assert_eq!(moments["half_width_ratio"].as_f64(), Some(1.0));
    assert_eq!(moments["symmetric"].as_bool(), Some(true));
    let thresholds = wl::kill_thresholds();
    assert_eq!(thresholds["width_ratio_tol"].as_f64(), Some(0.05));
    assert_eq!(thresholds["shape_ratio_tol"].as_f64(), Some(0.15));
    assert_eq!(thresholds["skew_tol"].as_f64(), Some(0.3));
    let widths = wl::predicted_widths().unwrap();
    assert!(widths["width_0c_ev"].as_f64().unwrap() > 0.0);
    assert!(widths["width_45c_ev"].as_f64().unwrap() > 0.0);
    assert!(widths["width_ratio_45_over_0"].as_f64().unwrap() > 0.0);
    let scales = wl::lineshape_scales().unwrap();
    assert!((scales["lambda_ev"].as_f64().unwrap() - wl::LAMBDA_EV).abs() < 1e-3);
    assert!(scales.get("moments").is_some() && scales.get("prediction").is_some());
}

#[test]
fn temperature_dependent_cavity() {
    use research_engine::domains_fluid_water_temperature as wt;
    assert!((wt::water_dielectric_constant(0.0).unwrap() - 87.740).abs() < 1e-9);
    assert!((wt::water_surface_tension(0.0).unwrap() - 0.07564).abs() < 1e-9);
    assert!(wt::water_dielectric_constant(-1.0).is_err());
    assert!(wt::water_surface_tension(101.0).is_err());
    let cavity = wt::born_cavity_at_temperature(25.0).unwrap();
    assert!(cavity["radius_m"].as_f64().unwrap() > 1.8e-10);
    assert!(cavity["lambda_ev"].as_f64().unwrap() > 0.0);
    assert!(cavity["fwhm_ev"].as_f64().unwrap() > 0.0);
    let scales = wt::temperature_scales().unwrap();
    assert_eq!(scales["scan"].as_array().unwrap().len(), 7);
    assert_eq!(scales["cavity_terms_oppose"].as_bool(), Some(true));
    assert!(scales["width_change_ev"].as_f64().unwrap().abs() > 0.0);
    assert!(scales["lambda_slope_mev_per_k"].as_f64().unwrap() < 0.0);
}

#[test]
fn marcus_band_width() {
    use research_engine::domains_fluid_water_marcus as wm;
    let width = wm::marcus_width_ev(1.6171325440878093, 300.0).unwrap();
    assert!((width - 0.680915).abs() < 0.001);
    assert!(wm::marcus_width_ev(0.0, 300.0).is_err());
    assert!(wm::marcus_width_ev(1.0, 0.0).is_err());
    assert_eq!(wm::gaussian_line_shape(1.7, 1.7, 0.68).unwrap(), 1.0);
    assert!(wm::gaussian_line_shape(2.0, 1.7, 0.68).unwrap() < 1.0);
    assert!(wm::gaussian_line_shape(1.7, 1.7, 0.0).is_err());
    let scales = wm::marcus_scales().unwrap();
    assert_eq!(scales["center_ev"].as_f64(), Some(1.70));
    assert_eq!(scales["widths_ev"].as_object().unwrap().len(), 5);
    assert!(scales["ratio_classical"].as_f64().unwrap() > 0.0);
    assert!((scales["sqrt_ratio_350_300"].as_f64().unwrap() - (350.0_f64 / 300.0_f64).sqrt()).abs() < 1e-12);
}

#[test]
fn born_cavity_synthesis() {
    use research_engine::domains_fluid_water_born_cavity as bc;
    let energy = bc::born_cavity_energy(2.86e-10).unwrap();
    assert!(energy.is_some());
    assert!(bc::born_cavity_energy(0.0).is_err());
    let equilibrium = bc::born_cavity_equilibrium(1.8e-10, 4.0e-10).unwrap();
    let radius = equilibrium["radius_m"].as_f64().unwrap();
    assert!(radius > 1.8e-10 && radius < 4.0e-10);
    assert!(equilibrium["total_energy_ev"].as_f64().unwrap() < 0.0);
    assert!(equilibrium["binding_ev"].as_f64().unwrap() > 0.0);
    assert!(bc::born_cavity_equilibrium(4.0e-10, 1.8e-10).is_err());
    let scales = bc::born_cavity_scales().unwrap();
    assert_eq!(scales["vde_ev"].as_f64(), Some(3.27));
    let synthesis = &scales["synthesis"];
    assert!(synthesis["lambda_ev"].as_f64().unwrap() > 0.0);
    assert!(synthesis["predicted_vde_ev"].as_f64().unwrap() > 3.0);
    assert!(synthesis["required_ratio"].as_f64().unwrap() > 0.0);
    assert!(synthesis["capillary_ratio"].as_f64().unwrap() > 0.0);
}

#[test]
fn water_reorganization_relation() {
    use research_engine::domains_fluid_water_reorganization as wr;
    let contrast = wr::dielectric_contrast(78.4, 1.78).unwrap();
    assert!((contrast - (1.0 / 1.78 - 1.0 / 78.4)).abs() < 1e-15);
    assert!(wr::dielectric_contrast(1.0, 1.78).is_err());
    assert!(wr::dielectric_contrast(78.4, 78.4).is_err());
    assert!(wr::dielectric_contrast(78.4, 0.0).is_err());
    let radius = 2.858e-10;
    let lambda = wr::reorganization_energy_ev(radius, 78.4, 1.78).unwrap();
    assert!(lambda > 0.0 && lambda < 3.0);
    assert!(wr::reorganization_energy_ev(0.0, 78.4, 1.78).is_err());
    let inverted = wr::radius_for_difference(lambda, 78.4, 1.78).unwrap();
    assert!((inverted - radius).abs() / radius < 1e-12);
    assert!(wr::radius_for_difference(0.0, 78.4, 1.78).is_err());
    let scales = wr::reorganization_scales().unwrap();
    assert_eq!(scales["observed_difference_ev"].as_f64(), Some(1.57));
    assert_eq!(scales["vde_ev"].as_f64(), Some(3.27));
    let capillary = &scales["capillary"];
    assert!(capillary["lambda_ev"].as_f64().unwrap() > 0.0);
    assert!(capillary["sigma"].as_f64().unwrap() > 0.0);
    assert!(scales["pressure"]["radius_m"].as_f64().unwrap() > 0.0);
}

#[test]
fn pressure_balanced_cavity() {
    use research_engine::domains_fluid_water_pressure as wp;
    let radius = research_engine::domains_fluid_water_electron::capillary_cavity_radius(0.0728, 9.1093837015e-31, 1.054571817e-34).unwrap();
    assert!(wp::surface_energy_ev(radius).unwrap() > 0.0);
    assert!(wp::surface_energy_ev(0.0).is_err());
    let born = research_engine::domains_fluid_water_well::born_depth_ev(radius, 78.4).unwrap();
    assert!(wp::total_energy_ev(radius, born).unwrap().is_some());
    assert!(wp::total_energy_ev(radius, 0.0).is_err());
    let equilibrium = wp::equilibrium_radius(4.0, 1.5e-10, 6.0e-10).unwrap();
    let r = equilibrium["radius_m"].as_f64().unwrap();
    assert!(r > 1.5e-10 && r < 6.0e-10);
    assert!(equilibrium["total_energy_ev"].as_f64().unwrap() < 0.0);
    assert!(wp::equilibrium_radius(0.0, 1.5e-10, 6.0e-10).is_err());
    assert!(wp::equilibrium_radius(4.0, 6.0e-10, 1.5e-10).is_err());
    let matched = wp::vde_matched_depth(3.27).unwrap();
    assert!(matched["radius_m"].as_f64().unwrap() > 0.0);
    assert!(wp::vde_matched_depth(0.0).is_err());
    let scales = wp::pressure_scales().unwrap();
    assert_eq!(scales["scans"].as_array().unwrap().len(), 7);
    assert!(scales.get("vde_matched").is_some());
}

#[test]
fn two_branch_nodal_defect() {
    use research_engine::domains_fluid_node_defect as nd;
    let xs = [-2.0, -1.0, 0.0, 1.0, 2.0];
    let split = nd::branch_split(&xs, 1.0, 1.0, 1.0).unwrap();
    assert_eq!(split.get("identity_residual").and_then(Value::as_f64), Some(0.0));
    assert_eq!(split.get("node_density").and_then(Value::as_f64), Some(0.0));
    assert_eq!(split.get("phase_slip").and_then(Value::as_f64).unwrap().to_string(),
        std::f64::consts::PI.to_string());
    let match_result = nd::branch_regular_pressure_match(&xs, 1.0, 1.0, 1.0).unwrap();
    assert_eq!(match_result.get("n_branch_points").and_then(Value::as_u64), Some(4));
    assert_eq!(match_result.get("n_excluded").and_then(Value::as_u64), Some(1));
    assert_eq!(match_result.get("pressure finite").and_then(Value::as_bool), Some(true));
    let scaling = nd::node_scaling().unwrap();
    assert_eq!(scaling.get("grid_ns").unwrap().as_array().unwrap().len(), 4);
    assert!(scaling.get("slope").and_then(Value::as_f64).unwrap() < 0.0);
    let vortex = nd::vortex_gate().unwrap();
    assert!((vortex["radial_norm"].as_f64().unwrap() - 1.0).abs() < 1e-6);
    let scales = nd::representation_scales().unwrap();
    assert_eq!(scales["branch"]["node_density"].as_f64(), Some(0.0));
    assert!(scales.get("scaling").is_some() && scales.get("vortex").is_some());
}

#[test]
fn hydrogen_2p_vortex_identification() {
    use research_engine::domains_fluid_hydrogen_vortex as hv;
    let xs = [0.0, 1.0, 2.0, 4.0];
    let radial = hv::radial_2p(&xs, 1.0).unwrap();
    assert!(radial[0] == 0.0 && radial[2] > radial[3]);
    assert!(hv::radial_2p(&xs, 0.0).is_err());
    let probability = hv::radial_probability(&xs, 1.0).unwrap();
    assert!(probability.iter().all(|v| *v >= 0.0));
    assert_eq!(hv::most_probable_radius(1.0).unwrap(), 4.0);
    assert!(hv::most_probable_radius(0.0).is_err());
    let theta = std::f64::consts::FRAC_PI_2;
    assert!((hv::azimuthal_velocity(2.0, theta, 1, 1.0, 1.0).unwrap() - 0.5).abs() < 1e-12);
    assert!(hv::azimuthal_velocity(2.0, 0.0, 1, 1.0, 1.0).is_err());
    assert!((hv::circulation(1, 1.0, 1.0).unwrap() - 2.0 * std::f64::consts::PI).abs() < 1e-12);
    assert!((hv::loop_circulation(2.0, theta, 1, 1.0, 1.0, 4000).unwrap()
        - 2.0 * std::f64::consts::PI).abs() < 1e-12);
    assert!(hv::loop_circulation(2.0, theta, 1, 1.0, 1.0, 8).is_err());
    assert_eq!(hv::angular_momentum(1, 1.0).unwrap(), 1.0);
    assert!(hv::angular_momentum(1, 0.0).is_err());
}

#[test]
fn observed_band_shape_comparator() {
    use research_engine::domains_fluid_observed_shape as os;
    let width = os::observed_width_change_ev(45.0).unwrap();
    assert!((width["change_as_stated_ev"].as_f64().unwrap() - 0.009).abs() < 1e-15);
    assert!((width["change_if_hwhm_ev"].as_f64().unwrap() - 0.018).abs() < 1e-15);
    assert!(os::observed_width_change_ev(0.0).is_err());
    let evidence = os::shape_evidence();
    assert_eq!(evidence["component_width_ratio"].as_f64(), Some(0.71 / 0.37));
    assert_eq!(evidence["single_gaussian_compatible"].as_bool(), Some(false));
    assert_eq!(evidence["sources"].as_array().unwrap().len(), 3);
    let scales = os::observed_scales().unwrap();
    assert_eq!(scales["emax_ev"].as_f64(), Some(1.72));
    let sides = os::jou_freeman_side_widths(299.15).unwrap();
    assert_eq!(sides["red_gaussian_hwhm_ev"].as_f64(), Some(0.1517 + 0.00051 * 299.15));
    assert_eq!(sides["blue_lorentzian_hwhm_ev"].as_f64(), Some(0.5124 - 0.00010 * 299.15));
    assert!((sides["fwhm_ev"].as_f64().unwrap() - 0.786).abs() < 0.01);
    assert!(os::jou_freeman_side_widths(0.0).is_err());
}

#[test]
fn vortex_knot_mass_hypothesis() {
    use research_engine::domains_fluid_vortex_particles as vp;
    let (points, tangents) = vp::torus_knot(3, 2.0, 1.0, 64).unwrap();
    assert_eq!(points.len(), 64);
    assert_eq!(tangents.len(), 64);
    assert!(vp::torus_knot(0, 2.0, 1.0, 64).is_err());
    assert!(vp::torus_knot(3, 2.0, 1.0, 8).is_err());
    assert!(vp::knot_length(&points) > 0.0);
    assert!(vp::biot_savart_energy(&points, 0.1).unwrap() > 0.0);
    assert!(vp::biot_savart_energy(&points, 0.0).is_err());
    let q = vp::koide_q(&[0.511, 105.7, 1776.9]).unwrap();
    assert!((q - 2.0 / 3.0).abs() < 1e-3);
    assert!(vp::koide_q(&[]).is_err());
    let masses = [0.511, 105.7, 1776.9];
    let result = vp::mass_hypothesis(&masses, &[3, 5, 7], 0.1, 0.1, 0.01).unwrap();
    assert_eq!(result["knots"].as_array().unwrap().len(), 3);
    assert_eq!(result["falsified"].as_bool(), Some(true));
    assert!(result["required_power"].as_f64().unwrap() > 0.0);
    assert!(result["note"].as_str().unwrap().contains("thin filament"));
    assert!(vp::mass_hypothesis(&[1.0], &[3], 0.1, 0.1, 0.01).is_err());
}

#[test]
fn vortex_hierarchy_hypotheses() {
    use research_engine::domains_fluid_vortex_cascade as vc;
    let masses = [0.511, 105.7, 1776.9];
    let q = vc::koide_q(&masses).unwrap();
    assert!((q - 2.0 / 3.0).abs() < 1e-3);
    assert!(vc::koide_q(&[]).is_err());
    assert!(vc::koide_q(&[-1.0]).is_err());
    let geometric = vc::geometric_spectrum(2.0, 3).unwrap();
    assert_eq!(geometric, vec![1.0, 2.0, 4.0]);
    assert!(vc::geometric_spectrum(0.0, 3).is_err());
    assert_eq!(vc::power_law_spectrum(2.0, 3), vec![1.0, 4.0, 9.0]);
    let p = vc::solve_power_for_koide(vc::KOIDE_TARGET, 0.0, 50.0).unwrap();
    assert!(p > 0.0 && p < 50.0);
    assert!(vc::solve_power_for_koide(0.2, 0.0, 50.0).is_err());
    assert!(vc::solve_power_for_koide(vc::KOIDE_TARGET, 20.0, 50.0).is_err());
    let result = vc::run_hypotheses(&masses).unwrap();
    assert_eq!(result["models"].as_object().unwrap().len(), 3);
    assert_eq!(result.get("falsified").and_then(Value::as_bool), Some(true));
    assert!(result.get("status").and_then(Value::as_str).unwrap().starts_with("FALSIFIED"));
    assert!(vc::run_hypotheses(&[1.0, 2.0]).is_err());
    assert!(vc::run_hypotheses(&[1.0, -2.0, 3.0]).is_err());
}

#[test]
fn acoustic_horizon_rays() {
    use research_engine::domains_fluid_water_rays as wr;
    let flow = 1e-3;
    let depth = 0.1;
    let speed = research_engine::domains_fluid_water_analogue::sound_speed(depth, 9.81).unwrap();
    let horizon = research_engine::domains_fluid_water_analogue::horizon_radius(flow, depth, 9.81).unwrap();
    assert!(wr::outgoing_speed(0.005, flow, depth, 9.81).unwrap() > 0.0);
    assert!(wr::outgoing_speed(horizon, flow, depth, 9.81).unwrap().abs() < 1e-12);
    assert!(wr::ingoing_speed(0.005, flow, depth, 9.81).unwrap() < 0.0);
    assert!((wr::peeling_rate(flow, depth, 9.81).unwrap() - speed * speed / horizon).abs() < 1e-9);
    assert!(wr::analytic_outgoing_time(0.01, 0.004, horizon, speed).unwrap() > 0.0);
    assert!(wr::analytic_outgoing_time(horizon, 0.004, horizon, speed).is_err());
    let integrated = wr::integrate_outgoing(0.003, 0.004, flow, depth, 9.81, 1e-5).unwrap();
    assert!(integrated["time"].as_f64().unwrap() > 0.0);
    assert!(integrated["radius"].as_f64().unwrap() >= 0.004);
    assert!(integrated["steps"].as_u64().unwrap() > 0);
    assert!(wr::integrate_outgoing(0.004, 0.003, flow, depth, 9.81, 1e-5).is_err());
    assert!(wr::outgoing_speed(0.0, flow, depth, 9.81).is_err());
}

#[test]
fn excited_madelung_fluid_node() {
    use research_engine::domains_fluid_excited_fluid as ef;
    assert!((ef::oscillator_width(1.0, 1.0, 1.0).unwrap() - 1.0).abs() < 1e-12);
    assert!(ef::oscillator_width(0.0, 1.0, 1.0).is_err());
    let xs = vec![-2.0, -1.0, 0.0, 1.0, 2.0];
    let density = ef::excited_density(&xs, 1.0, 1.0, 1.0).unwrap();
    assert_eq!(density[2], 0.0);
    assert!(density[0] < density[1]);
    let wave = ef::excited_wavefunction(&xs, 1.0, 1.0, 1.0).unwrap();
    assert!(wave[0] < 0.0 && wave[4] > 0.0);
    let pressure = ef::excited_quantum_pressure_regular(&xs, 1.0, 1.0, 1.0).unwrap();
    assert!((pressure[2] - 1.5).abs() < 1e-12);
    assert!((ef::phase_slip(&wave) - std::f64::consts::PI).abs() < 1e-12);
    assert!((ef::phase_slip(&[1.0, 2.0, 3.0])).abs() < 1e-12);
    assert!(ef::phase_gradient_max(&wave, 0.25).unwrap() > 0.0);
    assert!(ef::phase_gradient_max(&wave, 0.0).is_err());
    let slope = ef::scaling_slope(&[0.1, 0.05, 0.025, 0.0125], &[8.0, 16.1, 32.2, 64.5]).unwrap();
    assert!(slope < 0.0);
    assert!(ef::scaling_slope(&[0.1], &[8.0]).is_err());
}

#[test]
fn shared_lambda_two_state_assignment() {
    use research_engine::domains_fluid_two_state_marcus as ts;
    let width = ts::marcus_width_ev(ts::LAMBDA_EV, 300.0).unwrap();
    assert!((width - 0.680915).abs() < 0.001);
    assert!(ts::marcus_width_ev(0.0, 300.0).is_err());
    assert!(ts::marcus_width_ev(ts::LAMBDA_EV, 0.0).is_err());
    let shared = ts::shared_lambda_widths(300.0).unwrap();
    assert_eq!(shared.get("width_g1_ev").and_then(Value::as_f64), Some(width));
    assert_eq!(shared.get("width_g2_ev").and_then(Value::as_f64), Some(width));
    assert_eq!(shared.get("predicted_ratio").and_then(Value::as_f64), Some(1.0));
    assert!(ts::shared_lambda_widths(0.0).is_err());
    let observed = ts::component_ratio();
    assert!((observed["observed_ratio"].as_f64().unwrap() - 0.71 / 0.37).abs() < 1e-12);
    assert!(observed["diff_vs_one"].as_f64().unwrap() > ts::SHAPE_RATIO_TOL);
    assert_eq!(ts::kill_thresholds()["shape_ratio_tol"].as_f64(), Some(0.15));
    let scales = ts::two_state_scales(300.0).unwrap();
    assert_eq!(scales["lambda_ev"].as_f64(), Some(ts::LAMBDA_EV));
    assert!(scales.get("observed").is_some());
}

#[test]
fn dispersive_water_horizon() {
    use research_engine::domains_fluid_water_dispersive as wd;
    let g = research_engine::domains_fluid_water_analogue::GRAVITY;
    assert_eq!(wd::dispersion(0.0, 0.1, 0.0728, 998.0, g).unwrap(), 0.0);
    assert!((wd::group_velocity(0.0, 0.1, 0.0728, 998.0, g).unwrap()
        - (g * 0.1).sqrt()).abs() < 1e-12);
    let omega = wd::dispersion(500.0, 0.1, 0.0728, 998.0, g).unwrap()
        + 500.0 * wd::group_velocity(500.0, 0.1, 0.0728, 998.0, g).unwrap();
    let k = wd::horizon_wavenumber(omega, 0.1, 0.0728, 998.0, g, 1e5).unwrap();
    assert!((k - 500.0).abs() / 500.0 < 1e-9);
    let horizon = wd::dispersive_horizon(omega, 1e-3, 0.1, 0.0728, 998.0, g).unwrap();
    assert!(horizon["horizon_radius_m"].as_f64().unwrap() > 0.0);
    assert!(horizon["ratio"].as_f64().unwrap() > 0.0);
    assert!(wd::capillary_frequency(0.1, 0.0728, 998.0, g).unwrap() > 0.0);
    assert!(wd::dispersion(-1.0, 0.1, 0.0728, 998.0, g).is_err());
    assert!(wd::horizon_wavenumber(0.0, 0.1, 0.0728, 998.0, g, 1e5).is_err());
    assert!(wd::dispersive_horizon(omega, 0.0, 0.1, 0.0728, 998.0, g).is_err());
}

#[test]
fn hydrated_electron_vde_inversion() {
    use research_engine::domains_fluid_water_vde as vde;
    let depth = vde::depth_for_binding(3.732e-10, 3.27).unwrap();
    assert!(depth > 0.0);
    assert!(vde::depth_for_binding(0.0, 3.27).is_err());
    assert!(vde::depth_for_binding(3.2e-10, 0.0).is_err());
    let cavity = vde::cavity_for_observables(3.27, 1.7).unwrap();
    let radius = cavity["radius_m"].as_f64().unwrap();
    assert!(radius > 3.0e-10 && radius < 4.5e-10);
    assert!((cavity["binding_ev"].as_f64().unwrap() - 3.27).abs() < 1e-6);
    assert!((cavity["gap_ev"].as_f64().unwrap() - 1.7).abs() < 1e-6);
    assert!(cavity["excess_ev"].as_f64().unwrap() > 0.0);
    assert!(vde::cavity_for_observables(0.0, 1.7).is_err());
    assert!(vde::cavity_for_observables(3.27, 0.0).is_err());
    let scales = vde::vde_scales().unwrap();
    assert_eq!(scales["vde_ev"].as_f64(), Some(3.27));
    assert!(scales["capillary"]["radius_ratio"].as_f64().unwrap() > 1.0);
    assert!(scales["reorganization_ev"].as_f64().unwrap() > 0.0);
}

#[test]
fn hydrated_electron_cavity_scale() {
    use research_engine::domains_fluid_water_electron as we;
    assert!((we::screened_bohr_radius(78.4).unwrap() - 78.4 * we::BOHR).abs() < 1e-20);
    assert!(we::screened_energy_ev(78.4).unwrap() < 0.0);
    assert!(we::screened_bohr_radius(0.0).is_err());
    let radius = we::capillary_cavity_radius(we::GAMMA_WATER, we::MASS, we::HBAR).unwrap();
    assert!((radius - 2.8580710555848763e-10).abs() < 1e-22);
    assert!(we::capillary_cavity_radius(0.0, we::MASS, we::HBAR).is_err());
    assert!(we::capillary_cavity_energy_ev(we::GAMMA_WATER, we::MASS, we::HBAR).unwrap() > 0.0);
    assert!(we::infinite_well_gap_ev(radius, we::MASS, we::HBAR).unwrap() > 0.0);
    assert!(we::infinite_well_gap_ev(0.0, we::MASS, we::HBAR).is_err());
    assert!(we::well_radius_for_gap(1.7, we::MASS, we::HBAR).unwrap() > 0.0);
    assert!(we::well_radius_for_gap(0.0, we::MASS, we::HBAR).is_err());
    let scales = we::hydrated_scales().unwrap();
    assert_eq!(scales.get("epsilon_water").and_then(Value::as_f64), Some(78.4));
    assert!(scales.get("cavity_energy_ev").and_then(Value::as_f64).unwrap() > 0.0);
}

#[test]
fn hydrated_electron_finite_well() {
    use research_engine::domains_fluid_water_well as well;
    let radius = well::capillary_cavity_radius();
    assert!((radius - 2.8580710555848763e-10).abs() < 1e-22);
    let born = well::born_depth_ev(radius, 78.4).unwrap();
    assert!(born > 0.0 && born < 3.0);
    assert!(well::threshold_depth_ev(radius).unwrap() > born);
    assert!(well::infinite_well_transition_ev(radius).unwrap() > 0.0);
    let roots = well::well_roots(radius, born).unwrap();
    assert!(roots.get("u_1s").and_then(Value::as_f64).is_some());
    assert!(roots.get("u_1p").and_then(Value::as_f64).is_none());
    assert!(roots.get("transition_ev").and_then(Value::as_f64).is_none());
    let deep = well::well_roots(radius, 30.0).unwrap();
    assert!(deep.get("transition_ev").and_then(Value::as_f64).is_some());
    assert!(well::required_depth_ev(radius, 1.7).unwrap().is_none());
    let minimum = well::minimum_required_depth(1.7).unwrap();
    assert!(minimum.get("excess_ev").and_then(Value::as_f64).unwrap() > 0.0);
    let scales = well::well_scales().unwrap();
    assert_eq!(scales.get("model").unwrap().get("epsilon_water").and_then(Value::as_f64), Some(78.4));
    assert!(scales.get("depth_scan").unwrap().as_array().unwrap().len() == 4);
    assert!(well::born_depth_ev(0.0, 78.4).is_err());
    assert!(well::well_roots(radius, 0.0).is_err());
    assert!(well::minimum_required_depth(0.0).is_err());
}

#[test]
fn pnn_atomic_report_writers() {
    use research_engine::domains_pnn_reports as reports;
    let path = temp_db("pnn-reports").parent().unwrap()
        .join(format!("report-{}.csv", COUNTER.load(Ordering::Relaxed)));
    let fields = vec!["compound_id".to_string(), "note".to_string(), "score".to_string()];
    let rows = vec![serde_json::json!({
        "compound_id": "C1", "note": "has, comma", "score": 0.985,
    })];
    reports::write_csv(&path, &fields, &rows).unwrap();
    let csv = std::fs::read(&path).unwrap();
    let text = String::from_utf8(csv).unwrap();
    assert!(text.starts_with("compound_id,note,score\r\n"));
    assert!(text.contains("\"has, comma\""));
    assert!(reports::write_csv(&path, &[], &rows).is_err());
    let json_path = path.with_extension("json");
    reports::write_json(&json_path, &serde_json::json!({"z": 1, "a": 2})).unwrap();
    let json_text = std::fs::read_to_string(&json_path).unwrap();
    assert!(json_text.starts_with("{\n  \"a\": 2,\n  \"z\": 1\n}\n"));
    let text_path = path.with_extension("txt");
    reports::write_text(&text_path, "line\n").unwrap();
    assert_eq!(std::fs::read_to_string(&text_path).unwrap(), "line\n");
}

#[test]
fn shallow_water_acoustic_horizon() {
    use research_engine::domains_fluid_water_analogue as wa;
    assert!((wa::sound_speed(0.1, 9.81).unwrap() - 0.9904544411531507).abs() < 1e-9);
    let radius = wa::horizon_radius(1e-3, 0.1, 9.81).unwrap();
    assert!(radius > 0.0);
    let kappa = wa::surface_gravity(1e-3, 0.1, 9.81).unwrap();
    assert!((kappa - 0.9904544411531507_f64.powi(2) / radius).abs() < 1e-9);
    assert!(wa::hawking_temperature(kappa).unwrap() > 0.0);
    let metric = wa::acoustic_metric(0.5, 1e-3, 0.1, 9.81).unwrap();
    assert_eq!(metric.get("g_rr").and_then(Value::as_f64), Some(1.0));
    assert_eq!(metric.get("g_phiphi").and_then(Value::as_f64), Some(0.25));
    assert!(metric.get("g_tt").and_then(Value::as_f64).unwrap() < 0.0);
    let lab = wa::lab_scales(0.1, 1e-3, 9.81).unwrap();
    assert!(lab.get("hawking_temperature_k").and_then(Value::as_f64).unwrap() > 0.0);
    let capillary = wa::capillary_length(0.0728, 998.0, 9.81).unwrap();
    assert!(capillary > 0.0);
    assert!((wa::capillary_ratio(radius, capillary).unwrap() - (capillary / radius).powi(2)).abs() < 1e-12);
    assert!(wa::long_wavelength_min_flow(0.1, 9.81, 0.0728, 998.0, 10.0).unwrap() > 0.0);
    let validity = wa::validity(0.1, 1e-3, 0.0728, 998.0, 9.81, 10.0).unwrap();
    assert!(validity.get("long_wavelength").and_then(Value::as_bool).is_some());
    assert!(wa::sound_speed(0.0, 9.81).is_err());
    assert!(wa::flow_velocity(0.0, 1e-3, 0.1, 9.81).is_err());
    assert!(wa::hawking_temperature(0.0).is_err());
    assert!(wa::capillary_ratio(radius, 0.0).is_err());
    assert!(wa::long_wavelength_min_flow(0.1, 9.81, 0.0728, 998.0, 0.0).is_err());
}

#[test]
fn pnn_library_curation_pipeline() {
    use research_engine::domains_pnn_curation as curation;
    fn compound(id: &str, smiles: &str) -> Value {
        serde_json::json!({
            "compound_id": id, "mw": 345.5, "logp": 2.6, "tpsa": 58.0,
            "hbd": 2, "hba": 5, "rotatable_bonds": 4,
            "name": id, "smiles": smiles, "charge": "", "pka": null,
        })
    }
    let inputs = vec![
        ("libA".to_string(), vec![compound("C1", "CCO"), compound("C2", "CCN")]),
        ("libB".to_string(), vec![compound("C1", "CCO")]),
    ];
    let prepared = curation::prepare_candidates(&inputs).unwrap();
    assert_eq!(prepared.len(), 3);
    assert!(curation::prepare_candidates(&[]).is_err());
    let deduped = curation::deduplicate(&prepared).unwrap();
    assert_eq!(deduped.get("stats").unwrap().get("duplicate_ids").and_then(Value::as_u64), Some(1));
    assert_eq!(deduped.get("stats").unwrap().get("duplicate_smiles").and_then(Value::as_u64), Some(0));
    let curated = curation::curate(&prepared, "A", 25, 0.1, None).unwrap();
    assert!(curated.get("summary").unwrap().get("selected").and_then(Value::as_u64).unwrap() <= 3);
    let capped = curation::curate(&prepared, "B", 25, 0.1, Some(1)).unwrap();
    assert_eq!(capped.get("summary").unwrap().get("selected").and_then(Value::as_u64), Some(1));
    assert_eq!(capped.get("summary").unwrap().get("truncated_by_max").and_then(Value::as_bool), Some(true));
    assert!(curation::curate(&prepared, "Z", 25, 0.1, None).is_err());
    assert!(curation::curate(&prepared, "B", 0, 0.1, None).is_err());
    assert!(curation::curate(&prepared, "B", 25, 0.0, None).is_err());
    assert!(curation::curate(&prepared, "B", 25, 0.1, Some(0)).is_err());
}

#[test]
fn pnn_csv_row_contracts() {
    use research_engine::domains_pnn_tables as tables;
    let compound = serde_json::json!({
        "compound_id": "C1", "mw": 345.5, "logp": 2.6, "tpsa": 58.0,
        "hbd": 2, "hba": 5, "rotatable_bonds": 4, "name": "Compound A",
        "smiles": "CCO", "pka": 8.2, "charge": "basic", "logbb": -0.3,
    });
    let bins = tables::property_bin(&compound, 0.1).unwrap();
    assert_eq!(bins.len(), 6);
    assert!(bins.iter().all(|value| *value >= 0 && *value < 10));
    assert!(tables::property_bin(&compound, 0.0).is_err());
    let result = serde_json::json!({
        "compound": compound,
        "tier": "A", "score": 0.98512345,
        "failed_criteria": ["logbb", "herg_liability"],
        "unknown_criteria": ["pka"],
    });
    let row = tables::screen_row(&result);
    assert_eq!(row.get("score").and_then(Value::as_str), Some("0.9851"));
    assert_eq!(row.get("failed_criteria").and_then(Value::as_str), Some("logbb;herg_liability"));
    assert_eq!(row.get("unknown_criteria").and_then(Value::as_str), Some("pka"));
    let candidate = serde_json::json!({
        "compound": compound, "source": "synthetic-library", "result": result,
    });
    let curated = tables::curated_row(&candidate, 0.1).unwrap();
    assert_eq!(curated.get("source").and_then(Value::as_str), Some("synthetic-library"));
    assert!(curated.get("property_bin").and_then(Value::as_str).unwrap().contains('-'));
    assert_eq!(tables::CURATED_FIELDS.len(), 17);
    assert_eq!(tables::SCREEN_FIELDS.len(), 21);
}

#[test]
fn pnn_screen_tiering_and_ranking() {
    use research_engine::domains_pnn_screen as screen;
    let good = serde_json::json!({
        "compound_id": "C1", "mw": 345.5, "logp": 2.6, "tpsa": 58.0,
        "hbd": 2, "hba": 5, "rotatable_bonds": 4, "pka": 8.2, "charge": "basic",
        "logbb": -0.3, "brain_plasma_ratio": 0.45, "oral_bioavailability": 24.0,
        "cyp3a4_inhibition": 18.0, "herg_liability": 8.0, "pnn_ec50_nm": 42.0,
    });
    let bad = serde_json::json!({
        "compound_id": "C2", "mw": 480.0, "logp": 4.2, "tpsa": 95.0,
        "hbd": 5, "hba": 9, "rotatable_bonds": 9, "herg_liability": 40.0,
    });
    let result = screen::evaluate_compound(&good);
    assert_eq!(result.get("tier").and_then(Value::as_str), Some("A"));
    assert!(result.get("compound").unwrap().get("name").and_then(Value::as_str) == Some(""));
    let rejected = screen::evaluate_compound(&bad);
    assert_eq!(rejected.get("tier").and_then(Value::as_str), Some("Reject"));
    let ranked = screen::screen_compounds(&[bad.clone(), good.clone()]);
    assert_eq!(ranked[0].get("tier").and_then(Value::as_str), Some("A"));
    let summary = screen::summarize(&ranked);
    assert_eq!(summary.get("total").and_then(Value::as_u64), Some(2));
    assert_eq!(summary.get("by_tier").unwrap().get("Reject").and_then(Value::as_u64), Some(1));
    assert!(summary.get("average_score").and_then(Value::as_f64).is_some());
    assert_eq!(screen::summarize(&[]).get("average_score").and_then(Value::as_f64), Some(0.0));
}

#[test]
fn pnn_compound_ingestion() {
    use research_engine::domains_pnn_compounds as compounds;
    use std::collections::BTreeMap;
    assert_eq!(compounds::normalize_field("CLogP"), Some("logp"));
    assert_eq!(compounds::normalize_field("Compound Name"), Some("name"));
    assert_eq!(compounds::normalize_field("Ionization"), Some("charge"));
    assert_eq!(compounds::normalize_field("bogus"), None);
    let row: BTreeMap<String, String> = [
        ("ID", "C1"), ("Molecular Weight", "345.5"), ("clogp", "2.6"),
        ("Polar Area", "58"), ("Donors", "2"), ("Acceptors", "5"), ("Rotors", "4"),
        ("Charge", "weakly basic"),
    ].into_iter().map(|(k, v)| (k.to_string(), v.to_string())).collect();
    let parsed = compounds::parse_compounds(&[row.clone()], "input", false).unwrap();
    assert_eq!(parsed.len(), 1);
    assert_eq!(parsed[0].get("compound_id").and_then(Value::as_str), Some("C1"));
    assert_eq!(parsed[0].get("charge").and_then(Value::as_str), Some("basic"));
    assert_eq!(parsed[0].get("mw").and_then(Value::as_f64), Some(345.5));
    assert!(compounds::parse_compounds(&[row.clone(), row.clone()], "input", false).is_err());
    assert_eq!(compounds::parse_compounds(&[row.clone(), row], "input", true).unwrap().len(), 2);
}

#[test]
fn pnn_docking_consensus_ranking() {
    use research_engine::domains_pnn_docking as docking;
    use std::collections::BTreeMap;
    let raw = serde_json::json!([
        {"Compound ID": "C1", "Target": "TP53", "Vina (kcal/mol)": "-9.2", "Glide": "-6.1", "mmGBSA": "-45.3", "RMSD": "1.2"},
        {"id": "C1", "receptor": "MDM2", "vinaaffinity": "-8.0", "dG": "-40.0"},
        {"compound": "C2", "targetname": "TP53", "affinity": "-7.5", "mmgbsadg": "-35.0"},
    ]);
    let rows: Vec<BTreeMap<String, String>> = serde_json::from_value(raw).unwrap();
    let scores = docking::parse_rows(&rows, "input").unwrap();
    assert_eq!(scores.len(), 3);
    let (kept, dropped) = docking::filter_scores(&scores, Some(2.0), Some(-8.5));
    assert_eq!(dropped, 2);
    assert_eq!(kept.len(), 1);
    let ranks = docking::normalize_scores(&kept);
    let aggregated = docking::aggregate_best(&ranks);
    assert_eq!(aggregated.len(), 1);
    assert!(aggregated.contains_key("C1"));
    assert_eq!(aggregated["C1"].get("targets_docked").and_then(Value::as_u64), Some(1));
    assert!(docking::parse_rows(&[], "empty").is_err());
}

#[test]
fn lattice_provider_parsers_and_urls() {
    use research_engine::lattice_providers as providers;
    let url = providers::query_url("crossref", "sleep memory", 5).unwrap();
    assert!(url.contains("query=sleep+memory") && url.contains("rows=5"));
    let crossref = r#"{"message":{"items":[{"title":["Quantum"],"DOI":"10.1/x"}]}}"#;
    let rows = providers::parse("crossref", crossref, 5).unwrap();
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].get("source").and_then(Value::as_str), Some("crossref"));
    let arxiv = r#"<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1</id><title>T</title></entry></feed>"#;
    assert_eq!(providers::parse("arxiv", arxiv, 5).unwrap().len(), 1);
    assert!(providers::parse("unknown", "{}", 5).is_err());
}

#[test]
fn pnn_design_rules_evaluate_compound() {
    use research_engine::domains_pnn_rules as rules;
    let compound = serde_json::json!({
        "mw": 345.5, "logp": 2.6, "tpsa": 58.0, "hbd": 2, "hba": 5,
        "rotatable_bonds": 4, "pka": 8.2, "charge": "basic", "logbb": -0.3,
        "brain_plasma_ratio": 0.45, "oral_bioavailability": 24.0,
        "cyp3a4_inhibition": 18.0, "herg_liability": 8.0, "pnn_ec50_nm": 42.0,
    });
    let results = rules::evaluate(&compound);
    assert_eq!(results.len(), 14);
    assert!(results.iter().all(|r| r.get("status").and_then(Value::as_str) == Some("PASS")));
    assert_eq!(rules::weight("mw"), 1.0);
    assert_eq!(rules::weight("logbb"), 0.5);
    let empty = serde_json::json!({"mw": 100.0, "logp": 0.0, "tpsa": 10.0,
        "hbd": 1, "hba": 1, "rotatable_bonds": 1});
    let verdicts = rules::evaluate(&empty);
    assert!(verdicts.iter().any(|r| r.get("status").and_then(Value::as_str) == Some("UNKNOWN")));
}

#[test]
fn obezite_citation_extraction_and_dedupe() {
    use research_engine::domains_obezite as obezite;
    let ids = obezite::atiflar("Bulgur 74, Nature. 2020;578(7795):444-448, PMID: 12345, 120 ve 42");
    assert_eq!(ids, vec![42, 74, 120]);
    let path = temp_db("obezite");
    let dir = path.parent().unwrap();
    let chunk = dir.join(format!("{}-chunk.md", path.file_name().unwrap().to_string_lossy()));
    let retracted = dir.join(format!("{}-cur.md", path.file_name().unwrap().to_string_lossy()));
    std::fs::write(&chunk, "| **1** | first | x |\n").unwrap();
    std::fs::write(&retracted, "| **1** | old | y |\n| **2** | keep | z |\n").unwrap();
    let archive = dir.join(format!("{}-archive.md", path.file_name().unwrap().to_string_lossy()));
    let updated = dir.join(format!("{}-updated.md", path.file_name().unwrap().to_string_lossy()));
    let result = obezite::deduplicate(&[chunk], &retracted, &archive, &updated, "2026-01-01").unwrap();
    assert_eq!(result.get("duplicates").and_then(Value::as_u64), Some(1));
    assert_eq!(result.get("remaining").and_then(Value::as_u64), Some(1));
    assert!(std::fs::read_to_string(&archive).unwrap().contains("### İddia 1"));
}

#[test]
fn fluid_bridge_primitives() {
    use research_engine::domains_fluid_bridge as bridge;
    assert!((bridge::diffusivity(1.0, 2.0).unwrap() - 0.25).abs() < 1e-12);
    assert!(bridge::diffusivity(-1.0, 2.0).is_err());
    assert!((bridge::horizon(1.0).unwrap() - std::f64::consts::PI / 4.0).abs() < 1e-12);
    let coeffs = bridge::pinney_coeffs(1.2, 1.0, 0.7853981633974483, 1.0, 1.0, 1.0).unwrap();
    assert_eq!(coeffs.len(), 2);
    let values = bridge::pinney_path(&coeffs[0], &[0.0, 0.5], 1.0);
    assert_eq!(values.len(), 2);
    assert!(values.iter().all(|v| *v >= 0.0));
}

#[test]
fn studio_client_read_only_policy() {
    let path = temp_db("client");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let writable = research_engine::studio_client::tool_schemas(false);
    let read_only = research_engine::studio_client::tool_schemas(true);
    assert!(writable.as_array().unwrap().len() > read_only.as_array().unwrap().len());
    assert_eq!(research_engine::studio_client::resource_schemas().as_array().map(|v| v.len()), Some(3));
    assert_eq!(research_engine::studio_client::prompt_schemas().as_array().map(|v| v.len()), Some(1));
    assert!(research_engine::studio_client::call_tool(&conn, true, "search",
        &serde_json::json!({"query": "x"}), &serde_json::json!({})).is_ok());
    assert!(research_engine::studio_client::call_tool(&conn, true, "add_question",
        &serde_json::json!({"text": "x"}), &serde_json::json!({})).is_err());
}

#[test]
fn studio_web_post_routes() {
    let path = temp_db("web_post");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let question = research_engine::studio_web::dispatch_web_request(&conn, "POST", "/api/questions",
        Some(r#"{"text":"Does it work?"}"#)).unwrap();
    assert_eq!(question.get("status").and_then(Value::as_i64), Some(200));
    let missing = research_engine::studio_web::dispatch_web_request(&conn, "POST", "/api/nope", None).unwrap();
    assert_eq!(missing.get("status").and_then(Value::as_i64), Some(404));
}

#[test]
fn pnn_safety_assessment_and_report() {
    use research_engine::domains_pnn_safety as safety;
    let heds = safety::noael_hed(50.0, "rat", 37.0).unwrap();
    assert!((heds - 8.108108108108109).abs() < 1e-12);
    assert!(safety::noael_hed(1.0, "unknown", 37.0).is_err());
    let studies = vec![serde_json::json!({
        "compound_id": "X", "species": "rat", "study_type": "subchronic",
        "noael_mg_kg": 50.0, "target_organ": "liver",
    })];
    let pharm = serde_json::json!({"X": {
        "herg_ic50_um": 30.0, "free_cmax_um": 0.5, "cyp3a4_inhibition_pct": 20.0,
        "ames_positive": false, "micronucleus_positive": false,
        "respiratory_noael_mg_kg": 100.0, "cns_noael_mg_kg": 80.0,
    }});
    let assessments = safety::assess(&studies, Some(&pharm), 10.0, 30.0, 10.0,
        50.0, 30.0, 60.0).unwrap();
    assert_eq!(assessments.len(), 1);
    assert!(["SAFE_TO_PROGRESS", "CAUTION", "FAIL_SAFETY"].contains(&field(&assessments[0], "status").as_str()));
    let report = safety::render_report(&assessments, &serde_json::json!({}));
    assert!(report.contains("PNN IND-Enabling Safety Pharmacology"));
}

#[test]
fn atlas_visual_schema_coercion_and_merge() {
    use research_engine::domains_atlas as atlas;
    let payload = serde_json::json!({
        "entities": [
            {"id": "e1", "name": "Hippocampus", "category": "anatomical-structure",
             "box": [100, 200, 400, 500], "confidence": 0.9},
            {"id": "e2", "name": "Memory", "category": "function", "confidence": 0.8},
        ],
        "relationships": [{"source_id": "e1", "target_id": "e2",
                           "rel_type": "participates-in", "confidence": 0.7}],
    });
    let analysis = atlas::coerce_muse_payload(&payload, "doc", 1, "fig").unwrap();
    assert_eq!(field(&analysis, "analysis_version"), "domains.atlas.visual-knowledge/v1");
    assert_eq!(analysis.get("entities").and_then(Value::as_array).map(|v| v.len()), Some(2));
    let merged = atlas::merge_analyses(&[analysis.clone()], "", "").unwrap();
    assert_eq!(merged.get("entities").and_then(Value::as_array).map(|v| v.len()), Some(2));
    assert!(atlas::coerce_muse_payload(&serde_json::json!({"entities": []}), "", 0, "").is_ok());
    assert!(atlas::coerce_muse_payload(&serde_json::json!({
        "entities": [{"id": "e", "name": "X", "category": "unknown", "confidence": 0.5}]
    }), "", 0, "").is_err());
}

#[test]
fn studio_web_routes_dispatch() {
    let path = temp_db("web");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let index = research_engine::studio_web::dispatch_web_request(&conn, "GET", "/", None).unwrap();
    assert_eq!(index.get("status").and_then(Value::as_i64), Some(200));
    assert!(field(&index, "body").contains("GraphRAG") || field(&index, "body").contains("Lattice"));
    let matrix = research_engine::studio_web::dispatch_web_request(&conn, "GET", "/api/matrix", None).unwrap();
    assert!(field(&matrix, "body").contains("\"matrix\""));
    let export = research_engine::studio_web::dispatch_web_request(&conn, "GET", "/api/export", None).unwrap();
    assert_eq!(field(&export, "content_type"), "application/x-ndjson; charset=utf-8");
    let missing = research_engine::studio_web::dispatch_web_request(&conn, "GET", "/api/nope", None).unwrap();
    assert_eq!(missing.get("status").and_then(Value::as_i64), Some(404));
}

#[test]
fn studio_mcp_message_dispatch() {
    let path = temp_db("mcp");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let ping = serde_json::json!({"jsonrpc": "2.0", "id": 1, "method": "ping"});
    let response = research_engine::studio_mcp::handle_message(&conn, &ping).unwrap();
    assert_eq!(response.get("id").and_then(Value::as_i64), Some(1));
    assert!(response.get("result").is_some());
    let tools = research_engine::studio_mcp::handle_message(&conn,
        &serde_json::json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})).unwrap();
    assert!(tools.get("result").and_then(|r| r.get("tools")).and_then(Value::as_array)
        .map(|list| list.len()).unwrap_or(0) >= 28);
    let notification = research_engine::studio_mcp::handle_message(&conn,
        &serde_json::json!({"jsonrpc": "2.0", "method": "notifications/initialized"}));
    assert!(notification.is_none());
    let unknown = research_engine::studio_mcp::handle_message(&conn,
        &serde_json::json!({"jsonrpc": "2.0", "id": 3, "method": "nope"})).unwrap();
    assert_eq!(unknown.get("error").and_then(|e| e.get("code")).and_then(Value::as_i64), Some(-32601));
}

#[test]
fn studio_evidence_matrix_and_question_evidence() {
    let path = temp_db("studio");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let mut metadata = std::collections::BTreeMap::new();
    metadata.insert("title".to_string(), "Quantum Effects".to_string());
    metadata.insert("doi".to_string(), "10.1/studio".to_string());
    let (paper, _) = research_engine::lattice_repo::add_paper(&conn, &metadata).unwrap();
    research_engine::lattice_repo::add_claim(&conn, &field(&paper, "id"), "It works",
        "quote", "abstract:s1", "supports", 0.8).unwrap();
    let question = research_engine::lattice_repo::add_question(&conn, "Does it work?").unwrap();
    research_engine::lattice_repo::add_edge(&conn, "c_000001", &field(&question, "id"), "supports", "").unwrap();

    let matrix = research_engine::studio_api::build_evidence_matrix(&conn).unwrap();
    assert_eq!(matrix.get("cells").and_then(Value::as_array).map(|v| v.len()), Some(1));
    let wanted = vec![field(&question, "id")];
    let filtered = research_engine::studio_api::get_evidence_matrix(&conn, Some(wanted.as_slice())).unwrap();
    assert_eq!(filtered.get("questions").and_then(Value::as_array).map(|v| v.len()), Some(1));
    let evidence = research_engine::studio_api::question_evidence(&conn, "q_000001").unwrap();
    assert_eq!(evidence.get("evidence_count").and_then(Value::as_u64), Some(1));
    assert!(research_engine::studio_api::question_evidence(&conn, "p_000001").is_err());
}

#[test]
fn lattice_discovery_offline_provider_and_ingest() {
    use research_engine::lattice_discovery as d;
    let found = d::offline_search("sleep memory", 5).unwrap();
    assert!(!found.is_empty());
    assert_eq!(field(&found[0], "source"), "offline");
    let deduped = d::dedupe(&[found[0].clone(), found[0].clone()]);
    assert_eq!(deduped.len(), 1);
    assert_eq!(d::provider_names(), vec!["arxiv", "crossref", "europepmc", "offline", "openalex"]);
    let path = temp_db("discovery");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let result = d::discover(&conn, "sleep", "offline", 3, true).unwrap();
    assert_eq!(result.get("count").and_then(Value::as_u64), Some(2));
    assert!(result.get("created").and_then(Value::as_u64).unwrap_or(0) > 0);
    assert!(d::offline_search("", 5).is_err());
}

#[test]
fn lattice_queries_detect_contradictions_and_pack_context() {
    let path = temp_db("lattice_query");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let mut metadata = std::collections::BTreeMap::new();
    metadata.insert("title".to_string(), "Quantum Effects".to_string());
    metadata.insert("doi".to_string(), "10.1/qq".to_string());
    let (paper, _) = research_engine::lattice_repo::add_paper(&conn, &metadata).unwrap();
    let pid = field(&paper, "id");
    research_engine::lattice_repo::add_claim(&conn, &pid, "Quantum simulation improves diffusion",
        "diffusion increased", "abstract:s1", "supports", 0.8).unwrap();
    research_engine::lattice_repo::add_claim(&conn, &pid, "Quantum simulation fails to improve diffusion",
        "diffusion unchanged", "abstract:s2", "contradicts", 0.7).unwrap();
    let question = research_engine::lattice_repo::add_question(&conn, "Does it improve?").unwrap();
    research_engine::lattice_repo::add_edge(&conn, "c_000001", &field(&question, "id"), "supports", "").unwrap();
    research_engine::lattice_repo::add_edge(&conn, "c_000002", &field(&question, "id"), "contradicts", "").unwrap();

    let pairs = research_engine::lattice_query::detect_contradictions(&conn, false).unwrap();
    assert_eq!(pairs.len(), 1);
    let outline = research_engine::lattice_query::outline(&conn, 400).unwrap();
    assert_eq!(outline.get("questions").and_then(Value::as_array).map(|v| v.len()), Some(1));
    let pack = research_engine::lattice_query::build_context_pack(&conn, &[], 2000, "markdown").unwrap();
    assert!(field(&pack, "content").contains("GraphRAG Evidence Pack"));
    let json_pack = research_engine::lattice_query::build_context_pack(&conn, &[], 2000, "json").unwrap();
    assert!(field(&json_pack, "content").contains("\"claims\""));
}

#[test]
fn meta_analysis_pools_studies() {
    use research_engine::meta;
    let studies = vec![
        serde_json::json!({"id": "s1", "effect_size": 0.5, "ci_lower": 0.1, "ci_upper": 0.9}),
        serde_json::json!({"id": "s2", "effect_size": 0.8, "ci_lower": 0.3, "ci_upper": 1.3}),
    ];
    let result = meta::compute_meta_analysis(&studies, "random").unwrap();
    assert_eq!(field(&result, "model"), "random");
    assert_eq!(result.get("studies").and_then(Value::as_array).map(|v| v.len()), Some(2));
    assert!(result.get("pooled_effect").and_then(Value::as_f64).unwrap() > 0.0);
    let ci = meta::study_from_ci("s", "Study", 0.5, 0.1, 0.9, "").unwrap();
    assert!(number(&ci, "se") > 0.0);
    let groups = meta::study_from_groups("g", "Groups", 30, 10.0, 2.0, 28, 8.5, 2.1, "").unwrap();
    assert!(number(&groups, "effect_size") > 0.0);
    let forest = meta::render_forest_ascii(&result, 40);
    assert!(forest.contains("Heterogeneity:"));
    assert!(meta::compute_meta_analysis(&[], "random").is_err());
}

fn number(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

#[test]
fn lattice_snapshots_are_deterministic() {
    let path = temp_db("lattice_snaps");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let mut metadata = std::collections::BTreeMap::new();
    metadata.insert("title".to_string(), "Quantum Effects".to_string());
    metadata.insert("doi".to_string(), "10.1/q".to_string());
    let (paper, _) = research_engine::lattice_repo::add_paper(&conn, &metadata).unwrap();
    let claim = research_engine::lattice_repo::add_claim(&conn, &field(&paper, "id"),
        "Effect reproduced", "we observed it", "abstract:s1", "supports", 0.5).unwrap();
    let question = research_engine::lattice_repo::add_question(&conn, "Does it reproduce?").unwrap();
    research_engine::lattice_repo::add_edge(&conn, &field(&claim, "id"), &field(&question, "id"),
        "supports", "").unwrap();

    let records = research_engine::lattice_snapshots::collect_records(&conn).unwrap();
    assert_eq!(records.len(), 4);
    assert_eq!(field(&records[0], "record_type"), "paper");
    let bibtex = research_engine::lattice_snapshots::format_bibtex(&conn).unwrap();
    assert!(bibtex.contains("@article{"));
    let cytoscape = research_engine::lattice_snapshots::cytoscape_data(&conn).unwrap();
    assert_eq!(cytoscape.get("elements").and_then(|e| e.get("nodes"))
        .and_then(Value::as_array).map(|v| v.len()), Some(3));
    let graphml = research_engine::lattice_snapshots::graphml_string(&conn).unwrap();
    assert!(graphml.contains("edge:1"));
    let out = path.with_extension("jsonl");
    let counts = research_engine::lattice_snapshots::export_snapshot(&conn, &out).unwrap();
    assert_eq!(counts.get("papers").and_then(Value::as_u64), Some(1));
    assert_eq!(std::fs::read_to_string(&out).unwrap().lines().count(), 4);
}

#[test]
fn lattice_repository_graph() {
    let path = temp_db("lattice_repo");
    let conn = research_engine::lattice_repo::open(path.to_str().unwrap()).unwrap();
    let mut metadata = std::collections::BTreeMap::new();
    metadata.insert("title".to_string(), "Quantum Effects".to_string());
    metadata.insert("doi".to_string(), "https://doi.org/10.1/q".to_string());
    metadata.insert("year".to_string(), "2024".to_string());
    let (paper, created) = research_engine::lattice_repo::add_paper(&conn, &metadata).unwrap();
    assert!(created);
    assert_eq!(field(&paper, "doi"), "10.1/q");
    let (same, created_again) = research_engine::lattice_repo::add_paper(&conn, &metadata).unwrap();
    assert!(!created_again);
    assert_eq!(field(&same, "id"), field(&paper, "id"));

    let claim = research_engine::lattice_repo::add_claim(&conn, &field(&paper, "id"),
        "The effect reproduced", "we observed it", "abstract:s1", "supports", 0.8).unwrap();
    let question = research_engine::lattice_repo::add_question(&conn, "Does it reproduce?").unwrap();
    research_engine::lattice_repo::add_edge(&conn, &field(&claim, "id"), &field(&question, "id"),
        "supports", "").unwrap();
    let found = research_engine::lattice_repo::search(&conn, "effect", 20).unwrap();
    assert_eq!(found.get("papers").and_then(Value::as_array).map(|v| v.len()), Some(1));
    assert_eq!(found.get("claims").and_then(Value::as_array).map(|v| v.len()), Some(1));
    let stats = research_engine::lattice_repo::stats(&conn).unwrap();
    assert_eq!(stats.get("edges").and_then(Value::as_i64), Some(1));
    let entity = research_engine::lattice_repo::get(&conn, &field(&claim, "id")).unwrap();
    assert!(entity.get("edges").and_then(Value::as_array).map(|v| v.len()).unwrap_or(0) > 0);
}

#[test]
fn lattice_value_rules_and_parsers() {
    use research_engine::lattice as l;
    assert_eq!(l::normalize_text("Fluid   Universe—101!"), "fluid universe 101");
    assert_eq!(l::normalize_tags("Physics; physics, AI ; ML"), "physics, ai, ml");
    assert_eq!(l::derive_tags("Quantum Field", "A computational simulation", 3).unwrap(),
        "quantum, field, computational");
    assert_eq!(l::normalize_study_type("RCT"), "Randomized Controlled Trial");
    assert_eq!(l::infer_study_type("A meta-analysis of trials", ""), "Meta-Analysis");
    assert_eq!(l::paper_id("Fluid Universe", "10.1/fluid", "").unwrap(), "p_ef3b1839141c");
    assert_eq!(l::validate_ref("claim:c_000001").unwrap(), "claim:c_000001");
    assert!(l::validate_ref("claim:p_000001").is_err());
    assert_eq!(l::parse_confidence(None).unwrap(), 0.5);
    assert!(l::parse_confidence(Some(1.5)).is_err());

    let bib = "@article{k, title={Quantum Effects}, author={Ada and Alan}, year={2024}, doi={10.1/q}}";
    let records = l::parse_bibtex(bib).unwrap();
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].get("authors").and_then(Value::as_str), Some("Ada; Alan"));
    let csl = r#"[{"title":"Quantum Effects","author":[{"family":"Lovelace","given":"Ada"}],"issued":{"date-parts":[[2024]]}}]"#;
    let records = l::parse_csl_json(csl).unwrap();
    assert_eq!(records[0].get("year").and_then(Value::as_str), Some("2024"));
}

#[test]
fn experiment_records_and_analysis() {
    let path = temp_db("experiments");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "N1 Program", "", None).unwrap();
    let rid = field(&research, "id");
    let intervention = research_engine::experiments::add_intervention(&conn, &rid, "dose A",
        "2026-01-01", None, Some("2026-02-14"), "10mg", "").unwrap();
    assert_eq!(field(&intervention, "id"), "iv_000001");
    research_engine::experiments::add_metric_definition(&conn, &rid, "m1", "desc", "mg").unwrap();
    for day in 18..32 {
        research_engine::experiments::add_metric(&conn, &rid, "m1", &format!("2026-01-{day:02}"),
            day as f64 / 10.0, Some("iv_000001"), "").unwrap();
    }
    for day in 1..15 {
        research_engine::experiments::add_metric(&conn, &rid, "m1", &format!("2026-02-{day:02}"),
            2.0 + day as f64 / 10.0, None, "").unwrap();
    }
    research_engine::experiments::add_event(&conn, &rid, "adverse", "2026-02-05T09:00:00+00:00",
        Some(2), "", Some("iv_000001")).unwrap();
    let metrics = research_engine::experiments::list_metrics(&conn, Some(&rid), Some("m1")).unwrap();
    assert_eq!(metrics.len(), 28);
    let analysis = research_engine::experiments::analyze_baseline_vs_intervention(&conn, &rid,
        "m1", "2026-02-01", 14, 14).unwrap();
    assert!(analysis.get("analysis").is_some());
    let correlation = research_engine::experiments::correlation_matrix(&conn, &rid, None).unwrap();
    assert_eq!(correlation.get("metrics").and_then(Value::as_array).map(|v| v.len()), Some(1));
    let sparse = research_engine::experiments::analyze_baseline_vs_intervention(&conn, &rid,
        "m1", "2027-01-01", 14, 14).unwrap();
    assert!(sparse.get("error").is_some());
}

#[test]
fn ai_artifacts_notarize_without_storing_raw_text() {
    let path = temp_db("ai");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "AI Program", "", None).unwrap();
    let rid = field(&research, "id");
    let source = core::add_source(&conn, &rid, "Paper", Some(2024), "", "", "", "paper").unwrap();
    let cited = vec![serde_json::json!({"source_id": field(&source, "id"), "locator": "p. 3"})];
    let artifact = research_engine::ai::record(&conn, &rid, "extraction", "local:test",
        "prompt bytes", "output bytes", &cited).unwrap();
    assert_eq!(field(&artifact, "prompt_sha256"),
        research_engine::util::sha256_text("prompt bytes"));
    assert_eq!(field(&artifact, "actor"), "model:local:test");
    assert!(field(&artifact, "cited_json").contains("p. 3"));
    assert!(!field(&artifact, "cited_json").contains("prompt bytes"));

    assert!(research_engine::ai::record(&conn, &rid, "sweep", "", "p", "o", &[]).is_err());
    let claim = research_engine::ai::ingest_claim(&conn, &field(&artifact, "id"), "AI claim",
        "empirical", Some(&field(&source, "id")), "quote", "p. 3", 0.5, "", "", &[], None,
        "supports", "agent").unwrap();
    assert_eq!(field(&claim, "status"), "UNVERIFIED");
    let events: i64 = conn.query_row("SELECT COUNT(*) FROM event WHERE kind IN ('ai.record','ai.ingest')", [], |r| r.get(0)).unwrap();
    assert_eq!(events, 2);
}

#[test]
fn diff_detects_added_records() {
    let path = temp_db("diff");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Diff", "", None).unwrap();
    let old = path.with_extension("old.jsonl");
    let new = path.with_extension("new.jsonl");
    research_engine::bundle::export_jsonl(&conn, &old, None).unwrap();
    core::add_claim(&conn, &field(&research, "id"), "Added", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();
    research_engine::bundle::export_jsonl(&conn, &new, None).unwrap();
    let result = research_engine::diffing::diff_files(&old, &new, true).unwrap();
    assert_eq!(result.get("counts").and_then(|c| c.get("added")).and_then(Value::as_u64), Some(1));
    assert_eq!(result.get("identical").and_then(Value::as_bool), Some(false));
    let same = research_engine::diffing::diff_files(&old, &old, true).unwrap();
    assert_eq!(same.get("identical").and_then(Value::as_bool), Some(true));
}

#[test]
fn discovery_ranks_from_the_graph() {
    let path = temp_db("discovery");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Discovery", "", None).unwrap();
    let rid = field(&research, "id");
    let source = core::add_source(&conn, &rid, "Paper", Some(2024), "", "", "", "paper").unwrap();
    let question = core::add_question(&conn, &rid, "Does X work?").unwrap();
    let qid = field(&question, "id");
    let a = core::add_claim(&conn, &rid, "X works", "empirical", Some(&field(&source, "id")),
        "quote", "p1", 0.8, "echo ok", "", &[]).unwrap();
    let b = core::add_claim(&conn, &rid, "X does not work", "empirical", Some(&field(&source, "id")),
        "quote", "p2", 0.7, "echo ok", "", &[]).unwrap();
    core::record_edge(&conn, "claim", &field(&a, "id"), "question", &qid, "supports").unwrap();
    core::record_edge(&conn, "claim", &field(&b, "id"), "question", &qid, "contradicts").unwrap();

    let pairs = research_engine::discovery::contradictions(&conn, &rid, 0.0).unwrap();
    assert_eq!(pairs.len(), 1);
    assert_eq!(field(&pairs[0], "support"), field(&a, "id"));
    assert_eq!(field(&pairs[0], "contradicts"), field(&b, "id"));
    assert!(pairs[0].get("polarity_mismatch").and_then(Value::as_bool).unwrap());

    let matrix = research_engine::discovery::evidence_matrix(&conn, &rid).unwrap();
    assert_eq!(matrix.get("rows").and_then(Value::as_array).map(|v| v.len()), Some(1));
    assert_eq!(matrix.get("rows").unwrap()[0].get("total").and_then(Value::as_i64), Some(2));

    let keystone = research_engine::discovery::keystone_claims(&conn, &rid, 10).unwrap();
    assert_eq!(keystone.len(), 2);
    let exposed = research_engine::discovery::expose(&conn, &field(&a, "id")).unwrap();
    assert_eq!(field(&exposed, "claim"), field(&a, "id"));

    let hypothesis = core::add_hypothesis(&conn, &rid, "X replicates", "no effect", 0.6, None).unwrap();
    core::record_outcome(&conn, &field(&hypothesis, "id"), "SUPPORTED", "study", "", "agent").unwrap();
    let calibration = research_engine::calibration::score(&conn, &rid, 10, "agent").unwrap();
    assert_eq!(calibration.get("counts").and_then(|c| c.get("resolved")).and_then(Value::as_i64), Some(1));
    let events: i64 = conn.query_row("SELECT COUNT(*) FROM event WHERE kind='hypothesis.calibration'", [], |r| r.get(0)).unwrap();
    assert_eq!(events, 1);
}

#[test]
fn bounded_views_and_manifest_digests() {
    let path = temp_db("views");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Views", "", None).unwrap();
    let question = core::add_question(&conn, &field(&research, "id"), "Is it real?").unwrap();
    let claim = core::add_claim(&conn, &field(&research, "id"), "It is real", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();
    core::record_edge(&conn, "claim", &field(&claim, "id"), "question", &field(&question, "id"), "supports").unwrap();
    core::set_verdict(&conn, &field(&claim, "id"), "PROVEN", "evidence", "", "", "agent").unwrap();

    let outline = research_engine::context::outline(&conn, &field(&research, "id"), 800).unwrap();
    assert!(field(&outline, "text").starts_with("OUTLINE r_000001"));
    let brief = research_engine::context::brief(&conn, &field(&research, "id"), 800).unwrap();
    assert!(field(&brief, "text").contains("Is it real?"));
    let tiny = research_engine::context::outline(&conn, &field(&research, "id"), 1).unwrap();
    assert!(tiny.get("omitted").and_then(Value::as_u64).unwrap() > 0);
    assert!(field(&tiny, "text").contains("OUTLINE"));

    let report_text = research_engine::synthesis::report(&conn, &field(&research, "id")).unwrap();
    let manifest = research_engine::manifest::build_manifest(&conn, &field(&research, "id"), &report_text).unwrap();
    assert_eq!(field(&manifest, "schema"), "research-engine.report/3");
    assert_eq!(field(&manifest, "report_sha256"),
        research_engine::util::digest("report/1", report_text.as_bytes()));
    assert_eq!(field(&manifest, "content_sha256"),
        research_engine::bundle::content_sha256(&conn, Some(&field(&research, "id"))).unwrap());
    assert_eq!(field(&manifest, "graph_sha256"),
        research_engine::bundle::graph_sha256(&conn, Some(&field(&research, "id"))).unwrap());
}

#[test]
fn export_is_self_verifying() {
    let path = temp_db("export");
    let conn = open(path.to_str().unwrap()).unwrap();
    initialize(&conn).unwrap();
    let research = core::add_research(&conn, "Export", "", None).unwrap();
    core::add_claim(&conn, &field(&research, "id"), "Exported", "derived",
        None, "", "", 0.5, "", "basis", &[]).unwrap();
    let out = path.with_extension("jsonl");
    let counts = research_engine::bundle::export_jsonl(&conn, &out, None).unwrap();
    assert_eq!(counts.get("claim").and_then(Value::as_u64), Some(1));
    let verified = research_engine::bundle::verify_export(&out).unwrap();
    assert_eq!(verified.get("ok").and_then(Value::as_bool), Some(true));
    assert_eq!(verified.get("records").and_then(Value::as_u64), Some(2)); // research + claim
}

#[test]
fn event_hash_matches_python_algorithm() {
    // Known-answer vector produced by engine/events.py::event_hash_for.
    let expected = "3aeec2a90f93534620f34bc6221960af490a48d6d61ac926d51105ad56abd46e";
    let actual = research_engine::util::event_hash_for(
        "", "ev_000001", "2026-01-01T00:00:00+00:00", "r_000001", "research.add",
        "r_000001", "", "engine", 1, "ev_000001", "",
    );
    assert_eq!(actual, expected);
}
