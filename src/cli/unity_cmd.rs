use super::colors::{print_error, print_success};
use super::errors;
use std::fs;
use std::path::PathBuf;

pub fn run_unity(args: &[String]) -> Result<(), i32> {
    let sub = args.get(2).map(|s| s.as_str()).unwrap_or("help");
    match sub {
        "compile" => {
            let input = args.get(3).ok_or_else(|| {
                print_error("usage: frontier unity compile <file.fr> [-o out]");
                1
            })?;
            let source = fs::read_to_string(input).map_err(|e| {
                errors::print_io_error("Failed to read input", &e);
                1
            })?;

            let output = args
                .iter()
                .position(|a| a == "-o" || a == "--output")
                .and_then(|i| args.get(i + 1))
                .map(PathBuf::from)
                .unwrap_or_else(|| PathBuf::from(input).with_extension("wasm"));

            let module = frontier::unity_compile(&source).map_err(|e| {
                print_error(&e);
                1
            })?;
            fs::write(&output, &module.wasm).map_err(|e| {
                errors::print_io_error("Failed to write wasm", &e);
                1
            })?;
            print_success(&format!(
                "✅ Unity compiled to WASM: {} ({} bytes)",
                output.display(),
                module.size
            ));

            let js_path = output.with_extension("js");
            fs::write(&js_path, &module.glue).map_err(|e| {
                errors::print_io_error("Failed to write js glue", &e);
                1
            })?;
            print_success(&format!("✅ Unity glue: {}", js_path.display()));

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
            let input = args.get(3).ok_or_else(|| {
                print_error("usage: frontier unity verify <file.fr>");
                1
            })?;
            let source = fs::read_to_string(input).map_err(|e| {
                errors::print_io_error("Failed to read input", &e);
                1
            })?;
            let module = frontier::unity_compile(&source).map_err(|e| {
                print_error(&e);
                1
            })?;
            if frontier::unity_verify(&module) {
                print_success("✅ Unity module verified");
                println!("  Size: {} bytes", module.size);
                println!("  Entry: {}", module.entry_value);
                println!("  Knowledge suggestions: {}", module.knowledge.len());
            } else {
                print_error("❌ Unity module verification failed");
                return Err(1);
            }
        }
        _ => {
            print_error("Usage: frontier unity [compile|verify] <file.fr> [-o out]");
            return Err(1);
        }
    }
    Ok(())
}
