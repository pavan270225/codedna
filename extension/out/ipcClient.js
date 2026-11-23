"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.IPCClient = void 0;
const events_1 = require("events");
/**
 * JSON-RPC client for communicating with the codedna-core IPC server.
 */
class IPCClient extends events_1.EventEmitter {
    constructor(pythonPath) {
        super();
        this.process = null;
        this.pendingRequests = new Map();
        this.requestId = 0;
        this.buffer = '';
        this.connected = false;
        this.pythonPath = pythonPath;
    }
    connect(proc) {
        this.process = proc;
        this.buffer = '';
        this.connected = true;
        proc.stdout?.on('data', (data) => {
            this.buffer += data.toString();
            this.processBuffer();
        });
        proc.stderr?.on('data', (data) => {
            console.error('CodeDNA IPC stderr:', data.toString());
        });
        proc.on('exit', (code) => {
            this.connected = false;
            this.emit('exit', code);
        });
        proc.on('error', (err) => {
            this.emit('error', err);
        });
    }
    processBuffer() {
        const lines = this.buffer.split('\n');
        this.buffer = lines.pop() || '';
        for (const line of lines) {
            if (!line.trim())
                continue;
            try {
                const response = JSON.parse(line);
                this.handleResponse(response);
            }
            catch (err) {
                // Ignore non-JSON lines
            }
        }
    }
    handleResponse(response) {
        const pending = this.pendingRequests.get(response.id);
        if (!pending)
            return;
        this.pendingRequests.delete(response.id);
        if (response.error) {
            pending.reject(new Error(response.error.message));
        }
        else {
            pending.resolve(response.result);
        }
    }
    async sendRequest(method, params) {
        if (!this.connected || !this.process) {
            throw new Error('IPC client not connected');
        }
        const id = ++this.requestId;
        const request = JSON.stringify({ jsonrpc: '2.0', id, method, params });
        return new Promise((resolve, reject) => {
            this.pendingRequests.set(id, { resolve, reject });
            this.process.stdin?.write(request + '\n', (err) => {
                if (err) {
                    this.pendingRequests.delete(id);
                    reject(err);
                }
            });
            setTimeout(() => {
                if (this.pendingRequests.has(id)) {
                    this.pendingRequests.delete(id);
                    reject(new Error('Request timeout'));
                }
            }, 10000);
        });
    }
    async classify(edits) {
        return this.sendRequest('classify', { events: edits });
    }
    async getRatio(file) {
        return this.sendRequest('get_ratio', { file });
    }
    async getAttributions(file) {
        const result = await this.sendRequest('get_attributions', { file });
        return result.attributions || [];
    }
    async getReport() {
        return this.sendRequest('get_status', {});
    }
    async writeHeader(file) {
        const attributions = await this.getAttributions(file);
        if (attributions.length === 0)
            return;
        const regions = attributions.map(a => ({
            start_line: a.start_line,
            end_line: a.end_line,
            label: a.label,
            confidence: a.confidence,
            author: a.source_hint || (a.label !== 'human' ? 'ai' : 'human'),
            rules: [],
        }));
        const header = {
            version: 1,
            regions,
            used_by: ['vscode-extension'],
            rules: [],
        };
        await this.sendRequest('write_header', { file, header });
    }
    async toggleHeader(file) {
        await this.writeHeader(file);
    }
    disconnect() {
        this.connected = false;
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
        this.pendingRequests.forEach(({ reject }) => {
            reject(new Error('Client disconnected'));
        });
        this.pendingRequests.clear();
    }
    isConnected() {
        return this.connected;
    }
}
exports.IPCClient = IPCClient;
//# sourceMappingURL=ipcClient.js.map