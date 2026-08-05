use crate::decompiler::JavaClassOutput;
use serde::{Deserialize, Serialize};
use sha3::{Digest, Sha3_256};

fn sha3_hex(data: &[u8]) -> String {
    let mut hasher = Sha3_256::new();
    hasher.update(data);
    format!("{:x}", hasher.finalize())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProofBundle {
    pub parse_proof: String,
    pub opt_proof: String,
    pub combined: String,
}

pub struct ProofVerifier;

impl ProofVerifier {
    pub fn new() -> Self {
        Self
    }

    pub fn parse_with_proof(&self, bytes: &[u8]) -> Result<(String, String), String> {
        let proof = sha3_hex(bytes);
        Ok((proof.clone(), format!("parse:{proof}")))
    }

    pub fn optimize_with_proof(&self, ast_hash: &str) -> Result<String, String> {
        Ok(format!("opt:{ast_hash}"))
    }

    pub fn combine(&self, proofs: &[String]) -> Result<String, String> {
        let joined = proofs.join("|");
        Ok(sha3_hex(joined.as_bytes()))
    }

    pub fn decompile_with_proof(
        &self,
        bytes: &[u8],
        outputs: &[JavaClassOutput],
    ) -> Result<String, String> {
        let (_, parse_proof) = self.parse_with_proof(bytes)?;
        let source_blob: String = outputs.iter().map(|o| o.source.as_str()).collect();
        let opt_proof = self.optimize_with_proof(&sha3_hex(source_blob.as_bytes()))?;
        self.combine(&[parse_proof, opt_proof])
    }
}

impl Default for ProofVerifier {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_proof_combine() {
        let v = ProofVerifier::new();
        let combined = v.combine(&["a".into(), "b".into()]).unwrap();
        assert!(!combined.is_empty());
    }

    #[test]
    fn test_parse_proof() {
        let v = ProofVerifier::new();
        let (_, proof) = v.parse_with_proof(b"dex").unwrap();
        assert!(proof.starts_with("parse:"));
    }
}
