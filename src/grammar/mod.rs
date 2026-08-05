pub mod mutator;

use mutator::GrammarMutator;
use serde_json::Value;
use std::fs;

pub fn load_grammar_v2() -> Result<Value, String> {
    let content = fs::read_to_string("syntax/grammar_v2.json")
        .map_err(|e| format!("Failed to load grammar_v2.json: {e}"))?;
    serde_json::from_str(&content).map_err(|e| format!("Invalid grammar JSON: {e}"))
}

pub fn apply_mutation(name: &str, pattern: Vec<&str>) -> Result<Value, String> {
    let grammar = load_grammar_v2()?;
    let mut mutator = GrammarMutator::new(grammar);
    mutator.add_rule(name, pattern);
    Ok(mutator.grammar().clone())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_grammar_v2() {
        let grammar = load_grammar_v2().expect("grammar should load");
        assert_eq!(
            grammar.get("version").and_then(|v| v.as_str()),
            Some("2.0")
        );
    }

    #[test]
    fn test_apply_mutation() {
        let updated = apply_mutation("asyncFn", vec!["async", "fn"]).expect("mutation ok");
        let rules = updated
            .get("rules")
            .and_then(|r| r.as_object())
            .expect("rules object");
        assert!(rules.contains_key("asyncFn"));
    }
}
