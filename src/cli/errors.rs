use super::colors;
use frontier::FrontierError;

pub fn print_parse_error(err: &FrontierError) {
    colors::print_error(&format!(
        "Error [{}] at line {}, column {}",
        err.code, err.line, err.column
    ));
    eprintln!("  {}", err.message);
    print_contextual_help(&err.code);
}

pub fn print_io_error(context: &str, err: &std::io::Error) {
    colors::print_error(&format!("{context}: {err}"));
}

pub fn print_compile_error(message: &str) {
    colors::print_error(message);
    eprintln!("  Hint: run `frontier compile --help` for usage examples");
}

fn print_contextual_help(code: &str) {
    match code {
        "E-PARSE" => {
            eprintln!("  Help: check syntax against `frontier parse-v2 <file>`");
        }
        "E-DEPTH" => {
            eprintln!("  Help: reduce nesting depth (max 64 levels)");
        }
        "E-RESOLVE" => {
            eprintln!("  Help: run `frontier resolve <file>` to inspect symbols");
        }
        _ => {}
    }
}
