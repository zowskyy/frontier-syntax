use crate::ast::{AstExpr, AstNode, AstStmt, BinOp};
use crate::ir::{SsaFunction, SsaInstruction, SsaOperand};
use std::collections::HashMap;

pub struct AstOptimizer;

impl AstOptimizer {
    pub fn rewrite_ast(mut ast: AstNode) -> AstNode {
        ast.body = ast
            .body
            .into_iter()
            .map(Self::rewrite_stmt)
            .filter(|s| !matches!(s, AstStmt::Block(ref v) if v.is_empty()))
            .collect();
        ast.body = Self::simplify_blocks(ast.body);
        ast
    }

    fn rewrite_stmt(stmt: AstStmt) -> AstStmt {
        match stmt {
            AstStmt::Block(stmts) => {
                let rewritten: Vec<AstStmt> = stmts.into_iter().map(Self::rewrite_stmt).collect();
                AstStmt::Block(Self::simplify_blocks(rewritten))
            }
            AstStmt::If {
                cond,
                then_branch,
                else_branch,
            } => AstStmt::If {
                cond: Self::fold_expr(cond),
                then_branch: Box::new(Self::rewrite_stmt(*then_branch)),
                else_branch: else_branch.map(|e| Box::new(Self::rewrite_stmt(*e))),
            },
            AstStmt::While { cond, body } => AstStmt::While {
                cond: Self::fold_expr(cond),
                body: Box::new(Self::rewrite_stmt(*body)),
            },
            AstStmt::For { init, cond, update, body } => AstStmt::For {
                init: init.map(|i| Box::new(Self::rewrite_stmt(*i))),
                cond: cond.map(Self::fold_expr),
                update: update.map(|u| Box::new(Self::rewrite_stmt(*u))),
                body: Box::new(Self::rewrite_stmt(*body)),
            },
            AstStmt::Switch {
                discriminant,
                cases,
                default,
            } => AstStmt::Switch {
                discriminant: Self::fold_expr(discriminant),
                cases: cases
                    .into_iter()
                    .map(|(k, s)| (k, Self::rewrite_stmt(s)))
                    .collect(),
                default: default.map(|d| Box::new(Self::rewrite_stmt(*d))),
            },
            AstStmt::Assign { name, value } => AstStmt::Assign {
                name,
                value: Self::fold_expr(value),
            },
            AstStmt::Return(v) => AstStmt::Return(v.map(Self::fold_expr)),
            AstStmt::Expr(e) => AstStmt::Expr(Self::fold_expr(e)),
            other => other,
        }
    }

    fn fold_expr(expr: AstExpr) -> AstExpr {
        match expr {
            AstExpr::Binary { op, left, right } => {
                let left = Self::fold_expr(*left);
                let right = Self::fold_expr(*right);
                if let (AstExpr::LiteralI32(a), AstExpr::LiteralI32(b)) = (&left, &right) {
                    let folded = match op {
                        BinOp::Add => a + b,
                        BinOp::Sub => a - b,
                        BinOp::Mul => a * b,
                        BinOp::Eq => if a == b { 1 } else { 0 },
                        BinOp::Ne => if a != b { 1 } else { 0 },
                        BinOp::Lt => if a < b { 1 } else { 0 },
                        BinOp::Gt => if a > b { 1 } else { 0 },
                    };
                    return AstExpr::LiteralI32(folded);
                }
                AstExpr::Binary {
                    op,
                    left: Box::new(left),
                    right: Box::new(right),
                }
            }
            AstExpr::Ternary { cond, then_expr, else_expr } => {
                let cond = Self::fold_expr(*cond);
                if let AstExpr::LiteralI32(v) = &cond {
                    return if *v != 0 {
                        Self::fold_expr(*then_expr)
                    } else {
                        Self::fold_expr(*else_expr)
                    };
                }
                AstExpr::Ternary {
                    cond: Box::new(cond),
                    then_expr: Box::new(Self::fold_expr(*then_expr)),
                    else_expr: Box::new(Self::fold_expr(*else_expr)),
                }
            }
            other => other,
        }
    }

    fn simplify_blocks(stmts: Vec<AstStmt>) -> Vec<AstStmt> {
        let mut out = Vec::new();
        for stmt in stmts {
            match stmt {
                AstStmt::Block(inner) if inner.is_empty() => continue,
                AstStmt::Block(inner) => out.push(AstStmt::Block(Self::simplify_blocks(inner))),
                other => out.push(other),
            }
        }
        out
    }

    pub fn flatten_ternaries(expr: AstExpr) -> AstExpr {
        match expr {
            AstExpr::Ternary { cond, then_expr, else_expr } => {
                let then_e = Self::flatten_ternaries(*then_expr);
                let else_e = Self::flatten_ternaries(*else_expr);
                if let AstExpr::Ternary { .. } = else_e {
                    return AstExpr::Ternary {
                        cond,
                        then_expr: Box::new(then_e),
                        else_expr: Box::new(else_e),
                    };
                }
                AstExpr::Ternary {
                    cond,
                    then_expr: Box::new(then_e),
                    else_expr: Box::new(else_e),
                }
            }
            AstExpr::Binary { op, left, right } => AstExpr::Binary {
                op,
                left: Box::new(Self::flatten_ternaries(*left)),
                right: Box::new(Self::flatten_ternaries(*right)),
            },
            other => other,
        }
    }
}

pub struct FixedPointOptimizer {
    pub max_iterations: usize,
}

impl Default for FixedPointOptimizer {
    fn default() -> Self {
        Self {
            max_iterations: 5,
        }
    }
}

impl FixedPointOptimizer {
    pub fn run_until_fixed_point(
        &self,
        mut func: SsaFunction,
        mut ast: AstNode,
    ) -> (SsaFunction, AstNode, usize) {
        let mut iterations = 0;
        loop {
            iterations += 1;
            func = Self::optimize_ir(func);
            ast = crate::ast::PatternMatcher::match_ir_to_ast(&func);
            ast = AstOptimizer::rewrite_ast(ast);
            let constants = Self::extract_constants_from_ast(&ast);
            let (new_func, changed) = Self::apply_constants_to_ir(func, &constants);
            func = new_func;
            if !changed || iterations >= self.max_iterations {
                break;
            }
        }
        (func, ast, iterations)
    }

    fn optimize_ir(mut func: SsaFunction) -> SsaFunction {
        for block in func.blocks.values_mut() {
            block.instructions.retain(|insn| !is_dead(insn));
        }
        func
    }

    fn extract_constants_from_ast(ast: &AstNode) -> HashMap<String, i32> {
        let mut map = HashMap::new();
        for stmt in &ast.body {
            collect_constants(stmt, &mut map);
        }
        map
    }

    fn apply_constants_to_ir(
        mut func: SsaFunction,
        constants: &HashMap<String, i32>,
    ) -> (SsaFunction, bool) {
        let mut changed = false;
        for block in func.blocks.values_mut() {
            for insn in &mut block.instructions {
                if let SsaInstruction::Move { dest, src } = insn {
                    if let SsaOperand::Register(r) = src {
                        let key = format!("v{r}");
                        if let Some(v) = constants.get(&key) {
                            *insn = SsaInstruction::Const {
                                dest: *dest,
                                value: SsaOperand::ConstI32(*v),
                            };
                            changed = true;
                        }
                    }
                }
            }
        }
        (func, changed)
    }
}

fn is_dead(insn: &SsaInstruction) -> bool {
    matches!(insn, SsaInstruction::Nop)
}

fn collect_constants(stmt: &AstStmt, map: &mut HashMap<String, i32>) {
    match stmt {
        AstStmt::Assign { name, value } => {
            if let AstExpr::LiteralI32(v) = value {
                map.insert(name.clone(), *v);
            }
        }
        AstStmt::Block(stmts) => stmts.iter().for_each(|s| collect_constants(s, map)),
        AstStmt::If { then_branch, else_branch, .. } => {
            collect_constants(then_branch, map);
            if let Some(e) = else_branch {
                collect_constants(e, map);
            }
        }
        AstStmt::While { body, .. } => collect_constants(body, map),
        AstStmt::For { init, body, update, .. } => {
            if let Some(i) = init {
                collect_constants(i, map);
            }
            collect_constants(body, map);
            if let Some(u) = update {
                collect_constants(u, map);
            }
        }
        _ => {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ir::{BasicBlock, SsaFunction};
    use std::collections::HashMap;

    #[test]
    fn test_constant_fold() {
        let expr = AstExpr::Binary {
            op: BinOp::Add,
            left: Box::new(AstExpr::LiteralI32(2)),
            right: Box::new(AstExpr::LiteralI32(3)),
        };
        let folded = AstOptimizer::fold_expr(expr);
        assert!(matches!(folded, AstExpr::LiteralI32(5)));
    }

    #[test]
    fn test_flatten_ternary() {
        let expr = AstExpr::Ternary {
            cond: Box::new(AstExpr::LiteralI32(1)),
            then_expr: Box::new(AstExpr::LiteralI32(1)),
            else_expr: Box::new(AstExpr::Ternary {
                cond: Box::new(AstExpr::LiteralI32(0)),
                then_expr: Box::new(AstExpr::LiteralI32(2)),
                else_expr: Box::new(AstExpr::LiteralI32(3)),
            }),
        };
        let flat = AstOptimizer::flatten_ternaries(expr);
        assert!(matches!(flat, AstExpr::Ternary { .. }));
    }

    #[test]
    fn test_fixed_point() {
        let mut blocks = HashMap::new();
        blocks.insert(
            0,
            BasicBlock {
                id: 0,
                start_pc: 0,
                end_pc: 1,
                instructions: vec![
                    SsaInstruction::Const {
                        dest: 1,
                        value: SsaOperand::ConstI32(42),
                    },
                    SsaInstruction::Nop,
                    SsaInstruction::ReturnVoid,
                ],
                successors: vec![],
                predecessors: vec![],
            },
        );
        let func = SsaFunction {
            name: "fp".into(),
            registers: 2,
            blocks,
            entry: 0,
            phi_count: 0,
        };
        let ast = AstNode {
            name: "fp".into(),
            body: vec![AstStmt::Assign {
                name: "v1".into(),
                value: AstExpr::LiteralI32(42),
            }],
        };
        let opt = FixedPointOptimizer::default();
        let (func, ast, iters) = opt.run_until_fixed_point(func, ast);
        assert!(iters >= 1);
        assert!(!func.blocks.is_empty());
        assert!(!ast.body.is_empty());
    }

    #[test]
    fn test_remove_empty_blocks() {
        let stmts = vec![
            AstStmt::Block(vec![]),
            AstStmt::ReturnVoid,
        ];
        let simplified = AstOptimizer::simplify_blocks(stmts);
        assert_eq!(simplified.len(), 1);
    }
}
