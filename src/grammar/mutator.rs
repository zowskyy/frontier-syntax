use serde_json::{json, Value};

pub struct GrammarMutator {
    grammar: Value,
    version: String,
    mutations: Vec<String>,
}

impl GrammarMutator {
    pub fn new(grammar: Value) -> Self {
        let version = grammar
            .get("version")
            .and_then(|v| v.as_str())
            .unwrap_or("2.0")
            .to_string();
        GrammarMutator {
            grammar,
            version,
            mutations: Vec::new(),
        }
    }

    pub fn add_rule(&mut self, name: &str, pattern: Vec<&str>) {
        let rules = self
            .grammar
            .get_mut("rules")
            .expect("grammar must have rules")
            .as_object_mut()
            .expect("rules must be object");
        rules.insert(name.to_string(), json!(pattern));
        self.mutations.push(format!("Added rule: {name}"));
        self.bump_version();
    }

    pub fn remove_rule(&mut self, name: &str) {
        let rules = self
            .grammar
            .get_mut("rules")
            .expect("grammar must have rules")
            .as_object_mut()
            .expect("rules must be object");
        if rules.remove(name).is_some() {
            self.mutations.push(format!("Removed rule: {name}"));
            self.bump_version();
        }
    }

    pub fn grammar(&self) -> &Value {
        &self.grammar
    }

    pub fn version(&self) -> &str {
        &self.version
    }

    pub fn mutations(&self) -> &[String] {
        &self.mutations
    }

    fn bump_version(&mut self) {
        let parts: Vec<&str> = self.version.split('.').collect();
        let major = parts.first().and_then(|p| p.parse::<u32>().ok()).unwrap_or(2);
        let minor = parts.get(1).and_then(|p| p.parse::<u32>().ok()).unwrap_or(0) + 1;
        self.version = format!("{major}.{minor}");
        if let Some(obj) = self.grammar.as_object_mut() {
            obj.insert("version".to_string(), json!(self.version));
            if let Some(mutations) = obj.get_mut("mutations").and_then(|m| m.as_array_mut()) {
                for m in &self.mutations {
                    mutations.push(json!(m));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_rule_bumps_version() {
        let grammar = json!({ "version": "2.0", "rules": {}, "mutations": [] });
        let mut mutator = GrammarMutator::new(grammar);
        mutator.add_rule("newRule", vec!["token1", "token2"]);
        assert_eq!(mutator.version(), "2.1");
        assert_eq!(mutator.mutations().len(), 1);
    }
}
