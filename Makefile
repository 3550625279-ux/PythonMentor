# PythonMentor Makefile
# 在 Windows 上使用 PowerShell 执行：make <target>

.PHONY: help start-backend start-backend-dev build-extension install-backend install-extension index-knowledge clean

help: ## 显示帮助信息
	@echo "PythonMentor 可用命令："
	@echo ""
	@echo "  make install-backend     安装 Python 后端依赖"
	@echo "  make install-extension   安装 VSCode 插件依赖"
	@echo "  make start-backend       启动后端服务（生产模式）"
	@echo "  make start-backend-dev   启动后端服务（开发模式，自动重载）"
	@echo "  make build-extension     构建 VSCode 插件"
	@echo "  make index-knowledge     构建 RAG 知识库索引"
	@echo "  make clean               清理构建产物"
	@echo ""

install-backend: ## 安装 Python 后端依赖
	cd python-backend && pip install -e .

install-extension: ## 安装 VSCode 插件依赖
	cd vscode-extension && npm install

start-backend: ## 启动后端服务（生产模式）
	cd python-backend && python main.py

start-backend-dev: ## 启动后端服务（开发模式，自动重载）
	cd python-backend && uvicorn main:app --host 127.0.0.1 --port 8000 --reload

build-extension: ## 构建 VSCode 插件
	cd vscode-extension && npm run build

index-knowledge: ## 构建 RAG 知识库索引
	cd python-backend && python -m rag.indexer

clean: ## 清理构建产物
	if exist vscode-extension\dist rmdir /s /q vscode-extension\dist
	if exist python-backend\__pycache__ rmdir /s /q python-backend\__pycache__
	if exist python-backend\rag\__pycache__ rmdir /s /q python-backend\rag\__pycache__
	if exist python-backend\chroma_db rmdir /s /q python-backend\chroma_db
	@echo "清理完成"
