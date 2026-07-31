from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


DOCS_DIR = Path(__file__).parent / "docs"

# Role/topic tags per doc. retriever.py uses these to restrict the candidate
# pool to docs actually relevant to the query's role before falling back to
# pure embedding similarity - two generic, whole-document-embedded CS docs
# can otherwise sit within noise-level distance of each other for a role
# name that doesn't genuinely belong to either (e.g. os.md vs ml.md for an
# "AIML Engineer" query).
DOC_TAGS = {
    "dbms": ["dbms", "database", "sql", "backend", "data-engineer"],
    "dsa": ["dsa", "data-structures", "algorithms", "coding", "software-engineer"],
    "hr": ["hr", "behavioral", "soft-skills", "general"],
    "interview": ["general", "interview-prep", "software-engineer"],
    "oop": ["oop", "software-engineer", "backend", "frontend"],
    "os": ["operating-systems", "systems", "backend", "infrastructure"],
    "ml": [
        "ai", "aiml", "ml", "machine-learning", "deep-learning",
        "artificial-intelligence", "data-science", "nlp",
    ],
}

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
        tags = DOC_TAGS.get(file.stem, [])

        collection.add(
            documents=[text],
            ids=[file.stem],
            metadatas=[{"topic": file.stem, "tags": ",".join(tags)}],
        )

    print("Documents indexed successfully!")


if __name__ == "__main__":
    ingest_documents()
