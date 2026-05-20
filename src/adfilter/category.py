"""Rule category classification — GDPR-style labeling for rules.

Categorizes rules by purpose (ads, tracking, malware, etc.) using:
1. Source-level labels from source_catalog.yaml
2. Keyword-based domain inference
"""

from __future__ import annotations

import re
from enum import StrEnum, auto


class RuleCategory(StrEnum):
    """Rule classification labels."""

    ADS = auto()
    TRACKING = auto()
    MALWARE = auto()
    PHISHING = auto()
    SOCIAL = auto()
    FINGERPRINT = auto()
    CRYPTOMINER = auto()
    ANNOYANCE = auto()
    TELEMETRY = auto()
    UNKNOWN = auto()


# Keyword patterns for domain-based inference
_CATEGORY_PATTERNS: dict[RuleCategory, list[re.Pattern[str]]] = {
    RuleCategory.TRACKING: [
        re.compile(r"track", re.IGNORECASE),
        re.compile(r"pixel", re.IGNORECASE),
        re.compile(r"analytic", re.IGNORECASE),
        re.compile(r"telemetry", re.IGNORECASE),
        re.compile(r"beacon", re.IGNORECASE),
        re.compile(r"metric", re.IGNORECASE),
    ],
    RuleCategory.ADS: [
        re.compile(r"^ads?\.", re.IGNORECASE),
        re.compile(r"adserv", re.IGNORECASE),
        re.compile(r"doubleclick", re.IGNORECASE),
        re.compile(r"adsystem", re.IGNORECASE),
        re.compile(r"adnetwork", re.IGNORECASE),
        re.compile(r"banner", re.IGNORECASE),
    ],
    RuleCategory.MALWARE: [
        re.compile(r"malware", re.IGNORECASE),
        re.compile(r"phish", re.IGNORECASE),
        re.compile(r"botnet", re.IGNORECASE),
        re.compile(r"ransomware", re.IGNORECASE),
    ],
    RuleCategory.SOCIAL: [
        re.compile(r"facebook.*pixel", re.IGNORECASE),
        re.compile(r"fbcdn.*track", re.IGNORECASE),
        re.compile(r"connect\.facebook", re.IGNORECASE),
    ],
    RuleCategory.CRYPTOMINER: [
        re.compile(r"coinhive", re.IGNORECASE),
        re.compile(r"cryptomine", re.IGNORECASE),
        re.compile(r"miner", re.IGNORECASE),
    ],
}

# Source category string → RuleCategory mapping
_SOURCE_CATEGORY_MAP: dict[str, RuleCategory] = {
    "ads": RuleCategory.ADS,
    "privacy": RuleCategory.TRACKING,
    "tracking": RuleCategory.TRACKING,
    "malware": RuleCategory.MALWARE,
    "phishing": RuleCategory.PHISHING,
    "annoyance": RuleCategory.ANNOYANCE,
    "social": RuleCategory.SOCIAL,
    "fingerprint": RuleCategory.FINGERPRINT,
    "cryptominer": RuleCategory.CRYPTOMINER,
    "telemetry": RuleCategory.TELEMETRY,
}


def category_from_source(source_category: str) -> RuleCategory:
    """Map a source's category string to a RuleCategory enum."""
    return _SOURCE_CATEGORY_MAP.get(source_category.lower(), RuleCategory.UNKNOWN)


def infer_category(domain: str) -> RuleCategory:
    """Infer rule category from domain name using keyword patterns.

    Returns RuleCategory.UNKNOWN if no pattern matches.
    """
    for category, patterns in _CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(domain):
                return category
    return RuleCategory.UNKNOWN


def classify_domain(domain: str, source_category: str = "") -> RuleCategory:
    """Classify a domain using source label first, then keyword inference.

    Source-level category takes priority over keyword inference.
    """
    if source_category:
        cat = category_from_source(source_category)
        if cat != RuleCategory.UNKNOWN:
            return cat
    return infer_category(domain)
