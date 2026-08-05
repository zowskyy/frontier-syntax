use criterion::{black_box, criterion_group, criterion_main, Criterion, Throughput};
use frontier::{compile_to_object, parse_program, resolve_program};
use std::path::PathBuf;

fn make_source(size_kb: usize) -> String {
    let line = "let x: int = 42;\n";
    let count = (size_kb * 1024) / line.len().max(1);
    line.repeat(count)
}

fn bench_parse(c: &mut Criterion) {
    let mut group = c.benchmark_group("parse");
    for size in [1, 100, 1024] {
        let source = make_source(size);
        group.throughput(Throughput::Bytes(source.len() as u64));
        group.bench_function(format!("{}KB", size), |b| {
            b.iter(|| parse_program(black_box(&source), 64))
        });
    }
    group.finish();
}

fn bench_resolve(c: &mut Criterion) {
    let source = make_source(100);
    let program = parse_program(&source, 64).unwrap();
    c.bench_function("resolve_100KB", |b| {
        b.iter(|| resolve_program(black_box(&program)))
    });
}

fn bench_codegen(c: &mut Criterion) {
    let source = std::fs::read_to_string("examples/sample.fr").unwrap();
    let program = parse_program(&source, 64).unwrap();
    c.bench_function("codegen_sample", |b| {
        b.iter(|| {
            let tmp = PathBuf::from("/tmp/frontier_bench.o");
            let _ = compile_to_object(black_box(&program), &tmp);
        })
    });
}

criterion_group!(benches, bench_parse, bench_resolve, bench_codegen);
criterion_main!(benches);
