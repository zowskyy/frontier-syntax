//! Frontier Knowledge Hypercube — binary format definitions.
//! All structures are packed for zero-overhead memory mapping.

pub const MAGIC: &[u8; 8] = b"FRONTIER";
pub const VERSION: u32 = 1;

pub const MASTER_INDEX_SIZE: usize = 124;
pub const ALGORITHM_ENTRY_SIZE: usize = 48;
pub const TRADEOFF_ENTRY_SIZE: usize = 8;
pub const LANGUAGE_ENTRY_SIZE: usize = 36;
pub const HARDWARE_ENTRY_SIZE: usize = 29;

#[derive(Debug, Clone, Copy)]
pub struct MasterIndex {
    pub magic: [u8; 8],
    pub version: u32,
    pub num_algorithms: u64,
    pub num_structures: u64,
    pub num_optimizations: u64,
    pub num_languages: u64,
    pub algorithm_offset: u64,
    pub structure_offset: u64,
    pub optimization_offset: u64,
    pub language_offset: u64,
    pub tradeoff_offset: u64,
    pub hardware_offset: u64,
    pub checksum: [u8; 32],
}

#[derive(Debug, Clone, Copy)]
pub struct AlgorithmEntry {
    pub name_hash: u64,
    pub discovery_year: u16,
    pub paradigm_flags: u8,
    pub complexity_class: u8,
    pub impl_offset: u64,
    pub impl_size: u32,
    pub tradeoff_index: u32,
    pub hardware_compat: u64,
    pub dependencies: u64,
    pub num_dependencies: u32,
}

#[derive(Debug, Clone, Copy)]
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

#[derive(Debug, Clone, Copy)]
pub struct LanguageEntry {
    pub name_hash: u64,
    pub birth_year: u16,
    pub paradigm_flags: u8,
    pub parent_count: u16,
    pub parent_offset: u64,
    pub child_count: u16,
    pub child_offset: u64,
    pub influence_radius: u8,
    pub domain_flags: u32,
}

#[derive(Debug, Clone, Copy)]
pub struct HardwareEntry {
    pub name_hash: u64,
    pub architecture: u8,
    pub cache_line: u16,
    pub page_size: u32,
    pub available_simd: u16,
    pub memory_latency: u8,
    pub branch_penalty: u8,
    pub vector_width: u16,
    pub features: u64,
}

fn read_u16(data: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes([data[offset], data[offset + 1]])
}

fn read_u32(data: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes([
        data[offset],
        data[offset + 1],
        data[offset + 2],
        data[offset + 3],
    ])
}

fn read_u64(data: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes([
        data[offset],
        data[offset + 1],
        data[offset + 2],
        data[offset + 3],
        data[offset + 4],
        data[offset + 5],
        data[offset + 6],
        data[offset + 7],
    ])
}

pub fn parse_master_index(data: &[u8]) -> Option<MasterIndex> {
    if data.len() < MASTER_INDEX_SIZE {
        return None;
    }
    let mut magic = [0u8; 8];
    magic.copy_from_slice(&data[0..8]);
    if &magic != MAGIC {
        return None;
    }
    Some(MasterIndex {
        magic,
        version: read_u32(data, 8),
        num_algorithms: read_u64(data, 12),
        num_structures: read_u64(data, 20),
        num_optimizations: read_u64(data, 28),
        num_languages: read_u64(data, 36),
        algorithm_offset: read_u64(data, 44),
        structure_offset: read_u64(data, 52),
        optimization_offset: read_u64(data, 60),
        language_offset: read_u64(data, 68),
        tradeoff_offset: read_u64(data, 76),
        hardware_offset: read_u64(data, 84),
        checksum: data[92..124].try_into().ok()?,
    })
}

pub fn parse_algorithm_entry(data: &[u8], offset: usize) -> Option<AlgorithmEntry> {
    if data.len() < offset + ALGORITHM_ENTRY_SIZE {
        return None;
    }
    Some(AlgorithmEntry {
        name_hash: read_u64(data, offset),
        discovery_year: read_u16(data, offset + 8),
        paradigm_flags: data[offset + 10],
        complexity_class: data[offset + 11],
        impl_offset: read_u64(data, offset + 12),
        impl_size: read_u32(data, offset + 20),
        tradeoff_index: read_u32(data, offset + 24),
        hardware_compat: read_u64(data, offset + 28),
        dependencies: read_u64(data, offset + 36),
        num_dependencies: read_u32(data, offset + 44),
    })
}

pub fn parse_tradeoff_entry(data: &[u8], offset: usize) -> Option<TradeoffEntry> {
    if data.len() < offset + TRADEOFF_ENTRY_SIZE {
        return None;
    }
    Some(TradeoffEntry {
        speed: data[offset],
        memory: data[offset + 1],
        clarity: data[offset + 2],
        safety: data[offset + 3],
        portability: data[offset + 4],
        energy: data[offset + 5],
        parallelism: data[offset + 6],
        realtime: data[offset + 7],
    })
}

pub fn hash_name(name: &str) -> u64 {
    let mut hash = 0x9e3779b97f4a7c15u64;
    for byte in name.as_bytes() {
        hash ^= *byte as u64;
        hash = hash.wrapping_mul(0x9e3779b97f4a7c15);
    }
    hash
}
