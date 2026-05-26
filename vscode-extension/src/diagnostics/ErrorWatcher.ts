import * as vscode from 'vscode';
import { SidebarChatProvider } from '../webview/SidebarChatProvider';

export class ErrorWatcher implements vscode.Disposable {
    private _disposable: vscode.Disposable;
    private _provider: SidebarChatProvider;
    private _debounceTimer: ReturnType<typeof setTimeout> | null = null;
    private _pendingUri: vscode.Uri | null = null;

    constructor(provider: SidebarChatProvider) {
        this._provider = provider;
        this._disposable = vscode.languages.onDidChangeDiagnostics(
            this._onDiagnosticsChange.bind(this)
        );
    }

    private _onDiagnosticsChange(event: vscode.DiagnosticChangeEvent) {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'python') return;

        // Debounce: 同一文件连续变化只触发一次（2 秒内）
        this._pendingUri = editor.document.uri;
        if (this._debounceTimer) {
            clearTimeout(this._debounceTimer);
        }
        this._debounceTimer = setTimeout(() => {
            this._debounceTimer = null;
            if (this._pendingUri) {
                this._checkAndPrompt(this._pendingUri);
                this._pendingUri = null;
            }
        }, 2000);
    }

    private _checkAndPrompt(uri: vscode.Uri) {
        const diagnostics = vscode.languages.getDiagnostics(uri);
        const errors = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error);

        if (errors.length > 0) {
            const errorMessages = errors.map(e => {
                const line = e.range.start.line + 1;
                return `第 ${line} 行: ${e.message}`;
            }).join('\n');

            vscode.window.showInformationMessage(
                `PythonMentor 检测到 ${errors.length} 个错误，需要帮助分析吗？`,
                '是', '否'
            ).then(choice => {
                if (choice === '是') {
                    const fullError = `我在 ${uri.fsPath} 中遇到了以下错误:\n${errorMessages}`;
                    this._provider.sendErrorForDiagnosis(fullError);
                }
            });
        }
    }

    dispose() {
        if (this._debounceTimer) {
            clearTimeout(this._debounceTimer);
        }
        this._disposable.dispose();
    }
}
