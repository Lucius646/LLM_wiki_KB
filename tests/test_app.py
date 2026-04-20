from llm_wiki.repl import parse_command


def test_parse_query_command_preserves_rest_of_line():
    command = parse_command("query transformer attention solves what problem")
    assert command.name == "query"
    assert command.args == ["transformer attention solves what problem"]


def test_parse_exit_command():
    command = parse_command("exit")
    assert command.name == "exit"
