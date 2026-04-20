from llm_wiki.models import ParsedCommand


def parse_command(line: str) -> ParsedCommand:
    head, _, tail = line.strip().partition(" ")
    if head == "query" and tail:
        return ParsedCommand(name=head, args=[tail])
    return ParsedCommand(name=head, args=tail.split() if tail else [])


class WikiRepl:
    def run(self) -> None:
        return None

