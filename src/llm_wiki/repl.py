from pathlib import Path

from llm_wiki.config import load_config
from llm_wiki.commands.ingest import ingest_raw_file
from llm_wiki.commands.init import run_init_command
from llm_wiki.commands.lint import lint_workspace
from llm_wiki.commands.query import answer_query
from llm_wiki.commands.undo import undo_last_ingest
from llm_wiki.llm import build_openai_compatible_client
from llm_wiki.models import ParsedCommand, WorkspaceStatus
from llm_wiki.workspace import detect_workspace

HELP_TEXT = """LLM Wiki REPL

Commands:
- init
- status
- ingest raw/<topic>/<file>.md [--article <slug>]
- query <question>
- lint
- undo
- help
- exit
"""


def parse_command(line: str) -> ParsedCommand:
    head, _, tail = line.strip().partition(" ")
    if head == "query" and tail:
        return ParsedCommand(name=head, args=[tail])
    return ParsedCommand(name=head, args=tail.split() if tail else [])


class WikiRepl:
    def run(self) -> None:
        self._print_header()
        while True:
            command = parse_command(input("> "))
            if command.name in {"exit", "quit"}:
                return
            if command.name in {"help", "?"}:
                print(HELP_TEXT)
                continue
            if command.name == "init":
                try:
                    result = run_init_command()
                except RuntimeError as exc:
                    print(str(exc))
                    continue
                print(f"Initialized workspace: {len(result.created)} file(s) created")
                print(f"Git initialized: {'yes' if result.git_initialized else 'no'}")
                print(f"Baseline committed: {'yes' if result.baseline_committed else 'no'}")
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
            if command.name == "lint":
                self._run_lint()
                continue
            if command.name == "undo":
                self._run_undo()
                continue
            if command.name:
                print(f"Unknown command: {command.name}")
                print(HELP_TEXT)

    def _print_header(self) -> None:
        status = detect_workspace(Path.cwd())
        print("LLM Wiki REPL")
        print(f"Workspace: {Path.cwd()}")
        print(f"Status: {'initialized' if status.initialized else 'not initialized'}")
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
        except RuntimeError as exc:
            print(str(exc))
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
        except RuntimeError as exc:
            print(str(exc))
            return

        print(result.answer)

    def _parse_article_override(self, args: list[str]) -> str | None:
        if len(args) >= 2 and args[0] == "--article":
            return args[1].strip() or None
        return None

    def _confirm_new_article(self, article_title: str) -> bool:
        answer = input(f"Create new article '{article_title}'? [y/N]: ").strip().lower()
        return answer in {"y", "yes"}

    def _run_lint(self) -> None:
        result = lint_workspace(Path.cwd())
        if result.ok:
            print("Lint passed: 0 issues found")
            return
        print(f"Lint found {len(result.issues)} issue(s):")
        for issue in result.issues:
            print(f"- {issue}")

    def _run_undo(self) -> None:
        result = undo_last_ingest(Path.cwd())
        print(result.message)
