from pathlib import Path

from llm_wiki.models import InitResult
from llm_wiki.workspace import init_workspace


def run_init_command() -> InitResult:
    return init_workspace(Path.cwd())
