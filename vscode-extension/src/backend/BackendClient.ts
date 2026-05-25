import * as vscode from 'vscode';

export interface ChatEvent {
    type: 'status' | 'token' | 'done';
    value?: string;
}

export class BackendClient {
    private baseUrl: string;
    private maxRetries: number = 2;

    constructor() {
        const config = vscode.workspace.getConfiguration('python-mentor');
        this.baseUrl = config.get<string>('backendUrl', 'http://localhost:8000');
    }

    async *chatStream(
        message: string,
        context: any = {},
        studentId: string = 'default'
    ): AsyncGenerator<ChatEvent> {
        let lastError: Error | null = null;

        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 30000);

                const response = await fetch(`${this.baseUrl}/api/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message,
                        student_id: studentId,
                        context,
                        mode: 'auto'
                    }),
                    signal: controller.signal
                });

                clearTimeout(timeout);

                if (!response.ok) {
                    throw new Error(`Backend error: ${response.status} ${response.statusText}`);
                }

                const reader = response.body?.getReader();
                if (!reader) throw new Error('Cannot read response stream');

                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.done) {
                                    yield { type: 'done' };
                                    return;
                                }
                                if (data.status) {
                                    yield { type: 'status', value: data.status };
                                }
                                if (data.token) {
                                    yield { type: 'token', value: data.token };
                                }
                            } catch {
                                // skip malformed JSON
                            }
                        }
                    }
                }

                yield { type: 'done' };
                return;

            } catch (error: any) {
                lastError = error;
                if (attempt < this.maxRetries) {
                    await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
                    continue;
                }
            }
        }

        throw lastError || new Error('Failed to connect to backend');
    }

    async clearSession(studentId: string = 'default'): Promise<void> {
        try {
            await fetch(`${this.baseUrl}/api/chat/clear?student_id=${studentId}`, {
                method: 'POST'
            });
        } catch {
            // ignore clear errors
        }
    }

    async endSession(studentId: string = 'default'): Promise<any> {
        try {
            const response = await fetch(`${this.baseUrl}/api/chat/end`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: studentId })
            });
            if (!response.ok) {
                throw new Error(`Backend error: ${response.status}`);
            }
            return await response.json();
        } catch (error: any) {
            throw new Error(`Failed to end session: ${error.message}`);
        }
    }

    async healthCheck(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            return response.ok;
        } catch {
            return false;
        }
    }

    getStudentId(): string {
        const config = vscode.workspace.getConfiguration('python-mentor');
        return config.get<string>('studentId', 'default');
    }
}
