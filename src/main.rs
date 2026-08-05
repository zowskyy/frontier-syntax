use frontier::{canonical_ast_json, parse_program, resolve_program, sha3_256_hex};
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = env::args().collect();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("help");

    match cmd {
        "parse" => {
            let path = args.get(2).expect("usage: frontier parse <file.fr>");
            let output = args.get(3).map(|s| s.as_str());
            let source = fs::read_to_string(path).expect("read file");
            let program = parse_program(&source, 64).expect("parse");
            let json = serde_json::to_string_pretty(&program).unwrap();
            if let Some(out) = output {
                if out == "--output" {
                    let out_path = args.get(4).expect("usage: frontier parse <file> --output <path>");
                    fs::write(out_path, &json).expect("write output");
                    println!("✅ Wrote AST to {out_path}");
                } else {
                    println!("{json}");
                }
            } else {
                println!("{json}");
            }
        }
        "parse-v2" => {
            let path = args.get(2).expect("usage: frontier parse-v2 <file.fr>");
            let output = args
                .get(4)
                .filter(|_| args.get(3).map(|s| s.as_str()) == Some("--output"))
                .map(|s| s.as_str());
            let ast = frontier::parser::parse_file(path).expect("parse v2");
            let json = serde_json::to_string_pretty(&ast).unwrap();
            if let Some(out_path) = output {
                fs::write(out_path, &json).expect("write output");
                println!("✅ Wrote v2 AST to {out_path}");
            } else {
                println!("{json}");
            }
        }
        "resolve" => {
            let path = args.get(2).expect("usage: frontier resolve <file.fr>");
            let source = fs::read_to_string(path).expect("read file");
            let program = parse_program(&source, 64).expect("parse");
            let resolved = resolve_program(&program).expect("resolve");
            println!("{}", serde_json::to_string_pretty(&resolved).unwrap());
        }
        "hash" => {
            let path = args.get(2).expect("usage: frontier hash <file.fr>");
            let source = fs::read_to_string(path).expect("read file");
            let program = parse_program(&source, 64).expect("parse");
            let json = canonical_ast_json(&program).expect("canonicalize");
            println!("{}", sha3_256_hex(&json));
        }
        "gen-artifacts" => {
            gen_all_artifacts();
        }
        "fuzz" => {
            let count: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(1_000_000);
            run_fuzz(count);
        }
        "migrate" => {
            let input = args
                .iter()
                .position(|a| a == "--input")
                .and_then(|i| args.get(i + 1))
                .expect("usage: frontier migrate --input <dir> --output <dir>");
            let output = args
                .iter()
                .position(|a| a == "--output")
                .and_then(|i| args.get(i + 1))
                .expect("usage: frontier migrate --input <dir> --output <dir>");
            let report = frontier::migrate::migrate_project(
                PathBuf::from(input).as_path(),
                PathBuf::from(output).as_path(),
            )
            .expect("migration failed");
            println!("✅ Migration complete");
            println!("  Language: {}", report.source_language);
            println!("  Files scanned: {}", report.files_scanned);
            println!("  Migrated: {}", report.files_migrated);
            println!("  Manual review: {}", report.files_manual);
            println!("  Output: {}", report.output_dir.display());
        }
        "verify" => {
            let input = args
                .iter()
                .position(|a| a == "--input")
                .and_then(|i| args.get(i + 1))
                .expect("usage: frontier verify --input <dir>");
            let result = frontier::migrate::verify_migrated_project(PathBuf::from(input).as_path())
                .expect("verification failed");
            println!("{}", serde_json::to_string_pretty(&result).unwrap());
            if result["errors"].as_array().map(|a| !a.is_empty()).unwrap_or(false) {
                std::process::exit(1);
            }
        }
        "run" => {
            let path = args.get(2).expect("usage: frontier run <file.frontier>");
            let msg = frontier::migrate::run_frontier_file(PathBuf::from(path).as_path())
                .expect("run failed");
            println!("{msg}");
        }
        "compile" => {
            run_compile(&args);
        }
        "knowledge" => {
            run_knowledge(&args);
        }
        "unity" => {
            run_unity(&args);
        }
        _ => {
            eprintln!(
                "Commands: parse, parse-v2, resolve, hash, gen-artifacts, fuzz, migrate, verify, run, compile, knowledge, unity"
            );
        }
    }
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
    fs::write(root.join("syntax/ast_hash.sha3"), format!("{}\n", hash)).expect("write ast_hash");

    let grammar = fs::read_to_string(root.join("syntax/grammar.g4")).expect("read grammar");
    let lexicon = fs::read_to_string(root.join("syntax/lexicon.ebnf")).expect("read lexicon");
    let schema_content = fs::read_to_string(root.join("syntax/schema.json")).expect("read schema");
    let final_input = format!("{}{}{}", grammar, lexicon, schema_content);
    let final_hash = sha3_256_hex(&final_input);
    fs::write(
        root.join("syntax/final_hash.sha3"),
        format!("{}\n", final_hash),
    )
    .expect("write final_hash");

    println!("Artifacts generated.");
    println!("ast_hash: {}", hash);
    println!("final_hash: {}", final_hash);
}

fn run_fuzz(iterations: usize) {
    use std::time::{Duration, Instant};

    let tokens = [
        "let", "fn", "if", "else", "return", "true", "false", "null",
        "int", "float", "bool", "string", "void",
        "x", "y", "z", "foo", "bar",
        "(", ")", "{", "}", ";", ":", ",", ".",
        "+", "-", "*", "/", "%", "^", "==", "!=", "<", ">", "<=", ">=",
        "&&", "||", "!", "~", "=",
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

    println!("Fuzz complete: {} iterations", iterations);
    println!("  Parsed OK: {}", parsed);
    println!("  Crashes: {}", crashes);
    println!("  Hangs (>100ms): {}", hangs);
    assert_eq!(crashes, 0, "Parser must not crash");
}

fn run_compile(args: &[String]) {
    let input = args.get(2).expect("usage: frontier compile <file.fr> [--target wasm] [--browser] [--optimize] [-o out]");
    let source = fs::read_to_string(input).expect("read input");

    let target_wasm = args.windows(2).any(|w| w[0] == "--target" && w[1] == "wasm")
        || args.iter().any(|a| a == "--wasm");
    let browser = args.iter().any(|a| a == "--browser");
    let optimize = !args.iter().any(|a| a == "--no-optimize");

    let output = args
        .iter()
        .position(|a| a == "-o" || a == "--output")
        .and_then(|i| args.get(i + 1))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(input).with_extension("wasm"));

    if target_wasm || browser {
        let options = frontier::browser_compiler::CompileOptions {
            optimize,
            browser_compat: browser,
        };
        let result = frontier::browser_compiler::compile(&source, &options).expect("compile failed");
        fs::write(&output, &result.wasm).expect("write wasm");
        println!("✅ Compiled to WASM: {}", output.display());
        if let Some(js) = result.js_glue {
            let js_path = output.with_extension("js");
            fs::write(&js_path, js).expect("write js glue");
            println!("✅ JS glue: {}", js_path.display());
        }
        for warning in &result.warnings {
            println!("  ⚡ {warning}");
        }
    } else {
        eprintln!("Native compilation not yet implemented. Use --target wasm or --browser.");
        std::process::exit(1);
    }
}

fn run_knowledge(args: &[String]) {
    let sub = args.get(2).map(|s| s.as_str()).unwrap_or("help");
    match sub {
        "suggest" => {
            let operation = args.get(3).expect("usage: frontier knowledge suggest <op> [data_type]");
            let data_type = args.get(4).map(|s| s.as_str()).unwrap_or("list::i32");
            let suggestion = frontier::browser_compiler::algorithm_suggestion(operation, data_type);
            println!("{}", serde_json::to_string_pretty(&suggestion).unwrap());
        }
        "ancestry" => {
            let operation = args.get(3).expect("usage: frontier knowledge ancestry <op>");
            let ancestors = frontier::browser_compiler::ancestors(operation);
            println!("{}", serde_json::to_string_pretty(&ancestors).unwrap());
        }
        "tradeoffs" => {
            let operation = args.get(3).expect("usage: frontier knowledge tradeoffs <op>");
            let tradeoffs = frontier::browser_compiler::tradeoffs(operation);
            println!("{}", serde_json::to_string_pretty(&tradeoffs).unwrap());
        }
        _ => {
            eprintln!("Usage: frontier knowledge [suggest|ancestry|tradeoffs] ...");
        }
    }
}

fn run_unity(args: &[String]) {
    let sub = args.get(2).map(|s| s.as_str()).unwrap_or("help");
    match sub {
        "compile" => {
            let input = args.get(3).expect("usage: frontier unity compile <file.fr> [-o out]");
            let source = fs::read_to_string(input).expect("read input");

            let output = args
                .iter()
                .position(|a| a == "-o" || a == "--output")
                .and_then(|i| args.get(i + 1))
                .map(PathBuf::from)
                .unwrap_or_else(|| PathBuf::from(input).with_extension("wasm"));

            let module = frontier::unity_compile(&source).expect("unity compile failed");
            fs::write(&output, &module.wasm).expect("write wasm");
            println!("✅ Unity compiled to WASM: {} ({} bytes)", output.display(), module.size);

            let js_path = output.with_extension("js");
            fs::write(&js_path, &module.glue).expect("write js glue");
            println!("✅ Unity glue: {}", js_path.display());

            for k in &module.knowledge {
                println!(
                    "  ⚡ Knowledge: {} → {} ({})",
                    k.operation, k.algorithm, k.year
                );
            }

            if module.spec_verified {
                println!("  ✅ Spec and implementation aligned");
            }
        }
        "verify" => {
            let input = args.get(3).expect("usage: frontier unity verify <file.fr>");
            let source = fs::read_to_string(input).expect("read input");
            let module = frontier::unity_compile(&source).expect("unity compile failed");
            if frontier::unity_verify(&module) {
                println!("✅ Unity module verified");
                println!("  Size: {} bytes", module.size);
                println!("  Entry: {}", module.entry_value);
                println!("  Knowledge suggestions: {}", module.knowledge.len());
            } else {
                eprintln!("❌ Unity module verification failed");
                std::process::exit(1);
            }
        }
        _ => {
            eprintln!("Usage: frontier unity [compile|verify] <file.fr> [-o out]");
        }
    }
}
