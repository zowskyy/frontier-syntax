use crate::ir::{BasicBlock, IfCondition, SsaFunction, SsaInstruction, SsaOperand};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AstExpr {
    LiteralI32(i32),
    LiteralString(String),
    Variable(String),
    Binary {
        op: BinOp,
        left: Box<AstExpr>,
        right: Box<AstExpr>,
    },
    Call {
        name: String,
        args: Vec<AstExpr>,
    },
    Ternary {
        cond: Box<AstExpr>,
        then_expr: Box<AstExpr>,
        else_expr: Box<AstExpr>,
    },
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Eq,
    Ne,
    Lt,
    Gt,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AstStmt {
    Block(Vec<AstStmt>),
    If {
        cond: AstExpr,
        then_branch: Box<AstStmt>,
        else_branch: Option<Box<AstStmt>>,
    },
    While {
        cond: AstExpr,
        body: Box<AstStmt>,
    },
    For {
        init: Option<Box<AstStmt>>,
        cond: Option<AstExpr>,
        update: Option<Box<AstStmt>>,
        body: Box<AstStmt>,
    },
    Switch {
        discriminant: AstExpr,
        cases: Vec<(i32, AstStmt)>,
        default: Option<Box<AstStmt>>,
    },
    Assign {
        name: String,
        value: AstExpr,
    },
    Return(Option<AstExpr>),
    ReturnVoid,
    Expr(AstExpr),
    Nop,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AstNode {
    pub name: String,
    pub body: Vec<AstStmt>,
}

pub struct PatternMatcher;

impl PatternMatcher {
    pub fn match_ir_to_ast(func: &SsaFunction) -> AstNode {
        let mut stmts = Vec::new();
        let mut visited = std::collections::HashSet::new();
        if let Some(stmt) = Self::walk_block(func, func.entry, &mut visited) {
            stmts.push(stmt);
        }
        for block in func.blocks.values() {
            if let Some(loop_stmt) = Self::detect_loop(func, block) {
                if !stmts.iter().any(stmt_contains_loop) {
                    stmts.push(loop_stmt);
                }
            }
        }
        AstNode {
            name: func.name.clone(),
            body: stmts,
        }
    }

    fn walk_block(func: &SsaFunction, block_id: u32, visited: &mut std::collections::HashSet<u32>) -> Option<AstStmt> {
        if !visited.insert(block_id) {
            return None;
        }
        let block = func.blocks.get(&block_id)?;
        let mut stmts = Vec::new();
        for insn in &block.instructions {
            if let Some(stmt) = insn_to_stmt(insn) {
                stmts.push(stmt);
            }
        }
        if block.successors.len() == 2 {
            let cond_stmt = block.instructions.iter().find_map(|i| {
                if let SsaInstruction::If { cond, left, right, .. } = i {
                    Some(AstStmt::If {
                        cond: operand_to_expr(left, cond, right),
                        then_branch: Box::new(AstStmt::Block(vec![])),
                        else_branch: None,
                    })
                } else {
                    None
                }
            });
            if let Some(if_stmt) = cond_stmt {
                stmts.push(if_stmt);
            }
        } else if block.successors.len() == 1 {
            if let Some(next) = Self::walk_block(func, block.successors[0], visited) {
                stmts.push(next);
            }
        }
        if stmts.is_empty() {
            None
        } else if stmts.len() == 1 {
            Some(stmts.into_iter().next().unwrap())
        } else {
            Some(AstStmt::Block(stmts))
        }
    }

    fn detect_loop(_func: &SsaFunction, block: &BasicBlock) -> Option<AstStmt> {
        for succ in &block.successors {
            if *succ <= block.id {
                let cond = AstExpr::LiteralI32(1);
                let body = AstStmt::Block(
                    block
                        .instructions
                        .iter()
                        .filter_map(insn_to_stmt)
                        .collect(),
                );
                return Some(AstStmt::While {
                    cond,
                    body: Box::new(body),
                });
            }
        }
        for insn in &block.instructions {
            if let SsaInstruction::Switch {
                discriminant,
                targets,
                default: _default,
            } = insn
            {
                let cases: Vec<(i32, AstStmt)> = targets
                    .iter()
                    .map(|(k, _)| (*k, AstStmt::Nop))
                    .collect();
                return Some(AstStmt::Switch {
                    discriminant: operand_to_expr_simple(discriminant),
                    cases,
                    default: Some(Box::new(AstStmt::Nop)),
                });
            }
        }
        None
    }
}

fn stmt_contains_loop(stmt: &AstStmt) -> bool {
    matches!(
        stmt,
        AstStmt::While { .. } | AstStmt::For { .. }
    )
}

fn insn_to_stmt(insn: &SsaInstruction) -> Option<AstStmt> {
    match insn {
        SsaInstruction::Const { dest, value } => Some(AstStmt::Assign {
            name: format!("v{dest}"),
            value: operand_to_expr_simple(value),
        }),
        SsaInstruction::Add { dest, left, right } => Some(AstStmt::Assign {
            name: format!("v{dest}"),
            value: AstExpr::Binary {
                op: BinOp::Add,
                left: Box::new(operand_to_expr_simple(left)),
                right: Box::new(operand_to_expr_simple(right)),
            },
        }),
        SsaInstruction::Return { value } => Some(AstStmt::Return(
            value.as_ref().map(operand_to_expr_simple),
        )),
        SsaInstruction::ReturnVoid => Some(AstStmt::ReturnVoid),
        SsaInstruction::Invoke { method, args, result, .. } => {
            let call = AstExpr::Call {
                name: method.clone(),
                args: args.iter().map(operand_to_expr_simple).collect(),
            };
            if let Some(r) = result {
                Some(AstStmt::Assign {
                    name: format!("v{r}"),
                    value: call,
                })
            } else {
                Some(AstStmt::Expr(call))
            }
        }
        SsaInstruction::Nop | SsaInstruction::Phi { .. } | SsaInstruction::Raw { .. } => None,
        SsaInstruction::Goto { .. } => None,
        SsaInstruction::If { .. } => None,
        SsaInstruction::Move { dest, src } => Some(AstStmt::Assign {
            name: format!("v{dest}"),
            value: operand_to_expr_simple(src),
        }),
        SsaInstruction::Switch { .. } => None,
    }
}

fn operand_to_expr(left: &SsaOperand, cond: &IfCondition, right: &SsaOperand) -> AstExpr {
    let op = match cond {
        IfCondition::Eq => BinOp::Eq,
        IfCondition::Ne => BinOp::Ne,
        IfCondition::Lt => BinOp::Lt,
        IfCondition::Gt => BinOp::Gt,
        _ => BinOp::Eq,
    };
    AstExpr::Binary {
        op,
        left: Box::new(operand_to_expr_simple(left)),
        right: Box::new(operand_to_expr_simple(right)),
    }
}

fn operand_to_expr_simple(op: &SsaOperand) -> AstExpr {
    match op {
        SsaOperand::Register(r) => AstExpr::Variable(format!("v{r}")),
        SsaOperand::ConstI32(v) => AstExpr::LiteralI32(*v),
        SsaOperand::ConstWide(v) => AstExpr::LiteralI32(*v as i32),
        SsaOperand::String(s) => AstExpr::LiteralString(s.clone()),
        SsaOperand::Type(t) => AstExpr::LiteralString(t.clone()),
        SsaOperand::Value(v) => AstExpr::Variable(format!("ssa{}", v.0)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ir::{BasicBlock, SsaFunction};
    use std::collections::HashMap;

    #[test]
    fn test_match_if_pattern() {
        let mut blocks = HashMap::new();
        blocks.insert(
            0,
            BasicBlock {
                id: 0,
                start_pc: 0,
                end_pc: 3,
                instructions: vec![SsaInstruction::If {
                    cond: IfCondition::Eq,
                    left: SsaOperand::Register(0),
                    right: SsaOperand::ConstI32(0),
                    target: 4,
                }],
                successors: vec![4, 2],
                predecessors: vec![],
            },
        );
        let func = SsaFunction {
            name: "test".into(),
            registers: 2,
            blocks,
            entry: 0,
            phi_count: 0,
        };
        let ast = PatternMatcher::match_ir_to_ast(&func);
        assert!(!ast.body.is_empty());
    }

    #[test]
    fn test_match_switch() {
        let mut blocks = HashMap::new();
        blocks.insert(
            0,
            BasicBlock {
                id: 0,
                start_pc: 0,
                end_pc: 5,
                instructions: vec![SsaInstruction::Switch {
                    discriminant: SsaOperand::Register(0),
                    targets: vec![(1, 10), (2, 20)],
                    default: 30,
                }],
                successors: vec![],
                predecessors: vec![],
            },
        );
        let func = SsaFunction {
            name: "sw".into(),
            registers: 1,
            blocks,
            entry: 0,
            phi_count: 0,
        };
        let ast = PatternMatcher::match_ir_to_ast(&func);
        assert!(ast.body.iter().any(|s| matches!(s, AstStmt::Switch { .. })));
    }
}
