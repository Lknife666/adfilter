"""Source quality scoring — rates rule sources across multiple dimensions.

Produces an A/B/C/D/F grade for each source based on availability,
freshness, dead domain ratio, false positive rate, unique contribution,
stability, and community trust.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SourceQualityScore:
    """Quality score for a single rule source."""

    source_id: str
    overall_score: float = 0.0

    # Dimension scores (0.0 - 1.0)
    freshness: float = 0.5
    availability: float = 1.0
    dead_domain_ratio: float = 0.0
    false_positive_rate: float = 0.0
    overlap_ratio: float = 0.0
    unique_contribution: float = 0.5
    stability: float = 1.0
    community_trust: float = 0.5

    @property
    def grade(self) -> str:
        """A/B/C/D/F letter grade."""
        if self.overall_score >= 90:
            return "A"
        if self.overall_score >= 75:
            return "B"
        if self.overall_score >= 60:
            return "C"
        if self.overall_score >= 40:
            return "D"
        return "F"

    def compute_overall(self) -> float:
        """Compute the weighted overall score from dimensions."""
        self.overall_score = (
            self.freshness * 0.15
            + self.availability * 0.20
            + (1 - self.dead_domain_ratio) * 0.15
            + (1 - self.false_positive_rate) * 0.20
            + self.unique_contribution * 0.15
            + self.stability * 0.10
            + self.community_trust * 0.05
        ) * 100
        return self.overall_score

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "overall_score": round(self.overall_score, 1),
            "grade": self.grade,
            "freshness": round(self.freshness, 3),
            "availability": round(self.availability, 3),
            "dead_domain_ratio": round(self.dead_domain_ratio, 3),
            "false_positive_rate": round(self.false_positive_rate, 3),
            "overlap_ratio": round(self.overlap_ratio, 3),
            "unique_contribution": round(self.unique_contribution, 3),
            "stability": round(self.stability, 3),
            "community_trust": round(self.community_trust, 3),
        }


@dataclass
class FetchRecord:
    """Record of a single fetch attempt."""

    timestamp: float
    success: bool
    duration_ms: int = 0
    rule_count: int = 0


@dataclass
class SourceHistory:
    """Historical data for scoring a source."""

    source_id: str
    fetch_records: list[FetchRecord] = field(default_factory=list)
    last_rule_count: int = 0
    rule_count_history: list[int] = field(default_factory=list)
    dead_domain_samples: list[str] = field(default_factory=list)
    dead_ratio_estimate: float = 0.0

    @property
    def availability_rate(self) -> float:
        """Success rate over all recorded fetches."""
        if not self.fetch_records:
            return 1.0
        successes = sum(1 for r in self.fetch_records if r.success)
        return successes / len(self.fetch_records)

    @property
    def freshness_score(self) -> float:
        """Score based on time since last successful fetch (1.0 = just now, 0.0 = very old)."""
        successful = [r for r in self.fetch_records if r.success]
        if not successful:
            return 0.5
        last_success = max(r.timestamp for r in successful)
        hours_ago = (time.time() - last_success) / 3600
        if hours_ago <= 8:
            return 1.0
        if hours_ago <= 24:
            return 0.9
        if hours_ago <= 48:
            return 0.7
        if hours_ago <= 168:
            return 0.5
        return 0.3

    @property
    def stability_score(self) -> float:
        """Score based on variance in rule count changes."""
        if len(self.rule_count_history) < 2:
            return 1.0
        changes = []
        for i in range(1, len(self.rule_count_history)):
            prev = self.rule_count_history[i - 1]
            if prev > 0:
                change_ratio = abs(self.rule_count_history[i] - prev) / prev
                changes.append(change_ratio)
        if not changes:
            return 1.0
        avg_change = sum(changes) / len(changes)
        # Low variance = high stability
        if avg_change <= 0.01:
            return 1.0
        if avg_change <= 0.05:
            return 0.9
        if avg_change <= 0.10:
            return 0.7
        if avg_change <= 0.20:
            return 0.5
        return 0.3


class SourceScorer:
    """Compute quality scores for rule sources."""

    def __init__(self, cache_file: str | Path = ".cache/source_scores.json") -> None:
        self.cache_file = Path(cache_file)
        self._histories: dict[str, SourceHistory] = {}
        self._scores: dict[str, SourceQualityScore] = {}
        self._load_cache()

    def record_fetch(
        self,
        source_id: str,
        success: bool,
        duration_ms: int = 0,
        rule_count: int = 0,
    ) -> None:
        """Record a fetch attempt for a source."""
        history = self._histories.setdefault(source_id, SourceHistory(source_id=source_id))
        history.fetch_records.append(
            FetchRecord(
                timestamp=time.time(),
                success=success,
                duration_ms=duration_ms,
                rule_count=rule_count,
            )
        )
        if success and rule_count > 0:
            history.last_rule_count = rule_count
            history.rule_count_history.append(rule_count)
            # Keep last 30 entries
            if len(history.rule_count_history) > 30:
                history.rule_count_history = history.rule_count_history[-30:]
        # Keep last 30 fetch records
        if len(history.fetch_records) > 30:
            history.fetch_records = history.fetch_records[-30:]

    def update_dead_ratio(self, source_id: str, dead_ratio: float, samples: list[str] | None = None) -> None:
        """Update the dead domain ratio estimate for a source."""
        history = self._histories.setdefault(source_id, SourceHistory(source_id=source_id))
        history.dead_ratio_estimate = dead_ratio
        if samples:
            history.dead_domain_samples = samples[:10]

    def compute_scores(
        self,
        overlap_data: dict[str, float] | None = None,
        unique_data: dict[str, float] | None = None,
        fp_data: dict[str, float] | None = None,
    ) -> dict[str, SourceQualityScore]:
        """Compute scores for all tracked sources."""
        overlap_data = overlap_data or {}
        unique_data = unique_data or {}
        fp_data = fp_data or {}

        self._scores = {}
        for source_id, history in self._histories.items():
            score = SourceQualityScore(source_id=source_id)
            score.freshness = history.freshness_score
            score.availability = history.availability_rate
            score.dead_domain_ratio = history.dead_ratio_estimate
            score.false_positive_rate = fp_data.get(source_id, 0.0)
            score.overlap_ratio = overlap_data.get(source_id, 0.0)
            score.unique_contribution = unique_data.get(source_id, 0.5)
            score.stability = history.stability_score
            score.community_trust = 0.5  # Default; could be enriched from GitHub API
            score.compute_overall()
            self._scores[source_id] = score

        self._save_cache()
        return self._scores

    def get_scores(self) -> dict[str, SourceQualityScore]:
        """Get the last computed scores."""
        return self._scores

    def get_score(self, source_id: str) -> SourceQualityScore | None:
        """Get score for a single source."""
        return self._scores.get(source_id)

    def _load_cache(self) -> None:
        """Load cached history from disk."""
        if not self.cache_file.exists():
            return
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            for source_id, hist_data in data.get("histories", {}).items():
                history = SourceHistory(source_id=source_id)
                history.last_rule_count = hist_data.get("last_rule_count", 0)
                history.rule_count_history = hist_data.get("rule_count_history", [])
                history.dead_ratio_estimate = hist_data.get("dead_ratio_estimate", 0.0)
                history.dead_domain_samples = hist_data.get("dead_domain_samples", [])
                for rec in hist_data.get("fetch_records", []):
                    history.fetch_records.append(
                        FetchRecord(
                            timestamp=rec["timestamp"],
                            success=rec["success"],
                            duration_ms=rec.get("duration_ms", 0),
                            rule_count=rec.get("rule_count", 0),
                        )
                    )
                self._histories[source_id] = history
            for source_id, score_data in data.get("scores", {}).items():
                score = SourceQualityScore(source_id=source_id)
                score.overall_score = score_data.get("overall_score", 0)
                score.freshness = score_data.get("freshness", 0.5)
                score.availability = score_data.get("availability", 1.0)
                score.dead_domain_ratio = score_data.get("dead_domain_ratio", 0.0)
                score.false_positive_rate = score_data.get("false_positive_rate", 0.0)
                score.overlap_ratio = score_data.get("overlap_ratio", 0.0)
                score.unique_contribution = score_data.get("unique_contribution", 0.5)
                score.stability = score_data.get("stability", 1.0)
                score.community_trust = score_data.get("community_trust", 0.5)
                self._scores[source_id] = score
        except (json.JSONDecodeError, OSError, KeyError) as e:
            log.warning("SourceScorer: failed to load cache: %s", e)

    def _save_cache(self) -> None:
        """Persist history and scores to disk."""
        data: dict = {"histories": {}, "scores": {}, "last_updated": time.time()}
        for source_id, history in self._histories.items():
            data["histories"][source_id] = {
                "last_rule_count": history.last_rule_count,
                "rule_count_history": history.rule_count_history,
                "dead_ratio_estimate": history.dead_ratio_estimate,
                "dead_domain_samples": history.dead_domain_samples,
                "fetch_records": [
                    {
                        "timestamp": r.timestamp,
                        "success": r.success,
                        "duration_ms": r.duration_ms,
                        "rule_count": r.rule_count,
                    }
                    for r in history.fetch_records
                ],
            }
        for source_id, score in self._scores.items():
            data["scores"][source_id] = score.to_dict()
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except OSError as e:
            log.warning("SourceScorer: failed to save cache: %s", e)
