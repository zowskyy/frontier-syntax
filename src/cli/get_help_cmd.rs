use super::colors;
use std::process::Command;

pub fn run_get_help(args: &[String]) {
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string());
    let script = format!("{manifest_dir}/scripts/get_help.py");

    let mut cmd = Command::new("python3");
    cmd.arg(&script);
    for arg in args.iter().skip(2) {
        cmd.arg(arg);
    }

    match cmd.status() {
        Ok(status) if status.success() => {}
        Ok(status) => std::process::exit(status.code().unwrap_or(1)),
        Err(e) => {
            colors::print_error(&format!("Failed to run get_help.py: {e}"));
            colors::print_error("Try: python3 scripts/get_help.py \"your problem\"");
            std::process::exit(1);
        }
    }
}
