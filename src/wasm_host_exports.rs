//! C ABI exports for wasmtime native self-host host (`frontier_wasm_host`).

#[cfg(all(target_arch = "wasm32", feature = "wasm-slim"))]
mod imp {
    /// Compile Frontier source from guest linear memory.
    /// Returns bytes written to output buffer, or negative error code.
    #[no_mangle]
    pub unsafe extern "C" fn compile_fr(
        input_off: i32,
        input_len: i32,
        output_off: i32,
        output_max: i32,
    ) -> i32 {
        if input_len < 0 || output_max <= 0 || input_off < 0 || output_off < 0 {
            return -1;
        }
        let input_ptr = input_off as *const u8;
        let output_ptr = output_off as *mut u8;
        let source = match core::str::from_utf8(core::slice::from_raw_parts(
            input_ptr,
            input_len as usize,
        )) {
            Ok(s) => s,
            Err(_) => return -2,
        };
        match crate::wasm_codegen::compile_to_wasm_bytes(source) {
            Ok(wasm) => {
                if wasm.len() > output_max as usize {
                    return -3;
                }
                core::ptr::copy_nonoverlapping(wasm.as_ptr(), output_ptr, wasm.len());
                wasm.len() as i32
            }
            Err(_) => -4,
        }
    }
}

#[cfg(not(all(target_arch = "wasm32", feature = "wasm-slim")))]
mod imp {}
