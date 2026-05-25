import * as vscode from 'vscode';
import { SidebarChatProvider } from '../webview/SidebarChatProvider';

export class ErrorWatcher implements vscode.Disposable {
    private _disposable: vscode.Disposable;
    private _provider: SidebarChatProvider;

    constructor(provider: SidebarChatProvider) {
        this._provider = provider;
        this._disposable = vscode.languages.onDidChangeDiagnostics(
            this._onDiagnosticsChange.bind(this)
        );
    }

    private _onDiagnosticsChange(event: vscode.DiagnosticChangeEvent) {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'python') return;

        const diagnostics = vscode.languages.getDiagnostics(editor.document.uri);
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
                    const fullError = `我在 ${editor.document.fileName} 中遇到了以下错误:\n${errorMessages}`;
                    this._provider.sendErrorForDiagnosis(fullError);
                }
            });
        }
    }

    dispose() {
        this._disposable.dispose();
    }
}
