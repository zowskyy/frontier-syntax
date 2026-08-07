fn main() {
    println!("cargo:rerun-if-changed=frontier/core/");
    println!("cargo:rerun-if-changed=frontier/stdlib/");
    println!("cargo:rerun-if-changed=browser/");

    // Spec hook for knowledge/wasm_codegen/browser_compiler .frontier modules.
    // Rust implementations live in src/{knowledge_bridge,wasm_codegen,browser_compiler}.rs.
    // Intentionally no recursive `cargo run` here — that deadlocks the build script.
    note_frontier_core_modules();
}

fn note_frontier_core_modules() {
    for file in [
        "knowledge.frontier",
        "wasm_codegen.frontier",
        "browser_compiler.frontier",
    ] {
        let path = format!("frontier/core/{file}");
        if std::path::Path::new(&path).exists() {
            println!("cargo:rerun-if-changed={path}");
        }
    }
}
