import * as vscode from 'vscode';
import { IPCClient } from './ipcClient';

/**
 * Manages gutter decorations showing AI/human attribution per line.
 */
export class GutterDecorations {
    private ipcClient: IPCClient;
    private decorationTypes: Map<string, vscode.TextEditorDecorationType> = new Map();
    private currentDecorations: Map<string, vscode.Range[]> = new Map();

    constructor(ipcClient: IPCClient) {
        this.ipcClient = ipcClient;
    }

    async update(uri: vscode.Uri) {
        if (!vscode.workspace.getConfiguration('codedna').get<boolean>('showGutterDecorations', true)) {
            this.clear(uri);
            return;
        }

        try {
            const attributions = await this.ipcClient.getAttributions(uri.fsPath);
            this.applyDecorations(uri, attributions);
        } catch (err) {
            console.error('CodeDNA: Failed to update gutter decorations:', err);
        }
    }

    private applyDecorations(uri: vscode.Uri, attributions: any[]) {
        const editor = vscode.window.visibleTextEditors.find(e => e.document.uri.fsPath === uri.fsPath);
        if (!editor) {
            return;
        }

        const rangesByLabel: Map<string, vscode.Range[]> = new Map();

        for (const attr of attributions) {
            const label = attr.label;
            const color = attr.label_color || this.getColorForLabel(label);

            if (!rangesByLabel.has(label)) {
                rangesByLabel.set(label, []);
            }

            const range = new vscode.Range(
                attr.start_line - 1, 0,
                attr.end_line - 1, 0
            );
            rangesByLabel.get(label)!.push(range);
        }

        for (const [label, ranges] of rangesByLabel) {
            const color = this.getColorForLabel(label);
            let decorationType = this.decorationTypes.get(label);

            if (!decorationType) {
                decorationType = vscode.window.createTextEditorDecorationType({
                    gutterIconSize: 'contain',
                    overviewRulerColor: color,
                    overviewRulerLane: vscode.OverviewRulerLane.Full,
                    after: {
                        contentText: ` ${label}`,
                        color: color,
                    },
                });
                this.decorationTypes.set(label, decorationType);
            }

            editor.setDecorations(decorationType, ranges);
            this.currentDecorations.set(`${uri.fsPath}:${label}`, ranges);
        }
    }

    private getColorForLabel(label: string): string {
        switch (label.toLowerCase()) {
            case 'human': return '#22c55e';
            case 'ai-generated': return '#3b82f6';
            case 'ai-modified': return '#f97316';
            case 'ambiguous': return '#a855f7';
            default: return '#888888';
        }
    }

    clear(uri: vscode.Uri) {
        const editor = vscode.window.visibleTextEditors.find(e => e.document.uri.fsPath === uri.fsPath);
        if (!editor) return;

        for (const decorationType of this.decorationTypes.values()) {
            editor.setDecorations(decorationType, []);
        }
        for (const key of this.currentDecorations.keys()) {
            if (key.startsWith(uri.fsPath)) {
                this.currentDecorations.delete(key);
            }
        }
    }

    dispose() {
        for (const decorationType of this.decorationTypes.values()) {
            decorationType.dispose();
        }
        this.decorationTypes.clear();
        this.currentDecorations.clear();
    }
}