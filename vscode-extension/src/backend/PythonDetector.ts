import { exec } from 'child_process';
import * as vscode from 'vscode';

/**
 * Detect a usable Python interpreter (>= 3.10).
 * Priority: user setting > VS Code Python extension > python3 > python > py -3
 */
export async function findPython(userPath?: string): Promise<string> {
    // 1. User-specified path
    if (userPath && userPath !== 'python') {
        const version = await getVersion(userPath);
        if (version) {
            return userPath;
        }
        throw new Error(`Specified Python path "${userPath}" is not valid.`);
    }

    // 2. VS Code Python extension
    const pythonExt = vscode.extensions.getExtension('ms-python.python');
    if (pythonExt) {
        try {
            if (!pythonExt.isActive) {
                await pythonExt.activate();
            }
            const execPath = pythonExt.exports?.environments?.getActiveEnvironmentPath?.();
            if (execPath?.path) {
                const version = await getVersion(execPath.path);
                if (version) {
                    return execPath.path;
                }
            }
        } catch {
            // fall through
        }
    }

    // 3. Try common commands
    const candidates = process.platform === 'win32'
        ? ['python', 'python3', 'py -3']
        : ['python3', 'python'];

    for (const cmd of candidates) {
        const version = await getVersion(cmd);
        if (version) {
            return cmd;
        }
    }

    throw new Error(
        'Python 3.10+ not found. Please install Python or set "python-mentor.pythonPath" in settings.'
    );
}

/** Get Python version string, or null if command fails or version < 3.10. */
async function getVersion(cmd: string): Promise<string | null> {
    return new Promise((resolve) => {
        const proc = cmd.includes(' ')
            ? exec(cmd + ' --version', { timeout: 5000 })
            : exec(`"${cmd}" --version`, { timeout: 5000 });

        let stdout = '';
        let stderr = '';
        proc.stdout?.on('data', (d: string) => (stdout += d));
        proc.stderr?.on('data', (d: string) => (stderr += d));

        proc.on('close', (code) => {
            const output = (stdout + stderr).trim();
            const match = output.match(/Python (\d+)\.(\d+)/);
            if (match) {
                const major = parseInt(match[1], 10);
                const minor = parseInt(match[2], 10);
                if (major === 3 && minor >= 10) {
                    resolve(`${major}.${minor}`);
                    return;
                }
            }
            resolve(null);
        });

        proc.on('error', () => resolve(null));
    });
}

/** Execute a command and return { stdout, stderr, exitCode }. */
export function execAsync(
    command: string,
    options: { cwd?: string; timeout?: number } = {}
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    return new Promise((resolve, reject) => {
        const child = exec(command, {
            cwd: options.cwd,
            timeout: options.timeout ?? 120_000,
            maxBuffer: 10 * 1024 * 1024,
        });

        let stdout = '';
        let stderr = '';
        child.stdout?.on('data', (d: string) => (stdout += d));
        child.stderr?.on('data', (d: string) => (stderr += d));

        child.on('close', (code) => {
            resolve({ stdout, stderr, exitCode: code ?? 1 });
        });

        child.on('error', (err) => reject(err));
    });
}
