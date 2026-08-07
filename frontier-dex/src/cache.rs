use crate::decompiler::DecompileResult;
use serde_json;
use sha3::{Digest, Sha3_256};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

fn sha3_hex(data: &[u8]) -> String {
    let mut hasher = Sha3_256::new();
    hasher.update(data);
    format!("{:x}", hasher.finalize())
}

pub struct DexCache {
    dir: PathBuf,
    memory: HashMap<String, DecompileResult>,
}

impl Default for DexCache {
    fn default() -> Self {
        let dir = std::env::temp_dir().join("frontier-dex-cache");
        let _ = fs::create_dir_all(&dir);
        Self {
            dir,
            memory: HashMap::new(),
        }
    }
}

impl DexCache {
    pub fn content_key(bytes: &[u8]) -> String {
        sha3_hex(bytes)
    }

    pub fn get(&self, key: &str) -> Option<DecompileResult> {
        if let Some(v) = self.memory.get(key) {
            return Some(v.clone());
        }
        let path = self.dir.join(format!("{key}.json"));
        let data = fs::read_to_string(path).ok()?;
        serde_json::from_str(&data).ok()
    }

    pub fn put(&mut self, key: &str, result: &DecompileResult) -> bool {
        self.memory.insert(key.to_string(), result.clone());
        let path = self.dir.join(format!("{key}.json"));
        if let Ok(json) = serde_json::to_string_pretty(result) {
            fs::write(path, json).is_ok()
        } else {
            false
        }
    }

    pub fn pin_ipfs_stub(&self, key: &str) -> String {
        format!("ipfs://Qm{key}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::decompiler::DecompileResult;

    #[test]
    fn test_cache_roundtrip() {
        let mut cache = DexCache::default();
        let key = DexCache::content_key(b"test");
        let result = DecompileResult {
            java_sources: vec![],
            proof_hash: None,
            cache_key: Some(key.clone()),
            obfuscation_score: 0.0,
            engine_used: "frontier-dex".into(),
            iterations: 0,
        };
        assert!(cache.put(&key, &result));
        let got = cache.get(&key).expect("hit");
        assert_eq!(got.engine_used, "frontier-dex");
    }

    #[test]
    fn test_ipfs_pin_stub() {
        let cache = DexCache::default();
        let uri = cache.pin_ipfs_stub("abc123");
        assert!(uri.starts_with("ipfs://"));
    }
}
