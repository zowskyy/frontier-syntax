use crate::ast::{AstExpr, AstNode, AstStmt};
use crate::parser::dex_type_to_java;

pub struct JavaPrettyPrinter {
    pub indent: usize,
    pub use_java21: bool,
}

impl Default for JavaPrettyPrinter {
    fn default() -> Self {
        Self {
            indent: 4,
            use_java21: true,
        }
    }
}

impl JavaPrettyPrinter {
    pub fn print_class(&self, class_name: &str, methods: &[AstNode]) -> String {
        let java_name = dex_type_to_java(class_name);
        let mut out = String::new();
        out.push_str("public class ");
        out.push_str(&java_name);
        out.push_str(" {\n");
        for method in methods {
            out.push_str(&self.print_method(method));
            out.push('\n');
        }
        out.push_str("}\n");
        out
    }

    pub fn print_method(&self, node: &AstNode) -> String {
        let mut out = String::new();
        let pad = " ".repeat(self.indent);
        out.push_str(&pad);
        out.push_str("public void ");
        let method_name = node.name.split("::").last().unwrap_or("method");
        out.push_str(method_name);
        out.push_str("() {\n");
        for stmt in &node.body {
            out.push_str(&self.print_stmt(stmt, self.indent + self.indent));
        }
        out.push_str(&pad);
        out.push_str("}\n");
        out
    }

    fn print_stmt(&self, stmt: &AstStmt, depth: usize) -> String {
        let pad = " ".repeat(depth);
        match stmt {
            AstStmt::Block(stmts) => {
                let mut out = String::new();
                for s in stmts {
                    out.push_str(&self.print_stmt(s, depth));
                }
                out
            }
            AstStmt::If { cond, then_branch, else_branch } => {
                let mut out = format!("{pad}if ({}) {{\n", self.print_expr(cond));
                out.push_str(&self.print_stmt(then_branch, depth + self.indent));
                if let Some(el) = else_branch {
                    out.push_str(&format!("{pad}}} else {{\n"));
                    out.push_str(&self.print_stmt(el, depth + self.indent));
                }
                out.push_str(&format!("{pad}}}\n"));
                out
            }
            AstStmt::While { cond, body } => {
                let mut out = format!("{pad}while ({}) {{\n", self.print_expr(cond));
                out.push_str(&self.print_stmt(body, depth + self.indent));
                out.push_str(&format!("{pad}}}\n"));
                out
            }
            AstStmt::For { init, cond, update, body } => {
                let init_s = init
                    .as_ref()
                    .map(|i| self.print_stmt(i, 0).trim().trim_end_matches(';').to_string())
                    .unwrap_or_default();
                let cond_s = cond
                    .as_ref()
                    .map(|c| self.print_expr(c))
                    .unwrap_or_else(|| "true".into());
                let update_s = update
                    .as_ref()
                    .map(|u| self.print_stmt(u, 0).trim().trim_end_matches(';').to_string())
                    .unwrap_or_default();
                let mut out = format!("{pad}for ({init_s}; {cond_s}; {update_s}) {{\n");
                out.push_str(&self.print_stmt(body, depth + self.indent));
                out.push_str(&format!("{pad}}}\n"));
                out
            }
            AstStmt::Switch { discriminant, cases, default } => {
                if self.use_java21 {
                    self.print_switch_expr(discriminant, cases, default, depth)
                } else {
                    self.print_switch_stmt(discriminant, cases, default, depth)
                }
            }
            AstStmt::Assign { name, value } => {
                format!("{pad}int {name} = {};\n", self.print_expr(value))
            }
            AstStmt::Return(Some(v)) => format!("{pad}return {};\n", self.print_expr(v)),
            AstStmt::ReturnVoid | AstStmt::Return(None) => format!("{pad}return;\n"),
            AstStmt::Expr(e) => format!("{pad}{};\n", self.print_expr(e)),
            AstStmt::Nop => String::new(),
        }
    }

    fn print_switch_expr(
        &self,
        discriminant: &AstExpr,
        cases: &[(i32, AstStmt)],
        default: &Option<Box<AstStmt>>,
        depth: usize,
    ) -> String {
        let pad = " ".repeat(depth);
        let mut out = format!(
            "{pad}int _sw = {};\n{pad}String result = switch (_sw) {{\n",
            self.print_expr(discriminant)
        );
        for (key, stmt) in cases {
            out.push_str(&format!("{pad}    case {key} -> \"{}\";\n", stmt_label(stmt)));
        }
        if let Some(d) = default {
            out.push_str(&format!(
                "{pad}    default -> \"{}\";\n",
                stmt_label(d)
            ));
        }
        out.push_str(&format!("{pad}}};\n"));
        out
    }

    fn print_switch_stmt(
        &self,
        discriminant: &AstExpr,
        cases: &[(i32, AstStmt)],
        default: &Option<Box<AstStmt>>,
        depth: usize,
    ) -> String {
        let pad = " ".repeat(depth);
        let mut out = format!("{pad}switch ({}) {{\n", self.print_expr(discriminant));
        for (key, stmt) in cases {
            out.push_str(&format!("{pad}    case {key}:\n"));
            out.push_str(&self.print_stmt(stmt, depth + self.indent));
            out.push_str(&format!("{pad}        break;\n"));
        }
        if let Some(d) = default {
            out.push_str(&format!("{pad}    default:\n"));
            out.push_str(&self.print_stmt(d, depth + self.indent));
        }
        out.push_str(&format!("{pad}}}\n"));
        out
    }

    fn print_expr(&self, expr: &AstExpr) -> String {
        match expr {
            AstExpr::LiteralI32(v) => v.to_string(),
            AstExpr::LiteralString(s) => format!("\"{s}\""),
            AstExpr::Variable(v) => v.clone(),
            AstExpr::Binary { op, left, right } => {
                let op_s = match op {
                    crate::ast::BinOp::Add => "+",
                    crate::ast::BinOp::Sub => "-",
                    crate::ast::BinOp::Mul => "*",
                    crate::ast::BinOp::Eq => "==",
                    crate::ast::BinOp::Ne => "!=",
                    crate::ast::BinOp::Lt => "<",
                    crate::ast::BinOp::Gt => ">",
                };
                format!("({} {} {})", self.print_expr(left), op_s, self.print_expr(right))
            }
            AstExpr::Call { name, args } => {
                let args_s: Vec<String> = args.iter().map(|a| self.print_expr(a)).collect();
                if name.contains("lambda") || name.starts_with("invoke@") {
                    format!(
                        "() -> {{ {}({}); }}",
                        name,
                        args_s.join(", ")
                    )
                } else {
                    format!("{}({})", name, args_s.join(", "))
                }
            }
            AstExpr::Ternary { cond, then_expr, else_expr } => format!(
                "({}) ? {} : {}",
                self.print_expr(cond),
                self.print_expr(then_expr),
                self.print_expr(else_expr)
            ),
        }
    }
}

fn stmt_label(stmt: &AstStmt) -> &'static str {
    match stmt {
        AstStmt::Nop => "nop",
        AstStmt::ReturnVoid => "ret",
        _ => "case",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ast::{AstNode, AstStmt};

    #[test]
    fn test_print_method() {
        let node = AstNode {
            name: "LFoo;::bar".into(),
            body: vec![AstStmt::ReturnVoid],
        };
        let pp = JavaPrettyPrinter::default();
        let java = pp.print_method(&node);
        assert!(java.contains("public void bar"));
        assert!(java.contains("return;"));
    }

    #[test]
    fn test_java21_switch() {
        let pp = JavaPrettyPrinter::default();
        let stmt = AstStmt::Switch {
            discriminant: AstExpr::Variable("x".into()),
            cases: vec![(1, AstStmt::Nop)],
            default: None,
        };
        let out = pp.print_stmt(&stmt, 4);
        assert!(out.contains("switch"));
    }
}
