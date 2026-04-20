from llm_wiki.app import main
from llm_wiki.repl import parse_command


def test_parse_query_command_preserves_rest_of_line():
    command = parse_command("query transformer attention solves what problem")
    assert command.name == "query"
    assert command.args == ["transformer attention solves what problem"]


def test_parse_exit_command():
    command = parse_command("exit")
    assert command.name == "exit"


def test_main_constructs_wiki_repl_and_runs_it(monkeypatch):
    called = []

    class DummyRepl:
        def run(self):
            called.append(True)

    monkeypatch.setattr("llm_wiki.app.WikiRepl", DummyRepl)

    main()

    assert called == [True]


def test_repl_run_exits_on_exit_command(monkeypatch):
    inputs = iter(["query transformer attention", "exit"])
    parsed = []

    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(
        "llm_wiki.repl.parse_command",
        lambda line: parsed.append(line) or parse_command(line),
    )

    from llm_wiki.repl import WikiRepl

    WikiRepl().run()

    assert parsed == ["query transformer attention", "exit"]
