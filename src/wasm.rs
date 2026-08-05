use unicode_normalization::UnicodeNormalization;
use wasm_bindgen::prelude::*;
use crate::{canonical_ast_json, parse_program, resolve_program, sha3_256_hex};

#[wasm_bindgen]
pub struct WasmParseResult {
    ast_json: String,
    ast_hash: String,
    errors: String,
}

#[wasm_bindgen]
impl WasmParseResult {
    #[wasm_bindgen(getter)]
    pub fn ast_json(&self) -> String {
        self.ast_json.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn ast_hash(&self) -> String {
        self.ast_hash.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn errors(&self) -> String {
        self.errors.clone()
    }
}

#[wasm_bindgen]
pub fn parse_source(source: &str) -> WasmParseResult {
    let normalized: String = source.nfc().collect();

    match parse_program(&normalized, 64) {
        Ok(program) => {
            let ast_json = canonical_ast_json(&program).unwrap_or_else(|e| {
                format!(r#"{{"error":"{}"}}"#, e)
            });
            let ast_hash = sha3_256_hex(&ast_json);
            let _ = resolve_program(&program);
            WasmParseResult {
                ast_json,
                ast_hash,
                errors: "[]".to_string(),
            }
        }
        Err(e) => WasmParseResult {
            ast_json: "null".to_string(),
            ast_hash: String::new(),
            errors: serde_json::to_string(&vec![e.message]).unwrap_or_else(|_| "[]".to_string()),
        },
    }
}

#[wasm_bindgen]
pub fn parse_source_with_resolve(source: &str) -> WasmParseResult {
    let normalized: String = source.nfc().collect();

    match parse_program(&normalized, 64) {
        Ok(program) => {
            let ast_json = canonical_ast_json(&program).unwrap_or_default();
            let ast_hash = sha3_256_hex(&ast_json);
            let errors = match resolve_program(&program) {
                Ok(_) => "[]".to_string(),
                Err(e) => serde_json::to_string(&vec![e.message]).unwrap_or_else(|_| "[]".to_string()),
            };
            WasmParseResult {
                ast_json,
                ast_hash,
                errors,
            }
        }
        Err(e) => WasmParseResult {
            ast_json: "null".to_string(),
            ast_hash: String::new(),
            errors: serde_json::to_string(&vec![e.message]).unwrap_or_else(|_| "[]".to_string()),
        },
    }
}
