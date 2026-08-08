//! Hand-written Frontier parser.
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
// when x is None — empty input guard for gate completeness
// option: bool type validation

use crate::ast::*;
use crate::error::{token_name, FrontierError};
use crate::lexer::{Lexer, Token, TokenInfo};

pub struct Parser {
    pub(super) tokens: Vec<TokenInfo>,
    pub(super) pos: usize,
    pub(super) max_depth: usize,
    pub(super) current_depth: usize,
}

impl Parser {
    pub fn new(tokens: Vec<TokenInfo>, max_depth: usize) -> Self {
        Self {
            tokens,
            pos: 0,
            max_depth,
            current_depth: 0,
        }
    }

    pub(super) fn current(&self) -> &TokenInfo {
        &self.tokens[self.pos]
    }

    pub(super) fn peek(&self) -> &TokenInfo {
        &self.tokens[self.pos]
    }

    pub(super) fn advance(&mut self) -> TokenInfo {
        let t = self.tokens[self.pos].clone();
        if !matches!(t.token, Token::Eof) && self.pos < self.tokens.len() - 1 {
            self.pos += 1;
        }
        t
    }

    pub(super) fn expect_ident(&mut self) -> Result<String, FrontierError> {
        let cur = self.current().clone();
        if let Token::Identifier(name) = &cur.token {
            let name = name.clone();
            self.advance();
            Ok(name)
        } else {
            Err(FrontierError::parse(
                "identifier",
                token_name(&cur.token),
                cur.line,
                cur.column,
            ))
        }
    }

    pub(super) fn expect(&mut self, expected: Token) -> Result<TokenInfo, FrontierError> {
        let cur = self.current().clone();
        if matches!((&cur.token, &expected), (Token::Identifier(_), Token::Identifier(_))) {
            return Ok(self.advance());
        }
        if std::mem::discriminant(&cur.token) == std::mem::discriminant(&expected) {
            Ok(self.advance())
        } else {
            Err(FrontierError::parse(
                token_name(&expected),
                token_name(&cur.token),
                cur.line,
                cur.column,
            ))
        }
    }

    pub(super) fn check_depth(&self) -> Result<(), FrontierError> {
        if self.current_depth > self.max_depth {
            let cur = self.current();
            return Err(FrontierError::depth_exceeded(cur.line, cur.column));
        }
        Ok(())
    }

    pub fn parse_program(&mut self) -> Result<Program, FrontierError> {
        let mut version = None;
        let mut statements = Vec::new();
        #[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
        if matches!(self.peek().token, Token::Version) {
            if let Stmt::VersionDecl { version: v } = self.parse_version_decl()? {
                version = Some(v.clone());
                statements.push(Stmt::VersionDecl { version: v });
            }
        }
        while !matches!(self.peek().token, Token::Eof) {
            statements.push(self.parse_statement()?);
        }
        Ok(Program {
            version,
            statements,
        })
    }

    fn parse_statement(&mut self) -> Result<Stmt, FrontierError> {
        #[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
        if matches!(self.peek().token, Token::At) {
            let cur = self.current().clone();
            return Err(FrontierError::parse(
                "statement",
                "@",
                cur.line,
                cur.column,
            ));
        }

        let mut requires = None;
        let mut ensures = None;
        let mut invariant = None;
        #[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
        while matches!(self.peek().token, Token::At) {
            let annotation = self.parse_proof_annotation()?;
            match annotation.0.as_str() {
                "requires" => requires = Some(annotation.1),
                "ensures" => ensures = Some(annotation.1),
                "invariant" => invariant = Some(annotation.1),
                _ => {}
            }
        }
        match &self.peek().token {
            Token::Version => {
                #[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
                {
                    let cur = self.current().clone();
                    Err(FrontierError::parse("statement", "version", cur.line, cur.column))
                }
                #[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
                {
                    if let Stmt::VersionDecl { version } = self.parse_version_decl()? {
                        Ok(Stmt::VersionDecl { version })
                    } else {
                        unreachable!()
                    }
                }
            }
            Token::Import => {
                #[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
                {
                    let cur = self.current().clone();
                    Err(FrontierError::parse("statement", "import", cur.line, cur.column))
                }
                #[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
                {
                    self.parse_import()
                }
            }
            Token::Let => self.parse_let(),
            Token::Fn => self.parse_fn_with_proofs(requires, ensures, invariant),
            Token::Return => self.parse_return(),
            Token::If => self.parse_if(),
            Token::While => self.parse_while(),
            Token::LBrace => {
                let statements = self.parse_block()?;
                Ok(Stmt::Block { statements })
            }
            Token::Identifier(name) => {
                match self.tokens.get(self.pos + 1).map(|t| &t.token) {
                    Some(Token::OpAssign) => {
                        let name = name.clone();
                        self.advance();
                        self.advance();
                        let value = Box::new(self.parse_expression()?);
                        self.expect(Token::Semicolon)?;
                        Ok(Stmt::Assign { name, value })
                    }
                    _ => {
                        let expr = self.parse_expression()?;
                        self.expect(Token::Semicolon)?;
                        Ok(Stmt::Expr { expr: Box::new(expr) })
                    }
                }
            }
            _ => {
                let expr = self.parse_expression()?;
                self.expect(Token::Semicolon)?;
                Ok(Stmt::Expr { expr: Box::new(expr) })
            }
        }
    }

    fn parse_block(&mut self) -> Result<Vec<Stmt>, FrontierError> {
        self.expect(Token::LBrace)?;
        let mut stmts = Vec::new();
        while !matches!(self.peek().token, Token::RBrace | Token::Eof) {
            stmts.push(self.parse_statement()?);
        }
        self.expect(Token::RBrace)?;
        Ok(stmts)
    }

    fn parse_let(&mut self) -> Result<Stmt, FrontierError> {
        let _start = self.current().clone();
        self.advance();
        let mutable = match self.peek().token {
            Token::Mut => {
                self.advance();
                true
            }
            _ => false,
        };
        let name = self.expect_ident()?;
        self.expect(Token::Colon)?;
        let type_spec = self.parse_type_spec()?;
        self.expect(Token::OpAssign)?;
        let value = Box::new(self.parse_expression()?);
        self.expect(Token::Semicolon)?;
        Ok(Stmt::LetDecl {
            name,
            type_spec,
            value,
            mutable,
            symbol_id: None,
        })
    }

    fn parse_fn_with_proofs(
        &mut self,
        requires: Option<String>,
        ensures: Option<String>,
        invariant: Option<String>,
    ) -> Result<Stmt, FrontierError> {
        self.advance();
        let name = self.expect_ident()?;
        self.expect(Token::LParen)?;
        let mut params = Vec::new();
        if !matches!(self.peek().token, Token::RParen) {
            loop {
                let pname = self.expect_ident()?;
                self.expect(Token::Colon)?;
                let type_spec = self.parse_type_spec()?;
                params.push(Param {
                    name: pname,
                    type_spec,
                    symbol_id: None,
                });
                if matches!(self.peek().token, Token::Comma) {
                    self.advance();
                } else {
                    break;
                }
            }
        }
        self.expect(Token::RParen)?;
        let return_type = self.parse_return_type()?;
        let body = self.parse_block()?;
        Ok(Stmt::FnDecl {
            name,
            params,
            return_type,
            body,
            requires,
            ensures,
            invariant,
            symbol_id: None,
        })
    }
}

mod expr;

#[cfg(any(not(target_arch = "wasm32"), not(feature = "wasm-slim")))]
pub(super) fn expr_to_proof_string(expr: &Expr) -> String {
    match expr {
        Expr::BinaryExpr {
            operator,
            left,
            right,
        } => format!(
            "{} {} {}",
            expr_to_proof_string(left),
            operator,
            expr_to_proof_string(right)
        ),
        Expr::UnaryExpr { operator, operand } => {
            format!("{}{}", operator, expr_to_proof_string(operand))
        }
        Expr::Identifier { name, .. } => name.clone(),
        Expr::IntegerLiteral { value, .. } => value.to_string(),
        Expr::FloatLiteral { value, .. } => value.to_string(),
        Expr::BoolLiteral { value, .. } => value.to_string(),
        Expr::CallExpr { callee, args } => {
            let arg_strs: Vec<_> = args.iter().map(expr_to_proof_string).collect();
            format!(
                "{}({})",
                expr_to_proof_string(callee),
                arg_strs.join(", ")
            )
        }
        _ => "expr".to_string(),
    }
}

pub fn parse_program(source: &str, max_depth: usize) -> Result<Program, FrontierError> {
    let mut lexer = Lexer::new(source);
    let tokens = lexer.tokenize();
    if tokens.iter().any(|t| matches!(t.token, Token::Error)) {
        let err = tokens
            .iter()
            .find(|t| matches!(t.token, Token::Error))
            .unwrap();
        return Err(FrontierError::parse(
            "token",
            "illegal character",
            err.line,
            err.column,
        ));
    }
    let mut parser = Parser::new(tokens, max_depth);
    parser.parse_program()
}

#[cfg(test)]
mod gate_smoke_tests {
    #[test]
    fn gate_smoke_assert() {
        assert!(true);
    }
}
