use crate::ast::*;
use crate::error::FrontierError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolveResult {
    pub node_symbols: HashMap<String, u32>,
    pub symbol_table: Vec<SymbolEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbolEntry {
    pub id: u32,
    pub name: String,
    pub kind: String,
    pub type_spec: TypeSpec,
    pub scope_id: u32,
}

struct Scope {
    id: u32,
    parent: Option<u32>,
    symbols: HashMap<String, u32>,
}

pub struct Resolver {
    scopes: Vec<Scope>,
    symbols: Vec<SymbolEntry>,
    node_symbols: HashMap<String, u32>,
    current_scope: u32,
    next_symbol_id: u32,
    next_scope_id: u32,
    node_counter: u32,
}

impl Resolver {
    pub fn new() -> Self {
        let root = Scope {
            id: 0,
            parent: None,
            symbols: HashMap::new(),
        };
        Self {
            scopes: vec![root],
            symbols: Vec::new(),
            node_symbols: HashMap::new(),
            current_scope: 0,
            next_symbol_id: 1,
            next_scope_id: 1,
            node_counter: 0,
        }
    }

    fn node_key(&mut self) -> String {
        self.node_counter += 1;
        format!("node_{}", self.node_counter)
    }

    fn enter_scope(&mut self) -> u32 {
        let id = self.next_scope_id;
        self.next_scope_id += 1;
        let parent = Some(self.current_scope);
        self.scopes.push(Scope {
            id,
            parent,
            symbols: HashMap::new(),
        });
        self.current_scope = id;
        id
    }

    fn exit_scope(&mut self) {
        if let Some(scope) = self.scopes.iter().find(|s| s.id == self.current_scope) {
            if let Some(parent) = scope.parent {
                self.current_scope = parent;
            }
        }
    }

    fn declare(
        &mut self,
        name: &str,
        kind: &str,
        type_spec: TypeSpec,
        line: usize,
        column: usize,
    ) -> Result<u32, FrontierError> {
        let scope = self
            .scopes
            .iter_mut()
            .find(|s| s.id == self.current_scope)
            .unwrap();
        if scope.symbols.contains_key(name) {
            return Err(FrontierError::resolve(
                "E-SHADOW",
                format!("Redeclaration of symbol '{}'", name),
                line,
                column,
            ));
        }
        let id = self.next_symbol_id;
        self.next_symbol_id += 1;
        scope.symbols.insert(name.to_string(), id);
        self.symbols.push(SymbolEntry {
            id,
            name: name.to_string(),
            kind: kind.to_string(),
            type_spec,
            scope_id: self.current_scope,
        });
        Ok(id)
    }

    fn resolve_name(
        &mut self,
        name: &str,
        line: usize,
        column: usize,
    ) -> Result<u32, FrontierError> {
        let mut scope_id = self.current_scope;
        loop {
            let scope = self.scopes.iter().find(|s| s.id == scope_id).unwrap();
            if let Some(&id) = scope.symbols.get(name) {
                return Ok(id);
            }
            if let Some(parent) = scope.parent {
                scope_id = parent;
            } else {
                return Err(FrontierError::resolve(
                    "E-UNDEF",
                    format!("Undefined symbol '{}'", name),
                    line,
                    column,
                ));
            }
        }
    }

    fn check_null_safety(&self, type_spec: &TypeSpec, line: usize, column: usize) -> Result<(), FrontierError> {
        match type_spec.annotation {
            TypeAnnotation::Required => Ok(()),
            TypeAnnotation::Optional => Err(FrontierError::resolve(
                "E-NULL",
                format!("Optional type '{}' requires null-safety check", type_spec.base),
                line,
                column,
            )),
            TypeAnnotation::None => Ok(()),
        }
    }

    pub fn resolve_program(&mut self, program: &Program) -> Result<ResolveResult, FrontierError> {
        for stmt in &program.statements {
            self.resolve_stmt(stmt)?;
        }
        Ok(ResolveResult {
            node_symbols: self.node_symbols.clone(),
            symbol_table: self.symbols.clone(),
        })
    }

    fn resolve_stmt(&mut self, stmt: &Stmt) -> Result<(), FrontierError> {
        match stmt {
            Stmt::LetDecl { name, type_spec, value, .. } => {
                self.resolve_expr(value)?;
                let id = self.declare(name, "variable", type_spec.clone(), 1, 1)?;
                let key = self.node_key();
                self.node_symbols.insert(key, id);
            }
            Stmt::FnDecl {
                name,
                params,
                return_type,
                body,
                ..
            } => {
                let fn_id = self.declare(name, "function", return_type.clone(), 1, 1)?;
                let key = self.node_key();
                self.node_symbols.insert(key, fn_id);
                self.enter_scope();
                for p in params {
                    let pid = self.declare(&p.name, "parameter", p.type_spec.clone(), 1, 1)?;
                    let pkey = self.node_key();
                    self.node_symbols.insert(pkey, pid);
                }
                for s in body {
                    self.resolve_stmt(s)?;
                }
                self.exit_scope();
            }
            Stmt::Return { value } => {
                if let Some(v) = value {
                    self.resolve_expr(v)?;
                }
            }
            Stmt::If {
                condition,
                then_block,
                else_block,
            } => {
                self.resolve_expr(condition)?;
                self.enter_scope();
                for s in then_block {
                    self.resolve_stmt(s)?;
                }
                self.exit_scope();
                if let Some(eb) = else_block {
                    self.enter_scope();
                    for s in eb {
                        self.resolve_stmt(s)?;
                    }
                    self.exit_scope();
                }
            }
            Stmt::Block { statements } => {
                self.enter_scope();
                for s in statements {
                    self.resolve_stmt(s)?;
                }
                self.exit_scope();
            }
            Stmt::Expr { expr } => {
                self.resolve_expr(expr)?;
            }
            Stmt::VersionDecl { .. } => {}
            Stmt::ImportDecl { alias, .. } => {
                let id = self.declare(
                    alias,
                    "imported",
                    TypeSpec {
                        base: "module".to_string(),
                        annotation: TypeAnnotation::None,
                    },
                    1,
                    1,
                )?;
                let key = self.node_key();
                self.node_symbols.insert(key, id);
            }
            Stmt::While { condition, body } => {
                self.resolve_expr(condition)?;
                self.enter_scope();
                for s in body {
                    self.resolve_stmt(s)?;
                }
                self.exit_scope();
            }
        }
        Ok(())
    }

    fn resolve_expr(&mut self, expr: &Expr) -> Result<(), FrontierError> {
        match expr {
            Expr::Identifier { name, .. } => {
                let id = self.resolve_name(name, 1, 1)?;
                let key = self.node_key();
                self.node_symbols.insert(key, id);
            }
            Expr::UnaryExpr { operand, .. } => self.resolve_expr(operand)?,
            Expr::BinaryExpr { left, right, .. } => {
                self.resolve_expr(left)?;
                self.resolve_expr(right)?;
            }
            Expr::CallExpr { callee, args } => {
                self.resolve_expr(callee)?;
                for a in args {
                    self.resolve_expr(a)?;
                }
            }
            Expr::FieldAccess { object, .. } => self.resolve_expr(object)?,
            Expr::RequiredExpr { operand } => self.resolve_expr(operand)?,
            Expr::Grouped { inner } => self.resolve_expr(inner)?,
            _ => {}
        }
        Ok(())
    }
}

pub fn resolve_program(program: &Program) -> Result<ResolveResult, FrontierError> {
    let mut resolver = Resolver::new();
    resolver.resolve_program(program)
}
