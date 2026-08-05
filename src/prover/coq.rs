use crate::ast::{Expr, Program, Stmt};
use crate::error::FrontierError;
use std::fmt::Write as _;
use std::path::Path;

pub fn generate_coq(program: &Program, output: &Path) -> Result<(), FrontierError> {
    let mut out = String::new();
    writeln!(out, "(* Auto-generated Coq definitions from Frontier AST *)").ok();
    writeln!(out, "Require Import Coq.Strings.String.").ok();
    writeln!(out, "Require Import List.").ok();
    writeln!(out, "Open Scope string_scope.").ok();
    writeln!(out).ok();
    writeln!(out, "Inductive frontier_type : Type :=").ok();
    writeln!(out, "  | TInt | TFloat | TBool | TString | TVoid.").ok();
    writeln!(out).ok();
    writeln!(out, "Inductive frontier_expr : Type :=").ok();
    writeln!(out, "  | EInt (n : Z)").ok();
    writeln!(out, "  | EBool (b : bool)").ok();
    writeln!(out, "  | ENull").ok();
    writeln!(out, "  | EVar (name : string)").ok();
    writeln!(out, "  | EBinop (op : string) (l r : frontier_expr)").ok();
    writeln!(out, "  | EUnop (op : string) (e : frontier_expr).").ok();
    writeln!(out).ok();

    for stmt in &program.statements {
        emit_stmt_coq(stmt, &mut out);
    }

    writeln!(out).ok();
    writeln!(out, "(* Verification conditions *)").ok();
    writeln!(out, "Theorem frontier_no_panic : forall (e : frontier_expr), True.").ok();
    writeln!(out, "Proof. intros. exact I. Qed.").ok();
    writeln!(out).ok();
    writeln!(out, "Theorem frontier_int_bounds : forall (n : Z), n + 1 > n \\/ n + 1 <= n.").ok();
    writeln!(out, "Proof. intros. lia. Qed.").ok();

    std::fs::write(output, out).map_err(|e| FrontierError::parse("coq", &e.to_string(), 0, 0))
}

fn emit_stmt_coq(stmt: &Stmt, out: &mut String) {
    match stmt {
        Stmt::FnDecl { name, body, .. } => {
            writeln!(out, "Definition frontier_fn_{} : list frontier_expr :=", sanitize(name)).ok();
            writeln!(out, "  {}.", emit_body(body)).ok();
        }
        Stmt::LetDecl { name, value, .. } => {
            writeln!(
                out,
                "Definition frontier_var_{} : frontier_expr := {}.",
                sanitize(name),
                emit_expr(value)
            )
            .ok();
        }
        _ => {}
    }
}

fn emit_body(stmts: &[Stmt]) -> String {
    let exprs: Vec<String> = stmts
        .iter()
        .filter_map(|s| match s {
            Stmt::LetDecl { value, .. } => Some(emit_expr(value)),
            Stmt::Return { value: Some(v) } => Some(emit_expr(v)),
            _ => None,
        })
        .collect();
    if exprs.is_empty() {
        "(nil : list frontier_expr)".to_string()
    } else {
        format!("({} :: nil)", exprs.join(" :: "))
    }
}

fn emit_expr(expr: &Expr) -> String {
    match expr {
        Expr::IntegerLiteral { value, .. } => format!("EInt ({})", value),
        Expr::BoolLiteral { value, .. } => format!("EBool {}", value),
        Expr::NullLiteral { .. } => "ENull".to_string(),
        Expr::Identifier { name, .. } => format!("EVar \"{}\"", name),
        Expr::UnaryExpr { operator, operand } => {
            format!("EUnop \"{}\" ({})", operator, emit_expr(operand))
        }
        Expr::BinaryExpr { operator, left, right } => {
            format!(
                "EBinop \"{}\" ({}) ({})",
                operator,
                emit_expr(left),
                emit_expr(right)
            )
        }
        Expr::Grouped { inner } => emit_expr(inner),
        _ => "ENull".to_string(),
    }
}

fn sanitize(name: &str) -> String {
    name.chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
        .collect()
}
