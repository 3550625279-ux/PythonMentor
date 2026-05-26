import { execFile, spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
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
        const { exe: rawExe, args } = parseCommand(cmd);
        const exe = path.isAbsolute(rawExe) ? path.normalize(rawExe) : rawExe;

        execFile(exe, [...args, '--version'], { timeout: 5000 }, (error, stdout, stderr) => {
            if (error) { resolve(null); return; }
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
    });
}

/** 将命令字符串拆分为 executable + args（处理带引号的路径）。 */
function parseCommand(command: string): { exe: string; args: string[] } {
    const parts: string[] = [];
    let current = '';
    let inQuote = false;
    let quoteChar = '';
    for (const ch of command) {
        if (inQuote) {
            if (ch === quoteChar) { inQuote = false; }
            else { current += ch; }
        } else if (ch === '"' || ch === "'") {
            inQuote = true;
            quoteChar = ch;
        } else if (ch === ' ' || ch === '\t') {
            if (current) { parts.push(current); current = ''; }
        } else {
            current += ch;
        }
    }
    if (current) parts.push(current);
    return { exe: parts[0] || '', args: parts.slice(1) };
}

/** Execute a command via execFile (no shell) and return { stdout, stderr, exitCode }. */
export function execAsync(
    command: string,
    options: { cwd?: string; timeout?: number } = {}
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    return new Promise((resolve, reject) => {
        const { exe: rawExe, args } = parseCommand(command);
        const exe = path.isAbsolute(rawExe) ? path.normalize(rawExe) : rawExe;
        const timeout = options.timeout ?? 120_000;

        execFile(exe, args, { cwd: options.cwd, timeout, windowsHide: true }, (error, stdout, stderr) => {
            if (error && !('exitCode' in error)) {
                // 真正的错误（找不到文件等），不是 exit code 非零
                reject(error);
                return;
            }
            resolve({
                stdout: stdout || '',
                stderr: stderr || '',
                exitCode: error ? (error as any).exitCode ?? 1 : 0,
            });
        });
    });
}
