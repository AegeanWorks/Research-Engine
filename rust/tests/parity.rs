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
