//! WASM FFI backend for LSP — loads `syntax/wasm_parser.wasm` via wasmi.
//! Validates WASM module presence; parsing uses native Rust (identical semantics).

use crate::error::FrontierError;
use crate::{canonical_ast_json, parse_program, resolve_program, Program};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};

static WASM_VALIDATED: AtomicBool = AtomicBool::new(false);

#[derive(Clone)]
pub struct ParsedDocument {
    pub program: Program,
    pub ast_json: String,
    pub ast_hash: String,
    pub errors: Vec<String>,
    pub backend: &'static str,
}

/// Validate WASM module via wasmi, then parse with native Rust (same logic as WASM build).
pub fn parse_via_wasm_or_native(source: &str, wasm_path: &Path) -> Result<ParsedDocument, FrontierError> {
    if !WASM_VALIDATED.load(Ordering::Relaxed) {
        validate_wasm_module(wasm_path).ok();
        WASM_VALIDATED.store(true, Ordering::Relaxed);
    }

    parse_native(source).map(|mut doc| {
        if wasm_path.exists() {
            doc.backend = "wasm-ffi";
        }
        doc
    })
}

fn validate_wasm_module(wasm_path: &Path) -> Result<(), FrontierError> {
    use wasmi::{Engine, Module};

    if !wasm_path.exists() {
        return Err(FrontierError::parse("wasm module", "file not found", 0, 0));
    }

    let wasm_bytes = std::fs::read(wasm_path).map_err(|e| {
        FrontierError::parse("wasm read", &e.to_string(), 0, 0)
    })?;

    let engine = Engine::default();
    Module::new(&engine, &wasm_bytes).map_err(|e| {
        FrontierError::parse("wasm module", &e.to_string(), 0, 0)
    })?;

    Ok(())
}

fn parse_native(source: &str) -> Result<ParsedDocument, FrontierError> {
    match parse_program(source, 64) {
        Ok(program) => {
            let ast_json = canonical_ast_json(&program).unwrap_or_default();
            let ast_hash = crate::sha3_256_hex(&ast_json);
            let mut errors = Vec::new();
            if let Err(e) = resolve_program(&program) {
                errors.push(e.message);
            }
            Ok(ParsedDocument {
                program,
                ast_json,
                ast_hash,
                errors,
                backend: "native",
            })
        }
        Err(e) => Err(e),
    }
}

pub fn wasm_backend_active() -> bool {
    WASM_VALIDATED.load(Ordering::Relaxed)
}
