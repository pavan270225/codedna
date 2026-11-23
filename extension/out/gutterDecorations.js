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
exports.GutterDecorations = void 0;
const vscode = __importStar(require("vscode"));
/**
 * Manages gutter decorations showing AI/human attribution per line.
 */
class GutterDecorations {
    constructor(ipcClient) {
        this.decorationTypes = new Map();
        this.currentDecorations = new Map();
        this.ipcClient = ipcClient;
    }
    async update(uri) {
        if (!vscode.workspace.getConfiguration('codedna').get('showGutterDecorations', true)) {
            this.clear(uri);
            return;
        }
        try {
            const attributions = await this.ipcClient.getAttributions(uri.fsPath);
            this.applyDecorations(uri, attributions);
        }
        catch (err) {
            console.error('CodeDNA: Failed to update gutter decorations:', err);
        }
    }
    applyDecorations(uri, attributions) {
        const editor = vscode.window.visibleTextEditors.find(e => e.document.uri.fsPath === uri.fsPath);
        if (!editor) {
            return;
        }
        const rangesByLabel = new Map();
        for (const attr of attributions) {
            const label = attr.label;
            const color = attr.label_color || this.getColorForLabel(label);
            if (!rangesByLabel.has(label)) {
                rangesByLabel.set(label, []);
            }
            const range = new vscode.Range(attr.start_line - 1, 0, attr.end_line - 1, 0);
            rangesByLabel.get(label).push(range);
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
    getColorForLabel(label) {
        switch (label.toLowerCase()) {
            case 'human': return '#22c55e';
            case 'ai-generated': return '#3b82f6';
            case 'ai-modified': return '#f97316';
            case 'ambiguous': return '#a855f7';
            default: return '#888888';
        }
    }
    clear(uri) {
        const editor = vscode.window.visibleTextEditors.find(e => e.document.uri.fsPath === uri.fsPath);
        if (!editor)
            return;
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
exports.GutterDecorations = GutterDecorations;
//# sourceMappingURL=gutterDecorations.js.map