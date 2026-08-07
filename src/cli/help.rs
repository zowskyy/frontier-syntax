use super::colors;
use colored::Colorize;

pub fn print_global_help() {
    println!("{}", "Frontier CLI v2.0".bold().green());
    println!("Formally verifiable programming language toolchain\n");

    colors::print_help_heading("Core Commands");
    colors::print_command("parse <file>", "Parse v1 source to AST JSON");
    colors::print_command("parse-v2 <file>", "Parse v2 source to AST JSON");
    colors::print_command("resolve <file>", "Parse and resolve symbols");
    colors::print_command("hash <file>", "Compute canonical AST SHA3-256 hash");
    colors::print_command("compile <file>", "Compile to WASM (use -t wasm, -O, -p)");
    colors::print_command("knowledge <sub>", "Knowledge Hypercube queries");

    colors::print_help_heading("Tooling");
    colors::print_command("get-help <message>", "Plain-language help — no GitHub required");
    colors::print_command("shell", "Interactive REPL");
    colors::print_command("watch [path]", "Watch directory and recompile on change");
    colors::print_command("config init|show", "Manage frontier.toml configuration");
    colors::print_command("completions <shell>", "Generate shell completions (bash/zsh/fish)");

    colors::print_help_heading("Project");
    colors::print_command("migrate --input --output", "Migrate foreign project to Frontier");
    colors::print_command("verify --input <dir>", "Verify migrated project");
    colors::print_command("run <file.frontier>", "Run a Frontier file");
    colors::print_command("gen-artifacts", "Regenerate syntax artifacts");
    colors::print_command("fuzz [count]", "Fuzz the parser");

    colors::print_help_heading("Examples");
    println!("  frontier compile examples/v2_parser_test.fr -t wasm -O -p");
    println!("  frontier knowledge suggest sort list::i32");
    println!("  frontier shell");
    println!("  frontier watch examples -- -t wasm -O");
}

pub fn print_compile_help() {
    colors::print_help_heading("compile — Compile Frontier source to WASM");
    println!();
    println!("Usage: frontier compile <file.fr> [options]");
    println!();
    colors::print_command("-t, --target wasm", "Compile to WebAssembly (default)");
    colors::print_command("--browser", "Emit browser-compatible JS glue");
    colors::print_command("-O, --optimize", "Enable Knowledge Hypercube optimization");
    colors::print_command("--no-optimize", "Disable optimization");
    colors::print_command("-o, --output <path>", "Output WASM file path");
    colors::print_command("-p, --profile", "Show compilation phase timings");
    println!();
    println!("Example:");
    println!("  frontier compile examples/v2_parser_test.fr -t wasm -O -p");
}
