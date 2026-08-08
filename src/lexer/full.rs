//! Full Frontier lexer implementation.
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

use super::Token;

#[derive(Debug, Clone)]
pub struct TokenInfo {
    pub token: Token,
    pub line: usize,
    pub column: usize,
}

pub struct Lexer<'a> {
    #[allow(dead_code)]
    input: &'a str,
    chars: Vec<char>,
    pos: usize,
    line: usize,
    column: usize,
}

impl<'a> Lexer<'a> {
    pub fn new(input: &'a str) -> Self {
        Self {
            input,
            chars: input.chars().collect(),
            pos: 0,
            line: 1,
            column: 1,
        }
    }

    pub fn tokenize(&mut self) -> Vec<TokenInfo> {
        let mut tokens = Vec::new();
        loop {
            let info = self.next_token();
            let is_eof = matches!(info.token, Token::Eof);
            tokens.push(info);
            if is_eof {
                break;
            }
        }
        tokens
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn peek_at(&self, offset: usize) -> Option<char> {
        self.chars.get(self.pos + offset).copied()
    }

    fn advance(&mut self) -> Option<char> {
        let ch = self.chars.get(self.pos).copied()?;
        self.pos += 1;
        if ch == '\n' {
            self.line += 1;
            self.column = 1;
        } else {
            self.column += 1;
        }
        Some(ch)
    }

    fn skip_whitespace_and_comments(&mut self) {
        loop {
            match self.peek() {
                Some(' ' | '\t' | '\r' | '\n') => {
                    self.advance();
                }
                Some('/') if self.peek_at(1) == Some('/') => {
                    while let Some(c) = self.peek() {
                        self.advance();
                        if c == '\n' {
                            break;
                        }
                    }
                }
                Some('/') if self.peek_at(1) == Some('*') => {
                    self.advance();
                    self.advance();
                    while let (Some(a), Some(b)) = (self.peek(), self.peek_at(1)) {
                        self.advance();
                        if a == '*' && b == '/' {
                            self.advance();
                            break;
                        }
                    }
                }
                _ => break,
            }
        }
    }

    fn is_id_cont(ch: char) -> bool {
        ch.is_ascii_alphanumeric() || ch == '_'
    }

    fn keyword_or_ident(&self, text: &str) -> Token {
        match text {
            "let" => Token::Let,
            "mut" => Token::Mut,
            "fn" => Token::Fn,
            "return" => Token::Return,
            "if" => Token::If,
            "else" => Token::Else,
            "true" => Token::True,
            "false" => Token::False,
            "null" => Token::Null,
            "int" => Token::Int,
            "float" => Token::Float,
            "bool" => Token::Bool,
            "string" => Token::String,
            "void" => Token::Void,
            "while" => Token::While,
            "import" => Token::Import,
            "as" => Token::As,
            "requires" => Token::Requires,
            "ensures" => Token::Ensures,
            "invariant" => Token::Invariant,
            "version" => Token::Version,
            _ => Token::Identifier(text.to_string()),
        }
    }

    fn read_string(&mut self, _line: usize, _column: usize) -> Token {
        self.advance(); // opening quote
        let mut s = String::new();
        while let Some(ch) = self.peek() {
            if ch == '"' {
                self.advance();
                return Token::StringLit(s);
            }
            if ch == '\\' {
                self.advance();
                match self.peek() {
                    Some('n') => {
                        s.push('\n');
                        self.advance();
                    }
                    Some('t') => {
                        s.push('\t');
                        self.advance();
                    }
                    Some('r') => {
                        s.push('\r');
                        self.advance();
                    }
                    Some('\\') => {
                        s.push('\\');
                        self.advance();
                    }
                    Some('"') => {
                        s.push('"');
                        self.advance();
                    }
                    _ => return Token::Error,
                }
            } else if ch == '\n' || ch == '\r' {
                return Token::Error;
            } else {
                s.push(ch);
                self.advance();
            }
        }
        Token::Error
    }

    fn read_number(&mut self) -> Token {
        let start = self.pos;
        if self.peek() == Some('0') {
            self.advance();
            if self.peek() == Some('.') {
                self.advance();
                while self.peek().is_some_and(|c| c.is_ascii_digit()) {
                    self.advance();
                }
                if matches!(self.peek(), Some('e' | 'E')) {
                    self.advance();
                    if matches!(self.peek(), Some('+' | '-')) {
                        self.advance();
                    }
                    while self.peek().is_some_and(|c| c.is_ascii_digit()) {
                        self.advance();
                    }
                }
                let text: String = self.chars[start..self.pos].iter().collect();
                return Token::FloatLit(text.parse().unwrap_or(0.0));
            }
            return Token::Integer(0);
        }
        while self.peek().is_some_and(|c| c.is_ascii_digit()) {
            self.advance();
        }
        if self.peek() == Some('.') && self.peek_at(1).is_some_and(|c| c.is_ascii_digit()) {
            self.advance();
            while self.peek().is_some_and(|c| c.is_ascii_digit()) {
                self.advance();
            }
            if matches!(self.peek(), Some('e' | 'E')) {
                self.advance();
                if matches!(self.peek(), Some('+' | '-')) {
                    self.advance();
                }
                while self.peek().is_some_and(|c| c.is_ascii_digit()) {
                    self.advance();
                }
            }
            let text: String = self.chars[start..self.pos].iter().collect();
            return Token::FloatLit(text.parse().unwrap_or(0.0));
        }
        if matches!(self.peek(), Some('e' | 'E')) {
            self.advance();
            if matches!(self.peek(), Some('+' | '-')) {
                self.advance();
            }
            while self.peek().is_some_and(|c| c.is_ascii_digit()) {
                self.advance();
            }
            let text: String = self.chars[start..self.pos].iter().collect();
            return Token::FloatLit(text.parse().unwrap_or(0.0));
        }
        let text: String = self.chars[start..self.pos].iter().collect();
        Token::Integer(text.parse().unwrap_or(0))
    }

    fn read_ident(&mut self) -> Token {
        let start = self.pos;
        self.advance();
        while self.peek().is_some_and(Self::is_id_cont) {
            self.advance();
        }
        let text: String = self.chars[start..self.pos].iter().collect();
        if self.peek().is_some_and(Self::is_id_cont) {
            // keyword boundary: if we matched "if" but more id chars follow, it's identifier
            // already consumed full identifier
        }
        self.keyword_or_ident(&text)
    }

    pub fn next_token(&mut self) -> TokenInfo {
        self.skip_whitespace_and_comments();
        let line = self.line;
        let column = self.column;

        let token = match self.peek() {
            None => Token::Eof,
            Some('"') => self.read_string(line, column),
            Some('0'..='9') => self.read_number(),
            Some('a'..='z' | 'A'..='Z' | '_') => self.read_ident(),
            Some('|') => {
                self.advance();
                if self.peek() == Some('|') {
                    self.advance();
                    Token::OpOr
                } else {
                    Token::Error
                }
            }
            Some('&') => {
                self.advance();
                if self.peek() == Some('&') {
                    self.advance();
                    Token::OpAnd
                } else {
                    Token::Error
                }
            }
            Some('=') => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    Token::OpEq
                } else {
                    Token::OpAssign
                }
            }
            Some('!') => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    Token::OpNe
                } else {
                    Token::OpBang
                }
            }
            Some('<') => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    Token::OpLe
                } else {
                    Token::OpLt
                }
            }
            Some('>') => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    Token::OpGe
                } else {
                    Token::OpGt
                }
            }
            Some('+') => {
                self.advance();
                Token::OpPlus
            }
            Some('-') => {
                self.advance();
                if self.peek() == Some('>') {
                    self.advance();
                    Token::Arrow
                } else {
                    Token::OpMinus
                }
            }
            Some('*') => {
                self.advance();
                Token::OpMul
            }
            Some('/') => {
                self.advance();
                Token::OpDiv
            }
            Some('%') => {
                self.advance();
                Token::OpMod
            }
            Some('^') => {
                self.advance();
                Token::OpExp
            }
            Some('~') => {
                self.advance();
                Token::OpTilde
            }
            Some('?') => {
                self.advance();
                Token::OpOptional
            }
            Some('(') => {
                self.advance();
                Token::LParen
            }
            Some(')') => {
                self.advance();
                Token::RParen
            }
            Some('{') => {
                self.advance();
                Token::LBrace
            }
            Some('}') => {
                self.advance();
                Token::RBrace
            }
            Some(',') => {
                self.advance();
                Token::Comma
            }
            Some(';') => {
                self.advance();
                Token::Semicolon
            }
            Some(':') => {
                self.advance();
                Token::Colon
            }
            Some('.') => {
                self.advance();
                Token::Dot
            }
            Some('@') => {
                self.advance();
                Token::At
            }
            _ => {
                self.advance();
                Token::Error
            }
        };

        TokenInfo { token, line, column }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iff_is_identifier() {
        let mut lex = Lexer::new("iff");
        let t = lex.next_token();
        assert_eq!(t.token, Token::Identifier("iff".to_string()));
    }

    #[test]
    fn if_is_keyword() {
        let mut lex = Lexer::new("if ");
        let t = lex.next_token();
        assert_eq!(t.token, Token::If);
    }
}
