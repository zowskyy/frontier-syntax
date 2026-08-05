# Frontier Syntax — Language Reference

## Overview

Frontier is a compiled, statically-typed programming language with a focus on performance, safety, and developer productivity. It features a syntax inspired by Python and Rust, with a powerful type system and built-in concurrency.

## Syntax

### Variables

```frontier
let x = 5;                    // Immutable variable
let mut y = 10;              // Mutable variable
y = 20;                      // Assign new value

const PI = 3.14159;          // Constant (compile-time)
```

### Types

```frontier
// Primitive types
let a: i32 = 42;
let b: f64 = 3.14159;
let c: bool = true;
let d: char = 'A';
let e: string = "Hello";

// Compound types
let arr: [i32; 3] = [1, 2, 3];
let tuple: (i32, bool) = (5, true);
let slice: &[i32] = &arr;

// User-defined types
struct Point {
    x: f64,
    y: f64,
}

enum Direction {
    North,
    South,
    East,
    West,
}
```

### Functions

```frontier
fn add(a: i32, b: i32) -> i32 {
    return a + b;
}

fn factorial(n: i32) -> i32 {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}
```

### Control Flow

```frontier
// If/Else
if x > 0 {
    print("Positive");
} else if x < 0 {
    print("Negative");
} else {
    print("Zero");
}

// For loop
for i in 0..10 {
    print(i);
}

// While loop
while x > 0 {
    x -= 1;
}

// Match
match direction {
    Direction.North => print("Going north"),
    Direction.South => print("Going south"),
    _ => print("Going somewhere"),
}
```

## Memory Management

```frontier
// Ownership
let x = 5;
let y = x;  // Copy (not move)
let s = "Hello".to_string();
let t = s;  // Move (s is invalid after this)

// Borrowing
fn print_len(s: &string) {
    print(s.len());
}
let s = "Hello".to_string();
print_len(&s);  // Immutable borrow
let mut s = "Hello".to_string();
fn append(s: &mut string, tail: string) {
    s += tail;
}
append(&mut s, " World");  // Mutable borrow
```

## Concurrency

```frontier
// Async/Await
async fn fetch_data(url: string) -> Result<string, Error> {
    let response = await http.get(url);
    return response.text();
}

// Parallel execution
parallel_for(0, 1000, |i| {
    process(i);
});
```

## Error Handling

```frontier
// Result
fn parse_int(s: string) -> Result<i32, Error> {
    if s.is_numeric() {
        return Result.ok(s.to_i32());
    } else {
        return Result.err(Error.new("Not a number"));
    }
}

let result = parse_int("123");
if result.is_ok() {
    print(result.unwrap());
} else {
    print("Error: " + result.unwrap_err().message);
}

// Try/Catch
try {
    let data = read_file("data.txt")?;
    process(data);
} catch(error) {
    print("Failed: " + error.message);
}
```

## Traits and Generics

```frontier
// Trait definition
trait Add<T> {
    fn add(self, other: T) -> T;
}

// Implementation for i32
impl Add for i32 {
    fn add(self, other: i32) -> i32 {
        return self + other;
    }
}

// Generic function
fn identity<T>(value: T) -> T {
    return value;
}
```

## Modules and Imports

```frontier
// Import a module
import std.collections.Vec;
import std.io as io;

// Export a function
pub fn greet(name: string) -> string {
    return "Hello, " + name;
}

// Module definition
mod utils {
    pub fn helper() {
        print("Helper function");
    }
}
```

## Standard Library

### Collections

- `Vec<T>` — Dynamic array
- `Map<K, V>` — Hash map
- `Set<T>` — Hash set
- `Option<T>` — Optional value
- `Result<T, E>` — Result with error

### String

- `string.len()` — Length
- `string.split(delimiter)` — Split into parts
- `string.trim()` — Remove whitespace
- `string.to_lower()` — Lowercase

### Math

- `Math.sin(x)` — Sine
- `Math.cos(x)` — Cosine
- `Math.sqrt(x)` — Square root
- `Math.pow(x, y)` — Power
- `Math.floor(x)` — Floor
- `Math.ceil(x)` — Ceiling

### IO

- `IO.read_file(path)` — Read file
- `IO.write_file(path, content)` — Write file
- `IO.print(message)` — Print to stdout
- `IO.println(message)` — Print with newline

## Compiler

### Commands

```bash
frontier compile source.frontier       # Compile to native code
frontier compile source.frontier --target wasm  # Compile to WASM
frontier run source.frontier           # Compile and run
frontier build                         # Build project
frontier test                          # Run tests
```

### Optimization Flags

- `-O0` — No optimization
- `-O1` — Basic optimization
- `-O2` — Aggressive optimization
- `-O3` — Maximum optimization
- `-Os` — Optimize for size
- `-Oz` — Optimize for size (aggressive)

## ARC Gates

The compiler enforces ARC gates during compilation:

- Parse 10,000 lines < 100ms
- Type check 10,000 lines < 500ms
- Optimize 10,000 lines < 500ms
- Generate code 10,000 lines < 500ms
- No memory leaks in test suite

## Examples

### Hello World

```frontier
fn main() {
    print("Hello, World!");
}
```

### Fibonacci

```frontier
fn fib(n: i32) -> i32 {
    if n <= 1 {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

fn main() {
    for i in 0..10 {
        print(fib(i));
    }
}
```

### Concurrent Web Scraper

```frontier
async fn fetch(url: string) -> Result<string, Error> {
    let response = await http.get(url);
    return response.text();
}

fn main() {
    let urls = ["https://example.com", "https://google.com"];
    let futures = [];
    for url in urls {
        futures.push(fetch(url));
    }
    let results = await Future.all(futures);
    for result in results {
        print(result.unwrap());
    }
}
```
