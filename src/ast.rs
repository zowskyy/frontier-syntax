use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Stmt {
    LetDecl {
        name: String,
        type_spec: TypeSpec,
        value: Box<Expr>,
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    FnDecl {
        name: String,
        params: Vec<Param>,
        return_type: TypeSpec,
        body: Vec<Stmt>,
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    Return {
        value: Option<Box<Expr>>,
    },
    If {
        condition: Box<Expr>,
        then_block: Vec<Stmt>,
        else_block: Option<Vec<Stmt>>,
    },
    Block {
        statements: Vec<Stmt>,
    },
    Expr {
        expr: Box<Expr>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Param {
    pub name: String,
    pub type_spec: TypeSpec,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub symbol_id: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TypeSpec {
    pub base: String,
    pub annotation: TypeAnnotation,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum TypeAnnotation {
    None,
    Optional,
    Required,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Expr {
    IntegerLiteral {
        value: i64,
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    FloatLiteral {
        value: f64,
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    StringLiteral {
        value: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    BoolLiteral {
        value: bool,
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    NullLiteral {
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    Identifier {
        name: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        symbol_id: Option<u32>,
    },
    UnaryExpr {
        operator: String,
        operand: Box<Expr>,
    },
    BinaryExpr {
        operator: String,
        left: Box<Expr>,
        right: Box<Expr>,
    },
    CallExpr {
        callee: Box<Expr>,
        args: Vec<Expr>,
    },
    FieldAccess {
        object: Box<Expr>,
        field: String,
    },
    RequiredExpr {
        operand: Box<Expr>,
    },
    Grouped {
        inner: Box<Expr>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Program {
    pub statements: Vec<Stmt>,
}

impl Expr {
    pub fn nesting_depth(&self) -> usize {
        match self {
            Expr::UnaryExpr { operand, .. }
            | Expr::RequiredExpr { operand }
            | Expr::Grouped { inner: operand } => 1 + operand.nesting_depth(),
            Expr::BinaryExpr { left, right, .. } => {
                1 + left.nesting_depth().max(right.nesting_depth())
            }
            Expr::CallExpr { callee, args } => {
                1 + callee
                    .nesting_depth()
                    .max(args.iter().map(|a| a.nesting_depth()).max().unwrap_or(0))
            }
            Expr::FieldAccess { object, .. } => 1 + object.nesting_depth(),
            _ => 1,
        }
    }
}
