use super::colors;
use std::env;
use std::fs;
use std::path::PathBuf;

pub fn run_mcp(args: &[String]) {
    let sub = args.get(2).map(|s| s.as_str()).unwrap_or("help");
    match sub {
        "register" => {
            let tool = args
                .iter()
                .position(|a| a == "--tool")
                .and_then(|i| args.get(i + 1))
                .map(|s| s.as_str())
                .unwrap_or("query_chat_knowledge");

            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let server_script = root.join("scripts/frontier_mcp_server.py");
            let config_dir = root.join(".cursor");
            fs::create_dir_all(&config_dir).unwrap_or_else(|e| {
                colors::print_error(&format!("Failed to create .cursor: {e}"));
                std::process::exit(1);
            });

            let config_path = config_dir.join("mcp_config.json");
            let config = serde_json::json!({
                "mcpServers": {
                    "frontier": {
                        "command": "python3",
                        "args": [server_script.to_string_lossy()],
                        "tools": [tool]
                    }
                }
            });
            fs::write(&config_path, serde_json::to_string_pretty(&config).unwrap())
                .unwrap_or_else(|e| {
                    colors::print_error(&format!("Failed to write MCP config: {e}"));
                    std::process::exit(1);
                });

            colors::print_success(&format!(
                "✅ Registered MCP tool '{tool}' at {}",
                config_path.display()
            ));
            println!("Server: python3 {}", server_script.display());
        }
        _ => {
            colors::print_help_heading("MCP Commands");
            colors::print_command(
                "register --tool <name>",
                "Register frontier MCP server with query_chat_knowledge",
            );
        }
    }
}
