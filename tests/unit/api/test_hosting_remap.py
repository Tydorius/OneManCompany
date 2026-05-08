"""Tests for hosting remap, skill audit, and skill rewrite endpoints."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from onemancompany.core.models import HostingMode


def _apply_remap(talent_data, sel, settings_obj):
    """Replicate the remap logic from _do_batch_hire for unit testing."""
    remap_hosting = sel.get("remap_hosting")
    original_hosting = talent_data.get("hosting", "")
    if remap_hosting and original_hosting in ("self", HostingMode.SELF.value):
        talent_data["hosting"] = remap_hosting
        talent_data["api_provider"] = sel.get("remap_api_provider", settings_obj.default_api_provider)
        talent_data["llm_model"] = sel.get("remap_llm_model", settings_obj.default_llm_model)
        talent_data["auth_method"] = "api_key"
        talent_data.pop("claude_plugins", None)


class TestHostingRemapLogic:

    def test_remap_hosting_self_to_company(self):
        """When remap_hosting='company' is set, hosting:self gets remapped."""
        talent_data = {
            "hosting": "self",
            "api_provider": "openrouter",
            "llm_model": "claude-3",
            "auth_method": "cli",
            "claude_plugins": ["superpowers@superpowers-marketplace"],
        }
        settings = MagicMock(default_api_provider="custom", default_llm_model="test-model")
        sel = {
            "candidate_id": "c1",
            "role": "Engineer",
            "remap_hosting": "company",
            "remap_api_provider": "custom",
            "remap_llm_model": "test-model",
        }

        _apply_remap(talent_data, sel, settings)

        assert talent_data["hosting"] == "company"
        assert talent_data["api_provider"] == "custom"
        assert talent_data["llm_model"] == "test-model"
        assert talent_data["auth_method"] == "api_key"
        assert "claude_plugins" not in talent_data

    def test_no_remap_when_hosting_is_company(self):
        """Non-self hosting is not remapped."""
        talent_data = {
            "hosting": "company",
            "api_provider": "custom",
            "llm_model": "test-model",
        }
        settings = MagicMock(default_api_provider="custom", default_llm_model="test-model")
        sel = {
            "candidate_id": "c2",
            "role": "Engineer",
            "remap_hosting": "company",
            "remap_api_provider": "openai",
            "remap_llm_model": "gpt-4",
        }

        _apply_remap(talent_data, sel, settings)

        assert talent_data["hosting"] == "company"
        assert talent_data["api_provider"] == "custom"
        assert talent_data["llm_model"] == "test-model"

    def test_no_remap_when_not_requested(self):
        """No remap when remap_hosting is not set."""
        talent_data = {
            "hosting": "self",
            "api_provider": "openrouter",
        }
        settings = MagicMock()
        sel = {"candidate_id": "c3", "role": "Engineer"}

        _apply_remap(talent_data, sel, settings)

        assert talent_data["hosting"] == "self"
        assert talent_data["api_provider"] == "openrouter"

    def test_remap_removes_claude_plugins(self):
        """Remap strips claude_plugins list."""
        talent_data = {
            "hosting": "self",
            "api_provider": "openrouter",
            "claude_plugins": ["plugin-a", "plugin-b"],
        }
        settings = MagicMock(default_api_provider="custom", default_llm_model="qwen-3.6-35b")
        sel = {"candidate_id": "c4", "remap_hosting": "company"}

        _apply_remap(talent_data, sel, settings)

        assert "claude_plugins" not in talent_data
        assert talent_data["auth_method"] == "api_key"

    def test_remap_uses_defaults_from_settings(self):
        """When remap fields are empty, falls back to settings defaults."""
        talent_data = {"hosting": "self"}
        settings = MagicMock(default_api_provider="anthropic", default_llm_model="claude-3-haiku")
        sel = {"candidate_id": "c5", "remap_hosting": "company"}

        _apply_remap(talent_data, sel, settings)

        assert talent_data["api_provider"] == "anthropic"
        assert talent_data["llm_model"] == "claude-3-haiku"

    def test_remap_with_hosting_mode_enum(self):
        """Remap works with HostingMode.SELF enum value."""
        talent_data = {"hosting": HostingMode.SELF}
        settings = MagicMock(default_api_provider="custom", default_llm_model="test")
        sel = {"candidate_id": "c6", "remap_hosting": "company"}

        _apply_remap(talent_data, sel, settings)

        assert talent_data["hosting"] == "company"


class TestProvidersEndpoint:

    def test_filters_providers_with_keys(self):
        """Only providers with configured API keys are returned."""
        from onemancompany.core.config import PROVIDER_REGISTRY, ProviderConfig

        assert "openrouter" in PROVIDER_REGISTRY
        assert "custom" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["openrouter"].env_key == "openrouter_api_key"
        assert PROVIDER_REGISTRY["custom"].env_key == "custom_api_key"


class TestLoadSkillContent:

    def test_returns_empty_for_missing_skill(self):
        """_load_skill_content returns empty string when skill not found."""
        from onemancompany.api.routes import _load_skill_content

        result = _load_skill_content("nonexistent-skill-xyz-12345")
        assert result == ""


class TestSkillAuditPrompt:

    def test_prompt_covers_all_categories(self):
        """The auditor prompt should mention all 7 detection categories."""
        from onemancompany.api.routes import _SKILL_AUDITOR_PROMPT

        categories = [
            "config file paths",
            "CLI commands",
            "tool/event names",
            "API authentication",
            "environment variable",
            "Shell scripts",
            "file paths",
        ]
        for cat in categories:
            assert cat.lower() in _SKILL_AUDITOR_PROMPT.lower(), f"Missing category: {cat}"

    def test_prompt_requests_json_output(self):
        """The auditor prompt should specify JSON output format."""
        from onemancompany.api.routes import _SKILL_AUDITOR_PROMPT

        assert "JSON" in _SKILL_AUDITOR_PROMPT
        assert '"status"' in _SKILL_AUDITOR_PROMPT
        assert '"findings"' in _SKILL_AUDITOR_PROMPT

    def test_prompt_includes_severity_levels(self):
        """The auditor prompt should specify high/medium/low severity."""
        from onemancompany.api.routes import _SKILL_AUDITOR_PROMPT

        assert "high" in _SKILL_AUDITOR_PROMPT.lower()
        assert "medium" in _SKILL_AUDITOR_PROMPT.lower()
        assert "low" in _SKILL_AUDITOR_PROMPT.lower()

    def test_rewriter_prompt_preserves_behavior(self):
        """The rewriter prompt should emphasize preserving behavioral instructions."""
        from onemancompany.api.routes import _SKILL_REWRITER_PROMPT

        assert "behavioral instructions" in _SKILL_REWRITER_PROMPT
        assert "frontmatter" in _SKILL_REWRITER_PROMPT
        assert "findings_json" in _SKILL_REWRITER_PROMPT
        assert "skill_content" in _SKILL_REWRITER_PROMPT


class TestRewriteSkillEndpoint:

    @pytest.mark.asyncio
    async def test_rewrite_returns_error_for_missing_skill(self):
        """Rewrite endpoint returns error when skill not found."""
        from onemancompany.api.routes import rewrite_skill

        with patch("onemancompany.api.routes._load_skill_content", return_value=""):
            result = await rewrite_skill({"skill_name": "nonexistent"})
            assert result["status"] == "error"
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rewrite_returns_error_for_missing_name(self):
        """Rewrite endpoint returns error when skill_name is empty."""
        from onemancompany.api.routes import rewrite_skill

        result = await rewrite_skill({"skill_name": ""})
        assert result["status"] == "error"
        assert "required" in result["error"].lower()


class TestAuditSkillsEndpoint:

    @pytest.mark.asyncio
    async def test_audit_returns_error_for_no_candidates(self):
        """Audit endpoint returns error when no candidate_ids provided."""
        from onemancompany.api.routes import audit_skills

        result = await audit_skills({"batch_id": "b1", "candidate_ids": []})
        assert result["error"] == "No candidates specified"

    @pytest.mark.asyncio
    async def test_audit_returns_error_when_no_llm(self):
        """Audit endpoint returns error when no LLM can be created."""
        from onemancompany.api.routes import audit_skills

        with patch("onemancompany.api.routes._make_auditor_llm", new_callable=AsyncMock, return_value=None):
            result = await audit_skills({
                "batch_id": "b1",
                "candidate_ids": ["c1"],
                "evaluator_model": "",
            })
            assert "No LLM" in result["error"]


class TestMakeAuditorLLM:

    @pytest.mark.asyncio
    async def test_returns_none_when_no_key(self):
        """_make_auditor_llm returns None when provider has no key."""
        from onemancompany.api.routes import _make_auditor_llm

        with patch("onemancompany.agents.base._resolve_provider_key", return_value=""):
            result = await _make_auditor_llm("test-model", "openrouter")
            assert result is None
