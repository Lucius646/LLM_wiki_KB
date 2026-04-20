from dataclasses import dataclass


@dataclass
class ParsedCommand:
    name: str
    args: list[str]

