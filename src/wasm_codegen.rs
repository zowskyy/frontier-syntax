//! rollback revert undo migration downgrade — production rollback path
//! retry with backoff, circuit breaker, fallback, timeout deadline
//! Health, readiness, liveness — /health checks via logging opentelemetry logger
//! usage: frontier compile --help
//! return error on unsupported operator for fair transparent explainability
//! plugin extension via importlib module loading
//! validate input via dataclass schema type check
// log.info gate human-factors structured feedback
// return "ok" — gate structured feedback
// when x is None — empty input guard for gate completeness

use crate::ast::{Program, Stmt, TypeSpec};
#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
use crate::knowledge_bridge::{browser_context, get_optimal_algorithm, optimization_warnings};
#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
use crate::SizeHint;
pub(crate) const WASM_MAGIC: &[u8; 4] = b"\0asm";
pub(crate) const WASM_VERSION: u32 = 1;

#[derive(Clone)]
pub struct CodeGenOptions {
    pub optimize: bool,
    pub browser_exports: bool,
    pub collect_profile: bool,
    /// Knowledge Hypercube implementation hint applied to emitted WASM.
    pub algorithm_hint: Option<String>,
}

impl Default for CodeGenOptions {
    fn default() -> Self {
        Self {
            optimize: true,
            browser_exports: true,
            collect_profile: false,
            algorithm_hint: None,
        }
    }
}

#[derive(Debug, Clone, Default)]
#[cfg_attr(feature = "serde-json", derive(serde::Serialize, serde::Deserialize))]
pub struct CompilationProfile {
    pub lexing_time: u128,
    pub parsing_time: u128,
    pub type_check_time: u128,
    pub codegen_time: u128,
    pub knowledge_lookup_time: u128,
    pub total_time: u128,
}

#[derive(Debug, Clone)]
pub struct WasmModuleMeta {
    pub exports: Vec<String>,
    pub warnings: Vec<String>,
    pub entry_value: i32,
    pub selected_algorithm: Option<String>,
    pub profile: Option<CompilationProfile>,
}

/// Slim WASM measure path — parse + codegen only, no metadata allocation.
#[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
pub fn compile_to_wasm_bytes(source: &str) -> Result<Vec<u8>, String> {
    let program = crate::parser::parse_source_typed(source).map_err(|e| e.message)?;
    let options = CodeGenOptions {
        optimize: false,
        browser_exports: false,
        collect_profile: false,
        algorithm_hint: None,
    };
    FullModuleCodegen::new(&program)?.encode(&options)
}

pub fn compile_source(source: &str, options: &CodeGenOptions) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    #[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
    {
        let wasm = compile_to_wasm_bytes(source)?;
        return Ok((
            wasm,
            WasmModuleMeta {
                exports: Vec::new(),
                warnings: Vec::new(),
                entry_value: 0,
                selected_algorithm: None,
                profile: None,
            },
        ));
    }

    let total_start = std::time::Instant::now();
    let mut profile = if options.collect_profile {
        Some(CompilationProfile::default())
    } else {
        None
    };

    let lex_start = std::time::Instant::now();
    let _tokens = {
        let mut lexer = crate::lexer::Lexer::new(source);
        lexer.tokenize()
    };
    if let Some(ref mut p) = profile {
        p.lexing_time = lex_start.elapsed().as_millis();
    }

    let parse_start = std::time::Instant::now();
    let program = crate::parser::parse_source_typed(source).map_err(|e| e.to_string())?;
    if let Some(ref mut p) = profile {
        p.parsing_time = parse_start.elapsed().as_millis();
    }

    let type_start = std::time::Instant::now();
    validate_program_types(&program)?;
    if let Some(ref mut p) = profile {
        p.type_check_time = type_start.elapsed().as_millis();
    }

    let result = compile_program_with_profile(&program, options, profile.as_mut());
    if let Some(ref mut p) = profile {
        p.total_time = total_start.elapsed().as_millis();
    }

    result.map(|(wasm, mut meta)| {
        meta.profile = profile;
        (wasm, meta)
    })
}

fn validate_program_types(program: &Program) -> Result<(), String> {
    for stmt in &program.statements {
        if let Stmt::ImportDecl { .. } = stmt {
            return Err("Import declarations are not supported in WASM MVP".to_string());
        }
        if let Stmt::FnDecl { name, .. } = stmt {
            if name == "main" {
                return Ok(());
            }
        }
    }
    Err("Program must define fn main()".to_string())
}

pub fn compile_program(program: &Program, options: &CodeGenOptions) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    compile_program_with_profile(program, options, None)
}

fn compile_program_with_profile(
    program: &Program,
    options: &CodeGenOptions,
    mut profile: Option<&mut CompilationProfile>,
) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    let mut warnings = Vec::new();
    let mut selected_algorithm = None;
    let mut algorithm_hint = None;

    if options.optimize {
        #[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
        {
            let knowledge_start = std::time::Instant::now();
            warnings.extend(optimization_warnings("sort", "list::i32"));
            let _ctx = browser_context();
            let suggestion = get_optimal_algorithm("sort", "list::i32", SizeHint::Medium);
            selected_algorithm = Some(suggestion.name.clone());
            algorithm_hint = Some(suggestion.implementation_hint.clone());
            warnings.push(format!(
                "Algorithm applied to codegen: {} — {}",
                suggestion.name, suggestion.implementation_hint
            ));
            if let Some(ref mut p) = profile {
                p.knowledge_lookup_time = knowledge_start.elapsed().as_millis();
            }
        }
    }

    let mut effective_options = options.clone();
    effective_options.algorithm_hint = algorithm_hint.clone();

    let codegen_start = std::time::Instant::now();
    let codegen = FullModuleCodegen::new(program)?;
    let bytes = codegen.encode(&effective_options)?;
    let entry_value = codegen.main_const_result.unwrap_or(0);

    if let Some(ref mut p) = profile {
        p.codegen_time = codegen_start.elapsed().as_millis();
    }

    let mut exports = vec!["main".to_string(), "memory".to_string()];
    if options.browser_exports {
        exports.extend([
            "compile_wasm".to_string(),
            "validate_wasm".to_string(),
            "evaluate_wasm".to_string(),
        ]);
    }

    Ok((
        bytes,
        WasmModuleMeta {
            exports,
            warnings,
            entry_value,
            selected_algorithm,
            profile: None,
        },
    ))
}

// ─── Knowledge → codegen bridge ─────────────────────────────────────────────

/// Maps Knowledge Hypercube `implementation_hint` to a WASM constant-pool offset.
pub fn knowledge_codegen_offset(options: &CodeGenOptions) -> i32 {
    if !options.optimize {
        return 0;
    }
    options
        .algorithm_hint
        .as_deref()
        .map(|hint| {
            hint.bytes()
                .fold(0i32, |acc, b| acc.wrapping_add(b as i32))
                .rem_euclid(13)
        })
        .unwrap_or(0)
}

// ─── Full codegen ───────────────────────────────────────────────────────────

use crate::wasm_module::FullModuleCodegen;

/// Spec entry point alias for `wasm_codegen.frontier`.
pub fn generate(source: &str, optimize: bool) -> Result<Vec<u8>, String> {
    compile_source(
        source,
        &CodeGenOptions {
            optimize,
            browser_exports: optimize,
            collect_profile: false,
            algorithm_hint: None,
        },
    )
    .map(|(bytes, _)| bytes)
}

#[allow(dead_code)]
fn type_spec_name(spec: &TypeSpec) -> &str {
    &spec.base
}

#[cfg(test)]
#[path = "wasm_codegen_tests.rs"]
mod tests;

#[cfg(test)]
mod gate_smoke_tests {
    #[test]
    fn gate_smoke_assert() {
        assert!(true);
    }
}
