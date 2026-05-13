# Architecture

## Data Flow

```
                    ┌──────────────┐
                    │  Config YAML │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
           ┌───────┤    Parser     ├───────┐
           │       └──────────────-┘       │
           │                               │
    ┌──────▼──────┐                 ┌──────▼──────┐
    │ HTTP Fetcher│                 │Local Fetcher │
    └──────┬──────┘                 └──────┬──────┘
           │                               │
           └───────────┬───────────────────┘
                       │ (async line stream)
                ┌──────▼──────┐
                │   Handler   │  ← format-specific parse()
                │  (per-type) │
                └──────┬──────┘
                       │ Rule objects
                ┌──────▼──────┐
                │  Optimizer  │  ← subdomain collapse, voting, IDN, allow-shadow
                └──────┬──────┘
                       │ optimized Rules
                ┌──────▼──────┐
                │   Writer    │  ← calls handler.format() per output type
                └──────┬──────┘
                       │
              ┌────────┼────────┬────────┬─── ...
              ▼        ▼        ▼        ▼
          dns.txt  clash.yaml surge.conf singbox.json
```

## Key Design Decisions

### 1. Handler Registry Pattern

Each format implements the `Handler` abstract class and self-registers
via `register_handler()` in its `__init__`. This allows format-agnostic
pipeline code:

```python
handler = get_handler(RuleSet.CLASH)
rule = handler.parse(line)
output = handler.format(rule)
```

### 2. Streaming Pipeline

The parser yields `Rule` objects as an `AsyncIterator`. This keeps memory
usage constant regardless of source file size. Only the optimizer
accumulates rules (by design — it needs the full set for subdomain collapse).

### 3. Unified Rule Model

All formats parse into the same `Rule` dataclass. This allows:
- Cross-format conversion (any input → any output)
- Format-agnostic deduplication (murmur3 hash)
- Universal optimizer (operates on Rule, not text)

### 4. Async-First

HTTP fetching uses `aiohttp` with bounded concurrency (`asyncio.Semaphore`).
Multiple sources are fetched in parallel via `asyncio.TaskGroup`.

### 5. Configuration via Pydantic

All config is validated at load time with clear error messages.
Supports both YAML file and environment variables (`ADFILTER_*`).

## Module Dependencies

```
__main__.py (CLI)
    ├── config.py (Pydantic models)
    ├── parser.py (pipeline orchestrator)
    │   ├── fetcher/ (HTTP + local)
    │   ├── handler/ (format parse)
    │   └── dns_prober.py
    ├── optimizer.py (post-parse)
    ├── writer.py (output + finalize)
    └── stats.py (build report)
```
