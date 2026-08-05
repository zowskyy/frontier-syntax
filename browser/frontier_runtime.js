// Frontier Browser Runtime — JS glue for in-browser compilation

export class FrontierRuntime {
  constructor(wasmModule) {
    this.module = wasmModule;
    this.memory = wasmModule.instance.exports.memory;
    this.exports = wasmModule.instance.exports;
  }

  compile(source) {
    if (this.exports.compile_frontier) {
      return this.exports.compile_frontier(source);
    }
    if (this.exports.compile) {
      return this.exports.compile(source);
    }
    throw new Error('No compile export found in WASM module');
  }

  validate(source) {
    if (this.exports.validate_frontier) {
      return this.exports.validate_frontier(source);
    }
    if (this.exports.validate) {
      return this.exports.validate(source);
    }
    throw new Error('No validate export found in WASM module');
  }

  getAlgorithmSuggestion(operation, dataType) {
    if (this.exports.get_algorithm_suggestion) {
      return this.exports.get_algorithm_suggestion(operation, dataType);
    }
    return { operation, dataType, note: 'Build with browser_wasm exports enabled' };
  }
}

export async function createFrontierRuntime(wasmBytes) {
  const memory = new WebAssembly.Memory({ initial: 1, maximum: 64 });
  const imports = {
    env: {
      memory,
      console_log: (ptr, len) => {
        const bytes = new Uint8Array(memory.buffer, ptr, len);
        console.log('[Frontier]', new TextDecoder().decode(bytes));
      },
    },
  };
  const wasmModule = await WebAssembly.instantiate(wasmBytes, imports);
  return new FrontierRuntime(wasmModule);
}

export function readString(memory, ptr, len) {
  return new TextDecoder().decode(new Uint8Array(memory.buffer, ptr, len));
}

export function writeString(memory, str) {
  const bytes = new TextEncoder().encode(str);
  const view = new Uint8Array(memory.buffer, 0, bytes.length);
  view.set(bytes);
  return 0;
}
