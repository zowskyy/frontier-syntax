//! Minimal wasm-bindgen surface for wasm-slim builds (<100 KB target).

use wasm_bindgen::prelude::*;

use crate::browser_compiler;

#[wasm_bindgen]
pub fn compile_frontier_wasm(source: &str) -> Result<Vec<u8>, JsValue> {
    browser_compiler::compile_to_wasm(source, true).map_err(|e| JsValue::from_str(&e))
}
