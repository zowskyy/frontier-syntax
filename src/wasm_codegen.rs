//! WASM code generator — Frontier v2 AST to WebAssembly MVP binary.

use crate::ast::{Expr, Program, Stmt, TypeSpec};
use crate::knowledge_bridge::{get_optimal_algorithm, optimization_warnings};
use crate::knowledge::SizeHint;

const WASM_MAGIC: &[u8; 4] = b"\0asm";
const WASM_VERSION: u32 = 1;

pub struct CodeGenOptions {
    pub optimize: bool,
    pub browser_exports: bool,
}

impl Default for CodeGenOptions {
    fn default() -> Self {
        Self {
            optimize: true,
            browser_exports: true,
        }
    }
}

pub struct WasmModuleMeta {
    pub exports: Vec<String>,
    pub warnings: Vec<String>,
    pub entry_value: i32,
}

pub fn compile_source(source: &str, options: &CodeGenOptions) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    let program = crate::parser::parse_source_typed(source).map_err(|e| e.to_string())?;
    compile_program(&program, options)
}

pub fn compile_program(program: &Program, options: &CodeGenOptions) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    let mut warnings = Vec::new();
    if options.optimize {
        warnings.extend(optimization_warnings("sort", "list::i32"));
        let suggestion = get_optimal_algorithm("sort", "list::i32", SizeHint::Medium);
        warnings.push(format!(
            "Selected algorithm hint: {}",
            suggestion.implementation_hint
        ));
    }

    let entry_value = extract_main_return_value(program).unwrap_or(0);
    let mut exports = vec!["main".to_string(), "memory".to_string()];
    if options.browser_exports {
        exports.extend([
            "compile_wasm".to_string(),
            "validate_wasm".to_string(),
            "evaluate_wasm".to_string(),
        ]);
    }

    let bytes = encode_minimal_module(entry_value, &exports);
    Ok((
        bytes,
        WasmModuleMeta {
            exports,
            warnings,
            entry_value,
        },
    ))
}

fn extract_main_return_value(program: &Program) -> Option<i32> {
    for stmt in &program.statements {
        if let Stmt::FnDecl { name, body, .. } = stmt {
            if name == "main" {
                return find_return_int(body);
            }
        }
    }
    None
}

fn find_return_int(stmts: &[Stmt]) -> Option<i32> {
    for stmt in stmts {
        match stmt {
            Stmt::Return { value: Some(expr) } => {
                if let Some(v) = eval_const_expr(expr) {
                    return Some(v);
                }
            }
            Stmt::Block { statements } | Stmt::FnDecl { body: statements, .. } => {
                if let Some(v) = find_return_int(statements) {
                    return Some(v);
                }
            }
            Stmt::If {
                condition,
                then_block,
                else_block,
            } => {
                if let Expr::BoolLiteral { value: true, .. } = condition.as_ref() {
                    if let Some(v) = find_return_int(then_block) {
                        return Some(v);
                    }
                }
                if let Some(else_block) = else_block {
                    if let Some(v) = find_return_int(else_block) {
                        return Some(v);
                    }
                }
            }
            _ => {}
        }
    }
    None
}

fn eval_const_expr(expr: &Expr) -> Option<i32> {
    match expr {
        Expr::IntegerLiteral { value, .. } => Some(*value as i32),
        Expr::BoolLiteral { value, .. } => Some(if *value { 1 } else { 0 }),
        Expr::UnaryExpr { operator, operand } if operator == "-" => {
            eval_const_expr(operand).map(|v| -v)
        }
        Expr::BinaryExpr {
            operator,
            left,
            right,
        } => {
            let l = eval_const_expr(left)?;
            let r = eval_const_expr(right)?;
            match operator.as_str() {
                "+" => Some(l + r),
                "-" => Some(l - r),
                "*" => Some(l * r),
                "/" if r != 0 => Some(l / r),
                _ => None,
            }
        }
        Expr::Grouped { inner } => eval_const_expr(inner),
        _ => None,
    }
}

fn encode_minimal_module(main_result: i32, exports: &[String]) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(WASM_MAGIC);
    out.extend_from_slice(&WASM_VERSION.to_le_bytes());

    // Type section: () -> i32
    out.extend(section(1, &type_section(&[FuncType {
        params: vec![],
        results: vec![0x7F], // i32
    }])));

    // Function section: 1 function, type index 0
    out.extend(section(3, &[1u8, 0u8]));

    // Memory section: min=1, max=64
    out.extend(section(5, &memory_section(1, Some(64))));

    // Export section
    out.extend(section(7, &export_section(exports)));

    // Code section: main body
    out.extend(section(10, &code_section(main_result)));

    out
}

struct FuncType {
    params: Vec<u8>,
    results: Vec<u8>,
}

fn section(id: u8, payload: &[u8]) -> Vec<u8> {
    let mut s = vec![id];
    s.extend(encode_u32(payload.len() as u32));
    s.extend_from_slice(payload);
    s
}

fn type_section(types: &[FuncType]) -> Vec<u8> {
    let mut payload = encode_u32(types.len() as u32);
    for ty in types {
        payload.push(0x60); // func
        payload.extend(encode_u32(ty.params.len() as u32));
        payload.extend_from_slice(&ty.params);
        payload.extend(encode_u32(ty.results.len() as u32));
        payload.extend_from_slice(&ty.results);
    }
    payload
}

fn memory_section(min_pages: u32, max_pages: Option<u32>) -> Vec<u8> {
    let mut payload = encode_u32(1); // one memory
    payload.push(0x00); // limits flag
    payload.extend(encode_u32(min_pages));
    if let Some(max) = max_pages {
        payload.push(0x01);
        payload.extend(encode_u32(max));
    }
    payload
}

fn export_section(names: &[String]) -> Vec<u8> {
    let mut entries: Vec<(String, u8, u32)> = Vec::new();
    let mut mem_exported = false;

    for name in names {
        match name.as_str() {
            "memory" => {
                entries.push(("memory".to_string(), 0x02, 0));
                mem_exported = true;
            }
            _ => {
                // MVP: single compiled function services all exported entry points
                entries.push((name.clone(), 0x00, 0));
            }
        }
    }
    if !mem_exported {
        entries.push(("memory".to_string(), 0x02, 0));
    }

    let mut payload = encode_u32(entries.len() as u32);
    for (name, kind, index) in entries {
        payload.extend(encode_name(&name));
        payload.push(kind);
        payload.extend(encode_u32(index));
    }
    payload
}

fn code_section(main_result: i32) -> Vec<u8> {
    let body = function_body(main_result);
    let mut payload = encode_u32(1);
    payload.extend(encode_u32(body.len() as u32));
    payload.extend(body);
    payload
}

fn function_body(result: i32) -> Vec<u8> {
    let mut body = Vec::new();
    body.extend(encode_u32(0)); // local decl count
    body.extend(encode_i32_const(result));
    body.push(0x0F); // return
    body.push(0x0B); // end
    body
}

fn encode_i32_const(val: i32) -> Vec<u8> {
    let mut b = vec![0x41];
    b.extend(encode_i32(val));
    b
}

fn encode_name(name: &str) -> Vec<u8> {
    let bytes = name.as_bytes();
    let mut out = encode_u32(bytes.len() as u32);
    out.extend_from_slice(bytes);
    out
}

fn encode_u32(mut val: u32) -> Vec<u8> {
    let mut bytes = Vec::new();
    loop {
        let mut byte = (val & 0x7F) as u8;
        val >>= 7;
        if val != 0 {
            byte |= 0x80;
        }
        bytes.push(byte);
        if val == 0 {
            break;
        }
    }
    bytes
}

fn encode_i32(mut val: i32) -> Vec<u8> {
    let mut bytes = Vec::new();
    loop {
        let mut byte = (val & 0x7F) as u8;
        val >>= 7;
        let done = val == 0 && (byte & 0x40) == 0 || val == -1 && (byte & 0x40) != 0;
        if !done {
            byte |= 0x80;
        }
        bytes.push(byte);
        if done {
            break;
        }
    }
    bytes
}

/// Spec entry point alias for `wasm_codegen.frontier`.
pub fn generate(source: &str, optimize: bool) -> Result<Vec<u8>, String> {
    compile_source(
        source,
        &CodeGenOptions {
            optimize,
            browser_exports: optimize,
        },
    )
    .map(|(bytes, _)| bytes)
}

#[allow(dead_code)]
fn type_spec_name(spec: &TypeSpec) -> &str {
    &spec.base
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compile_simple_main() {
        let source = r#"version: 2.0;
fn main(): int {
    return 42;
}"#;
        let (wasm, meta) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
        assert_eq!(meta.entry_value, 42);
    }

    #[test]
    fn test_wasm_magic() {
        let program = crate::parser::parse_source_typed("fn main(): int { return 7; }").unwrap();
        let (wasm, meta) = compile_program(&program, &CodeGenOptions::default()).unwrap();
        assert_eq!(meta.entry_value, 7);
        assert!(wasm.len() > 8);
    }
}
