use frontier::lsp::run_server;
use std::env;
use std::path::PathBuf;

#[tokio::main]
async fn main() {
    let wasm_path = env::var("FRONTIER_WASM_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("syntax/wasm_parser.wasm")
        });
    run_server(wasm_path).await;
}
