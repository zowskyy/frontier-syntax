use frontier_lexer::Lexer;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;

const VERSION: &str = env!("CARGO_PKG_VERSION");

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

fn load_lexer() -> Lexer {
    let root = repo_root();
    let cycle1 = fs::read_to_string(root.join("syntax/token_regex_table.json"))
        .expect("token_regex_table.json");
    let cycle2_path = root.join("syntax/cycle2/extensions.json");
    let cycle2 = fs::read_to_string(cycle2_path).ok();
    Lexer::from_tables(&cycle1, cycle2.as_deref()).expect("lexer init")
}

fn cmd_version() {
    println!("frontier {VERSION} (Frontier Syntax — A+ Hard Gate)");
}

fn cmd_validate(path: &PathBuf) {
    let source = fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("read error: {e}");
        process::exit(1);
    });
    let lexer = load_lexer();
    let result = lexer.lex(&source);
    if result.valid {
        println!(
            "✅ valid — {} tokens",
            result.tokens.len()
        );
    } else {
        for err in &result.errors {
            eprintln!("L{}:{} {}", err.line, err.column, err.message);
        }
        process::exit(1);
    }
}

fn cmd_compile(path: &PathBuf, target: &str, output: Option<&PathBuf>) {
    let source = fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("read error: {e}");
        process::exit(1);
    });
    let lexer = load_lexer();
    let result = lexer.lex(&source);
    if !result.valid {
        eprintln!("❌ syntax errors — cannot compile");
        for err in &result.errors {
            eprintln!("L{}:{} {}", err.line, err.column, err.message);
        }
        process::exit(1);
    }

    let out = output.cloned().unwrap_or_else(|| {
        path.file_stem()
            .map(|s| PathBuf::from(s.to_string_lossy().to_string()))
            .unwrap_or_else(|| PathBuf::from("out"))
    });

    // LHN1 capsule — same format as Lighthouse browser-compiler offline mode
    let meta = serde_json::json!({
        "magic": "LHN1",
        "target": target,
        "mode": "frontier-cli",
        "compiledAt": chrono_now(),
        "version": VERSION,
        "sourceFile": path.display().to_string(),
        "tokenCount": result.tokens.len()
    });
    let meta_bytes = meta.to_string().into_bytes();
    let src_bytes = source.into_bytes();
    let mut out_bytes = Vec::with_capacity(8 + meta_bytes.len() + src_bytes.len());
    out_bytes.extend_from_slice(&(meta_bytes.len() as u32).to_le_bytes());
    out_bytes.extend_from_slice(&meta_bytes);
    out_bytes.extend_from_slice(&(src_bytes.len() as u32).to_le_bytes());
    out_bytes.extend_from_slice(&src_bytes);

    fs::write(&out, &out_bytes).unwrap_or_else(|e| {
        eprintln!("write error: {e}");
        process::exit(1);
    });
    println!("✅ compiled {} → {} ({} bytes, target={target})", path.display(), out.display(), out_bytes.len());
}

fn chrono_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let d = SystemTime::now().duration_since(UNIX_EPOCH).unwrap();
    format!("{}.{:03}Z", d.as_secs(), d.subsec_millis())
}

fn cmd_targets() {
    let targets = [
        ("linux-x64", "Linux x64", ""),
        ("linux-arm64", "Linux ARM64 (Raspberry Pi 4/5)", ""),
        ("windows-x64", "Windows .exe", ".exe"),
        ("macos-arm64", "macOS Apple Silicon", ""),
        ("android-arm64", "Android ARM64", ".apk"),
        ("ios-arm64", "iOS ARM64", ".ipa"),
        ("rpi-zero", "Raspberry Pi Zero", ""),
        ("riscv64", "RISC-V 64", ""),
    ];
    let json: Vec<serde_json::Value> = targets
        .iter()
        .map(|(id, label, ext)| {
            serde_json::json!({ "id": id, "label": label, "ext": ext })
        })
        .collect();
    println!("{}", serde_json::to_string_pretty(&json).unwrap());
}

fn usage() {
    eprintln!(
        "Frontier Syntax CLI v{VERSION}

Usage:
  frontier --version
  frontier validate <file.fr>
  frontier compile <file.fr> [--target <id>] [-o <output>]
  frontier targets
"
    );
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        usage();
        process::exit(1);
    }

    match args[1].as_str() {
        "--version" | "-V" | "version" => cmd_version(),
        "validate" => {
            let path = PathBuf::from(args.get(2).expect("file required"));
            cmd_validate(&path);
        }
        "compile" | "build" => {
            let path = PathBuf::from(args.get(2).expect("file required"));
            let mut target = "native".to_string();
            let mut output = None;
            let mut i = 3;
            while i < args.len() {
                match args[i].as_str() {
                    "--target" | "-t" => {
                        target = args.get(i + 1).expect("--target value").clone();
                        i += 2;
                    }
                    "-o" | "--output" => {
                        output = Some(PathBuf::from(args.get(i + 1).expect("-o value")));
                        i += 2;
                    }
                    _ => i += 1,
                }
            }
            cmd_compile(&path, &target, output.as_ref());
        }
        "targets" => cmd_targets(),
        _ => {
            usage();
            process::exit(1);
        }
    }
}
