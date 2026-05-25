import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { ChildProcess, spawn } from 'child_process';
import { findPython, execAsync } from './PythonDetector';

type BackendStatus = 'stopped' | 'starting' | 'running' | 'error';

export class BackendManager implements vscode.Disposable {
    private status: BackendStatus = 'stopped';
    private process: ChildProcess | null = null;
    private statusBarItem: vscode.StatusBarItem;
    private healthInterval: ReturnType<typeof setInterval> | null = null;
    private backendDir: string;
    private outputChannel: vscode.OutputChannel;

    constructor(private context: vscode.ExtensionContext) {
        this.backendDir = path.join(context.extensionPath, 'python-backend');
        this.outputChannel = vscode.window.createOutputChannel('PythonMentor Backend');

        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right, -1
        );
        this.updateStatusBar();
        this.statusBarItem.show();
        context.subscriptions.push(this.statusBarItem, this.outputChannel);
    }

    // --- Public API ---

    /** Silent auto-start on extension activation. */
    async autoStart(): Promise<void> {
        try {
            this.setStatus('starting');
            const config = vscode.workspace.getConfiguration('python-mentor');
            const userPath = config.get<string>('pythonPath', 'python');

            const pythonPath = await findPython(userPath);
            const depsInstalled = await this.checkDepsInstalled(pythonPath);

            if (!depsInstalled) {
                await vscode.window.withProgress(
                    { location: vscode.ProgressLocation.Notification, title: 'PythonMentor' },
                    async (progress) => {
                        progress.report({ message: 'Installing Python dependencies (first time)...' });
                        await this.installDeps(pythonPath);

                        progress.report({ message: 'Writing configuration...' });
                        this.writeEnvFile();

                        const chromaPath = path.join(this.backendDir, 'chroma_db');
                        if (!fs.existsSync(chromaPath)) {
                            progress.report({ message: 'Building knowledge index...' });
                            await this.buildIndex(pythonPath);
                        }

                        progress.report({ message: 'Starting backend...' });
                        this.spawnBackend(pythonPath);
                    }
                );
            } else {
                this.writeEnvFile();
                this.spawnBackend(pythonPath);
            }

            const ok = await this.waitForHealth(60_000);
            if (ok) {
                this.setStatus('running');
                this.startHealthMonitor();
            } else {
                this.setStatus('error');
            }
        } catch (err: any) {
            this.outputChannel.appendLine(`Auto-start failed: ${err.message}`);
            this.setStatus('error');
            vscode.window.showErrorMessage(
                `PythonMentor: ${err.message}`,
                'Show Details', 'Retry'
            ).then(choice => {
                if (choice === 'Show Details') {
                    this.outputChannel.show();
                } else if (choice === 'Retry') {
                    this.start();
                }
            });
        }
    }

    /** Manual start with progress notification. */
    async start(): Promise<void> {
        if (this.status === 'running') {
            vscode.window.showInformationMessage('Backend is already running.');
            return;
        }

        try {
            this.setStatus('starting');
            await vscode.window.withProgress(
                { location: vscode.ProgressLocation.Notification, title: 'PythonMentor' },
                async (progress) => {
                    progress.report({ message: 'Detecting Python...' });
                    const pythonPath = await this.prepareEnvironment();

                    progress.report({ message: 'Starting backend server...' });
                    this.spawnBackend(pythonPath);

                    progress.report({ message: 'Waiting for backend...' });
                    const ok = await this.waitForHealth(60_000);
                    if (!ok) {
                        throw new Error('Backend failed to start within 60 seconds. Check Output panel for details.');
                    }
                }
            );
            this.setStatus('running');
            this.startHealthMonitor();
            vscode.window.showInformationMessage('PythonMentor backend started.');
        } catch (err: any) {
            this.setStatus('error');
            vscode.window.showErrorMessage(`Failed to start backend: ${err.message}`);
        }
    }

    /** Stop the backend. */
    stop(): void {
        if (this.healthInterval) {
            clearInterval(this.healthInterval);
            this.healthInterval = null;
        }
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
        this.setStatus('stopped');
    }

    isRunning(): boolean {
        return this.status === 'running';
    }

    dispose(): void {
        this.stop();
        this.statusBarItem.dispose();
        this.outputChannel.dispose();
    }

    // --- Internal ---

    private async prepareEnvironment(): Promise<string> {
        const config = vscode.workspace.getConfiguration('python-mentor');
        const userPath = config.get<string>('pythonPath', 'python');
        const pythonPath = await findPython(userPath);

        const depsInstalled = await this.checkDepsInstalled(pythonPath);
        if (!depsInstalled) {
            this.outputChannel.appendLine('Installing backend dependencies...');
            await this.installDeps(pythonPath);
        }

        this.writeEnvFile();

        const chromaPath = path.join(this.backendDir, 'chroma_db');
        if (!fs.existsSync(chromaPath)) {
            this.outputChannel.appendLine('Building RAG knowledge index...');
            await this.buildIndex(pythonPath);
        }

        return pythonPath;
    }

    private async checkDepsInstalled(pythonPath: string): Promise<boolean> {
        try {
            const cmd = pythonPath.includes(' ')
                ? `${pythonPath} -c "import fastapi"`
                : `"${pythonPath}" -c "import fastapi"`;
            const result = await execAsync(cmd, { cwd: this.backendDir, timeout: 10_000 });
            return result.exitCode === 0;
        } catch {
            return false;
        }
    }

    private async installDeps(pythonPath: string): Promise<void> {
        const cmd = pythonPath.includes(' ')
            ? `${pythonPath} -m pip install -e . --quiet`
            : `"${pythonPath}" -m pip install -e . --quiet`;

        this.outputChannel.appendLine(`Running: ${cmd}`);
        const result = await execAsync(cmd, {
            cwd: this.backendDir,
            timeout: 300_000,
        });

        if (result.exitCode !== 0) {
            this.outputChannel.appendLine(result.stderr);
            throw new Error('Failed to install backend dependencies. Check your internet connection and try again.');
        }
        this.outputChannel.appendLine('Dependencies installed successfully.');
    }

    private writeEnvFile(): void {
        const config = vscode.workspace.getConfiguration('python-mentor');
        const llmBackend = config.get<string>('llmBackend', 'ollama');

        const lines: string[] = [
            `LLM_BACKEND=${llmBackend}`,
            '',
            '# Claude',
            `CLAUDE_API_KEY=${config.get<string>('claudeApiKey', '')}`,
            `CLAUDE_MODEL=claude-sonnet-4-20250514`,
            '',
            '# OpenAI',
            `OPENAI_API_KEY=${config.get<string>('openaiApiKey', '')}`,
            `OPENAI_MODEL=gpt-4o`,
            '',
            '# Ollama',
            `OLLAMA_URL=${config.get<string>('ollamaUrl', 'http://localhost:11434')}`,
            `OLLAMA_MODEL=${config.get<string>('ollamaModel', 'qwen2.5:14b')}`,
        ];

        const envPath = path.join(this.backendDir, '.env');
        fs.writeFileSync(envPath, lines.join('\n'), 'utf-8');
    }

    private async buildIndex(pythonPath: string): Promise<void> {
        const cmd = pythonPath.includes(' ')
            ? `${pythonPath} -m rag.indexer`
            : `"${pythonPath}" -m rag.indexer`;

        this.outputChannel.appendLine('Building RAG index...');
        const result = await execAsync(cmd, {
            cwd: this.backendDir,
            timeout: 120_000,
        });

        if (result.exitCode !== 0) {
            this.outputChannel.appendLine(`RAG indexing warning: ${result.stderr}`);
        } else {
            this.outputChannel.appendLine('RAG index built successfully.');
        }
    }

    /** Start backend as a child process (more reliable than terminal). */
    private spawnBackend(pythonPath: string): void {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }

        const mainPy = path.join(this.backendDir, 'main.py');
        this.outputChannel.appendLine(`Starting backend: ${pythonPath} "${mainPy}"`);
        this.outputChannel.appendLine(`Backend dir: ${this.backendDir}`);

        const child = spawn(pythonPath, [mainPy], {
            cwd: this.backendDir,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
        });

        this.process = child;

        child.stdout?.on('data', (data: Buffer) => {
            this.outputChannel.appendLine(`[backend] ${data.toString().trim()}`);
        });

        child.stderr?.on('data', (data: Buffer) => {
            this.outputChannel.appendLine(`[backend] ${data.toString().trim()}`);
        });

        child.on('error', (err) => {
            this.outputChannel.appendLine(`Backend process error: ${err.message}`);
            this.setStatus('error');
        });

        child.on('exit', (code, signal) => {
            this.outputChannel.appendLine(`Backend exited: code=${code}, signal=${signal}`);
            if (this.status === 'running') {
                this.setStatus('error');
            }
            this.process = null;
        });
    }

    private async waitForHealth(maxMs: number): Promise<boolean> {
        const config = vscode.workspace.getConfiguration('python-mentor');
        const baseUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        const deadline = Date.now() + maxMs;
        this.outputChannel.appendLine(`Waiting for backend at ${baseUrl}/health (timeout: ${maxMs}ms)`);

        while (Date.now() < deadline) {
            try {
                const resp = await fetch(`${baseUrl}/health`, {
                    signal: AbortSignal.timeout(2000),
                });
                if (resp.ok) {
                    this.outputChannel.appendLine('Backend health check passed.');
                    return true;
                }
            } catch {
                // not ready yet
            }
            await new Promise((r) => setTimeout(r, 1000));
        }
        this.outputChannel.appendLine(`Backend health check timed out after ${maxMs}ms.`);
        return false;
    }

    private startHealthMonitor(): void {
        if (this.healthInterval) {
            clearInterval(this.healthInterval);
        }

        this.healthInterval = setInterval(async () => {
            const config = vscode.workspace.getConfiguration('python-mentor');
            const baseUrl = config.get<string>('backendUrl', 'http://localhost:8000');
            try {
                const resp = await fetch(`${baseUrl}/health`, {
                    signal: AbortSignal.timeout(5000),
                });
                if (resp.ok) {
                    if (this.status !== 'running') {
                        this.setStatus('running');
                    }
                } else {
                    this.setStatus('error');
                }
            } catch {
                if (this.status === 'running') {
                    this.setStatus('error');
                }
            }
        }, 30_000);
    }

    private setStatus(newStatus: BackendStatus): void {
        this.status = newStatus;
        this.updateStatusBar();
    }

    private updateStatusBar(): void {
        switch (this.status) {
            case 'starting':
                this.statusBarItem.text = '$(loading~spin) PythonMentor';
                this.statusBarItem.tooltip = 'Starting backend...';
                this.statusBarItem.command = undefined;
                break;
            case 'running':
                this.statusBarItem.text = '$(check) PythonMentor';
                this.statusBarItem.tooltip = 'Backend running (click to stop)';
                this.statusBarItem.command = 'python-mentor.stopBackend';
                break;
            case 'stopped':
                this.statusBarItem.text = '$(warning) PythonMentor';
                this.statusBarItem.tooltip = 'Backend stopped (click to start)';
                this.statusBarItem.command = 'python-mentor.startBackend';
                break;
            case 'error':
                this.statusBarItem.text = '$(error) PythonMentor';
                this.statusBarItem.tooltip = 'Backend error (click to retry)';
                this.statusBarItem.command = 'python-mentor.startBackend';
                break;
        }
    }
}
