// Frontier Browser Runtime — wasm-bindgen glue for in-browser compilation

import init, { BrowserCompiler } from './wasm-bindings/frontier_browser.js';

let initPromise = null;

async function ensureInit() {
  if (!initPromise) {
    initPromise = init();
  }
  await initPromise;
}

export class FrontierRuntime {
  constructor(compiler) {
    this.compiler = compiler;
  }

  setOptimize(enabled) {
    this.compiler.set_optimize(enabled);
  }

  compile(source) {
    return this.compiler.compile(source);
  }

  validate(source) {
    return this.compiler.validate(source);
  }

  getAlgorithmSuggestion(operation, dataType) {
    return this.compiler.get_algorithm_suggestion(operation, dataType);
  }
}

export async function createFrontierRuntime() {
  await ensureInit();
  return new FrontierRuntime(new BrowserCompiler());
}
