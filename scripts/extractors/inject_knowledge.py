#!/usr/bin/env python3
"""Frontier Knowledge Injector — embeds historical knowledge into the syntax library."""

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "src" / "knowledge" / "hypercube"

ALGORITHMS = [
    ("bubble_sort", 1962, ["imperative"], "O(n^2)", 20, 90, 95, 100, 100, 80, 10, 50),
    ("insertion_sort", 1960, ["imperative"], "O(n^2)", 25, 95, 95, 100, 100, 85, 10, 60),
    ("merge_sort", 1945, ["functional", "imperative"], "O(n log n)", 80, 70, 75, 85, 95, 75, 60, 70),
    ("quick_sort", 1961, ["functional", "imperative"], "O(n log n)", 95, 75, 80, 60, 95, 80, 50, 60),
    ("heap_sort", 1964, ["imperative"], "O(n log n)", 85, 80, 70, 70, 95, 80, 40, 65),
    ("shell_sort", 1959, ["imperative"], "O(n log n)", 70, 85, 65, 80, 95, 75, 20, 60),
    ("timsort", 2002, ["imperative", "functional"], "O(n log n)", 92, 80, 65, 85, 95, 85, 70, 70),
    ("radix_sort", 1887, ["imperative"], "O(n)", 98, 60, 40, 70, 70, 90, 80, 50),
    ("counting_sort", 1954, ["imperative"], "O(n)", 95, 50, 35, 70, 60, 85, 70, 50),
    ("introspective_sort", 1997, ["imperative"], "O(n log n)", 90, 75, 65, 75, 95, 80, 50, 65),
    ("block_sort", 2008, ["imperative", "functional"], "O(n log n)", 88, 78, 55, 80, 90, 85, 75, 65),
    ("linear_search", 1950, ["imperative"], "O(n)", 50, 100, 95, 100, 100, 70, 10, 60),
    ("binary_search", 1946, ["functional", "imperative"], "O(log n)", 90, 95, 90, 95, 95, 85, 30, 80),
    ("interpolation_search", 1957, ["imperative"], "O(log log n)", 70, 80, 60, 75, 80, 75, 20, 70),
    ("exponential_search", 1990, ["imperative"], "O(log n)", 85, 85, 65, 85, 90, 80, 40, 75),
    ("fibonacci_search", 1960, ["imperative"], "O(log n)", 75, 85, 55, 80, 90, 75, 30, 70),
    ("hash_search", 1953, ["imperative", "functional"], "O(1)", 95, 70, 70, 85, 85, 85, 80, 70),
    ("dijkstra", 1956, ["imperative", "functional"], "O(n log n)", 80, 70, 70, 85, 90, 80, 50, 85),
    ("bellman_ford", 1958, ["imperative"], "O(n^2)", 60, 75, 65, 85, 95, 70, 30, 80),
    ("floyd_warshall", 1962, ["imperative", "functional"], "O(n^2)", 50, 60, 60, 80, 95, 60, 20, 75),
    ("kruskal", 1956, ["imperative", "functional"], "O(n log n)", 75, 75, 70, 85, 90, 75, 40, 80),
    ("prim", 1957, ["imperative"], "O(n log n)", 80, 75, 70, 85, 90, 75, 40, 80),
    ("a_star", 1968, ["functional", "imperative"], "O(n^2)", 85, 60, 65, 70, 80, 75, 30, 85),
    ("pagerank", 1998, ["functional", "imperative"], "O(n)", 70, 50, 40, 60, 80, 65, 70, 60),
    ("kmp_search", 1977, ["imperative"], "O(n)", 85, 80, 70, 80, 95, 75, 30, 70),
    ("boyer_moore", 1977, ["imperative"], "O(n)", 90, 75, 65, 75, 95, 80, 30, 70),
    ("rabin_karp", 1987, ["imperative", "functional"], "O(n)", 80, 70, 65, 70, 85, 75, 40, 65),
    ("aho_corasick", 1975, ["imperative"], "O(n)", 85, 65, 60, 75, 90, 75, 40, 70),
    ("levenshtein", 1965, ["functional", "imperative"], "O(n^2)", 50, 60, 70, 80, 95, 55, 20, 65),
    ("fft", 1965, ["functional", "imperative"], "O(n log n)", 90, 60, 50, 65, 80, 85, 80, 70),
    ("strassen", 1969, ["imperative"], "O(n^2)", 85, 50, 40, 60, 70, 80, 70, 65),
    ("karatsuba", 1960, ["functional", "imperative"], "O(n log n)", 80, 55, 55, 70, 80, 75, 60, 65),
    ("montgomery", 1985, ["imperative"], "O(n)", 85, 70, 50, 70, 60, 80, 50, 75),
    ("gcd", 300, ["functional", "imperative"], "O(log n)", 95, 95, 90, 100, 100, 85, 10, 90),
    ("huffman", 1952, ["imperative", "functional"], "O(n log n)", 80, 70, 70, 80, 95, 65, 30, 60),
    ("lz77", 1977, ["imperative"], "O(n)", 85, 60, 55, 70, 80, 70, 40, 60),
    ("lz78", 1978, ["imperative"], "O(n)", 85, 60, 55, 70, 80, 70, 40, 60),
    ("deflate", 1993, ["imperative"], "O(n)", 88, 55, 50, 65, 80, 75, 40, 65),
    ("bzip2", 1996, ["imperative"], "O(n)", 75, 50, 45, 60, 75, 70, 30, 60),
    ("zstandard", 2015, ["imperative"], "O(n)", 90, 55, 45, 65, 80, 80, 50, 65),
    ("mutex", 1965, ["imperative"], "O(1)", 70, 85, 70, 90, 100, 65, 50, 85),
    ("spinlock", 1970, ["imperative"], "O(1)", 90, 80, 60, 75, 95, 70, 40, 80),
    ("semaphore", 1965, ["imperative"], "O(1)", 75, 85, 65, 85, 100, 70, 45, 85),
    ("rw_lock", 1975, ["imperative"], "O(1)", 65, 80, 60, 80, 100, 65, 50, 80),
    ("mcs_lock", 1989, ["imperative"], "O(1)", 85, 75, 55, 80, 90, 70, 55, 80),
    ("rcu", 1980, ["imperative"], "O(1)", 80, 70, 45, 90, 80, 75, 60, 85),
    ("malloc", 1965, ["imperative"], "O(1)", 70, 70, 60, 70, 95, 65, 30, 70),
    ("buddy_alloc", 1965, ["imperative"], "O(log n)", 75, 65, 55, 70, 90, 65, 30, 70),
    ("slab_alloc", 1994, ["imperative"], "O(1)", 85, 75, 55, 70, 80, 70, 40, 70),
    ("arena_alloc", 1980, ["imperative"], "O(1)", 90, 80, 60, 70, 85, 75, 40, 70),
    ("pool_alloc", 1980, ["imperative"], "O(1)", 85, 80, 65, 75, 85, 70, 35, 70),
    ("gc_mark_sweep", 1960, ["imperative", "functional"], "O(n)", 60, 50, 50, 85, 70, 60, 50, 65),
    ("gc_reference_count", 1960, ["imperative", "functional"], "O(1)", 75, 55, 60, 80, 80, 65, 60, 70),
]

LANGUAGES = [
    ("AnalyticalEngine", 1837, ["imperative"]),
    ("Plankalkul", 1943, ["imperative"]),
    ("ShortCode", 1949, ["imperative"]),
    ("RegionalAssembly", 1951, ["imperative"]),
    ("IPL", 1954, ["imperative", "functional"]),
    ("FLOWMATIC", 1955, ["imperative"]),
    ("FORTRAN", 1957, ["imperative"]),
    ("Lisp", 1958, ["functional"]),
    ("ALGOL58", 1958, ["imperative", "functional"]),
    ("COBOL", 1959, ["imperative"]),
    ("Simula", 1962, ["imperative", "oop"]),
    ("APL", 1962, ["functional"]),
    ("SNOBOL", 1962, ["imperative"]),
    ("CPL", 1963, ["imperative", "functional"]),
    ("BASIC", 1964, ["imperative"]),
    ("PLI", 1964, ["imperative"]),
    ("BCPL", 1967, ["imperative"]),
    ("B", 1969, ["imperative"]),
    ("Pascal", 1970, ["imperative"]),
    ("Forth", 1970, ["imperative"]),
    ("C", 1972, ["imperative"]),
    ("Prolog", 1972, ["logic"]),
    ("Smalltalk", 1972, ["oop"]),
    ("ML", 1973, ["functional"]),
    ("Scheme", 1975, ["functional"]),
    ("SQL", 1978, ["imperative"]),
    ("CPlusPlus", 1980, ["imperative", "oop"]),
    ("Ada", 1983, ["imperative", "oop"]),
    ("CommonLisp", 1984, ["functional", "oop"]),
    ("MATLAB", 1984, ["imperative", "functional"]),
    ("Eiffel", 1985, ["oop"]),
    ("Erlang", 1986, ["functional", "concurrent"]),
    ("ObjectiveC", 1986, ["imperative", "oop"]),
    ("Perl", 1987, ["imperative", "functional"]),
    ("Tcl", 1988, ["imperative"]),
    ("Python", 1990, ["imperative", "functional", "oop"]),
    ("Haskell", 1990, ["functional"]),
    ("VisualBasic", 1991, ["imperative", "oop"]),
    ("Lua", 1993, ["imperative", "functional"]),
    ("R", 1993, ["functional", "imperative"]),
    ("Java", 1995, ["imperative", "oop", "functional"]),
    ("JavaScript", 1995, ["imperative", "functional", "oop"]),
    ("Ruby", 1995, ["imperative", "functional", "oop"]),
    ("PHP", 1995, ["imperative", "functional", "oop"]),
    ("Delphi", 1995, ["imperative", "oop"]),
    ("ActionScript", 2000, ["imperative", "oop"]),
    ("D", 2001, ["imperative", "functional", "oop"]),
    ("CSharp", 2001, ["imperative", "oop", "functional"]),
    ("Scala", 2003, ["functional", "oop"]),
    ("Groovy", 2003, ["imperative", "oop", "functional"]),
    ("FSharp", 2005, ["functional", "imperative", "oop"]),
    ("PowerShell", 2006, ["imperative", "functional"]),
    ("Clojure", 2007, ["functional"]),
    ("Go", 2009, ["imperative", "concurrent", "functional"]),
    ("Julia", 2010, ["functional", "imperative"]),
    ("Dart", 2011, ["imperative", "oop", "functional"]),
    ("Rust", 2015, ["imperative", "functional"]),
    ("Swift", 2014, ["imperative", "oop", "functional"]),
    ("Ballerina", 2019, ["imperative", "functional"]),
]

HARDWARE = [
    ("ENIAC", 0, 0, 0, 0, 0, 0, 0),
    ("IBM704", 0, 0, 0, 0, 0, 0, 0),
    ("IBM7090", 0, 0, 0, 0, 0, 0, 0),
    ("PDP8", 0, 0, 0, 0, 0, 0, 0),
    ("System360", 0, 0, 0, 0, 0, 0, 0),
    ("PDP11", 0, 0, 0, 0, 0, 0, 0),
    ("Intel4004", 0, 0, 0, 0, 0, 0, 0),
    ("Intel8080", 0, 0, 0, 0, 0, 0, 0),
    ("x86_8086", 0, 0, 0, 0, 0, 0, 0),
    ("Motorola68000", 0, 0, 0, 0, 0, 0, 0),
    ("VAX", 0, 0, 0, 0, 0, 0, 0),
    ("Intel486", 0, 0, 0, 0, 0, 0, 0),
    ("Pentium", 0, 0, 0, 0, 0, 0, 0),
    ("PowerPC", 0, 0, 0, 0, 0, 0, 0),
    ("SPARC", 0, 0, 0, 0, 0, 0, 0),
    ("ARMv7", 0, 0, 0, 0, 0, 0, 0),
    ("IntelCore", 0, 0, 0, 0, 0, 0, 0),
    ("ARMv8", 0, 0, 0, 0, 0, 0, 0),
    ("AppleM1", 0, 0, 0, 0, 0, 0, 0),
    ("RISC_V", 0, 0, 0, 0, 0, 0, 0),
    ("NVIDIA_GPU", 0, 0, 0, 0, 0, 0, 0),
]

ALGO_FMT = "<QHBBQIIQQI"
TRADEOFF_FMT = "<BBBBBBBB"
LANG_FMT = "<QHBHQHQBI"
HW_FMT = "<QBHIBHBHQ"
HEADER_FMT = "<IQQQQQQQQQQ"


def hash_name(name: str) -> int:
    h = 0x9E3779B97F4A7C15
    for c in name.encode():
        h ^= c
        h = (h * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    return h


def paradigm_flags(paradigms):
    mapping = {
        "functional": 1,
        "oop": 2,
        "imperative": 4,
        "logic": 8,
        "concurrent": 16,
    }
    flags = 0
    for p in paradigms:
        flags |= mapping.get(p.lower(), 0)
    return flags


def complexity_to_class(complexity: str) -> int:
    mapping = {
        "O(1)": 0,
        "O(log n)": 1,
        "O(log log n)": 1,
        "O(n)": 2,
        "O(n log n)": 3,
        "O(n^2)": 4,
        "O(n^3)": 5,
        "O(2^n)": 6,
    }
    return mapping.get(complexity, 3)


def build_knowledge(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    algo_entries = []
    tradeoff_entries = []
    impl_cursor = 0

    for name, year, paradigms, complexity, speed, memory, clarity, safety, portability, energy, parallelism, realtime in ALGORITHMS:
        impl_bytes = f"// {name} implementation (year {year})".encode()
        tradeoff_entries.append(
            struct.pack(
                TRADEOFF_FMT,
                speed,
                memory,
                clarity,
                safety,
                portability,
                energy,
                parallelism,
                realtime,
            )
        )
        entry = struct.pack(
            ALGO_FMT,
            hash_name(name),
            year,
            paradigm_flags(paradigms),
            complexity_to_class(complexity),
            impl_cursor,
            len(impl_bytes),
            len(tradeoff_entries) - 1,
            0xFFFFFFFFFFFFFFFF,
            0,
            0,
        )
        algo_entries.append(entry)
        impl_cursor += len(impl_bytes)

    magic = b"FRONTIER"
    num_algorithms = len(algo_entries)
    num_languages = len(LANGUAGES)
    num_hardware = len(HARDWARE)

    header_size = 8 + struct.calcsize(HEADER_FMT) + 32
    algo_offset = header_size
    tradeoff_offset = algo_offset + num_algorithms * struct.calcsize(ALGO_FMT)
    language_offset = tradeoff_offset + len(tradeoff_entries) * struct.calcsize(TRADEOFF_FMT)
    hardware_offset = language_offset + num_languages * struct.calcsize(LANG_FMT)

    with open(output_dir / "index.bin", "wb") as f:
        f.write(magic)
        f.write(
            struct.pack(
                HEADER_FMT,
                1,
                num_algorithms,
                0,
                0,
                num_languages,
                algo_offset,
                0,
                0,
                language_offset,
                tradeoff_offset,
                hardware_offset,
            )
        )
        f.write(b"\x00" * 32)

        for entry in algo_entries:
            f.write(entry)
        for entry in tradeoff_entries:
            f.write(entry)
        for name, year, paradigms in LANGUAGES:
            f.write(
                struct.pack(
                    LANG_FMT,
                    hash_name(name),
                    year,
                    paradigm_flags(paradigms),
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                )
            )
        for name, arch, cline, psize, simd, mlat, bpen, vwidth in HARDWARE:
            f.write(
                struct.pack(
                    HW_FMT,
                    hash_name(name),
                    arch,
                    cline,
                    psize,
                    simd,
                    mlat,
                    bpen,
                    vwidth,
                    0,
                )
            )

    print(f"✅ Knowledge hypercube built at: {output_dir}/index.bin")
    print(f"   - {num_algorithms} algorithms")
    print(f"   - {num_languages} languages")
    print(f"   - {num_hardware} hardware profiles")
    print(f"   - {len(tradeoff_entries)} tradeoff entries")


if __name__ == "__main__":
    build_knowledge(OUTPUT_DIR)
