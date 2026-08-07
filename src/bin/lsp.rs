//! Frontier Neural-Symbolic LSP server (stdio JSON-RPC subset).

use frontier::lsp::neural_server::NeuralLspServer;
use std::io::{self, BufRead, Write};

fn main() {
    let server = NeuralLspServer::new();
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.trim().is_empty() {
            continue;
        }

        let req: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                let err = serde_json::json!({
                    "error": format!("invalid json: {e}"),
                });
                let _ = writeln!(stdout, "{err}");
                let _ = stdout.flush();
                continue;
            }
        };

        let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
        let id = req.get("id").cloned().unwrap_or(serde_json::Value::Null);

        let result = match method {
            "initialize" => serde_json::json!({
                "capabilities": {
                    "completionProvider": { "triggerCharacters": [".", " ", ":"] }
                }
            }),
            "completion" => {
                let params = req.get("params").cloned().unwrap_or_default();
                let source = params
                    .get("text")
                    .and_then(|t| t.as_str())
                    .unwrap_or("");
                let line_no = params.get("line").and_then(|l| l.as_u64()).unwrap_or(0) as usize;
                let character = params.get("character").and_then(|c| c.as_u64()).unwrap_or(0) as usize;
                let items = server.complete(source, line_no, character);
                serde_json::json!({ "items": items })
            }
            "health" => serde_json::json!({ "status": "ok", "service": "frontier-lsp" }),
            "shutdown" => serde_json::json!({ "status": "shutdown" }),
            _ => serde_json::json!({ "error": format!("unknown method: {method}") }),
        };

        let resp = serde_json::json!({ "id": id, "result": result });
        let _ = writeln!(stdout, "{resp}");
        let _ = stdout.flush();
    }
}
