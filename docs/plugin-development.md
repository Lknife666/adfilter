# Plugin Development Guide

This guide explains how to create third-party plugins for adfilter, including custom format handlers and notification channels.

## Overview

adfilter uses Python's `entry_points` mechanism for plugin discovery. Plugins are installed as separate packages and automatically detected at runtime.

## Custom Format Handler

### Step 1: Create a Handler Class

```python
# my_adfilter_plugin/handler.py
from adfilter.handler.base import Handler, register_handler
from adfilter.constants import RuleSet
from adfilter.model import Rule, Mode, Scope, RuleType, Control

class MyFormatHandler(Handler):
    """Handler for my custom format."""
    
    rule_set = RuleSet.MY_FORMAT  # Add to constants.py or use existing

    def __init__(self):
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        """Parse a line from my format into a Rule object."""
        line = line.strip()
        if not line or self.is_comment(line):
            return Rule.empty()
        
        # Your parsing logic here
        return Rule(
            origin=line,
            target=line,  # extracted domain
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )

    def format(self, rule: Rule) -> str | None:
        """Format a Rule object into my format's syntax."""
        if rule.is_empty() or not rule.target:
            return None
        # Your formatting logic here
        return f"BLOCK {rule.target}"

    def is_comment(self, line: str) -> bool:
        return line.startswith("#")

    def commented(self, value: str) -> str:
        return f"# {value}"
```

### Step 2: Register via entry_points

In your package's `pyproject.toml`:

```toml
[project.entry-points."adfilter.handlers"]
my_format = "my_adfilter_plugin.handler:MyFormatHandler"
```

### Step 3: Install and Use

```bash
pip install my-adfilter-plugin
# The handler is now automatically available
adfilter convert input.txt output.myformat --to my_format
```

## Custom Notifier

### Step 1: Create a Notifier Class

```python
# my_adfilter_plugin/notifier.py
from adfilter.notifier.base import Notifier, NotifyPayload, register_notifier

class SlackNotifier(Notifier):
    """Send notifications to Slack."""

    def __init__(self, webhook_url: str):
        self._url = webhook_url

    async def send(self, payload: NotifyPayload) -> bool:
        """Send the notification. Return True on success."""
        import aiohttp
        
        message = {
            "text": f"adfilter: {payload.title}\n{payload.message}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self._url, json=message) as resp:
                return resp.status == 200

# Register the notifier
register_notifier("slack", SlackNotifier)
```

### Step 2: Register via entry_points

```toml
[project.entry-points."adfilter.notifiers"]
slack = "my_adfilter_plugin.notifier:SlackNotifier"
```

### Step 3: Configure

```yaml
notifier:
  enable: true
  channels:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
```

## Testing Your Plugin

```python
import pytest
from my_adfilter_plugin.handler import MyFormatHandler
from adfilter.model import Rule, Mode, Scope, RuleType

def test_parse():
    handler = MyFormatHandler()
    rule = handler.parse("BLOCK example.com")
    assert rule.target == "example.com"
    assert rule.mode == Mode.DENY

def test_format():
    handler = MyFormatHandler()
    rule = Rule(target="example.com", mode=Mode.DENY, scope=Scope.DOMAIN, type=RuleType.BASIC)
    result = handler.format(rule)
    assert result == "BLOCK example.com"

def test_roundtrip():
    handler = MyFormatHandler()
    original = "BLOCK ads.example.com"
    rule = handler.parse(original)
    formatted = handler.format(rule)
    assert formatted == original
```

## Best Practices

1. **Idempotent parse/format**: `format(parse(line))` should produce the same rule semantics
2. **Handle edge cases**: empty lines, comments, malformed input
3. **Return `Rule.empty()`** for unparseable lines (don't raise exceptions)
4. **Preserve metadata**: set `source_type`, `source_name` when possible
5. **Test thoroughly**: include unit tests for both parse and format directions
6. **Document the format**: explain the syntax in your README

## Plugin Discovery

At runtime, adfilter discovers plugins via:

```python
from importlib.metadata import entry_points

# Discover handler plugins
for ep in entry_points(group="adfilter.handlers"):
    handler_class = ep.load()
    handler_class()  # __init__ calls register_handler()

# Discover notifier plugins
for ep in entry_points(group="adfilter.notifiers"):
    notifier_module = ep.load()
```

This happens automatically during CLI initialization.
