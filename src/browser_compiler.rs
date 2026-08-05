//! Browser compiler — compile Frontier source to WASM + optional JS glue.

use crate::canonicalize::{canonical_ast_json, sha3_256_hex};
use crate::knowledge_bridge::{get_ancestors_json, get_optimal_algorithm, get_tradeoffs_json};
use crate::knowledge::SizeHint;
use crate::parser;
use crate::wasm_codegen::{compile_source, CodeGenOptions, CompilationProfile};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
pub struct CompileOptions {
    pub optimize: bool,
    pub browser_compat: bool,
    pub profile: bool,
}

impl Default for CompileOptions {
    fn default() -> Self {
        Self {
            optimize: true,
            browser_compat: false,
            profile: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompileResult {
    pub success: bool,
    pub wasm: Vec<u8>,
    pub js_glue: Option<String>,
    pub exports: Vec<String>,
    pub imports: Vec<String>,
    pub memory_pages: u32,
    pub warnings: Vec<String>,
    pub ast_hash: String,
    pub selected_algorithm: Option<String>,
    pub profile: Option<CompilationProfile>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidateResult {
    pub valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
    pub ast_hash: String,
}

pub fn compile(source: &str, options: &CompileOptions) -> Result<CompileResult, String> {
    let codegen_opts = CodeGenOptions {
        optimize: options.optimize,
        browser_exports: options.browser_compat,
        collect_profile: options.profile,
    };

    let (wasm, meta) = compile_source(source, &codegen_opts)?;
    let ast_hash = compute_ast_hash(source)?;

    let js_glue = if options.browser_compat {
        Some(generate_js_glue(&meta.exports))
    } else {
        None
    };

    Ok(CompileResult {
        success: true,
        wasm,
        js_glue,
        exports: meta.exports,
        imports: default_browser_imports(),
        memory_pages: 1,
        warnings: meta.warnings,
        ast_hash,
        selected_algorithm: meta.selected_algorithm,
        profile: meta.profile,
    })
}

pub fn compile_to_wasm(source: &str, optimize: bool) -> Result<Vec<u8>, String> {
    let options = CompileOptions {
        optimize,
        browser_compat: false,
        profile: false,
    };
    Ok(compile(source, &options)?.wasm)
}

pub fn validate(source: &str) -> ValidateResult {
    match parser::parse_source_typed(source) {
        Ok(program) => {
            let json = canonical_ast_json(&program).unwrap_or_default();
            ValidateResult {
                valid: true,
                errors: vec![],
                warnings: vec![],
                ast_hash: sha3_256_hex(&json),
            }
        }
        Err(e) => ValidateResult {
            valid: false,
            errors: vec![e.message],
            warnings: vec![],
            ast_hash: String::new(),
        },
    }
}

pub fn algorithm_suggestion(operation: &str, data_type: &str) -> crate::knowledge_bridge::AlgorithmSuggestion {
    get_optimal_algorithm(operation, data_type, SizeHint::Medium)
}

pub fn ancestors(operation: &str) -> Vec<(String, u16)> {
    get_ancestors_json(operation)
}

pub fn tradeoffs(operation: &str) -> Option<crate::knowledge_bridge::TradeoffEntry> {
    get_tradeoffs_json(operation)
}

fn compute_ast_hash(source: &str) -> Result<String, String> {
    let program = parser::parse_source_typed(source).map_err(|e| e.to_string())?;
    let json = canonical_ast_json(&program).map_err(|e| e.to_string())?;
    Ok(sha3_256_hex(&json))
}

fn default_browser_imports() -> Vec<String> {
    vec![
        "env.memory".to_string(),
        "env.console_log".to_string(),
    ]
}

pub fn generate_js_glue(exports: &[String]) -> String {
    let export_list: Vec<String> = exports
        .iter()
        .map(|e| format!("    {e}: instance.exports.{e},"))
        .collect();

    format!(
        r#"// Frontier Browser Runtime — auto-generated
export async function instantiate(wasmBytes) {{
  const memory = new WebAssembly.Memory({{ initial: 1, maximum: 64 }});
  const imports = {{
    env: {{
      memory,
      console_log: (ptr, len) => {{
        const bytes = new Uint8Array(memory.buffer, ptr, len);
        console.log(new TextDecoder().decode(bytes));
      }},
    }},
  }};
  const {{ instance }} = await WebAssembly.instantiate(wasmBytes, imports);
  return {{
    memory,
    instance,
    exports: {{
{exports}
    }},
  }};
}}

export function readString(memory, ptr, len) {{
  return new TextDecoder().decode(new Uint8Array(memory.buffer, ptr, len));
}}

export function writeString(memory, str) {{
  const bytes = new TextEncoder().encode(str);
  const pageSize = 65536;
  const needed = bytes.length + 1;
  if (needed > pageSize) memory.grow(Math.ceil(needed / pageSize));
  const ptr = 0;
  new Uint8Array(memory.buffer, ptr, bytes.length).set(bytes);
  return ptr;
}}
"#,
        exports = export_list.join("\n")
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_browser_compile() {
        let source = "fn main(): int { return 99; }";
        let result = compile(
            source,
            &CompileOptions {
                optimize: true,
                browser_compat: true,
                profile: false,
            },
        )
        .expect("compile");
        assert!(result.success);
        assert!(result.js_glue.is_some());
        assert!(result.wasm.starts_with(b"\0asm"));
    }

    #[test]
    fn test_validate_ok() {
        let result = validate("fn main(): void {}");
        assert!(result.valid);
    }
}
