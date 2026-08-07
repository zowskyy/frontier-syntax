// Browser test runner for Frontier compiler runtime

import { createFrontierRuntime } from './frontier_runtime.js';

const tests = [
  {
    name: 'runtime loads',
    run: async (runtime) => runtime !== null,
  },
  {
    name: 'validate simple main',
    run: async (runtime) => {
      const r = runtime.validate('fn main(): int { return 1; }');
      return r.valid !== false;
    },
  },
  {
    name: 'compile simple main',
    run: async (runtime) => {
      const r = runtime.compile('fn main(): int { return 7; }');
      return r && (r.success === true || r.wasm || Array.isArray(r));
    },
  },
];

export async function runBrowserCompilerTests(wasmPath) {
  const resp = await fetch(wasmPath);
  if (!resp.ok) throw new Error(`Failed to load ${wasmPath}`);
  const runtime = await createFrontierRuntime(await resp.arrayBuffer());

  let passed = 0;
  for (const test of tests) {
    try {
      const ok = await test.run(runtime);
      console.log(`${ok ? '✅' : '❌'} ${test.name}`);
      if (ok) passed += 1;
    } catch (e) {
      console.log(`💥 ${test.name}: ${e.message}`);
    }
  }
  console.log(`Results: ${passed}/${tests.length} passed`);
  return passed === tests.length;
}

if (typeof window !== 'undefined') {
  runBrowserCompilerTests('../syntax/wasm/frontier_browser.wasm').catch(console.error);
}
