//! Minimal wasm-bindgen surface for wasm-slim builds (<100 KB target).

use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn compile_frontier_wasm(source: &str) -> Result<Vec<u8>, JsValue> {
    crate::wasm_codegen::compile_to_wasm_bytes(source)
        .map_err(|e| JsValue::from_str(&e))
}
