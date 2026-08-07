pub mod llvm;
pub mod optimizer;

pub use llvm::{compile_to_object, generate_module};
pub use optimizer::optimize_ir;
