pub mod ast;
pub mod canonicalize;
pub mod error;
pub mod lexer;
pub mod parser;
pub mod resolver;

pub use ast::Program;
pub use canonicalize::{canonical_ast_json, sha3_256_hex};
pub use error::FrontierError;
pub use parser::parse_program;
pub use resolver::resolve_program;

const MAX_NESTING_DEPTH: usize = 64;

use unicode_normalization::UnicodeNormalization;

pub fn parse_and_resolve(source: &str) -> Result<(Program, resolver::ResolveResult), FrontierError> {
    let normalized: String = source.nfc().collect();
    let program = parse_program(&normalized, MAX_NESTING_DEPTH)?;
    let resolved = resolve_program(&program)?;
    Ok((program, resolved))
}

#[cfg(target_arch = "wasm32")]
mod wasm;
