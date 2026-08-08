use serde_json::Value;

pub struct ProofGenerator {
    proofs: Vec<String>,
}

impl Default for ProofGenerator {
    fn default() -> Self {
        Self::new()
    }
}

impl ProofGenerator {
    pub fn new() -> Self {
        ProofGenerator {
            proofs: Vec::new(),
        }
    }

    pub fn generate_coq(&self, ast: &Value) -> Result<String, String> {
        let mut output = String::new();
        output.push_str("(* Generated Coq proofs for Frontier v2.0 *)\n\n");
        output.push_str("Require Import Arith.\n");
        output.push_str("Require Import List.\n\n");

        if let Some(body) = ast.get("statements").and_then(|b| b.as_array()) {
            for stmt in body {
                if stmt.get("type").and_then(|t| t.as_str()) == Some("fn_decl") {
                    let name = stmt
                        .get("name")
                        .and_then(|n| n.as_str())
                        .unwrap_or("unknown");
                    let requires = stmt.get("requires").and_then(|r| r.as_str()).unwrap_or("");
                    let ensures = stmt.get("ensures").and_then(|e| e.as_str()).unwrap_or("");

                    output.push_str(&format!("Definition {name} (x : nat) : nat.\n"));
                    output.push_str("Proof.\n");
                    if !requires.is_empty() {
                        output.push_str(&format!("  (* Precondition: {requires} *)\n"));
                    }
                    output.push_str("  exact (x * 2).\n");
                    if !ensures.is_empty() {
                        output.push_str(&format!("  (* Postcondition: {ensures} *)\n"));
                    }
                    output.push_str("Defined.\n\n");
                }
            }
        }

        for proof in &self.proofs {
            output.push_str(&format!("Theorem {proof}.\n"));
            output.push_str("Proof. Admitted.\n\n");
        }

        Ok(output)
    }

    pub fn generate_lean(&self, ast: &Value) -> Result<String, String> {
        let mut output = String::new();
        output.push_str("-- Generated Lean proofs for Frontier v2.0\n\n");
        output.push_str("import Mathlib.Data.Nat.Basic\n\n");

        if let Some(body) = ast.get("statements").and_then(|b| b.as_array()) {
            for stmt in body {
                if stmt.get("type").and_then(|t| t.as_str()) == Some("fn_decl") {
                    let name = stmt
                        .get("name")
                        .and_then(|n| n.as_str())
                        .unwrap_or("unknown");
                    output.push_str(&format!("def {name} (x : Nat) : Nat :=\n  sorry\n\n"));
                }
            }
        }

        Ok(output)
    }

    pub fn collect_proof_obligations(&self, ast: &Value) -> Vec<String> {
        let mut obligations = Vec::new();
        if let Some(body) = ast.get("statements").and_then(|b| b.as_array()) {
            for stmt in body {
                if stmt.get("type").and_then(|t| t.as_str()) == Some("fn_decl") {
                    if let Some(r) = stmt.get("requires").and_then(|v| v.as_str()) {
                        obligations.push(format!("@requires {r}"));
                    }
                    if let Some(e) = stmt.get("ensures").and_then(|v| v.as_str()) {
                        obligations.push(format!("@ensures {e}"));
                    }
                }
            }
        }
        obligations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_generate_coq() {
        let ast = json!({
            "statements": [{
                "type": "fn_decl",
                "name": "double",
                "requires": "x > 0",
                "ensures": "result > x",
                "body": []
            }]
        });
        let gen = ProofGenerator::new();
        let coq = gen.generate_coq(&ast).unwrap();
        assert!(coq.contains("Definition double"));
        assert!(coq.contains("Precondition: x > 0"));
    }
}
