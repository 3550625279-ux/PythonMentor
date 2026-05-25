# PythonMentor

个性化 Python 学习助手 — 基于苏格拉底式教学法的 AI 编程导师。

Personalized Python learning assistant — an AI programming tutor based on the Socratic teaching method.

## Features / 功能

- **苏格拉底式对话** — 不直接给答案，通过引导式提问帮助你发现解决方案
- **自动错误检测** — 编辑器中出现 Python 错误时，自动弹出诊断帮助
- **RAG 知识检索** — 内置 Python 知识库，回答基于教材和最佳实践
- **多 LLM 支持** — 支持 Claude、OpenAI、Ollama（本地模型）
- **一键启动** — 扩展激活时自动启动后端，无需手动配置

- **Socratic Dialogue** — Guides you to discover solutions through questions instead of giving direct answers
- **Auto Error Detection** — Automatically prompts for diagnosis when Python errors appear in the editor
- **RAG Knowledge Retrieval** — Built-in Python knowledge base, answers based on textbooks and best practices
- **Multi-LLM Support** — Works with Claude, OpenAI, and Ollama (local models)
- **One-Click Start** — Backend auto-starts on extension activation, no manual setup required

## Quick Start / 快速开始

1. 安装扩展 / Install the extension
2. 打开任意 Python 文件，扩展自动激活并启动后端 / Open any Python file — the extension activates and starts the backend automatically
3. 在侧边栏 Chat 面板中开始提问 / Start asking questions in the sidebar Chat panel

首次启动会自动安装 Python 依赖（约 1-2 分钟），后续启动秒开。

The first launch automatically installs Python dependencies (about 1-2 minutes). Subsequent launches are instant.

## Requirements / 环境要求

- **Python 3.10+**（需在系统 PATH 中，或在设置中指定路径 / must be in PATH or configured in settings）
- **VS Code 1.85+**

## Extension Settings / 扩展设置

| 设置 / Setting | 说明 / Description | 默认值 / Default |
|------|------|--------|
| `python-mentor.llmBackend` | LLM 后端选择 / LLM backend | `ollama` |
| `python-mentor.claudeApiKey` | Claude API Key | - |
| `python-mentor.openaiApiKey` | OpenAI API Key | - |
| `python-mentor.ollamaUrl` | Ollama 服务地址 / Ollama URL | `http://localhost:11434` |
| `python-mentor.ollamaModel` | Ollama 模型名 / Ollama model | `qwen2.5:14b` |
| `python-mentor.pythonPath` | Python 解释器路径 / Python interpreter path | `python` |
| `python-mentor.studentId` | 学生 ID / Student ID | `default` |
| `python-mentor.backendUrl` | 后端服务地址 / Backend URL | `http://localhost:8000` |

## Commands / 命令

| 命令 / Command | 说明 / Description |
|------|------|
| `PythonMentor: Open Chat` | 打开侧边栏聊天面板 / Open sidebar chat panel |
| `PythonMentor: Diagnose Error` | 对选中的代码进行错误诊断 / Diagnose errors in selected code |
| `PythonMentor: Start Backend Server` | 手动启动后端 / Manually start backend |
| `PythonMentor: Stop Backend Server` | 停止后端 / Stop backend |
| `PythonMentor: Configure API Keys` | 打开 API Key 配置 / Open API key settings |

## Known Limitations / 已知限制

- 首次启动需安装 Python 依赖，耗时较长 / First launch requires installing Python dependencies, which takes a while
- Ollama 需要单独安装和运行 / Ollama must be installed and running separately
- RAG 知识库基于内置内容，暂不支持自定义扩展 / RAG knowledge base uses built-in content only; custom extensions not yet supported
