use super::completions;
use super::config::{self, FrontierConfig};
use std::path::{Path, PathBuf};

struct CwdGuard {
    original: PathBuf,
}

impl CwdGuard {
    fn change_to(path: &Path) -> Self {
        let original = std::env::current_dir().expect("current dir");
        std::env::set_current_dir(path).expect("set current dir");
        Self { original }
    }
}

impl Drop for CwdGuard {
    fn drop(&mut self) {
        let _ = std::env::set_current_dir(&self.original);
    }
}

fn temp_test_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "frontier_cli_test_{}_{}",
        std::process::id(),
        name
    ));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    dir
}

fn assert_default_config(config: &FrontierConfig) {
    let defaults = FrontierConfig::default();
    assert_eq!(config.optimize, defaults.optimize);
    assert_eq!(config.target, defaults.target);
    assert_eq!(config.telemetry, defaults.telemetry);
    assert_eq!(config.profile, defaults.profile);
    assert_eq!(config.browser_compat, defaults.browser_compat);
}

#[test]
fn load_config_returns_defaults_when_no_file_exists() {
    let dir = temp_test_dir("no_config");
    let _guard = CwdGuard::change_to(&dir);

    let config = config::load_config();
    assert_default_config(&config);

    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn load_config_falls_back_to_defaults_on_malformed_toml() {
    let dir = temp_test_dir("malformed_toml");
    let _guard = CwdGuard::change_to(&dir);
    std::fs::write("frontier.toml", "not valid [[[").expect("write malformed config");

    let config = config::load_config();
    assert_default_config(&config);

    std::fs::remove_file("frontier.toml").ok();
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn generate_bash_returns_completion_script() {
    let script = completions::generate("bash").expect("bash completions");
    assert!(!script.is_empty());
    assert!(script.contains("_frontier_completions"));
}

#[test]
fn generate_invalid_shell_returns_err() {
    let result = completions::generate("invalid");
    assert!(result.is_err());
}
