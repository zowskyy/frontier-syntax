//! Native wasmtime host — run Frontier compiler WASM without Rust bootstrap.run.

use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;

use wasmtime::{Engine, Instance, Module, Store};

const INPUT_OFF: i32 = 0;
const OUTPUT_OFF: i32 = 65536;
const OUTPUT_MAX: i32 = 512 * 1024;

fn usage() -> ! {
    eprintln!(
        "usage:\n  frontier_wasm_host <compiler.wasm> <source.fr> -o <out.wasm>\n  frontier_wasm_host --genesis <source.fr> -o <out.wasm>"
    );
    process::exit(2);
}

fn compile_native_genesis(source: &str) -> Result<Vec<u8>, String> {
    let options = frontier::wasm_codegen::CodeGenOptions {
        optimize: false,
        browser_exports: false,
        collect_profile: false,
        algorithm_hint: None,
    };
    frontier::wasm_codegen::compile_source(source, &options).map(|(wasm, _)| wasm)
}

fn compile_via_wasmtime(compiler_wasm: &PathBuf, source: &str) -> Result<Vec<u8>, String> {
    let wasm_bytes = fs::read(compiler_wasm).map_err(|e| e.to_string())?;
    let engine = Engine::default();
    let module = Module::new(&engine, wasm_bytes).map_err(|e| e.to_string())?;
    let mut store = Store::new(&engine, ());
    let instance = Instance::new(&mut store, &module, &[]).map_err(|e| e.to_string())?;
    let memory = instance
        .get_memory(&mut store, "memory")
        .ok_or_else(|| "compiler wasm missing memory export".to_string())?;
    // Ensure enough pages for input + output buffers
    let need_bytes = (OUTPUT_OFF + OUTPUT_MAX) as u64;
    let page_size = 65536u64;
    let need_pages = (need_bytes + page_size - 1) / page_size;
    let current_pages = memory.size(&store) as u64;
    if need_pages > current_pages {
        memory
            .grow(&mut store, (need_pages - current_pages) as u64)
            .map_err(|e| e.to_string())?;
    }
    let compile_fr = instance
        .get_typed_func::<(i32, i32, i32, i32), i32>(&mut store, "compile_fr")
        .map_err(|e| e.to_string())?;

    let src_bytes = source.as_bytes();
    memory
        .write(&mut store, INPUT_OFF as usize, src_bytes)
        .map_err(|e| e.to_string())?;

    let written = compile_fr
        .call(
            &mut store,
            (
                INPUT_OFF,
                src_bytes.len() as i32,
                OUTPUT_OFF,
                OUTPUT_MAX,
            ),
        )
        .map_err(|e| e.to_string())?;

    if written < 0 {
        return Err(format!("compile_fr error code {written}"));
    }
    let mut out = vec![0u8; written as usize];
    memory
        .read(&store, OUTPUT_OFF as usize, &mut out)
        .map_err(|e| e.to_string())?;
    Ok(out)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        usage();
    }

    let genesis = args[1] == "--genesis";
    let (compiler_wasm, source_path, output_path) = if genesis {
        if args.len() < 5 || args[3] != "-o" {
            usage();
        }
        (
            None,
            PathBuf::from(&args[2]),
            PathBuf::from(&args[4]),
        )
    } else {
        if args.len() < 5 || args[3] != "-o" {
            usage();
        }
        (
            Some(PathBuf::from(&args[1])),
            PathBuf::from(&args[2]),
            PathBuf::from(&args[4]),
        )
    };

    let source = fs::read_to_string(&source_path).unwrap_or_else(|e| {
        eprintln!("read {}: {e}", source_path.display());
        process::exit(1);
    });

    let wasm = if genesis {
        compile_native_genesis(&source).unwrap_or_else(|e| {
            eprintln!("genesis compile failed: {e}");
            process::exit(1);
        })
    } else {
        compile_via_wasmtime(compiler_wasm.as_ref().unwrap(), &source).unwrap_or_else(|e| {
            eprintln!("wasmtime compile failed: {e}");
            process::exit(1);
        })
    };

    fs::write(&output_path, &wasm).unwrap_or_else(|e| {
        eprintln!("write {}: {e}", output_path.display());
        process::exit(1);
    });
    println!("OK: {} ({} bytes)", output_path.display(), wasm.len());
}
