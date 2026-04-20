from datetime import date
from pathlib import Path

from llm_wiki.models import IndexEntry, IngestResult
from llm_wiki.wiki.article import parse_article_document
from llm_wiki.wiki.index import read_index_entries, upsert_index_entry
from llm_wiki.wiki.log import append_log_entry


def ingest_raw_file(
    root: Path,
    raw_path: Path,
    llm: object,
    article_override: str | None,
    confirm_new,
) -> IngestResult:
    try:
        relative = raw_path.relative_to(root)
    except ValueError:
        return IngestResult(ok=False, message="Raw file must be inside the active workspace.")

    if not relative.parts or relative.parts[0] != "raw" or raw_path.suffix.lower() != ".md":
        return IngestResult(ok=False, message="Unsupported raw file type: only .md is supported in v1.")
    if not raw_path.is_file():
        return IngestResult(ok=False, message=f"Raw file not found: {relative.as_posix()}")

    raw_text = raw_path.read_text(encoding="utf-8")
    index_path = root / "wiki" / "index.md"
    entries = read_index_entries(index_path)
    topic = _determine_topic(relative)

    if article_override:
        slug = article_override.strip()
        title = _slug_to_title(slug)
        existing_entry = _find_existing_entry(entries, slug, title)
        is_new = existing_entry is None
    else:
        inference = llm.infer_article(raw_text, entries)
        slug = str(inference.get("article_slug", "")).strip()
        title = str(inference.get("article_title", "")).strip()
        if not slug:
            return IngestResult(ok=False, message="Unable to infer a target article. Try --article.")
        if not title:
            title = _slug_to_title(slug)
        existing_entry = _find_existing_entry(entries, slug, title)
        is_new = bool(inference.get("is_new", False)) and existing_entry is None

    if is_new and not article_override and not confirm_new(title):
        return IngestResult(ok=False, message=f"Ingest cancelled before creating {title}.")

    if existing_entry is not None:
        article_path = root / "wiki" / Path(existing_entry.path)
        article_path_rel = f"wiki/{existing_entry.path.replace('\\', '/')}"
        topic = existing_entry.topic
    else:
        article_path = root / "wiki" / topic / f"{slug}.md"
        article_path_rel = f"wiki/{topic}/{slug}.md"

    existing_article = article_path.read_text(encoding="utf-8") if article_path.is_file() else ""
    compile_prompt = load_prompt_template("compile_article.md")
    compiled = llm.compile_article(
        prompt=compile_prompt,
        raw_text=raw_text,
        raw_path=relative.as_posix(),
        topic=topic,
        article_slug=slug,
        article_title=title,
        existing_article=existing_article,
    )
    if not compiled.strip():
        return IngestResult(ok=False, message="LLM returned empty article content.")

    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(compiled.rstrip() + "\n", encoding="utf-8")

    document = parse_article_document(compiled)
    summary = _extract_summary(document)
    today = date.today().isoformat()
    upsert_index_entry(
        index_path,
        topic=topic,
        article_title=document.title or title,
        article_path=article_path.relative_to(root / "wiki").as_posix(),
        summary=summary,
        updated=today,
    )
    append_log_entry(root / "wiki" / "log.md", today, "ingest", document.title or title)
    return IngestResult(ok=True, message="Ingest complete.", article_path=article_path_rel)


def load_prompt_template(name: str) -> str:
    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    return (prompts_dir / name).read_text(encoding="utf-8")


def _determine_topic(relative_raw_path: Path) -> str:
    if len(relative_raw_path.parts) >= 3:
        return relative_raw_path.parts[1]
    return "general"


def _find_existing_entry(entries: list[IndexEntry], slug: str, title: str) -> IndexEntry | None:
    target_filename = f"{slug}.md"
    for entry in entries:
        if Path(entry.path).name == target_filename:
            return entry
    for entry in entries:
        if entry.title.strip().lower() == title.strip().lower():
            return entry
    return None


def _slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").strip().title()


def _extract_summary(document) -> str:
    for line in document.body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return "(no summary)"
