# Rule Efficiency Metrics

This document explains how adfilter measures "rule efficiency" — what
each number means, how it's calculated, and common pitfalls.

---

## TL;DR

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Efficiency Score** | `effective / raw_total` | % of input that became output |
| **Liveness Rate** | `effective / (effective + dead)` | % of probed domains that resolved |
| **Bloat Ratio** | `(invalid + repeat + dead) / raw_total` | % of input discarded |

---

## Field Definitions

Every source produces these counters during parsing (`parser.py`):

| Field | When it increments |
|-------|-------------------|
| `total` | Line was non-empty and not a comment |
| `invalid` | Handler could not parse the line, or the parsed rule was empty/filtered by length |
| `repeat` | Rule hash was already emitted by an **earlier** source (cross-source dedup) |
| `dead` | DNS probe returned NXDOMAIN (only when `parser.dns_probe.enable: true`) |
| `effective` | Rule survived all checks and entered the output pipeline |

**Identity:** `effective + invalid + repeat + dead = total` (modulo excluded domains).

---

## The `repeat` Counter — Why Is anti-AD So High?

### How Deduplication Works

```
┌─────────────────────────────────────────────────────────┐
│  Global hash set (shared across ALL sources)            │
│                                                         │
│  For each rule that passes parse + validation:          │
│    hash = murmur3(rule.target + rule.type + rule.mode)  │
│    if hash IN seen_hashes → repeat++, skip             │
│    else → seen_hashes.add(hash), effective++, emit     │
└─────────────────────────────────────────────────────────┘
```

Key points:

1. **It's cross-source, not internal.** If anti-AD has 75,905 "repeat",
   that means 75,905 of its rules were *already emitted* by a source
   that was processed before it. It does NOT mean anti-AD has 75k
   internal duplicates.

2. **Order-dependent.** The first source to emit `||example.com^` gets
   credit; the second source that also contains `||example.com^` gets
   a `repeat` increment. Changing source order in `application.yaml`
   changes which source "owns" each rule.

3. **Not a quality indictment.** A high repeat count for source B
   simply means source B overlaps heavily with sources processed
   earlier. For anti-AD specifically:
   - anti-AD is a large aggregated Chinese ad-blocking list (~100k rules)
   - It overlaps significantly with EasyList China, AdGuard DNS filter,
     and other Chinese-focused lists
   - If anti-AD were listed first in config, its repeat count would
     drop dramatically while other sources' counts would rise

4. **The hash is content-based.** Two rules are "the same" if they
   target the same domain with the same type and mode, regardless of
   original syntax differences (e.g. `||example.com^` in EasyList
   format vs `address=/example.com/` in dnsmasq format → same hash
   after parsing to the unified Rule model).

### Example

```yaml
# config/application.yaml
input:
  - name: adguard-dns     # processed first → claims shared rules
  - name: easylist-china  # processed second → some repeats
  - name: anti-ad         # processed third → most repeats (huge overlap)
```

If you move anti-ad to the top:
```yaml
input:
  - name: anti-ad         # now first → repeat ≈ 0
  - name: adguard-dns     # now second → repeat goes up
  - name: easylist-china  # third → repeat goes up
```

The total effective count stays the same — only the attribution shifts.

---

## Subdomain Collapse vs. `repeat`

These are two different mechanisms:

| Mechanism | Where | What it does |
|-----------|-------|-------------|
| `repeat` (dedup) | `parser.py` | Drops exact-hash duplicates across sources |
| Subdomain collapse | `optimizer.py` | Drops `sub.example.com` when `example.com` with OVERLAY flag is present |

### Does "covered by parent" make subdomains unnecessary?

**Yes, for DNS-level blocking.** If you have `||example.com^` (overlay),
it already blocks `sub.example.com`, `a.b.example.com`, etc. The
optimizer's `_collapse_subdomains` function removes these redundant
children *after* all sources are merged.

However, this only applies to rules marked with `Control.OVERLAY`
(which in EasyList/DNS syntax means `||domain^` without path qualifiers).
Path-based rules like `||example.com/ads^` are NOT collapsed because
they're more specific.

---

## When DNS Probe Is Disabled

When `parser.dns_probe.enable` is false (the default):

- `dead` is always 0
- `liveness_rate` returns 1.0 (no evidence of dead domains)
- The Efficiency Score reflects only parse success + dedup
- "Dead (NXDOMAIN)" shows as "not measured" in the CLI panel

Enable DNS probing for a more complete picture:
```yaml
parser:
  dns_probe:
    enable: true
    timeout_ms: 3000
    max_concurrency: 50
```

⚠️ DNS probing adds significant build time (minutes to hours depending
on rule count and network conditions).

---

## Reading the Release Notes

The GitHub Release "Rule Efficiency" table shows:

| Release Label | Build-report field | What it actually means |
|---------------|-------------------|----------------------|
| Efficiency Score | `effective / raw` | % of input → output |
| Raw Input | `eff + inv + rep + dead` | Total lines attempted |
| Effective | `effective` | Output rules |
| Invalid (parse) | `invalid` | Could not parse |
| Repeat (cross-src) | `repeat` | Hash collision with earlier source |
| Dead (NXDOMAIN) | `dead` | DNS probe failed (0 if probe off) |
| Liveness Rate | `eff / (eff + dead)` | DNS health ratio |
| Bloat Ratio | `(inv + rep + dead) / raw` | Waste ratio |
