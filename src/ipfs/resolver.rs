use serde_json::Value;

const IPFS_PREFIX: &str = "ipfs://";

pub struct IpfsImportResolver {
    imports: Vec<String>,
}

impl IpfsImportResolver {
    pub fn new() -> Self {
        IpfsImportResolver {
            imports: Vec::new(),
        }
    }

    pub fn resolve_import(&mut self, path: &str, alias: &str) -> Result<(), String> {
        if !path.starts_with(IPFS_PREFIX) {
            return Err(format!("Invalid IPFS path: {path}"));
        }
        let cid = &path[IPFS_PREFIX.len()..];
        if cid.is_empty() || !cid.chars().all(|c| c.is_ascii_alphanumeric()) {
            return Err(format!("Invalid IPFS CID: {cid}"));
        }
        self.imports.push(format!("{alias}={path}"));
        Ok(())
    }

    pub fn resolve_ast(&mut self, ast: &Value) -> Result<Vec<String>, Vec<String>> {
        let mut errors = Vec::new();
        if let Some(stmts) = ast.get("statements").and_then(|s| s.as_array()) {
            for stmt in stmts {
                if stmt.get("type").and_then(|t| t.as_str()) == Some("import_decl") {
                    let path = stmt.get("path").and_then(|p| p.as_str()).unwrap_or("");
                    let alias = stmt.get("alias").and_then(|a| a.as_str()).unwrap_or("");
                    if let Err(e) = self.resolve_import(path, alias) {
                        errors.push(e);
                    }
                }
            }
        }
        if errors.is_empty() {
            Ok(self.imports.clone())
        } else {
            Err(errors)
        }
    }

    pub fn imports(&self) -> &[String] {
        &self.imports
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_ipfs_import() {
        let mut resolver = IpfsImportResolver::new();
        resolver
            .resolve_import("ipfs://QmExampleHash1234567890", "math_utils")
            .unwrap();
        assert_eq!(resolver.imports().len(), 1);
    }

    #[test]
    fn test_invalid_ipfs_path() {
        let mut resolver = IpfsImportResolver::new();
        assert!(resolver.resolve_import("http://bad", "x").is_err());
    }

    #[test]
    fn test_resolve_ast() {
        let ast = json!({
            "statements": [{
                "type": "import_decl",
                "path": "ipfs://QmExampleHash1234567890",
                "alias": "utils"
            }]
        });
        let mut resolver = IpfsImportResolver::new();
        let imports = resolver.resolve_ast(&ast).unwrap();
        assert_eq!(imports.len(), 1);
    }
}
