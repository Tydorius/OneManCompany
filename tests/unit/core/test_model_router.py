"""Tests for the model_router module — cognitive budget model resolution."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def cb_config_enabled():
    """Return a CognitiveBudgetConfig with enabled=True and test profiles."""
    from onemancompany.core.config import CognitiveBudgetConfig, ModelProfile
    return CognitiveBudgetConfig(
        enabled=True,
        provider="custom",
        base_url="http://127.0.0.1:8080",
        api_key="not-needed",
        chat_class="openai",
        model_profiles={
            "architect": ModelProfile(
                model="architect",
                description="Strategic planning",
                context_window=256000,
                cost_tier="high",
                roles=["Architect", "Senior Architect"],
            ),
            "senior-engineer": ModelProfile(
                model="senior-engineer",
                description="Deep reasoning",
                context_window=128000,
                cost_tier="medium",
                roles=["Senior Engineer", "Software Engineer"],
            ),
            "tool-executor": ModelProfile(
                model="tool-executor",
                description="Fast execution",
                context_window=32000,
                cost_tier="low",
                roles=["Junior Developer", "QA Engineer"],
            ),
            "general": ModelProfile(
                model="senior-engineer",
                description="General-purpose",
                context_window=128000,
                cost_tier="medium",
                roles=["Assistant", "Engineer"],
            ),
        },
    )


@pytest.fixture
def cb_config_disabled():
    """Return a CognitiveBudgetConfig with enabled=False."""
    from onemancompany.core.config import CognitiveBudgetConfig
    return CognitiveBudgetConfig(enabled=False)


class TestResolveModelForRole:

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_disabled_returns_none(self, mock_load, cb_config_disabled):
        mock_load.return_value = cb_config_disabled
        from onemancompany.core.model_router import resolve_model_for_role
        assert resolve_model_for_role("Architect") is None

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_exact_role_match(self, mock_load, cb_config_enabled):
        mock_load.return_value = cb_config_enabled
        from onemancompany.core.model_router import resolve_model_for_role
        result = resolve_model_for_role("Architect")
        assert result == ("architect", "custom")

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_senior_engineer_role(self, mock_load, cb_config_enabled):
        mock_load.return_value = cb_config_enabled
        from onemancompany.core.model_router import resolve_model_for_role
        result = resolve_model_for_role("Senior Engineer")
        assert result == ("senior-engineer", "custom")

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_no_match_falls_back_to_general(self, mock_load, cb_config_enabled):
        mock_load.return_value = cb_config_enabled
        from onemancompany.core.model_router import resolve_model_for_role
        result = resolve_model_for_role("Unknown Role")
        assert result == ("senior-engineer", "custom")  # general profile's model

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_no_match_no_general_returns_none(self, mock_load):
        from onemancompany.core.config import CognitiveBudgetConfig, ModelProfile
        from onemancompany.core.model_router import resolve_model_for_role
        mock_load.return_value = CognitiveBudgetConfig(
            enabled=True,
            provider="custom",
            model_profiles={
                "architect": ModelProfile(model="architect", roles=["Architect"]),
            },
        )
        assert resolve_model_for_role("Unknown") is None


class TestResolveModelForProfileHint:

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_hint_matches_profile(self, mock_load, cb_config_enabled):
        mock_load.return_value = cb_config_enabled
        from onemancompany.core.model_router import resolve_model_for_profile_hint
        result = resolve_model_for_profile_hint("architect")
        assert result == ("architect", "custom")

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_hint_no_match_returns_none(self, mock_load, cb_config_enabled):
        mock_load.return_value = cb_config_enabled
        from onemancompany.core.model_router import resolve_model_for_profile_hint
        result = resolve_model_for_profile_hint("nonexistent")
        assert result is None

    @patch("onemancompany.core.model_router.load_cognitive_budget")
    def test_disabled_returns_none(self, mock_load, cb_config_disabled):
        mock_load.return_value = cb_config_disabled
        from onemancompany.core.model_router import resolve_model_for_profile_hint
        assert resolve_model_for_profile_hint("architect") is None


class TestResolveModelForEmployee:

    @patch("onemancompany.core.model_router.resolve_model_for_role")
    @patch("onemancompany.core.model_router.resolve_model_for_profile_hint")
    @patch("onemancompany.core.model_router.employee_configs")
    def test_explicit_model_returns_none(self, mock_configs, mock_hint, mock_role):
        from onemancompany.core.model_router import resolve_model_for_employee
        cfg = MagicMock()
        cfg.llm_model = "gpt-4"
        cfg.model_profile_hint = ""
        mock_configs.get.return_value = cfg
        assert resolve_model_for_employee("00100") is None
        mock_hint.assert_not_called()
        mock_role.assert_not_called()

    @patch("onemancompany.core.model_router.resolve_model_for_role")
    @patch("onemancompany.core.model_router.resolve_model_for_profile_hint")
    @patch("onemancompany.core.model_router.employee_configs")
    def test_empty_model_uses_hint(self, mock_configs, mock_hint, mock_role):
        from onemancompany.core.model_router import resolve_model_for_employee
        cfg = MagicMock()
        cfg.llm_model = ""
        cfg.model_profile_hint = "architect"
        cfg.role = "Engineer"
        mock_configs.get.return_value = cfg
        mock_hint.return_value = ("architect", "custom")
        result = resolve_model_for_employee("00100")
        assert result == ("architect", "custom")
        mock_role.assert_not_called()

    @patch("onemancompany.core.model_router.resolve_model_for_role")
    @patch("onemancompany.core.model_router.resolve_model_for_profile_hint")
    @patch("onemancompany.core.model_router.employee_configs")
    def test_no_hint_uses_role(self, mock_configs, mock_hint, mock_role):
        from onemancompany.core.model_router import resolve_model_for_employee
        cfg = MagicMock()
        cfg.llm_model = ""
        cfg.model_profile_hint = ""
        cfg.role = "Architect"
        mock_configs.get.return_value = cfg
        mock_hint.return_value = None
        mock_role.return_value = ("architect", "custom")
        result = resolve_model_for_employee("00100")
        assert result == ("architect", "custom")

    @patch("onemancompany.core.model_router.employee_configs")
    def test_unknown_employee_returns_none(self, mock_configs):
        from onemancompany.core.model_router import resolve_model_for_employee
        mock_configs.get.return_value = None
        assert resolve_model_for_employee("99999") is None


class TestGetEffectiveModel:

    @patch("onemancompany.core.model_router.resolve_model_for_role")
    @patch("onemancompany.core.model_router.employee_configs")
    def test_explicit_model_wins(self, mock_configs, mock_role):
        from onemancompany.core.model_router import get_effective_model
        cfg = MagicMock()
        cfg.llm_model = "gpt-4"
        cfg.api_provider = "openai"
        cfg.temperature = 0.5
        mock_configs.get.return_value = cfg
        model, provider, temp = get_effective_model("00100")
        assert model == "gpt-4"
        assert provider == "openai"
        assert temp == 0.5
        mock_role.assert_not_called()

    @patch("onemancompany.core.model_router.resolve_model_for_role")
    @patch("onemancompany.core.model_router.employee_configs")
    def test_cognitive_budget_used_when_no_explicit(self, mock_configs, mock_role):
        from onemancompany.core.model_router import get_effective_model
        cfg = MagicMock()
        cfg.llm_model = ""
        cfg.api_provider = "openrouter"
        cfg.temperature = 0.7
        cfg.role = "Architect"
        mock_configs.get.return_value = cfg
        mock_role.return_value = ("architect", "custom")
        model, provider, temp = get_effective_model("00100")
        assert model == "architect"
        assert provider == "custom"

    @patch("onemancompany.core.model_router.resolve_model_for_role")
    @patch("onemancompany.core.model_router.employee_configs")
    def test_fallback_to_defaults(self, mock_configs, mock_role):
        from onemancompany.core.model_router import get_effective_model
        mock_configs.get.return_value = None
        mock_role.return_value = None
        model, provider, temp = get_effective_model("99999")
        # Should use company defaults
        assert model is not None
        assert provider is not None
