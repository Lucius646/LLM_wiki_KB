from pathlib import Path

from llm_wiki.config import load_config
from llm_wiki.commands.ingest import ingest_raw_file
from llm_wiki.commands.init import run_init_command
from llm_wiki.commands.query import answer_query
from llm_wiki.llm import build_openai_compatible_client
from llm_wiki.models import ParsedCommand, WorkspaceStatus
from llm_wiki.workspace import detect_workspace


def parse_command(line: str) -> ParsedCommand:
    head, _, tail = line.strip().partition(" ")
    if head == "query" and tail:
        return ParsedCommand(name=head, args=[tail])
    return ParsedCommand(name=head, args=tail.split() if tail else [])


class WikiRepl:
    def run(self) -> None:
        self._print_config_header()
        while True:
            command = parse_command(input("> "))
            if command.name in {"exit", "quit"}:
                return
            if command.name == "init":
                result = run_init_command()
                print(f"Initialized workspace: {len(result.created)} file(s) created")
                continue
            if command.name == "status":
                status = detect_workspace(Path.cwd())
                self._print_status(status)
                continue
            if command.name == "ingest":
                self._run_ingest(command.args)
                continue
            if command.name == "query":
                self._run_query(command.args)
                continue

    def _print_config_header(self) -> None:
        config = load_config()
        if config.provider and not config.errors:
            print(f"Config: ready | model: {config.provider.model}")
            return
        if config.provider:
            model = config.provider.model or "none"
            print(f"Config: invalid | model: {model}")
            return
        print("Config: unavailable | model: none")

    def _print_status(self, status: WorkspaceStatus) -> None:
        print(f"Workspace initialized: {'yes' if status.initialized else 'no'}")
        print(f"Raw files: {status.raw_file_count}")
        print(f"Wiki pages: {status.wiki_page_count}")

    def _run_ingest(self, args: list[str]) -> None:
        if not args:
            print("Usage: ingest raw/<topic>/<file>.md [--article <slug>]")
            return

        raw_path = Path.cwd() / args[0]
        article_override = self._parse_article_override(args[1:])
        config = load_config()
        if not config.provider or config.errors:
            print("Config is not ready for ingest.")
            return

        client = build_openai_compatible_client(config.provider)
        try:
            result = ingest_raw_file(
                Path.cwd(),
                raw_path,
                llm=client,
                article_override=article_override,
                confirm_new=self._confirm_new_article,
            )
        except NotImplementedError:
            print("LLM client implementation is not available yet.")
            return

        print(result.message)
        if result.article_path:
            print(result.article_path)

    def _run_query(self, args: list[str]) -> None:
        if not args:
            print("Usage: query <question>")
            return

        config = load_config()
        if not config.provider or config.errors:
            print("Config is not ready for query.")
            return

        client = build_openai_compatible_client(config.provider)
        try:
            result = answer_query(Path.cwd(), args[0], llm=client)
        except NotImplementedError:
            print("LLM client implementation is not available yet.")
            return

        print(result.answer)

    def _parse_article_override(self, args: list[str]) -> str | None:
        if len(args) >= 2 and args[0] == "--article":
            return args[1].strip() or None
        return None

    def _confirm_new_article(self, article_title: str) -> bool:
        answer = input(f"Create new article '{article_title}'? [y/N]: ").strip().lower()
        return answer in {"y", "yes"}
