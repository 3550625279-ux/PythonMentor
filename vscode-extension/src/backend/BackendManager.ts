import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { ChildProcess, execFile, spawn } from 'child_process';
import { findPython, execAsync, parseCommand } from './PythonDetector';

type BackendStatus = 'stopped' | 'starting' | 'running' | 'error';

export class BackendManager implements vscode.Disposable {
    private status: BackendStatus = 'stopped';
    private process: ChildProcess | null = null;
    private statusBarItem: vscode.StatusBarItem;
    private healthInterval: ReturnType<typeof setInterval> | null = null;
    private backendDir: string;
    private outputChannel: vscode.OutputChannel;

    constructor(private context: vscode.ExtensionContext) {
        // Production: python-backend is bundled inside the extension
        // Development: python-backend lives at the project root (one level up from vscode-extension/)
        const bundledDir = path.join(context.extensionPath, 'python-backend');
        if (fs.existsSync(bundledDir)) {
            this.backendDir = bundledDir;
        } else {
            this.backendDir = path.join(context.extensionPath, '..', 'python-backend');
        }
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

            // 1. Find system Python
            const systemPython = await findPython(userPath);

            // 2. Ensure venv exists
            const venvPython = await this.ensureVenv(systemPython);

            // 3. Check and install deps in venv
            const depsInstalled = await this.checkDepsInstalled(venvPython);
            if (!depsInstalled) {
                await vscode.window.withProgress(
                    { location: vscode.ProgressLocation.Notification, title: 'PythonMentor' },
                    async (progress) => {
                        progress.report({ message: 'Creating virtual environment and installing dependencies (may take 5-20 min on first run)...' });
                        await this.installDeps(venvPython);

                        progress.report({ message: 'Writing configuration...' });
                        this.writeEnvFile();

                        progress.report({ message: 'Starting backend...' });
                        await this.spawnBackend(venvPython);
                    }
                );
            } else {
                this.writeEnvFile();
                await this.spawnBackend(venvPython);
            }

            // 4. Build RAG index if needed
            const chromaPath = path.join(this.backendDir, 'chroma_db');
            let needsIndex = true;
            try {
                const sqlitePath = path.join(chromaPath, 'chroma.sqlite3');
                needsIndex = !fs.existsSync(chromaPath) ||
                    !fs.existsSync(sqlitePath) ||
                    fs.statSync(sqlitePath).size < 50000;
            } catch {
                needsIndex = true;
            }
            if (needsIndex) {
                this.outputChannel.appendLine('Building RAG knowledge index...');
                await this.buildIndex(venvPython);
            }

            // 5. Health check
            const ok = await this.waitForHealth(120_000);
            if (!ok) {
                // Auto-retry once
                this.outputChannel.appendLine('Health check failed, retrying...');
                this.stop();
                await new Promise(r => setTimeout(r, 2000));
                await this.spawnBackend(venvPython);
                const ok2 = await this.waitForHealth(120_000);
                if (ok2) {
                    this.setStatus('running');
                    this.startHealthMonitor();
                    this.checkLlmConfig();
                } else {
                    this.setStatus('error');
                    vscode.window.showErrorMessage(
                        'PythonMentor: Backend failed to start after retry. Check Output panel for details.',
                        'Show Output'
                    ).then(choice => {
                        if (choice === 'Show Output') {
                            this.outputChannel.show();
                        }
                    });
                }
            } else {
                this.setStatus('running');
                this.startHealthMonitor();
                this.checkLlmConfig();
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
                    await this.spawnBackend(pythonPath);

                    progress.report({ message: 'Waiting for backend...' });
                    const ok = await this.waitForHealth(120_000);
                    if (!ok) {
                        throw new Error('Backend failed to start within 120 seconds. Check Output panel for details.');
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

    /** Get the venv Python path for the current platform. */
    private getVenvPython(): string {
        if (process.platform === 'win32') {
            return path.join(this.backendDir, '.venv', 'Scripts', 'python.exe');
        }
        return path.join(this.backendDir, '.venv', 'bin', 'python');
    }

    /**
     * Ensure a venv exists in python-backend/.venv.
     * Returns the path to the venv Python interpreter.
     */
    private async ensureVenv(systemPython: string): Promise<string> {
        const venvPython = this.getVenvPython();

        if (fs.existsSync(venvPython)) {
            this.outputChannel.appendLine(`Using existing venv: ${venvPython}`);
            return venvPython;
        }

        this.outputChannel.appendLine(`Creating venv at ${path.join(this.backendDir, '.venv')}...`);

        const cmd = systemPython.includes(' ')
            ? `"${systemPython}" -m venv .venv`
            : `${systemPython} -m venv .venv`;

        const result = await execAsync(cmd, {
            cwd: this.backendDir,
            timeout: 120_000,
        });

        if (result.exitCode !== 0) {
            this.outputChannel.appendLine(`Venv creation failed: ${result.stderr}`);
            throw new Error(
                'Failed to create Python virtual environment. ' +
                'Ensure Python 3.10+ is installed and the venv module is available.'
            );
        }

        this.outputChannel.appendLine('Venv created successfully.');
        return venvPython;
    }

    /**
     * Full environment preparation: find system Python → ensure venv → install deps → write .env → build index.
     * Returns the venv Python path.
     */
    private async prepareEnvironment(): Promise<string> {
        const config = vscode.workspace.getConfiguration('python-mentor');
        const userPath = config.get<string>('pythonPath', 'python');
        const systemPython = await findPython(userPath);

        const venvPython = await this.ensureVenv(systemPython);

        const depsInstalled = await this.checkDepsInstalled(venvPython);
        if (!depsInstalled) {
            this.outputChannel.appendLine('Installing backend dependencies into venv...');
            await this.installDeps(venvPython);
        }

        this.writeEnvFile();

        const chromaPath = path.join(this.backendDir, 'chroma_db');
        let needsIndex = true;
        try {
            const sqlitePath = path.join(chromaPath, 'chroma.sqlite3');
            needsIndex = !fs.existsSync(chromaPath) ||
                !fs.existsSync(sqlitePath) ||
                fs.statSync(sqlitePath).size < 50000;
        } catch {
            needsIndex = true;
        }
        if (needsIndex) {
            this.outputChannel.appendLine('Building RAG knowledge index...');
            await this.buildIndex(venvPython);
        }

        return venvPython;
    }

    private async checkDepsInstalled(pythonPath: string): Promise<boolean> {
        try {
            const cmd = pythonPath.includes(' ')
                ? `"${pythonPath}" -c "import fastapi; import uvicorn; import chromadb"`
                : `${pythonPath} -c "import fastapi; import uvicorn; import chromadb"`;
            const result = await execAsync(cmd, { cwd: this.backendDir, timeout: 10_000 });
            return result.exitCode === 0;
        } catch {
            return false;
        }
    }

    private async installDeps(pythonPath: string): Promise<void> {
        // Use python -m pip to ensure we use the venv's pip, not a system pip
        const cmd = pythonPath.includes(' ')
            ? `"${pythonPath}" -m pip install . --quiet`
            : `${pythonPath} -m pip install . --quiet`;

        this.outputChannel.appendLine(`Running: ${cmd}`);
        const result = await execAsync(cmd, {
            cwd: this.backendDir,
            timeout: 1_200_000,
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
            '# Claude / Anthropic-compatible',
            `CLAUDE_API_KEY=${config.get<string>('claudeApiKey', '')}`,
            `CLAUDE_BASE_URL=${config.get<string>('claudeBaseUrl', '')}`,
            `CLAUDE_MODEL=${config.get<string>('claudeModel', 'claude-sonnet-4-20250514')}`,
            '',
            '# OpenAI / OpenAI-compatible (DeepSeek, Xiaomi, etc.)',
            `OPENAI_API_KEY=${config.get<string>('openaiApiKey', '')}`,
            `OPENAI_BASE_URL=${config.get<string>('openaiBaseUrl', '')}`,
            `OPENAI_MODEL=${config.get<string>('openaiModel', 'gpt-4o')}`,
            '',
            '# Ollama',
            `OLLAMA_URL=${config.get<string>('ollamaUrl', 'http://localhost:11434')}`,
            `OLLAMA_MODEL=${config.get<string>('ollamaModel', 'qwen2.5:14b')}`,
            '',
            '# Embedding API',
            `EMBEDDING_API_KEY=${config.get<string>('embeddingApiKey', '')}`,
            `EMBEDDING_API_MODEL=${config.get<string>('embeddingModel', 'text-embedding-v4')}`,
            `EMBEDDING_API_URL=${config.get<string>('embeddingApiUrl', 'https://dashscope.aliyuncs.com/compatible-mode/v1')}`,
            '',
            '# LLM Parameters',
            `MAX_TOKENS=${config.get<number>('maxTokens', 2048)}`,
            `TEMPERATURE=${config.get<number>('temperature', 0.7)}`,
            `TOP_P=${config.get<number>('topP', 1.0)}`,
            `CONTEXT_WINDOW=${config.get<number>('contextWindow', 40)}`,
        ];

        const envPath = path.join(this.backendDir, '.env');
        fs.writeFileSync(envPath, lines.join('\n'), 'utf-8');
    }

    private async buildIndex(pythonPath: string): Promise<void> {
        const cmd = pythonPath.includes(' ')
            ? `"${pythonPath}" -m rag.indexer`
            : `${pythonPath} -m rag.indexer`;

        this.outputChannel.appendLine('Building RAG index...');
        const result = await execAsync(cmd, {
            cwd: this.backendDir,
            timeout: 300_000,
        });

        if (result.exitCode !== 0) {
            this.outputChannel.appendLine(`RAG indexing warning: ${result.stderr}`);
        } else {
            this.outputChannel.appendLine('RAG index built successfully.');
        }
    }

    /** Kill any process occupying the backend port. */
    private async killPortOccupant(): Promise<void> {
        const config = vscode.workspace.getConfiguration('python-mentor');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        const url = new URL(backendUrl);
        const port = url.port || '8000';

        try {
            const { execSync } = require('child_process');
            if (process.platform === 'win32') {
                const output = execSync(`netstat -ano | findstr ":${port} " | findstr "LISTENING"`, {
                    encoding: 'utf-8', timeout: 5000,
                }).trim();
                if (output) {
                    const match = output.match(/\s(\d+)\s*$/);
                    if (match) {
                        const pid = match[1];
                        this.outputChannel.appendLine(`Port ${port} occupied by PID ${pid}, killing...`);
                        execSync(`taskkill /F /PID ${pid}`, { timeout: 5000 });
                        await new Promise(r => setTimeout(r, 1000));
                    }
                }
            } else {
                // Unix: lsof -ti :PORT | xargs kill -9
                try {
                    const pid = execSync(`lsof -ti :${port}`, { encoding: 'utf-8', timeout: 5000 }).trim();
                    if (pid) {
                        this.outputChannel.appendLine(`Port ${port} occupied by PID ${pid}, killing...`);
                        execSync(`kill -9 ${pid}`, { timeout: 5000 });
                        await new Promise(r => setTimeout(r, 1000));
                    }
                } catch {
                    // No process on port
                }
            }
        } catch {
            // No process on port or kill failed — proceed and let spawn fail with clear error
        }
    }

    /** Start backend as a child process (more reliable than terminal). */
    private async spawnBackend(pythonPath: string): Promise<void> {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }

        const mainPy = path.join(this.backendDir, 'main.py');
        this.outputChannel.appendLine(`Starting backend: ${pythonPath} "${mainPy}"`);
        this.outputChannel.appendLine(`Backend dir: ${this.backendDir}`);

        // Pre-flight checks
        if (!fs.existsSync(this.backendDir)) {
            throw new Error(`Backend directory not found: ${this.backendDir}. The extension may be corrupted — try reinstalling.`);
        }
        if (!fs.existsSync(mainPy)) {
            throw new Error(`Backend main.py not found at: ${mainPy}. The extension may be corrupted — try reinstalling.`);
        }

        // Kill any leftover process on the backend port
        await this.killPortOccupant();

        // 直接 spawn Python，不用 shell（避免 cmd.exe ENOENT 问题）
        // py -3 需要拆分为 executable + args
        const { exe: rawExe, args: extraArgs } = parseCommand(pythonPath);
        // 规范化路径：resolve 处理相对路径和 ..，normalize 处理 Unicode
        const exe = path.resolve(rawExe);

        if (!fs.existsSync(exe)) {
            throw new Error(`Python executable not found: ${exe}. Check "python-mentor.pythonPath" setting or reinstall your Python environment.`);
        }
        this.outputChannel.appendLine(`Resolved exe: ${exe}`);

        this.outputChannel.appendLine(`[diag] rawExe="${rawExe}" exe="${exe}"`);
        this.outputChannel.appendLine(`[diag] existsSync=${fs.existsSync(exe)}`);
        this.outputChannel.appendLine(`[diag] platform=${process.platform} ComSpec=${process.env.ComSpec}`);

        // Windows: 用 shell + 显式 ComSpec 路径，解决 spawn ENOENT
        // 其他平台: 直接 spawn
        const isWin = process.platform === 'win32';
        const shellOpt = isWin ? (process.env.ComSpec || true) : false;
        this.outputChannel.appendLine(`[diag] isWin=${isWin} shell=${shellOpt}`);

        const child = spawn(exe, [...extraArgs, mainPy], {
            cwd: this.backendDir,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
            shell: shellOpt,
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
            if (this.status === 'starting' || this.status === 'running') {
                vscode.window.showErrorMessage(
                    `PythonMentor backend exited unexpectedly (code ${code}). Check Output panel for details.`,
                    'Show Output', 'Retry'
                ).then(choice => {
                    if (choice === 'Show Output') {
                        this.outputChannel.show();
                    } else if (choice === 'Retry') {
                        this.start();
                    }
                });
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
            // 进程已退出则提前终止（端口冲突、启动错误等）
            if (!this.process) {
                this.outputChannel.appendLine('Backend process exited during health check.');
                return false;
            }
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

    private checkLlmConfig(): void {
        const config = vscode.workspace.getConfiguration('python-mentor');
        const llmBackend = config.get<string>('llmBackend', 'ollama');

        const missing: string[] = [];

        // Check LLM API key
        if (llmBackend === 'claude' && !config.get<string>('claudeApiKey', '')) {
            missing.push('Claude API Key');
        } else if (llmBackend === 'openai' && !config.get<string>('openaiApiKey', '')) {
            missing.push('OpenAI API Key');
        }

        // Check embedding API key (required for RAG knowledge retrieval)
        if (!config.get<string>('embeddingApiKey', '')) {
            missing.push('Embedding API Key');
        }

        if (missing.length > 0) {
            vscode.window.showWarningMessage(
                `PythonMentor: Missing ${missing.join(' and ')}. Please configure to use full functionality.`,
                'Configure API Keys'
            ).then(choice => {
                if (choice === 'Configure API Keys') {
                    vscode.commands.executeCommand('python-mentor.configureApiKeys');
                }
            });
        }
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
