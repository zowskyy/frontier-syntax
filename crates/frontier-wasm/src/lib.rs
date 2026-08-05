//! WASM exports for Lighthouse browser-compiler.js
//!
//! Exports: alloc, free, memory, parse, compile, get_targets, get_result_length

use frontier_lexer::Lexer;
use serde::{Deserialize, Serialize};
use std::alloc::{alloc as heap_alloc, dealloc, Layout};
use std::ptr;
use std::slice;
use std::sync::OnceLock;

static LEXER: OnceLock<Lexer> = OnceLock::new();
static mut RESULT_BUF: Vec<u8> = Vec::new();

const CYCLE1_TABLE: &str = include_str!("../../../syntax/token_regex_table.json");
const CYCLE2_EXT: &str = include_str!("../../../syntax/cycle2/extensions.json");

fn lexer() -> &'static Lexer {
    LEXER.get_or_init(|| {
        Lexer::from_tables(CYCLE1_TABLE, Some(CYCLE2_EXT)).expect("lexer init")
    })
}

#[no_mangle]
pub extern "C" fn alloc(size: usize) -> *mut u8 {
    if size == 0 {
        return ptr::null_mut();
    }
    let layout = Layout::from_size_align(size, 1).unwrap();
    unsafe { heap_alloc(layout) }
}

#[no_mangle]
pub extern "C" fn free(ptr: *mut u8, size: usize) {
    if ptr.is_null() || size == 0 {
        return;
    }
    let layout = Layout::from_size_align(size, 1).unwrap();
    unsafe { dealloc(ptr, layout) }
}

#[no_mangle]
pub extern "C" fn get_result_length(ptr: usize) -> usize {
    if ptr == 0 {
        return 0;
    }
    unsafe { RESULT_BUF.len() }
}

fn store_result(bytes: Vec<u8>) -> usize {
    unsafe {
        RESULT_BUF = bytes;
        RESULT_BUF.as_ptr() as usize
    }
}

#[derive(Deserialize)]
struct WasmInput {
    source: String,
    target: Option<String>,
}

#[derive(Serialize)]
struct ParseOutput {
    valid: bool,
    token_count: usize,
    errors: Vec<serde_json::Value>,
}

#[derive(Serialize)]
struct CompileOutput {
    success: bool,
    binary: Option<Vec<u8>>,
    target: String,
    size: usize,
    compiled_in: String,
    error: Option<String>,
}

#[no_mangle]
pub extern "C" fn parse(ptr: usize, len: usize) -> usize {
    let input = read_json_input(ptr, len);
    let result = lexer().lex(&input.source);
    let out = ParseOutput {
        valid: result.valid,
        token_count: result.tokens.len(),
        errors: result
            .errors
            .iter()
            .map(|e| {
                serde_json::json!({
                    "message": e.message,
                    "line": e.line,
                    "column": e.column
                })
            })
            .collect(),
    };
    store_result(serde_json::to_vec(&out).unwrap_or_default())
}

#[no_mangle]
pub extern "C" fn compile(ptr: usize, len: usize) -> usize {
    let input = read_json_input(ptr, len);
    let target = input.target.unwrap_or_else(|| "linux-x64".into());
    let lex = lexer().lex(&input.source);

    if !lex.valid {
        let out = CompileOutput {
            success: false,
            binary: None,
            target: target.clone(),
            size: 0,
            compiled_in: "browser-wasm".into(),
            error: Some("syntax validation failed".into()),
        };
        return store_result(serde_json::to_vec(&out).unwrap_or_default());
    }

    let binary = build_capsule(&input.source, &target, lex.tokens.len());
    let size = binary.len();
    let out = CompileOutput {
        success: true,
        binary: Some(binary),
        target,
        size,
        compiled_in: "browser-wasm".into(),
        error: None,
    };
    store_result(serde_json::to_vec(&out).unwrap_or_default())
}

#[no_mangle]
pub extern "C" fn get_targets(_ptr: usize, _len: usize) -> usize {
    let targets = [
        ("linux-x64", "Linux Binary", ""),
        ("linux-arm64", "Linux ARM64 (Raspberry Pi 4/5)", ""),
        ("windows-x64", "Windows .exe", ".exe"),
        ("macos-arm64", "macOS Apple Silicon", ""),
        ("android-arm64", "Android ARM64", ".apk"),
        ("ios-arm64", "iOS ARM64", ".ipa"),
        ("rpi-zero", "Raspberry Pi Zero", ""),
        ("riscv64", "RISC-V 64", ""),
    ];
    let json: Vec<serde_json::Value> = targets
        .iter()
        .map(|(id, label, ext)| serde_json::json!({ "id": id, "label": label, "ext": ext }))
        .collect();
    store_result(serde_json::to_vec(&json).unwrap_or_default())
}

fn read_json_input(ptr: usize, len: usize) -> WasmInput {
    if ptr == 0 || len == 0 {
        return WasmInput {
            source: String::new(),
            target: None,
        };
    }
    let bytes = unsafe { slice::from_raw_parts(ptr as *const u8, len) };
    let text = String::from_utf8_lossy(bytes);
    serde_json::from_str(&text).unwrap_or(WasmInput {
        source: text.to_string(),
        target: None,
    })
}

fn build_capsule(source: &str, target: &str, token_count: usize) -> Vec<u8> {
    let meta = serde_json::json!({
        "magic": "LHN1",
        "target": target,
        "mode": "wasm-compiler",
        "tokenCount": token_count,
        "version": "2.0.0"
    });
    let meta_bytes = meta.to_string().into_bytes();
    let src_bytes = source.as_bytes();
    let mut out = Vec::with_capacity(8 + meta_bytes.len() + src_bytes.len());
    out.extend_from_slice(&(meta_bytes.len() as u32).to_le_bytes());
    out.extend_from_slice(&meta_bytes);
    out.extend_from_slice(&(src_bytes.len() as u32).to_le_bytes());
    out.extend_from_slice(src_bytes);
    out
}
