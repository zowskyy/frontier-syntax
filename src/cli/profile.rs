use frontier::wasm_codegen::CompilationProfile;

pub fn print_profile(profile: &CompilationProfile) {
    println!("\n📊 Compilation Profile");
    println!("  Lexing:            {:>8} ms", profile.lexing_time);
    println!("  Parsing:           {:>8} ms", profile.parsing_time);
    println!("  Type checking:     {:>8} ms", profile.type_check_time);
    println!("  Knowledge lookup:  {:>8} ms", profile.knowledge_lookup_time);
    println!("  Code generation:   {:>8} ms", profile.codegen_time);
    println!("  ─────────────────────────────");
    println!("  Total:             {:>8} ms", profile.total_time);
}
