# adfilter

Ad-filter rule aggregator & converter — a Python port of
[Lknife-Ad-Filter](https://github.com/Lknife666/Lknife-Ad-Filter).

Fetch rule lists (local or HTTP), parse them across multiple formats, de-duplicate,
optionally DNS-probe each domain, and emit unified outputs in any combination of:

- **EasyList / ABP** (`||example.com^`, `@@allow`, `$important`)
- **AdGuard Home DNS** (EasyList + hosts + `dnsrewrite`)
- **dnsmasq** (`address=/example.com/0.0.0.0`)
- **smartdns** (`address /example.com/#`)
- **Clash** domain rule-provider (`- '+.example.com'`)
- **hosts** (`0.0.0.0 example.com`)

## Requirements

- Python **3.14+**

## Quick start

```bash
uv sync
uv run adfilter run --config config/application.yaml
```

Or without `uv`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
adfilter run --config config/application.yaml
```

## Configuration

See [`config/application-example.yaml`](config/application-example.yaml) for a
fully documented example. The top-level shape mirrors the original Java project
(`application.config.{input,output,fetcher,parser}`).

Placeholders supported inside `file_header`:
`${date}`, `${name}`, `${desc}`, `${type}`, `${total}`.

## CI / Auto-update

The included workflow [`auto-update.yml`](.github/workflows/auto-update.yml)
runs daily at 02:00 UTC, builds fresh rule lists, uploads them as an artifact,
and (on `main`) commits them back into `dist-rules/`.

## License

MIT — see [LICENSE](LICENSE).
