import * as vscode from 'vscode';
import { IPCClient } from './ipcClient';

/**
 * Manages the status bar item showing H/AI ratio.
 */
export class StatusBarManager {
    private ipcClient: IPCClient;
    private statusBarItem: vscode.StatusBarItem;
    private updateTimer: NodeJS.Timeout | null = null;

    constructor(ipcClient: IPCClient) {
        this.ipcClient = ipcClient;
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'codedna.showReport';
        this.statusBarItem.tooltip = 'CodeDNA: Click for attribution report';
    }

    async update(uri: vscode.Uri) {
        if (!vscode.workspace.getConfiguration('codedna').get<boolean>('showStatusBar', true)) {
            this.hide();
            return;
        }

        try {
            const ratio = await this.ipcClient.getRatio(uri.fsPath);
            this.render(ratio);
        } catch {
            this.statusBarItem.text = '$(pulse) CodeDNA';
            this.statusBarItem.show();
        }
    }

    private render(ratio: { human: number; ai: number; human_pct: number }) {
        const { human, ai, human_pct } = ratio;
        const total = human + ai;

        if (total === 0) {
            this.statusBarItem.text = '$(pulse) CodeDNA: No data';
            this.statusBarItem.color = undefined;
            this.statusBarItem.show();
            return;
        }

        const humanPct = human_pct.toFixed(1);
        this.statusBarItem.text = `$(pulse) H:${human} AI:${ai} (${humanPct}% human)`;

        if (human_pct >= 80) {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.prominentBackground');
        } else if (human_pct >= 50) {
            this.statusBarItem.color = new vscode.ThemeColor('charts.yellow');
        } else {
            this.statusBarItem.color = new vscode.ThemeColor('charts.red');
        }

        this.statusBarItem.show();
    }

    hide() {
        this.statusBarItem.hide();
    }

    dispose() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        this.statusBarItem.dispose();
    }
}