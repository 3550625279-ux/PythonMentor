"""Test RAG module with sentence-transformers"""
import asyncio
import sys, os
import shutil
sys.path.insert(0, os.path.dirname(__file__))

TEST_DB = "./test_chroma_db"

async def main():
    print("=== RAG Module Test ===")

    # Test 1: Import
    try:
        from rag.indexer import split_by_heading, build_index
        from rag.retriever import HybridRetriever
        print("[PASS] RAG modules imported successfully")
    except ImportError as e:
        print(f"[FAIL] RAG import: {e}")
        return

    # Test 2: split_by_heading
    text = """# Title

## Section 1
Content 1

## Section 2
Content 2

## Section 3
Content 3"""
    chunks = split_by_heading(text)
    assert len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}"
    print(f"[PASS] split_by_heading: {len(chunks)} chunks")

    # Test 3: Build index from knowledge-base
    try:
        build_index(
            knowledge_base_dir="../knowledge-base",
            db_path=TEST_DB,
        )
        print("[PASS] Index built successfully")
    except Exception as e:
        print(f"[FAIL] Index build: {e}")
        return

    # Test 4: Retriever
    try:
        retriever = HybridRetriever(db_path=TEST_DB)
        results = retriever.retrieve("TypeError unpack", top_k=3)
        print(f"[PASS] Search returned {len(results)} results")
        if results:
            print(f"  Top result: {results[0].get('text', '')[:100]}...")
            print(f"  Distance: {results[0].get('distance', 'N/A')}")
    except Exception as e:
        print(f"[FAIL] Retrieval: {e}")
        return

    # Test 5: Stats
    try:
        stats = retriever.get_collection_stats()
        print(f"[PASS] Collection stats: {stats}")
    except Exception as e:
        print(f"[FAIL] Stats: {e}")

    # Cleanup (Windows may lock files, ignore errors)
    try:
        if os.path.exists(TEST_DB):
            shutil.rmtree(TEST_DB)
            print("[PASS] Cleanup done")
    except PermissionError:
        print("[INFO] Cleanup skipped (files locked by ChromaDB)")

    print("\n=== RAG Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
