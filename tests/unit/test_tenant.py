"""Tests for the tenant module."""

from __future__ import annotations

from pathlib import Path

from adfilter.tenant import TenantConfig, TenantManager


class TestTenantConfig:
    def test_default_output_dir(self):
        t = TenantConfig(id="test", name="Test", config_path="config.yaml")
        assert t.output_dir == "./rule/test"

    def test_custom_output_dir(self):
        t = TenantConfig(id="test", name="Test", config_path="c.yaml", output_dir="/custom")
        assert t.output_dir == "/custom"

    def test_enabled_default(self):
        t = TenantConfig(id="t", name="T", config_path="c.yaml")
        assert t.enabled is True

    def test_tags(self):
        t = TenantConfig(id="t", name="T", config_path="c.yaml", tags=["prod", "cn"])
        assert t.tags == ["prod", "cn"]


class TestTenantManager:
    def test_register_and_get(self):
        mgr = TenantManager()
        tc = TenantConfig(id="a", name="A", config_path="a.yaml")
        mgr.register(tc)
        assert mgr.get("a") == tc
        assert mgr.tenant_count == 1

    def test_register_overwrites(self):
        mgr = TenantManager()
        tc1 = TenantConfig(id="a", name="A1", config_path="a1.yaml")
        tc2 = TenantConfig(id="a", name="A2", config_path="a2.yaml")
        mgr.register(tc1)
        mgr.register(tc2)
        assert mgr.get("a").name == "A2"
        assert mgr.tenant_count == 1

    def test_unregister(self):
        mgr = TenantManager()
        tc = TenantConfig(id="a", name="A", config_path="a.yaml")
        mgr.register(tc)
        assert mgr.unregister("a")
        assert mgr.get("a") is None
        assert mgr.tenant_count == 0

    def test_unregister_nonexistent(self):
        mgr = TenantManager()
        assert not mgr.unregister("nonexistent")

    def test_list_tenants(self):
        mgr = TenantManager()
        mgr.register(TenantConfig(id="a", name="A", config_path="a.yaml"))
        mgr.register(TenantConfig(id="b", name="B", config_path="b.yaml"))
        assert len(mgr.list_tenants()) == 2

    def test_list_enabled(self):
        mgr = TenantManager()
        mgr.register(TenantConfig(id="a", name="A", config_path="a.yaml", enabled=True))
        mgr.register(TenantConfig(id="b", name="B", config_path="b.yaml", enabled=False))
        enabled = mgr.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].id == "a"

    def test_get_output_dir(self):
        mgr = TenantManager(base_dir="/base")
        mgr.register(TenantConfig(id="a", name="A", config_path="a.yaml"))
        assert mgr.get_output_dir("a") == Path("/base/./rule/a")

    def test_get_output_dir_unknown(self):
        mgr = TenantManager(base_dir="/base")
        assert mgr.get_output_dir("unknown") == Path("/base/rule")

    def test_get_config_path(self):
        mgr = TenantManager(base_dir="/base")
        mgr.register(TenantConfig(id="a", name="A", config_path="configs/a.yaml"))
        assert mgr.get_config_path("a") == Path("/base/configs/a.yaml")

    def test_get_config_path_absolute(self):
        mgr = TenantManager(base_dir="/base")
        mgr.register(TenantConfig(id="a", name="A", config_path="/abs/a.yaml"))
        assert mgr.get_config_path("a") == Path("/abs/a.yaml")

    def test_get_config_path_unknown(self):
        mgr = TenantManager()
        assert mgr.get_config_path("unknown") is None

    def test_ensure_directories(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        mgr.register(TenantConfig(id="a", name="A", config_path="a.yaml", output_dir="output/a"))
        mgr.ensure_directories()
        assert (tmp_path / "output" / "a").is_dir()
