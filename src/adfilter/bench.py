"""Rule-set benchmarking — compare against known-good baseline lists.

Approach (Plan B): load your generated rules into a DomainTrie, then
compare against two types of baseline lists:

1. **Known-ad lists** (ground truth positives): domains that *should*
   be blocked. Measures detection/coverage rate.
2. **Known-legit lists** (ground truth negatives): domains that should
   *not* be blocked. Measures over-blocking / false-positive rate.

Metrics produced:

* True Positive Rate (TPR / Detection)  = blocked ∩ known-ad / known-ad
* False Negative Rate (Miss)            = 1 − TPR
* False Positive Rate (Over-block)      = blocked ∩ known-legit / known-legit
* Precision                             = blocked ∩ known-ad / all-blocked-in-baselines
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import aiohttp

from .trie import DomainTrie

log = logging.getLogger(__name__)

# ── Built-in baseline sources ────────────────────────────────────────

# Known-ad domain lists (ground truth: should be blocked)
BUILTIN_AD_BASELINES: dict[str, str] = {
    "disconnect-ad": "https://s3.amazonaws.com/lists.disconnect.me/simple_ad.txt",
    "disconnect-tracking": "https://s3.amazonaws.com/lists.disconnect.me/simple_tracking.txt",
    "steven-black-hosts": "https://raw.githubusercontent.com/StevenBlack/hosts/master/data/StevenBlack/hosts",
}

# Known-legit domain lists (ground truth: should NOT be blocked)
BUILTIN_LEGIT_BASELINES: dict[str, str] = {
    "tranco-10k": "https://tranco-list.eu/download/JQN54/10000",
    "anudeep-whitelist": "https://raw.githubusercontent.com/anudeepND/whitelist/master/domains/whitelist.txt",
}


@dataclass
class BenchResult:
    """Results from a single baseline comparison."""

    baseline_name: str
    baseline_type: str  # "ad" or "legit"
    baseline_size: int = 0
    matched: int = 0
    unmatched: int = 0
    # Samples for inspection
    sample_matched: list[str] = field(default_factory=list)
    sample_unmatched: list[str] = field(default_factory=list)

    @property
    def rate(self) -> float:
        """Match rate: matched / baseline_size."""
        return self.matched / self.baseline_size if self.baseline_size else 0.0


@dataclass
class BenchReport:
    """Aggregated bench results."""

    rule_count: int = 0
    elapsed_ms: int = 0
    results: list[BenchResult] = field(default_factory=list)

    @property
    def detection_rate(self) -> float:
        """Average TPR across all ad baselines."""
        ad_results = [r for r in self.results if r.baseline_type == "ad"]
        if not ad_results:
            return 0.0
        return sum(r.rate for r in ad_results) / len(ad_results)

    @property
    def false_positive_rate(self) -> float:
        """Average FPR across all legit baselines."""
        legit_results = [r for r in self.results if r.baseline_type == "legit"]
        if not legit_results:
            return 0.0
        return sum(r.rate for r in legit_results) / len(legit_results)

    def to_dict(self) -> dict:
        return {
            "rule_count": self.rule_count,
            "elapsed_ms": self.elapsed_ms,
            "detection_rate": round(self.detection_rate, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "baselines": [
                {
                    "name": r.baseline_name,
                    "type": r.baseline_type,
                    "size": r.baseline_size,
                    "matched": r.matched,
                    "rate": round(r.rate, 4),
                    "sample_matched": r.sample_matched[:10],
                    "sample_unmatched": r.sample_unmatched[:10],
                }
                for r in self.results
            ],
        }


# ── Core logic ────────────────────────────────────────────────────────


def load_rules_into_trie(rule_dir: Path) -> DomainTrie:
    """Load all rule files in rule_dir into a DomainTrie.

    Supports dns.txt (AdGuard format) and hosts.txt (/etc/hosts format).
    """
    trie = DomainTrie()

    # dns.txt: ||domain^
    dns_file = rule_dir / "dns.txt"
    if dns_file.exists():
        for raw in dns_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith(("!", "#", "[")):
                continue
            domain = line.lstrip("|").rstrip("^").strip()
            if domain and "." in domain:
                trie.insert(domain.lower())

    # hosts.txt: 0.0.0.0 domain
    hosts_file = rule_dir / "hosts.txt"
    if hosts_file.exists():
        for raw in hosts_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1"):
                domain = parts[1].lower()
                if domain and "." in domain and domain != "localhost":
                    trie.insert(domain)

    # clash.yaml: - domain lines (simple domain list)
    clash_file = rule_dir / "clash.yaml"
    if clash_file.exists():
        for raw in clash_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("- "):
                domain = line[2:].strip().strip("'\"").lower()
                if domain and "." in domain:
                    trie.insert(domain)

    return trie


async def fetch_domain_list(url: str, *, timeout: int = 30) -> set[str]:
    """Download a domain list and parse it into a set of domains.

    Handles common formats:
    - One domain per line
    - hosts format (0.0.0.0 domain)
    - Comment lines (# or !)
    - CSV with domain in first column (Tranco)
    """
    domains: set[str] = set()

    try:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session,
            session.get(url) as resp,
        ):
            resp.raise_for_status()
            text = await resp.text(encoding="utf-8", errors="replace")
    except Exception as e:
        log.warning("Failed to fetch baseline %s: %s", url, e)
        return domains

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "!", "[")):
            continue

        # CSV format (Tranco): rank,domain
        if "," in line and line[0].isdigit():
            parts = line.split(",", maxsplit=1)
            if len(parts) == 2:
                domain = parts[1].strip().lower()
                if domain and "." in domain:
                    domains.add(domain)
                continue

        # Hosts format: 0.0.0.0 domain or 127.0.0.1 domain
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1"):
            domain = parts[1].strip().lower()
            if domain and "." in domain and domain != "localhost":
                domains.add(domain)
            continue

        # Plain domain format
        domain = parts[0].strip().lower().rstrip(".")
        if domain and "." in domain and not domain.startswith("http"):
            domains.add(domain)

    return domains


def compare_trie_with_baseline(
    trie: DomainTrie,
    baseline_domains: set[str],
    baseline_name: str,
    baseline_type: str,
    *,
    sample_limit: int = 20,
) -> BenchResult:
    """Compare a trie against a baseline domain set."""
    result = BenchResult(
        baseline_name=baseline_name,
        baseline_type=baseline_type,
        baseline_size=len(baseline_domains),
    )

    for domain in baseline_domains:
        if trie.matches(domain):
            result.matched += 1
            if len(result.sample_matched) < sample_limit:
                result.sample_matched.append(domain)
        else:
            result.unmatched += 1
            if len(result.sample_unmatched) < sample_limit:
                result.sample_unmatched.append(domain)

    return result


async def run_bench(
    rule_dir: Path,
    *,
    ad_baselines: dict[str, str] | None = None,
    legit_baselines: dict[str, str] | None = None,
    timeout: int = 30,
) -> BenchReport:
    """Run the full benchmark.

    Args:
        rule_dir: directory containing generated rule files
        ad_baselines: {name: url} for known-ad lists (None = use builtins)
        legit_baselines: {name: url} for known-legit lists (None = use builtins)
        timeout: HTTP timeout per request
    """
    t0 = time.monotonic()

    if ad_baselines is None:
        ad_baselines = BUILTIN_AD_BASELINES
    if legit_baselines is None:
        legit_baselines = BUILTIN_LEGIT_BASELINES

    # Load rules
    trie = load_rules_into_trie(rule_dir)
    report = BenchReport(rule_count=trie.size)
    log.info("bench: loaded %d rules from %s", trie.size, rule_dir)

    # Fetch all baselines concurrently
    all_baselines: list[tuple[str, str, str]] = []  # (name, url, type)
    for name, url in ad_baselines.items():
        all_baselines.append((name, url, "ad"))
    for name, url in legit_baselines.items():
        all_baselines.append((name, url, "legit"))

    async def fetch_one(name: str, url: str, btype: str) -> tuple[str, str, set[str]]:
        domains = await fetch_domain_list(url, timeout=timeout)
        log.info("bench: fetched %s (%s): %d domains", name, btype, len(domains))
        return name, btype, domains

    tasks = [fetch_one(n, u, t) for n, u, t in all_baselines]
    fetched = await asyncio.gather(*tasks, return_exceptions=True)

    # Compare
    for item in fetched:
        if isinstance(item, Exception):
            log.warning("bench: baseline fetch failed: %s", item)
            continue
        name, btype, domains = item
        if not domains:
            log.warning("bench: baseline %s returned 0 domains, skipping", name)
            continue
        result = compare_trie_with_baseline(trie, domains, name, btype)
        report.results.append(result)

    report.elapsed_ms = int((time.monotonic() - t0) * 1000)
    return report
