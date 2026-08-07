use frontier::repl::run_repl;

fn main() {
    if let Err(e) = run_repl() {
        eprintln!("{}", e.message);
        std::process::exit(1);
    }
}
