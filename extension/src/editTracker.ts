import * as vscode from 'vscode';
import { IPCClient } from './ipcClient';

interface PendingEdit {
    file: string;
    startLine: number;
    endLine: number;
    insertedText: string;
    deletedText: string;
    timestamp: number;
    startTime: number;
}

/**
 * Tracks text document changes and sends them to the IPC server for classification.
 */
export class EditTracker {
    private ipcClient: IPCClient;
    private pendingEdits: Map<string, PendingEdit[]> = new Map();
    private lastChangeTime: Map<string, number> = new Map();
    private debounceTimer: Map<string, NodeJS.Timeout> = new Map();
    private readonly DEBOUNCE_MS = 300;

    constructor(ipcClient: IPCClient) {
        this.ipcClient = ipcClient;
    }

    onDidChangeTextDocument(e: vscode.TextDocumentChangeEvent) {
        const doc = e.document;
        const file = doc.uri.fsPath;
        const now = Date.now();

        let insertedText = '';
        let deletedText = '';
        let startLine = doc.lineCount;
        let endLine = 0;

        for (const change of e.contentChanges) {
            const range = change.range;
            startLine = Math.min(startLine, range.start.line);
            endLine = Math.max(endLine, range.end.line);

            if (change.text) {
                insertedText += change.text;
            }
            if (change.rangeLength > 0) {
                deletedText += doc.getText(change.range);
            }
        }

        if (!insertedText && !deletedText) {
            return;
        }

        const lastTime = this.lastChangeTime.get(file) || now;
        const durationMs = now - lastTime;
        this.lastChangeTime.set(file, now);

        const edit: PendingEdit = {
            file,
            startLine: startLine + 1,
            endLine: endLine + 1,
            insertedText,
            deletedText,
            timestamp: now,
            startTime: lastTime,
        };

        const pending = this.pendingEdits.get(file) || [];
        pending.push(edit);
        this.pendingEdits.set(file, pending);

        const existingTimer = this.debounceTimer.get(file);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        const timer = setTimeout(() => {
            this.flush(file);
        }, this.DEBOUNCE_MS);
        this.debounceTimer.set(file, timer);
    }

    private async flush(file: string) {
        const pending = this.pendingEdits.get(file);
        if (!pending || pending.length === 0) {
            return;
        }

        this.pendingEdits.set(file, []);
        const timer = this.debounceTimer.get(file);
        if (timer) {
            clearTimeout(timer);
            this.debounceTimer.delete(file);
        }

        try {
            await this.ipcClient.classify(pending);
        } catch (err) {
            console.error('CodeDNA: Failed to classify edits:', err);
        }
    }

    async flushAll() {
        for (const file of this.pendingEdits.keys()) {
            await this.flush(file);
        }
    }

    dispose() {
        for (const timer of this.debounceTimer.values()) {
            clearTimeout(timer);
        }
        this.debounceTimer.clear();
        this.pendingEdits.clear();
        this.lastChangeTime.clear();
    }
}