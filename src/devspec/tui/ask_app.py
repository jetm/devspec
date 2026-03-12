"""Rich-based TUI for presenting structured questions to the user."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import readchar
import yaml
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

_CACHE_DIR = Path.home() / ".cache" / "claude-ask"

console = Console()


def _render_question(
    q: dict,
    selected_idx: int,
    show_research: bool,
    show_reflection: bool,
    q_num: int,
    q_total: int,
) -> Panel:
    qtype = q.get("type", "options")
    title = f"[bold]Q{q.get('id', q_num)}: {q.get('text', '')}[/bold]"
    position = f"[dim]{q_num}/{q_total}[/dim]"

    body = Text()

    context = q.get("context", "")
    if context:
        body.append(context + "\n\n", style="dim")

    if qtype == "options":
        options: dict = q.get("options", {})
        recommendation = q.get("recommendation")
        option_keys = list(options.keys()) + ["_custom"]
        for i, key in enumerate(option_keys):
            bullet = "●" if i == selected_idx else "○"
            if key == "_custom":
                label = "custom answer..."
            else:
                label = f"[{key}] {options[key]}"
                if key == recommendation:
                    label += " [green](recommended)[/green]"
            body.append(f"  {bullet} {label}\n")

    elif qtype == "confirm":
        choices = ["yes", "no"]
        for i, choice in enumerate(choices):
            bullet = "●" if i == selected_idx else "○"
            body.append(f"  {bullet} {choice}\n")

    elif qtype == "freetext":
        hint = q.get("hint", "Type your answer and press Enter")
        body.append(f"  {hint}\n", style="dim")

    if show_reflection:
        reflection = q.get("reflection", "")
        if reflection:
            body.append("\n[bold yellow]Reflection:[/bold yellow]\n", style="")
            body.append(reflection + "\n", style="yellow")

    if show_research and qtype == "options":
        research: dict = q.get("research", {})
        option_keys_list = list(q.get("options", {}).keys())
        if option_keys_list and selected_idx < len(option_keys_list):
            current_key = option_keys_list[selected_idx]
            research_text = research.get(current_key, "")
            if research_text:
                body.append(f"\n[bold cyan]Research ({current_key}):[/bold cyan]\n", style="")
                body.append(research_text + "\n", style="cyan")

    keybinds = "[dim]</> navigate  ↑↓ select  Enter confirm  R research  T reflect  Esc cancel[/dim]"
    body.append("\n" + keybinds)

    return Panel(body, title=title, title_align="left", subtitle=position, subtitle_align="right")


def _get_option_count(q: dict) -> int:
    qtype = q.get("type", "options")
    if qtype == "options":
        return len(q.get("options", {})) + 1  # +1 for custom
    elif qtype == "confirm":
        return 2
    return 0


def _prompt_freetext(prompt: str) -> str:
    console.print(f"\n[bold]{prompt}[/bold] ", end="")
    return input()


def run_ask_app(session_id: str) -> None:
    session_dir = _CACHE_DIR / "sessions" / session_id
    questions_path = session_dir / "questions.json"

    if not questions_path.exists():
        console.print(f"[red]Session not found: {session_id}[/red]")
        sys.exit(1)

    questions: list[dict] = json.loads(questions_path.read_text())
    if not questions:
        console.print("[red]No questions in session.[/red]")
        sys.exit(1)

    q_total = len(questions)
    current_q = 0
    selected_idx = 0
    show_research = False
    show_reflection = False
    answers: list[dict] = []

    # Initialize answers list
    for q in questions:
        answers.append(
            {
                "id": q.get("id"),
                "text": q.get("text"),
                "answer": None,
                "skipped": False,
                "note": None,
            }
        )

    with Live(console=console, auto_refresh=False, screen=True) as live:

        def redraw():
            q = questions[current_q]
            panel = _render_question(q, selected_idx, show_research, show_reflection, current_q + 1, q_total)
            live.update(panel)
            live.refresh()

        redraw()

        while True:
            key = readchar.readkey()
            q = questions[current_q]
            qtype = q.get("type", "options")

            if key == readchar.key.ESC:
                # Cancel without saving
                live.stop()
                console.print("[yellow]Cancelled.[/yellow]")
                sys.exit(0)

            elif key == "r" or key == "R":
                show_research = not show_research
                redraw()

            elif key == "t" or key == "T":
                show_reflection = not show_reflection
                redraw()

            elif key in (readchar.key.LEFT, "<"):
                if current_q > 0:
                    current_q -= 1
                    selected_idx = 0
                    show_research = False
                    show_reflection = False
                    redraw()

            elif key in (readchar.key.RIGHT, ">"):
                if current_q < q_total - 1:
                    current_q += 1
                    selected_idx = 0
                    show_research = False
                    show_reflection = False
                    redraw()

            elif key in (readchar.key.UP, "k"):
                if qtype in ("options", "confirm"):
                    count = _get_option_count(q)
                    if selected_idx > 0:
                        selected_idx -= 1
                        redraw()

            elif key in (readchar.key.DOWN, "j"):
                if qtype in ("options", "confirm"):
                    count = _get_option_count(q)
                    if selected_idx < count - 1:
                        selected_idx += 1
                        redraw()

            elif key == readchar.key.ENTER:
                if qtype == "freetext":
                    live.stop()
                    hint = q.get("hint", "Enter your answer")
                    answer_text = _prompt_freetext(hint)
                    answers[current_q]["answer"] = answer_text
                    if current_q < q_total - 1:
                        current_q += 1
                        selected_idx = 0
                        show_research = False
                        show_reflection = False
                        live.start()
                        redraw()
                    else:
                        break

                elif qtype == "confirm":
                    choices = ["yes", "no"]
                    answers[current_q]["answer"] = choices[selected_idx]
                    if current_q < q_total - 1:
                        current_q += 1
                        selected_idx = 0
                        show_research = False
                        show_reflection = False
                        redraw()
                    else:
                        break

                elif qtype == "options":
                    option_keys = list(q.get("options", {}).keys())
                    if selected_idx == len(option_keys):
                        # Custom answer
                        live.stop()
                        answer_text = _prompt_freetext("Custom answer")
                        answers[current_q]["answer"] = answer_text
                        if current_q < q_total - 1:
                            current_q += 1
                            selected_idx = 0
                            show_research = False
                            show_reflection = False
                            live.start()
                            redraw()
                        else:
                            break
                    else:
                        answers[current_q]["answer"] = option_keys[selected_idx]
                        if current_q < q_total - 1:
                            current_q += 1
                            selected_idx = 0
                            show_research = False
                            show_reflection = False
                            redraw()
                        else:
                            break

    # Write answers YAML
    round_path = session_dir / "round-1.yaml"
    data = {"questions": answers}
    round_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
    console.print("[green]Answers saved.[/green]")
