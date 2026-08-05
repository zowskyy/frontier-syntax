use super::colors;
use notify::{Config, RecommendedWatcher, RecursiveMode, Watcher};
use signal_hook::{consts::SIGINT, iterator::Signals};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc;
use std::time::Duration;

static RUNNING: AtomicBool = AtomicBool::new(true);

pub fn start_watch(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let path = args
        .get(2)
        .map(|s| s.as_str())
        .unwrap_or("examples");

    let watch_path = Path::new(path);
    if !watch_path.exists() {
        return Err(format!("Watch path does not exist: {path}").into());
    }

    setup_signal_handler()?;

    let (tx, rx) = mpsc::channel();
    let mut watcher = RecommendedWatcher::new(
        move |res| {
            if let Ok(event) = res {
                let _ = tx.send(event);
            }
        },
        Config::default().with_poll_interval(Duration::from_secs(1)),
    )?;

    watcher.watch(watch_path, RecursiveMode::Recursive)?;

    colors::print_success(&format!(
        "👀 Watching {} for changes (Ctrl+C to stop)",
        watch_path.display()
    ));

    let compile_args = build_watch_compile_args(args);

    while RUNNING.load(Ordering::SeqCst) {
        match rx.recv_timeout(Duration::from_millis(500)) {
            Ok(event) => {
                if let notify::EventKind::Modify(_) | notify::EventKind::Create(_) = event.kind {
                    for changed in &event.paths {
                        if is_frontier_file(changed) {
                            colors::print_progress(&format!(
                                "🔄 Change detected: {}",
                                changed.display()
                            ));
                            recompile_file(changed, &compile_args);
                        }
                    }
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => continue,
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
        }
    }

    Ok(())
}

fn setup_signal_handler() -> Result<(), Box<dyn std::error::Error>> {
    let mut signals = Signals::new([SIGINT])?;
    std::thread::spawn(move || {
        for _ in signals.forever() {
            RUNNING.store(false, Ordering::SeqCst);
            println!("\n👋 Stopping watch...");
            std::process::exit(0);
        }
    });
    Ok(())
}

fn is_frontier_file(path: &Path) -> bool {
    path.extension()
        .and_then(|e| e.to_str())
        .is_some_and(|ext| ext == "fr" || ext == "frontier")
}

fn build_watch_compile_args(args: &[String]) -> Vec<String> {
    let mut compile_args = vec!["frontier".to_string(), "compile".to_string()];
    let mut i = 3;
    while i < args.len() {
        if args[i] == "--" {
            i += 1;
            compile_args.extend(args[i..].iter().cloned());
            break;
        }
        i += 1;
    }
    if compile_args.len() == 2 {
        compile_args.push("-t".to_string());
        compile_args.push("wasm".to_string());
        compile_args.push("-O".to_string());
    }
    compile_args
}

fn recompile_file(path: &Path, compile_args: &[String]) {
    let mut args = compile_args.to_vec();
    args.push(path.to_string_lossy().to_string());
    super::compile::run_compile(&args);
}
