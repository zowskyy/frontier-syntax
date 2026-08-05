pub struct EngineOrchestrator {
    engines: Vec<&'static str>,
    last: usize,
}

impl EngineOrchestrator {
    pub fn new() -> Self {
        Self {
            engines: vec!["frontier-dex", "cfr", "procyon", "fernflower"],
            last: 0,
        }
    }

    pub fn last_engine(&self) -> &'static str {
        self.engines[self.last]
    }

    /// JNI hook stub — external engines invoked when primary fails.
    pub fn try_fallback(&mut self, bytes: &[u8]) -> Option<String> {
        for (i, name) in self.engines.iter().enumerate().skip(1) {
            if let Some(src) = self.invoke_jni_stub(name, bytes) {
                self.last = i;
                return Some(src);
            }
        }
        None
    }

    fn invoke_jni_stub(&self, engine: &str, bytes: &[u8]) -> Option<String> {
        if bytes.len() < 8 || &bytes[0..3] != b"dex" {
            return None;
        }
        Some(format!(
            "// Fallback decompilation via {engine} (JNI stub)\npublic class Fallback {{ /* {} bytes */ }}",
            bytes.len()
        ))
    }
}

impl Default for EngineOrchestrator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_priority() {
        let orch = EngineOrchestrator::new();
        assert_eq!(orch.last_engine(), "frontier-dex");
    }

    #[test]
    fn test_fallback_stub() {
        let mut dex = vec![0u8; 64];
        dex[0..8].copy_from_slice(b"dex\n035\0");
        let mut orch = EngineOrchestrator::new();
        let src = orch.try_fallback(&dex);
        assert!(src.is_some());
        assert_eq!(orch.last_engine(), "cfr");
    }
}
