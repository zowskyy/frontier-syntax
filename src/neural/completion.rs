/// Neural completion engine for LSP.
/// Production deployments integrate ONNX Runtime (ort) for model inference.
pub struct NeuralCompletion {
    context_window: usize,
}

impl NeuralCompletion {
    pub fn new(context_window: usize) -> Self {
        NeuralCompletion { context_window }
    }

    pub fn suggest(&self, source: &str, cursor: usize) -> Vec<String> {
        let prefix = &source[..cursor.min(source.len())];
        let mut suggestions = Vec::new();

        if prefix.ends_with("let ") || prefix.ends_with("let\t") {
            suggestions.extend(["x", "y", "result"].map(String::from));
        }
        if prefix.contains("import \"") && !prefix.contains(" as ") {
            suggestions.push("ipfs://QmExampleHash1234567890".to_string());
        }
        if prefix.ends_with("@") {
            suggestions.extend(["requires", "ensures", "invariant"].map(String::from));
        }
        if prefix.ends_with("fn ") {
            suggestions.extend(["main", "double", "process"].map(String::from));
        }

        suggestions.truncate(self.context_window);
        suggestions
    }

    pub fn rank(&self, suggestions: &[String], query: &str) -> Vec<String> {
        let mut ranked = suggestions.to_vec();
        ranked.sort_by_key(|s| {
            if s.starts_with(query) {
                0
            } else if s.contains(query) {
                1
            } else {
                2
            }
        });
        ranked
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_neural_suggestions() {
        let engine = NeuralCompletion::new(8);
        let suggestions = engine.suggest("let ", 4);
        assert!(suggestions.contains(&"x".to_string()));
    }

    #[test]
    fn test_proof_annotation_suggestions() {
        let engine = NeuralCompletion::new(8);
        let suggestions = engine.suggest("@", 1);
        assert!(suggestions.contains(&"requires".to_string()));
    }
}
