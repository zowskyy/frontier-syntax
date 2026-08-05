use crate::ast::{Program, Stmt};
use crate::error::FrontierError;
use std::fs;
use std::path::Path;

pub fn generate_docs(program: &Program, output_dir: &Path) -> Result<(), FrontierError> {
    fs::create_dir_all(output_dir).map_err(|e| FrontierError::parse("docs", &e.to_string(), 0, 0))?;

    let index = generate_index(program);
    let functions = generate_functions(program);
    let types = generate_types();

    fs::write(output_dir.join("index.md"), index).ok();
    fs::write(output_dir.join("functions.md"), functions).ok();
    fs::write(output_dir.join("types.md"), types).ok();

    Ok(())
}

fn generate_index(program: &Program) -> String {
    let mut s = String::from("# Frontier Syntax Documentation\n\n");
    s.push_str("Auto-generated API documentation.\n\n");
    s.push_str("## Overview\n\n");
    s.push_str("Frontier is a formally verifiable programming language.\n\n");
    s.push_str("## Modules\n\n");
    s.push_str("- [Functions](functions.md)\n");
    s.push_str("- [Types](types.md)\n\n");
    s.push_str(&format!("## Statements: {}\n\n", program.statements.len()));
    for stmt in &program.statements {
        if let Stmt::FnDecl { name, .. } = stmt {
            s.push_str(&format!("- `{}`\n", name));
        }
    }
    s
}

fn generate_functions(program: &Program) -> String {
    let mut s = String::from("# Functions\n\n");
    for stmt in &program.statements {
        if let Stmt::FnDecl { name, params, return_type, .. } = stmt {
            s.push_str(&format!("## fn `{}`\n\n", name));
            s.push_str(&format!("**Returns:** `{}`\n\n", return_type.base));
            s.push_str("### Parameters\n\n");
            if params.is_empty() {
                s.push_str("_None_\n\n");
            } else {
                for p in params {
                    s.push_str(&format!("- `{}`: `{}`\n", p.name, p.type_spec.base));
                }
                s.push('\n');
            }
        }
    }
    if !s.contains("## fn") {
        s.push_str("_No functions defined._\n");
    }
    s
}

fn generate_types() -> String {
    r#"# Types

| Type | Description |
|------|-------------|
| `int` | 64-bit signed integer |
| `float` | IEEE 754 double |
| `bool` | Boolean (`true` / `false`) |
| `string` | UTF-8 string (double-quoted) |
| `void` | No return value |

## Annotations

- `?` — Optional type (nullable)
- `!` — Required type (non-null assertion)
"#
    .to_string()
}
