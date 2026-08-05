#!/usr/bin/env bash
# Package a self-contained demo bundle you can share or run offline.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="2.0.0"
OUT="dist/frontier-demo-${VERSION}"
ARCHIVE="dist/frontier-demo-${VERSION}.tar.gz"

echo "🔨 Building release binary..."
cargo build --release --bin frontier 2>&1 | tail -1

echo "📦 Packaging demo bundle..."
rm -rf "$OUT"
mkdir -p "$OUT/bin" "$OUT/examples" "$OUT/scripts"

cp target/release/frontier "$OUT/bin/"
cp examples/showcase.fr examples/sample.fr examples/v2_parser_test.fr "$OUT/examples/"
cp scripts/demo.sh scripts/verify_cli.sh "$OUT/scripts/"
cp DEMO.md "$OUT/README.md"

cat > "$OUT/run-demo.sh" << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
export PATH="$PWD/bin:$PATH"
./scripts/demo.sh "$@"
EOF
chmod +x "$OUT/run-demo.sh" "$OUT/scripts/"*.sh

mkdir -p dist
tar -czf "$ARCHIVE" -C dist "$(basename "$OUT")"

echo ""
echo "✅ Demo bundle ready:"
echo "   Directory: $OUT/"
echo "   Archive:   $ARCHIVE"
echo ""
echo "To share:"
echo "   scp $ARCHIVE user@host:~/"
echo ""
echo "To run locally:"
echo "   cd $OUT && ./run-demo.sh"
