"""playground command — interactive rule debugger."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from . import app

if TYPE_CHECKING:
    from ..trie import DomainTrie


@app.command(name="playground")
def cmd_playground(
    rule_dir: Annotated[
        Path, typer.Option("--rule-dir", "-d", help="Directory containing rule files")
    ] = Path("rule"),
) -> None:
    """Interactive rule debugger — query domains, simulate changes."""
    from ..trie import DomainTrie

    c = Console()

    if not rule_dir.exists():
        c.print(f"[red]Rule directory not found: {rule_dir}[/red]")
        raise typer.Exit(code=2)

    # Load rules into trie
    trie = DomainTrie()
    rule_origins: dict[str, str] = {}  # domain -> source file
    loaded = 0

    dns_file = rule_dir / "dns.txt"
    if dns_file.exists():
        for raw_line in dns_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("!", "#", "[")):
                continue
            # AdGuard DNS format: ||domain^
            domain = line.lstrip("|").rstrip("^").strip()
            if domain and "." in domain:
                trie.insert(domain)
                rule_origins[domain] = "dns.txt"
                loaded += 1

    # Also load hosts.txt if available
    hosts_file = rule_dir / "hosts.txt"
    if hosts_file.exists():
        for raw_line in hosts_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if (
                len(parts) >= 2
                and parts[0] in ("0.0.0.0", "127.0.0.1")
                and parts[1]
                and "." in parts[1]
                and parts[1] != "localhost"
                and not trie.contains(parts[1])
            ):
                trie.insert(parts[1])
                rule_origins[parts[1]] = "hosts.txt"
                loaded += 1

    c.print(
        Panel(
            f"[bold cyan]adfilter Playground[/bold cyan]\n"
            f"Loaded [green]{loaded}[/green] rules from [blue]{rule_dir}[/blue]\n"
            f"Trie size: {trie.size} domains\n\n"
            f"Commands: [bold]query[/bold] <domain> | [bold]whatif-add[/bold] <domain> | "
            f"[bold]whatif-remove[/bold] <domain> | [bold]stats[/bold] | [bold]quit[/bold]",
            title="🎮",
            border_style="cyan",
        )
    )

    # REPL loop
    while True:
        try:
            user_input = c.input("[bold cyan]> [/bold cyan]").strip()
        except EOFError, KeyboardInterrupt:
            c.print("\n[dim]Bye![/dim]")
            break

        if not user_input:
            continue

        parts = user_input.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            c.print("[dim]Bye![/dim]")
            break
        if cmd == "query":
            if not arg:
                c.print("[yellow]Usage: query <domain>[/yellow]")
                continue
            _handle_query(c, trie, rule_origins, arg.lower())
        elif cmd in ("whatif-add", "add"):
            if not arg:
                c.print("[yellow]Usage: whatif-add <domain>[/yellow]")
                continue
            _handle_whatif_add(c, trie, arg.lower())
        elif cmd in ("whatif-remove", "remove"):
            if not arg:
                c.print("[yellow]Usage: whatif-remove <domain>[/yellow]")
                continue
            _handle_whatif_remove(c, trie, rule_origins, arg.lower())
        elif cmd == "stats":
            c.print(f"  Total domains in trie: [bold]{trie.size}[/bold]")
            c.print(f"  Rule files loaded from: [blue]{rule_dir}[/blue]")
        elif cmd == "help":
            c.print("  [bold]query[/bold] <domain>         Check if domain is blocked")
            c.print("  [bold]whatif-add[/bold] <domain>    Simulate adding a rule")
            c.print("  [bold]whatif-remove[/bold] <domain> Simulate removing a rule")
            c.print("  [bold]stats[/bold]                  Show trie statistics")
            c.print("  [bold]quit[/bold]                   Exit playground")
        else:
            c.print(f"[yellow]Unknown command: {cmd}. Type 'help' for commands.[/yellow]")


def _handle_query(c: Console, trie: DomainTrie, origins: dict[str, str], domain: str) -> None:
    """Handle a query command."""
    if trie.contains(domain):
        source = origins.get(domain, "unknown")
        c.print("  [red]✅ BLOCKED[/red] (exact match)")
        c.print(f"     Domain: [bold]{domain}[/bold]")
        c.print(f"     Source: {source}")
    elif trie.matches(domain):
        parent = trie.find_parent(domain)
        source = origins.get(parent, "unknown") if parent else "unknown"
        c.print("  [red]✅ BLOCKED[/red] (suffix match)")
        c.print(f"     Domain: [bold]{domain}[/bold]")
        c.print(f"     Matched by parent: [bold]{parent}[/bold]")
        c.print(f"     Source: {source}")
    else:
        c.print("  [green]🟢 NOT BLOCKED[/green]")
        c.print(f"     Domain: [bold]{domain}[/bold]")


def _handle_whatif_add(c: Console, trie: DomainTrie, domain: str) -> None:
    """Simulate adding a rule."""
    if trie.matches(domain):
        parent = trie.find_parent(domain)
        c.print("  [yellow]⚠ Already covered[/yellow]")
        c.print(f"     {domain} is already blocked by: {parent}")
        c.print("     Adding this rule would be redundant.")
    else:
        c.print(f"  [green]✓ Would block:[/green] [bold]{domain}[/bold]")
        c.print(f"     Plus all subdomains: *.{domain}")


def _handle_whatif_remove(c: Console, trie: DomainTrie, origins: dict[str, str], domain: str) -> None:
    """Simulate removing a rule."""
    if trie.contains(domain):
        source = origins.get(domain, "unknown")
        c.print(f"  [yellow]✓ Would unblock:[/yellow] [bold]{domain}[/bold]")
        c.print(f"     Source: {source}")
        c.print("     All subdomains covered by this rule would also be unblocked.")
    elif trie.matches(domain):
        parent = trie.find_parent(domain)
        c.print(f"  [red]✗ Cannot remove[/red]: {domain} is not a direct rule.")
        c.print(f"     It's blocked by parent rule: {parent}")
        c.print(f"     Remove [bold]{parent}[/bold] instead, or add an allowlist entry.")
    else:
        c.print(f"  [dim]Domain {domain} is not in the rule set.[/dim]")
