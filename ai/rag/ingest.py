from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


DOCS_DIR = Path(__file__).parent / "docs"

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(
    name="coachline_docs",
    embedding_function=embedding_function,
)


def ingest_documents():
    
    for file in DOCS_DIR.glob("*.md"):
        text = file.read_text(encoding="utf-8")

        collection.add(
            documents=[text],
            ids=[file.stem],
            metadatas=[{"topic": file.stem}],
        )

    print("Documents indexed successfully!")


if __name__ == "__main__":
    ingest_documents()