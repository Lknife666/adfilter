# Configuration Reference

adfilter uses a YAML configuration file. The default location is `config/application.yaml`.

## Top-level Structure

```yaml
application:
  config:
    input: ...
    output: ...
    fetcher: ...
    parser: ...
    optimizer: ...
```

---

## Input

### `input.rule`

Groups of rule sources to fetch and parse.

```yaml
input:
  rule:
    default:
      - name: anti-ad
        type: easylist           # Format: easylist|dns|dnsmasq|smartdns|clash|hosts|surge|singbox|mikrotik|unbound
        path: https://example.com/list.txt   # HTTP URL or local file path
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier for this source |
| `type` | enum | yes | Input format (see supported formats) |
| `path` | string | yes | URL or local file path |

---

## Output

### `output.path`

Directory where generated rule files are written.

```yaml
output:
  path: ./rule
```

### `output.file_header`

Template string prepended to each output file. Supports placeholders:
- `${date}` — build timestamp
- `${name}` — output file name
- `${total}` — total rule count
- `${type}` — output format type
- `${desc}` — file description

### `output.files`

List of output files to generate.

```yaml
output:
  files:
    - name: dns.txt
      type: dns
      desc: "AdGuard Home DNS filter"
      filter: [basic, wildcard, unknown]   # optional: only include these rule types
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Output filename |
| `type` | enum | yes | Output format |
| `desc` | string | no | Description (used in header) |
| `filter` | list[enum] | no | Accepted rule types (empty = all) |

---

## Fetcher

### `fetcher.http`

HTTP fetch settings.

```yaml
fetcher:
  http:
    timeout_seconds: 60
    max_retries: 3
    max_concurrency: 8
    cache_dir: .cache/http
    on_failure: cache_then_skip   # fail_fast | cache_then_skip | skip_always
    max_cache_age_hours: 72
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timeout_seconds` | int | 30 | HTTP request timeout |
| `max_retries` | int | 3 | Retry count before fallback |
| `max_concurrency` | int | 8 | Max parallel HTTP fetches |
| `cache_dir` | string | null | On-disk cache directory (null disables) |
| `on_failure` | string | cache_then_skip | Fallback strategy after retries exhausted |
| `max_cache_age_hours` | int | 72 | Max age of stale cache before it's rejected |

#### Fallback Strategies

- **`fail_fast`** — Raise an error immediately, abort the build.
- **`cache_then_skip`** — Try stale cache; if too old or absent, skip the source.
- **`skip_always`** — Always skip failed sources (never use stale cache).

---

## Parser

```yaml
parser:
  min_length: 4
  max_length: 1024
  alert_length: 6
  incremental_build: false
  progress: false
  json_logs: false
  dns_probe:
    enable: false
    timeout_seconds: 5.0
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min_length` | int | 0 | Minimum rule line length (0 = no limit) |
| `max_length` | int | 0 | Maximum rule line length (0 = no limit) |
| `alert_length` | int | 0 | Warn on rules shorter than this |
| `incremental_build` | bool | false | Skip rebuild when input fingerprint unchanged |
| `progress` | bool | false | Show Rich progress bar |
| `json_logs` | bool | false | Emit structured JSON logs |

---

## Optimizer

```yaml
optimizer:
  enable: true
  collapse_subdomains: true
  drop_allow_shadowed_deny: true
  min_source_votes: 1
  normalize_idn: true
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable` | bool | false | Enable the optimizer pass |
| `collapse_subdomains` | bool | false | Drop child rules when parent has overlay |
| `drop_allow_shadowed_deny` | bool | false | Remove deny rules shadowed by allows |
| `min_source_votes` | int | 1 | Minimum sources a rule must appear in (1 = disabled) |
| `normalize_idn` | bool | true | Normalize unicode domains to ASCII punycode |
