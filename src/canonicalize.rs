use crate::ast::Program;
use serde_json::{Map, Value};
use sha3::{Digest, Sha3_256};

pub fn canonical_value(value: &Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let mut sorted = Map::new();
            for key in keys {
                if key == "symbol_id" {
                    continue;
                }
                sorted.insert(key.clone(), canonical_value(&map[key]));
            }
            Value::Object(sorted)
        }
        Value::Array(arr) => Value::Array(arr.iter().map(canonical_value).collect()),
        other => other.clone(),
    }
}

pub fn canonical_ast_json(program: &Program) -> Result<String, serde_json::Error> {
    let raw = serde_json::to_value(program)?;
    let canonical = canonical_value(&raw);
    serde_json::to_string(&canonical)
}

pub fn sha3_256_hex(data: &str) -> String {
    let mut hasher = Sha3_256::new();
    hasher.update(data.as_bytes());
    format!("{:x}", hasher.finalize())
}
