#!/usr/bin/env python3
"""Property-based testing for the Frontier parser."""

from __future__ import annotations

import random
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple


@dataclass
class Property:
    name: str
    generator: Callable[[], str]
    checker: Callable[[str, Path, Path], bool]
    shrink: Callable[[str], List[str]]


class PropertyTestRunner:
    def __init__(self, frontier_bin: Path, max_tests: int = 1000, seed: int = 42):
        self.frontier_bin = frontier_bin
        self.max_tests = max_tests
        self._rng = random.Random(seed)
        self.failures: List[Tuple[str, str]] = []
        self.passed = 0

    def run(self, properties: List[Property]) -> bool:
        print(f"  Property tests: {len(properties)} properties, {self.max_tests} cases each")
        for prop in properties:
            if not self._test_property(prop):
                return False
        print(f"  All properties passed ({self.passed} total checks)")
        return True

    def _test_property(self, prop: Property) -> bool:
        print(f"    - {prop.name}")
        for i in range(self.max_tests):
            source = prop.generator()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".fr", delete=False) as handle:
                handle.write(source)
                path = Path(handle.name)
            try:
                if not prop.checker(source, path, self.frontier_bin):
                    minimal = self._shrink(prop, source)
                    self.failures.append((prop.name, minimal))
                    print(f"      FAIL at case {i + 1}")
                    return False
                self.passed += 1
            finally:
                path.unlink(missing_ok=True)
            if (i + 1) % max(self.max_tests // 5, 1) == 0:
                print(f"      progress: {i + 1}/{self.max_tests}")
        return True

    def _shrink(self, prop: Property, source: str) -> str:
        minimal = source
        for candidate in prop.shrink(source):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".fr", delete=False) as handle:
                handle.write(candidate)
                path = Path(handle.name)
            try:
                if not prop.checker(candidate, path, self.frontier_bin):
                    if len(candidate) < len(minimal):
                        minimal = candidate
            finally:
                path.unlink(missing_ok=True)
        return minimal

    def _choice(self, items: List[str]) -> str:
        return self._rng.choice(items)

    def _randint(self, low: int, high: int) -> int:
        return self._rng.randint(low, high)


def _run_parse(frontier_bin: Path, path: Path, timeout: int = 2) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(frontier_bin), "parse", str(path)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_hash(frontier_bin: Path, path: Path, timeout: int = 2) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(frontier_bin), "hash", str(path)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class FrontierProperties:
    @staticmethod
    def parser_never_panics(runner: PropertyTestRunner) -> Property:
        tokens = ["let", "fn", "return", "print", "if", "while", "true", "false", "1", '"hello"']

        def generator() -> str:
            lines = ["fn main() {"]
            for _ in range(runner._randint(1, 12)):
                lines.append(f"    {runner._choice(tokens)};")
            lines.append("}")
            return "\n".join(lines)

        def checker(_source: str, path: Path, frontier_bin: Path) -> bool:
            try:
                result = _run_parse(frontier_bin, path)
            except subprocess.TimeoutExpired:
                return False
            return result.returncode >= 0

        def shrink(source: str) -> List[str]:
            lines = source.split("\n")
            candidates = []
            for index in range(len(lines)):
                if "fn main" in lines[index] or lines[index].strip() == "}":
                    continue
                candidates.append("\n".join(lines[:index] + lines[index + 1 :]))
            return candidates

        return Property("parser_never_panics", generator, checker, shrink)

    @staticmethod
    def deterministic_parsing(runner: PropertyTestRunner) -> Property:
        snippets = [
            "fn main(): void { let x: int = 10; return; }\n",
            "fn main(): void { let y: int = 20; let z: int = x + y; return; }\n".replace("x + y", "y + 1"),
            'fn main(): void { let msg: string = "hello"; return; }\n',
        ]

        def generator() -> str:
            return runner._choice(snippets)

        def checker(_source: str, path: Path, frontier_bin: Path) -> bool:
            first = _run_parse(frontier_bin, path)
            second = _run_parse(frontier_bin, path)
            if first.returncode != 0 or second.returncode != 0:
                return first.returncode == second.returncode
            return first.stdout == second.stdout

        def shrink(source: str) -> List[str]:
            return ['fn main(): void { let x: int = 1; return; }\n']

        return Property("deterministic_parsing", generator, checker, shrink)

    @staticmethod
    def deterministic_hashing(runner: PropertyTestRunner, project_root: Path) -> Property:
        sample_paths = [
            project_root / "examples" / "sample.fr",
            project_root / "examples" / "sample_v2.fr",
            project_root / "examples" / "v2_parser_test.fr",
        ]
        available = [path for path in sample_paths if path.exists()]

        def generator() -> str:
            return runner._choice(available).read_text(encoding="utf-8")

        def checker(_source: str, path: Path, frontier_bin: Path) -> bool:
            first = _run_hash(frontier_bin, path)
            second = _run_hash(frontier_bin, path)
            if first.returncode != 0 or second.returncode != 0:
                return False
            return first.stdout.strip() == second.stdout.strip()

        def shrink(source: str) -> List[str]:
            return [source]

        return Property("deterministic_hashing", generator, checker, shrink)


def run_property_suite(frontier_bin: Path, max_tests: int = 100, seed: int = 42, project_root: Optional[Path] = None) -> dict:
    root = project_root or Path.cwd()
    runner = PropertyTestRunner(frontier_bin, max_tests=max_tests, seed=seed)
    properties = [
        FrontierProperties.parser_never_panics(runner),
        FrontierProperties.deterministic_parsing(runner),
        FrontierProperties.deterministic_hashing(runner, root),
    ]
    success = runner.run(properties)
    return {
        "success": success,
        "passed": runner.passed,
        "failures": runner.failures,
        "seed": seed,
        "max_tests": max_tests,
    }
