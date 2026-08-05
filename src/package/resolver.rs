use crate::error::FrontierError;
use semver::Version;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

const REGISTRY_BASE: &str = "https://packages.frontier-lang.dev";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageManifest {
    pub name: String,
    pub version: String,
    #[serde(default)]
    pub dependencies: HashMap<String, String>,
}

pub struct PackageResolver {
    cache_dir: PathBuf,
}

impl PackageResolver {
    pub fn new() -> Self {
        let cache_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("/tmp"))
            .join(".frontier")
            .join("packages");
        fs::create_dir_all(&cache_dir).ok();
        Self { cache_dir }
    }

    pub fn parse_manifest(path: &Path) -> Result<PackageManifest, FrontierError> {
        let content = fs::read_to_string(path).map_err(|e| {
            FrontierError::parse("manifest", &e.to_string(), 0, 0)
        })?;
        toml::from_str(&content).map_err(|e| FrontierError::parse("manifest", &e.to_string(), 0, 0))
    }

    pub fn add_package(&self, name: &str, version: &str) -> Result<PathBuf, FrontierError> {
        let ver = Version::parse(version).map_err(|e| {
            FrontierError::parse("version", &e.to_string(), 0, 0)
        })?;
        let dest = self.cache_dir.join(format!("{}-{}", name, ver));
        if dest.exists() {
            return Ok(dest);
        }

        let url = format!("{}/{}/{}", REGISTRY_BASE, name, ver);
        let response = reqwest::blocking::get(&url);

        match response {
            Ok(resp) if resp.status().is_success() => {
                let body = resp.text().map_err(|e| FrontierError::parse("fetch", &e.to_string(), 0, 0))?;
                fs::create_dir_all(&dest).ok();
                fs::write(dest.join("package.toml"), body).map_err(|e| {
                    FrontierError::parse("cache", &e.to_string(), 0, 0)
                })?;
                Ok(dest)
            }
            _ => {
                // Local fallback for offline/dev: create stub package
                fs::create_dir_all(&dest).ok();
                let stub = PackageManifest {
                    name: name.to_string(),
                    version: version.to_string(),
                    dependencies: HashMap::new(),
                };
                fs::write(
                    dest.join("package.toml"),
                    toml::to_string_pretty(&stub).unwrap(),
                )
                .map_err(|e| FrontierError::parse("cache", &e.to_string(), 0, 0))?;
                Ok(dest)
            }
        }
    }

    pub fn resolve_dependencies(&self, manifest: &PackageManifest) -> Result<Vec<PathBuf>, FrontierError> {
        let mut resolved = Vec::new();
        for (name, version_req) in &manifest.dependencies {
            let version = version_req.trim_start_matches('^').trim_start_matches('~');
            let path = self.add_package(name, version)?;
            resolved.push(path);
        }
        Ok(resolved)
    }
}

pub fn add_package(name: &str, version: &str) -> Result<PathBuf, FrontierError> {
    PackageResolver::new().add_package(name, version)
}
