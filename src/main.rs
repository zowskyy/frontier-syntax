use frontier::{
    canonical_ast_json, compile_to_object, generate_coq, generate_docs,
    parse_program, resolve_program, sha3_256_hex, add_package,
};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let args: Vec<String> = env::args().collect();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("help");

    match cmd {
        "parse" => {
            let path = args.get(2).expect("usage: frontier parse <file.fr>");
            let source = fs::read_to_string(path).expect("read file");
            let program = parse_program(&source, 64).expect("parse");
            println!("{}", serde_json::to_string_pretty(&program).unwrap());
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
        "compile" => {
            let path = args.get(2).expect("usage: frontier compile <file.fr> -o <output.o>");
            let out = args.iter().position(|a| a == "-o")
                .and_then(|i| args.get(i + 1))
                .map(PathBuf::from)
                .unwrap_or_else(|| PathBuf::from("examples/sample.o"));
            let source = fs::read_to_string(path).expect("read file");
            let program = parse_program(&source, 64).expect("parse");
            compile_to_object(&program, &out).expect("compile");
            println!("Compiled: {}", out.display());

            let exe = out.with_extension("");
            let exe = if exe.extension().is_none() {
                PathBuf::from("examples/sample")
            } else {
                exe
            };
            link_executable(&out, &exe);
        }
        "repl" => {
            frontier::repl::run_repl().expect("repl");
        }
        "prove" => {
            let path = args.get(2).expect("usage: frontier prove <file.fr> --backend coq");
            let backend = args.iter().position(|a| a == "--backend")
                .and_then(|i| args.get(i + 1))
                .map(|s| s.as_str())
                .unwrap_or("coq");
            let source = fs::read_to_string(path).expect("read file");
            let program = parse_program(&source, 64).expect("parse");
            let out = PathBuf::from("proofs").join(
                PathBuf::from(path).file_stem().unwrap().to_str().unwrap()
            );
            if backend == "coq" {
                fs::create_dir_all("proofs").ok();
                generate_coq(&program, &out.with_extension("v")).expect("prove");
                println!("Generated: {}", out.with_extension("v").display());
            }
        }
        "docs" => {
            let default = "examples/sample.fr".to_string();
            let path = args.get(2).unwrap_or(&default);
            let source = fs::read_to_string(path).expect("read file");
            let program = parse_program(&source, 64).expect("parse");
            generate_docs(&program, PathBuf::from("docs").as_path()).expect("docs");
            println!("Documentation generated in docs/");
        }
        "package" => {
            let sub = args.get(2).map(|s| s.as_str()).unwrap_or("help");
            match sub {
                "add" => {
                    let spec = args.get(3).expect("usage: frontier package add <name>@<version>");
                    let parts: Vec<&str> = spec.split('@').collect();
                    let name = parts[0];
                    let version = parts.get(1).copied().unwrap_or("1.0.0");
                    let path = add_package(name, version).expect("add package");
                    println!("Package cached: {}", path.display());
                }
                _ => eprintln!("usage: frontier package add <name>@<version>"),
            }
        }
        "gen-artifacts" => gen_all_artifacts(),
        "fuzz" => {
            let count: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(1_000_000);
            run_fuzz(count);
        }
        "publish" => run_publish(),
        _ => {
            eprintln!("Frontier v1.0.0 — commands:");
            eprintln!("  parse, resolve, hash, compile, repl, prove, docs, package, gen-artifacts, fuzz, publish");
        }
    }
}

fn link_executable(obj: &PathBuf, exe: &PathBuf) {
    let status = Command::new("clang")
        .arg(obj)
        .arg("-o")
        .arg(exe)
        .status();
    match status {
        Ok(s) if s.success() => println!("Linked: {}", exe.display()),
        Ok(s) => eprintln!("clang link failed: exit {}", s),
        Err(e) => eprintln!("clang not available: {}", e),
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

    for i in 0..iterations {
        let len = (i % 50) + 1;
        let mut s = String::new();
        for j in 0..len {
            if j > 0 { s.push(' '); }
            s.push_str(tokens[(i + j) % tokens.len()]);
        }

        let start = Instant::now();
        let result = std::panic::catch_unwind(|| parse_program(&s, 64));
        if result.is_err() { crashes += 1; }
        if start.elapsed() > Duration::from_millis(100) { hangs += 1; }
    }

    println!("Fuzz complete: {} iterations, crashes={}, hangs={}", iterations, crashes, hangs);
    assert_eq!(crashes, 0);
}

fn run_publish() {
    let status = Command::new("cargo").args(["publish", "--dry-run"]).status();
    println!("cargo publish --dry-run: {:?}", status);
    let npm = PathBuf::from("npm-package");
    if npm.exists() {
        let s = Command::new("npm").args(["publish", "--dry-run"]).current_dir(&npm).status();
        println!("npm publish --dry-run: {:?}", s);
    }
}
