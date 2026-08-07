class FrontierSyntax < Formula
  desc "Formally verifiable programming language — A+ Hard Gate certified"
  homepage "https://github.com/zowskyy/frontier-syntax"
  url "https://github.com/zowskyy/frontier-syntax/archive/refs/tags/v1.0.0-a-plus-certified.tar.gz"
  version "1.0.0"
  license "MIT"

  depends_on "rust" => :build
  depends_on "llvm" => :build

  def install
    system "cargo", "build", "--release"
    bin.install "target/release/frontier"
    bin.install "target/release/lsp"
    bin.install "target/release/repl"
  end

  test do
    assert_match "Frontier", shell_output("#{bin}/frontier 2>&1 || true")
  end
end
