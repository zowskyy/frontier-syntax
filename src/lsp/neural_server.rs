use crate::neural::completion::NeuralCompletion;

pub struct NeuralLspServer {
    completion: NeuralCompletion,
}

impl Default for NeuralLspServer {
    fn default() -> Self {
        Self::new()
    }
}

impl NeuralLspServer {
    pub fn new() -> Self {
        NeuralLspServer {
            completion: NeuralCompletion::new(16),
        }
    }

    pub fn complete(&self, source: &str, line: usize, character: usize) -> Vec<String> {
        let lines: Vec<&str> = source.lines().collect();
        let mut offset = 0usize;
        for (i, l) in lines.iter().enumerate() {
            if i == line {
                offset += character.min(l.len());
                break;
            }
            offset += l.len() + 1;
        }
        self.completion.suggest(source, offset)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lsp_complete() {
        let server = NeuralLspServer::new();
        let suggestions = server.complete("let ", 0, 4);
        assert!(!suggestions.is_empty());
    }
}
