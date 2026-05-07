"""Tests for cognitive budget API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from onemancompany.main import app
    return TestClient(app, raise_server_exceptions=False)


def _make_cb_config(enabled=True, profiles=None):
    from onemancompany.core.config import CognitiveBudgetConfig, ModelProfile
    return CognitiveBudgetConfig(
        enabled=enabled,
        provider="custom",
        base_url="http://localhost:8080",
        api_key="test-key-1234",
        chat_class="openai",
        model_profiles=profiles or {
            "architect": ModelProfile(
                model="architect-model",
                roles=["Architect"],
                description="Strategic planning",
            ),
        },
    )


def _make_employee_config(name="Test Emp", role="Architect", llm_model=""):
    cfg = MagicMock()
    cfg.name = name
    cfg.role = role
    cfg.llm_model = llm_model
    return cfg


class TestGetCognitiveBudget:

    @patch("onemancompany.core.config.employee_configs")
    @patch("onemancompany.core.config.load_cognitive_budget")
    def test_returns_config_with_profiles(self, mock_load, mock_configs, client):
        mock_load.return_value = _make_cb_config()
        mock_configs.items.return_value = []
        mock_configs.values.return_value = []

        resp = client.get("/api/cognitive-budget")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["provider"] == "custom"
        assert data["base_url"] == "http://localhost:8080"
        assert data["api_key_set"] is True
        assert data["api_key_preview"] == "...1234"
        assert "architect" in data["model_profiles"]

    @patch("onemancompany.core.config.employee_configs")
    @patch("onemancompany.core.config.load_cognitive_budget")
    def test_shows_assigned_employees(self, mock_load, mock_configs, client):
        mock_load.return_value = _make_cb_config()
        cfg = _make_employee_config(role="Architect")
        mock_configs.items.return_value = [("00100", cfg)]
        mock_configs.values.return_value = [cfg]

        resp = client.get("/api/cognitive-budget")
        data = resp.json()
        arch = data["model_profiles"]["architect"]
        assert len(arch["assigned_employees"]) == 1
        assert arch["assigned_employees"][0]["id"] == "00100"

    @patch("onemancompany.core.config.employee_configs")
    @patch("onemancompany.core.config.load_cognitive_budget")
    def test_hides_key_when_short(self, mock_load, mock_configs, client):
        from onemancompany.core.config import CognitiveBudgetConfig
        mock_load.return_value = CognitiveBudgetConfig(
            enabled=False, api_key="ab",
        )
        mock_configs.items.return_value = []
        mock_configs.values.return_value = []

        resp = client.get("/api/cognitive-budget")
        data = resp.json()
        assert data["api_key_preview"] == ""

    @patch("onemancompany.core.config.employee_configs")
    @patch("onemancompany.core.config.load_cognitive_budget")
    def test_finds_unassigned_roles(self, mock_load, mock_configs, client):
        mock_load.return_value = _make_cb_config()
        cfg = _make_employee_config(role="Sales Manager")
        mock_configs.items.return_value = [("00100", cfg)]
        mock_configs.values.return_value = [cfg]

        resp = client.get("/api/cognitive-budget")
        data = resp.json()
        assert "Sales Manager" in data["unassigned_roles"]


class TestUpdateCognitiveBudget:

    @patch("onemancompany.core.config.reload_app_config")
    @patch("onemancompany.core.config.write_text_utf")
    @patch("onemancompany.core.config.load_app_config")
    def test_updates_enabled(self, mock_load_config, mock_write, mock_reload, client):
        mock_load_config.return_value = {"cognitive_budget": {"enabled": False}}

        resp = client.put("/api/cognitive-budget", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"
        mock_write.assert_called_once()
        mock_reload.assert_called_once()

    @patch("onemancompany.core.config.reload_app_config")
    @patch("onemancompany.core.config.write_text_utf")
    @patch("onemancompany.core.config.load_app_config")
    def test_updates_base_url(self, mock_load_config, mock_write, mock_reload, client):
        mock_load_config.return_value = {"cognitive_budget": {}}

        resp = client.put("/api/cognitive-budget", json={"base_url": "http://new:9999"})
        assert resp.status_code == 200
        written_yaml = mock_write.call_args[0][1]
        assert "http://new:9999" in written_yaml

    @patch("onemancompany.core.config.reload_app_config")
    @patch("onemancompany.core.config.write_text_utf")
    @patch("onemancompany.core.config.load_app_config")
    def test_creates_section_if_missing(self, mock_load_config, mock_write, mock_reload, client):
        mock_load_config.return_value = {}

        resp = client.put("/api/cognitive-budget", json={"enabled": True})
        assert resp.status_code == 200
        written_yaml = mock_write.call_args[0][1]
        assert "enabled: true" in written_yaml


class TestSyncCognitiveBudget:

    @patch("onemancompany.core.config.sync_cognitive_budget_models")
    def test_sync_returns_count(self, mock_sync, client):
        mock_sync.return_value = 3

        resp = client.post("/api/cognitive-budget/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "synced"
        assert data["synced_count"] == 3

    @patch("onemancompany.core.config.sync_cognitive_budget_models")
    def test_sync_zero_when_nothing_to_do(self, mock_sync, client):
        mock_sync.return_value = 0

        resp = client.post("/api/cognitive-budget/sync")
        assert resp.status_code == 200
        assert resp.json()["synced_count"] == 0
