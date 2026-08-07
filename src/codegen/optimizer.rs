/// O2 optimization pass — applies LLVM opt pipeline to IR text.
pub fn optimize_ir(ir: &str) -> String {
    use std::io::Write;
    use std::process::{Command, Stdio};

    let opt_bin = if std::path::Path::new("/usr/bin/opt-18").exists() {
        "/usr/bin/opt-18"
    } else if std::path::Path::new("/usr/bin/opt").exists() {
        "/usr/bin/opt"
    } else {
        return ir.to_string();
    };

    let mut child = Command::new(opt_bin)
        .args(["-O2", "-S"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn();

    match child {
        Ok(mut c) => {
            if let Some(mut stdin) = c.stdin.take() {
                let _ = stdin.write_all(ir.as_bytes());
            }
            match c.wait_with_output() {
                Ok(out) if out.status.success() => {
                    String::from_utf8_lossy(&out.stdout).to_string()
                }
                _ => ir.to_string(),
            }
        }
        Err(_) => ir.to_string(),
    }
}
