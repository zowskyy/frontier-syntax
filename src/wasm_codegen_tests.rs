use super::*;
use crate::wasm_binary::export_section_static;

#[test]
fn test_compile_simple_main() {
        let source = r#"version: 2.0;
fn main(): int {
    return 42;
}"#;
        let (wasm, meta) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
        assert_eq!(meta.entry_value, 42);
    }

    #[test]
    fn test_wasm_magic() {
        let program = crate::parser::parse_source_typed("fn main(): int { return 7; }").unwrap();
        let (wasm, meta) = compile_program(&program, &CodeGenOptions::default()).unwrap();
        assert_eq!(meta.entry_value, 7);
        assert!(wasm.len() > 8);
    }

    #[test]
    fn test_let_and_if() {
        let source = r#"fn main(): int {
    let x: int = 10;
    if (x > 5) {
        return x;
    }
    return 0;
}"#;
        let (wasm, _) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
        assert!(wasm.len() > 40);
    }

    #[test]
    fn test_function_call() {
        let source = r#"fn double(x: int) -> int {
    return x * 2;
}
fn main(): int {
    return double(21);
}"#;
        let (wasm, _) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
        assert!(wasm.len() > 60);
    }

    #[test]
    fn test_while_loop() {
        let source = r#"fn main(): int {
    let x: int = 3;
    while (x > 0) {
        return 0;
    }
    return x;
}"#;
        let (wasm, _) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(wasm.starts_with(b"\0asm"));
    }

    #[test]
    fn test_mut_reassign_while_loop() {
        let source = r#"fn main(): int {
    let mut x: int = 0;
    let mut i: int = 0;
    while (i < 5) {
        if (i == 3) {
            x = x + 100;
        } else {
            x = x + 1;
        }
        i = i + 1;
    }
    return x;
}"#;
        let (wasm, _) = compile_source(
            source,
            &CodeGenOptions {
                optimize: false,
                browser_exports: false,
                collect_profile: false,
                algorithm_hint: None,
            },
        )
        .expect("compile");
        assert!(wasm.starts_with(b"\0asm"));

        let engine = wasmtime::Engine::default();
        let module = wasmtime::Module::new(&engine, wasm).expect("wasm module");
        let mut store = wasmtime::Store::new(&engine, ());
        let instance = wasmtime::Instance::new(&mut store, &module, &[]).expect("instance");
        let main = instance
            .get_typed_func::<(), i32>(&mut store, "main")
            .expect("main export");
        let result = main.call(&mut store, ()).expect("invoke main");
        assert_eq!(result, 104);
    }

    #[test]
    fn test_knowledge_changes_wasm() {
        let source = "fn main(): int { return 42; }";
        let (wasm_off, _) = compile_source(
            source,
            &CodeGenOptions {
                optimize: false,
                browser_exports: false,
                collect_profile: false,
                algorithm_hint: None,
            },
        )
        .expect("compile");
        let (wasm_on, meta) = compile_source(source, &CodeGenOptions::default()).expect("compile");
        assert!(meta.selected_algorithm.is_some());
        assert_ne!(wasm_off, wasm_on, "knowledge optimization must change emitted WASM");
    }

    #[test]
    fn test_float_literal_rejected() {
        let source = "fn main(): int { return 3.14; }";
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("Float literals"));
    }

    #[test]
    fn test_string_literal_rejected() {
        let source = r#"fn main(): int { return "hi"; }"#;
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("String literals"));
    }

    #[test]
    fn test_missing_main_rejected() {
        let source = "fn helper(): int { return 1; }";
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("fn main()"));
    }

    #[test]
    fn test_import_decl_rejected() {
        let source = r#"import "bar" as foo;
fn main(): int { return 0; }"#;
        let err = compile_source(source, &CodeGenOptions::default()).unwrap_err();
        assert!(err.contains("Import declarations"));
    }

    #[test]
    fn test_browser_exports_section_indices() {
        let payload = export_section_static(
            &["main", "compile_wasm", "validate_wasm", "evaluate_wasm", "memory"],
            2,
        );
        // Export section payload: count + entries (name, kind, index)
        // main=0, compile_wasm=2, validate_wasm=3, evaluate_wasm=4, memory=0
        assert!(!payload.is_empty());
        let names = ["main", "compile_wasm", "validate_wasm", "evaluate_wasm", "memory"];
        let mut offset = 0usize;
        let (count, n) = decode_u32(&payload[offset..]);
        offset += n;
        assert_eq!(count, names.len() as u32);
        let mut seen = Vec::new();
        for _ in 0..count {
            let (name, n) = decode_name(&payload[offset..]);
            offset += n;
            let kind = payload[offset];
            offset += 1;
            let (index, n) = decode_u32(&payload[offset..]);
            offset += n;
            seen.push((name, kind, index));
        }
        assert_eq!(seen[0], ("main".to_string(), 0x00, 0));
        assert_eq!(seen[1], ("compile_wasm".to_string(), 0x00, 2));
        assert_eq!(seen[2], ("validate_wasm".to_string(), 0x00, 3));
        assert_eq!(seen[3], ("evaluate_wasm".to_string(), 0x00, 4));
    }

    fn decode_u32(bytes: &[u8]) -> (u32, usize) {
        let mut result = 0u32;
        let mut shift = 0;
        for (i, &b) in bytes.iter().enumerate() {
            result |= ((b & 0x7f) as u32) << shift;
            if b & 0x80 == 0 {
                return (result, i + 1);
            }
            shift += 7;
        }
        panic!("invalid u32");
    }

fn decode_name(bytes: &[u8]) -> (String, usize) {
    let (len, n) = decode_u32(bytes);
    let start = n;
    let end = start + len as usize;
    let name = String::from_utf8(bytes[start..end].to_vec()).unwrap();
    (name, end)
}
