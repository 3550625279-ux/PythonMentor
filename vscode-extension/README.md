# PythonMentor

个性化 Python 学习助手 — 基于苏格拉底式教学法的 AI 编程导师。

## Features

- **苏格拉底式对话**: 不直接给答案，通过引导式提问帮助你发现解决方案
- **自动错误检测**: 编辑器中出现 Python 错误时，自动弹出诊断帮助
- **RAG 知识检索**: 内置 Python 知识库，回答基于教材和最佳实践
- **多 LLM 支持**: 支持 Claude、OpenAI、Ollama（本地模型）
- **一键启动**: 扩展激活时自动启动后端，无需手动配置

## Quick Start

1. 安装扩展
2. 打开任意 Python 文件，扩展自动激活并启动后端
3. 在侧边栏 Chat 面板中开始提问

首次启动会自动安装 Python 依赖（约 1-2 分钟），后续启动秒开。

## Requirements

- **Python 3.10+**（需在系统 PATH 中，或在设置中指定路径）
- **VS Code 1.85+**

## Extension Settings

| 设置 | 说明 | 默认值 |
|------|------|--------|
| `python-mentor.llmBackend` | LLM 后端选择 | `ollama` |
| `python-mentor.claudeApiKey` | Claude API Key | - |
| `python-mentor.openaiApiKey` | OpenAI API Key | - |
| `python-mentor.ollamaUrl` | Ollama 服务地址 | `http://localhost:11434` |
| `python-mentor.ollamaModel` | Ollama 模型名 | `qwen2.5:14b` |
| `python-mentor.pythonPath` | Python 解释器路径 | `python` |

## Commands

- **PythonMentor: 打开聊天** — 打开侧边栏聊天面板
- **PythonMentor: 诊断错误** — 对选中的代码进行错误诊断
- **PythonMentor: Start Backend Server** — 手动启动后端
- **PythonMentor: Stop Backend Server** — 停止后端
- **PythonMentor: Configure API Keys** — 打开 API Key 配置

## Known Limitations

- 首次启动需安装 Python 依赖，耗时较长
- Ollama 需要单独安装和运行
- RAG 知识库基于内置内容，暂不支持自定义扩展
