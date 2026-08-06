//! Minimal knowledge bridge for wasm-slim — no serde, no FFI.

use crate::knowledge_slim::SizeHint;

#[derive(Debug, Clone)]
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

#[derive(Debug, Clone)]
pub struct AlgorithmSuggestion {
    pub name: String,
    pub discovery_year: u16,
    pub paradigm_flags: u8,
    pub complexity_class: u8,
    pub tradeoffs: TradeoffEntry,
    pub implementation_hint: String,
}

pub fn get_optimal_algorithm(operation: &str, _data_type: &str, _size_hint: SizeHint) -> AlgorithmSuggestion {
    AlgorithmSuggestion {
        name: operation.to_string(),
        discovery_year: 2002,
        paradigm_flags: 4,
        complexity_class: 2,
        tradeoffs: TradeoffEntry {
            speed: 80,
            memory: 70,
            clarity: 65,
            safety: 80,
            portability: 90,
            energy: 75,
            parallelism: 50,
            realtime: 60,
        },
        implementation_hint: "timsort".to_string(),
    }
}

pub fn optimization_warnings(_operation: &str, _data_type: &str) -> Vec<String> {
    Vec::new()
}

pub fn browser_context() -> crate::knowledge_slim::SolverContext {
    crate::knowledge_slim::SolverContext {
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

pub fn get_ancestors_json(operation: &str) -> Vec<(String, u16)> {
    crate::knowledge_slim::get_ancestors(operation)
        .into_iter()
        .map(|(name, year)| (name.to_string(), year))
        .collect()
}

pub fn get_tradeoffs_json(operation: &str) -> Option<TradeoffEntry> {
    crate::knowledge_slim::get_tradeoffs(operation).map(
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
