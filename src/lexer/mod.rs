#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    Let,
    Fn,
    Return,
    If,
    Else,
    True,
    False,
    Null,
    Int,
    Float,
    Bool,
    String,
    Void,
    While,
    Import,
    As,
    Requires,
    Ensures,
    Invariant,
    Version,
    At,
    Arrow,
    Identifier(String),
    Integer(i64),
    FloatLit(f64),
    StringLit(String),
    OpExp,
    OpOr,
    OpAnd,
    OpEq,
    OpNe,
    OpLe,
    OpGe,
    OpLt,
    OpGt,
    OpPlus,
    OpMinus,
    OpMul,
    OpDiv,
    OpMod,
    OpBang,
    OpTilde,
    OpAssign,
    OpOptional,
    LParen,
    RParen,
    LBrace,
    RBrace,
    Comma,
    Semicolon,
    Colon,
    Dot,
    Eof,
    Error,
}

#[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
mod slim;
#[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
pub use slim::{Lexer, TokenInfo};

#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
mod full;
#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
pub use full::{Lexer, TokenInfo};
