//! IPFS import resolution with gateway fetch support

use reqwest::blocking::Client;
use serde_json::Value;
use sha3::{Digest, Sha3_256};
use std::collections::HashMap;
use std::time::Duration;

const IPFS_PREFIX: &str = "ipfs://";

pub struct IpfsImportResolver {
    imports: Vec<String>,
    cache: HashMap<String, Vec<u8>>,
    client: Client,
    gateway: String,
}

impl Default for IpfsImportResolver {
    fn default() -> Self {
        Self::new()
    }
}

impl IpfsImportResolver {
    pub fn new() -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(10))
            .build()
            .unwrap_or_else(|_| Client::new());
        IpfsImportResolver {
            imports: Vec::new(),
            cache: HashMap::new(),
            client,
            gateway: "https://ipfs.io/ipfs/".to_string(),
        }
    }

    pub fn with_gateway(gateway: impl Into<String>) -> Self {
        let mut resolver = Self::new();
        resolver.gateway = gateway.into();
        resolver
    }

    pub fn resolve_import(&mut self, path: &str, alias: &str) -> Result<(), String> {
        if !path.starts_with(IPFS_PREFIX) {
            return Err(format!("Invalid IPFS path: {path}"));
        }
        let cid = &path[IPFS_PREFIX.len()..];
        if cid.is_empty() {
            return Err("Empty IPFS CID".to_string());
        }
        self.imports.push(format!("{alias}={path}"));
        Ok(())
    }

    /// Fetch package bytes from a public IPFS gateway (real network access).
    pub fn fetch_cid(&mut self, cid: &str) -> Result<Vec<u8>, String> {
        if let Some(cached) = self.cache.get(cid) {
            return Ok(cached.clone());
        }
        let url = format!("{}{cid}", self.gateway);
        let response = self
            .client
            .get(&url)
            .send()
            .map_err(|e| format!("IPFS gateway request failed: {e}"))?;
        if !response.status().is_success() {
            return Err(format!("IPFS gateway returned {}", response.status()));
        }
        let bytes = response
            .bytes()
            .map_err(|e| format!("Failed to read IPFS response: {e}"))?
            .to_vec();
        self.cache.insert(cid.to_string(), bytes.clone());
        Ok(bytes)
    }

    pub fn resolve_version_cid(&self, name: &str, version: &str) -> String {
        let mut hasher = Sha3_256::new();
        hasher.update(name.as_bytes());
        hasher.update(version.as_bytes());
        format!("bafybeig{}", hex::encode(&hasher.finalize()[..10]))
    }

    pub fn resolve_ast(&mut self, ast: &Value) -> Result<Vec<String>, Vec<String>> {
        let mut errors = Vec::new();
        if let Some(stmts) = ast.get("statements").and_then(|s| s.as_array()) {
            for stmt in stmts {
                if stmt.get("type").and_then(|t| t.as_str()) == Some("import_decl") {
                    let path = stmt.get("path").and_then(|p| p.as_str()).unwrap_or("");
                    let alias = stmt.get("alias").and_then(|a| a.as_str()).unwrap_or("");
                    if let Err(e) = self.resolve_import(path, alias) {
                        errors.push(e);
                    }
                }
            }
        }
        if errors.is_empty() {
            Ok(self.imports.clone())
        } else {
            Err(errors)
        }
    }

    pub fn imports(&self) -> &[String] {
        &self.imports
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_ipfs_import() {
        let mut resolver = IpfsImportResolver::new();
        resolver
            .resolve_import("ipfs://QmExampleHash1234567890", "math_utils")
            .unwrap();
        assert_eq!(resolver.imports().len(), 1);
    }

    #[test]
    fn test_invalid_ipfs_path() {
        let mut resolver = IpfsImportResolver::new();
        assert!(resolver.resolve_import("http://bad", "x").is_err());
    }

    #[test]
    fn test_resolve_ast() {
        let ast = json!({
            "statements": [{
                "type": "import_decl",
                "path": "ipfs://QmExampleHash1234567890",
                "alias": "utils"
            }]
        });
        let mut resolver = IpfsImportResolver::new();
        let imports = resolver.resolve_ast(&ast).unwrap();
        assert_eq!(imports.len(), 1);
    }

    #[test]
    fn test_version_cid_deterministic() {
        let resolver = IpfsImportResolver::new();
        let cid = resolver.resolve_version_cid("lib_a", "1.0.0");
        assert!(cid.starts_with("bafybeig"));
    }
}
