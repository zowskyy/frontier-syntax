use crate::ast::*;
use crate::error::{token_name, FrontierError};
use crate::lexer::{Lexer, Token, TokenInfo};

pub struct Parser {
    tokens: Vec<TokenInfo>,
    pos: usize,
    max_depth: usize,
    current_depth: usize,
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

    fn current(&self) -> &TokenInfo {
        &self.tokens[self.pos]
    }

    fn peek(&self) -> &TokenInfo {
        &self.tokens[self.pos]
    }

    fn advance(&mut self) -> TokenInfo {
        let t = self.tokens[self.pos].clone();
        if !matches!(t.token, Token::Eof) && self.pos < self.tokens.len() - 1 {
            self.pos += 1;
        }
        t
    }

    fn expect_ident(&mut self) -> Result<String, FrontierError> {
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

    fn expect(&mut self, expected: Token) -> Result<TokenInfo, FrontierError> {
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

    fn check_depth(&self) -> Result<(), FrontierError> {
        if self.current_depth > self.max_depth {
            let cur = self.current();
            return Err(FrontierError::depth_exceeded(cur.line, cur.column));
        }
        Ok(())
    }

    pub fn parse_program(&mut self) -> Result<Program, FrontierError> {
        let mut statements = Vec::new();
        while !matches!(self.peek().token, Token::Eof) {
            statements.push(self.parse_statement()?);
        }
        Ok(Program { statements })
    }

    fn parse_statement(&mut self) -> Result<Stmt, FrontierError> {
        match &self.peek().token {
            Token::Let => self.parse_let(),
            Token::Fn => self.parse_fn(),
            Token::Return => self.parse_return(),
            Token::If => self.parse_if(),
            Token::LBrace => {
                let statements = self.parse_block()?;
                Ok(Stmt::Block { statements })
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
        let start = self.current().clone();
        self.advance();
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
            symbol_id: None,
        })
    }

    fn parse_fn(&mut self) -> Result<Stmt, FrontierError> {
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
        self.expect(Token::Colon)?;
        let return_type = self.parse_type_spec()?;
        let body = self.parse_block()?;
        Ok(Stmt::FnDecl {
            name,
            params,
            return_type,
            body,
            symbol_id: None,
        })
    }

    fn parse_return(&mut self) -> Result<Stmt, FrontierError> {
        self.advance();
        let value = if matches!(self.peek().token, Token::Semicolon) {
            None
        } else {
            Some(Box::new(self.parse_expression()?))
        };
        self.expect(Token::Semicolon)?;
        Ok(Stmt::Return { value })
    }

    fn parse_if(&mut self) -> Result<Stmt, FrontierError> {
        self.advance();
        self.expect(Token::LParen)?;
        let condition = Box::new(self.parse_expression()?);
        self.expect(Token::RParen)?;
        let then_block = self.parse_block()?;
        let else_block = if matches!(self.peek().token, Token::Else) {
            self.advance();
            Some(self.parse_block()?)
        } else {
            None
        };
        Ok(Stmt::If {
            condition,
            then_block,
            else_block,
        })
    }

    fn parse_type_spec(&mut self) -> Result<TypeSpec, FrontierError> {
        let base = match &self.peek().token {
            Token::Int => {
                self.advance();
                "int".to_string()
            }
            Token::Float => {
                self.advance();
                "float".to_string()
            }
            Token::Bool => {
                self.advance();
                "bool".to_string()
            }
            Token::String => {
                self.advance();
                "string".to_string()
            }
            Token::Void => {
                self.advance();
                "void".to_string()
            }
            Token::Identifier(s) => {
                let s = s.clone();
                self.advance();
                s
            }
            other => {
                let cur = self.current().clone();
                return Err(FrontierError::parse(
                    "type",
                    token_name(other),
                    cur.line,
                    cur.column,
                ));
            }
        };
        let annotation = match &self.peek().token {
            Token::OpOptional => {
                self.advance();
                TypeAnnotation::Optional
            }
            Token::OpBang => {
                self.advance();
                TypeAnnotation::Required
            }
            _ => TypeAnnotation::None,
        };
        Ok(TypeSpec { base, annotation })
    }

    fn parse_expression(&mut self) -> Result<Expr, FrontierError> {
        self.parse_logical_or()
    }

    fn parse_logical_or(&mut self) -> Result<Expr, FrontierError> {
        let mut left = self.parse_logical_and()?;
        while matches!(self.peek().token, Token::OpOr) {
            self.advance();
            let right = self.parse_logical_and()?;
            left = Expr::BinaryExpr {
                operator: "||".to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_logical_and(&mut self) -> Result<Expr, FrontierError> {
        let mut left = self.parse_equality()?;
        while matches!(self.peek().token, Token::OpAnd) {
            self.advance();
            let right = self.parse_equality()?;
            left = Expr::BinaryExpr {
                operator: "&&".to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_equality(&mut self) -> Result<Expr, FrontierError> {
        let mut left = self.parse_relational()?;
        while matches!(self.peek().token, Token::OpEq | Token::OpNe) {
            let op = match self.advance().token {
                Token::OpEq => "==",
                Token::OpNe => "!=",
                _ => unreachable!(),
            };
            let right = self.parse_relational()?;
            left = Expr::BinaryExpr {
                operator: op.to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_relational(&mut self) -> Result<Expr, FrontierError> {
        let mut left = self.parse_additive()?;
        while matches!(
            self.peek().token,
            Token::OpLt | Token::OpGt | Token::OpLe | Token::OpGe
        ) {
            let op = match self.advance().token {
                Token::OpLt => "<",
                Token::OpGt => ">",
                Token::OpLe => "<=",
                Token::OpGe => ">=",
                _ => unreachable!(),
            };
            let right = self.parse_additive()?;
            left = Expr::BinaryExpr {
                operator: op.to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_additive(&mut self) -> Result<Expr, FrontierError> {
        let mut left = self.parse_exponent()?;
        while matches!(self.peek().token, Token::OpPlus | Token::OpMinus) {
            let op = match self.advance().token {
                Token::OpPlus => "+",
                Token::OpMinus => "-",
                _ => unreachable!(),
            };
            let right = self.parse_exponent()?;
            left = Expr::BinaryExpr {
                operator: op.to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_exponent(&mut self) -> Result<Expr, FrontierError> {
        let left = self.parse_multiplicative()?;
        if matches!(self.peek().token, Token::OpExp) {
            self.advance();
            let right = self.parse_exponent()?;
            return Ok(Expr::BinaryExpr {
                operator: "^".to_string(),
                left: Box::new(left),
                right: Box::new(right),
            });
        }
        Ok(left)
    }

    fn parse_multiplicative(&mut self) -> Result<Expr, FrontierError> {
        let mut left = self.parse_unary()?;
        while matches!(
            self.peek().token,
            Token::OpMul | Token::OpDiv | Token::OpMod
        ) {
            let op = match self.advance().token {
                Token::OpMul => "*",
                Token::OpDiv => "/",
                Token::OpMod => "%",
                _ => unreachable!(),
            };
            let right = self.parse_unary()?;
            left = Expr::BinaryExpr {
                operator: op.to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_unary(&mut self) -> Result<Expr, FrontierError> {
        self.check_depth()?;
        self.current_depth += 1;
        let result = match &self.peek().token {
            Token::OpMinus => {
                self.advance();
                let operand = Box::new(self.parse_unary()?);
                Ok(Expr::UnaryExpr {
                    operator: "-".to_string(),
                    operand,
                })
            }
            Token::OpBang => {
                self.advance();
                let operand = Box::new(self.parse_unary()?);
                Ok(Expr::UnaryExpr {
                    operator: "!".to_string(),
                    operand,
                })
            }
            Token::OpTilde => {
                self.advance();
                let operand = Box::new(self.parse_unary()?);
                Ok(Expr::UnaryExpr {
                    operator: "~".to_string(),
                    operand,
                })
            }
            _ => self.parse_postfix(),
        };
        self.current_depth -= 1;
        result
    }

    fn parse_postfix(&mut self) -> Result<Expr, FrontierError> {
        let mut expr = self.parse_primary()?;
        loop {
            match &self.peek().token {
                Token::LParen => {
                    self.advance();
                    let mut args = Vec::new();
                    if !matches!(self.peek().token, Token::RParen) {
                        loop {
                            args.push(self.parse_expression()?);
                            if matches!(self.peek().token, Token::Comma) {
                                self.advance();
                            } else {
                                break;
                            }
                        }
                    }
                    self.expect(Token::RParen)?;
                    expr = Expr::CallExpr {
                        callee: Box::new(expr),
                        args,
                    };
                }
                Token::Dot => {
                    self.advance();
                    let field = self.expect_ident()?;
                    expr = Expr::FieldAccess {
                        object: Box::new(expr),
                        field,
                    };
                }
                Token::OpBang => {
                    self.advance();
                    expr = Expr::RequiredExpr {
                        operand: Box::new(expr),
                    };
                }
                _ => break,
            }
        }
        Ok(expr)
    }

    fn parse_primary(&mut self) -> Result<Expr, FrontierError> {
        let cur = self.current().clone();
        match &cur.token {
            Token::Integer(v) => {
                self.advance();
                Ok(Expr::IntegerLiteral {
                    value: *v,
                    symbol_id: None,
                })
            }
            Token::FloatLit(v) => {
                self.advance();
                Ok(Expr::FloatLiteral {
                    value: *v,
                    symbol_id: None,
                })
            }
            Token::StringLit(v) => {
                self.advance();
                Ok(Expr::StringLiteral {
                    value: v.clone(),
                    symbol_id: None,
                })
            }
            Token::True => {
                self.advance();
                Ok(Expr::BoolLiteral {
                    value: true,
                    symbol_id: None,
                })
            }
            Token::False => {
                self.advance();
                Ok(Expr::BoolLiteral {
                    value: false,
                    symbol_id: None,
                })
            }
            Token::Null => {
                self.advance();
                Ok(Expr::NullLiteral { symbol_id: None })
            }
            Token::Identifier(name) => {
                let name = name.clone();
                self.advance();
                Ok(Expr::Identifier {
                    name,
                    symbol_id: None,
                })
            }
            Token::LParen => {
                self.advance();
                let inner = Box::new(self.parse_expression()?);
                self.expect(Token::RParen)?;
                Ok(Expr::Grouped { inner })
            }
            other => Err(FrontierError::parse(
                "expression",
                token_name(other),
                cur.line,
                cur.column,
            )),
        }
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
