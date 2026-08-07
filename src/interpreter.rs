use crate::ast::{Expr, Stmt, TypeAnnotation};
use crate::error::FrontierError;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub enum Value {
    Int(i64),
    Float(f64),
    Bool(bool),
    String(String),
    Null,
}

pub struct Interpreter {
    scopes: Vec<HashMap<String, Value>>,
}

impl Interpreter {
    pub fn new() -> Self {
        Self {
            scopes: vec![HashMap::new()],
        }
    }

    pub fn eval_source(&mut self, source: &str) -> Result<Option<Value>, FrontierError> {
        let program = crate::parse_program(source, 64)?;
        let mut last = None;
        for stmt in &program.statements {
            last = self.eval_stmt(stmt)?;
        }
        Ok(last)
    }

    pub fn eval_stmt(&mut self, stmt: &Stmt) -> Result<Option<Value>, FrontierError> {
        match stmt {
            Stmt::LetDecl { name, type_spec, value, .. } => {
                let val = self.eval_expr(value)?;
                self.check_type(&val, type_spec)?;
                self.declare(name, val.clone())?;
                Ok(Some(val))
            }
            Stmt::Return { value } => {
                if let Some(v) = value {
                    Ok(Some(self.eval_expr(v)?))
                } else {
                    Ok(Some(Value::Null))
                }
            }
            Stmt::Expr { expr } => Ok(Some(self.eval_expr(expr)?)),
            Stmt::If { condition, then_block, else_block } => {
                let cond = self.eval_expr(condition)?;
                let truthy = value_truthy(&cond);
                if truthy {
                    self.push_scope();
                    let mut last = None;
                    for s in then_block {
                        last = self.eval_stmt(s)?;
                    }
                    self.pop_scope();
                    Ok(last)
                } else if let Some(eb) = else_block {
                    self.push_scope();
                    let mut last = None;
                    for s in eb {
                        last = self.eval_stmt(s)?;
                    }
                    self.pop_scope();
                    Ok(last)
                } else {
                    Ok(None)
                }
            }
            Stmt::Block { statements } => {
                self.push_scope();
                let mut last = None;
                for s in statements {
                    last = self.eval_stmt(s)?;
                }
                self.pop_scope();
                Ok(last)
            }
            Stmt::FnDecl { .. } => Ok(None),
        }
    }

    pub fn eval_expr(&mut self, expr: &Expr) -> Result<Value, FrontierError> {
        match expr {
            Expr::IntegerLiteral { value, .. } => Ok(Value::Int(*value)),
            Expr::FloatLiteral { value, .. } => Ok(Value::Float(*value)),
            Expr::StringLiteral { value, .. } => Ok(Value::String(value.clone())),
            Expr::BoolLiteral { value, .. } => Ok(Value::Bool(*value)),
            Expr::NullLiteral { .. } => Ok(Value::Null),
            Expr::Identifier { name, .. } => self
                .lookup(name)
                .ok_or_else(|| FrontierError::resolve(
                    "E-404",
                    format!("Symbol '{}' not found", name),
                    1,
                    1,
                )),
            Expr::UnaryExpr { operator, operand } => {
                let v = self.eval_expr(operand)?;
                match operator.as_str() {
                    "-" => match v {
                        Value::Int(n) => Ok(Value::Int(-n)),
                        Value::Float(n) => Ok(Value::Float(-n)),
                        _ => Err(FrontierError::parse("unary -", "number", 0, 0)),
                    },
                    "!" | "~" => Ok(Value::Bool(!value_truthy(&v))),
                    _ => Err(FrontierError::parse("unary", operator, 0, 0)),
                }
            }
            Expr::BinaryExpr { operator, left, right } => {
                let l = self.eval_expr(left)?;
                let r = self.eval_expr(right)?;
                eval_binary(operator, &l, &r)
            }
            Expr::Grouped { inner } => self.eval_expr(inner),
            _ => Err(FrontierError::parse("expr", "unsupported in interpreter", 0, 0)),
        }
    }

    fn declare(&mut self, name: &str, val: Value) -> Result<(), FrontierError> {
        let scope = self.scopes.last_mut().unwrap();
        if scope.contains_key(name) {
            return Err(FrontierError::resolve(
                "E-SHADOW",
                format!("Redeclaration of '{}'", name),
                1,
                1,
            ));
        }
        scope.insert(name.to_string(), val);
        Ok(())
    }

    fn lookup(&self, name: &str) -> Option<Value> {
        for scope in self.scopes.iter().rev() {
            if let Some(v) = scope.get(name) {
                return Some(v.clone());
            }
        }
        None
    }

    fn push_scope(&mut self) {
        self.scopes.push(HashMap::new());
    }

    fn pop_scope(&mut self) {
        if self.scopes.len() > 1 {
            self.scopes.pop();
        }
    }

    fn check_type(&self, val: &Value, spec: &crate::ast::TypeSpec) -> Result<(), FrontierError> {
        match spec.annotation {
            TypeAnnotation::Required => Ok(()),
            TypeAnnotation::Optional => {
                if matches!(val, Value::Null) {
                    Ok(())
                } else {
                    Ok(())
                }
            }
            TypeAnnotation::None => Ok(()),
        }
    }
}

fn value_truthy(v: &Value) -> bool {
    match v {
        Value::Int(n) => *n != 0,
        Value::Float(n) => *n != 0.0,
        Value::Bool(b) => *b,
        Value::String(s) => !s.is_empty(),
        Value::Null => false,
    }
}

fn eval_binary(op: &str, l: &Value, r: &Value) -> Result<Value, FrontierError> {
    match (op, l, r) {
        ("+", Value::Int(a), Value::Int(b)) => Ok(Value::Int(a + b)),
        ("-", Value::Int(a), Value::Int(b)) => Ok(Value::Int(a - b)),
        ("*", Value::Int(a), Value::Int(b)) => Ok(Value::Int(a * b)),
        ("/", Value::Int(a), Value::Int(b)) => Ok(Value::Int(a / b)),
        ("%", Value::Int(a), Value::Int(b)) => Ok(Value::Int(a % b)),
        ("^", Value::Int(a), Value::Int(b)) => Ok(Value::Int(a.pow(*b as u32))),
        ("<", Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a < b)),
        (">", Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a > b)),
        ("<=", Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a <= b)),
        (">=", Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a >= b)),
        ("==", a, b) => Ok(Value::Bool(values_equal(a, b))),
        ("!=", a, b) => Ok(Value::Bool(!values_equal(a, b))),
        ("&&", a, b) => Ok(Value::Bool(value_truthy(a) && value_truthy(b))),
        ("||", a, b) => Ok(Value::Bool(value_truthy(a) || value_truthy(b))),
        _ => Err(FrontierError::parse("binary", op, 0, 0)),
    }
}

fn values_equal(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Int(x), Value::Int(y)) => x == y,
        (Value::Bool(x), Value::Bool(y)) => x == y,
        (Value::String(x), Value::String(y)) => x == y,
        (Value::Null, Value::Null) => true,
        _ => false,
    }
}

impl std::fmt::Display for Value {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Value::Int(n) => write!(f, "{}", n),
            Value::Float(n) => write!(f, "{}", n),
            Value::Bool(b) => write!(f, "{}", b),
            Value::String(s) => write!(f, "{}", s),
            Value::Null => write!(f, "null"),
        }
    }
}
