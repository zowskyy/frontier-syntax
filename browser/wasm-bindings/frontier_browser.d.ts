/* tslint:disable */
/* eslint-disable */

export class BrowserCompiler {
    free(): void;
    [Symbol.dispose](): void;
    compile(source: string): any;
    compile_to_wasm(source: string): Uint8Array;
    get_algorithm_suggestion(operation: string, data_type: string): any;
    get_ancestors(operation: string): any;
    constructor();
    set_optimize(enabled: boolean): void;
    validate(source: string): any;
}

export class WasmParseResult {
    private constructor();
    free(): void;
    [Symbol.dispose](): void;
    readonly ast_hash: string;
    readonly ast_json: string;
    readonly errors: string;
}

export function compile_frontier(source: string): any;

export function compile_frontier_wasm(source: string): Uint8Array;

export function generate_zk_proof(_ast_json: string): string;

export function hash_ast(ast_json: string): string;

export function parse_source(source: string): WasmParseResult;

export function parse_source_with_resolve(source: string): WasmParseResult;

export function validate_frontier(source: string): any;

export function verify_zk_proof(_ast_json: string, _proof_json: string): boolean;

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly knowledge_solver_get_optimal_algorithm: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => number;
    readonly knowledge_solver_get_ancestors: (a: number, b: number) => number;
    readonly knowledge_solver_get_tradeoffs: (a: number, b: number) => number;
    readonly knowledge_solver_free: (a: number) => void;
    readonly __wbg_wasmparseresult_free: (a: number, b: number) => void;
    readonly wasmparseresult_ast_json: (a: number) => [number, number];
    readonly wasmparseresult_ast_hash: (a: number) => [number, number];
    readonly wasmparseresult_errors: (a: number) => [number, number];
    readonly parse_source: (a: number, b: number) => number;
    readonly hash_ast: (a: number, b: number) => [number, number];
    readonly verify_zk_proof: (a: number, b: number, c: number, d: number) => number;
    readonly generate_zk_proof: (a: number, b: number) => [number, number];
    readonly parse_source_with_resolve: (a: number, b: number) => number;
    readonly __wbg_browsercompiler_free: (a: number, b: number) => void;
    readonly browsercompiler_new: () => number;
    readonly browsercompiler_set_optimize: (a: number, b: number) => void;
    readonly browsercompiler_compile: (a: number, b: number, c: number) => [number, number, number];
    readonly browsercompiler_compile_to_wasm: (a: number, b: number, c: number) => [number, number, number, number];
    readonly browsercompiler_validate: (a: number, b: number, c: number) => [number, number, number];
    readonly browsercompiler_get_algorithm_suggestion: (a: number, b: number, c: number, d: number, e: number) => [number, number, number];
    readonly browsercompiler_get_ancestors: (a: number, b: number, c: number) => [number, number, number];
    readonly compile_frontier: (a: number, b: number) => [number, number, number];
    readonly compile_frontier_wasm: (a: number, b: number) => [number, number, number, number];
    readonly validate_frontier: (a: number, b: number) => [number, number, number];
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __externref_table_dealloc: (a: number) => void;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
    readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;

/**
 * Instantiates the given `module`, which can either be bytes or
 * a precompiled `WebAssembly.Module`.
 *
 * @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
 *
 * @returns {InitOutput}
 */
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
 * If `module_or_path` is {RequestInfo} or {URL}, makes a request and
 * for everything else, calls `WebAssembly.instantiate` directly.
 *
 * @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
 *
 * @returns {Promise<InitOutput>}
 */
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
