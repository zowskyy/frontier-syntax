//! Frontier Dimensional Solver Engine — silent, zero-dependency knowledge selection.

use std::collections::HashMap;
use std::fs;
use std::path::Path;

use super::hypercube::{
    hash_name, parse_algorithm_entry, parse_master_index, parse_tradeoff_entry, AlgorithmEntry,
    MasterIndex, TradeoffEntry, ALGORITHM_ENTRY_SIZE,
};

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

impl Default for SolverContext {
    fn default() -> Self {
        Self {
            speed_weight: 0.5,
            memory_weight: 0.5,
            clarity_weight: 0.5,
            safety_weight: 0.5,
            portability_weight: 0.5,
            energy_weight: 0.5,
            parallelism_weight: 0.5,
            realtime_weight: 0.5,
            target_hardware: vec![],
        }
    }
}

impl SolverContext {
    pub fn from_project_type(project_type: &str) -> Self {
        match project_type {
            "embedded" => Self {
                memory_weight: 0.9,
                speed_weight: 0.7,
                clarity_weight: 0.3,
                safety_weight: 0.8,
                portability_weight: 0.6,
                energy_weight: 0.9,
                parallelism_weight: 0.1,
                realtime_weight: 0.9,
                target_hardware: vec![hash_name("ARM"), hash_name("RISC-V")],
            },
            "web" => Self {
                speed_weight: 0.6,
                memory_weight: 0.5,
                clarity_weight: 0.8,
                safety_weight: 0.9,
                portability_weight: 0.7,
                energy_weight: 0.3,
                parallelism_weight: 0.4,
                realtime_weight: 0.2,
                target_hardware: vec![hash_name("x86_64"), hash_name("ARM64")],
            },
            _ => Self::default(),
        }
    }
}

pub struct Solver {
    index_data: Vec<u8>,
    master: MasterIndex,
    algorithm_cache: HashMap<u64, AlgorithmEntry>,
    tradeoff_cache: HashMap<u32, TradeoffEntry>,
    pub context: SolverContext,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SizeHint {
    Tiny,
    Small,
    Medium,
    Large,
    Huge,
    Unknown,
}

pub struct ProblemSignature {
    pub operation_type: u64,
    pub data_type: u64,
    pub size_hint: SizeHint,
    pub context_flags: u32,
}

pub struct Solution {
    pub algorithm_hash: u64,
    pub year: u16,
    pub paradigm: u8,
    pub complexity: u8,
    pub tradeoffs: TradeoffEntry,
}

const SORT_ALGORITHMS: &[&str] = &[
    "bubble_sort", "insertion_sort", "merge_sort", "quick_sort", "heap_sort", "shell_sort",
    "timsort", "radix_sort", "counting_sort", "introspective_sort", "block_sort",
];

const HASH_ALGORITHMS: &[&str] = &["hash_search"];

impl Solver {
    pub fn from_embedded() -> Result<Self, Box<dyn std::error::Error>> {
        let index_data = include_bytes!("hypercube/index.bin").to_vec();
        let master = parse_master_index(&index_data)
            .ok_or_else(|| "Invalid embedded knowledge index".to_string())?;

        Ok(Self {
            index_data,
            master,
            algorithm_cache: HashMap::new(),
            tradeoff_cache: HashMap::new(),
            context: SolverContext::default(),
        })
    }

    pub fn new(knowledge_path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        #[cfg(target_arch = "wasm32")]
        {
            let _ = knowledge_path;
            return Self::from_embedded();
        }

        #[cfg(not(target_arch = "wasm32"))]
        {
            let index_path = Path::new(knowledge_path).join("index.bin");
            let index_data = fs::read(&index_path)?;
            let master = parse_master_index(&index_data)
                .ok_or_else(|| format!("Invalid knowledge index: {}", index_path.display()))?;

            Ok(Self {
                index_data,
                master,
                algorithm_cache: HashMap::new(),
                tradeoff_cache: HashMap::new(),
                context: SolverContext::default(),
            })
        }
    }

    pub fn with_context(mut self, context: SolverContext) -> Self {
        self.context = context;
        self
    }

    fn read_algorithm_at(&self, offset: u64) -> Option<AlgorithmEntry> {
        parse_algorithm_entry(&self.index_data, offset as usize)
    }

    fn read_tradeoff(&mut self, index: u32) -> Option<TradeoffEntry> {
        if let Some(cached) = self.tradeoff_cache.get(&index) {
            return Some(*cached);
        }
        let offset = self.master.tradeoff_offset
            + (index as u64 * super::hypercube::TRADEOFF_ENTRY_SIZE as u64);
        let entry = parse_tradeoff_entry(&self.index_data, offset as usize)?;
        self.tradeoff_cache.insert(index, entry);
        Some(entry)
    }

    fn candidate_hashes(&self, operation_hash: u64) -> Vec<u64> {
        if operation_hash == hash_operation("sort") {
            return SORT_ALGORITHMS.iter().map(|name| hash_name(name)).collect();
        }
        if operation_hash == hash_operation("hash_search") || operation_hash == hash_operation("hash") {
            return HASH_ALGORITHMS.iter().map(|name| hash_name(name)).collect();
        }
        vec![operation_hash]
    }

    pub fn solve(&mut self, problem: ProblemSignature) -> Option<Solution> {
        let cache_key = problem.operation_type ^ problem.data_type;
        if let Some(cached) = self.algorithm_cache.get(&cache_key).copied() {
            return Some(self.build_solution(&cached));
        }

        let wanted = self.candidate_hashes(problem.operation_type);
        let mut candidates = Vec::new();
        let start = self.master.algorithm_offset;

        for i in 0..self.master.num_algorithms {
            let offset = start + (i * ALGORITHM_ENTRY_SIZE as u64);
            if let Some(entry) = self.read_algorithm_at(offset) {
                if wanted.contains(&entry.name_hash) {
                    candidates.push(entry);
                }
            }
        }

        if candidates.is_empty() {
            return None;
        }

        let best = self.rank_candidates(candidates, &problem)?;
        self.algorithm_cache.insert(cache_key, best);
        Some(self.build_solution(&best))
    }

    fn rank_candidates(
        &mut self,
        candidates: Vec<AlgorithmEntry>,
        problem: &ProblemSignature,
    ) -> Option<AlgorithmEntry> {
        if candidates.len() == 1 {
            return Some(candidates[0]);
        }

        let context = self.context.clone();
        let mut best_score = f32::MAX;
        let mut best = None;

        for entry in candidates {
            let tradeoff = self.read_tradeoff(entry.tradeoff_index)?;
            let mut score = 1.0
                - ((tradeoff.speed as f32 / 100.0) * context.speed_weight
                    + (tradeoff.memory as f32 / 100.0) * context.memory_weight
                    + (tradeoff.clarity as f32 / 100.0) * context.clarity_weight
                    + (tradeoff.safety as f32 / 100.0) * context.safety_weight
                    + (tradeoff.portability as f32 / 100.0) * context.portability_weight
                    + (tradeoff.energy as f32 / 100.0) * context.energy_weight
                    + (tradeoff.parallelism as f32 / 100.0) * context.parallelism_weight
                    + (tradeoff.realtime as f32 / 100.0) * context.realtime_weight)
                    / 8.0;

            if matches!(problem.size_hint, SizeHint::Tiny | SizeHint::Small) {
                if entry.name_hash == hash_name("insertion_sort") {
                    score -= 0.05;
                }
            }
            if matches!(problem.size_hint, SizeHint::Large | SizeHint::Huge) {
                if entry.name_hash == hash_name("timsort") {
                    score -= 0.08;
                }
            }

            if score < best_score {
                best_score = score;
                best = Some(entry);
            }
        }

        best
    }

    fn build_solution(&mut self, entry: &AlgorithmEntry) -> Solution {
        let tradeoff = self
            .read_tradeoff(entry.tradeoff_index)
            .unwrap_or(TradeoffEntry {
                speed: 50,
                memory: 50,
                clarity: 50,
                safety: 50,
                portability: 50,
                energy: 50,
                parallelism: 50,
                realtime: 50,
            });
        Solution {
            algorithm_hash: entry.name_hash,
            year: entry.discovery_year,
            paradigm: entry.paradigm_flags,
            complexity: entry.complexity_class,
            tradeoffs: tradeoff,
        }
    }

    pub fn algorithm_count(&self) -> u64 {
        self.master.num_algorithms
    }

    pub fn language_count(&self) -> u64 {
        self.master.num_languages
    }
}

pub fn hash_operation(name: &str) -> u64 {
    hash_name(name)
}

pub fn default_knowledge_path() -> String {
    format!(
        "{}/src/knowledge/hypercube",
        env!("CARGO_MANIFEST_DIR")
    )
}
