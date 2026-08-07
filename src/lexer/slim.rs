use super::Token;

#[derive(Debug, Clone)]
pub struct TokenInfo {
    pub token: Token,
    pub line: usize,
    pub column: usize,
}

pub struct Lexer<'a> {
    bytes: &'a [u8],
    pos: usize,
    line: usize,
    column: usize,
}

impl<'a> Lexer<'a> {
    pub fn new(input: &'a str) -> Self {
        Self {
            bytes: input.as_bytes(),
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

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    fn peek_at(&self, n: usize) -> Option<u8> {
        self.bytes.get(self.pos + n).copied()
    }

    fn advance(&mut self) -> Option<u8> {
        let b = self.peek()?;
        self.pos += 1;
        if b == b'\n' {
            self.line += 1;
            self.column = 1;
        } else {
            self.column += 1;
        }
        Some(b)
    }

    fn slice_from(&self, start: usize) -> &str {
        std::str::from_utf8(&self.bytes[start..self.pos]).unwrap_or("")
    }

    fn skip_ws(&mut self) {
        loop {
            match self.peek() {
                Some(b' ' | b'\t' | b'\r' | b'\n') => {
                    self.advance();
                }
                Some(b'/') if self.peek_at(1) == Some(b'/') => {
                    while let Some(b) = self.peek() {
                        self.advance();
                        if b == b'\n' {
                            break;
                        }
                    }
                }
                _ => break,
            }
        }
    }

    fn keyword_or_ident(&self, text: &str) -> Token {
        match text {
            "let" => Token::Let,
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

    fn read_number(&mut self) -> Token {
        let start = self.pos;
        while self.peek().map_or(false, |b| b.is_ascii_digit()) {
            self.advance();
        }
        Token::Integer(self.slice_from(start).parse().unwrap_or(0))
    }

    fn read_ident(&mut self) -> Token {
        let start = self.pos;
        self.advance();
        while self
            .peek()
            .map_or(false, |b| b.is_ascii_alphanumeric() || b == b'_')
        {
            self.advance();
        }
        self.keyword_or_ident(self.slice_from(start))
    }

    pub fn next_token(&mut self) -> TokenInfo {
        self.skip_ws();
        let line = self.line;
        let column = self.column;
        let token = match self.peek() {
            None => Token::Eof,
            Some(b'0'..=b'9') => self.read_number(),
            Some(b'a'..=b'z' | b'A'..=b'Z' | b'_') => self.read_ident(),
            Some(b'|') => {
                self.advance();
                if self.peek() == Some(b'|') {
                    self.advance();
                    Token::OpOr
                } else {
                    Token::Error
                }
            }
            Some(b'&') => {
                self.advance();
                if self.peek() == Some(b'&') {
                    self.advance();
                    Token::OpAnd
                } else {
                    Token::Error
                }
            }
            Some(b'=') => {
                self.advance();
                if self.peek() == Some(b'=') {
                    self.advance();
                    Token::OpEq
                } else {
                    Token::OpAssign
                }
            }
            Some(b'!') => {
                self.advance();
                if self.peek() == Some(b'=') {
                    self.advance();
                    Token::OpNe
                } else {
                    Token::OpBang
                }
            }
            Some(b'<') => {
                self.advance();
                if self.peek() == Some(b'=') {
                    self.advance();
                    Token::OpLe
                } else {
                    Token::OpLt
                }
            }
            Some(b'>') => {
                self.advance();
                if self.peek() == Some(b'=') {
                    self.advance();
                    Token::OpGe
                } else {
                    Token::OpGt
                }
            }
            Some(b'+') => {
                self.advance();
                Token::OpPlus
            }
            Some(b'-') => {
                self.advance();
                if self.peek() == Some(b'>') {
                    self.advance();
                    Token::Arrow
                } else {
                    Token::OpMinus
                }
            }
            Some(b'*') => {
                self.advance();
                Token::OpMul
            }
            Some(b'/') => {
                self.advance();
                Token::OpDiv
            }
            Some(b'%') => {
                self.advance();
                Token::OpMod
            }
            Some(b'(') => {
                self.advance();
                Token::LParen
            }
            Some(b')') => {
                self.advance();
                Token::RParen
            }
            Some(b'{') => {
                self.advance();
                Token::LBrace
            }
            Some(b'}') => {
                self.advance();
                Token::RBrace
            }
            Some(b',') => {
                self.advance();
                Token::Comma
            }
            Some(b';') => {
                self.advance();
                Token::Semicolon
            }
            Some(b':') => {
                self.advance();
                Token::Colon
            }
            Some(b'.') => {
                self.advance();
                Token::Dot
            }
            Some(b'@') => {
                self.advance();
                Token::At
            }
            Some(b'"') => Token::Error,
            _ => {
                self.advance();
                Token::Error
            }
        };
        TokenInfo { token, line, column }
    }
}
