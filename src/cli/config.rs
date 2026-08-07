use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrontierConfig {
    pub optimize: bool,
    pub target: String,
    pub telemetry: bool,
    pub profile: bool,
    pub browser_compat: bool,
}

impl Default for FrontierConfig {
    fn default() -> Self {
        Self {
            optimize: true,
            target: "wasm".to_string(),
            telemetry: false,
            profile: false,
            browser_compat: false,
        }
    }
}

const DEFAULT_CONFIG: &str = r#"# Frontier CLI configuration
optimize = true
target = "wasm"
telemetry = false
profile = false
browser_compat = false
"#;

pub fn load_config() -> FrontierConfig {
    let paths = ["frontier.toml", ".frontierrc", ".frontierrc.toml"];

    for path in paths {
        let config_path = PathBuf::from(path);
        if config_path.exists() {
            let content = fs::read_to_string(&config_path).unwrap_or_default();
            match toml::from_str(&content) {
                Ok(config) => return config,
                Err(e) => {
                    eprintln!("⚠️  Failed to parse {}: {}", path, e);
                    eprintln!("   Using default configuration");
                }
            }
        }
    }

    FrontierConfig::default()
}

pub fn init_config(path: Option<&str>) -> Result<PathBuf, String> {
    let config_path = path
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("frontier.toml"));

    if config_path.exists() {
        return Err(format!(
            "Config file already exists: {}",
            config_path.display()
        ));
    }

    fs::write(&config_path, DEFAULT_CONFIG).map_err(|e| e.to_string())?;
    Ok(config_path)
}

pub fn show_config() {
    let config = load_config();
    println!("{}", toml::to_string_pretty(&config).unwrap_or_default());
}
