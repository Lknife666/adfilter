# Contributing Guide

## Development Setup

### Prerequisites
- Python **3.14+**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Quick Start

```bash
# Clone
git clone https://github.com/Lknife666/adfilter.git
cd adfilter

# Install dependencies (including dev)
uv sync --group dev

# Run the project
uv run adfilter --help

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=adfilter --cov-report=term
```

---

## Project Structure

```
src/adfilter/
├── __init__.py          # Version
├── __main__.py          # CLI entry point (typer)
├── config.py            # Pydantic configuration models
├── constants.py         # Enums, symbols
├── model.py             # Rule data model
├── parser.py            # Fetch → parse → filter → dedupe pipeline
├── optimizer.py         # Post-parse optimizations
├── writer.py            # Output file writing + sing-box finalization
├── stats.py             # Build report model
├── logging_setup.py     # JSON/standard log configuration
├── dns_prober.py        # Optional DNS existence check
├── util.py              # String utilities
├── regex_patterns.py    # Compiled regex patterns
├── fetcher/             # Input fetchers (HTTP, local)
│   ├── base.py
│   ├── factory.py
│   ├── http.py
│   └── local.py
└── handler/             # Format handlers (parse + format)
    ├── base.py          # Abstract Handler + registry
    ├── easylist_handler.py
    ├── dns_handler.py
    ├── dnsmasq_handler.py
    ├── smartdns_handler.py
    ├── clash_handler.py
    ├── hosts_handler.py
    ├── surge_handler.py
    ├── singbox_handler.py
    ├── mikrotik_handler.py
    └── unbound_handler.py
```

---

## Code Style

- **Formatter/Linter:** [Ruff](https://docs.astral.sh/ruff/)
- **Line length:** 110
- **Target:** Python 3.14

Run linting:
```bash
uvx ruff check src/
uvx ruff format --check src/
```

---

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/unit/test_optimizer.py

# With coverage report
uv run pytest --cov=adfilter --cov-report=html
```

### Writing Tests

- Unit tests go in `tests/unit/`
- Handler tests go in `tests/unit/handler/`
- Integration tests go in `tests/integration/`
- Test fixtures go in `tests/fixtures/`

---

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Ensure all tests pass: `uv run pytest`
4. Ensure linting passes: `uvx ruff check src/`
5. Open a PR targeting `main`

### Commit Convention

```
feat: new feature
fix: bug fix
perf: performance improvement
docs: documentation
refactor: code refactoring
test: add/update tests
chore: build/CI changes
```

---

## Adding a New Output Format

1. Create `src/adfilter/handler/yourformat_handler.py`
2. Subclass `Handler` from `handler/base.py`
3. Implement `parse()`, `format()`, `is_comment()`, `commented()`
4. Register via `register_handler(RuleSet.YOURFORMAT, self)` in `__init__`
5. Add `RuleSet.YOURFORMAT` to `constants.py`
6. Import in `handler/__init__.py`
7. Add tests in `tests/unit/handler/test_yourformat.py`
8. Document in `docs/formats.md`
