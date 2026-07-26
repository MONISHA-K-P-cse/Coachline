"""
Test-collection shim: stub out ai.rag.retriever so importing the agents never
touches a real ChromaDB collection or downloads a sentence-transformers
embedding model during test collection. Retrieval quality is not what these
unit tests are checking - agents are exercised with fake LLM clients that
depend on prompt *content*, not on the RAG context string - so a fast,
deterministic stub context is used instead of live vector retrieval.

Production code (ai/rag/retriever.py, backend/main.py) is untouched; this
only affects sys.modules inside the pytest process.
"""
import sys
import types


def _install_rag_retriever_stub():
    stub = types.ModuleType("ai.rag.retriever")

    def retrieve(query: str, k: int = 3):
        return [f"(stub retrieval context for '{query}' - no live vector DB in tests)"]

    stub.retrieve = retrieve
    sys.modules["ai.rag.retriever"] = stub


_install_rag_retriever_stub()
