import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import { EditTracker } from './editTracker';
import { StatusBarManager } from './statusBar';
import { GutterDecorations } from './gutterDecorations';
import { IPCClient } from './ipcClient';

let editTracker: EditTracker;
let statusBar: StatusBarManager;
let gutterDecorations: GutterDecorations;
let ipcClient: IPCClient;
let ipcProcess: ChildProcess | null = null;

export function activate(context: vscode.ExtensionContext) {
    console.log('CodeDNA extension activated');

    // Initialize components
    const config = vscode.workspace.getConfiguration('codedna');
    const pythonPath = config.get<string>('pythonPath', 'python');

    ipcClient = new IPCClient(pythonPath);
    editTracker = new EditTracker(ipcClient);
    statusBar = new StatusBarManager(ipcClient);
    gutterDecorations = new GutterDecorations(ipcClient);

    // Start IPC server
    startIPCServer(pythonPath);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('codedna.toggleHeaders', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                await ipcClient.toggleHeader(editor.document.uri.fsPath);
                vscode.window.showInformationMessage('CodeDNA: Provenance header toggled');
            }
        }),

        vscode.commands.registerCommand('codedna.showReport', async () => {
            const report = await ipcClient.getReport();
            showReportWebview(report);
        }),

        vscode.commands.registerCommand('codedna.showRatio', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const ratio = await ipcClient.getRatio(editor.document.uri.fsPath);
                vscode.window.showInformationMessage(
                    `CodeDNA: ${ratio.human} human / ${ratio.ai} AI lines (${ratio.human_pct.toFixed(1)}% human)`
                );
            }
        }),

        vscode.commands.registerCommand('codedna.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'codedna');
        })
    );

    // Track document changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument(e => {
            if (config.get<boolean>('enabled', true)) {
                editTracker.onDidChangeTextDocument(e);
            }
        })
    );

    // Update decorations on save if auto-write enabled
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async doc => {
            if (config.get<boolean>('autoWriteHeaders', false)) {
                await ipcClient.writeHeader(doc.uri.fsPath);
            }
            gutterDecorations.update(doc.uri);
        })
    );

    // Update status bar on editor change
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) {
                statusBar.update(editor.document.uri);
                gutterDecorations.update(editor.document.uri);
            }
        })
    );

    // Initial update for active editor
    if (vscode.window.activeTextEditor) {
        statusBar.update(vscode.window.activeTextEditor.document.uri);
        gutterDecorations.update(vscode.window.activeTextEditor.document.uri);
    }

    // Cleanup on deactivate
    context.subscriptions.push({ dispose: () => cleanup() });
}

function startIPCServer(pythonPath: string) {
    ipcProcess = spawn(pythonPath, ['-m', 'codedna', 'server'], {
        stdio: ['pipe', 'pipe', 'inherit'],
    });

    ipcProcess.on('error', (err: Error) => {
        console.error('Failed to start IPC server:', err);
        vscode.window.showErrorMessage(`CodeDNA: Failed to start core server: ${err.message}`);
    });

    ipcProcess.on('exit', (code: number) => {
        console.log(`IPC server exited with code ${code}`);
    });

    // Give server time to start
    setTimeout(() => {
        ipcClient.connect(ipcProcess!);
    }, 500);
}

function cleanup() {
    if (ipcProcess) {
        ipcProcess.kill();
        ipcProcess = null;
    }
    ipcClient.disconnect();
    editTracker.dispose();
    statusBar.dispose();
    gutterDecorations.dispose();
}

function showReportWebview(report: any) {
    const panel = vscode.window.createWebviewPanel(
        'codednaReport',
        'CodeDNA Attribution Report',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );

    panel.webview.html = generateReportHTML(report);
}

function generateReportHTML(report: any): string {
    const rows = report.attributions?.map((a: any) => `
        <tr>
            <td>${a.file}</td>
            <td>${a.start_line}-${a.end_line}</td>
            <td><span style="color: ${a.label_color}">${a.label}</span></td>
            <td>${(a.confidence * 100).toFixed(0)}%</td>
        </tr>
    `).join('') || '<tr><td colspan="4">No attribution data</td></tr>';

    return `<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid var(--vscode-panel-border); }
        th { color: var(--vscode-foreground); }
        .summary { margin-bottom: 20px; padding: 15px; background: var(--vscode-editor-inactiveSelectionBackground); border-radius: 4px; }
    </style>
</head>
<body>
    <div class="summary">
        <h2>CodeDNA Attribution Report</h2>
        <p>Human: ${report.human_lines} lines | AI: ${report.ai_lines} lines | ${report.human_pct?.toFixed(1) || 0}% human</p>
    </div>
    <table>
        <thead>
            <tr><th>File</th><th>Lines</th><th>Label</th><th>Confidence</th></tr>
        </thead>
        <tbody>${rows}</tbody>
    </table>
</body>
</html>`;
}

export function deactivate() {
    cleanup();
}
