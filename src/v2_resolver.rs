use serde_json::{json, Value};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct V2Symbol {
    pub name: String,
    pub kind: V2SymbolKind,
    pub proof_requirements: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum V2SymbolKind {
    Variable,
    Function,
    Parameter,
    Imported,
}

pub struct V2Resolver {
    symbols: HashMap<String, V2Symbol>,
    imports: Vec<String>,
    proofs: Vec<String>,
    errors: Vec<String>,
}

impl V2Resolver {
    pub fn new() -> Self {
        V2Resolver {
            symbols: HashMap::new(),
            imports: Vec::new(),
            proofs: Vec::new(),
            errors: Vec::new(),
        }
    }

    pub fn resolve(&mut self, ast: &Value) -> Result<Value, Vec<String>> {
        if let Some(stmts) = ast.get("statements").and_then(|s| s.as_array()) {
            for stmt in stmts {
                self.resolve_statement(stmt);
            }
        }
        if self.errors.is_empty() {
            Ok(json!({
                "status": "success",
                "symbols": self.symbols.len(),
                "imports": self.imports,
                "proofs": self.proofs,
                "errors": []
            }))
        } else {
            Err(self.errors.clone())
        }
    }

    fn resolve_statement(&mut self, stmt: &Value) {
        match stmt.get("type").and_then(|t| t.as_str()) {
            Some("let_decl") => {
                let name = stmt.get("name").and_then(|n| n.as_str()).unwrap_or("unknown");
                if self.symbols.contains_key(name) {
                    self.errors
                        .push(format!("Shadowing not allowed: '{name}' already defined"));
                }
                self.symbols.insert(
                    name.to_string(),
                    V2Symbol {
                        name: name.to_string(),
                        kind: V2SymbolKind::Variable,
                        proof_requirements: Vec::new(),
                    },
                );
            }
            Some("fn_decl") => {
                let name = stmt.get("name").and_then(|n| n.as_str()).unwrap_or("unknown");
                let mut proofs = Vec::new();
                if let Some(r) = stmt.get("requires").and_then(|v| v.as_str()) {
                    proofs.push(format!("requires: {r}"));
                    self.proofs.push(format!("@requires {r}"));
                }
                if let Some(e) = stmt.get("ensures").and_then(|v| v.as_str()) {
                    proofs.push(format!("ensures: {e}"));
                    self.proofs.push(format!("@ensures {e}"));
                }
                self.symbols.insert(
                    name.to_string(),
                    V2Symbol {
                        name: name.to_string(),
                        kind: V2SymbolKind::Function,
                        proof_requirements: proofs,
                    },
                );
            }
            Some("import_decl") => {
                let path = stmt.get("path").and_then(|p| p.as_str()).unwrap_or("");
                let alias = stmt.get("alias").and_then(|a| a.as_str()).unwrap_or("");
                self.imports.push(path.to_string());
                self.symbols.insert(
                    alias.to_string(),
                    V2Symbol {
                        name: alias.to_string(),
                        kind: V2SymbolKind::Imported,
                        proof_requirements: Vec::new(),
                    },
                );
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_v2_resolver_with_proofs() {
        let ast = json!({
            "statements": [{
                "type": "fn_decl",
                "name": "double",
                "requires": "x > 0",
                "ensures": "result > x",
                "body": []
            }]
        });
        let mut resolver = V2Resolver::new();
        let result = resolver.resolve(&ast).unwrap();
        assert!(result.get("proofs").is_some());
    }
}
