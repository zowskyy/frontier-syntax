use frontier_dex::{DecompileOptions, Decompiler};
use std::env;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 || args.contains(&"--help".to_string()) || args.contains(&"-h".to_string()) {
        print_help();
        return;
    }

    let mut input: Option<String> = None;
    let mut options = DecompileOptions::default();
    let mut output_dir: Option<String> = None;
    let mut json_out = false;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--input" | "-i" => {
                i += 1;
                input = args.get(i).cloned();
            }
            "--output" | "-o" => {
                i += 1;
                output_dir = args.get(i).cloned();
            }
            "--generate-proof" => options.generate_proof = true,
            "--neural" => options.neural = true,
            "--cache" => options.cache = true,
            "--fallback" => options.fallback_engines = true,
            "--json" => json_out = true,
            _ if !args[i].starts_with('-') && input.is_none() => {
                input = Some(args[i].clone());
            }
            _ => {}
        }
        i += 1;
    }

    let input = match input {
        Some(p) => p,
        None => {
            eprintln!("Error: --input <classes.dex> required");
            print_help();
            process::exit(1);
        }
    };

    let mut decompiler = Decompiler::new(options);
    match decompiler.decompile_file(&input) {
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
                for class in &result.java_sources {
                    let name = class.class_name.trim_start_matches('L').trim_end_matches(';');
                    let path = format!("{dir}/{name}.java");
                    if let Err(e) = std::fs::write(&path, &class.source) {
                        eprintln!("Write {path}: {e}");
                    }
                }
            }
        }
        Err(e) => {
            eprintln!("Decompile error: {e}");
            process::exit(1);
        }
    }
}

fn print_help() {
    println!(
        "frontier-dex 2.0 — Formally verified Android DEX decompiler\n\n\
         Usage: frontier-dex --input <classes.dex> [options]\n\n\
         Options:\n\
           --input, -i <path>    Input DEX file\n\
           --output, -o <dir>    Output directory for .java files\n\
           --generate-proof      Emit ZK proof hash\n\
           --neural              Enable obfuscation predictor\n\
           --cache               Use content-addressable cache\n\
           --fallback            Enable CFR/Procyon/Fernflower fallback\n\
           --json                JSON output\n\
           -h, --help            Show this help"
    );
}
