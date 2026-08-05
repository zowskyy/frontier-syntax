//! Post-Quantum Signatures with Dilithium3 (NIST PQC finalist)

use pqcrypto_dilithium::dilithium3;
use pqcrypto_traits::sign::{PublicKey as _, SecretKey as _, SignedMessage as _};
use serde::{Deserialize, Serialize};

/// Post-quantum cryptographic key pair (Dilithium3)
#[derive(Clone)]
pub struct PqCrypto {
    public_key: dilithium3::PublicKey,
    secret_key: dilithium3::SecretKey,
}

/// Signature with metadata
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct PQSignature {
    pub signature: Vec<u8>,
    pub public_key: Vec<u8>,
    pub algorithm: String,
}

impl PqCrypto {
    /// Generate a new Dilithium3 key pair
    pub fn generate_keys() -> Self {
        let (public_key, secret_key) = dilithium3::keypair();
        PqCrypto {
            public_key,
            secret_key,
        }
    }

    /// Sign a message with the secret key
    pub fn sign(&self, message: &[u8]) -> PQSignature {
        let signed = dilithium3::sign(message, &self.secret_key);
        PQSignature {
            signature: signed.as_bytes().to_vec(),
            public_key: self.public_key.as_bytes().to_vec(),
            algorithm: "Dilithium3".to_string(),
        }
    }

    /// Verify a signed message
    pub fn verify(&self, message: &[u8], signature: &PQSignature) -> bool {
        let Ok(signed) = dilithium3::SignedMessage::from_bytes(&signature.signature) else {
            return false;
        };
        let Ok(opened) = dilithium3::open(&signed, &self.public_key) else {
            return false;
        };
        opened == message
    }

    /// Verify using embedded public key in signature
    pub fn verify_detached(message: &[u8], signature: &PQSignature) -> bool {
        let Ok(pk) = dilithium3::PublicKey::from_bytes(&signature.public_key) else {
            return false;
        };
        let Ok(signed) = dilithium3::SignedMessage::from_bytes(&signature.signature) else {
            return false;
        };
        dilithium3::open(&signed, &pk)
            .map(|m| m == message)
            .unwrap_or(false)
    }

    pub fn public_key_bytes(&self) -> Vec<u8> {
        self.public_key.as_bytes().to_vec()
    }

    pub fn sign_ast(&self, ast: &serde_json::Value) -> PQSignature {
        let ast_json = serde_json::to_string(ast).unwrap_or_default();
        self.sign(ast_json.as_bytes())
    }
}

pub fn sign_artifact(content: &str) -> (String, PQSignature) {
    let crypto = PqCrypto::generate_keys();
    let signature = crypto.sign(content.as_bytes());
    let hash = crate::canonicalize::sha3_256_hex(content);
    (hash, signature)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dilithium_sign_verify() {
        let crypto = PqCrypto::generate_keys();
        let message = b"Hello, Frontier v2.0 with real Dilithium!";
        let signature = crypto.sign(message);
        assert!(crypto.verify(message, &signature));
    }

    #[test]
    fn test_ast_signing() {
        let crypto = PqCrypto::generate_keys();
        let ast = serde_json::json!({
            "type": "Program",
            "statements": [{"type": "LetStatement", "name": "x", "value": 5}]
        });
        let signature = crypto.sign_ast(&ast);
        let ast_json = serde_json::to_string(&ast).unwrap();
        assert!(crypto.verify(ast_json.as_bytes(), &signature));
    }
}
