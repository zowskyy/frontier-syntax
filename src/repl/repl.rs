use crate::interpreter::{Interpreter, Value};
use crate::FrontierError;
use rustyline::error::ReadlineError;
use rustyline::DefaultEditor;

pub fn run_repl() -> Result<(), FrontierError> {
    let mut rl = DefaultEditor::new().map_err(|e| FrontierError::parse("repl", &e.to_string(), 0, 0))?;
    let mut interp = Interpreter::new();
    let mut buffer = String::new();

    println!("Frontier REPL v1.0.0 (type :quit to exit)");

    loop {
        let prompt = if buffer.is_empty() { "fr> " } else { "..> " };
        match rl.readline(prompt) {
            Ok(line) => {
                let _ = rl.add_history_entry(&line);
                if line.trim() == ":quit" {
                    break;
                }
                buffer.push_str(&line);
                buffer.push('\n');

                if !is_complete(&buffer) {
                    continue;
                }

                match interp.eval_source(&buffer) {
                    Ok(Some(val)) => println!("{}", val),
                    Ok(None) => {}
                    Err(e) => println!("{}", e.message),
                }
                buffer.clear();
            }
            Err(ReadlineError::Interrupted) | Err(ReadlineError::Eof) => break,
            Err(e) => {
                println!("Error: {}", e);
                break;
            }
        }
    }
    Ok(())
}

fn is_complete(source: &str) -> bool {
    let mut braces = 0i32;
    let mut parens = 0i32;
    let mut in_string = false;
    let mut escape = false;

    for ch in source.chars() {
        if escape {
            escape = false;
            continue;
        }
        if ch == '\\' && in_string {
            escape = true;
            continue;
        }
        if ch == '"' {
            in_string = !in_string;
            continue;
        }
        if in_string {
            continue;
        }
        match ch {
            '{' => braces += 1,
            '}' => braces -= 1,
            '(' => parens += 1,
            ')' => parens -= 1,
            _ => {}
        }
    }

    braces <= 0 && parens <= 0 && !source.trim().is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::interpreter::Interpreter;

    #[test]
    fn repl_eval_addition() {
        let mut interp = Interpreter::new();
        interp.eval_source("let x: int = 5;").unwrap();
        let result = interp.eval_source("x + 3;").unwrap();
        assert!(matches!(result, Some(Value::Int(8))));
    }
}
