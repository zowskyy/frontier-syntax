pub mod ast;
pub mod browser_compiler;
pub mod canonicalize;
pub mod compiler;
pub mod error;
pub mod grammar;
#[cfg(not(target_arch = "wasm32"))]
pub mod ipfs;
pub mod knowledge;
pub mod knowledge_bridge;
pub mod lexer;
pub mod lsp;
pub mod migrate;
pub mod neural;
pub mod packages;
pub mod parser;
#[cfg(not(target_arch = "wasm32"))]
pub mod pq_signatures;
pub mod resolver;
pub mod v2_resolver;
pub mod unity;
pub mod wasm_codegen;
#[cfg(not(target_arch = "wasm32"))]
pub mod zk;

pub use ast::Program;
pub use canonicalize::{canonical_ast_json, sha3_256_hex};
pub use error::FrontierError;
pub use parser::parse_program;
pub use resolver::resolve_program;
pub use knowledge::{get_ancestors, get_tradeoffs, hypercube_stats, optimize_hash, optimize_sort};
pub use knowledge::solver::{SizeHint, SolverContext as KnowledgeContext};
pub use unity::{unity_compile, unity_evaluate, unity_verify, UnityCompiler, UnityModule};

const MAX_NESTING_DEPTH: usize = 64;

use unicode_normalization::UnicodeNormalization;

pub fn parse_and_resolve(source: &str) -> Result<(Program, resolver::ResolveResult), FrontierError> {
    let normalized: String = source.nfc().collect();
    let program = parse_program(&normalized, MAX_NESTING_DEPTH)?;
    let resolved = resolve_program(&program)?;
    Ok((program, resolved))
}

pub fn process_v2_ast(ast_json: &str) -> Result<serde_json::Value, String> {
    let ast: serde_json::Value =
        serde_json::from_str(ast_json).map_err(|e| format!("Invalid AST JSON: {e}"))?;

    #[cfg(not(target_arch = "wasm32"))]
    let imports_resolved = {
        let mut ipfs = ipfs::resolver::IpfsImportResolver::new();
        ipfs.resolve_ast(&ast).map_err(|e| e.join("; "))?;
        serde_json::json!(ipfs.imports())
    };

    #[cfg(target_arch = "wasm32")]
    let imports_resolved = serde_json::json!([]);

    let mut resolver = v2_resolver::V2Resolver::new();
    let resolved = resolver
        .resolve(&ast)
        .map_err(|e| e.join("; "))?;

    let proof_gen = compiler::proof_generator::ProofGenerator::new();
    let obligations = proof_gen.collect_proof_obligations(&ast);

    #[cfg(not(target_arch = "wasm32"))]
    {
        let mut verifier = zk::verifier::ZkVerifier::new();
        verifier.setup()?;
        let proof = verifier.generate_proof_json(&ast)?;
        Ok(serde_json::json!({
            "status": "processed",
            "imports": imports_resolved,
            "resolution": resolved,
            "proof_obligations": obligations,
            "zk_proof": proof,
        }))
    }

    #[cfg(target_arch = "wasm32")]
    {
        Ok(serde_json::json!({
            "status": "processed",
            "imports": imports_resolved,
            "resolution": resolved,
            "proof_obligations": obligations,
            "zk_proof": null,
        }))
    }
}

#[cfg(target_arch = "wasm32")]
mod wasm;

#[cfg(target_arch = "wasm32")]
pub mod browser_wasm;

#[cfg(test)]
mod integration_tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_v2_pipeline() {
        let ast_json = fs::read_to_string("syntax/ast_sample_v2.json").expect("sample v2 ast");
        let result = process_v2_ast(&ast_json).expect("v2 pipeline");
        assert_eq!(result["status"], "processed");
    }
}
