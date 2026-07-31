import re

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


def _tag_matches(tag: str, query_tokens: set, query_compact: str) -> bool:
    tag_l = tag.lower()
    if tag_l in query_tokens:
        return True
    # Longer, hyphenated tags (e.g. "machine-learning") are specific enough
    # that a substring match is safe; short tags (e.g. "ai") are only
    # trusted as an exact token match above, since a loose substring check
    # on 2-3 letter tags would false-positive on unrelated query words.
    tag_compact = tag_l.replace("-", "").replace(" ", "")
    return len(tag_compact) >= 4 and tag_compact in query_compact


def _tag_relevant_topics(query: str) -> list:
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    query_compact = "".join(query_tokens)

    all_docs = collection.get(include=["metadatas"])
    relevant = []
    for topic, metadata in zip(all_docs["ids"], all_docs["metadatas"]):
        tags_str = (metadata or {}).get("tags", "")
        tags = [t for t in tags_str.split(",") if t]
        if any(_tag_matches(t, query_tokens, query_compact) for t in tags):
            relevant.append(topic)
    return relevant


def retrieve(query: str, k: int = 3):
    # Restrict the candidate pool to docs whose tags actually match the
    # query's role/topic first, so retrieval can't hand back a doc that's
    # merely closest-by-embedding among otherwise-irrelevant options.
    relevant_topics = _tag_relevant_topics(query)

    if relevant_topics:
        results = collection.query(
            query_texts=[query],
            n_results=min(k, len(relevant_topics)),
            where={"topic": {"$in": relevant_topics}},
        )
        docs = results["documents"][0]
        if docs:
            return docs

    # No doc's tags matched the query (or that query somehow returned
    # nothing) - fall back to pure embedding similarity across the corpus.
    results = collection.query(
        query_texts=[query],
        n_results=k,
    )

    return results["documents"][0]
