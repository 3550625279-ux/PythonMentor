# PythonMentor

基于 RAG 和苏格拉底式教学的个性化 Python 学习助手，以 VSCode 插件形式运行。

## 项目简介

PythonMentor 是一个面向 Python 初学者的智能学习助手。它的核心特点是**不直接给答案**，而是通过苏格拉底式提问引导学生自己发现和解决问题。

### 核心功能

- **苏格拉底式对话**：遇到报错时，AI 不直接给出修复代码，而是通过提问引导学生自己定位问题
- **认知状态追踪**：通过 LLM 实时推断学生的认知状态（概念理解、代码转化、编码、调试）和情绪状态
- **分层提示升级**：根据学生卡住的程度，从轻推（nudge）逐步升级到针对性提问（targeted question）、部分揭示（partial reveal）
- **RAG 知识检索**：基于 ChromaDB 向量数据库检索相关错误模式和知识片段，提供精准的引导
- **自动错误检测**：VSCode 插件自动监听 Python 诊断信息，主动询问是否需要帮助

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | VSCode Extension (TypeScript) | WebView 聊天面板 + 侧边栏 |
| 后端 | Python FastAPI | LLM/RAG 核心逻辑 |
| LLM | Claude API / Ollama | 云端或本地模型 |
| RAG | ChromaDB + sentence-transformers | 嵌入式向量检索 |
| 通信 | HTTP + SSE | 流式响应 |

## 安装步骤

### 前置条件

- Python 3.10+
- Node.js 18+
- VSCode 1.85+
- Ollama（可选，用于本地 LLM）

### 1. 克隆项目

```bash
git clone <repository-url>
cd PythonMentor
```

### 2. 安装后端依赖

```bash
cd python-backend
pip install -e .
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填写配置：

```bash
cp .env.example .env
```

主要配置项：
- `LLM_BACKEND`：选择 LLM 提供商（`ollama` / `claude` / `openai`）
- `OLLAMA_URL`：Ollama 服务地址（默认 `http://localhost:11434`）
- `OLLAMA_MODEL`：使用的模型（默认 `qwen2.5:14b`）
- `EMBEDDING_MODEL`：嵌入模型（默认 `all-MiniLM-L6-v2`）

### 4. 安装插件依赖

```bash
cd vscode-extension
npm install
npm run build
```

### 5. 构建知识库索引

```bash
cd python-backend
python -m rag.indexer
```

## 使用方法

### 启动后端

```bash
cd python-backend
python main.py
```

服务默认运行在 `http://localhost:8000`。

### 运行插件

1. 在 VSCode 中打开项目
2. 按 `F5` 启动调试，会打开一个新的 VSCode 窗口
3. 在新窗口中按 `Ctrl+Shift+P`，输入 "PythonMentor: 打开聊天"
4. 在侧边栏可以看到 PythonMentor 图标

### 使用 Makefile

```bash
make install-backend     # 安装后端依赖
make install-extension   # 安装插件依赖
make start-backend       # 启动后端
make build-extension     # 构建插件
make index-knowledge     # 构建知识库索引
make help                # 查看所有命令
```

## 目录结构

```
PythonMentor/
├── vscode-extension/                    # VSCode 插件
│   ├── package.json                     # 插件清单
│   ├── tsconfig.json                    # TypeScript 配置
│   ├── src/
│   │   ├── extension.ts                 # 插件入口
│   │   ├── webview/ChatPanel.ts         # WebView 面板
│   │   ├── backend/BackendClient.ts     # 后端通信
│   │   ├── diagnostics/ErrorWatcher.ts  # 错误监听
│   │   └── config/Settings.ts           # 用户设置
│   └── webpack.config.js
│
├── python-backend/                      # Python 后端
│   ├── main.py                          # FastAPI 入口
│   ├── config.py                        # 配置管理
│   ├── routers/                         # API 路由
│   │   ├── chat.py                      # /chat 对话端点
│   │   ├── knowledge.py                 # /knowledge/search 知识检索
│   │   └── state.py                     # /state 学生状态
│   ├── llm/                             # LLM 提供商
│   │   ├── provider.py                  # 统一接口
│   │   ├── claude_provider.py           # Claude API
│   │   ├── ollama_provider.py           # Ollama 本地模型
│   │   └── prompts.py                   # System prompt 模板
│   ├── teaching/                        # 教学机制
│   │   ├── cognitive_state.py           # 认知状态定义
│   │   ├── state_evaluator.py           # LLM 驱动的状态评估
│   │   ├── error_diagnosis.py           # 错误诊断
│   │   └── emotion_detector.py          # 情绪检测
│   └── rag/                             # RAG 模块
│       ├── indexer.py                   # 索引构建
│       └── retriever.py                 # 混合检索器
│
├── knowledge-base/                      # RAG 知识库
│   ├── textbooks/                       # 教材
│   │   ├── python_basics.md             # Python 基础知识
│   │   └── python_errors.md             # 常见错误模式
│   ├── error_logs/
│   │   └── common_errors.json           # 结构化错误日志
│   └── code_examples/
│       └── patterns/basic_patterns.md   # 常见代码模式
│
├── Makefile                             # 启动命令
├── .env.example                         # 环境变量模板
└── README.md                            # 本文件
```

## 教学理念

PythonMentor 的教学设计借鉴了以下方案：

- **Khanmigo (Khan Academy)**：分层提示升级机制（nudge → targeted question → partial reveal）
- **Socratic Method**：通过连续提问引导学生自己发现答案
- **认知状态追踪**：实时推断学生处于哪个学习阶段，动态调整教学策略

### 三阶段处理流水线

```
学生消息
  → 阶段 1：快速预筛（traceback 解析、RED 情绪检测）
  → 阶段 2：LLM 状态评估（认知状态、情绪、提示级别）
  → 阶段 3：LLM 教学回复（注入状态评估结果，生成引导性回复）
```

## 许可证

本项目为课程大作业，仅供学习使用。
