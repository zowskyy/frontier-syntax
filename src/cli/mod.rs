pub mod colors;
pub mod compile;
pub mod completions;
pub mod config;
pub mod errors;
pub mod help;
pub mod knowledge;
pub mod mcp;
pub mod profile;
pub mod repl;
pub mod telemetry;
pub mod unity_cmd;
pub mod watch;

use colors::print_error;
use frontier::{canonical_ast_json, parse_program, resolve_program, sha3_256_hex};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

pub fn run() {
    let args: Vec<String> = env::args().collect();
    let start = Instant::now();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("help");

    let result = dispatch(&args, cmd);

    if let Err(code) = result {
        std::process::exit(code);
    }

    let cmd_str = args[1..].join(" ");
    telemetry::record_command(&cmd_str, start.elapsed().as_millis());
}

fn dispatch(args: &[String], cmd: &str) -> Result<(), i32> {
    match cmd {
        "help" | "--help" | "-h" => help::print_global_help(),
        "parse" => run_parse(args)?,
        "parse-v2" => run_parse_v2(args)?,
        "resolve" => run_resolve(args)?,
        "hash" => run_hash(args)?,
        "gen-artifacts" => gen_all_artifacts(),
        "fuzz" => {
            let count: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(1_000_000);
            run_fuzz(count);
        }
        "migrate" => run_migrate(args)?,
        "verify" => run_verify(args)?,
        "run" => run_file(args)?,
        "compile" => compile::run_compile(args),
        "knowledge" => knowledge::run_knowledge(args),
        "mcp" => mcp::run_mcp(args),
        "unity" => unity_cmd::run_unity(args)?,
        "config" => run_config(args)?,
        "shell" => {
            if let Err(e) = repl::start_repl() {
                print_error(&format!("REPL error: {e}"));
                return Err(1);
            }
        }
        "watch" => {
            if let Err(e) = watch::start_watch(args) {
                print_error(&format!("Watch error: {e}"));
                return Err(1);
            }
        }
        "completions" => {
            let shell = args.get(2).map(|s| s.as_str()).unwrap_or("bash");
            match completions::generate(shell) {
                Ok(script) => println!("{script}"),
                Err(e) => {
                    print_error(&e);
                    return Err(1);
                }
            }
        }
        "compile-help" => help::print_compile_help(),
        _ => {
            print_error(&format!("Unknown command: {cmd}"));
            help::print_global_help();
            return Err(1);
        }
    }
    Ok(())
}

fn run_parse(args: &[String]) -> Result<(), i32> {
    let path = args.get(2).ok_or_else(|| {
        print_error("usage: frontier parse <file.fr>");
        1
    })?;

    let source = fs::read_to_string(path).map_err(|e| {
        errors::print_io_error("Failed to read file", &e);
        1
    })?;

    let program = parse_program(&source, 64).map_err(|e| {
        errors::print_parse_error(&e);
        1
    })?;

    let json = serde_json::to_string_pretty(&program).unwrap();
    if let Some(out) = args.get(3) {
        if out == "--output" {
            let out_path = args.get(4).ok_or_else(|| {
                print_error("usage: frontier parse <file> --output <path>");
                1
            })?;
            fs::write(out_path, &json).map_err(|e| {
                errors::print_io_error("Failed to write output", &e);
                1
            })?;
            colors::print_success(&format!("✅ Wrote AST to {out_path}"));
        } else {
            println!("{json}");
        }
    } else {
        println!("{json}");
    }
    Ok(())
}

fn run_parse_v2(args: &[String]) -> Result<(), i32> {
    let path = args.get(2).ok_or_else(|| {
        print_error("usage: frontier parse-v2 <file.fr>");
        1
    })?;

    let ast = frontier::parser::parse_file(path).map_err(|e| {
        print_error(&e);
        1
    })?;

    let json = serde_json::to_string_pretty(&ast).unwrap();
    if let Some(out_path) = args
        .get(4)
        .filter(|_| args.get(3).map(|s| s.as_str()) == Some("--output"))
    {
        fs::write(out_path, &json).map_err(|e| {
            errors::print_io_error("Failed to write output", &e);
            1
        })?;
        colors::print_success(&format!("✅ Wrote v2 AST to {out_path}"));
    } else {
        println!("{json}");
    }
    Ok(())
}

fn run_resolve(args: &[String]) -> Result<(), i32> {
    let path = args.get(2).ok_or_else(|| {
        print_error("usage: frontier resolve <file.fr>");
        1
    })?;

    let source = fs::read_to_string(path).map_err(|e| {
        errors::print_io_error("Failed to read file", &e);
        1
    })?;

    let program = parse_program(&source, 64).map_err(|e| {
        errors::print_parse_error(&e);
        1
    })?;

    let resolved = resolve_program(&program).map_err(|e| {
        errors::print_parse_error(&e);
        1
    })?;

    println!("{}", serde_json::to_string_pretty(&resolved).unwrap());
    Ok(())
}

fn run_hash(args: &[String]) -> Result<(), i32> {
    let path = args.get(2).ok_or_else(|| {
        print_error("usage: frontier hash <file.fr>");
        1
    })?;

    let source = fs::read_to_string(path).map_err(|e| {
        errors::print_io_error("Failed to read file", &e);
        1
    })?;

    let program = parse_program(&source, 64).map_err(|e| {
        errors::print_parse_error(&e);
        1
    })?;

    let json = canonical_ast_json(&program).map_err(|e| {
        print_error(&e.to_string());
        1
    })?;

    println!("{}", sha3_256_hex(&json));
    Ok(())
}

fn run_migrate(args: &[String]) -> Result<(), i32> {
    let input = args
        .iter()
        .position(|a| a == "--input")
        .and_then(|i| args.get(i + 1))
        .ok_or_else(|| {
            print_error("usage: frontier migrate --input <dir> --output <dir>");
            1
        })?;
    let output = args
        .iter()
        .position(|a| a == "--output")
        .and_then(|i| args.get(i + 1))
        .ok_or_else(|| {
            print_error("usage: frontier migrate --input <dir> --output <dir>");
            1
        })?;

    let report = frontier::migrate::migrate_project(
        PathBuf::from(input).as_path(),
        PathBuf::from(output).as_path(),
    )
    .map_err(|e| {
        print_error(&e.to_string());
        1
    })?;

    colors::print_success("✅ Migration complete");
    println!("  Language: {}", report.source_language);
    println!("  Files scanned: {}", report.files_scanned);
    println!("  Migrated: {}", report.files_migrated);
    println!("  Manual review: {}", report.files_manual);
    println!("  Output: {}", report.output_dir.display());
    Ok(())
}

fn run_verify(args: &[String]) -> Result<(), i32> {
    let input = args
        .iter()
        .position(|a| a == "--input")
        .and_then(|i| args.get(i + 1))
        .ok_or_else(|| {
            print_error("usage: frontier verify --input <dir>");
            1
        })?;

    let result = frontier::migrate::verify_migrated_project(PathBuf::from(input).as_path())
        .map_err(|e| {
            print_error(&e.to_string());
            1
        })?;

    println!("{}", serde_json::to_string_pretty(&result).unwrap());
    if result["errors"]
        .as_array()
        .map(|a| !a.is_empty())
        .unwrap_or(false)
    {
        return Err(1);
    }
    Ok(())
}

fn run_file(args: &[String]) -> Result<(), i32> {
    let path = args.get(2).ok_or_else(|| {
        print_error("usage: frontier run <file.frontier>");
        1
    })?;

    let msg = frontier::migrate::run_frontier_file(PathBuf::from(path).as_path()).map_err(|e| {
        print_error(&e.to_string());
        1
    })?;

    println!("{msg}");
    Ok(())
}

fn run_config(args: &[String]) -> Result<(), i32> {
    let sub = args.get(2).map(|s| s.as_str()).unwrap_or("show");
    match sub {
        "init" => {
            let path = args.get(3).map(|s| s.as_str());
            match config::init_config(path) {
                Ok(p) => colors::print_success(&format!("✅ Created config: {}", p.display())),
                Err(e) => {
                    print_error(&e);
                    return Err(1);
                }
            }
        }
        "show" => config::show_config(),
        _ => {
            print_error("usage: frontier config [init|show]");
            return Err(1);
        }
    }
    Ok(())
}

fn gen_all_artifacts() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let sample = root.join("examples/sample.fr");
    let source = fs::read_to_string(&sample).expect("read sample");

    let program = parse_program(&source, 64).expect("parse sample");
    let ast_json = serde_json::to_string_pretty(&program).unwrap();
    fs::write(root.join("syntax/ast_sample.json"), &ast_json).expect("write ast_sample");

    let resolved = resolve_program(&program).expect("resolve sample");
    fs::write(
        root.join("syntax/resolved_symbols.json"),
        serde_json::to_string_pretty(&resolved).unwrap(),
    )
    .expect("write resolved_symbols");

    let schema = fs::read_to_string(root.join("syntax/schema.json")).unwrap_or_default();
    if schema.is_empty() {
        eprintln!("schema.json must exist before gen-artifacts");
    }

    let canonical = canonical_ast_json(&program).expect("canonicalize");
    let hash = sha3_256_hex(&canonical);
    fs::write(root.join("syntax/ast_hash.sha3"), format!("{hash}\n")).expect("write ast_hash");

    let grammar = fs::read_to_string(root.join("syntax/grammar.g4")).expect("read grammar");
    let lexicon = fs::read_to_string(root.join("syntax/lexicon.ebnf")).expect("read lexicon");
    let schema_content = fs::read_to_string(root.join("syntax/schema.json")).expect("read schema");
    let final_input = format!("{grammar}{lexicon}{schema_content}");
    let final_hash = sha3_256_hex(&final_input);
    fs::write(
        root.join("syntax/final_hash.sha3"),
        format!("{final_hash}\n"),
    )
    .expect("write final_hash");

    colors::print_success("Artifacts generated.");
    println!("ast_hash: {hash}");
    println!("final_hash: {final_hash}");
}

fn run_fuzz(iterations: usize) {
    use std::time::{Duration, Instant};

    let tokens = [
        "let", "fn", "if", "else", "return", "true", "false", "null", "int", "float", "bool",
        "string", "void", "x", "y", "z", "foo", "bar", "(", ")", "{", "}", ";", ":", ",", ".",
        "+", "-", "*", "/", "%", "^", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!", "~", "=",
        "0", "1", "42", "3.14", "\"hello\"",
    ];

    let mut crashes = 0;
    let mut hangs = 0;
    let mut parsed = 0;

    for i in 0..iterations {
        let len = (i % 50) + 1;
        let mut s = String::new();
        for j in 0..len {
            if j > 0 {
                s.push(' ');
            }
            s.push_str(tokens[(i + j) % tokens.len()]);
        }

        let start = Instant::now();
        let result = std::panic::catch_unwind(|| parse_program(&s, 64));
        let elapsed = start.elapsed();

        match result {
            Ok(Ok(_)) => parsed += 1,
            Ok(Err(_)) => {}
            Err(_) => crashes += 1,
        }
        if elapsed > Duration::from_millis(100) {
            hangs += 1;
        }
    }

    println!("Fuzz complete: {iterations} iterations");
    println!("  Parsed OK: {parsed}");
    println!("  Crashes: {crashes}");
    println!("  Hangs (>100ms): {hangs}");
    assert_eq!(crashes, 0, "Parser must not crash");
}
