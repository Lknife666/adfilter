# adfilter

Ad-filter rule aggregator & converter — a Python port of
[Lknife-Ad-Filter](https://github.com/Lknife666/Lknife-Ad-Filter)
with **20 features the upstream Java project does not have**.

Fetch rule lists (local or HTTP), parse them across many formats,
de-duplicate, optimise, optionally DNS-probe each domain, and emit any
combination of:

| Format | In upstream? | Output extension |
| --- | --- | --- |
| **EasyList / ABP** | ✅ | `easylist.txt` |
| **AdGuard Home DNS** | ✅ | `dns.txt` |
| **dnsmasq** | ✅ | `dnsmasq.conf` |
| **smartdns** | ✅ | `smartdns.conf` |
| **Clash** rule-provider | ✅ | `clash.yaml` |
| **hosts** | ✅ | `hosts.txt` |
| **Surge** domain-set | ❌ NEW | `surge.conf` |
| **sing-box** rule-set | ❌ NEW | `singbox.json` |
| **MikroTik** RouterOS script | ❌ NEW | `mikrotik.rsc` |
| **Unbound** local-zone | ❌ NEW | `unbound.conf` |

## 20 things this port adds

### New output formats (1–4)
1. **Surge `domain-set`** — for Surge / Shadowrocket / Stash.
2. **sing-box** native JSON rule-set (`version: 2`), ready for `sing-box rule-set compile`.
3. **MikroTik RouterOS** `/ip dns static` script.
4. **Unbound** `local-zone … always_nxdomain` fragments.

### New CLI commands (5–9)
5. `adfilter convert a.txt b.yaml --from hosts --to clash` — one-shot conversion, no config.
6. `adfilter diff old.txt new.txt --format dns` — by rule identity, not by text.
7. `adfilter stats build-report.json` — pretty-print a build report.
8. `adfilter doctor` — env + config health check with per-dependency status.
9. `adfilter serve --dir rule/` — tiny local HTTP server to expose generated files to your LAN.

### Ergonomics (10–12)
10. `adfilter formats` — list every supported format in a rich table.
11. `adfilter completion bash|zsh|fish|powershell` — print a shell-completion script.
12. **Bounded concurrency** for HTTP fetches (`fetcher.http.max_concurrency`).

### Performance & freshness (13–15)
13. **Conditional-GET cache** with on-disk ETag / Last-Modified (`fetcher.http.cache_dir`). Skips re-downloading unchanged sources.
14. **Incremental build** — skip the entire pipeline when the input fingerprint matches the last run (`--incremental`).
15. **Docker image** auto-published to GHCR on every push to `main`.

### Output quality (16–19)
16. **Subdomain collapse** — drop `||foo.bar.com^` when `||bar.com^` (overlay) already matches it.
17. **Allow-shadow elimination** — drop DENY rules shadowed by an equivalent `@@allow`.
18. **Multi-source voting** — only keep rules appearing in ≥ N distinct sources (`optimizer.min_source_votes`).
19. **IDN / punycode normalisation** — `测试.com` and `xn--0zwm56d.com` treated as the same rule.

### Observability (20)
20. **JSON build report** (`--report rule/build-report.json`) + **JSON structured logs** (`--json-logs`) + **Rich progress bar** (`--progress`).

## Requirements

Python **3.14+**. See [`pyproject.toml`](pyproject.toml) for dependencies.

## Quick start

```bash
uv sync
uv run adfilter run --config config/application.yaml --progress --report rule/build-report.json
uv run adfilter stats rule/build-report.json
uv run adfilter serve --dir rule/
```

Without `uv`:

```bash
pip install -e .
adfilter run -c config/application.yaml
```

## Configuration

See [`config/application-example.yaml`](config/application-example.yaml) for a
fully documented example. The top-level shape mirrors the original Java project
(`application.config.{input,output,fetcher,parser}`) plus a new `optimizer:` block.

Placeholders in `file_header`: `${date}` · `${name}` · `${desc}` · `${type}` · `${total}`.

## CI / Auto-update

Workflow: [`auto-update.yml`](.github/workflows/auto-update.yml)

- Runs every **8 hours** and on every `main` push
- Publishes all 10 output files to an orphan **`release`** branch (clean, no source leak)
- Also uploads a debugging artifact and a Docker image (`ghcr.io/Lknife666/adfilter:latest`)

### Subscribe URLs

Replace `main` with `release` in any raw URL:

```
https://raw.githubusercontent.com/Lknife666/adfilter/release/dns.txt
https://raw.githubusercontent.com/Lknife666/adfilter/release/clash.yaml
https://raw.githubusercontent.com/Lknife666/adfilter/release/singbox.json
```

## License

MIT — see [LICENSE](LICENSE).
