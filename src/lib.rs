pub mod ast;
pub mod canonicalize;
pub mod codegen;
pub mod docs;
pub mod error;
pub mod interpreter;
pub mod lexer;
pub mod lsp;
pub mod package;
pub mod parser;
pub mod prover;
pub mod repl;
pub mod resolver;

pub use ast::Program;
pub use canonicalize::{canonical_ast_json, sha3_256_hex};
pub use codegen::{compile_to_object, generate_module};
pub use docs::generate_docs;
pub use error::FrontierError;
pub use interpreter::{Interpreter, Value};
pub use package::{add_package, PackageManifest, PackageResolver};
pub use parser::parse_program;
pub use prover::generate_coq;
pub use repl::run_repl;
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
