use super::colors;
use super::compile;
use super::config;
use super::knowledge;
use std::io::{self, Write};

pub fn start_repl() -> Result<(), Box<dyn std::error::Error>> {
    match try_rustyline_repl() {
        Ok(()) => Ok(()),
        Err(e) => {
            colors::print_warning(&format!(
                "Advanced REPL unavailable ({e}), using basic mode"
            ));
            try_stdin_repl()
        }
    }
}

fn try_rustyline_repl() -> Result<(), Box<dyn std::error::Error>> {
    use rustyline::error::ReadlineError;
    use rustyline::DefaultEditor;

    let mut rl = DefaultEditor::new()?;
    colors::print_success("Frontier REPL v2.0 — type .help for commands, .exit to quit");

    loop {
        let readline = rl.readline("frontier> ");
        match readline {
            Ok(line) => {
                let _ = rl.add_history_entry(&line);
                if !process_repl_line(&line) {
                    break;
                }
            }
            Err(ReadlineError::Interrupted) => {
                println!("^C");
                continue;
            }
            Err(ReadlineError::Eof) => break,
            Err(err) => return Err(Box::new(err)),
        }
    }

    println!("👋 Goodbye!");
    Ok(())
}

fn try_stdin_repl() -> Result<(), Box<dyn std::error::Error>> {
    colors::print_success("Frontier REPL (basic mode) — type .help for commands, .exit to quit");
    let mut input = String::new();

    loop {
        print!("frontier> ");
        io::stdout().flush()?;
        input.clear();
        if io::stdin().read_line(&mut input)? == 0 {
            break;
        }
        if !process_repl_line(input.trim()) {
            break;
        }
    }

    println!("👋 Goodbye!");
    Ok(())
}

fn process_repl_line(line: &str) -> bool {
    let line = line.trim();
    if line.is_empty() {
        return true;
    }

    match line {
        ".exit" | ".quit" => return false,
        ".help" => print_repl_help(),
        ".config" => config::show_config(),
        cmd if cmd.starts_with("compile ") => {
            let args: Vec<String> = std::iter::once("frontier".to_string())
                .chain(cmd.split_whitespace().map(String::from))
                .collect();
            compile::run_compile(&args);
        }
        cmd if cmd.starts_with("knowledge ") => {
            let args: Vec<String> = std::iter::once("frontier".to_string())
                .chain(cmd.split_whitespace().map(String::from))
                .collect();
            knowledge::run_knowledge(&args);
        }
        cmd if cmd.starts_with("parse ") => {
            let path = cmd.strip_prefix("parse ").unwrap_or("");
            if path.is_empty() {
                colors::print_error("Usage: parse <file.fr>");
            } else {
                repl_parse(path);
            }
        }
        _ => colors::print_error(&format!("Unknown command: {line}. Type .help for help.")),
    }

    true
}

fn print_repl_help() {
    colors::print_help_heading("REPL Commands");
    colors::print_command(".help", "Show this help");
    colors::print_command(".exit", "Exit the REPL");
    colors::print_command(".config", "Show current configuration");
    colors::print_command("parse <file>", "Parse a Frontier source file");
    colors::print_command("compile <file>", "Compile a Frontier source file");
    colors::print_command("knowledge suggest <op>", "Get algorithm suggestion");
}

fn repl_parse(path: &str) {
    match frontier::parser::parse_file(path) {
        Ok(ast) => {
            if let Ok(json) = serde_json::to_string_pretty(&ast) {
                println!("{json}");
            }
        }
        Err(e) => colors::print_error(&e),
    }
}
