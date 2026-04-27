from datetime import date
from pathlib import Path

from llm_wiki.git import commit_paths, get_git_status, is_git_repo
from llm_wiki.ledger import (
    LEDGER_RELATIVE_PATH,
    read_ledger,
    record_success,
    sha256_file,
    write_ledger,
)
from llm_wiki.models import IndexEntry, IngestResult, IngestPlan, PageChangePlan
from llm_wiki.raw_input import build_raw_input
from llm_wiki.wiki.article import parse_article_document
from llm_wiki.wiki.index import read_index_entries, upsert_index_entry
from llm_wiki.wiki.log import append_ingest_audit_entry


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

    raw_input = build_raw_input(root, raw_path)
    if not raw_input.ok:
        return IngestResult(ok=False, message=raw_input.message)

    if not is_git_repo(root):
        return IngestResult(ok=False, message="Workspace must be initialized with git before ingest.")

    status = get_git_status(root)
    if status.other_changes:
        return IngestResult(
            ok=False,
            message="Ingest blocked: uncommitted changes outside raw/ and wiki/.",
        )
    if status.raw_wiki_changes:
        commit_paths(
            root,
            [root / "raw", root / "wiki"],
            "checkpoint: save raw/wiki changes\n\nLLM-Wiki-Action: checkpoint",
        )

    index_path = root / "wiki" / "index.md"
    entries = read_index_entries(index_path)
    plan = _parse_ingest_plan(
        llm.plan_ingest(
            raw_input=raw_input,
            candidates=entries,
        )
    )

    today = date.today().isoformat()
    updated: list[str] = []
    created: list[str] = []
    article_paths: list[str] = []
    planned: list[str] = []

    for change in plan.changes:
        existing_entry = _find_existing_entry(entries, change.slug, change.title)
        if existing_entry is not None:
            article_path = root / "wiki" / Path(existing_entry.path)
            topic = existing_entry.topic
        else:
            article_path = root / "wiki" / change.topic / f"{change.slug}.md"
            topic = change.topic
        existing_article = article_path.read_text(encoding="utf-8") if article_path.is_file() else ""
        compiled = llm.compile_page_change(
            action=change.action,
            topic=topic,
            slug=change.slug,
            title=change.title,
            reason=change.reason,
            raw_input=raw_input,
            existing_article=existing_article,
        )
        if not compiled.strip():
            return IngestResult(ok=False, message=f"LLM returned empty content for {change.title}.")

        article_path.parent.mkdir(parents=True, exist_ok=True)
        existed_before = article_path.is_file()
        article_path.write_text(compiled.rstrip() + "\n", encoding="utf-8")

        document = parse_article_document(compiled)
        article_path_in_wiki = article_path.relative_to(root / "wiki").as_posix()
        article_path_rel = f"wiki/{article_path_in_wiki}"
        article_paths.append(article_path_rel)
        planned.append(f"{change.action}: {article_path_rel} - {change.reason}")
        if existed_before:
            updated.append(article_path_rel)
        else:
            created.append(article_path_rel)
        upsert_index_entry(
            index_path,
            topic=topic,
            article_title=document.title or change.title,
            article_path=article_path_in_wiki,
            summary=_extract_summary(document),
            updated=today,
        )

    commit_subject = llm.generate_commit_message(
        source=relative.as_posix(),
        summary=plan.summary,
        changed_paths=article_paths,
    )
    append_ingest_audit_entry(
        root / "wiki" / "log.md",
        date=today,
        source=relative.as_posix(),
        summary=plan.summary,
        planned=planned,
        updated=updated,
        created=created,
        warnings=plan.warnings,
        commit="see enclosing git commit",
    )
    ledger_path = root / LEDGER_RELATIVE_PATH
    ledger = read_ledger(ledger_path)
    record_success(
        ledger,
        relative_path=relative.as_posix(),
        sha256=sha256_file(raw_path),
        commit="see enclosing git commit",
        article_paths=article_paths,
    )
    write_ledger(ledger_path, ledger)
    commit_message = _build_ingest_commit_message(commit_subject, relative.as_posix())
    commit_paths(root, [root / "raw", root / "wiki"], commit_message)
    return IngestResult(
        ok=True,
        message="Ingest complete.",
        article_path=article_paths[0] if article_paths else "",
        article_paths=article_paths,
    )


def load_prompt_template(name: str) -> str:
    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    return (prompts_dir / name).read_text(encoding="utf-8")


def _find_existing_entry(entries: list[IndexEntry], slug: str, title: str) -> IndexEntry | None:
    target_filename = f"{slug}.md"
    for entry in entries:
        if Path(entry.path).name == target_filename:
            return entry
    for entry in entries:
        if entry.title.strip().lower() == title.strip().lower():
            return entry
    return None


def _extract_summary(document) -> str:
    for line in document.body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return "(no summary)"


def _parse_ingest_plan(raw_plan: dict[str, object]) -> IngestPlan:
    summary = str(raw_plan.get("summary", "")).strip()
    raw_changes = raw_plan.get("changes", [])
    raw_warnings = raw_plan.get("warnings", [])
    if not isinstance(raw_changes, list) or not 1 <= len(raw_changes) <= 3:
        raise RuntimeError("Ingest plan must contain 1-3 changes.")
    changes: list[PageChangePlan] = []
    for item in raw_changes:
        if not isinstance(item, dict):
            raise RuntimeError("Ingest plan changes must be objects.")
        action = str(item.get("action", "")).strip()
        topic = str(item.get("topic", "")).strip()
        slug = str(item.get("slug", "")).strip()
        title = str(item.get("title", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if action not in {"update", "create"} or not topic or not slug or not title:
            raise RuntimeError("Ingest plan contains an invalid page change.")
        changes.append(PageChangePlan(action=action, topic=topic, slug=slug, title=title, reason=reason))
    warnings = [str(item).strip() for item in raw_warnings] if isinstance(raw_warnings, list) else []
    return IngestPlan(summary=summary or "(no summary)", changes=changes, warnings=[item for item in warnings if item])


def _build_ingest_commit_message(subject: str, source: str) -> str:
    clean_subject = subject.strip().splitlines()[0] if subject.strip() else "ingest: compile raw source"
    return "\n\n".join(
        [
            clean_subject,
            f"LLM-Wiki-Action: ingest",
            f"LLM-Wiki-Source: {source}",
        ]
    )
