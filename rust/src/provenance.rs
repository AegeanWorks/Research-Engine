//! Workspace provenance: the exact code and input identity each run is bound to.
//!
//! Length-prefixed `(name, kind, content)` hashing mirrors
//! `engine/provenance.py`, so a run recorded by either implementation has the
//! same `code_sha256` and `inputs_sha256` for an unchanged tree.

use std::path::{Path, PathBuf};
use std::process::Command;

use sha2::{Digest, Sha256};

use crate::error::{EngineError, Result};

const KIND_FILE: &[u8] = b"file";
const KIND_MISSING: &[u8] = b"missing";

pub fn project_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("rust crate lives inside the project")
        .to_path_buf()
}

fn digest_entries(entries: &[(String, &[u8], Vec<u8>)]) -> String {
    let mut hasher = Sha256::new();
    for (name, kind, content) in entries {
        let encoded = name.as_bytes();
        hasher.update((encoded.len() as u64).to_be_bytes());
        hasher.update(encoded);
        hasher.update([kind.len() as u8]);
        hasher.update(kind);
        hasher.update((content.len() as u64).to_be_bytes());
        hasher.update(content);
    }
    format!("{:x}", hasher.finalize())
}

fn collect_python_files(dir: &Path, root: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    for entry in std::fs::read_dir(dir)? {
        let path = entry?.path();
        if path.is_dir() {
            if path.file_name().and_then(|n| n.to_str()) == Some("__pycache__") {
                continue;
            }
            collect_python_files(&path, root, out)?;
        } else if path.extension().and_then(|e| e.to_str()) == Some("py") {
            out.push(path.strip_prefix(root).unwrap_or(&path).to_path_buf());
        }
    }
    Ok(())
}

pub fn code_sha256() -> Result<(String, usize)> {
    let root = project_root();
    let mut files = Vec::new();
    collect_python_files(&root.join("engine"), &root, &mut files)?;
    files.sort();
    let entries: Vec<(String, &[u8], Vec<u8>)> = files.iter()
        .map(|relative| {
            let name = relative.to_string_lossy().replace('\\', "/");
            let content = std::fs::read(root.join(relative))?;
            Ok((name, KIND_FILE, content))
        })
        .collect::<Result<Vec<_>>>()?;
    let count = entries.len();
    Ok((digest_entries(&entries), count))
}

pub fn resolve_inputs(declarations: &[String]) -> Result<Vec<String>> {
    let root = project_root();
    let mut names: Vec<String> = Vec::new();
    for raw in declarations {
        let raw = raw.trim();
        if raw.is_empty() { continue; }
        let path = if Path::new(raw).is_absolute() {
            PathBuf::from(raw)
        } else {
            root.join(raw)
        };
        // Only literal file paths are expanded: glob expansion requires a glob
        // dependency, and a literal declaration is the common case.
        if path.is_dir() {
            return Err(EngineError::new(
                format!("declared input is a directory: {raw}"),
                "a directory has no stable content, so binding it would hash nothing.",
                "declare the files with a glob such as `--input data/*.csv`, or declare each file.",
            ));
        }
        let name = if path.exists() {
            path.strip_prefix(&root).map(|p| p.to_string_lossy().replace('\\', "/"))
                .unwrap_or_else(|_| raw.to_string())
        } else {
            raw.to_string()
        };
        names.push(name);
    }
    names.sort();
    names.dedup();
    Ok(names)
}

pub fn inputs_sha256(declarations: &[String]) -> Result<(String, usize)> {
    let root = project_root();
    let mut entries: Vec<(String, &[u8], Vec<u8>)> = Vec::new();
    for name in resolve_inputs(declarations)? {
        let path = if Path::new(&name).is_absolute() { PathBuf::from(&name) } else { root.join(&name) };
        if path.is_dir() {
            return Err(EngineError::new(
                format!("declared input is a directory: {name}"),
                "a directory has no stable content to bind.",
                "declare files or a glob pattern instead.",
            ));
        }
        if path.is_file() {
            entries.push((name, KIND_FILE, std::fs::read(&path)?));
        } else {
            entries.push((name, KIND_MISSING, Vec::new()));
        }
    }
    let count = entries.len();
    Ok((digest_entries(&entries), count))
}

#[derive(Debug, Clone)]
pub struct Fingerprint {
    pub code_sha256: String,
    pub inputs_sha256: String,
    pub code_files: usize,
    pub input_files: usize,
}

pub fn fingerprint(inputs: &[String]) -> Result<Fingerprint> {
    let (code, code_files) = code_sha256()?;
    let (input, input_files) = inputs_sha256(inputs)?;
    Ok(Fingerprint { code_sha256: code, inputs_sha256: input, code_files, input_files })
}

pub fn git_state() -> (String, bool) {
    let root = project_root();
    let commit = Command::new("git").args(["rev-parse", "HEAD"]).current_dir(&root).output()
        .ok().filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).unwrap_or_else(|| "no-git".to_string());
    let status = Command::new("git").args(["status", "--porcelain"]).current_dir(&root).output()
        .ok().filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| !s.trim().is_empty()).unwrap_or(true);
    (commit, status)
}
