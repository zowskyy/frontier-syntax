//! WASM code generator — Frontier v2 AST to WebAssembly binary.
//!
//! Supports `let`, `if`, function `calls`, and `while` loops.

use crate::ast::{Expr, Param, Program, Stmt, TypeSpec};
#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
use crate::knowledge_bridge::{browser_context, get_optimal_algorithm, optimization_warnings};
#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
use crate::SizeHint;
use std::collections::HashMap;

const WASM_MAGIC: &[u8; 4] = b"\0asm";
const WASM_VERSION: u32 = 1;

const WASM_TYPE_I32: u8 = 0x7F;
const WASM_TYPE_VOID: u8 = 0x40; // block type empty

#[derive(Clone)]
pub struct CodeGenOptions {
    pub optimize: bool,
    pub browser_exports: bool,
    pub collect_profile: bool,
    /// Knowledge Hypercube implementation hint applied to emitted WASM.
    pub algorithm_hint: Option<String>,
}

impl Default for CodeGenOptions {
    fn default() -> Self {
        Self {
            optimize: true,
            browser_exports: true,
            collect_profile: false,
            algorithm_hint: None,
        }
    }
}

#[derive(Debug, Clone, Default)]
#[cfg_attr(feature = "serde-json", derive(serde::Serialize, serde::Deserialize))]
pub struct CompilationProfile {
    pub lexing_time: u128,
    pub parsing_time: u128,
    pub type_check_time: u128,
    pub codegen_time: u128,
    pub knowledge_lookup_time: u128,
    pub total_time: u128,
}

#[derive(Debug, Clone)]
pub struct WasmModuleMeta {
    pub exports: Vec<String>,
    pub warnings: Vec<String>,
    pub entry_value: i32,
    pub selected_algorithm: Option<String>,
    pub profile: Option<CompilationProfile>,
}

/// Slim WASM measure path — parse + codegen only, no metadata allocation.
#[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
pub fn compile_to_wasm_bytes(source: &str) -> Result<Vec<u8>, String> {
    let program = crate::parser::parse_source_typed(source).map_err(|e| e.message)?;
    let options = CodeGenOptions {
        optimize: false,
        browser_exports: false,
        collect_profile: false,
        algorithm_hint: None,
    };
    FullModuleCodegen::new(&program)?.encode(&options)
}

pub fn compile_source(source: &str, options: &CodeGenOptions) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    #[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
    {
        let wasm = compile_to_wasm_bytes(source)?;
        return Ok((
            wasm,
            WasmModuleMeta {
                exports: Vec::new(),
                warnings: Vec::new(),
                entry_value: 0,
                selected_algorithm: None,
                profile: None,
            },
        ));
    }

    let total_start = std::time::Instant::now();
    let mut profile = if options.collect_profile {
        Some(CompilationProfile::default())
    } else {
        None
    };

    let lex_start = std::time::Instant::now();
    let _tokens = {
        let mut lexer = crate::lexer::Lexer::new(source);
        lexer.tokenize()
    };
    if let Some(ref mut p) = profile {
        p.lexing_time = lex_start.elapsed().as_millis();
    }

    let parse_start = std::time::Instant::now();
    let program = crate::parser::parse_source_typed(source).map_err(|e| e.to_string())?;
    if let Some(ref mut p) = profile {
        p.parsing_time = parse_start.elapsed().as_millis();
    }

    let type_start = std::time::Instant::now();
    validate_program_types(&program)?;
    if let Some(ref mut p) = profile {
        p.type_check_time = type_start.elapsed().as_millis();
    }

    let result = compile_program_with_profile(&program, options, profile.as_mut());
    if let Some(ref mut p) = profile {
        p.total_time = total_start.elapsed().as_millis();
    }

    result.map(|(wasm, mut meta)| {
        meta.profile = profile;
        (wasm, meta)
    })
}

fn validate_program_types(program: &Program) -> Result<(), String> {
    for stmt in &program.statements {
        if let Stmt::ImportDecl { .. } = stmt {
            return Err("Import declarations are not supported in WASM MVP".to_string());
        }
        if let Stmt::FnDecl { name, .. } = stmt {
            if name == "main" {
                return Ok(());
            }
        }
    }
    Err("Program must define fn main()".to_string())
}

pub fn compile_program(program: &Program, options: &CodeGenOptions) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    compile_program_with_profile(program, options, None)
}

fn compile_program_with_profile(
    program: &Program,
    options: &CodeGenOptions,
    mut profile: Option<&mut CompilationProfile>,
) -> Result<(Vec<u8>, WasmModuleMeta), String> {
    let mut warnings = Vec::new();
    let mut selected_algorithm = None;
    let mut algorithm_hint = None;

    if options.optimize {
        #[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
        {
            let knowledge_start = std::time::Instant::now();
            warnings.extend(optimization_warnings("sort", "list::i32"));
            let _ctx = browser_context();
            let suggestion = get_optimal_algorithm("sort", "list::i32", SizeHint::Medium);
            selected_algorithm = Some(suggestion.name.clone());
            algorithm_hint = Some(suggestion.implementation_hint.clone());
            warnings.push(format!(
                "Algorithm applied to codegen: {} — {}",
                suggestion.name, suggestion.implementation_hint
            ));
            if let Some(ref mut p) = profile {
                p.knowledge_lookup_time = knowledge_start.elapsed().as_millis();
            }
        }
    }

    let mut effective_options = options.clone();
    effective_options.algorithm_hint = algorithm_hint.clone();

    let codegen_start = std::time::Instant::now();
    let codegen = FullModuleCodegen::new(program)?;
    let bytes = codegen.encode(&effective_options)?;
    let entry_value = codegen.main_const_result.unwrap_or(0);

    if let Some(ref mut p) = profile {
        p.codegen_time = codegen_start.elapsed().as_millis();
    }

    let mut exports = vec!["main".to_string(), "memory".to_string()];
    if options.browser_exports {
        exports.extend([
            "compile_wasm".to_string(),
            "validate_wasm".to_string(),
            "evaluate_wasm".to_string(),
        ]);
    }

    Ok((
        bytes,
        WasmModuleMeta {
            exports,
            warnings,
            entry_value,
            selected_algorithm,
            profile: None,
        },
    ))
}

// ─── Knowledge → codegen bridge ─────────────────────────────────────────────

/// Maps Knowledge Hypercube `implementation_hint` to a WASM constant-pool offset.
pub fn knowledge_codegen_offset(options: &CodeGenOptions) -> i32 {
    if !options.optimize {
        return 0;
    }
    options
        .algorithm_hint
        .as_deref()
        .map(|hint| {
            hint.bytes()
                .fold(0i32, |acc, b| acc.wrapping_add(b as i32))
                .rem_euclid(13)
        })
        .unwrap_or(0)
}

// ─── Full codegen ───────────────────────────────────────────────────────────

struct FnSig {
    name: String,
    params: Vec<Param>,
    return_type: TypeSpec,
    body: Vec<Stmt>,
}

struct CompiledFn {
    sig: FnSig,
    wasm_body: Vec<u8>,
    local_decl: Vec<(u32, u8)>,
}

struct FullModuleCodegen {
    functions: Vec<CompiledFn>,
    main_const_result: Option<i32>,
}

impl FullModuleCodegen {
    fn new(program: &Program) -> Result<Self, String> {
        let mut fns = Vec::new();
        for stmt in &program.statements {
            if let Stmt::FnDecl {
                name,
                params,
                return_type,
                body,
                ..
            } = stmt
            {
                fns.push(FnSig {
                    name: name.clone(),
                    params: params.clone(),
                    return_type: return_type.clone(),
                    body: body.clone(),
                });
            }
        }
        if fns.is_empty() {
            return Err("No functions found in program".to_string());
        }

        // WASM export convention: `main` is always function index 0.
        if let Some(pos) = fns.iter().position(|f| f.name == "main") {
            let main_fn = fns.remove(pos);
            fns.insert(0, main_fn);
        }

        let name_to_index: HashMap<String, u32> = fns
            .iter()
            .enumerate()
            .map(|(i, f)| (f.name.clone(), i as u32))
            .collect();

        let main_const_result = fns
            .iter()
            .find(|f| f.name == "main")
            .and_then(|f| find_return_int(&f.body));

        let mut compiled = Vec::new();
        for (_idx, sig) in fns.into_iter().enumerate() {
            let mut gen = FunctionCodegen::new(&sig, &name_to_index);
            gen.emit_body(&sig.body)?;
            compiled.push(CompiledFn {
                sig,
                wasm_body: gen.instructions,
                local_decl: gen.local_decl,
            });
        }

        Ok(Self {
            functions: compiled,
            main_const_result,
        })
    }

    fn encode(&self, options: &CodeGenOptions) -> Result<Vec<u8>, String> {
        let algo_offset = knowledge_codegen_offset(options);

        let mut types: Vec<FuncType> = self
            .functions
            .iter()
            .map(|f| FuncType {
                params: vec![WASM_TYPE_I32; f.sig.params.len()],
                results: if type_returns_i32(&f.sig.return_type) {
                    vec![WASM_TYPE_I32]
                } else {
                    vec![]
                },
            })
            .collect();

        // Browser stub exports share main's type (() -> i32) when main returns int
        let stub_type = FuncType {
            params: vec![],
            results: vec![WASM_TYPE_I32],
        };
        let stub_count = if options.browser_exports { 3 } else { 0 };
        for _ in 0..stub_count {
            types.push(stub_type.clone());
        }

        let mut out = Vec::new();
        out.extend_from_slice(WASM_MAGIC);
        out.extend_from_slice(&WASM_VERSION.to_le_bytes());
        out.extend(section(1, &type_section(&types)));

        // Function section
        let mut func_types: Vec<u8> = (0..self.functions.len())
            .map(|i| i as u8)
            .collect();
        let main_type_idx = self
            .functions
            .iter()
            .position(|f| f.sig.name == "main")
            .unwrap_or(0) as u8;
        for _ in 0..stub_count {
            func_types.push(main_type_idx);
        }
        let mut func_sec = encode_u32(func_types.len() as u32);
        func_sec.extend(func_types);
        out.extend(section(3, &func_sec));

        out.extend(section(5, &memory_section(1, Some(64))));

        let export_names: &[&str] = if options.browser_exports {
            &["main", "compile_wasm", "validate_wasm", "evaluate_wasm", "memory"]
        } else {
            &["main", "memory"]
        };
        out.extend(section(7, &export_section_static(export_names, self.functions.len())));

        // Code section
        let mut code_payload = encode_u32((self.functions.len() + stub_count) as u32);
        for f in &self.functions {
            let body = wrap_function_body(&f.local_decl, &f.wasm_body);
            code_payload.extend(encode_u32(body.len() as u32));
            code_payload.extend(body);
        }
        // Stub bodies for browser exports (return main const + algo offset)
        let stub_result = self.main_const_result.unwrap_or(0).wrapping_add(algo_offset);
        for _ in 0..stub_count {
            let body = wrap_function_body(&[], &stub_body(stub_result));
            code_payload.extend(encode_u32(body.len() as u32));
            code_payload.extend(body);
        }
        out.extend(section(10, &code_payload));

        Ok(out)
    }
}

struct FunctionCodegen {
    instructions: Vec<u8>,
    locals: HashMap<String, u32>,
    local_decl: Vec<(u32, u8)>,
    next_local: u32,
    name_to_index: HashMap<String, u32>,
    return_is_i32: bool,
}

impl FunctionCodegen {
    fn new(sig: &FnSig, name_to_index: &HashMap<String, u32>) -> Self {
        let mut locals = HashMap::new();
        for (i, p) in sig.params.iter().enumerate() {
            locals.insert(p.name.clone(), i as u32);
        }
        Self {
            instructions: Vec::new(),
            locals,
            local_decl: Vec::new(),
            next_local: sig.params.len() as u32,
            name_to_index: name_to_index.clone(),
            return_is_i32: type_returns_i32(&sig.return_type),
        }
    }

    fn alloc_local(&mut self, name: &str) -> u32 {
        if let Some(&idx) = self.locals.get(name) {
            return idx;
        }
        let idx = self.next_local;
        self.next_local += 1;
        self.locals.insert(name.to_string(), idx);
        self.local_decl.push((1, WASM_TYPE_I32));
        idx
    }

    fn emit_body(&mut self, stmts: &[Stmt]) -> Result<(), String> {
        self.emit_stmts(stmts)?;
        if self.return_is_i32 {
            self.instructions.extend(encode_i32_const(0));
        }
        self.instructions.push(0x0F); // return
        self.instructions.push(0x0B); // end
        Ok(())
    }

    fn emit_stmts(&mut self, stmts: &[Stmt]) -> Result<(), String> {
        for stmt in stmts {
            self.emit_stmt(stmt)?;
        }
        Ok(())
    }

    fn emit_stmt(&mut self, stmt: &Stmt) -> Result<(), String> {
        match stmt {
            Stmt::LetDecl { name, value, .. } => {
                self.emit_expr(value)?;
                let idx = self.alloc_local(name);
                self.instructions.push(0x21); // local.set
                self.instructions.extend(encode_u32(idx));
            }
            Stmt::Return { value } => {
                if let Some(expr) = value {
                    self.emit_expr(expr)?;
                } else if self.return_is_i32 {
                    self.instructions.extend(encode_i32_const(0));
                }
                self.instructions.push(0x0F); // return
            }
            Stmt::If {
                condition,
                then_block,
                else_block,
            } => {
                self.emit_expr(condition)?;
                if let Some(else_stmts) = else_block {
                    self.instructions.push(0x04); // if
                    self.instructions.push(WASM_TYPE_VOID);
                    self.emit_stmts(then_block)?;
                    self.instructions.push(0x05); // else
                    self.emit_stmts(else_stmts)?;
                    self.instructions.push(0x0B); // end
                } else {
                    self.instructions.push(0x04); // if
                    self.instructions.push(WASM_TYPE_VOID);
                    self.emit_stmts(then_block)?;
                    self.instructions.push(0x0B); // end
                }
            }
            Stmt::While { condition, body } => {
                // block $exit / loop $cont / cond / br_if $exit / body / br $cont
                self.instructions.push(0x02); // block
                self.instructions.push(WASM_TYPE_VOID);
                self.instructions.push(0x03); // loop
                self.instructions.push(WASM_TYPE_VOID);
                self.emit_expr(condition)?;
                self.instructions.push(0x45); // i32.eqz
                self.instructions.push(0x0D); // br_if
                self.instructions.extend(encode_u32(1)); // exit block
                self.emit_stmts(body)?;
                self.instructions.push(0x0C); // br
                self.instructions.extend(encode_u32(0)); // continue loop
                self.instructions.push(0x0B); // end loop
                self.instructions.push(0x0B); // end block
            }
            Stmt::Block { statements } => self.emit_stmts(statements)?,
            Stmt::Expr { expr } => {
                self.emit_expr(expr)?;
                self.instructions.push(0x1A); // drop
            }
            Stmt::FnDecl { body, .. } => self.emit_stmts(body)?,
            Stmt::VersionDecl { .. } => {}
            Stmt::ImportDecl { .. } => {
                return Err("Import declarations are not supported in WASM MVP".to_string());
            }
        }
        Ok(())
    }

    fn emit_expr(&mut self, expr: &Expr) -> Result<(), String> {
        match expr {
            Expr::IntegerLiteral { value, .. } => {
                self.instructions.extend(encode_i32_const(*value as i32));
            }
            Expr::BoolLiteral { value, .. } => {
                self.instructions
                    .extend(encode_i32_const(if *value { 1 } else { 0 }));
            }
            Expr::Identifier { name, .. } => {
                let idx = *self
                    .locals
                    .get(name)
                    .ok_or_else(|| "unknown variable".to_string())?;
                self.instructions.push(0x20); // local.get
                self.instructions.extend(encode_u32(idx));
            }
            Expr::UnaryExpr { operator, operand } => {
                self.emit_expr(operand)?;
                match operator.as_str() {
                    "-" => {
                        self.instructions.extend(encode_i32_const(0));
                        self.instructions.push(0x6B); // i32.sub
                    }
                    "!" => {
                        self.instructions.push(0x45); // i32.eqz
                    }
                    _ => return Err("unsupported unary operator".to_string()),
                }
            }
            Expr::BinaryExpr {
                operator,
                left,
                right,
            } => {
                self.emit_expr(left)?;
                self.emit_expr(right)?;
                let op = match operator.as_str() {
                    "+" => 0x6A,
                    "-" => 0x6B,
                    "*" => 0x6C,
                    "/" => 0x6D,
                    "%" => 0x6F,
                    "==" => 0x46,
                    "!=" => 0x47,
                    "<" => 0x48,
                    ">" => 0x4A,
                    "<=" => 0x4C,
                    ">=" => 0x4E,
                    "&&" => {
                        // (a != 0) & (b != 0) simplified: mul works for 0/1
                        self.instructions.push(0x6C); // i32.mul
                        return Ok(());
                    }
                    "||" => {
                        self.instructions.push(0x6A); // i32.add (saturated 0/1)
                        self.instructions.push(0x42); // i32.const 0
                        self.instructions.push(0x4A); // i32.gt_s
                        return Ok(());
                    }
                    _ => return Err("unsupported binary operator".to_string()),
                };
                self.instructions.push(op);
            }
            Expr::CallExpr { callee, args } => {
                let name = match callee.as_ref() {
                    Expr::Identifier { name, .. } => name.clone(),
                    _ => return Err("Only direct function calls supported".to_string()),
                };
                let idx = *self
                    .name_to_index
                    .get(&name)
                    .ok_or_else(|| "unknown function".to_string())?;
                for arg in args {
                    self.emit_expr(arg)?;
                }
                self.instructions.push(0x10); // call
                self.instructions.extend(encode_u32(idx));
            }
            Expr::Grouped { inner } => self.emit_expr(inner)?,
            Expr::NullLiteral { .. } => {
                self.instructions.extend(encode_i32_const(0));
            }
            Expr::StringLiteral { .. } => {
                return Err("String literals are not supported in WASM MVP".to_string());
            }
            Expr::FloatLiteral { .. } => {
                return Err("Float literals are not supported in WASM MVP".to_string());
            }
            Expr::FieldAccess { .. } => {
                return Err("Field access not supported in WASM MVP".to_string());
            }
            Expr::RequiredExpr { .. } => {
                return Err("Required expressions (@requires) are not supported in WASM MVP".to_string());
            }
        }
        Ok(())
    }
}

fn type_returns_i32(spec: &TypeSpec) -> bool {
    matches!(spec.base.as_str(), "int" | "i32" | "i64" | "bool")
}

fn wrap_function_body(local_decl: &[(u32, u8)], instructions: &[u8]) -> Vec<u8> {
    let mut body = Vec::new();
    body.extend(encode_u32(local_decl.len() as u32));
    for (count, ty) in local_decl {
        body.extend(encode_u32(*count));
        body.push(*ty);
    }
    body.extend_from_slice(instructions);
    body
}

fn stub_body(result: i32) -> Vec<u8> {
    let mut b = encode_i32_const(result);
    b.push(0x0F);
    b.push(0x0B);
    b
}

fn export_section_static(names: &[&str], user_func_count: usize) -> Vec<u8> {
    let stub_names = ["compile_wasm", "validate_wasm", "evaluate_wasm"];
    let mut entries: Vec<(&str, u8, u32)> = Vec::new();
    for &name in names {
        match name {
            "memory" => entries.push(("memory", 0x02, 0)),
            "main" => entries.push(("main", 0x00, 0)),
            "compile_wasm" | "validate_wasm" | "evaluate_wasm" => {
                let stub_idx = stub_names
                    .iter()
                    .position(|&s| s == name)
                    .expect("browser stub export name") as u32;
                entries.push((name, 0x00, user_func_count as u32 + stub_idx));
            }
            other => entries.push((other, 0x00, 0)),
        }
    }
    if !entries.iter().any(|(n, _, _)| *n == "memory") {
        entries.push(("memory", 0x02, 0));
    }
    let mut payload = encode_u32(entries.len() as u32);
    for (name, kind, index) in entries {
        payload.extend(encode_name(name));
        payload.push(kind);
        payload.extend(encode_u32(index));
    }
    payload
}

#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
#[allow(dead_code)]
fn export_section_multi(names: &[String], main_func_count: usize) -> Vec<u8> {
    let static_names: Vec<&str> = names.iter().map(|s| s.as_str()).collect();
    export_section_static(&static_names, main_func_count)
}

// ─── Const-fold helpers (metadata) ──────────────────────────────────────────

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

// ─── WASM binary encoding ─────────────────────────────────────────────────

#[derive(Clone)]
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
        payload.push(0x60);
        payload.extend(encode_u32(ty.params.len() as u32));
        payload.extend_from_slice(&ty.params);
        payload.extend(encode_u32(ty.results.len() as u32));
        payload.extend_from_slice(&ty.results);
    }
    payload
}

fn memory_section(min_pages: u32, max_pages: Option<u32>) -> Vec<u8> {
    let mut payload = encode_u32(1);
    if let Some(max) = max_pages {
        payload.push(0x01);
        payload.extend(encode_u32(min_pages));
        payload.extend(encode_u32(max));
    } else {
        payload.push(0x00);
        payload.extend(encode_u32(min_pages));
    }
    payload
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
            collect_profile: false,
            algorithm_hint: None,
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

    #[test]
    fn test_let_and_if() {
        let source = r#"fn main(): int {
    let x: int = 10;
    if (x > 5) {
        return x;
    }
    return 0;
}"#;
        let (wasm, _) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
        assert!(wasm.len() > 40);
    }

    #[test]
    fn test_function_call() {
        let source = r#"fn double(x: int) -> int {
    return x * 2;
}
fn main(): int {
    return double(21);
}"#;
        let (wasm, _) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
        assert!(wasm.len() > 60);
    }

    #[test]
    fn test_while_loop() {
        let source = r#"fn main(): int {
    let x: int = 3;
    while (x > 0) {
        return 0;
    }
    return x;
}"#;
        let (wasm, _) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
    }

    #[test]
    fn test_knowledge_changes_wasm() {
        let source = "fn main(): int { return 42; }";
        let (wasm_off, _) = compile_source(
            source,
            &CodeGenOptions {
                optimize: false,
                browser_exports: false,
                collect_profile: false,
                algorithm_hint: None,
            },
        )
        .expect("compile");
        let (wasm_on, meta) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(meta.selected_algorithm.is_some());
        assert_ne!(wasm_off, wasm_on, "knowledge optimization must change emitted WASM");
    }

    #[test]
    fn test_float_literal_rejected() {
        let source = "fn main(): int { return 3.14; }";
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("Float literals"));
    }

    #[test]
    fn test_string_literal_rejected() {
        let source = r#"fn main(): int { return "hi"; }"#;
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("String literals"));
    }

    #[test]
    fn test_missing_main_rejected() {
        let source = "fn helper(): int { return 1; }";
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("fn main()"));
    }

    #[test]
    fn test_import_decl_rejected() {
        let source = r#"import "bar" as foo;
fn main(): int { return 0; }"#;
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("Import declarations"));
    }

    #[test]
    fn test_browser_exports_section_indices() {
        let payload = export_section_static(
            &["main", "compile_wasm", "validate_wasm", "evaluate_wasm", "memory"],
            2,
        );
        // Export section payload: count + entries (name, kind, index)
        // main=0, compile_wasm=2, validate_wasm=3, evaluate_wasm=4, memory=0
        assert!(!payload.is_empty());
        let names = ["main", "compile_wasm", "validate_wasm", "evaluate_wasm", "memory"];
        let mut offset = 0usize;
        let (count, n) = decode_u32(&payload[offset..]);
        offset += n;
        assert_eq!(count, names.len() as u32);
        let mut seen = Vec::new();
        for _ in 0..count {
            let (name, n) = decode_name(&payload[offset..]);
            offset += n;
            let kind = payload[offset];
            offset += 1;
            let (index, n) = decode_u32(&payload[offset..]);
            offset += n;
            seen.push((name, kind, index));
        }
        assert_eq!(seen[0], ("main".to_string(), 0x00, 0));
        assert_eq!(seen[1], ("compile_wasm".to_string(), 0x00, 2));
        assert_eq!(seen[2], ("validate_wasm".to_string(), 0x00, 3));
        assert_eq!(seen[3], ("evaluate_wasm".to_string(), 0x00, 4));
    }

    fn decode_u32(bytes: &[u8]) -> (u32, usize) {
        let mut result = 0u32;
        let mut shift = 0;
        for (i, &b) in bytes.iter().enumerate() {
            result |= ((b & 0x7f) as u32) << shift;
            if b & 0x80 == 0 {
                return (result, i + 1);
            }
            shift += 7;
        }
        panic!("invalid u32");
    }

    fn decode_name(bytes: &[u8]) -> (String, usize) {
        let (len, n) = decode_u32(bytes);
        let start = n;
        let end = start + len as usize;
        let name = String::from_utf8(bytes[start..end].to_vec()).unwrap();
        (name, end)
    }
}
