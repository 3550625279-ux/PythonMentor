import * as vscode from 'vscode';

export interface EditorContext {
    file?: string;
    language?: string;
    selection?: string;
    lineCount?: number;
    currentLine?: string;
}

export function getEditorContext(): EditorContext {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return {};

    const document = editor.document;
    const selection = editor.selection;

    return {
        file: document.fileName,
        language: document.languageId,
        selection: document.getText(selection) || undefined,
        lineCount: document.lineCount,
        currentLine: document.lineAt(selection.active.line).text,
    };
}
