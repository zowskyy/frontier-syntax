use chrono::Utc;
use serde::Serialize;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;

#[derive(Debug, Serialize)]
pub struct TelemetryData {
    pub event: String,
    pub timestamp: String,
    pub duration_ms: Option<u128>,
    pub command: Option<String>,
}

pub fn is_enabled() -> bool {
    std::env::var("FRONTIER_TELEMETRY")
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false)
}

pub fn record_event(data: TelemetryData) {
    if !is_enabled() {
        return;
    }

    let path = PathBuf::from(".frontier-telemetry.log");

    if path.exists() {
        if let Ok(meta) = path.metadata() {
            if meta.len() > 1_000_000 {
                let backup = path.with_extension("log.old");
                let _ = fs::rename(&path, &backup);
            }
        }
    }

    let json = serde_json::to_string(&data).unwrap_or_default();
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&path) {
        let _ = writeln!(file, "{json}");
    }
}

pub fn record_command(command: &str, duration_ms: u128) {
    record_event(TelemetryData {
        event: "command".to_string(),
        timestamp: Utc::now().to_rfc3339(),
        duration_ms: Some(duration_ms),
        command: Some(command.to_string()),
    });
}
