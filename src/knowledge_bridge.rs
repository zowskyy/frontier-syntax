//! Bridge between the Rust Knowledge Hypercube and browser/WASM compiler pipeline.

use crate::knowledge::{get_ancestors, get_tradeoffs, optimize_hash, optimize_sort, SizeHint};
use crate::knowledge::solver::SolverContext;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeoffEntry {
    pub speed: u8,
    pub memory: u8,
    pub clarity: u8,
    pub safety: u8,
    pub portability: u8,
    pub energy: u8,
    pub parallelism: u8,
    pub realtime: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlgorithmSuggestion {
    pub name: String,
    pub discovery_year: u16,
    pub paradigm_flags: u8,
    pub complexity_class: u8,
    pub tradeoffs: TradeoffEntry,
    pub implementation_hint: String,
}

pub fn browser_context() -> SolverContext {
    SolverContext {
        speed_weight: 0.6,
        memory_weight: 0.4,
        clarity_weight: 0.7,
        safety_weight: 0.8,
        portability_weight: 0.9,
        energy_weight: 0.3,
        parallelism_weight: 0.5,
        realtime_weight: 0.2,
        target_hardware: vec![],
    }
}

pub fn native_context() -> SolverContext {
    SolverContext {
        speed_weight: 0.8,
        memory_weight: 0.5,
        clarity_weight: 0.5,
        safety_weight: 0.7,
        portability_weight: 0.4,
        energy_weight: 0.6,
        parallelism_weight: 0.7,
        realtime_weight: 0.8,
        target_hardware: vec![],
    }
}

pub fn get_optimal_algorithm(
    operation: &str,
    data_type: &str,
    size_hint: SizeHint,
) -> AlgorithmSuggestion {
    let (year, complexity) = match operation {
        "hash" | "hash_search" => optimize_hash(data_type),
        _ => optimize_sort(data_type, size_hint),
    };

    let tradeoffs = get_tradeoffs(operation)
        .map(|(speed, memory, clarity, safety, portability)| TradeoffEntry {
            speed,
            memory,
            clarity,
            safety,
            portability,
            energy: 75,
            parallelism: 50,
            realtime: 60,
        })
        .unwrap_or(TradeoffEntry {
            speed: 80,
            memory: 70,
            clarity: 65,
            safety: 80,
            portability: 90,
            energy: 75,
            parallelism: 50,
            realtime: 60,
        });

    let hint = match operation {
        "sort" => "timsort",
        "hash" | "hash_search" => "hash_search",
        _ => "generic",
    };

    AlgorithmSuggestion {
        name: operation.to_string(),
        discovery_year: year,
        paradigm_flags: 4,
        complexity_class: complexity,
        tradeoffs,
        implementation_hint: hint.to_string(),
    }
}

pub fn get_ancestors_json(operation: &str) -> Vec<(String, u16)> {
    get_ancestors(operation)
        .into_iter()
        .map(|(name, year)| (name.to_string(), year))
        .collect()
}

pub fn get_tradeoffs_json(operation: &str) -> Option<TradeoffEntry> {
    get_tradeoffs(operation).map(
        |(speed, memory, clarity, safety, portability)| TradeoffEntry {
            speed,
            memory,
            clarity,
            safety,
            portability,
            energy: 75,
            parallelism: 50,
            realtime: 60,
        },
    )
}

pub fn optimization_warnings(operation: &str, data_type: &str) -> Vec<String> {
    let suggestion = get_optimal_algorithm(operation, data_type, SizeHint::Medium);
    vec![format!(
        "Knowledge Hypercube: using {} ({}) — complexity class {}",
        suggestion.implementation_hint, suggestion.discovery_year, suggestion.complexity_class
    )]
}

fn read_str(ptr: *const u8, len: u32) -> &'static str {
    if ptr.is_null() || len == 0 {
        return "";
    }
    unsafe {
        std::str::from_utf8(std::slice::from_raw_parts(ptr, len as usize)).unwrap_or("")
    }
}

fn leak_json<T: Serialize>(value: &T) -> *const u8 {
    let json = serde_json::to_string(value).unwrap_or_else(|_| "{}".to_string());
    Box::leak(json.into_bytes().into_boxed_slice()).as_ptr()
}

/// FFI entry point for `knowledge.frontier` — optimal algorithm lookup.
#[no_mangle]
pub extern "C" fn knowledge_solver_get_optimal_algorithm(
    operation_ptr: *const u8,
    operation_len: u32,
    data_type_ptr: *const u8,
    data_type_len: u32,
    size_hint: u32,
    _context_ptr: *const u8,
    _context_len: u32,
) -> *const u8 {
    let operation = read_str(operation_ptr, operation_len);
    let data_type = read_str(data_type_ptr, data_type_len);
    let hint = match size_hint {
        0 => SizeHint::Tiny,
        1 => SizeHint::Small,
        2 => SizeHint::Medium,
        3 => SizeHint::Large,
        4 => SizeHint::Huge,
        _ => SizeHint::Unknown,
    };
    let suggestion = get_optimal_algorithm(operation, data_type, hint);
    leak_json(&suggestion)
}

#[no_mangle]
pub extern "C" fn knowledge_solver_get_ancestors(
    operation_ptr: *const u8,
    operation_len: u32,
) -> *const u8 {
    let operation = read_str(operation_ptr, operation_len);
    let ancestors = get_ancestors_json(operation);
    leak_json(&ancestors)
}

#[no_mangle]
pub extern "C" fn knowledge_solver_get_tradeoffs(
    operation_ptr: *const u8,
    operation_len: u32,
) -> *const u8 {
    let operation = read_str(operation_ptr, operation_len);
    let tradeoffs = get_tradeoffs_json(operation);
    leak_json(&tradeoffs)
}

#[no_mangle]
pub extern "C" fn knowledge_solver_free(_ptr: *const u8) {
    // Leaked JSON buffers are process-lifetime for MVP FFI bridge.
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bridge_suggestion() {
        let s = get_optimal_algorithm("sort", "list::i32", SizeHint::Large);
        assert!(s.discovery_year >= 1990);
    }
}
