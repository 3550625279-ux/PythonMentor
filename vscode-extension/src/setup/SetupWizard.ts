import * as vscode from 'vscode';

const CONFIGURED_KEY = 'pythonmentor.configured';

/**
 * Check if the user has completed the initial setup wizard.
 */
export function isConfigured(context: vscode.ExtensionContext): boolean {
    return context.globalState.get<boolean>(CONFIGURED_KEY, false);
}

/**
 * Mark the setup as completed.
 */
export function markConfigured(context: vscode.ExtensionContext): Thenable<void> {
    return context.globalState.update(CONFIGURED_KEY, true);
}

/**
 * Reset the configured flag (for re-running the wizard).
 */
export function resetConfigured(context: vscode.ExtensionContext): Thenable<void> {
    return context.globalState.update(CONFIGURED_KEY, false);
}

/**
 * Run the first-time setup wizard.
 * Returns true if the user completed the setup, false if they escaped at any point.
 */
export async function runSetupWizard(context: vscode.ExtensionContext): Promise<boolean> {
    const config = vscode.workspace.getConfiguration('python-mentor');

    // ── Step 1: Choose LLM backend ──
    const backendPick = await vscode.window.showQuickPick(
        [
            {
                label: 'Claude API',
                description: 'Anthropic Claude (requires API Key)',
                detail: 'Recommended for best quality. Get key at console.anthropic.com',
                value: 'claude' as const,
            },
            {
                label: 'OpenAI API',
                description: 'OpenAI GPT (requires API Key)',
                detail: 'Also supports DeepSeek, Xiaomi, and other OpenAI-compatible services',
                value: 'openai' as const,
            },
            {
                label: 'Ollama (Local)',
                description: 'Run models locally (requires Ollama installed)',
                detail: 'Free, no API key needed. Install at ollama.com',
                value: 'ollama' as const,
            },
        ],
        {
            title: 'PythonMentor Setup - Step 1/2: Choose LLM Backend / 选择 LLM 后端',
            placeHolder: 'Select your LLM provider / 选择 LLM 提供商',
            ignoreFocusOut: true,
        }
    );

    if (!backendPick) return false;

    await config.update('llmBackend', backendPick.value, vscode.ConfigurationTarget.Global);

    // ── Step 1b: Enter LLM API Key (skip for Ollama) ──
    if (backendPick.value !== 'ollama') {
        const keyLabel = backendPick.value === 'claude' ? 'Claude API Key' : 'OpenAI API Key';
        const apiKey = await vscode.window.showInputBox({
            title: `PythonMentor Setup - Enter ${keyLabel} / 输入 ${keyLabel}`,
            prompt: `Enter your ${keyLabel} / 输入你的 ${keyLabel}`,
            password: true,
            ignoreFocusOut: true,
            validateInput: (value) => {
                if (!value || value.trim().length === 0) {
                    return 'API Key cannot be empty / API Key 不能为空';
                }
                return null;
            },
        });

        if (!apiKey) return false;

        if (backendPick.value === 'claude') {
            await config.update('claudeApiKey', apiKey.trim(), vscode.ConfigurationTarget.Global);
        } else {
            await config.update('openaiApiKey', apiKey.trim(), vscode.ConfigurationTarget.Global);
        }

        // Optional: custom base URL
        const baseUrl = await vscode.window.showInputBox({
            title: `PythonMentor Setup - Custom Base URL (optional) / 自定义 API 地址（可选）`,
            prompt: 'Leave empty for official API, or enter a custom URL / 留空使用官方 API，或输入自定义地址',
            ignoreFocusOut: true,
            placeHolder: backendPick.value === 'claude'
                ? 'https://api.anthropic.com (default)'
                : 'https://api.openai.com (default)',
        });

        if (baseUrl === undefined) return false; // escaped
        if (baseUrl && baseUrl.trim()) {
            const urlKey = backendPick.value === 'claude' ? 'claudeBaseUrl' : 'openaiBaseUrl';
            await config.update(urlKey, baseUrl.trim(), vscode.ConfigurationTarget.Global);
        }
    }

    // ── Step 2: Embedding API Key ──
    const embeddingChoice = await vscode.window.showQuickPick(
        [
            {
                label: 'DashScope (Alibaba Cloud)',
                description: 'Default embedding service / 默认嵌入服务',
                detail: 'Get key at dashscope.console.aliyun.com',
                value: 'dashscope' as const,
            },
            {
                label: 'OpenAI-Compatible',
                description: 'OpenAI or compatible embedding API / OpenAI 兼容嵌入 API',
                detail: 'Supports OpenAI, DeepSeek, etc.',
                value: 'openai' as const,
            },
            {
                label: 'Skip (no RAG)',
                description: 'Use basic chat without knowledge retrieval',
                detail: 'You can add an embedding key later for RAG support',
                value: 'skip' as const,
            },
        ],
        {
            title: 'PythonMentor Setup - Step 2/2: Embedding Service / 嵌入服务',
            placeHolder: 'Select embedding provider (for RAG knowledge retrieval) / 选择嵌入服务',
            ignoreFocusOut: true,
        }
    );

    if (!embeddingChoice) return false;

    if (embeddingChoice.value !== 'skip') {
        const embeddingKey = await vscode.window.showInputBox({
            title: 'PythonMentor Setup - Embedding API Key / 嵌入 API 密钥',
            prompt: 'Enter your Embedding API Key / 输入嵌入 API 密钥',
            password: true,
            ignoreFocusOut: true,
            validateInput: (value) => {
                if (!value || value.trim().length === 0) {
                    return 'Embedding API Key cannot be empty / 嵌入 API Key 不能为空';
                }
                return null;
            },
        });

        if (!embeddingKey) return false;

        await config.update('embeddingApiKey', embeddingKey.trim(), vscode.ConfigurationTarget.Global);

        if (embeddingChoice.value === 'openai') {
            const embeddingUrl = await vscode.window.showInputBox({
                title: 'PythonMentor Setup - Embedding API URL / 嵌入 API 地址',
                prompt: 'Enter the embedding API base URL / 输入嵌入 API 地址',
                ignoreFocusOut: true,
                placeHolder: 'https://api.openai.com/v1',
                validateInput: (value) => {
                    if (!value || value.trim().length === 0) {
                        return 'URL cannot be empty / 地址不能为空';
                    }
                    return null;
                },
            });

            if (!embeddingUrl) return false;
            await config.update('embeddingApiUrl', embeddingUrl.trim(), vscode.ConfigurationTarget.Global);
        }
    } else {
        await config.update('embeddingApiKey', '', vscode.ConfigurationTarget.Global);
    }

    // ── Done ──
    await markConfigured(context);
    vscode.window.showInformationMessage(
        'PythonMentor: Setup complete! Starting backend... / 配置完成！正在启动后端...'
    );
    return true;
}
