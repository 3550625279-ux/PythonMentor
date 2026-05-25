"""RAG 知识库索引构建脚本。

扫描 knowledge-base/ 目录下的 Markdown 和 JSON 文件，
按 heading 分块后生成嵌入向量，存入 ChromaDB collection_knowledge。

用法：
    cd python-backend
    python -m rag.indexer
"""

import json
from pathlib import Path

import chromadb
from rag.embedding_provider import create_embedding_provider


def split_by_heading(text: str, max_chunk: int = 500) -> list[str]:
    """按 Markdown heading（## 级别）分块。

    每遇到一个 ## 标题就开始新的 chunk，
    这样每个 chunk 对应一个完整的知识点。
    """
    chunks = []
    current = ""
    for line in text.split("\n"):
        if line.startswith("## ") and current:
            chunks.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


def build_index(
    knowledge_base_dir: str = "../knowledge-base",
    db_path: str = "../chroma_db",
    api_key: str = "",
    api_model: str = "text-embedding-v4",
    api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    dimensions: int = 1024,
    fallback_model: str = "all-MiniLM-L6-v2",
):
    """构建 RAG 知识库索引。

    扫描 knowledge_base_dir 下所有 .md 和 .json 文件，
    生成嵌入后存入 ChromaDB collection_knowledge。

    Args:
        knowledge_base_dir: 知识库目录路径
        db_path: ChromaDB 持久化存储路径
        api_key: DashScope API key（为空时 fallback 到本地模型）
        api_model: DashScope 模型名
        api_url: DashScope API 地址
        dimensions: 嵌入维度
        fallback_model: 本地 sentence-transformers 模型名
    """
    embedder = create_embedding_provider(
        api_key=api_key, model=api_model, base_url=api_url,
        dimensions=dimensions, fallback_model=fallback_model,
    )

    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(
        name="collection_knowledge",
        metadata={"hnsw:space": "cosine"},
    )

    kb_dir = Path(knowledge_base_dir)
    documents = []
    metadatas = []
    ids = []

    # 1. 扫描 Markdown 文件（textbooks、code_examples 等）
    for md_file in kb_dir.rglob("*.md"):
        # 跳过 teaching_cases 目录下的 md（如果有）
        if "teaching_cases" in str(md_file):
            continue
        print(f"  扫描 Markdown: {md_file.relative_to(kb_dir)}")
        content = md_file.read_text(encoding="utf-8")
        chunks = split_by_heading(content)
        for i, chunk in enumerate(chunks):
            doc_id = f"{md_file.stem}_{i}"
            documents.append(chunk)
            metadatas.append({
                "source": str(md_file.relative_to(kb_dir)),
                "type": "textbook",
            })
            ids.append(doc_id)

    # 2. 扫描错误日志 JSON（error_logs/*.json）
    error_logs_dir = kb_dir / "error_logs"
    if error_logs_dir.exists():
        for json_file in error_logs_dir.glob("*.json"):
            print(f"  扫描错误日志: {json_file.relative_to(kb_dir)}")
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print(f"    跳过（JSON 格式错误）: {json_file.name}")
                continue
            if isinstance(data, list):
                for i, item in enumerate(data):
                    doc_id = f"{json_file.stem}_{i}"
                    # 构建包含新字段的文档文本
                    text = f"错误类型: {item.get('error_type', '')}\n"
                    text += f"模式: {item.get('pattern', '')}\n"
                    text += f"描述: {item.get('description', '')}\n"
                    text += f"引导问题: {item.get('guide_question', '')}\n"
                    if item.get('reasoning_chain'):
                        text += f"推理链: {' -> '.join(item['reasoning_chain'])}\n"
                    if item.get('common_causes'):
                        text += f"常见原因: {', '.join(item['common_causes'])}\n"
                    if item.get('guidance_strategy'):
                        text += f"引导策略: {item['guidance_strategy']}\n"
                    documents.append(text)
                    # 存储增强 metadata
                    metadatas.append({
                        "source": str(json_file.relative_to(kb_dir)),
                        "type": "error_log",
                        "error_type": item.get("error_type", ""),
                        "difficulty": item.get("difficulty", "beginner"),
                        "guidance_strategy": item.get("guidance_strategy", "socratic"),
                        "related_concepts": ",".join(item.get("related_concepts", [])),
                    })
                    ids.append(doc_id)

    # 3. 扫描概念知识（concepts.json）
    concepts_file = kb_dir / "concepts.json"
    if concepts_file.exists():
        print(f"  扫描概念知识: concepts.json")
        with open(concepts_file, encoding="utf-8") as f:
            concepts = json.load(f)
        for concept in concepts:
            doc_id = f"concept_{concept['concept_id']}"
            text = f"概念: {concept.get('name', '')}\n"
            text += f"描述: {concept.get('description', '')}\n"
            if concept.get('common_misconceptions'):
                text += f"常见误解: {'; '.join(concept['common_misconceptions'])}\n"
            if concept.get('teaching_examples'):
                for ex in concept['teaching_examples']:
                    text += f"示例代码:\n{ex.get('code', '')}\n"
                    text += f"说明: {ex.get('explanation', '')}\n"
            if concept.get('related_errors'):
                text += f"相关错误: {', '.join(concept['related_errors'])}\n"
            documents.append(text)
            metadatas.append({
                "source": "concepts.json",
                "type": "concept",
                "concept_id": concept['concept_id'],
                "difficulty": concept.get("difficulty", "beginner"),
            })
            ids.append(doc_id)

    # 4. 扫描教学案例（teaching_cases/*.json）
    cases_dir = kb_dir / "teaching_cases"
    if cases_dir.exists():
        for case_file in cases_dir.glob("*.json"):
            print(f"  扫描教学案例: {case_file.relative_to(kb_dir)}")
            try:
                with open(case_file, encoding="utf-8") as f:
                    case = json.load(f)
            except json.JSONDecodeError:
                print(f"    跳过（JSON 格式错误）: {case_file.name}")
                continue

            case_id = case.get('case_id', case_file.stem)
            text = f"教学案例: {case_id}\n"
            text += f"模式: {case.get('mode', '')}\n"
            text += f"主题: {case.get('topic', '')}\n"
            text += f"难度: {case.get('difficulty', '')}\n"
            # 包含最近几条对话作为参考
            msgs = case.get('messages', [])[-6:]
            for msg in msgs:
                text += f"{msg['role']}: {msg['content']}\n"
            if case.get('key_teaching_moments'):
                text += f"关键教学时刻: {', '.join(case['key_teaching_moments'])}\n"
            documents.append(text)
            metadatas.append({
                "source": f"teaching_cases/{case_file.name}",
                "type": "teaching_case",
                "mode": case.get("mode", ""),
                "difficulty": case.get("difficulty", "beginner"),
            })
            ids.append(case_id)

    # 5. 生成嵌入并存入 ChromaDB
    if documents:
        print(f"正在索引 {len(documents)} 条文档...")
        embeddings = embedder.encode(documents)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        print(f"索引完成！共 {len(documents)} 条文档已存入 collection_knowledge")
    else:
        print("没有找到文档，请检查 knowledge-base 目录。")


if __name__ == "__main__":
    from config import settings
    build_index(
        api_key=settings.embedding_api_key,
        api_model=settings.embedding_api_model,
        api_url=settings.embedding_api_url,
        dimensions=settings.embedding_dimensions,
        fallback_model=settings.embedding_model,
    )
