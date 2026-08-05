//! Frontier Syntax lexer — O(n) tokenization from token_regex_table.json + Cycle 2 extensions.

use regex::Regex;
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Token {
    pub kind: String,
    pub text: String,
    pub line: usize,
    pub column: usize,
}

#[derive(Debug, Clone)]
pub struct LexError {
    pub message: String,
    pub line: usize,
    pub column: usize,
}

#[derive(Debug, Clone)]
pub struct LexResult {
    pub valid: bool,
    pub tokens: Vec<Token>,
    pub errors: Vec<LexError>,
}

#[derive(Deserialize)]
struct TokenSpec {
    pattern: String,
    #[serde(default = "default_true")]
    emits_token: bool,
}

fn default_true() -> bool {
    true
}

#[derive(Deserialize)]
struct TokenTable {
    tokens: HashMap<String, TokenSpec>,
}

#[derive(Deserialize)]
struct ExtensionFile {
    tokens: HashMap<String, TokenSpec>,
}

pub struct Lexer {
    rules: Vec<(String, Regex, bool)>,
}

fn is_token_boundary(rest: &str, match_len: usize) -> bool {
    rest.chars()
        .nth(match_len)
        .map(|c| !c.is_ascii_alphanumeric() && c != '_')
        .unwrap_or(true)
}

fn strip_lookahead(pattern: &str) -> String {
    // Rust `regex` lacks lookahead; strip (?![...]) suffix used in token table
    if let Some(idx) = pattern.find("(?") {
        pattern[..idx].to_string()
    } else {
        pattern.to_string()
    }
}

impl Lexer {
    pub fn from_tables(cycle1: &str, cycle2_ext: Option<&str>) -> Result<Self, String> {
        let base: TokenTable =
            serde_json::from_str(cycle1).map_err(|e| format!("cycle1 table: {e}"))?;
        let mut merged = base.tokens;

        if let Some(ext_json) = cycle2_ext {
            let ext: ExtensionFile =
                serde_json::from_str(ext_json).map_err(|e| format!("cycle2 ext: {e}"))?;
            merged.extend(ext.tokens);
        }

        let mut rules = Vec::new();
        for (name, spec) in merged {
            let emits = spec.emits_token;
            let pattern = strip_lookahead(&spec.pattern);
            let regex = Regex::new(&pattern)
                .map_err(|e| format!("invalid regex for {name}: {e}"))?;
            rules.push((name, regex, emits));
        }

        Ok(Self { rules })
    }

    pub fn lex(&self, source: &str) -> LexResult {
        let mut tokens = Vec::new();
        let mut errors = Vec::new();
        let mut pos = 0;
        let mut line = 1usize;
        let mut col = 1usize;
        let chars: Vec<char> = source.chars().collect();

        while pos < chars.len() {
            let rest: String = chars[pos..].iter().collect();
            let mut best_name = None;
            let mut best_len = 0usize;
            let mut best_emits = false;

            for (name, re, emits) in &self.rules {
                if let Some(m) = re.find(&rest) {
                    if m.start() == 0 && m.len() > best_len {
                        let len = m.len();
                        if name.starts_with("KW_") && !is_token_boundary(&rest, len) {
                            continue;
                        }
                        best_len = len;
                        best_name = Some(name.clone());
                        best_emits = *emits;
                    }
                }
            }

            if best_len == 0 {
                errors.push(LexError {
                    message: format!("Unexpected character '{}'", chars[pos]),
                    line,
                    column: col,
                });
                pos += 1;
                col += 1;
                continue;
            }

            let text: String = chars[pos..pos + best_len].iter().collect();
            if best_emits {
                tokens.push(Token {
                    kind: best_name.unwrap_or_else(|| "UNKNOWN".into()),
                    text,
                    line,
                    column: col,
                });
            }

            for ch in chars[pos..pos + best_len].iter() {
                if *ch == '\n' {
                    line += 1;
                    col = 1;
                } else {
                    col += 1;
                }
            }
            pos += best_len;
        }

        LexResult {
            valid: errors.is_empty(),
            tokens,
            errors,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn lexes_cycle1_snippet() {
        let cycle1 = fs::read_to_string("../../syntax/token_regex_table.json").unwrap();
        let lexer = Lexer::from_tables(&cycle1, None).unwrap();
        let result = lexer.lex("let x: int = 1;");
        assert!(result.valid, "{:?}", result.errors);
        assert!(!result.tokens.is_empty());
    }

    #[test]
    fn lexes_cycle2_module_snippet() {
        let cycle1 = fs::read_to_string("../../syntax/token_regex_table.json").unwrap();
        let cycle2 = fs::read_to_string("../../syntax/cycle2/extensions.json").unwrap();
        let lexer = Lexer::from_tables(&cycle1, Some(&cycle2)).unwrap();
        let result = lexer.lex("module app;\nfn main() -> void {}");
        assert!(result.valid, "{:?}", result.errors);
    }
}
