//! WASM-bindgen exports for in-browser Frontier compilation.

use wasm_bindgen::prelude::*;

use crate::browser_compiler::{self, CompileOptions, CompileResult, ValidateResult};

#[wasm_bindgen]
pub struct BrowserCompiler {
    optimize: bool,
}

#[wasm_bindgen]
impl BrowserCompiler {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Self {
        Self { optimize: true }
    }

    #[wasm_bindgen]
    pub fn set_optimize(&mut self, enabled: bool) {
        self.optimize = enabled;
    }

    #[wasm_bindgen]
    pub fn compile(&self, source: &str) -> Result<JsValue, JsValue> {
        let options = CompileOptions {
            optimize: self.optimize,
            browser_compat: true,
            profile: false,
        };
        let result = browser_compiler::compile(source, &options)
            .map_err(|e| JsValue::from_str(&e))?;
        to_js(&result)
    }

    #[wasm_bindgen]
    pub fn compile_to_wasm(&self, source: &str) -> Result<Vec<u8>, JsValue> {
        browser_compiler::compile_to_wasm(source, self.optimize)
            .map_err(|e| JsValue::from_str(&e))
    }

    #[wasm_bindgen]
    pub fn validate(&self, source: &str) -> Result<JsValue, JsValue> {
        let result = browser_compiler::validate(source);
        to_js(&result)
    }

    #[wasm_bindgen]
    pub fn get_algorithm_suggestion(&self, operation: &str, data_type: &str) -> Result<JsValue, JsValue> {
        let suggestion = browser_compiler::algorithm_suggestion(operation, data_type);
        to_js(&suggestion)
    }

    #[wasm_bindgen]
    pub fn get_ancestors(&self, operation: &str) -> Result<JsValue, JsValue> {
        let ancestors = browser_compiler::ancestors(operation);
        to_js(&ancestors)
    }
}

#[wasm_bindgen]
pub fn compile_frontier(source: &str) -> Result<JsValue, JsValue> {
    BrowserCompiler::new().compile(source)
}

#[wasm_bindgen]
pub fn compile_frontier_wasm(source: &str) -> Result<Vec<u8>, JsValue> {
    BrowserCompiler::new().compile_to_wasm(source)
}

#[wasm_bindgen]
pub fn validate_frontier(source: &str) -> Result<JsValue, JsValue> {
    BrowserCompiler::new().validate(source)
}

fn to_js<T: serde::Serialize>(value: &T) -> Result<JsValue, JsValue> {
    serde_wasm_bindgen::to_value(value).map_err(|e| JsValue::from_str(&e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_native_path() {
        let result = browser_compiler::validate("fn main(): int { return 1; }");
        assert!(result.valid);
    }
}
