from pathlib import Path

from llm_wiki.config import load_config
from llm_wiki.commands.init import run_init_command
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
