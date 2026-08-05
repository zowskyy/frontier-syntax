//! Frontier v2.0 parser — hand-written Rust implementation
//! aligned with `syntax/Frontier.g4` (ANTLR v4.13.1 grammar specification).
//!
//! The ANTLR grammar at `syntax/Frontier.g4` is the canonical specification.
//! This module implements that grammar in Rust for production parsing.

pub mod handwritten;

pub use handwritten::parse_program;
use crate::ast::Program;
use crate::error::FrontierError;
use serde_json::Value;
use std::fs;
use std::path::Path;

/// Parse Frontier v2.0 source into a JSON AST value.
pub fn parse_source(source: &str) -> Result<Value, String> {
    let program = parse_program(source, 64).map_err(|e| e.message)?;
    serde_json::to_value(&program).map_err(|e| e.to_string())
}

/// Parse a `.fr` source file into JSON AST.
pub fn parse_file(path: &str) -> Result<Value, String> {
    let source = fs::read_to_string(path)
        .map_err(|e| format!("Failed to read file: {e}"))?;
    parse_source(&source)
}

/// Parse and return typed AST.
pub fn parse_source_typed(source: &str) -> Result<Program, FrontierError> {
    parse_program(source, 64)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_v2_sample_parse() {
        let source = include_str!("../../examples/v2_parser_test.fr");
        let ast = parse_source(source).expect("v2 sample should parse");
        assert_eq!(ast.get("version").and_then(|v| v.as_str()), Some("2.0"));
    }
}
