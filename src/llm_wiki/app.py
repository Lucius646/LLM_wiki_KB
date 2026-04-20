import sys

from llm_wiki.repl import HELP_TEXT, WikiRepl


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if any(arg in {"-h", "--help"} for arg in args):
        print(HELP_TEXT)
        return
    WikiRepl().run()


if __name__ == "__main__":
    main()
