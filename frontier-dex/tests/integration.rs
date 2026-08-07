//! Integration tests for frontier-dex end-to-end pipeline.

use std::path::PathBuf;

use frontier_dex::parser::parse_dex;
use frontier_dex::{DecompileOptions, Decompiler};

fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(name)
}

#[test]
fn integration_decompile_pipeline() {
    let mut dex = vec![0u8; 512];
    dex[0..8].copy_from_slice(b"dex\n035\0");
    dex[32] = 0x00;
    dex[33] = 0x02;
    dex[36] = 0x70;
    dex[40] = 0x78;
    dex[41] = 0x56;
    dex[42] = 0x34;
    dex[43] = 0x12;
    dex[52] = 0x70;
    dex[112] = 1;
    dex[116] = 0;
    dex[117] = 0;
    dex[120] = 1;

    let options = DecompileOptions {
        generate_proof: true,
        neural: true,
        cache: true,
        fallback_engines: true,
    };
    let mut dec = Decompiler::new(options);
    let result = dec.decompile_bytes(&dex).expect("pipeline");
    assert!(result.proof_hash.is_some());
}

#[test]
fn integration_fixture_minimal_dex() {
    let path = fixture_path("minimal.dex");
    let bytes = std::fs::read(&path).expect("read minimal.dex fixture");
    let dex = parse_dex(&bytes).expect("parse minimal.dex");
    assert_eq!(dex.header.magic[0..4], *b"dex\n");
    assert_eq!(dex.classes.len(), 1);
    assert_eq!(dex.classes[0].class_name, "LHello;");
    assert!(!dex.classes[0].methods.is_empty());

    let mut dec = Decompiler::new(DecompileOptions {
        generate_proof: false,
        neural: false,
        cache: false,
        fallback_engines: false,
    });
    let result = dec.decompile_bytes(&bytes).expect("decompile minimal.dex");
    assert_eq!(result.engine_used, "frontier-dex");
    assert!(!result.java_sources.is_empty());
    assert!(result.java_sources[0].source.contains("Hello"));
}

#[test]
fn integration_proof_verifier() {
    use frontier_dex::verifier::ProofVerifier;
    let v = ProofVerifier::new();
    let combined = v.combine(&["parse:a".into(), "opt:b".into()]).unwrap();
    assert_eq!(combined.len(), 64);
}
