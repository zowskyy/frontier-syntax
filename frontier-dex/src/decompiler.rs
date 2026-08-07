use crate::ast::PatternMatcher;
use crate::cache::DexCache;
use crate::engines::EngineOrchestrator;
use crate::ir::Disassembler;
use crate::neural::ObfuscationPredictor;
use crate::optimizer::{AstOptimizer, FixedPointOptimizer};
use crate::parser::{parse_dex, DexFile};
use crate::pretty::JavaPrettyPrinter;
use crate::verifier::ProofVerifier;
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DecompileOptions {
    pub generate_proof: bool,
    pub neural: bool,
    pub cache: bool,
    pub fallback_engines: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecompileResult {
    pub java_sources: Vec<JavaClassOutput>,
    pub proof_hash: Option<String>,
    pub cache_key: Option<String>,
    pub obfuscation_score: f32,
    pub engine_used: String,
    pub iterations: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JavaClassOutput {
    pub class_name: String,
    pub source: String,
}

pub struct Decompiler {
    pub options: DecompileOptions,
    cache: DexCache,
    orchestrator: EngineOrchestrator,
    predictor: ObfuscationPredictor,
    verifier: ProofVerifier,
}

impl Default for Decompiler {
    fn default() -> Self {
        Self::new(DecompileOptions::default())
    }
}

impl Decompiler {
    pub fn new(options: DecompileOptions) -> Self {
        Self {
            options,
            cache: DexCache::default(),
            orchestrator: EngineOrchestrator::new(),
            predictor: ObfuscationPredictor::new(),
            verifier: ProofVerifier::new(),
        }
    }

    pub fn decompile_bytes(&mut self, bytes: &[u8]) -> Result<DecompileResult, String> {
        if self.options.cache {
            let key = DexCache::content_key(bytes);
            if let Some(cached) = self.cache.get(&key) {
                return Ok(cached);
            }
        }

        let dex = parse_dex(bytes).map_err(|e| e.to_string())?;
        self.decompile_dex(&dex, bytes)
    }

    pub fn decompile_file<P: AsRef<Path>>(&mut self, path: P) -> Result<DecompileResult, String> {
        let bytes = std::fs::read(path.as_ref()).map_err(|e| e.to_string())?;
        self.decompile_bytes(&bytes)
    }

    pub fn decompile_with_proof(&mut self, dex_path: &str) -> Result<DecompileResult, String> {
        self.options.generate_proof = true;
        self.decompile_file(dex_path)
    }

    fn decompile_dex(&mut self, dex: &DexFile, bytes: &[u8]) -> Result<DecompileResult, String> {
        let _functions = Disassembler::disassemble_all(dex);
        let mut java_sources = Vec::new();
        let mut total_iters = 0usize;
        let pp = JavaPrettyPrinter::default();

        for class in &dex.classes {
            let mut method_asts = Vec::new();
            for method in &class.methods {
                if let Some(func) = Disassembler::disassemble_method(&class.class_name, method) {
                    let ast = PatternMatcher::match_ir_to_ast(&func);
                    let opt = FixedPointOptimizer::default();
                    let (_, ast, iters) = opt.run_until_fixed_point(func, ast);
                    total_iters += iters;
                    let mut ast = AstOptimizer::rewrite_ast(ast);
                    if self.options.neural {
                        ast = self.predictor.enhance(ast);
                    }
                    method_asts.push(ast);
                }
            }
            if !method_asts.is_empty() {
                java_sources.push(JavaClassOutput {
                    class_name: class.class_name.clone(),
                    source: pp.print_class(&class.class_name, &method_asts),
                });
            }
        }

        if java_sources.is_empty() && self.options.fallback_engines {
            if let Some(fallback) = self.orchestrator.try_fallback(bytes) {
                java_sources.push(JavaClassOutput {
                    class_name: "Fallback".into(),
                    source: fallback,
                });
            }
        }

        let obfuscation_score = if self.options.neural {
            self.predictor.score_dex(dex)
        } else {
            0.0
        };

        let proof_hash = if self.options.generate_proof {
            let hash = self
                .verifier
                .decompile_with_proof(bytes, &java_sources)
                .map_err(|e| e.to_string())?;
            Some(hash)
        } else {
            None
        };

        let engine_used = if self.options.fallback_engines && java_sources.iter().any(|j| j.class_name == "Fallback") {
            self.orchestrator.last_engine().to_string()
        } else {
            "frontier-dex".into()
        };

        let result = DecompileResult {
            java_sources,
            proof_hash,
            cache_key: None,
            obfuscation_score,
            engine_used,
            iterations: total_iters,
        };

        if self.options.cache {
            let key = DexCache::content_key(bytes);
            let mut cached = result.clone();
            cached.cache_key = Some(key.clone());
            self.cache.put(&key, &cached);
        }

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decompile_minimal() {
        let mut dex = vec![0u8; 512];
        dex[0..8].copy_from_slice(b"dex\n035\0");
        dex[32] = 0x00; dex[33] = 0x02; // file_size 512
        dex[36] = 0x70;
        dex[40] = 0x78; dex[41] = 0x56; dex[42] = 0x34; dex[43] = 0x12;
        dex[52] = 0x70;
        dex[112] = 1;
        dex[116] = 0; dex[117] = 0;
        dex[120] = 1;
        let mut dec = Decompiler::default();
        let result = dec.decompile_bytes(&dex).expect("decompile");
        assert!(result.iterations >= 0);
    }
}
