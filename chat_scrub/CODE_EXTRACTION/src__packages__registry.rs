use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Decentralized package registry backed by IPFS content addressing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageManifest {
    pub name: String,
    pub version: String,
    pub ipfs_cid: String,
    pub dependencies: HashMap<String, String>,
}

pub struct PackageRegistry {
    packages: HashMap<String, PackageManifest>,
}

impl PackageRegistry {
    pub fn new() -> Self {
        PackageRegistry {
            packages: HashMap::new(),
        }
    }

    pub fn publish(&mut self, manifest: PackageManifest) -> Result<(), String> {
        if !manifest.ipfs_cid.starts_with("Qm") && !manifest.ipfs_cid.starts_with("ipfs://") {
            return Err(format!("Invalid CID: {}", manifest.ipfs_cid));
        }
        let key = format!("{}@{}", manifest.name, manifest.version);
        self.packages.insert(key, manifest);
        Ok(())
    }

    pub fn resolve(&self, name: &str, version: &str) -> Option<&PackageManifest> {
        let key = format!("{name}@{version}");
        self.packages.get(&key)
    }

    pub fn list(&self) -> Vec<&PackageManifest> {
        self.packages.values().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_publish_and_resolve() {
        let mut registry = PackageRegistry::new();
        registry
            .publish(PackageManifest {
                name: "math-utils".to_string(),
                version: "1.0.0".to_string(),
                ipfs_cid: "QmExampleHash1234567890".to_string(),
                dependencies: HashMap::new(),
            })
            .unwrap();
        assert!(registry.resolve("math-utils", "1.0.0").is_some());
    }
}
