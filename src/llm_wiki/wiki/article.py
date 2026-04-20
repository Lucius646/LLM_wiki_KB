from pathlib import Path

from llm_wiki.models import ArticleDocument


def parse_article_document(text: str) -> ArticleDocument:
    lines = text.splitlines()
    title = lines[0].removeprefix("# ").strip() if lines else ""
    sources_line = ""
    raw_line = ""
    body_start = 0
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("> Sources:"):
            sources_line = line.removeprefix("> Sources:").strip()
        elif line.startswith("> Raw:"):
            raw_line = line.removeprefix("> Raw:").strip()
        elif line.strip() == "":
            continue
        else:
            body_start = index
            break
    body = "\n".join(lines[body_start:]).strip()
    if body:
        body = f"{body}\n"
    return ArticleDocument(
        title=title,
        sources_line=sources_line,
        raw_line=raw_line,
        body=body,
    )


def save_article(path: Path, document: ArticleDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = document.body.strip("\n")
    content = "\n".join(
        [
            f"# {document.title}",
            "",
            f"> Sources: {document.sources_line}",
            f"> Raw: {document.raw_line}",
            "",
            body,
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def load_article(path: Path) -> ArticleDocument:
    return parse_article_document(path.read_text(encoding="utf-8"))
