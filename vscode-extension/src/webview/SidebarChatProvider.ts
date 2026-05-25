import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { BackendClient } from '../backend/BackendClient';
import { BackendManager } from '../backend/BackendManager';
import { getEditorContext } from '../editor/CodeContext';

export class SidebarChatProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'python-mentor.chat';

    private _view?: vscode.WebviewView;
    private _backend: BackendClient;
    private _backendManager: BackendManager;
    private _extensionUri: vscode.Uri;
    private _pendingError?: string;

    constructor(backend: BackendClient, extensionUri: vscode.Uri, backendManager: BackendManager) {
        this._backend = backend;
        this._extensionUri = extensionUri;
        this._backendManager = backendManager;
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri],
        };

        webviewView.webview.html = this._getHtml(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(
            async (message) => {
                if (message.command === 'send') {
                    await this._handleUserMessage(message.text);
                } else if (message.command === 'clear') {
                    this._backend.clearSession(this._backend.getStudentId());
                } else if (message.command === 'endSession') {
                    await this._handleEndSession();
                }
            },
            null,
            []
        );

        // Flush pending error if any
        if (this._pendingError) {
            this._sendDiagnose(this._pendingError);
            this._pendingError = undefined;
        }
    }

    public sendErrorForDiagnosis(errorText: string) {
        if (this._view) {
            this._view.show?.(true);
            this._sendDiagnose(errorText);
        } else {
            this._pendingError = errorText;
        }
    }

    private _sendDiagnose(text: string) {
        this._view?.webview.postMessage({ command: 'diagnose', text });
    }

    private async _handleEndSession() {
        if (!this._view) return;
        try {
            const result = await this._backend.endSession(this._backend.getStudentId());
            this._view.webview.postMessage({
                command: 'session_ended',
                summary: result?.summary
            });
        } catch (error: any) {
            this._view.webview.postMessage({
                command: 'session_ended',
                summary: null
            });
            vscode.window.showWarningMessage(`Failed to end session: ${error.message}`);
        }
    }

    private async _handleUserMessage(content: string) {
        if (!this._view) return;
        try {
            // Ensure backend is running before sending
            if (!this._backendManager.isRunning()) {
                this._view.webview.postMessage({ command: 'status', text: 'Starting backend...' });
                await this._backendManager.start();
                if (!this._backendManager.isRunning()) {
                    this._view.webview.postMessage({ command: 'error', text: 'Backend failed to start.' });
                    return;
                }
            }

            const context = getEditorContext();
            const response = this._backend.chatStream(content, context, this._backend.getStudentId());

            for await (const event of response) {
                if (!this._view) return;
                if (event.type === 'status') {
                    this._view.webview.postMessage({ command: 'status', text: event.value });
                } else if (event.type === 'token') {
                    this._view.webview.postMessage({ command: 'token', text: event.value });
                } else if (event.type === 'done') {
                    this._view.webview.postMessage({ command: 'done' });
                    return;
                }
            }
            this._view?.webview.postMessage({ command: 'done' });
        } catch (error: any) {
            this._view?.webview.postMessage({ command: 'error', text: error.message });
        }
    }

    private _getHtml(webview: vscode.Webview): string {
        const scriptPath = path.join(this._extensionUri.fsPath, 'media', 'chat.js');
        const scriptContent = fs.readFileSync(scriptPath, 'utf-8');

        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: var(--vscode-font-family, sans-serif);
    display: flex; flex-direction: column;
    height: 100vh; color: var(--vscode-foreground);
    font-size: 13px;
}
#messages { flex: 1; overflow-y: auto; padding: 8px; }
.msg { margin: 6px 0; }
.msg-content {
    padding: 6px 10px; border-radius: 8px;
    white-space: pre-wrap; word-wrap: break-word;
    max-width: 90%; line-height: 1.5;
}
.msg.user .msg-content {
    background: var(--vscode-input-background);
    margin-left: auto; text-align: right;
    border: 1px solid var(--vscode-input-border);
}
.msg.bot .msg-content {
    background: var(--vscode-editor-background);
    border: 1px solid var(--vscode-panel-border);
}
.msg.err .msg-content {
    color: var(--vscode-errorForeground);
    border: 1px solid var(--vscode-errorForeground);
}
.msg-content code {
    background: var(--vscode-textCodeBlock-background, rgba(0,0,0,0.15));
    padding: 1px 4px; border-radius: 3px;
    font-family: var(--vscode-editor-font-family, monospace);
}
.code-block {
    position: relative; margin: 6px 0;
    background: var(--vscode-textCodeBlock-background, rgba(0,0,0,0.2));
    border-radius: 6px; overflow: hidden;
}
.code-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 8px; font-size: 11px;
    background: var(--vscode-toolbar-hoverBackground, rgba(0,0,0,0.1));
    color: var(--vscode-descriptionForeground);
}
.copy-btn {
    background: none; border: 1px solid var(--vscode-panel-border);
    color: var(--vscode-descriptionForeground);
    padding: 2px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;
}
.copy-btn:hover { background: var(--vscode-toolbar-hoverBackground); }
.code-block pre {
    margin: 0; padding: 8px 12px; overflow-x: auto;
    font-family: var(--vscode-editor-font-family, monospace);
    font-size: var(--vscode-editor-font-size, 13px); line-height: 1.4;
}
#input-area {
    display: flex; flex-wrap: wrap; gap: 6px; padding: 8px;
    border-top: 1px solid var(--vscode-panel-border); flex-shrink: 0;
    align-items: center;
}
#statusText {
    font-size: 11px; color: var(--vscode-descriptionForeground);
    width: 100%;
}
#msgInput {
    flex: 1; padding: 6px; resize: none;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border); border-radius: 4px;
    font-family: var(--vscode-font-family); font-size: 13px;
    min-height: 32px; max-height: 80px;
}
#msgInput:focus { outline: 1px solid var(--vscode-focusBorder); }
#sendBtn, #clearBtn {
    padding: 6px 10px;
    border: none; border-radius: 4px; cursor: pointer;
    font-size: 12px; flex-shrink: 0;
}
#sendBtn {
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    font-weight: 500;
}
#sendBtn:hover { background: var(--vscode-button-hoverBackground); }
#sendBtn:disabled { opacity: 0.5; cursor: not-allowed; }
#clearBtn, #endBtn {
    background: none;
    color: var(--vscode-descriptionForeground);
    border: 1px solid var(--vscode-panel-border);
}
#clearBtn:hover, #endBtn:hover { background: var(--vscode-toolbar-hoverBackground); }
#endBtn:disabled { opacity: 0.5; cursor: not-allowed; }
.cursor::after { content: '\\2588'; animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }
</style>
</head>
<body>
<div id="messages"></div>
<div id="input-area">
    <span id="statusText">Ready</span>
    <textarea id="msgInput" placeholder="Ask a question..." rows="1"></textarea>
    <button id="sendBtn">Send</button>
    <button id="clearBtn" title="Clear chat">Clear</button>
    <button id="endBtn" title="End session and save progress">End</button>
</div>
<script>${scriptContent}</script>
</body>
</html>`;
    }
}
