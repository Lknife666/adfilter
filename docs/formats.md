# Supported Formats

adfilter supports 10 output formats. All formats can be both parsed (input) and generated (output).

---

## EasyList / ABP (`easylist`)

**Extension:** `.txt`
**Compatibility:** Adblock Plus, uBlock Origin, AdGuard Browser Extension

```
! Comment
||ads.example.com^
@@||allow.example.com^
||tracker.example.org^$important
```

### Syntax Elements
- `||` — Match domain and subdomains (overlay)
- `^` — Separator qualifier
- `@@` — Exception (allow) rule
- `$important` — Override exceptions
- `$all` — Block all content types

---

## AdGuard Home DNS (`dns`)

**Extension:** `.txt`
**Compatibility:** AdGuard Home, AdGuard DNS

Superset of EasyList. Additionally supports hosts-format lines.

```
||ads.example.com^
0.0.0.0	blocked.example.com
@@||allow.example.com^
```

---

## dnsmasq (`dnsmasq`)

**Extension:** `.conf`
**Compatibility:** dnsmasq, OpenWrt, Pi-hole (partial)

```
address=/ads.example.com/0.0.0.0
address=/tracker.example.org/0.0.0.0
```

**Limitations:** Cannot express allow rules.

---

## smartdns (`smartdns`)

**Extension:** `.conf`
**Compatibility:** SmartDNS

```
address /ads.example.com/#
address /-exact.example.com/#
address /allow.example.com/-
```

- Leading `-` means exact match only (no subdomains)
- `#` = deny (NXDOMAIN)
- `-` = allow

---

## Clash (`clash`)

**Extension:** `.yaml`
**Compatibility:** Clash, Clash Meta, Stash

```yaml
payload:
  - "ads.example.com"
  - "+.tracker.example.org"
```

- `+.` prefix = match domain and all subdomains
- Quoted strings (single or double)

---

## Hosts (`hosts`)

**Extension:** `.txt`
**Compatibility:** All operating systems, Pi-hole, StevenBlack/hosts

```
0.0.0.0	ads.example.com
0.0.0.0	tracker.example.org
```

**Limitations:** Only exact domain match (no wildcards).

---

## Surge (`surge`)

**Extension:** `.conf`
**Compatibility:** Surge, Shadowrocket, Stash, Loon

```
.example.com
ads.example.com
```

- Leading `.` = match domain and subdomains
- No prefix = exact match only

---

## sing-box (`singbox`)

**Extension:** `.json`
**Compatibility:** sing-box rule-set (version 2)

```json
{"domain_suffix": ["example.com"]}
{"domain": ["exact.example.com"]}
```

Output is assembled into a complete JSON rule-set:
```json
{
  "version": 2,
  "rules": [
    {"domain_suffix": [...], "domain": [...]}
  ]
}
```

---

## MikroTik (`mikrotik`)

**Extension:** `.rsc`
**Compatibility:** MikroTik RouterOS v6/v7

```
/ip dns static
add name=ads.example.com type=A address=0.0.0.0 comment="adfilter"
```

**Limitations:** Only exact domain match (no wildcards in output).

---

## Unbound (`unbound`)

**Extension:** `.conf`
**Compatibility:** Unbound DNS resolver

```
server:
    local-zone: "ads.example.com." always_nxdomain
    local-zone: "tracker.example.org." always_nxdomain
```

Note: Domain names include trailing dot per DNS convention.
