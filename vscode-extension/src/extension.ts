import * as vscode from 'vscode';
import { SidebarChatProvider } from './webview/SidebarChatProvider';
import { ErrorWatcher } from './diagnostics/ErrorWatcher';
import { BackendClient } from './backend/BackendClient';
import { BackendManager } from './backend/BackendManager';

let backendManager: BackendManager;

export function activate(context: vscode.ExtensionContext) {
    console.log('PythonMentor 已激活');

    const backend = new BackendClient();
    backendManager = new BackendManager(context);
    const sidebarProvider = new SidebarChatProvider(backend, context.extensionUri, backendManager);

    // Register sidebar view
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            SidebarChatProvider.viewType,
            sidebarProvider,
            { webviewOptions: { retainContextWhenHidden: true } }
        )
    );

    // Open chat = reveal sidebar
    context.subscriptions.push(
        vscode.commands.registerCommand('python-mentor.openChat', () => {
            vscode.commands.executeCommand('python-mentor.chat.focus');
        })
    );

    // Diagnose error command
    context.subscriptions.push(
        vscode.commands.registerCommand('python-mentor.diagnoseError', () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const selection = editor.document.getText(editor.selection);
                sidebarProvider.sendErrorForDiagnosis(selection);
            }
        })
    );

    // Backend management commands
    context.subscriptions.push(
        vscode.commands.registerCommand('python-mentor.startBackend', () => {
            backendManager.start();
        })
    );
    context.subscriptions.push(
        vscode.commands.registerCommand('python-mentor.stopBackend', () => {
            backendManager.stop();
        })
    );
    context.subscriptions.push(
        vscode.commands.registerCommand('python-mentor.configureApiKeys', () => {
            vscode.commands.executeCommand(
                'workbench.action.openSettings',
                '@ext:Eddie-58-cgw.pythonmentor'
            );
        })
    );

    const errorWatcher = new ErrorWatcher(sidebarProvider);
    context.subscriptions.push(errorWatcher);
    context.subscriptions.push(backendManager);

    // Auto-start backend (non-blocking)
    backendManager.autoStart();
}

export function deactivate() {
    if (backendManager) {
        backendManager.stop();
    }
}
