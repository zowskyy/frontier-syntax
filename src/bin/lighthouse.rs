//! Frontier Lighthouse — verification and audit service.

use frontier::{parse_and_resolve, sha3_256_hex};
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = env::args().collect();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("audit");

    match cmd {
        "audit" => run_audit(),
        "health" => {
            println!("{{\"status\":\"ok\",\"service\":\"frontier-lighthouse\"}}");
        }
        _ => {
            eprintln!("Usage: lighthouse [audit|health]");
            std::process::exit(1);
        }
    }
}

fn run_audit() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let mut checks = 0usize;
    let mut passed = 0usize;

    let samples = [
        root.join("examples/sample.fr"),
        root.join("examples/v2_parser_test.fr"),
    ];

    for sample in samples {
        checks += 1;
        if !sample.exists() {
            eprintln!("SKIP missing {}", sample.display());
            continue;
        }
        let source = fs::read_to_string(&sample).expect("read sample");
        if sample.extension().and_then(|e| e.to_str()) == Some("fr")
            || sample.file_name().and_then(|n| n.to_str()) == Some("v2_parser_test.fr")
        {
            match frontier::parser::parse_file(sample.to_str().unwrap_or("")) {
                Ok(_) => {
                    passed += 1;
                    println!("✅ v2 parse: {}", sample.display());
                }
                Err(e) => eprintln!("❌ v2 parse {}: {e}", sample.display()),
            }
        } else {
            match parse_and_resolve(&source) {
                Ok((program, _)) => {
                    passed += 1;
                    let hash = sha3_256_hex(&serde_json::to_string(&program).unwrap());
                    println!("✅ v1 resolve: {} hash={hash}", sample.display());
                }
                Err(e) => eprintln!("❌ v1 resolve {}: {e}", sample.display()),
            }
        }
    }

    println!("Lighthouse audit: {passed}/{checks} checks passed");
    if passed < checks {
        std::process::exit(1);
    }
}
