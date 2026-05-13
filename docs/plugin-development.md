# Plugin Development Guide

adfilter supports third-party plugins for **output format handlers** and **notification channels** via Python's `entry_points` mechanism.

---

## Handler Plugins

A handler plugin adds a new output format (e.g., pfBlockerNG, Bind RPZ, or a custom corporate format).

### Step 1: Create Your Package

```
my-adfilter-plugin/
├── pyproject.toml
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       └── handler.py
└── tests/
    └── test_handler.py
```

### Step 2: Implement the Handler

```python
# src/my_plugin/handler.py
from adfilter.handler.base import Handler, register_handler
from adfilter.constants import RuleSet
from adfilter.model import Control, Mode, Rule, RuleType, Scope


class MyFormatHandler(Handler):
    """Handler for my custom format."""

    rule_set = RuleSet.DNS  # Use closest existing RuleSet or register a new one

    def __init__(self) -> None:
        # Self-registration on instantiation
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        """Parse a line from your format into a Rule object.

        Return Rule.empty() for lines that cannot be parsed (comments, blanks, etc.)
        """
        stripped = line.strip()
        if not stripped:
            return Rule.empty()

        # Your parsing logic here
        return Rule(
            origin=line,
            target=stripped,
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )

    def format(self, rule: Rule) -> str | None:
        """Convert a Rule to your output format string.

        Return None to skip rules that cannot be represented in your format.
        """
        if rule.type is RuleType.UNKNOWN:
            return None
        if rule.scope is not Scope.DOMAIN:
            return None
        if rule.mode is not Mode.DENY:
            return None

        # Your formatting logic here
        return f"block {rule.target}"

    def head_format(self) -> str | None:
        """Optional: return a header line for the output file."""
        return "# My Custom Format"

    def is_comment(self, line: str) -> bool:
        """Return True if the line is a comment in your format."""
        return line.startswith("#")

    def commented(self, value: str) -> str:
        """Wrap a text block as comments in your format."""
        return "\n".join(f"# {line}" for line in value.splitlines() if line.strip())
```

### Step 3: Register via Entry Points

```toml
# pyproject.toml
[project]
name = "my-adfilter-plugin"
version = "0.1.0"
dependencies = ["adfilter>=0.4.0"]

[project.entry-points."adfilter.handlers"]
my_format = "my_plugin.handler:MyFormatHandler"
```

### Step 4: Install and Use

```bash
pip install my-adfilter-plugin

# The handler is now available in adfilter
adfilter run --config config/application.yaml
```

In your config, reference the format:

```yaml
output:
  files:
    - name: custom.txt
      type: my_format  # matches the entry_point name
      desc: "My Custom Format"
```

---

## Notifier Plugins

A notifier plugin adds a new notification channel (e.g., Slack, PagerDuty, email).

### Implementation

```python
# src/my_plugin/notifier.py
from adfilter.notifier.base import Notifier, NotifyPayload, register_notifier


class SlackNotifier(Notifier):
    """Send build notifications to Slack."""

    def __init__(self, webhook_url: str, channel: str = "") -> None:
        self._url = webhook_url
        self._channel = channel

    async def send(self, payload: NotifyPayload) -> bool:
        """Send the notification. Return True on success."""
        import aiohttp

        message = self._format_message(payload)
        body = {"text": message}
        if self._channel:
            body["channel"] = self._channel

        async with aiohttp.ClientSession() as session:
            async with session.post(self._url, json=body) as resp:
                return resp.status == 200

    def _format_message(self, payload: NotifyPayload) -> str:
        icon = "✅" if payload.success else "❌"
        return (
            f"{icon} adfilter build {'succeeded' if payload.success else 'failed'}\n"
            f"Rules: {payload.total_rules:,} | Duration: {payload.elapsed_ms}ms"
        )


# Register the notifier type
register_notifier("slack", SlackNotifier)
```

### Entry Point Registration

```toml
[project.entry-points."adfilter.notifiers"]
slack = "my_plugin.notifier:SlackNotifier"
```

### Configuration

```yaml
notifier:
  enable: true
  channels:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#alerts"
```

---

## The Rule Model

All handlers operate on the unified `Rule` dataclass:

```python
@dataclass(slots=True)
class Rule:
    origin: str = ""              # Original line text
    target: str = ""              # Extracted domain/pattern
    dest: str | None = None       # Destination IP (for rewrite/hosts)
    source_type: RuleSet | None   # Which format this was parsed from
    source_name: str = ""         # Name of the input source
    source_group: str = ""        # Group tag for categorized output
    mode: Mode | None = None      # DENY / ALLOW / REWRITE
    scope: Scope | None = None    # DOMAIN / IP / URL
    type: RuleType | None = None  # BASIC / WILDCARD / REGEX / UNKNOWN
    controls: set[Control]        # OVERLAY / QUALIFIER / IMPORTANT / ALL
```

### Key Rules for Handler Authors

1. **Return `Rule.empty()` for unparseable lines** — never raise exceptions from `parse()`
2. **Return `None` from `format()` for unsupported rules** — the writer skips them
3. **Preserve `origin` field** — used for verbatim pass-through of same-source UNKNOWN rules
4. **Set `source_type`** — enables same-source detection for UNKNOWN rule pass-through
5. **Use `Control.OVERLAY`** — marks rules that match subdomains (like `||` in EasyList)

---

## Testing Your Plugin

```python
# tests/test_handler.py
import pytest
from adfilter.model import Mode, Rule, RuleType, Scope
from my_plugin.handler import MyFormatHandler


@pytest.fixture
def handler():
    return MyFormatHandler()


class TestParse:
    def test_basic_rule(self, handler):
        rule = handler.parse("block example.com")
        assert rule.target == "example.com"
        assert rule.mode == Mode.DENY

    def test_empty_line(self, handler):
        assert handler.parse("").is_empty()

    def test_comment(self, handler):
        assert handler.is_comment("# comment")


class TestFormat:
    def test_basic_deny(self, handler):
        rule = Rule(target="example.com", mode=Mode.DENY, scope=Scope.DOMAIN, type=RuleType.BASIC)
        assert handler.format(rule) == "block example.com"

    def test_allow_skipped(self, handler):
        rule = Rule(target="example.com", mode=Mode.ALLOW, scope=Scope.DOMAIN, type=RuleType.BASIC)
        assert handler.format(rule) is None
```

---

## API Stability

Starting from **v1.0**, the following are covered by SemVer guarantees:

- `Handler` abstract class interface (`parse`, `format`, `is_comment`, `commented`, `head_format`)
- `Rule` dataclass fields and methods
- `Mode`, `Scope`, `RuleType`, `Control` enums
- `register_handler()` and `get_handler()` functions
- `Notifier` abstract class and `register_notifier()`
- `NotifyPayload` dataclass

Breaking changes to these interfaces will only occur in major version bumps.
