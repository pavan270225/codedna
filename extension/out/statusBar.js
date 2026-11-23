"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.StatusBarManager = void 0;
const vscode = __importStar(require("vscode"));
/**
 * Manages the status bar item showing H/AI ratio.
 */
class StatusBarManager {
    constructor(ipcClient) {
        this.updateTimer = null;
        this.ipcClient = ipcClient;
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.statusBarItem.command = 'codedna.showReport';
        this.statusBarItem.tooltip = 'CodeDNA: Click for attribution report';
    }
    async update(uri) {
        if (!vscode.workspace.getConfiguration('codedna').get('showStatusBar', true)) {
            this.hide();
            return;
        }
        try {
            const ratio = await this.ipcClient.getRatio(uri.fsPath);
            this.render(ratio);
        }
        catch {
            this.statusBarItem.text = '$(pulse) CodeDNA';
            this.statusBarItem.show();
        }
    }
    render(ratio) {
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
        }
        else if (human_pct >= 50) {
            this.statusBarItem.color = new vscode.ThemeColor('charts.yellow');
        }
        else {
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
exports.StatusBarManager = StatusBarManager;
//# sourceMappingURL=statusBar.js.map