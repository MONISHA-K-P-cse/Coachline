import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(
    name="coachline_docs",
    embedding_function=embedding_function,
)


def retrieve(query: str, k: int = 3):
    results = collection.query(
        query_texts=[query],
        n_results=k,
    )

    return results["documents"][0]