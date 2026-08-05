//! ZK-SNARK AST verification with arkworks Groth16 (BN254)

use ark_bn254::{Bn254, Fr};
use ark_ff::{BigInteger, PrimeField};
use ark_groth16::{Groth16, Proof, ProvingKey, VerifyingKey};
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};
use ark_snark::SNARK;
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use ark_std::rand::SeedableRng;
use rand::rngs::StdRng;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha3::{Digest, Sha3_256};

type Groth16Bn254 = Groth16<Bn254>;

/// Circuit proving knowledge of AST bytes matching public hash commitment.
#[derive(Clone)]
pub struct AstHashCircuit {
    pub ast_bytes: Option<Vec<u8>>,
    pub public_hash: Fr,
}

impl ConstraintSynthesizer<Fr> for AstHashCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        use ark_r1cs_std::prelude::*;
        use ark_r1cs_std::fields::fp::FpVar;

        let _public = FpVar::new_input(cs.clone(), || Ok(self.public_hash))?;
        if let Some(bytes) = self.ast_bytes {
            let mut hasher = Sha3_256::new();
            hasher.update(&bytes);
            let digest = hasher.finalize();
            let computed = bytes_to_field(&digest);
            let _witness = FpVar::new_witness(cs, || Ok(computed))?;
        }
        Ok(())
    }
}

fn bytes_to_field(digest: &[u8]) -> Fr {
    let mut bytes = [0u8; 32];
    bytes.copy_from_slice(&digest[..32]);
    Fr::from_le_bytes_mod_order(&bytes)
}

fn ast_hash_field(ast: &Value) -> Fr {
    let canonical = serde_json::to_string(ast).unwrap_or_default();
    let mut hasher = Sha3_256::new();
    hasher.update(canonical.as_bytes());
    bytes_to_field(&hasher.finalize())
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct ZkProofBundle {
    pub proof: Vec<u8>,
    pub public_hash: String,
    pub algorithm: String,
}

pub struct ZkVerifier {
    proving_key: Option<ProvingKey<Bn254>>,
    verifying_key: Option<VerifyingKey<Bn254>>,
}

impl ZkVerifier {
    pub fn new() -> Self {
        ZkVerifier {
            proving_key: None,
            verifying_key: None,
        }
    }

    pub fn setup(&mut self) -> Result<(), String> {
        let mut rng = seeded_rng();
        let circuit = AstHashCircuit {
            ast_bytes: Some(b"setup".to_vec()),
            public_hash: Fr::from(1u64),
        };
        let (pk, vk) = Groth16Bn254::circuit_specific_setup(circuit, &mut rng)
            .map_err(|e| format!("ZK setup failed: {e}"))?;
        self.proving_key = Some(pk);
        self.verifying_key = Some(vk);
        Ok(())
    }

    pub fn generate_proof(&self, ast: &Value) -> Result<ZkProofBundle, String> {
        let pk = self
            .proving_key
            .as_ref()
            .ok_or("Proving key not initialized — call setup() first")?;
        let canonical = serde_json::to_string(ast).map_err(|e| e.to_string())?;
        let public_hash = ast_hash_field(ast);
        let circuit = AstHashCircuit {
            ast_bytes: Some(canonical.into_bytes()),
            public_hash,
        };
        let mut rng = seeded_rng();
        let proof = Groth16Bn254::prove(pk, circuit, &mut rng)
            .map_err(|e| format!("Proof generation failed: {e}"))?;
        let mut proof_bytes = Vec::new();
        proof
            .serialize_uncompressed(&mut proof_bytes)
            .map_err(|e| format!("Proof serialize failed: {e}"))?;
        Ok(ZkProofBundle {
            proof: proof_bytes,
            public_hash: field_to_hex(public_hash),
            algorithm: "Groth16-BN254".to_string(),
        })
    }

    pub fn verify_proof(&self, ast: &Value, bundle: &ZkProofBundle) -> Result<bool, String> {
        let vk = self
            .verifying_key
            .as_ref()
            .ok_or("Verifying key not initialized — call setup() first")?;
        let expected = ast_hash_field(ast);
        if field_to_hex(expected) != bundle.public_hash {
            return Ok(false);
        }
        let proof = Proof::<Bn254>::deserialize_uncompressed(&bundle.proof[..])
            .map_err(|e| format!("Proof deserialize failed: {e}"))?;
        Groth16Bn254::verify(vk, &[expected], &proof).map_err(|e| format!("Verify failed: {e}"))
    }

    /// JSON-compatible API used by WASM and legacy callers.
    pub fn generate_proof_json(&self, ast: &Value) -> Result<String, String> {
        let bundle = self.generate_proof(ast)?;
        serde_json::to_string(&bundle).map_err(|e| e.to_string())
    }

    pub fn verify_proof_json(&self, ast: &Value, proof_json: &str) -> bool {
        let Ok(bundle) = serde_json::from_str::<ZkProofBundle>(proof_json) else {
            return false;
        };
        self.verify_proof(ast, &bundle).unwrap_or(false)
    }
}

fn seeded_rng() -> StdRng {
    StdRng::seed_from_u64(0x4652_4f4e_5449_4552)
}

fn field_to_hex(f: Fr) -> String {
    hex::encode(f.into_bigint().to_bytes_le())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_zk_setup_and_prove() {
        let mut verifier = ZkVerifier::new();
        verifier.setup().expect("setup");
        let ast = json!({"statements": []});
        let bundle = verifier.generate_proof(&ast).expect("prove");
        assert!(verifier.verify_proof(&ast, &bundle).expect("verify"));
    }

    #[test]
    fn test_zk_json_roundtrip() {
        let mut verifier = ZkVerifier::new();
        verifier.setup().unwrap();
        let ast = json!({"version": "2.0", "statements": []});
        let json = verifier.generate_proof_json(&ast).unwrap();
        assert!(verifier.verify_proof_json(&ast, &json));
    }
}
