import * as vscode from 'vscode';
import { IPCClient } from './ipcClient';
/**
 * Tracks text document changes and sends them to the IPC server for classification.
 */
export declare class EditTracker {
    private ipcClient;
    private pendingEdits;
    private lastChangeTime;
    private debounceTimer;
    private readonly DEBOUNCE_MS;
    constructor(ipcClient: IPCClient);
    onDidChangeTextDocument(e: vscode.TextDocumentChangeEvent): void;
    private flush;
    flushAll(): Promise<void>;
    dispose(): void;
}
//# sourceMappingURL=editTracker.d.ts.map