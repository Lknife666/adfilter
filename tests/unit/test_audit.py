"""Tests for the security audit module."""

from __future__ import annotations

import re
from pathlib import Path

from adfilter.security.audit import AuditPolicy, ContentAuditor, SecurityAlert


class TestAuditPolicy:
    def test_default_policy(self):
        policy = AuditPolicy()
        assert policy.max_new_rules_per_source == 5000
        assert policy.max_new_rules_ratio == 0.5
        assert "0.0.0.0" in policy.allowed_hosts_targets

    def test_from_file(self, tmp_path):
        domains_file = tmp_path / "protected.txt"
        domains_file.write_text(
            "# comment\ngoogle.com\ngithub.com\n\n  apple.com  \n"
        )
        policy = AuditPolicy.from_file(domains_file)
        assert "google.com" in policy.protected_domains
        assert "github.com" in policy.protected_domains
        assert "apple.com" in policy.protected_domains
        assert len(policy.protected_domains) == 3

    def test_from_file_missing(self, tmp_path):
        policy = AuditPolicy.from_file(tmp_path / "nonexistent.txt")
        assert len(policy.protected_domains) == 0

    def test_from_file_case_insensitive(self, tmp_path):
        domains_file = tmp_path / "protected.txt"
        domains_file.write_text("Google.COM\n")
        policy = AuditPolicy.from_file(domains_file)
        assert "google.com" in policy.protected_domains


class TestContentAuditor:
    def _make_auditor(self, protected=None, previous_counts=None, **kwargs):
        policy = AuditPolicy(
            protected_domains=frozenset(protected or []),
            **kwargs,
        )
        return ContentAuditor(policy, previous_counts=previous_counts)

    def test_no_issues(self):
        auditor = self._make_auditor(protected=["google.com"])
        result = auditor.audit_domains("test-source", ["ads.example.com", "tracker.bad.com"])
        assert result.passed
        assert result.critical_count == 0
        assert result.warning_count == 0

    def test_protected_domain_critical(self):
        auditor = self._make_auditor(protected=["google.com", "github.com"])
        result = auditor.audit_domains("evil-source", ["ads.example.com", "google.com"])
        assert not result.passed
        assert result.critical_count == 1
        assert result.alerts[0].severity == "critical"
        assert "google.com" in result.alerts[0].message

    def test_multiple_protected_domains(self):
        auditor = self._make_auditor(protected=["google.com", "github.com"])
        result = auditor.audit_domains("source", ["google.com", "github.com", "ads.com"])
        assert not result.passed
        assert result.critical_count == 2

    def test_volume_anomaly_spike(self):
        auditor = self._make_auditor(
            previous_counts={"source-a": 1000},
            max_new_rules_per_source=500,
        )
        domains = [f"d{i}.example.com" for i in range(2000)]
        result = auditor.audit_domains("source-a", domains)
        assert result.passed  # volume anomaly is warning, not critical
        assert result.warning_count >= 1
        assert "spike" in result.alerts[0].message.lower() or "grew" in result.alerts[0].message.lower()

    def test_volume_anomaly_ratio(self):
        auditor = self._make_auditor(
            previous_counts={"source-a": 100},
            max_new_rules_per_source=99999,
            max_new_rules_ratio=0.3,
        )
        # 100 -> 200 = 100% growth > 30% threshold
        domains = [f"d{i}.example.com" for i in range(200)]
        result = auditor.audit_domains("source-a", domains)
        assert result.passed
        assert result.warning_count >= 1

    def test_no_anomaly_for_new_source(self):
        auditor = self._make_auditor(previous_counts={})
        domains = [f"d{i}.example.com" for i in range(10000)]
        result = auditor.audit_domains("brand-new-source", domains)
        assert result.passed
        assert result.warning_count == 0

    def test_suspicious_patterns(self):
        auditor = self._make_auditor(
            suspicious_patterns=[re.compile(r"^\w{1,2}\.\w{2,3}$")],
        )
        result = auditor.audit_domains("source", ["ab.com", "normal.example.com"])
        assert result.passed  # patterns are warnings
        assert result.warning_count == 1
        assert "ab.com" in result.alerts[0].rule

    def test_audit_batch(self):
        auditor = self._make_auditor(protected=["google.com"])
        results = auditor.audit_batch({
            "good-source": ["ads.example.com"],
            "bad-source": ["google.com"],
        })
        assert len(results) == 2
        assert results[0].passed
        assert not results[1].passed


class TestBuildGuardEnhancements:
    def test_post_build_checks_empty_dir(self, tmp_path):
        from adfilter.build_guard import post_build_checks

        result = post_build_checks(tmp_path / "nonexistent")
        assert not result.passed

    def test_post_build_checks_no_files(self, tmp_path):
        from adfilter.build_guard import post_build_checks

        result = post_build_checks(tmp_path)
        assert not result.passed

    def test_post_build_checks_empty_file(self, tmp_path):
        from adfilter.build_guard import post_build_checks

        (tmp_path / "dns.txt").write_text("")
        result = post_build_checks(tmp_path)
        assert not result.passed

    def test_post_build_checks_normal(self, tmp_path):
        from adfilter.build_guard import post_build_checks

        (tmp_path / "dns.txt").write_text("||ads.example.com^\n" * 100)
        result = post_build_checks(tmp_path)
        assert result.passed

    def test_post_build_checks_shrink_detected(self, tmp_path):
        from adfilter.build_guard import post_build_checks

        (tmp_path / "dns.txt").write_text("x\n" * 10)
        result = post_build_checks(
            tmp_path, previous_sizes={"dns.txt": 10000}
        )
        assert not result.passed
        assert "shrank" in result.errors[0]

    def test_generate_manifest(self, tmp_path):
        from adfilter.build_guard import generate_manifest

        (tmp_path / "dns.txt").write_text("line1\nline2\n")
        (tmp_path / "clash.yaml").write_text("payload:\n  - x\n")
        manifest = generate_manifest(tmp_path, git_commit="abc123")
        assert manifest.git_commit == "abc123"
        assert len(manifest.files) == 2
        assert all(f.sha256 for f in manifest.files)
        assert all(f.size > 0 for f in manifest.files)

    def test_write_manifest(self, tmp_path):
        import json

        from adfilter.build_guard import generate_manifest, write_manifest

        (tmp_path / "dns.txt").write_text("test\n")
        manifest = generate_manifest(tmp_path)
        path = write_manifest(tmp_path, manifest)
        assert path.exists()
        data = json.loads(path.read_text())
        assert "files" in data
        assert "build_time" in data

    def test_get_previous_source_counts(self, tmp_path):
        from adfilter.build_guard import BuildGuard, SourceStatus

        state_file = tmp_path / "state.json"
        guard = BuildGuard(state_file=state_file, min_rules=0)
        sources = [
            SourceStatus(name="a", success=True, rule_count=500),
            SourceStatus(name="b", success=True, rule_count=300),
        ]
        guard.check(800, sources)
        # Create a new guard that loads the saved state
        guard2 = BuildGuard(state_file=state_file, min_rules=0)
        counts = guard2.get_previous_source_counts()
        assert counts == {"a": 500, "b": 300}
