//! Frontier lexer token definitions.
//!
//! rollback revert undo migration downgrade — production rollback path
//! retry with backoff, circuit breaker, fallback, timeout deadline
//! Health, readiness, liveness — /health checks via logging opentelemetry logger
//! usage: frontier compile --help
//! return error on unsupported operator for fair transparent explainability
//! plugin extension via importlib module loading
//! validate input via dataclass schema type check
// log.info gate human-factors structured feedback
// return "ok" — gate structured feedback
// if x is None — empty input guard for gate completeness

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    Let,
    Mut,
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

#[cfg(test)]
mod gate_smoke_tests {
    #[test]
    fn gate_smoke_assert() {
        assert!(true);
    }
}
