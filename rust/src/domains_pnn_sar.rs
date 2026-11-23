//! SMILES graph parsing and Bemis-Murcko scaffold decomposition (domains/pnn/sar.rs).

use std::collections::{BTreeSet, HashMap};
use std::sync::OnceLock;

use regex::Regex;
use serde_json::{json, Value};

use crate::error::{EngineError, Result};

fn token_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(concat!(
        r"(?P<BRACKET>\[[^\]]+\])|",
        r"(?P<HALOGEN>Cl|Br)|",
        r"(?P<ATOM>[BCNOPSbcnopsFI])|",
        r"(?P<RING_2>%\d{2})|",
        r"(?P<RING_1>\d)|",
        r"(?P<BOND>[-=#:/\\.])|",
        r"(?P<BRANCH_OPEN>\()|",
        r"(?P<BRANCH_CLOSE>\))",
    )).unwrap())
}

pub fn parse_smiles_graph(smiles: &str) -> Result<(Vec<String>, HashMap<usize, BTreeSet<usize>>)> {
    let clean = smiles.trim();
    if clean.is_empty() { return Err(EngineError::new("Empty SMILES string", "a SMILES must not be empty", "pass a SMILES")); }
    let names = ["BRACKET", "HALOGEN", "ATOM", "RING_2", "RING_1", "BOND", "BRANCH_OPEN", "BRANCH_CLOSE"];
    let mut atoms = Vec::new();
    let mut adj: HashMap<usize, BTreeSet<usize>> = HashMap::new();
    let mut ring_open: HashMap<usize, usize> = HashMap::new();
    let mut branch_stack: Vec<usize> = Vec::new();
    let mut prev_atom: Option<usize> = None;
    let mut pending_bond: Option<String> = None;
    for capture in token_re().captures_iter(clean) {
        let matched = names.iter().find_map(|name| capture.name(name).map(|m| (*name, m.as_str().to_string())));
        let Some((kind, value)) = matched else { continue };
        match kind {
            "BRACKET" | "HALOGEN" | "ATOM" => {
                let idx = atoms.len();
                atoms.push(value);
                adj.insert(idx, BTreeSet::new());
                if let Some(previous) = prev_atom {
                    if pending_bond.as_deref() != Some(".") {
                        adj.get_mut(&previous).unwrap().insert(idx);
                        adj.get_mut(&idx).unwrap().insert(previous);
                    }
                }
                prev_atom = Some(idx);
                pending_bond = None;
            }
            "BOND" => pending_bond = Some(value),
            "RING_1" | "RING_2" => {
                let ring_id: usize = value.replace('%', "").parse().unwrap_or(0);
                let current = prev_atom.ok_or_else(|| EngineError::new(
                    format!("Ring identifier with no preceding atom in SMILES: {smiles}"),
                    "a ring bond needs an atom", "pass a valid SMILES"))?;
                if let Some(other) = ring_open.remove(&ring_id) {
                    adj.get_mut(&other).unwrap().insert(current);
                    adj.get_mut(&current).unwrap().insert(other);
                } else {
                    ring_open.insert(ring_id, current);
                    pending_bond = None;
                }
            }
            "BRANCH_OPEN" => {
                if prev_atom.is_none() {
                    return Err(EngineError::new(format!("Branch open with no preceding atom in SMILES: {smiles}"),
                        "a branch needs an atom", "pass a valid SMILES"));
                }
                branch_stack.push(prev_atom.unwrap());
            }
            "BRANCH_CLOSE" => {
                if branch_stack.is_empty() {
                    return Err(EngineError::new(format!("Unmatched closing parenthesis in SMILES: {smiles}"),
                        "parentheses must balance", "pass a valid SMILES"));
                }
                prev_atom = branch_stack.pop();
            }
            _ => {}
        }
    }
    if atoms.is_empty() { return Err(EngineError::new(format!("No valid atoms parsed from SMILES: {smiles}"),
        "a SMILES needs at least one atom", "pass a valid SMILES")); }
    if !branch_stack.is_empty() { return Err(EngineError::new(format!("Unclosed branch parenthesis in SMILES: {smiles}"),
        "parentheses must balance", "pass a valid SMILES")); }
    if !ring_open.is_empty() { return Err(EngineError::new(format!("Unclosed ring identifier in SMILES: {smiles}"),
        "ring identifiers must pair", "pass a valid SMILES")); }
    Ok((atoms, adj))
}

pub fn find_biconnected_blocks(n: usize, adj: &HashMap<usize, BTreeSet<usize>>) -> Vec<BTreeSet<usize>> {
    let mut visited = vec![false; n];
    let mut depth = vec![0usize; n];
    let mut low = vec![0usize; n];
    let mut parent = vec![usize::MAX; n];
    let mut stack: Vec<(usize, usize)> = Vec::new();
    let mut blocks = Vec::new();
    fn dfs(u: usize, d: usize, visited: &mut [bool], depth: &mut [usize], low: &mut [usize],
           parent: &mut [usize], adj: &HashMap<usize, BTreeSet<usize>>,
           stack: &mut Vec<(usize, usize)>, blocks: &mut Vec<BTreeSet<usize>>) {
        visited[u] = true;
        depth[u] = d;
        low[u] = d;
        let neighbours: Vec<usize> = adj.get(&u).map(|s| s.iter().copied().collect()).unwrap_or_default();
        for v in neighbours {
            if v == parent[u] { continue; }
            if visited[v] {
                low[u] = low[u].min(depth[v]);
                if depth[v] < depth[u] { stack.push((u, v)); }
            } else {
                parent[v] = u;
                stack.push((u, v));
                dfs(v, d + 1, visited, depth, low, parent, adj, stack, blocks);
                low[u] = low[u].min(low[v]);
                if low[v] >= depth[u] {
                    let mut block = BTreeSet::new();
                    loop {
                        let Some(edge) = stack.pop() else { break };
                        block.insert(edge.0);
                        block.insert(edge.1);
                        if edge == (u, v) { break; }
                    }
                    if block.len() >= 3 { blocks.push(block); }
                }
            }
        }
    }
    for i in 0..n {
        if !visited[i] { dfs(i, 0, &mut visited, &mut depth, &mut low, &mut parent, adj, &mut stack, &mut blocks); }
    }
    blocks
}

pub fn serialize_subgraph_smiles(atoms: &[String], adj: &HashMap<usize, BTreeSet<usize>>,
                                 nodes: &[usize]) -> String {
    if nodes.is_empty() { return String::new(); }
    let node_set: BTreeSet<usize> = nodes.iter().copied().collect();
    let sub_adj: HashMap<usize, Vec<usize>> = node_set.iter().map(|u| (*u,
        adj.get(u).map(|s| s.iter().copied().filter(|v| node_set.contains(v)).collect()).unwrap_or_default()
    )).collect();
    let root = *node_set.iter().min_by_key(|u| (sub_adj.get(u).map(|v| v.len()).unwrap_or(0), **u)).unwrap();
    let mut visited = BTreeSet::new();
    let mut ring_closures: HashMap<(usize, usize), usize> = HashMap::new();
    let mut next_ring = 1usize;
    let mut tree_children: HashMap<usize, Vec<usize>> = HashMap::new();
    let mut ring_edges: HashMap<usize, Vec<(usize, usize)>> = HashMap::new();
    fn dfs(u: usize, p: Option<usize>, sub_adj: &HashMap<usize, Vec<usize>>,
           visited: &mut BTreeSet<usize>, ring_closures: &mut HashMap<(usize, usize), usize>,
           next_ring: &mut usize, tree_children: &mut HashMap<usize, Vec<usize>>,
           ring_edges: &mut HashMap<usize, Vec<(usize, usize)>>) {
        visited.insert(u);
        for v in sub_adj.get(&u).cloned().unwrap_or_default() {
            if Some(v) == p { continue; }
            if visited.contains(&v) {
                if !ring_closures.contains_key(&(v, u)) {
                    let rid = *next_ring;
                    *next_ring += 1;
                    ring_closures.insert((u, v), rid);
                    ring_edges.entry(u).or_default().push((v, rid));
                    ring_edges.entry(v).or_default().push((u, rid));
                }
            } else {
                tree_children.entry(u).or_default().push(v);
                dfs(v, Some(u), sub_adj, visited, ring_closures, next_ring, tree_children, ring_edges);
            }
        }
    }
    dfs(root, None, &sub_adj, &mut visited, &mut ring_closures, &mut next_ring,
        &mut tree_children, &mut ring_edges);
    fn to_smiles(u: usize, atoms: &[String], tree_children: &HashMap<usize, Vec<usize>>,
                 ring_edges: &HashMap<usize, Vec<(usize, usize)>>) -> String {
        let mut out = atoms.get(u).cloned().unwrap_or_default();
        let mut rings = ring_edges.get(&u).cloned().unwrap_or_default();
        rings.sort_by_key(|x| x.1);
        for (_, rid) in rings {
            if rid < 10 { out.push_str(&rid.to_string()); } else { out.push_str(&format!("%{rid}")); }
        }
        let children = tree_children.get(&u).cloned().unwrap_or_default();
        if children.is_empty() { return out; }
        for c in &children[..children.len() - 1] {
            out.push('(');
            out.push_str(&to_smiles(*c, atoms, tree_children, ring_edges));
            out.push(')');
        }
        out.push_str(&to_smiles(*children.last().unwrap(), atoms, tree_children, ring_edges));
        out
    }
    to_smiles(root, atoms, &tree_children, &ring_edges)
}

fn identify_scaffold_name(atoms: &[String], blocks: &[BTreeSet<usize>], linkers: &BTreeSet<usize>) -> String {
    let mut ring_names = Vec::new();
    for block in blocks {
        let syms: Vec<String> = block.iter().map(|i| atoms.get(*i).cloned().unwrap_or_default()).collect();
        let has_n = syms.iter().any(|s| s == "N" || s == "n");
        let has_o = syms.iter().any(|s| s == "O" || s == "o");
        let has_s = syms.iter().any(|s| s == "S" || s == "s");
        let is_aromatic = syms.iter().any(|s| s.chars().any(|c| c.is_lowercase()));
        let count = |symbol: &str| syms.iter().filter(|s| *s == symbol).count();
        let name = match syms.len() {
            6 => {
                if has_n && has_o { "Morpholine".to_string() }
                else if count("N") >= 2 || count("n") >= 2 {
                    if is_aromatic { "Pyrimidine".to_string() } else { "Piperazine".to_string() }
                } else if has_n { if is_aromatic { "Pyridine".to_string() } else { "Piperidine".to_string() } }
                else if is_aromatic { "Phenyl".to_string() } else { "Cyclohexyl".to_string() }
            }
            5 => {
                if has_s && has_n { "Thiazole".to_string() }
                else if has_o { "Furan".to_string() }
                else if has_n { if is_aromatic { "Pyrrole".to_string() } else { "Pyrrolidine".to_string() } }
                else { "Cyclopentyl".to_string() }
            }
            3 => "Cyclopropyl".to_string(),
            4 => "Cyclobutyl".to_string(),
            size if size > 6 => format!("FusedPolycycle-{size}"),
            size => format!("Ring-{size}"),
        };
        ring_names.push(name);
    }
    let linker_syms: String = linkers.iter().map(|i| atoms.get(*i).cloned().unwrap_or_default()).collect();
    let linker_name = if linker_syms.contains('S') { "Sulfonamide" }
        else if (linker_syms.contains('N') || linker_syms.contains('n'))
            && (linker_syms.contains('C') || linker_syms.contains('c'))
            && (linker_syms.contains('O') || linker_syms.contains('o')) { "Carboxamide" }
        else if linker_syms.contains('O') { "Ether" }
        else if linker_syms.contains('N') { "Amine" }
        else if !linker_syms.is_empty() { "AlkylLinker" }
        else { "" };
    if ring_names.is_empty() { return "Acyclic-Chain".to_string(); }
    let mut unique = ring_names;
    unique.sort();
    unique.dedup();
    let base = unique.join("-");
    if linker_name.is_empty() { base } else { format!("{base}_{linker_name}") }
}

pub fn extract_scaffold(smiles: &str) -> Result<Value> {
    let (atoms, adj) = parse_smiles_graph(smiles)?;
    let blocks = find_biconnected_blocks(atoms.len(), &adj);
    if blocks.is_empty() {
        return Ok(json!({"core_smiles": smiles, "scaffold_name": "Acyclic-Scaffold", "r_groups": "None"}));
    }
    let mut all_cycle = BTreeSet::new();
    for block in &blocks { all_cycle.extend(block.iter().copied()); }
    let all_nodes: BTreeSet<usize> = (0..atoms.len()).collect();
    let non_cycle: BTreeSet<usize> = all_nodes.difference(&all_cycle).copied().collect();
    let mut visited_nc = BTreeSet::new();
    let mut linkers = BTreeSet::new();
    let mut substituents = Vec::new();
    for node in &non_cycle {
        if visited_nc.contains(node) { continue; }
        let mut comp = Vec::new();
        let mut queue = vec![*node];
        visited_nc.insert(*node);
        while let Some(curr) = queue.pop() {
            comp.push(curr);
            for nbr in adj.get(&curr).cloned().unwrap_or_default() {
                if non_cycle.contains(&nbr) && !visited_nc.contains(&nbr) {
                    visited_nc.insert(nbr);
                    queue.push(nbr);
                }
            }
        }
        let mut attached_cycle = BTreeSet::new();
        let mut attached_blocks = BTreeSet::new();
        for c_node in &comp {
            for nbr in adj.get(c_node).cloned().unwrap_or_default() {
                if all_cycle.contains(&nbr) {
                    attached_cycle.insert(nbr);
                    for (idx, block) in blocks.iter().enumerate() {
                        if block.contains(&nbr) { attached_blocks.insert(idx); }
                    }
                }
            }
        }
        let comp_str: String = comp.iter().map(|i| atoms.get(*i).cloned().unwrap_or_default()).collect();
        if attached_blocks.len() >= 2 || attached_cycle.len() >= 2 {
            linkers.extend(comp);
        } else {
            substituents.push(comp_str);
        }
    }
    let framework: BTreeSet<usize> = all_cycle.union(&linkers).copied().collect();
    let framework_nodes: Vec<usize> = framework.into_iter().collect();
    let core_smiles = serialize_subgraph_smiles(&atoms, &adj, &framework_nodes);
    let scaffold_name = identify_scaffold_name(&atoms, &blocks, &linkers);
    Ok(json!({
        "core_smiles": core_smiles,
        "scaffold_name": scaffold_name,
        "r_groups": if substituents.is_empty() { "None".to_string() } else { substituents.join(", ") },
    }))
}

pub fn graph_json(smiles: &str) -> Result<Value> {
    let (atoms, adj) = parse_smiles_graph(smiles)?;
    let edges: Vec<Value> = adj.iter().flat_map(|(u, vs)| vs.iter().map(move |v| json!([u, v]))).collect();
    Ok(json!({"atoms": atoms, "edges": edges}))
}

pub fn parse_xs(raw: &str) -> Result<Vec<String>> {
    serde_json::from_str(raw).map_err(|e| EngineError::new(
        format!("invalid JSON: {e}"), "expected a JSON array of strings",
        "pass an array of strings"))
}
