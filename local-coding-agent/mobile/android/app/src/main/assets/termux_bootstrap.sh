#!/data/data/com.termux/files/usr/bin/bash
# Local Coding Agent — Termux bootstrap (offline-first)
pkg update -y && pkg install -y python clang cmake git
pip install --user local-coding-agent==0.1.0rc1
mkdir -p ~/models && agent benchmark --profile android
