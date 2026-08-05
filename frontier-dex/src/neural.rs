use crate::ast::{AstNode, AstStmt};
use crate::parser::DexFile;
use serde::Deserialize;
use std::fs;

#[derive(Debug, Deserialize)]
pub struct ObfuscationPattern {
    pub name: String,
    pub score: f32,
    pub strategy: String,
}

pub struct ObfuscationPredictor {
    patterns: Vec<ObfuscationPattern>,
}

impl ObfuscationPredictor {
    pub fn new() -> Self {
        let patterns = load_patterns().unwrap_or_default();
        Self { patterns }
    }

    pub fn score_dex(&self, dex: &DexFile) -> f32 {
        let mut score = 0.0f32;
        let method_count: usize = dex.classes.iter().map(|c| c.methods.len()).sum();
        if method_count > 1000 {
            score += 0.3;
        }
        for class in &dex.classes {
            for method in &class.methods {
                if method.name.len() <= 2 {
                    score += 0.1;
                }
            }
        }
        for p in &self.patterns {
            if p.name == "short_names" && score > 0.2 {
                score += p.score;
            }
        }
        score.min(1.0)
    }

    pub fn enhance(&self, mut ast: AstNode) -> AstNode {
        let score = self.score_ast(&ast);
        if score < 0.3 {
            return ast;
        }
        for pattern in &self.patterns {
            ast = apply_strategy(ast, pattern);
        }
        ast
    }

    fn score_ast(&self, ast: &AstNode) -> f32 {
        let mut score = 0.0;
        for stmt in &ast.body {
            score += stmt_score(stmt);
        }
        score.min(1.0)
    }
}

impl Default for ObfuscationPredictor {
    fn default() -> Self {
        Self::new()
    }
}

fn load_patterns() -> Option<Vec<ObfuscationPattern>> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("assets/obfuscation_patterns.json");
    let data = fs::read_to_string(path).ok()?;
    serde_json::from_str(&data).ok()
}

fn apply_strategy(mut ast: AstNode, pattern: &ObfuscationPattern) -> AstNode {
    match pattern.strategy.as_str() {
        "rename_locals" => {
            ast.name = format!("{}_deobf", ast.name);
        }
        "unwrap_strings" => {}
        _ => {}
    }
    ast
}

fn stmt_score(stmt: &AstStmt) -> f32 {
    match stmt {
        AstStmt::Block(stmts) => stmts.iter().map(stmt_score).sum(),
        AstStmt::Expr(crate::ast::AstExpr::Call { name, .. }) if name.starts_with("invoke@") => 0.2,
        _ => 0.0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ast::AstNode;

    #[test]
    fn test_predictor_score() {
        let p = ObfuscationPredictor::new();
        let ast = AstNode {
            name: "test".into(),
            body: vec![],
        };
        assert!(p.score_ast(&ast) < 0.3);
    }

    #[test]
    fn test_enhance_low_score() {
        let p = ObfuscationPredictor::new();
        let ast = AstNode {
            name: "clean".into(),
            body: vec![AstStmt::ReturnVoid],
        };
        let enhanced = p.enhance(ast);
        assert_eq!(enhanced.name, "clean");
    }
}
