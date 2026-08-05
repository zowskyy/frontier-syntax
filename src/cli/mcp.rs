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
        "list" => {
            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let config_path = root.join(".cursor/mcp_config.json");
            if !config_path.exists() {
                colors::print_error("No MCP config found. Run: frontier mcp register --tool query_chat_knowledge");
                std::process::exit(1);
            }
            let config: serde_json::Value = serde_json::from_str(
                &fs::read_to_string(&config_path).unwrap_or_else(|e| {
                    colors::print_error(&format!("Failed to read MCP config: {e}"));
                    std::process::exit(1);
                }),
            )
            .unwrap_or_else(|e| {
                colors::print_error(&format!("Invalid MCP config: {e}"));
                std::process::exit(1);
            });
            let tools = config
                .get("mcpServers")
                .and_then(|s| s.get("frontier"))
                .and_then(|f| f.get("tools"))
                .and_then(|t| t.as_array())
                .cloned()
                .unwrap_or_default();
            colors::print_help_heading("Registered MCP Tools");
            for tool in tools {
                if let Some(name) = tool.as_str() {
                    colors::print_command(name, "frontier MCP server tool");
                }
            }
        }
        _ => {
            colors::print_help_heading("MCP Commands");
            colors::print_command(
                "register --tool <name>",
                "Register frontier MCP server with query_chat_knowledge",
            );
            colors::print_command("list", "List registered MCP tools");
        }
    }
}
