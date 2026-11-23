import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as vscode from 'vscode';

interface PendingRequest {
    resolve: (value: unknown) => void;
    reject: (error: Error) => void;
}

interface IPCResponse {
    jsonrpc: string;
    id: number;
    result?: unknown;
    error?: { message: string };
}

/**
 * JSON-RPC client for communicating with the codedna-core IPC server.
 */
export class IPCClient extends EventEmitter {
    private pythonPath: string;
    private process: ChildProcess | null = null;
    private pendingRequests: Map<number, PendingRequest> = new Map();
    private requestId = 0;
    private buffer = '';
    private connected = false;

    constructor(pythonPath: string) {
        super();
        this.pythonPath = pythonPath;
    }

    connect(proc: ChildProcess) {
        this.process = proc;
        this.buffer = '';
        this.connected = true;

        proc.stdout?.on('data', (data: Buffer) => {
            this.buffer += data.toString();
            this.processBuffer();
        });

        proc.stderr?.on('data', (data: Buffer) => {
            console.error('CodeDNA IPC stderr:', data.toString());
        });

        proc.on('exit', (code: number) => {
            this.connected = false;
            this.emit('exit', code);
        });

        proc.on('error', (err: Error) => {
            this.emit('error', err);
        });
    }

    private processBuffer() {
        const lines = this.buffer.split('\n');
        this.buffer = lines.pop() || '';

        for (const line of lines) {
            if (!line.trim()) continue;
            try {
                const response: IPCResponse = JSON.parse(line);
                this.handleResponse(response);
            } catch (err) {
                // Ignore non-JSON lines
            }
        }
    }

    private handleResponse(response: IPCResponse) {
        const pending = this.pendingRequests.get(response.id);
        if (!pending) return;

        this.pendingRequests.delete(response.id);

        if (response.error) {
            pending.reject(new Error(response.error.message));
        } else {
            pending.resolve(response.result);
        }
    }

    private async sendRequest(method: string, params: unknown): Promise<unknown> {
        if (!this.connected || !this.process) {
            throw new Error('IPC client not connected');
        }

        const id = ++this.requestId;
        const request = JSON.stringify({ jsonrpc: '2.0', id, method, params });

        return new Promise((resolve, reject) => {
            this.pendingRequests.set(id, { resolve, reject });

            this.process!.stdin?.write(request + '\n', (err: Error | null | undefined) => {
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

    async classify(edits: unknown[]): Promise<unknown> {
        return this.sendRequest('classify', { events: edits });
    }

    async getRatio(file: string): Promise<{ human: number; ai: number; human_pct: number }> {
        return this.sendRequest('get_ratio', { file }) as Promise<{ human: number; ai: number; human_pct: number }>;
    }

    async getAttributions(file: string): Promise<Array<{ start_line: number; end_line: number; label: string; confidence: number; source_hint?: string }>> {
        const result = await this.sendRequest('get_attributions', { file }) as { attributions?: Array<{ start_line: number; end_line: number; label: string; confidence: number; source_hint?: string }> };
        return result.attributions || [];
    }

    async getReport(): Promise<unknown> {
        return this.sendRequest('get_status', {});
    }

    async writeHeader(file: string): Promise<void> {
        const attributions = await this.getAttributions(file);
        if (attributions.length === 0) return;

        const regions = attributions.map((a: { start_line: number; end_line: number; label: string; confidence: number; source_hint?: string }) => ({
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

    async toggleHeader(file: string): Promise<void> {
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

    isConnected(): boolean {
        return this.connected;
    }
}