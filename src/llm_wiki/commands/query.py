from pathlib import Path

from llm_wiki.models import QueryResult
from llm_wiki.wiki.article import load_article
from llm_wiki.wiki.search import search_index


def answer_query(root: Path, question: str, llm: object) -> QueryResult:
    candidates = search_index(root / "wiki" / "index.md", question)
    if not candidates:
        return QueryResult(ok=False, answer="No relevant wiki content found. Ingest more material first.")

    documents = [load_article(root / "wiki" / candidate.path) for candidate in candidates[:3]]
    answer = llm.answer_query(question=question, documents=documents)
    return QueryResult(ok=True, answer=answer)
