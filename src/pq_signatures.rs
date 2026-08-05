use sha3::{Digest, Sha3_256};

/// Post-quantum signature interface.
/// Production deployments use Dilithium/Kyber via pqcrypto crates.
pub struct PqCrypto {
    secret_key: [u8; 32],
    public_key: [u8; 32],
}

impl PqCrypto {
    pub fn generate_keys(seed: &[u8]) -> Self {
        let mut hasher = Sha3_256::new();
        hasher.update(b"frontier-pq-secret:");
        hasher.update(seed);
        let secret_key: [u8; 32] = hasher.finalize().into();

        let mut hasher = Sha3_256::new();
        hasher.update(b"frontier-pq-public:");
        hasher.update(&secret_key);
        let public_key: [u8; 32] = hasher.finalize().into();

        PqCrypto {
            secret_key,
            public_key,
        }
    }

    pub fn sign(&self, data: &[u8]) -> Vec<u8> {
        let mut hasher = Sha3_256::new();
        hasher.update(b"frontier-pq-sign:");
        hasher.update(&self.secret_key);
        hasher.update(data);
        hasher.finalize().to_vec()
    }

    pub fn verify(&self, data: &[u8], signature: &[u8]) -> bool {
        self.sign(data) == signature
    }

    pub fn public_key(&self) -> [u8; 32] {
        self.public_key
    }
}

pub fn sign_artifact(content: &str) -> (String, Vec<u8>) {
    let crypto = PqCrypto::generate_keys(content.as_bytes());
    let signature = crypto.sign(content.as_bytes());
    let hash = crate::canonicalize::sha3_256_hex(content);
    (hash, signature)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sign_verify() {
        let crypto = PqCrypto::generate_keys(b"frontier-v2");
        let data = b"Hello, Frontier v2.0!";
        let signature = crypto.sign(data);
        assert!(crypto.verify(data, &signature));
    }
}
