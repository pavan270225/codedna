import * as vscode from 'vscode';
import { IPCClient } from './ipcClient';
/**
 * Manages gutter decorations showing AI/human attribution per line.
 */
export declare class GutterDecorations {
    private ipcClient;
    private decorationTypes;
    private currentDecorations;
    constructor(ipcClient: IPCClient);
    update(uri: vscode.Uri): Promise<void>;
    private applyDecorations;
    private getColorForLabel;
    clear(uri: vscode.Uri): void;
    dispose(): void;
}
//# sourceMappingURL=gutterDecorations.d.ts.map