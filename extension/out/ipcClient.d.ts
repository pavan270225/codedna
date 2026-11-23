import { ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
/**
 * JSON-RPC client for communicating with the codedna-core IPC server.
 */
export declare class IPCClient extends EventEmitter {
    private pythonPath;
    private process;
    private pendingRequests;
    private requestId;
    private buffer;
    private connected;
    constructor(pythonPath: string);
    connect(proc: ChildProcess): void;
    private processBuffer;
    private handleResponse;
    private sendRequest;
    classify(edits: unknown[]): Promise<unknown>;
    getRatio(file: string): Promise<{
        human: number;
        ai: number;
        human_pct: number;
    }>;
    getAttributions(file: string): Promise<Array<{
        start_line: number;
        end_line: number;
        label: string;
        confidence: number;
        source_hint?: string;
    }>>;
    getReport(): Promise<unknown>;
    writeHeader(file: string): Promise<void>;
    toggleHeader(file: string): Promise<void>;
    disconnect(): void;
    isConnected(): boolean;
}
//# sourceMappingURL=ipcClient.d.ts.map