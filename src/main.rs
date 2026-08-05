#[cfg(not(target_arch = "wasm32"))]
mod cli;

#[cfg(not(target_arch = "wasm32"))]
fn main() {
    cli::run();
}

#[cfg(target_arch = "wasm32")]
fn main() {
    eprintln!("The frontier CLI is not available on wasm32 targets.");
}
