import * as vscode from 'vscode';
import { IPCClient } from './ipcClient';
/**
 * Manages the status bar item showing H/AI ratio.
 */
export declare class StatusBarManager {
    private ipcClient;
    private statusBarItem;
    private updateTimer;
    constructor(ipcClient: IPCClient);
    update(uri: vscode.Uri): Promise<void>;
    private render;
    hide(): void;
    dispose(): void;
}
//# sourceMappingURL=statusBar.d.ts.map