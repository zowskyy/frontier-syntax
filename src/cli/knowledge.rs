use super::colors;

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
        _ => {
            colors::print_help_heading("Knowledge Commands");
            colors::print_command("suggest <op> [type]", "Get optimal algorithm suggestion");
            colors::print_command("ancestry <op>", "Show algorithm ancestry chain");
            colors::print_command("tradeoffs <op>", "Show dimensional tradeoffs");
        }
    }
}
