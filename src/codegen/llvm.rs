use crate::ast::{Expr, Program, Stmt};
use crate::error::FrontierError;
use inkwell::context::Context;
use inkwell::module::Module;
use inkwell::types::IntType;
use inkwell::values::IntValue;
use inkwell::IntPredicate;
use std::collections::HashMap;
use std::path::Path;

pub struct Codegen<'ctx> {
    context: &'ctx Context,
    module: Module<'ctx>,
    i64_type: IntType<'ctx>,
    vars: HashMap<String, inkwell::values::PointerValue<'ctx>>,
    builder: Option<inkwell::builder::Builder<'ctx>>,
}

impl<'ctx> Codegen<'ctx> {
    pub fn new(context: &'ctx Context, module_name: &str) -> Self {
        let module = context.create_module(module_name);
        let i64_type = context.i64_type();
        Self {
            context,
            module,
            i64_type,
            vars: HashMap::new(),
            builder: None,
        }
    }

    pub fn module(&self) -> &Module<'ctx> {
        &self.module
    }

    pub fn generate(&mut self, program: &Program) -> Result<(), FrontierError> {
        for stmt in &program.statements {
            if let Stmt::FnDecl { name, params, return_type, body, .. } = stmt {
                if name == "main" {
                    self.gen_main(params, return_type, body)?;
                } else {
                    self.gen_function(name, params, return_type, body)?;
                }
            }
        }
        Ok(())
    }

    fn gen_main(
        &mut self,
        params: &[crate::ast::Param],
        return_type: &crate::ast::TypeSpec,
        body: &[Stmt],
    ) -> Result<(), FrontierError> {
        let fn_type = self.i64_type.fn_type(&[], false);
        let function = self.module.add_function("main", fn_type, None);
        let entry = self.context.append_basic_block(function, "entry");
        let builder = self.context.create_builder();
        builder.position_at_end(entry);
        self.builder = Some(builder);
        self.vars.clear();

        for p in params {
            let alloca = self.builder.as_ref().unwrap().build_alloca(self.i64_type, &p.name).unwrap();
            self.vars.insert(p.name.clone(), alloca);
        }

        let mut ret_val = self.i64_type.const_int(0, false);
        for stmt in body {
            if let Stmt::LetDecl { name, value, .. } = stmt {
                let val = self.gen_expr(value)?;
                let alloca = self.builder.as_ref().unwrap().build_alloca(self.i64_type, name).unwrap();
                self.builder.as_ref().unwrap().build_store(alloca, val).unwrap();
                self.vars.insert(name.clone(), alloca);
                ret_val = val;
            } else if let Some(v) = self.gen_stmt(stmt)? {
                ret_val = v;
            }
        }

        let _ = return_type;
        self.builder.as_ref().unwrap().build_return(Some(&ret_val)).unwrap();
        Ok(())
    }

    fn gen_function(
        &mut self,
        name: &str,
        params: &[crate::ast::Param],
        _return_type: &crate::ast::TypeSpec,
        body: &[Stmt],
    ) -> Result<(), FrontierError> {
        let param_types: Vec<inkwell::types::BasicMetadataTypeEnum> = params
            .iter()
            .map(|_| self.i64_type.into())
            .collect();
        let fn_type = self.i64_type.fn_type(&param_types, false);
        let function = self.module.add_function(name, fn_type, None);
        let entry = self.context.append_basic_block(function, "entry");
        let builder = self.context.create_builder();
        builder.position_at_end(entry);
        self.builder = Some(builder);
        self.vars.clear();

        for (i, p) in params.iter().enumerate() {
            let param_val = function.get_nth_param(i as u32).unwrap().into_int_value();
            let alloca = self.builder.as_ref().unwrap().build_alloca(self.i64_type, &p.name).unwrap();
            self.builder.as_ref().unwrap().build_store(alloca, param_val).unwrap();
            self.vars.insert(p.name.clone(), alloca);
        }

        let mut ret_val = self.i64_type.const_int(0, false);
        for stmt in body {
            if let Some(v) = self.gen_stmt(stmt)? {
                ret_val = v;
            }
        }
        self.builder.as_ref().unwrap().build_return(Some(&ret_val)).unwrap();
        Ok(())
    }

    fn gen_stmt(&mut self, stmt: &Stmt) -> Result<Option<IntValue<'ctx>>, FrontierError> {
        match stmt {
            Stmt::LetDecl { name, value, .. } => {
                let val = self.gen_expr(value)?;
                let alloca = self.builder.as_ref().unwrap().build_alloca(self.i64_type, name).unwrap();
                self.builder.as_ref().unwrap().build_store(alloca, val).unwrap();
                self.vars.insert(name.clone(), alloca);
                Ok(None)
            }
            Stmt::Return { value } => {
                let val = if let Some(v) = value {
                    self.gen_expr(v)?
                } else {
                    self.i64_type.const_int(0, false)
                };
                Ok(Some(val))
            }
            Stmt::If { condition, then_block, else_block } => {
                let cond = self.gen_expr(condition)?;
                let zero = self.i64_type.const_int(0, false);
                let cond_bool = self.builder.as_ref().unwrap()
                    .build_int_compare(IntPredicate::NE, cond, zero, "ifcond").unwrap();

                let function = self.builder.as_ref().unwrap().get_insert_block().unwrap()
                    .get_parent().unwrap();
                let then_bb = self.context.append_basic_block(function, "then");
                let else_bb = self.context.append_basic_block(function, "else");
                let merge_bb = self.context.append_basic_block(function, "ifcont");

                self.builder.as_ref().unwrap()
                    .build_conditional_branch(cond_bool, then_bb, else_bb).unwrap();

                self.builder.as_ref().unwrap().position_at_end(then_bb);
                for s in then_block {
                    self.gen_stmt(s)?;
                }
                self.builder.as_ref().unwrap().build_unconditional_branch(merge_bb).unwrap();

                self.builder.as_ref().unwrap().position_at_end(else_bb);
                if let Some(eb) = else_block {
                    for s in eb {
                        self.gen_stmt(s)?;
                    }
                }
                self.builder.as_ref().unwrap().build_unconditional_branch(merge_bb).unwrap();

                self.builder.as_ref().unwrap().position_at_end(merge_bb);
                Ok(None)
            }
            Stmt::Block { statements } => {
                for s in statements {
                    self.gen_stmt(s)?;
                }
                Ok(None)
            }
            Stmt::Expr { expr } => {
                let v = self.gen_expr(expr)?;
                Ok(Some(v))
            }
            Stmt::FnDecl { .. } => Ok(None),
        }
    }

    fn gen_expr(&mut self, expr: &Expr) -> Result<IntValue<'ctx>, FrontierError> {
        match expr {
            Expr::IntegerLiteral { value, .. } => {
                Ok(self.i64_type.const_int(*value as u64, false))
            }
            Expr::BoolLiteral { value, .. } => {
                Ok(self.i64_type.const_int(if *value { 1 } else { 0 }, false))
            }
            Expr::NullLiteral { .. } => Ok(self.i64_type.const_int(0, false)),
            Expr::Identifier { name, .. } => {
                let ptr = self.vars.get(name).ok_or_else(|| {
                    FrontierError::resolve("E-UNDEF", format!("Undefined symbol '{}'", name), 1, 1)
                })?;
                let val = self.builder.as_ref().unwrap().build_load(self.i64_type, *ptr, name).unwrap().into_int_value();
                Ok(val)
            }
            Expr::UnaryExpr { operator, operand } => {
                let v = self.gen_expr(operand)?;
                match operator.as_str() {
                    "-" => Ok(self.builder.as_ref().unwrap().build_int_neg(v, "neg").unwrap()),
                    "!" | "~" => {
                        let zero = self.i64_type.const_int(0, false);
                        Ok(self.builder.as_ref().unwrap()
                            .build_int_compare(IntPredicate::EQ, v, zero, "not").unwrap())
                    }
                    _ => Err(FrontierError::parse("unary op", operator, 0, 0)),
                }
            }
            Expr::BinaryExpr { operator, left, right } => {
                let l = self.gen_expr(left)?;
                let r = self.gen_expr(right)?;
                let b = self.builder.as_ref().unwrap();
                match operator.as_str() {
                    "+" => Ok(b.build_int_add(l, r, "add").unwrap()),
                    "-" => Ok(b.build_int_sub(l, r, "sub").unwrap()),
                    "*" => Ok(b.build_int_mul(l, r, "mul").unwrap()),
                    "/" => Ok(b.build_int_signed_div(l, r, "div").unwrap()),
                    "%" => Ok(b.build_int_signed_rem(l, r, "mod").unwrap()),
                    "<" => Ok(b.build_int_compare(IntPredicate::SLT, l, r, "lt").unwrap()),
                    ">" => Ok(b.build_int_compare(IntPredicate::SGT, l, r, "gt").unwrap()),
                    "<=" => Ok(b.build_int_compare(IntPredicate::SLE, l, r, "le").unwrap()),
                    ">=" => Ok(b.build_int_compare(IntPredicate::SGE, l, r, "ge").unwrap()),
                    "==" => Ok(b.build_int_compare(IntPredicate::EQ, l, r, "eq").unwrap()),
                    "!=" => Ok(b.build_int_compare(IntPredicate::NE, l, r, "ne").unwrap()),
                    "&&" => {
                        let zero = self.i64_type.const_int(0, false);
                        let lz = b.build_int_compare(IntPredicate::NE, l, zero, "l").unwrap();
                        let rz = b.build_int_compare(IntPredicate::NE, r, zero, "r").unwrap();
                        Ok(b.build_int_mul(lz, rz, "and").unwrap())
                    }
                    "||" => {
                        let zero = self.i64_type.const_int(0, false);
                        let lz = b.build_int_compare(IntPredicate::NE, l, zero, "l").unwrap();
                        let rz = b.build_int_compare(IntPredicate::NE, r, zero, "r").unwrap();
                        let sum = b.build_int_add(lz, rz, "or_sum").unwrap();
                        Ok(b.build_int_compare(IntPredicate::NE, sum, zero, "or").unwrap())
                    }
                    _ => Err(FrontierError::parse("binary op", operator, 0, 0)),
                }
            }
            Expr::StringLiteral { value, .. } => {
                let hash: i64 = value.bytes().map(|b| b as i64).sum();
                Ok(self.i64_type.const_int(hash as u64, false))
            }
            Expr::Grouped { inner } => self.gen_expr(inner),
            Expr::FieldAccess { object, .. } => self.gen_expr(object),
            Expr::RequiredExpr { operand } => self.gen_expr(operand),
            Expr::CallExpr { callee, args } => {
                if let Expr::Identifier { name, .. } = callee.as_ref() {
                    let fn_val = self.module.get_function(name).ok_or_else(|| {
                        FrontierError::resolve("E-UNDEF", format!("Undefined function '{}'", name), 1, 1)
                    })?;
                    let arg_vals: Vec<inkwell::values::BasicMetadataValueEnum> = args
                        .iter()
                        .map(|a| self.gen_expr(a).map(|v| v.into()))
                        .collect::<Result<Vec<_>, _>>()?;
                    let call = self.builder.as_ref().unwrap()
                        .build_call(fn_val, &arg_vals, "call").unwrap();
                    Ok(call.try_as_basic_value().left().unwrap().into_int_value())
                } else {
                    Err(FrontierError::parse("callee", "identifier", 0, 0))
                }
            }
            _ => Err(FrontierError::parse("expr", "unsupported", 0, 0)),
        }
    }
}

pub fn generate_module(program: &Program) -> Result<String, FrontierError> {
    let context = Context::create();
    let mut cg = Codegen::new(&context, "frontier");
    cg.generate(program)?;
    Ok(cg.module().to_string())
}

pub fn compile_to_object(program: &Program, output_path: &Path) -> Result<(), FrontierError> {
    use inkwell::targets::{CodeModel, FileType, InitializationConfig, RelocMode, Target, TargetMachine};
    use inkwell::OptimizationLevel;

    let context = Context::create();
    let mut cg = Codegen::new(&context, "frontier");
    cg.generate(program)?;

    Target::initialize_all(&InitializationConfig::default());
    let triple = TargetMachine::get_default_triple();
    let target = Target::from_triple(&triple).map_err(|e| FrontierError::parse("llvm", &e.to_string(), 0, 0))?;
    let machine = target
        .create_target_machine(&triple, "generic", "", OptimizationLevel::Aggressive, RelocMode::Default, CodeModel::Default)
        .ok_or_else(|| FrontierError::parse("llvm", "target machine", 0, 0))?;

    machine
        .write_to_file(cg.module(), FileType::Object, output_path)
        .map_err(|e| FrontierError::parse("object", &e.to_string(), 0, 0))?;
    Ok(())
}

pub fn frontier_type_to_llvm(base: &str) -> &'static str {
    match base {
        "int" => "i64",
        "bool" => "i1",
        "float" => "double",
        "string" => "i8*",
        "void" => "void",
        _ => "i64",
    }
}
