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


def test_main_prints_help_and_exits(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["llm-wiki", "--help"])

    main()

    captured = capsys.readouterr()
    assert "LLM Wiki REPL" in captured.out
    assert "ingest" in captured.out


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


def test_help_lists_core_commands():
    from llm_wiki.repl import HELP_TEXT

    assert "init" in HELP_TEXT
    assert "ingest raw/<file>" in HELP_TEXT
    assert "query" in HELP_TEXT
    assert "lint" in HELP_TEXT
    assert "undo" in HELP_TEXT


def test_help_lists_bare_ingest_auto_mode():
    from llm_wiki.repl import HELP_TEXT

    assert "- ingest" in HELP_TEXT
    assert "ingest raw/<file>" in HELP_TEXT
    assert "ingest --show-skipped" in HELP_TEXT


def test_repl_bare_ingest_runs_auto_ingest(monkeypatch, capsys):
    from llm_wiki.models import AutoIngestResult, ProviderConfig
    from llm_wiki.repl import WikiRepl

    called = []
    monkeypatch.setattr(
        "llm_wiki.repl.load_config",
        lambda: type("Config", (), {
            "provider": ProviderConfig(protocol="openai", model="gpt-5.5", api_key="sk-test"),
            "errors": [],
        })(),
    )
    monkeypatch.setattr("llm_wiki.repl.build_llm_client", lambda provider: object())
    monkeypatch.setattr(
        "llm_wiki.repl.ingest_pending_raw_files",
        lambda *args, **kwargs: called.append(kwargs) or AutoIngestResult(
            ok=True,
            message="auto result",
            ingested=[],
            skipped=[],
            failed=[],
        ),
    )

    WikiRepl()._run_ingest([])

    assert len(called) == 1
    assert called[0]["show_skipped"] is False
    assert "llm" in called[0]
    assert "confirm_new" in called[0]
    assert "auto result" in capsys.readouterr().out
