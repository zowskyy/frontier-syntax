// Frontier WASM Playground — uses native parser fallback via fetch API to local server
// or embedded JSON parse simulation when WASM unavailable in static hosting

const editor = document.getElementById('editor');
const astOutput = document.getElementById('ast-output');
const hashOutput = document.getElementById('hash-output');
const errorOutput = document.getElementById('error-output');
const runBtn = document.getElementById('run-btn');

let wasmModule = null;

async function loadWasm() {
  try {
    const resp = await fetch('./wasm_parser_bg.wasm');
    if (!resp.ok) return null;
    const bytes = await resp.arrayBuffer();
    const { instance } = await WebAssembly.instantiate(bytes, {
      wbg: {
        __wbindgen_throw: () => {},
        __wbindgen_object_drop_ref: () => {},
        __wbindgen_string_new: () => 0,
      }
    });
    wasmModule = instance.exports;
    return wasmModule;
  } catch (e) {
    console.warn('WASM load failed, using CLI fallback:', e);
    return null;
  }
}

async function parseSource(source) {
  // Try WASM first
  if (wasmModule && wasmModule.parse_source) {
    try {
      const result = wasmModule.parse_source(source);
      return {
        ast_json: result.ast_json || JSON.stringify(null),
        ast_hash: result.ast_hash || '',
        errors: result.errors || '[]'
      };
    } catch (e) {
      // fall through
    }
  }

  // Fallback: call local frontier binary via no server — use client-side regex validation
  return clientParse(source);
}

async function clientParse(source) {
  const errors = [];
  const lines = source.split('\n');

  // Basic syntax validation
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line || line.startsWith('//')) continue;
    if (line.includes("'")) {
      errors.push(`Error [E-PARSE]: Single quotes illegal at line ${i + 1}, column 1.`);
    }
    if (/\+\+|--/.test(line)) {
      errors.push(`Error [E-PARSE]: Increment/decrement banned at line ${i + 1}, column 1.`);
    }
  }

  if (errors.length > 0) {
    return { ast_json: 'null', ast_hash: '', errors: JSON.stringify(errors) };
  }

  // Build minimal AST representation
  const stmts = [];
  for (const line of lines) {
    const t = line.trim().replace(/;$/, '');
    if (t.startsWith('let ')) {
      const m = t.match(/let\s+(\w+):\s*(\w+)\s*=\s*(.+)/);
      if (m) {
        stmts.push({
          type: 'let_decl',
          name: m[1],
          type_spec: { base: m[2], annotation: 'none' },
          value: parseExpr(m[3])
        });
      }
    } else if (t && !t.startsWith('//')) {
      stmts.push({ type: 'expr', expr: parseExpr(t) });
    }
  }

  const ast = { statements: stmts };
  const ast_json = JSON.stringify(ast, null, 2);
  return {
    ast_json,
    ast_hash: await sha3(ast_json),
    errors: '[]'
  };
}

function parseExpr(expr) {
  expr = expr.trim();
  if (/^\d+$/.test(expr)) return { type: 'integer_literal', value: parseInt(expr) };
  if (/^[a-z_]\w*$/i.test(expr)) return { type: 'identifier', name: expr };
  const m = expr.match(/^(.+?)\s*\+\s*(.+)$/);
  if (m) {
    return {
      type: 'binary_expr',
      operator: '+',
      left: parseExpr(m[1]),
      right: parseExpr(m[2])
    };
  }
  return { type: 'identifier', name: expr };
}

async function sha3(text) {
  const data = new TextEncoder().encode(text);
  try {
    // Use SHA-256 as browser fallback (SHA-3 not in all browsers)
    const hash = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
  } catch {
    return 'hash-unavailable';
  }
}

runBtn.addEventListener('click', async () => {
  errorOutput.textContent = '';
  astOutput.textContent = 'Parsing...';
  const result = await parseSource(editor.value);
  astOutput.textContent = result.ast_json;
  hashOutput.textContent = result.ast_hash;
  const errors = JSON.parse(result.errors);
  if (errors.length > 0) {
    errorOutput.textContent = errors.join('\n');
  } else {
    errorOutput.textContent = '(none)';
    errorOutput.style.color = '#4ec9b0';
  }
});

loadWasm();
