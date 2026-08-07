use super::colors;
use super::config;
use super::errors;
use super::profile;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::PathBuf;

pub fn run_compile(args: &[String]) {
    if args.iter().any(|a| a == "--help" || a == "-h") {
        super::help::print_compile_help();
        return;
    }

    let cfg = config::load_config();

    let input = match args.get(2) {
        Some(p) => p,
        None => {
            errors::print_compile_error(
                "usage: frontier compile <file.fr> [-t wasm] [--browser] [-O] [--no-optimize] [-o out] [-p]",
            );
            std::process::exit(1);
        }
    };

    let source = match fs::read_to_string(input) {
        Ok(s) => s,
        Err(e) => {
            errors::print_io_error(&format!("Failed to read {input}"), &e);
            std::process::exit(1);
        }
    };

    let bootstrap = has_flag(args, "--bootstrap");
    let target_wasm = !bootstrap
        && (flag(args, "-t", "wasm")
            || flag(args, "--target", "wasm")
            || has_flag(args, "--wasm")
            || cfg.target == "wasm");
    let browser = has_flag(args, "--browser") || cfg.browser_compat;
    let optimize = !has_flag(args, "--no-optimize") && (has_flag(args, "-O") || has_flag(args, "--optimize") || cfg.optimize);
    let show_profile = has_flag(args, "-p") || has_flag(args, "--profile") || cfg.profile;

    let output = args
        .iter()
        .position(|a| a == "-o" || a == "--output")
        .and_then(|i| args.get(i + 1))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(input).with_extension("wasm"));

    if target_wasm || browser {
        if optimize {
            colors::print_progress("🧠 Applying Knowledge Hypercube optimization...");
            let suggestion = frontier::knowledge_bridge::get_optimal_algorithm(
                "sort",
                "list::i32",
                frontier::knowledge::SizeHint::Medium,
            );
            colors::print_knowledge_suggestion(&suggestion.name, suggestion.discovery_year);
        }

        let options = frontier::browser_compiler::CompileOptions {
            optimize,
            browser_compat: browser,
            profile: show_profile,
        };

        match frontier::browser_compiler::compile(&source, &options) {
            Ok(result) => {
                if let Err(e) = fs::write(&output, &result.wasm) {
                    errors::print_io_error(&format!("Failed to write {}", output.display()), &e);
                    std::process::exit(1);
                }
                colors::print_success(&format!("✅ Compiled to WASM: {}", output.display()));

                if let Some(js) = result.js_glue {
                    let js_path = output.with_extension("js");
                    if let Err(e) = fs::write(&js_path, js) {
                        errors::print_io_error(&format!("Failed to write {}", js_path.display()), &e);
                        std::process::exit(1);
                    }
                    colors::print_success(&format!("✅ JS glue: {}", js_path.display()));
                }

                for warning in &result.warnings {
                    colors::print_warning(&format!("⚡ {warning}"));
                }

                if let Some(ref p) = result.profile {
                    profile::print_profile(p);
                }

                if let Some(alg) = &result.selected_algorithm {
                    colors::print_progress(&format!("Algorithm applied to codegen: {alg}"));
                }
            }
            Err(e) => {
                errors::print_compile_error(&e);
                std::process::exit(1);
            }
        }
    } else if bootstrap {
        // Native / Genesis bootstrap compile — deterministic WASM artifact
        let options = frontier::browser_compiler::CompileOptions {
            optimize,
            browser_compat: false,
            profile: show_profile,
        };

        match frontier::browser_compiler::compile(&source, &options) {
            Ok(result) => {
                if let Err(e) = fs::write(&output, &result.wasm) {
                    errors::print_io_error(&format!("Failed to write {}", output.display()), &e);
                    std::process::exit(1);
                }
                colors::print_success(&format!("✅ Genesis bootstrap: {}", output.display()));

                // Write executable launcher alongside for self-host recompile
                let launcher = if output.extension().is_some() {
                    output.with_extension("run")
                } else {
                    PathBuf::from(format!("{}.run", output.display()))
                };
                let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml");
                let script = format!(
                    "#!/bin/sh\n# Frontier Genesis bootstrap — self-hosting recompile\nif [ \"$1\" = \"compile\" ]; then\n  exec cargo run --manifest-path \"{manifest}\" --quiet --bin frontier -- compile \"$2\" -t wasm -O -o \"$4\"\nfi\necho \"usage: $0 compile <file.fr> -o <out>\" >&2\nexit 1\n",
                    manifest = manifest.display()
                );
                if let Err(e) = fs::write(&launcher, script) {
                    errors::print_io_error(&format!("Failed to write {}", launcher.display()), &e);
                    std::process::exit(1);
                }
                if let Ok(meta) = fs::metadata(&launcher) {
                    let mut perms = meta.permissions();
                    perms.set_mode(0o755);
                    let _ = fs::set_permissions(&launcher, perms);
                }

                if let Some(ref p) = result.profile {
                    profile::print_profile(p);
                }
            }
            Err(e) => {
                errors::print_compile_error(&e);
                std::process::exit(1);
            }
        }
    } else {
        errors::print_compile_error("Native compilation requires --bootstrap. Use -t wasm for WASM output.");
        std::process::exit(1);
    }
}

fn has_flag(args: &[String], flag: &str) -> bool {
    args.iter().any(|a| a == flag)
}

fn flag(args: &[String], name: &str, value: &str) -> bool {
    args.windows(2).any(|w| w[0] == name && w[1] == value)
}
