//! Frontier Knowledge Module — dimensional solver integrated into the syntax library.

pub mod hypercube;
pub mod solver;

use solver::{hash_operation, ProblemSignature, SizeHint, Solver};

pub use solver::{Solver as KnowledgeSolver, SolverContext as KnowledgeContext, SizeHint as KnowledgeSizeHint};

fn open_solver() -> Solver {
    Solver::new(&solver::default_knowledge_path()).expect("Knowledge hypercube not found")
}

/// Automatically optimize a sort operation using 70+ years of algorithm history.
pub fn optimize_sort(data_type: &str, size_hint: SizeHint) -> (u16, u8) {
    let mut solver = open_solver();
    let problem = ProblemSignature {
        operation_type: hash_operation("sort"),
        data_type: hash_operation(data_type),
        size_hint,
        context_flags: 0,
    };

    if let Some(solution) = solver.solve(problem) {
        (solution.year, solution.complexity)
    } else {
        (1970, 3)
    }
}

/// Automatically optimize a hash operation.
pub fn optimize_hash(data_type: &str) -> (u16, u8) {
    let mut solver = open_solver();
    let problem = ProblemSignature {
        operation_type: hash_operation("hash_search"),
        data_type: hash_operation(data_type),
        size_hint: SizeHint::Unknown,
        context_flags: 0,
    };

    if let Some(solution) = solver.solve(problem) {
        (solution.year, solution.complexity)
    } else {
        (1953, 0)
    }
}

/// Get algorithm ancestry for a given operation category.
pub fn get_ancestors(op_name: &str) -> Vec<(&'static str, u16)> {
    match op_name {
        "sort" => vec![
            ("Merge Sort", 1945),
            ("Insertion Sort", 1960),
            ("Quick Sort", 1961),
            ("Timsort", 2002),
        ],
        "hash" | "hash_search" => vec![("Hash Search", 1953), ("Bloom Filter", 1970)],
        _ => vec![("Unknown", 0)],
    }
}

/// Get tradeoff matrix for an operation category (speed, memory, clarity, safety, portability).
pub fn get_tradeoffs(op_name: &str) -> Option<(u8, u8, u8, u8, u8)> {
    let mut solver = open_solver();
    let operation = match op_name {
        "hash" => hash_operation("hash_search"),
        _ => hash_operation(op_name),
    };
    let problem = ProblemSignature {
        operation_type: operation,
        data_type: 0,
        size_hint: SizeHint::Unknown,
        context_flags: 0,
    };
    solver.solve(problem).map(|s| {
        (
            s.tradeoffs.speed,
            s.tradeoffs.memory,
            s.tradeoffs.clarity,
            s.tradeoffs.safety,
            s.tradeoffs.portability,
        )
    })
}

/// Return hypercube statistics from the embedded index.
pub fn hypercube_stats() -> (u64, u64) {
    let solver = open_solver();
    (solver.algorithm_count(), solver.language_count())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sort_optimization() {
        let (year, complexity) = optimize_sort("list::i32", SizeHint::Large);
        assert!(year >= 1990);
        assert!(complexity <= 3);
    }

    #[test]
    fn test_hash_optimization() {
        let (year, complexity) = optimize_hash("String");
        assert!(year >= 1950);
        assert_eq!(complexity, 0);
    }

    #[test]
    fn test_ancestry_retrieval() {
        let ancestors = get_ancestors("sort");
        assert!(!ancestors.is_empty());
        assert!(ancestors[0].1 >= 1945);
    }

    #[test]
    fn test_tradeoff_retrieval() {
        let tradeoffs = get_tradeoffs("sort").expect("sort tradeoffs");
        assert!(tradeoffs.0 > 80);
        assert!(tradeoffs.4 > 80);
    }

    #[test]
    fn test_hypercube_loaded() {
        let (algos, langs) = hypercube_stats();
        assert!(algos >= 50);
        assert!(langs >= 50);
    }
}
