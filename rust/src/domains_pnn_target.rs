//! Target receptor profiles and Vina grid generation (domains/pnn/target.rs).

use serde_json::{json, Value};

use crate::error::{EngineError, Result};

pub fn target_profiles() -> Value {
    Value::Array(vec![
        json!({"target_id":"PTPsigma","name":"Protein Tyrosine Phosphatase Sigma (PTPRS)","gene_symbol":"PTPRS","uniprot_id":"Q13332","primary_pdb":"5K4P","resolution_angstrom":2.8,"domain":"D1 Ectodomain / CSPG Binding Site","pocket_type":"cspg_binding","grid_center":[12.5,18.3,22.1],"grid_size":[20.0,20.0,20.0],"key_residues":["Lys201","Arg204","Lys207","Arg210","Tyr199","Phe203"],"druggability":"Moderate","biological_function":"Primary neuronal receptor for CSPGs; binding triggers receptor dimerization, inhibiting neurite outgrowth and dephosphorylating the insulin receptor / IRS-1."}),
        json!({"target_id":"PTPsigma_catalytic","name":"PTPsigma Catalytic Domain (PTPRS D1)","gene_symbol":"PTPRS","uniprot_id":"Q13332","primary_pdb":"2PTS","resolution_angstrom":2.0,"domain":"Intracellular D1 Phosphatase Catalytic Pocket","pocket_type":"catalytic","grid_center":[24.0,15.2,-8.4],"grid_size":[18.0,18.0,18.0],"key_residues":["Cys267","Arg268","Asp326"],"druggability":"High","biological_function":"Intracellular catalytic pocket hydrolyzing phosphotyrosine on IRS-1 and downstream adaptors."}),
        json!({"target_id":"LAR","name":"Leukocyte Common Antigen-Related Phosphatase (PTPRF)","gene_symbol":"PTPRF","uniprot_id":"P10586","primary_pdb":"2LAR","resolution_angstrom":1.9,"domain":"D1 Catalytic / CSPG Co-Receptor Domain","pocket_type":"catalytic","grid_center":[18.1,10.4,15.8],"grid_size":[20.0,20.0,20.0],"key_residues":["Cys1522","Arg1528","Asp1490"],"druggability":"High","biological_function":"Co-receptor for CSPG inhibition; operates cooperatively with PTPsigma to suppress hypothalamic insulin signaling in diet-induced obesity."}),
        json!({"target_id":"NgR1","name":"Nogo-66 Receptor 1 (RTN4R)","gene_symbol":"RTN4R","uniprot_id":"Q9BZF1","primary_pdb":"2OZ7","resolution_angstrom":2.4,"domain":"Leucine-Rich Repeat (LRR) Ectodomain","pocket_type":"allosteric_lrr","grid_center":[-4.5,32.1,12.0],"grid_size":[24.0,24.0,24.0],"key_residues":["Arg68","Asn115","Arg140"],"druggability":"Moderate","biological_function":"High-affinity GPI-anchored co-receptor signaling growth cone collapse and restricting plasticity upon CSPG engagement."}),
        json!({"target_id":"MMP2","name":"Matrix Metalloproteinase-2 (72 kDa Type IV Collagenase)","gene_symbol":"MMP2","uniprot_id":"P08253","primary_pdb":"1CK7","resolution_angstrom":1.5,"domain":"Zinc-Dependent Catalytic Cleft","pocket_type":"catalytic","grid_center":[14.2,28.5,34.0],"grid_size":[18.0,18.0,18.0],"key_residues":["His403","His407","His413","Glu404"],"druggability":"High","biological_function":"Endogenous enzyme responsible for physiological turnover and cleavage of CSPG core proteins."}),
        json!({"target_id":"ChABC","name":"Chondroitinase ABC Lyase (Proteus vulgaris)","gene_symbol":"PL8","uniprot_id":"P59807","primary_pdb":"1L5D","resolution_angstrom":1.8,"domain":"Polysaccharide Lyase Catalytic Domain","pocket_type":"catalytic","grid_center":[30.5,42.1,15.6],"grid_size":[22.0,22.0,22.0],"key_residues":["His200","Tyr247","Arg287"],"druggability":"Moderate","biological_function":"Bacterial polysaccharide lyase serving as the benchmark standard for complete PNN degradation; small-molecule mimics target its catalytic cleft mechanism to achieve non-enzymatic cleavage."}),
        json!({"target_id":"ADAMTS4","name":"ADAMTS-4 Aggrecanase-1","gene_symbol":"ADAMTS4","uniprot_id":"O75173","primary_pdb":"2RJP","resolution_angstrom":1.5,"domain":"Zinc Metalloproteinase Catalytic & Disintegrin Domain","pocket_type":"catalytic_zinc","grid_center":[28.4,-12.1,45.6],"grid_size":[20.0,20.0,20.0],"key_residues":["His202","His206","His212","Glu203","Leu165","Phe198"],"druggability":"High","biological_function":"Endogenous CNS aggrecanase responsible for interglobular cleavage of CSPGs (aggrecan, brevican, neurocan); allosteric activation or selective engagement induces physiological PNN softening."}),
        json!({"target_id":"MMP9","name":"Matrix Metalloproteinase-9 (92 kDa Gelatinase B)","gene_symbol":"MMP9","uniprot_id":"P14780","primary_pdb":"1GKC","resolution_angstrom":2.3,"domain":"Zinc Catalytic Domain with Fibronectin Type II Repeats","pocket_type":"catalytic_zinc","grid_center":[38.2,16.5,24.8],"grid_size":[20.0,20.0,20.0],"key_residues":["His401","His405","His411","Glu402","Leu188","Met422"],"druggability":"High","biological_function":"Activity-dependent synaptic matrix metalloproteinase in the hypothalamus; cleaves PNN CSPG components and matrix scaffolds to restore insulin signaling and facilitate synaptic plasticity."}),
    ])
}

fn field(value: &Value, key: &str) -> String {
    value.get(key).and_then(Value::as_str).unwrap_or("").to_string()
}

fn number(value: &Value, key: &str) -> f64 {
    value.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

fn coord(value: &Value, key: &str, index: usize) -> f64 {
    value.get(key).and_then(Value::as_array)
        .and_then(|a| a.get(index)).and_then(Value::as_f64).unwrap_or(0.0)
}

pub fn get_target(target_id: &str) -> Result<Value> {
    let normalized = target_id.trim().to_lowercase();
    let profiles = target_profiles();
    for profile in profiles.as_array().unwrap() {
        if field(profile, "target_id").to_lowercase() == normalized {
            return Ok(profile.clone());
        }
    }
    let valid = profiles.as_array().unwrap().iter()
        .map(|p| field(p, "target_id")).collect::<Vec<_>>().join(", ");
    Err(EngineError::new(format!("Unknown target ID '{target_id}'. Valid targets are: {valid}"),
        "target IDs are a closed vocabulary", "pass one of the listed target IDs"))
}

pub fn generate_vina_config(profile: &Value, receptor_pdbqt: &str, out_pdbqt: &str,
                            exhaustiveness: i64, num_modes: i64, energy_range: i64) -> String {
    let residues = profile.get("key_residues").and_then(Value::as_array).unwrap()
        .iter().map(|v| v.as_str().unwrap_or("").to_string()).collect::<Vec<_>>().join(", ");
    let lines = vec![
        format!("# AutoDock Vina configuration for PNN target: {} ({})",
            field(profile, "name"), field(profile, "target_id")),
        format!("# Primary PDB structure: {} ({} A resolution)",
            field(profile, "primary_pdb"), number(profile, "resolution_angstrom")),
        format!("# Binding pocket: {} [{}]", field(profile, "pocket_type"), field(profile, "domain")),
        format!("# Key residues: {residues}"),
        String::new(),
        format!("receptor = {receptor_pdbqt}"),
        format!("out = {out_pdbqt}"),
        String::new(),
        "# Grid Center (Angstrom)".to_string(),
        format!("center_x = {:.3}", coord(profile, "grid_center", 0)),
        format!("center_y = {:.3}", coord(profile, "grid_center", 1)),
        format!("center_z = {:.3}", coord(profile, "grid_center", 2)),
        String::new(),
        "# Grid Dimensions (Angstrom)".to_string(),
        format!("size_x = {:.1}", coord(profile, "grid_size", 0)),
        format!("size_y = {:.1}", coord(profile, "grid_size", 1)),
        format!("size_z = {:.1}", coord(profile, "grid_size", 2)),
        String::new(),
        "# Search Parameters".to_string(),
        format!("exhaustiveness = {exhaustiveness}"),
        format!("num_modes = {num_modes}"),
        format!("energy_range = {energy_range}"),
        String::new(),
    ];
    lines.join("\n")
}
