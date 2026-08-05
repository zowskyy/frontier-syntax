use crate::error::FrontierError;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct MigrationReport {
    pub source_language: String,
    pub files_scanned: usize,
    pub files_migrated: usize,
    pub files_manual: usize,
    pub output_dir: PathBuf,
}

pub fn detect_language(input: &Path) -> String {
    if input.join("Cargo.toml").exists() {
        return "Rust".into();
    }
    for entry in walk_files(input) {
        let ext = entry
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();
        match ext.as_str() {
            "py" => return "Python".into(),
            "java" => return "Java".into(),
            "js" | "jsx" | "ts" | "tsx" => return "JavaScript".into(),
            "c" | "h" | "cpp" | "hpp" => return "C/C++".into(),
            "cob" | "cbl" => return "COBOL".into(),
            "sol" => return "Solidity".into(),
            "fr" | "frontier" => return "Frontier".into(),
            _ => {}
        }
    }
    "Unknown".into()
}

fn walk_files(dir: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    if !dir.is_dir() {
        return out;
    }
    let Ok(read) = fs::read_dir(dir) else {
        return out;
    };
    for entry in read.flatten() {
        let path = entry.path();
        if path.is_dir() {
            out.extend(walk_files(&path));
        } else {
            out.push(path);
        }
    }
    out
}

pub fn migrate_project(input: &Path, output: &Path) -> Result<MigrationReport, FrontierError> {
    let language = detect_language(input);
    fs::create_dir_all(output)?;

    let files = walk_files(input);
    let mut migrated = 0usize;
    let mut manual = 0usize;

    for file in &files {
        let rel = file.strip_prefix(input).unwrap_or(file);
        let ext = file
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        match ext.as_str() {
            "py" => {
                let source = fs::read_to_string(file)?;
                let frontier = translate_python(&source);
                let out_path = output.join(rel.with_extension("frontier"));
                if let Some(parent) = out_path.parent() {
                    fs::create_dir_all(parent)?;
                }
                fs::write(&out_path, frontier)?;
                migrated += 1;
            }
            "fr" | "frontier" => {
                let out_path = output.join(rel);
                if let Some(parent) = out_path.parent() {
                    fs::create_dir_all(parent)?;
                }
                fs::copy(file, &out_path)?;
                migrated += 1;
            }
            "md" | "txt" | "json" | "toml" | "yaml" | "yml" => {
                let out_path = output.join(rel);
                if let Some(parent) = out_path.parent() {
                    fs::create_dir_all(parent)?;
                }
                fs::copy(file, &out_path)?;
                migrated += 1;
            }
            _ => {
                manual += 1;
            }
        }
    }

    if migrated == 0 && language == "Python" {
        let main_py = input.join("main.py");
        if main_py.exists() {
            let source = fs::read_to_string(&main_py)?;
            let frontier = translate_python(&source);
            let out_path = output.join("main.frontier");
            fs::write(&out_path, frontier)?;
            migrated += 1;
        }
    }

    let report_path = output.join("MIGRATION_REPORT.json");
    let report_json = serde_json::json!({
        "source_language": language,
        "files_scanned": files.len(),
        "files_migrated": migrated,
        "files_manual": manual,
        "auto_migration_rate": if files.is_empty() {
            0.0
        } else {
            (migrated as f64 / files.len() as f64) * 100.0
        },
    });
    fs::write(report_path, serde_json::to_string_pretty(&report_json).unwrap())?;

    Ok(MigrationReport {
        source_language: language,
        files_scanned: files.len(),
        files_migrated: migrated,
        files_manual: manual,
        output_dir: output.to_path_buf(),
    })
}

fn translate_python(source: &str) -> String {
    let mut out = String::from("version: 2.0;\n\n");
    let mut in_fn = false;
    let mut in_main = false;

    for line in source.lines() {
        let trimmed = line.trim();

        if trimmed.starts_with("def ") {
            if in_fn {
                out.push_str("}\n\n");
                in_fn = false;
            }
            if let Some(rest) = trimmed.strip_prefix("def ") {
                if let Some((sig, _)) = rest.split_once(':') {
                    let name = sig.split('(').next().unwrap_or("unnamed").trim();
                    if name == "main" {
                        out.push_str("fn main(): void {\n");
                        in_main = true;
                        continue;
                    }
                    let params_raw = sig
                        .split('(')
                        .nth(1)
                        .unwrap_or("")
                        .trim_end_matches(')')
                        .trim();
                    let params = if params_raw.is_empty() {
                        String::new()
                    } else {
                        params_raw
                            .split(',')
                            .map(|p| {
                                let name = p.trim();
                                format!("{name}: int")
                            })
                            .collect::<Vec<_>>()
                            .join(", ")
                    };
                    out.push_str(&format!("fn {name}({params}) -> int {{\n"));
                    in_fn = true;
                    continue;
                }
            }
        }

        if trimmed.starts_with("return ") {
            let expr = trimmed.strip_prefix("return ").unwrap_or("0").trim();
            out.push_str(&format!("    return {expr};\n"));
            out.push_str("}\n\n");
            in_fn = false;
            continue;
        }

        if trimmed.starts_with("if __name__") {
            if in_fn {
                out.push_str("}\n\n");
                in_fn = false;
            }
            if !in_main {
                out.push_str("fn main(): void {\n");
                in_main = true;
            }
            continue;
        }

        if trimmed.starts_with("print(") {
            continue;
        }

        if trimmed.contains('=') && !trimmed.starts_with('#') && (in_main || in_fn) {
            let stmt = trimmed.trim_end_matches(':');
            let parts: Vec<&str> = stmt.splitn(2, '=').collect();
            if parts.len() == 2 {
                let lhs = parts[0].trim().trim_start_matches("let ");
                let rhs = parts[1].trim();
                out.push_str(&format!("    let {lhs}: int = {rhs};\n"));
                continue;
            }
        }

        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
    }

    if in_fn {
        out.push_str("}\n\n");
    }
    if in_main {
        out.push_str("}\n");
    } else if !out.contains("fn main") {
        out.push_str("\nfn main(): void {\n}\n");
    }

    out
}

pub fn verify_migrated_project(input: &Path) -> Result<serde_json::Value, FrontierError> {
    let files = walk_files(input);
    let frontier_files: Vec<_> = files
        .iter()
        .filter(|p| {
            matches!(
                p.extension().and_then(|e| e.to_str()),
                Some("frontier") | Some("fr")
            )
        })
        .collect();

    let mut verified = 0usize;
    let mut errors = Vec::new();

    for file in &frontier_files {
        let _source = fs::read_to_string(file)?;
        let path_str = file.to_string_lossy();
        match crate::parser::parse_file(&path_str) {
            Ok(ast) => {
                let json = serde_json::to_string(&ast).unwrap_or_default();
                if let Ok(result) = crate::process_v2_ast(&json) {
                    verified += 1;
                    let _ = result;
                } else {
                    errors.push(format!("{}: v2 pipeline failed", file.display()));
                }
            }
            Err(e) => errors.push(format!("{}: {e}", file.display())),
        }
    }

    Ok(serde_json::json!({
        "status": if errors.is_empty() { "verified" } else { "partial" },
        "frontier_files": frontier_files.len(),
        "verified": verified,
        "errors": errors,
    }))
}

pub fn run_frontier_file(path: &Path) -> Result<String, FrontierError> {
    let path_str = path.to_string_lossy();
    let ast = crate::parser::parse_file(&path_str).map_err(FrontierError::internal)?;
    let json = serde_json::to_string(&ast).map_err(|e| FrontierError::internal(e.to_string()))?;
    let processed = crate::process_v2_ast(&json).map_err(FrontierError::internal)?;
    Ok(format!(
        "✅ Executed {} — status: {}",
        path.display(),
        processed["status"]
    ))
}
