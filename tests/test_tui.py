"""Tests for the interactive TUI mode."""

from __future__ import annotations

import os
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prompt_toolkit.document import Document

from skilleval.i18n import reset
from skilleval.tui import (
    SLASH_COMMANDS,
    SlashCompleter,
    _QuitSignal,
    _handle_catalog,
    _handle_chain,
    _handle_compare,
    _handle_help,
    _handle_history,
    _handle_init,
    _handle_language,
    _handle_lint,
    _handle_matrix,
    _handle_quit,
    _handle_report,
    _handle_run,
    _invoke_cli,
    _prompt_value,
    interactive_session,
)


@pytest.fixture(autouse=True)
def _reset_i18n():
    """Reset i18n state before each test."""
    reset()
    yield
    reset()


@pytest.fixture
def _english_locale():
    """Force English locale for deterministic tests."""
    with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}):
        yield


def _mock_session(*responses: str) -> MagicMock:
    """Create a mock PromptSession that returns canned responses."""
    session = MagicMock()
    session.prompt.side_effect = list(responses)
    return session


class TestSlashCompleter:
    """Test the slash-command tab completer."""

    def test_completes_slash_prefix(self, _english_locale):
        completer = SlashCompleter()
        doc = Document("/r")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "run" in names
        assert "report" in names

    def test_no_completions_without_slash(self, _english_locale):
        completer = SlashCompleter()
        doc = Document("run")
        completions = list(completer.get_completions(doc, None))
        assert completions == []

    def test_empty_slash_returns_all(self, _english_locale):
        completer = SlashCompleter()
        doc = Document("/")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == len(SLASH_COMMANDS)

    def test_exact_match(self, _english_locale):
        completer = SlashCompleter()
        doc = Document("/quit")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "quit" in names

    def test_completions_have_descriptions(self, _english_locale):
        completer = SlashCompleter()
        doc = Document("/h")
        completions = list(completer.get_completions(doc, None))
        for comp in completions:
            assert comp.display_meta is not None

    def test_no_match_yields_nothing(self, _english_locale):
        completer = SlashCompleter()
        doc = Document("/zzz_nonexistent")
        completions = list(completer.get_completions(doc, None))
        assert completions == []

    def test_completion_start_position(self, _english_locale):
        completer = SlashCompleter()
        doc = Document("/ca")
        completions = list(completer.get_completions(doc, None))
        # "catalog" and "chain" and "compare" start with "c", "catalog" starts with "ca"
        for comp in completions:
            assert comp.start_position == -2  # len("ca")

    def test_chinese_descriptions(self):
        """Completions should show Chinese descriptions when locale is zh."""
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "zh"}):
            completer = SlashCompleter()
            doc = Document("/quit")
            completions = list(completer.get_completions(doc, None))
            assert len(completions) == 1
            # Chinese description for quit
            assert completions[0].display_meta is not None


class TestSlashCommands:
    """Test command registry and basic handlers."""

    def test_all_commands_have_handlers(self):
        for name, meta in SLASH_COMMANDS.items():
            assert "handler" in meta, f"/{name} missing handler"
            assert callable(meta["handler"]), f"/{name} handler not callable"

    def test_all_commands_have_desc_key(self):
        for name, meta in SLASH_COMMANDS.items():
            assert "desc_key" in meta, f"/{name} missing desc_key"
            assert meta["desc_key"].startswith("tui.commands."), f"/{name} bad desc_key"

    def test_quit_raises_signal(self):
        with pytest.raises(_QuitSignal):
            _handle_quit(None, None)

    def test_expected_commands_exist(self):
        expected = {
            "run",
            "matrix",
            "chain",
            "catalog",
            "init",
            "report",
            "history",
            "lint",
            "compare",
            "language",
            "help",
            "quit",
        }
        assert set(SLASH_COMMANDS.keys()) == expected

    def test_all_desc_keys_resolve_to_strings(self, _english_locale):
        """Every desc_key should resolve to a non-empty translated string."""
        from skilleval.i18n import t

        for name, meta in SLASH_COMMANDS.items():
            result = t(meta["desc_key"])
            assert isinstance(result, str), f"/{name} desc_key didn't resolve"
            assert len(result) > 0, f"/{name} desc_key resolved to empty"
            # Should not be the raw key (meaning it was found in YAML)
            assert result != meta["desc_key"], f"/{name} desc_key not in YAML"


class TestLanguageHandler:
    """Test the /language toggle handler."""

    def test_language_toggle(self, _english_locale):
        from skilleval.i18n import get_locale, t

        assert get_locale() == "en"
        assert t("display.tables.model") == "Model"

        with mock.patch("skilleval.tui.save_preference"):
            _handle_language(None, None)

        assert get_locale() == "zh"
        assert t("display.tables.model") == "模型"

        with mock.patch("skilleval.tui.save_preference"):
            _handle_language(None, None)

        assert get_locale() == "en"
        assert t("display.tables.model") == "Model"


class TestHelpHandler:
    """Test /help output."""

    def test_help_prints_all_commands(self, _english_locale):
        # Should not raise — verifies no KeyError or missing i18n keys
        _handle_help(None, None)


class TestCatalogHandler:
    """Test /catalog handler invokes CLI."""

    def test_catalog_calls_invoke(self, _english_locale):
        mock_ctx = MagicMock()
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_catalog(mock_ctx, None)
            mock_invoke.assert_called_once_with(mock_ctx, ["catalog"])


class TestRunHandler:
    """Test /run handler parameter prompting."""

    def test_run_with_all_params(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./my-task", "qwen-turbo", "5")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_run(mock_ctx, session)
            args = mock_invoke.call_args[0][1]
            assert args[0] == "run"
            assert "./my-task" in args
            assert "--models" in args
            assert "qwen-turbo" in args
            assert "--trials" in args
            assert "5" in args

    def test_run_with_defaults(self, _english_locale):
        """Pressing Enter for models and trials should omit those flags."""
        mock_ctx = MagicMock()
        session = _mock_session("./my-task", "", "")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_run(mock_ctx, session)
            args = mock_invoke.call_args[0][1]
            assert args == ["run", "./my-task"]

    def test_run_empty_task_path_aborts(self, _english_locale):
        """Empty task path should abort without calling invoke."""
        mock_ctx = MagicMock()
        session = _mock_session("")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_run(mock_ctx, session)
            mock_invoke.assert_not_called()


class TestMatrixHandler:
    """Test /matrix handler parameter prompting."""

    def test_matrix_with_all_params(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./task", "qwen-max", "glm-5", "3")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_matrix(mock_ctx, session)
            args = mock_invoke.call_args[0][1]
            assert "matrix" in args
            assert "--creators" in args
            assert "--executors" in args

    def test_matrix_empty_creators_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./task", "")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_matrix(mock_ctx, session)
            mock_invoke.assert_not_called()

    def test_matrix_empty_executors_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./task", "qwen-max", "")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_matrix(mock_ctx, session)
            mock_invoke.assert_not_called()


class TestChainHandler:
    """Test /chain handler parameter prompting."""

    def test_chain_with_all_params(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./task", "default", "qwen-max", "glm-5", "3")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_chain(mock_ctx, session)
            args = mock_invoke.call_args[0][1]
            assert "chain" in args
            assert "--meta-skills" in args
            assert "--yes" in args

    def test_chain_empty_meta_skills_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./task", "")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_chain(mock_ctx, session)
            mock_invoke.assert_not_called()


class TestInitHandler:
    """Test /init handler."""

    def test_init_calls_invoke(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("my-new-task")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_init(mock_ctx, session)
            mock_invoke.assert_called_once_with(mock_ctx, ["init", "my-new-task"])

    def test_init_empty_name_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_init(mock_ctx, session)
            mock_invoke.assert_not_called()


class TestReportHandler:
    """Test /report handler."""

    def test_report_calls_invoke(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./results")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_report(mock_ctx, session)
            mock_invoke.assert_called_once_with(mock_ctx, ["report", "./results"])

    def test_report_empty_path_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_report(mock_ctx, session)
            mock_invoke.assert_not_called()


class TestHistoryHandler:
    """Test /history handler."""

    def test_history_calls_invoke(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./my-task")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_history(mock_ctx, session)
            mock_invoke.assert_called_once_with(mock_ctx, ["history", "./my-task"])


class TestLintHandler:
    """Test /lint handler."""

    def test_lint_calls_invoke(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./skill.md")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_lint(mock_ctx, session)
            mock_invoke.assert_called_once_with(mock_ctx, ["lint", "./skill.md"])

    def test_lint_empty_path_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_lint(mock_ctx, session)
            mock_invoke.assert_not_called()


class TestCompareHandler:
    """Test /compare handler."""

    def test_compare_calls_invoke(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./old-run", "./new-run")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_compare(mock_ctx, session)
            mock_invoke.assert_called_once_with(mock_ctx, ["compare", "./old-run", "./new-run"])

    def test_compare_empty_old_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_compare(mock_ctx, session)
            mock_invoke.assert_not_called()

    def test_compare_empty_new_aborts(self, _english_locale):
        mock_ctx = MagicMock()
        session = _mock_session("./old-run", "")
        with mock.patch("skilleval.tui._invoke_cli") as mock_invoke:
            _handle_compare(mock_ctx, session)
            mock_invoke.assert_not_called()


class TestInvokeCli:
    """Test the _invoke_cli helper."""

    def test_click_exception_handled(self, _english_locale):
        """ClickException should be caught and printed, not raised."""
        import click

        mock_ctx = MagicMock()
        with mock.patch("skilleval.cli.cli") as mock_cli:
            mock_cli.side_effect = click.ClickException("test error")
            # Should not raise
            _invoke_cli(mock_ctx, ["catalog"])

    def test_system_exit_handled(self, _english_locale):
        """SystemExit should be caught silently."""
        mock_ctx = MagicMock()
        with mock.patch("skilleval.cli.cli") as mock_cli:
            mock_cli.side_effect = SystemExit(0)
            _invoke_cli(mock_ctx, ["catalog"])

    def test_keyboard_interrupt_handled(self, _english_locale):
        """KeyboardInterrupt should be caught and print interrupted message."""
        mock_ctx = MagicMock()
        with mock.patch("skilleval.cli.cli") as mock_cli:
            mock_cli.side_effect = KeyboardInterrupt()
            _invoke_cli(mock_ctx, ["run", "./task"])

    def test_generic_exception_handled(self, _english_locale):
        """Any other exception should be caught and printed."""
        mock_ctx = MagicMock()
        with mock.patch("skilleval.cli.cli") as mock_cli:
            mock_cli.side_effect = RuntimeError("something went wrong")
            _invoke_cli(mock_ctx, ["run", "./task"])


class TestPromptValueEdgeCases:
    """Test _prompt_value edge cases."""

    def test_eof_returns_default(self, _english_locale):
        session = MagicMock()
        session.prompt.side_effect = EOFError()
        result = _prompt_value(session, "task_path", default="fallback")
        assert result == "fallback"

    def test_keyboard_interrupt_returns_default(self, _english_locale):
        session = MagicMock()
        session.prompt.side_effect = KeyboardInterrupt()
        result = _prompt_value(session, "task_path", default="fallback")
        assert result == "fallback"

    def test_whitespace_only_returns_default(self, _english_locale):
        session = _mock_session("   ")
        result = _prompt_value(session, "task_path", default="fallback")
        assert result == "fallback"


class TestInteractiveSession:
    """Integration tests for the interactive session loop."""

    def test_quit_exits_cleanly(self, _english_locale):
        mock_ctx = MagicMock()
        mock_ctx.obj = {"verbosity": 0}

        with mock.patch("skilleval.tui.PromptSession") as MockSession:
            instance = MockSession.return_value
            instance.prompt.side_effect = ["/quit"]
            interactive_session(mock_ctx)

    def test_eof_exits_cleanly(self, _english_locale):
        mock_ctx = MagicMock()
        mock_ctx.obj = {"verbosity": 0}

        with mock.patch("skilleval.tui.PromptSession") as MockSession:
            instance = MockSession.return_value
            instance.prompt.side_effect = EOFError()
            interactive_session(mock_ctx)

    def test_keyboard_interrupt_exits_cleanly(self, _english_locale):
        mock_ctx = MagicMock()
        mock_ctx.obj = {"verbosity": 0}

        with mock.patch("skilleval.tui.PromptSession") as MockSession:
            instance = MockSession.return_value
            instance.prompt.side_effect = KeyboardInterrupt()
            interactive_session(mock_ctx)

    def test_unknown_command_shows_error(self, _english_locale):
        mock_ctx = MagicMock()
        mock_ctx.obj = {"verbosity": 0}

        with mock.patch("skilleval.tui.PromptSession") as MockSession:
            instance = MockSession.return_value
            instance.prompt.side_effect = ["/nonexistent", "/quit"]
            interactive_session(mock_ctx)

    def test_bare_text_invokes_cli(self, _english_locale):
        mock_ctx = MagicMock()
        mock_ctx.obj = {"verbosity": 0}

        with (
            mock.patch("skilleval.tui.PromptSession") as MockSession,
            mock.patch("skilleval.tui._invoke_cli") as mock_invoke,
        ):
            instance = MockSession.return_value
            instance.prompt.side_effect = ["catalog", "/quit"]
            interactive_session(mock_ctx)
            mock_invoke.assert_called_once_with(mock_ctx, ["catalog"])

    def test_empty_input_is_ignored(self, _english_locale):
        """Pressing Enter with no text should loop back, not crash."""
        mock_ctx = MagicMock()
        mock_ctx.obj = {"verbosity": 0}

        with mock.patch("skilleval.tui.PromptSession") as MockSession:
            instance = MockSession.return_value
            instance.prompt.side_effect = ["", "  ", "/quit"]
            interactive_session(mock_ctx)

    def test_slash_catalog_dispatches(self, _english_locale):
        """/catalog should invoke the catalog handler."""
        mock_ctx = MagicMock()
        mock_ctx.obj = {"verbosity": 0}

        with (
            mock.patch("skilleval.tui.PromptSession") as MockSession,
            mock.patch("skilleval.tui._invoke_cli") as mock_invoke,
        ):
            instance = MockSession.return_value
            instance.prompt.side_effect = ["/catalog", "/quit"]
            interactive_session(mock_ctx)
            mock_invoke.assert_called_once_with(mock_ctx, ["catalog"])
