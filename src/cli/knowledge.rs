use super::colors;
use std::env;
use std::path::PathBuf;
use std::process::Command;

pub fn run_knowledge(args: &[String]) {
    let sub = args.get(2).map(|s| s.as_str()).unwrap_or("help");
    match sub {
        "suggest" => {
            let operation = match args.get(3) {
                Some(op) => op.as_str(),
                None => {
                    colors::print_error("usage: frontier knowledge suggest <op> [data_type]");
                    std::process::exit(1);
                }
            };
            let data_type = args.get(4).map(|s| s.as_str()).unwrap_or("list::i32");
            let suggestion =
                frontier::browser_compiler::algorithm_suggestion(operation, data_type);
            colors::print_knowledge_suggestion(&suggestion.name, suggestion.discovery_year);
            println!("{}", serde_json::to_string_pretty(&suggestion).unwrap());
        }
        "ancestry" => {
            let operation = match args.get(3) {
                Some(op) => op.as_str(),
                None => {
                    colors::print_error("usage: frontier knowledge ancestry <op>");
                    std::process::exit(1);
                }
            };
            let ancestors = frontier::browser_compiler::ancestors(operation);
            println!("{}", serde_json::to_string_pretty(&ancestors).unwrap());
        }
        "tradeoffs" => {
            let operation = match args.get(3) {
                Some(op) => op.as_str(),
                None => {
                    colors::print_error("usage: frontier knowledge tradeoffs <op>");
                    std::process::exit(1);
                }
            };
            let tradeoffs = frontier::browser_compiler::tradeoffs(operation);
            println!("{}", serde_json::to_string_pretty(&tradeoffs).unwrap());
        }
        "ingest" => {
            let file = args
                .iter()
                .position(|a| a == "--file")
                .and_then(|i| args.get(i + 1))
                .map(|s| s.as_str())
                .unwrap_or("chat_scrub/WORKER_REPORT.json");

            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let script = root.join("scripts/chat_knowledge_store.py");
            let output = Command::new("python3")
                .arg(&script)
                .arg("ingest")
                .arg("--file")
                .arg(file)
                .current_dir(&root)
                .output()
                .unwrap_or_else(|e| {
                    colors::print_error(&format!("Failed to run ingest: {e}"));
                    std::process::exit(1);
                });

            if !output.status.success() {
                colors::print_error(&String::from_utf8_lossy(&output.stderr));
                std::process::exit(1);
            }
            colors::print_success("✅ Chat knowledge ingested into hypercube index");
            print!("{}", String::from_utf8_lossy(&output.stdout));
        }
        "query" => {
            let query = args[3..]
                .iter()
                .position(|a| a.as_str() == "--limit")
                .map(|i| args[3..i + 3].join(" "))
                .unwrap_or_else(|| args[3..].join(" "));

            if query.is_empty() {
                colors::print_error("usage: frontier knowledge query <text> [--limit N]");
                std::process::exit(1);
            }

            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let script = root.join("scripts/chat_knowledge_store.py");
            let output = Command::new("python3")
                .arg(&script)
                .arg("query")
                .arg(&query)
                .current_dir(&root)
                .output()
                .unwrap_or_else(|e| {
                    colors::print_error(&format!("Failed to run query: {e}"));
                    std::process::exit(1);
                });

            if !output.status.success() {
                colors::print_error(&String::from_utf8_lossy(&output.stderr));
                std::process::exit(1);
            }
            print!("{}", String::from_utf8_lossy(&output.stdout));
        }
        _ => {
            colors::print_help_heading("Knowledge Commands");
            colors::print_command("suggest <op> [type]", "Get optimal algorithm suggestion");
            colors::print_command("ancestry <op>", "Show algorithm ancestry chain");
            colors::print_command("tradeoffs <op>", "Show dimensional tradeoffs");
            colors::print_command(
                "ingest --file <path>",
                "Ingest WORKER_REPORT.json into chat knowledge index",
            );
            colors::print_command("query <text>", "Search embedded chat scrub knowledge");
        }
    }
}
