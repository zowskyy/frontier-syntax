use crate::ast::Stmt;
use crate::lsp::wasm_ffi::{parse_via_wasm_or_native, ParsedDocument};
use crate::resolver::ResolveResult;
use crate::{resolve_program, FrontierError};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;
use tower_lsp::jsonrpc::Result as LspResult;
use tower_lsp::lsp_types::*;
use tower_lsp::{Client, LanguageServer, LspService, Server};

const KEYWORDS: &[&str] = &[
    "let", "fn", "return", "if", "else", "true", "false", "null", "int", "float", "bool",
    "string", "void",
];

pub struct FrontierLanguageServer {
    client: Client,
    documents: Arc<RwLock<HashMap<Url, DocumentState>>>,
    wasm_path: PathBuf,
}

#[derive(Clone)]
struct DocumentState {
    text: String,
    parsed: Option<ParsedDocument>,
    resolved: Option<ResolveResult>,
    symbols: Vec<DocumentSymbol>,
}

struct SymbolLocation {
    name: String,
    uri: Url,
    range: Range,
    kind: SymbolKind,
}

pub async fn run_server(wasm_path: PathBuf) {
    let stdin = tokio::io::stdin();
    let stdout = tokio::io::stdout();
    let (service, socket) = LspService::new(|client| FrontierLanguageServer {
        client,
        documents: Arc::new(RwLock::new(HashMap::new())),
        wasm_path,
    });
    Server::new(stdin, stdout, socket).serve(service).await;
}

#[tower_lsp::async_trait]
impl LanguageServer for FrontierLanguageServer {
    async fn initialize(&self, _: InitializeParams) -> LspResult<InitializeResult> {
        Ok(InitializeResult {
            server_info: Some(ServerInfo {
                name: "frontier-lsp".to_string(),
                version: Some("0.1.0".to_string()),
            }),
            capabilities: ServerCapabilities {
                text_document_sync: Some(TextDocumentSyncCapability::Kind(
                    TextDocumentSyncKind::FULL,
                )),
                completion_provider: Some(CompletionOptions {
                    trigger_characters: Some(vec![".".to_string(), ":".to_string()]),
                    ..Default::default()
                }),
                definition_provider: Some(OneOf::Left(true)),
                ..Default::default()
            },
            ..Default::default()
        })
    }

    async fn initialized(&self, _: InitializedParams) {
        self.client
            .log_message(MessageType::INFO, "Frontier LSP initialized (WASM FFI backend)")
            .await;
    }

    async fn shutdown(&self) -> LspResult<()> {
        Ok(())
    }

    async fn did_open(&self, params: DidOpenTextDocumentParams) {
        self.update_document(params.text_document.uri, params.text_document.text)
            .await;
    }

    async fn did_change(&self, params: DidChangeTextDocumentParams) {
        if let Some(change) = params.content_changes.into_iter().next() {
            self.update_document(params.text_document.uri, change.text)
                .await;
        }
    }

    async fn completion(&self, params: CompletionParams) -> LspResult<Option<CompletionResponse>> {
        let docs = self.documents.read().await;
        let uri = &params.text_document_position.text_document.uri;
        let Some(state) = docs.get(uri) else {
            return Ok(None);
        };

        let mut items = Vec::new();
        for kw in KEYWORDS {
            items.push(CompletionItem {
                label: kw.to_string(),
                kind: Some(CompletionItemKind::KEYWORD),
                detail: Some("Frontier keyword".to_string()),
                ..Default::default()
            });
        }

        if let Some(resolved) = &state.resolved {
            for sym in &resolved.symbol_table {
                items.push(CompletionItem {
                    label: sym.name.clone(),
                    kind: Some(match sym.kind.as_str() {
                        "function" => CompletionItemKind::FUNCTION,
                        "parameter" => CompletionItemKind::VARIABLE,
                        _ => CompletionItemKind::VARIABLE,
                    }),
                    detail: Some(format!("{}: {}", sym.kind, sym.type_spec.base)),
                    ..Default::default()
                });
            }
        }

        Ok(Some(CompletionResponse::Array(items)))
    }

    async fn goto_definition(
        &self,
        params: GotoDefinitionParams,
    ) -> LspResult<Option<GotoDefinitionResponse>> {
        let docs = self.documents.read().await;
        let uri = &params.text_document_position_params.text_document.uri;
        let pos = params.text_document_position_params.position;
        let Some(state) = docs.get(uri) else {
            return Ok(None);
        };

        let word = word_at_position(&state.text, pos);
        let Some(name) = word else {
            return Ok(None);
        };

        if let Some(loc) = find_definition(&state.text, &name, uri) {
            return Ok(Some(GotoDefinitionResponse::Scalar(loc)));
        }

        Ok(None)
    }
}

impl FrontierLanguageServer {
    async fn update_document(&self, uri: Url, text: String) {
        let diagnostics = match self.parse_document(&text) {
            Ok((parsed, resolved, diags)) => {
                let mut docs = self.documents.write().await;
                docs.insert(
                    uri.clone(),
                    DocumentState {
                        text: text.clone(),
                        parsed: Some(parsed),
                        resolved: Some(resolved),
                        symbols: Vec::new(),
                    },
                );
                diags
            }
            Err(e) => {
                let mut docs = self.documents.write().await;
                docs.insert(
                    uri.clone(),
                    DocumentState {
                        text,
                        parsed: None,
                        resolved: None,
                        symbols: Vec::new(),
                    },
                );
                vec![Diagnostic {
                    range: Range {
                        start: Position {
                            line: (e.line.saturating_sub(1)) as u32,
                            character: (e.column.saturating_sub(1)) as u32,
                        },
                        end: Position {
                            line: (e.line.saturating_sub(1)) as u32,
                            character: e.column as u32,
                        },
                    },
                    severity: Some(DiagnosticSeverity::ERROR),
                    code: Some(NumberOrString::String(e.code.clone())),
                    message: e.message.clone(),
                    source: Some("frontier".to_string()),
                    ..Default::default()
                }]
            }
        };

        self.client
            .publish_diagnostics(uri, diagnostics, None)
            .await;
    }

    fn parse_document(
        &self,
        text: &str,
    ) -> std::result::Result<(ParsedDocument, ResolveResult, Vec<Diagnostic>), FrontierError> {
        let parsed = parse_via_wasm_or_native(text, &self.wasm_path)?;
        let mut diagnostics = Vec::new();

        for err in &parsed.errors {
            diagnostics.push(Diagnostic {
                range: Range {
                    start: Position {
                        line: 0,
                        character: 0,
                    },
                    end: Position {
                        line: 0,
                        character: 1,
                    },
                },
                severity: Some(DiagnosticSeverity::ERROR),
                message: err.clone(),
                source: Some("frontier".to_string()),
                ..Default::default()
            });
        }

        let resolved = resolve_program(&parsed.program)?;
        Ok((parsed, resolved, diagnostics))
    }
}

fn word_at_position(text: &str, pos: Position) -> Option<String> {
    let line: Vec<char> = text
        .lines()
        .nth(pos.line as usize)?
        .chars()
        .collect();
    let col = pos.character as usize;
    if col >= line.len() {
        return None;
    }
    let mut start = col;
    let mut end = col;
    while start > 0 && (line[start - 1].is_ascii_alphanumeric() || line[start - 1] == '_') {
        start -= 1;
    }
    while end < line.len() && (line[end].is_ascii_alphanumeric() || line[end] == '_') {
        end += 1;
    }
    if start == end {
        return None;
    }
    Some(line[start..end].iter().collect())
}

fn find_definition(text: &str, name: &str, uri: &Url) -> Option<Location> {
    for (line_idx, line) in text.lines().enumerate() {
        if line.contains("let ") && line.contains(name) {
            if let Some(pos) = line.find(name) {
                return Some(Location {
                    uri: uri.clone(),
                    range: Range {
                        start: Position {
                            line: line_idx as u32,
                            character: pos as u32,
                        },
                        end: Position {
                            line: line_idx as u32,
                            character: (pos + name.len()) as u32,
                        },
                    },
                });
            }
        }
        if line.contains("fn ") && line.contains(name) {
            if let Some(pos) = line.find(name) {
                return Some(Location {
                    uri: uri.clone(),
                    range: Range {
                        start: Position {
                            line: line_idx as u32,
                            character: pos as u32,
                        },
                        end: Position {
                            line: line_idx as u32,
                            character: (pos + name.len()) as u32,
                        },
                    },
                });
            }
        }
    }
    None
}

#[allow(dead_code)]
fn collect_symbols(stmts: &[Stmt], uri: &Url, line_offset: &mut u32) -> Vec<SymbolLocation> {
    let mut out = Vec::new();
    for stmt in stmts {
        match stmt {
            Stmt::LetDecl { name, .. } => {
                out.push(SymbolLocation {
                    name: name.clone(),
                    uri: uri.clone(),
                    range: Range {
                        start: Position {
                            line: *line_offset,
                            character: 0,
                        },
                        end: Position {
                            line: *line_offset,
                            character: name.len() as u32,
                        },
                    },
                    kind: SymbolKind::VARIABLE,
                });
            }
            Stmt::FnDecl { name, body, .. } => {
                out.push(SymbolLocation {
                    name: name.clone(),
                    uri: uri.clone(),
                    range: Range {
                        start: Position {
                            line: *line_offset,
                            character: 0,
                        },
                        end: Position {
                            line: *line_offset,
                            character: name.len() as u32,
                        },
                    },
                    kind: SymbolKind::FUNCTION,
                });
                out.extend(collect_symbols(body, uri, line_offset));
            }
            _ => {}
        }
        *line_offset += 1;
    }
    out
}
