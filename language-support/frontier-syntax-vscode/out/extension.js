"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode_1 = require("vscode");
const node_1 = require("vscode-languageclient/node");
let client;
function activate(context) {
    const config = vscode_1.workspace.getConfiguration("frontier");
    const lspPath = config.get("lsp.path") || "frontier-lsp";
    const wasmPath = config.get("wasm.path") || "";
    const serverOptions = {
        run: {
            command: lspPath,
            transport: node_1.TransportKind.stdio,
            options: {
                env: {
                    ...process.env,
                    ...(wasmPath ? { FRONTIER_WASM_PATH: wasmPath } : {}),
                },
            },
        },
        debug: {
            command: lspPath,
            transport: node_1.TransportKind.stdio,
            options: {
                env: {
                    ...process.env,
                    ...(wasmPath ? { FRONTIER_WASM_PATH: wasmPath } : {}),
                },
            },
        },
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "frontier" }],
    };
    client = new node_1.LanguageClient("frontierLanguageServer", "Frontier Language Server", serverOptions, clientOptions);
    context.subscriptions.push({
        dispose: () => {
            void client.stop();
        },
    });
    void client.start();
}
function deactivate() {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
//# sourceMappingURL=extension.js.map