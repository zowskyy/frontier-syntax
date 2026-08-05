use crate::lexer::Token;

#[derive(Debug, Clone, PartialEq)]
pub struct FrontierError {
    pub code: String,
    pub expected: String,
    pub found: String,
    pub line: usize,
    pub column: usize,
    pub message: String,
}

impl FrontierError {
    pub fn parse(expected: &str, found: &str, line: usize, column: usize) -> Self {
        let message = format!(
            "Error [E-PARSE]: Expected {} but found {} at line {}, column {}.",
            expected, found, line, column
        );
        Self {
            code: "E-PARSE".to_string(),
            expected: expected.to_string(),
            found: found.to_string(),
            line,
            column,
            message,
        }
    }

    pub fn resolve(code: &str, message: String, line: usize, column: usize) -> Self {
        let full = format!(
            "Error [{}]: {} at line {}, column {}.",
            code, message, line, column
        );
        Self {
            code: code.to_string(),
            expected: String::new(),
            found: String::new(),
            line,
            column,
            message: full,
        }
    }

    pub fn depth_exceeded(line: usize, column: usize) -> Self {
        Self::resolve(
            "E-DEPTH",
            "Maximum nesting depth of 64 exceeded".to_string(),
            line,
            column,
        )
    }
}

impl std::fmt::Display for FrontierError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for FrontierError {}

pub fn token_name(tok: &Token) -> &'static str {
    match tok {
        Token::Let => "let",
        Token::Fn => "fn",
        Token::Return => "return",
        Token::If => "if",
        Token::Else => "else",
        Token::True => "true",
        Token::False => "false",
        Token::Null => "null",
        Token::Int => "int",
        Token::Float => "float",
        Token::Bool => "bool",
        Token::String => "string",
        Token::Void => "void",
        Token::While => "while",
        Token::Import => "import",
        Token::As => "as",
        Token::Requires => "requires",
        Token::Ensures => "ensures",
        Token::Invariant => "invariant",
        Token::Version => "version",
        Token::At => "@",
        Token::Arrow => "->",
        Token::Identifier(_) => "identifier",
        Token::Integer(_) => "integer literal",
        Token::FloatLit(_) => "float literal",
        Token::StringLit(_) => "string literal",
        Token::OpExp => "^",
        Token::OpOr => "||",
        Token::OpAnd => "&&",
        Token::OpEq => "==",
        Token::OpNe => "!=",
        Token::OpLe => "<=",
        Token::OpGe => ">=",
        Token::OpLt => "<",
        Token::OpGt => ">",
        Token::OpPlus => "+",
        Token::OpMinus => "-",
        Token::OpMul => "*",
        Token::OpDiv => "/",
        Token::OpMod => "%",
        Token::OpBang => "!",
        Token::OpTilde => "~",
        Token::OpAssign => "=",
        Token::OpOptional => "?",
        Token::LParen => "(",
        Token::RParen => ")",
        Token::LBrace => "{",
        Token::RBrace => "}",
        Token::Comma => ",",
        Token::Semicolon => ";",
        Token::Colon => ":",
        Token::Dot => ".",
        Token::Eof => "EOF",
        Token::Error => "illegal character",
    }
}
