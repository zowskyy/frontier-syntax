#!/usr/bin/env bash
# Idempotent Cloud Agent install for Frontier Syntax.
# Prepares the Rust toolchain, the wasm32 target, a matching wasm-bindgen CLI,
# and warms the build cache so agents can build/test/run immediately.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Frontier install: $(rustc --version) / $(cargo --version)"

# 1. wasm32 target for the browser/WASM compiler pipeline.
echo "==> Ensuring wasm32-unknown-unknown target is installed"
rustup target add wasm32-unknown-unknown

# 2. Install a wasm-bindgen CLI that matches the version pinned in Cargo.lock.
WB_VERSION="$(awk '/^name = "wasm-bindgen"$/{getline; gsub(/[",]/,"",$3); print $3; exit}' Cargo.lock)"
if [ -z "${WB_VERSION:-}" ]; then
  echo "!! Could not determine wasm-bindgen version from Cargo.lock" >&2
  exit 1
fi
echo "==> Required wasm-bindgen CLI version: ${WB_VERSION}"

install_wasm_bindgen() {
  local ver="$1"
  local tmp triple url
  triple="x86_64-unknown-linux-musl"
  url="https://github.com/rustwasm/wasm-bindgen/releases/download/${ver}/wasm-bindgen-${ver}-${triple}.tar.gz"
  tmp="$(mktemp -d)"
  if curl -fsSL "$url" -o "$tmp/wb.tar.gz"; then
    tar xzf "$tmp/wb.tar.gz" -C "$tmp"
    install -m 0755 "$tmp/wasm-bindgen-${ver}-${triple}/wasm-bindgen" "$(dirname "$(command -v cargo)")/wasm-bindgen"
    rm -rf "$tmp"
    return 0
  fi
  rm -rf "$tmp"
  echo "==> Prebuilt download failed; falling back to 'cargo install wasm-bindgen-cli'"
  cargo install wasm-bindgen-cli --version "$ver" --locked
}

if command -v wasm-bindgen >/dev/null 2>&1 && [ "$(wasm-bindgen --version | awk '{print $2}')" = "$WB_VERSION" ]; then
  echo "==> wasm-bindgen ${WB_VERSION} already installed"
else
  install_wasm_bindgen "$WB_VERSION"
fi
echo "==> wasm-bindgen: $(wasm-bindgen --version)"

# 3. Fetch dependencies and warm the build cache (native binaries + wasm).
echo "==> Fetching crate dependencies"
cargo fetch --locked

echo "==> Building workspace (native binaries: frontier, lighthouse, lsp)"
cargo build --workspace

echo "==> Building release wasm32 browser artifact (lib, full feature)"
# The in-browser BrowserCompiler API lives in the cdylib and needs the `full`
# feature (serde-wasm-bindgen). The native-only bins (repl, frontier_wasm_host)
# cannot target wasm32, so restrict this to the library target.
cargo build --release --lib --target wasm32-unknown-unknown --features full

echo "==> Frontier install complete"
