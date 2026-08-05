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
        _ => {
            eprintln!("Commands: parse, parse-v2, resolve, hash, gen-artifacts, fuzz");
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
