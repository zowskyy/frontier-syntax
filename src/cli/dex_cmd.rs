use super::colors::{print_error, print_success};
use frontier_dex::{DecompileOptions, Decompiler};
use std::path::Path;

pub fn run_dex(args: &[String]) -> Result<(), i32> {
    let sub = args.get(2).map(|s| s.as_str()).unwrap_or("help");
    match sub {
        "decompile" => run_decompile(args),
        "help" | "--help" | "-h" => {
            super::help::print_dex_help();
            Ok(())
        }
        _ => {
            print_error("Usage: frontier dex decompile --input <file.dex> [--proof] [--neural] [--cache]");
            Err(1)
        }
    }
}

fn run_decompile(args: &[String]) -> Result<(), i32> {
    let input = args
        .iter()
        .position(|a| a == "--input" || a == "-i")
        .and_then(|i| args.get(i + 1))
        .ok_or_else(|| {
            print_error("usage: frontier dex decompile --input <file.dex> [--proof] [--neural] [--cache]");
            1
        })?;

    if !Path::new(input).exists() {
        print_error(&format!("Input file not found: {input}"));
        return Err(1);
    }

    let mut options = DecompileOptions::default();
    options.generate_proof = args.iter().any(|a| a == "--proof" || a == "--generate-proof");
    options.neural = args.iter().any(|a| a == "--neural");
    options.cache = args.iter().any(|a| a == "--cache");
    options.fallback_engines = args.iter().any(|a| a == "--fallback");

    let output_dir = args
        .iter()
        .position(|a| a == "--output" || a == "-o")
        .and_then(|i| args.get(i + 1));

    let json_out = args.iter().any(|a| a == "--json");

    let mut decompiler = Decompiler::new(options);
    match decompiler.decompile_file(input) {
        Ok(result) => {
            if json_out {
                println!("{}", serde_json::to_string_pretty(&result).unwrap_or_default());
            } else {
                for class in &result.java_sources {
                    println!("// === {} ===", class.class_name);
                    println!("{}", class.source);
                }
                if let Some(proof) = &result.proof_hash {
                    eprintln!("Proof: {proof}");
                }
                if result.obfuscation_score > 0.0 {
                    eprintln!("Obfuscation score: {:.2}", result.obfuscation_score);
                }
            }

            if let Some(dir) = output_dir {
                std::fs::create_dir_all(dir).map_err(|e| {
                    print_error(&format!("Failed to create output directory: {e}"));
                    1
                })?;
                for class in &result.java_sources {
                    let name = class.class_name.trim_start_matches('L').trim_end_matches(';');
                    let path = format!("{dir}/{name}.java");
                    std::fs::write(&path, &class.source).map_err(|e| {
                        print_error(&format!("Failed to write {path}: {e}"));
                        1
                    })?;
                }
                print_success(&format!("✅ Wrote {} Java file(s) to {dir}", result.java_sources.len()));
            }

            Ok(())
        }
        Err(e) => {
            print_error(&format!("Decompile error: {e}"));
            Err(1)
        }
    }
}
