//! Static knowledge stubs for wasm-slim builds — no hypercube index embedded.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SizeHint {
    Tiny,
    Small,
    Medium,
    Large,
    Huge,
    Unknown,
}

#[derive(Clone)]
pub struct SolverContext {
    pub speed_weight: f32,
    pub memory_weight: f32,
    pub clarity_weight: f32,
    pub safety_weight: f32,
    pub portability_weight: f32,
    pub energy_weight: f32,
    pub parallelism_weight: f32,
    pub realtime_weight: f32,
    pub target_hardware: Vec<u64>,
}

pub fn optimize_sort(_data_type: &str, _size_hint: SizeHint) -> (u16, u8) {
    (2002, 2) // Timsort
}

pub fn optimize_hash(_data_type: &str) -> (u16, u8) {
    (1953, 0)
}

pub fn get_ancestors(op_name: &str) -> Vec<(&'static str, u16)> {
    match op_name {
        "sort" => vec![("Timsort", 2002)],
        "hash" | "hash_search" => vec![("Hash Search", 1953)],
        _ => vec![("Unknown", 0)],
    }
}

pub fn get_tradeoffs(op_name: &str) -> Option<(u8, u8, u8, u8, u8)> {
    match op_name {
        "sort" => Some((80, 70, 65, 80, 90)),
        "hash" | "hash_search" => Some((85, 60, 70, 75, 85)),
        _ => None,
    }
}

pub fn hypercube_stats() -> (u64, u64) {
    (0, 0)
}
