"""Interactive TUI for SkillEval with slash-command menu."""

from __future__ import annotations

import shlex
from typing import Any

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML

from skilleval.display import console
from skilleval.i18n import get_locale, save_preference, set_locale, t


# ── Slash command handlers ──────────────────────────────────────────────


def _prompt_value(session: PromptSession, key: str, default: str = "") -> str:
    """Prompt the user for a value with a translated label."""
    label = t(f"tui.prompts.{key}")
    suffix = f" [{default}]" if default else ""
    try:
        value = session.prompt(f"  {label}{suffix}: ")
    except (EOFError, KeyboardInterrupt):
        return default
    return value.strip() or default


def _handle_run(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for parameters and invoke `skilleval run`."""
    task_path = _prompt_value(session, "task_path")
    if not task_path:
        return
    models = _prompt_value(session, "models")
    trials = _prompt_value(session, "trials")

    args = ["run", task_path]
    if models:
        args.extend(["--models", models])
    if trials:
        args.extend(["--trials", trials])

    _invoke_cli(ctx, args)


def _handle_matrix(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for parameters and invoke `skilleval matrix`."""
    task_path = _prompt_value(session, "task_path")
    if not task_path:
        return
    creators = _prompt_value(session, "creators")
    if not creators:
        return
    executors = _prompt_value(session, "executors")
    if not executors:
        return
    trials = _prompt_value(session, "trials")

    args = ["matrix", task_path, "--creators", creators, "--executors", executors]
    if trials:
        args.extend(["--trials", trials])

    _invoke_cli(ctx, args)


def _handle_chain(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for parameters and invoke `skilleval chain`."""
    task_path = _prompt_value(session, "task_path")
    if not task_path:
        return
    meta_skills = _prompt_value(session, "meta_skills")
    if not meta_skills:
        return
    creators = _prompt_value(session, "creators")
    if not creators:
        return
    executors = _prompt_value(session, "executors")
    if not executors:
        return
    trials = _prompt_value(session, "trials")

    args = [
        "chain",
        task_path,
        "--meta-skills",
        meta_skills,
        "--creators",
        creators,
        "--executors",
        executors,
        "--yes",
    ]
    if trials:
        args.extend(["--trials", trials])

    _invoke_cli(ctx, args)


def _handle_catalog(ctx: click.Context, session: PromptSession) -> None:
    """Invoke `skilleval catalog` with no extra prompting."""
    _invoke_cli(ctx, ["catalog"])


def _handle_init(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for task name and invoke `skilleval init`."""
    name = _prompt_value(session, "task_name")
    if not name:
        return
    _invoke_cli(ctx, ["init", name])


def _handle_report(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for results path and invoke `skilleval report`."""
    path = _prompt_value(session, "results_path")
    if not path:
        return
    _invoke_cli(ctx, ["report", path])


def _handle_history(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for task path and invoke `skilleval history`."""
    path = _prompt_value(session, "task_path")
    if not path:
        return
    _invoke_cli(ctx, ["history", path])


def _handle_lint(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for skill path and invoke `skilleval lint`."""
    path = _prompt_value(session, "skill_path")
    if not path:
        return
    _invoke_cli(ctx, ["lint", path])


def _handle_compare(ctx: click.Context, session: PromptSession) -> None:
    """Prompt for two run paths and invoke `skilleval compare`."""
    old_run = _prompt_value(session, "old_run")
    if not old_run:
        return
    new_run = _prompt_value(session, "new_run")
    if not new_run:
        return
    _invoke_cli(ctx, ["compare", old_run, new_run])


def _handle_language(ctx: click.Context, session: PromptSession) -> None:
    """Toggle language between English and Chinese and persist."""
    current = get_locale()
    console.print(f"  {t('tui.language.current', lang=current)}")

    new_locale = "zh" if current == "en" else "en"
    set_locale(new_locale)
    save_preference()
    console.print(f"  {t('tui.language.switched', lang=new_locale)}")


def _handle_help(ctx: click.Context, session: PromptSession) -> None:
    """Display available slash commands."""
    console.print()
    for name, meta in SLASH_COMMANDS.items():
        desc = t(meta["desc_key"])
        console.print(f"  [bold cyan]/{name:<12}[/bold cyan] {desc}")
    console.print()


def _handle_quit(ctx: click.Context, session: PromptSession) -> None:
    """Signal the main loop to exit."""
    raise _QuitSignal()


class _QuitSignal(Exception):
    """Raised by /quit to break the main loop."""


# ── Command registry ────────────────────────────────────────────────────

SLASH_COMMANDS: dict[str, dict[str, Any]] = {
    "run": {"handler": _handle_run, "desc_key": "tui.commands.run"},
    "matrix": {"handler": _handle_matrix, "desc_key": "tui.commands.matrix"},
    "chain": {"handler": _handle_chain, "desc_key": "tui.commands.chain"},
    "catalog": {"handler": _handle_catalog, "desc_key": "tui.commands.catalog"},
    "init": {"handler": _handle_init, "desc_key": "tui.commands.init"},
    "report": {"handler": _handle_report, "desc_key": "tui.commands.report"},
    "history": {"handler": _handle_history, "desc_key": "tui.commands.history"},
    "lint": {"handler": _handle_lint, "desc_key": "tui.commands.lint"},
    "compare": {"handler": _handle_compare, "desc_key": "tui.commands.compare"},
    "language": {"handler": _handle_language, "desc_key": "tui.commands.language"},
    "help": {"handler": _handle_help, "desc_key": "tui.commands.help"},
    "quit": {"handler": _handle_quit, "desc_key": "tui.commands.quit"},
}


# ── Completer ───────────────────────────────────────────────────────────


class SlashCompleter(Completer):
    """Tab-complete slash commands with translated descriptions."""

    def get_completions(self, document: Document, complete_event: Any):
        text = document.text_before_cursor.strip()
        if not text.startswith("/"):
            return

        prefix = text[1:]
        for name, meta in SLASH_COMMANDS.items():
            if name.startswith(prefix):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=t(meta["desc_key"]),
                )


# ── CLI invocation helper ───────────────────────────────────────────────


def _invoke_cli(ctx: click.Context, args: list[str]) -> None:
    """Invoke a CLI subcommand from within the TUI, catching errors gracefully."""
    from skilleval.cli import cli as cli_group

    try:
        cli_group(args, standalone_mode=False, parent=ctx)
    except click.ClickException as e:
        console.print(f"[red]{e.format_message()}[/red]")
    except SystemExit:
        pass
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{t('display.messages.interrupted')}[/yellow]")
    except Exception as e:
        console.print(f"[red]{type(e).__name__}: {e}[/red]")


# ── Main loop ───────────────────────────────────────────────────────────


def interactive_session(ctx: click.Context) -> None:
    """Run the interactive TUI with slash-command completion."""
    console.print(f"\n[bold]{t('tui.welcome')}[/bold]")
    console.print(f"[dim]{t('tui.type_help')}[/dim]\n")

    session: PromptSession = PromptSession(
        completer=SlashCompleter(),
        complete_while_typing=True,
    )

    while True:
        try:
            text = session.prompt(
                HTML(f"<b>{t('tui.prompt')}</b>"),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n{t('tui.goodbye')}")
            break

        if not text:
            continue

        if text.startswith("/"):
            parts = text[1:].split(None, 1)
            cmd_name = parts[0] if parts else ""
            meta = SLASH_COMMANDS.get(cmd_name)

            if meta is None:
                console.print(f"[yellow]{t('tui.unknown_command', command=cmd_name)}[/yellow]")
                continue

            try:
                meta["handler"](ctx, session)
            except _QuitSignal:
                console.print(t("tui.goodbye"))
                break
        else:
            # Treat bare text as a potential subcommand
            try:
                args = shlex.split(text)
            except ValueError:
                args = text.split()
            if args:
                _invoke_cli(ctx, args)
