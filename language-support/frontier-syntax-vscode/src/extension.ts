import * as path from "path";
import { workspace, ExtensionContext } from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
} from "vscode-languageclient/node";

let client: LanguageClient;

export function activate(context: ExtensionContext) {
  const config = workspace.getConfiguration("frontier");
  const lspPath = config.get<string>("lsp.path") || "frontier-lsp";
  const wasmPath = config.get<string>("wasm.path") || "";

  const serverOptions: ServerOptions = {
    run: {
      command: lspPath,
      transport: TransportKind.stdio,
      options: {
        env: {
          ...process.env,
          ...(wasmPath ? { FRONTIER_WASM_PATH: wasmPath } : {}),
        },
      },
    },
    debug: {
      command: lspPath,
      transport: TransportKind.stdio,
      options: {
        env: {
          ...process.env,
          ...(wasmPath ? { FRONTIER_WASM_PATH: wasmPath } : {}),
        },
      },
    },
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "frontier" }],
  };

  client = new LanguageClient(
    "frontierLanguageServer",
    "Frontier Language Server",
    serverOptions,
    clientOptions
  );

  context.subscriptions.push({
    dispose: () => {
      void client.stop();
    },
  });

  void client.start();
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  return client.stop();
}
