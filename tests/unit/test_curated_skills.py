"""Tests for curated skill system — frontmatter validation, injection, and SkillsMP toggle."""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


_CURATED_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "onemancompany" / "curated_skills"
_SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"


class TestCuratedSkillFrontmatter:
    """Every curated skill must have valid YAML frontmatter with required fields."""

    @pytest.fixture(params=[
        "systematic-debugging",
        "test-driven-development",
        "code-review",
        "context-fundamentals",
    ])
    def skill_dir(self, request):
        return _CURATED_DIR / request.param

    def test_skill_md_exists(self, skill_dir):
        assert (skill_dir / "SKILL.md").is_file(), f"Missing SKILL.md in {skill_dir.name}"

    def test_frontmatter_is_valid_yaml(self, skill_dir):
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, f"No YAML frontmatter found in {skill_dir.name}/SKILL.md"
        meta = yaml.safe_load(match.group(1))
        assert isinstance(meta, dict), f"Frontmatter must be a YAML dict in {skill_dir.name}"

    def test_has_required_fields(self, skill_dir):
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        meta = yaml.safe_load(match.group(1))
        for field in ("name", "description", "autoload", "version", "author"):
            assert field in meta, f"Missing '{field}' in {skill_dir.name}/SKILL.md frontmatter"

    def test_autoload_is_bool(self, skill_dir):
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        meta = yaml.safe_load(match.group(1))
        assert isinstance(meta["autoload"], bool), (
            f"autoload must be bool in {skill_dir.name}, got {type(meta['autoload'])}"
        )

    def test_has_mcp_schema(self, skill_dir):
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        meta = yaml.safe_load(match.group(1))
        assert "mcp_schema" in meta, f"Missing mcp_schema in {skill_dir.name}/SKILL.md"
        schema = meta["mcp_schema"]
        assert "inputs" in schema, f"mcp_schema missing 'inputs' in {skill_dir.name}"
        assert "outputs" in schema, f"mcp_schema missing 'outputs' in {skill_dir.name}"
        assert isinstance(schema["inputs"], dict)
        assert isinstance(schema["outputs"], dict)

    def test_mcp_schema_inputs_have_type_and_constraints(self, skill_dir):
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        meta = yaml.safe_load(match.group(1))
        for inp_name, inp_def in meta["mcp_schema"]["inputs"].items():
            assert "type" in inp_def, f"Input '{inp_name}' missing 'type' in {skill_dir.name}"
            if inp_def["type"] == "string":
                assert "maxLength" in inp_def, f"Input '{inp_name}' missing 'maxLength' in {skill_dir.name}"
            elif inp_def["type"] == "integer":
                assert "maximum" in inp_def, f"Input '{inp_name}' missing 'maximum' in {skill_dir.name}"

    def test_mcp_schema_outputs_have_type_and_maxlength(self, skill_dir):
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        meta = yaml.safe_load(match.group(1))
        for out_name, out_def in meta["mcp_schema"]["outputs"].items():
            assert "type" in out_def, f"Output '{out_name}' missing 'type' in {skill_dir.name}"
            assert "maxLength" in out_def, f"Output '{out_name}' missing 'maxLength' in {skill_dir.name}"

    def test_has_body_content_after_frontmatter(self, skill_dir):
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n.*?\n---\n+", content, re.DOTALL)
        assert match, f"No closing frontmatter delimiter in {skill_dir.name}"
        body = content[match.end():]
        assert len(body.strip()) > 50, f"Body too short in {skill_dir.name}/SKILL.md"


class TestCuratedSkillInjection:
    """_inject_curated_skills must copy skill directories correctly."""

    def test_inject_creates_skill_dirs(self, tmp_path):
        from onemancompany.agents.onboarding import _inject_curated_skills

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _inject_curated_skills(skills_dir)

        for name in ("systematic-debugging", "test-driven-development",
                      "code-review", "context-fundamentals"):
            skill_md = skills_dir / name / "SKILL.md"
            assert skill_md.is_file(), f"Curated skill {name} not injected"

    def test_inject_syncs_updated_skill_md(self, tmp_path):
        from onemancompany.agents.onboarding import _inject_curated_skills

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        _inject_curated_skills(skills_dir)

        modified = (skills_dir / "systematic-debugging" / "SKILL.md").read_text()
        assert "systematic-debugging" in modified

        _inject_curated_skills(skills_dir)

        assert (skills_dir / "systematic-debugging" / "SKILL.md").is_file()

    def test_inject_skips_missing_skills(self, tmp_path, monkeypatch):
        from onemancompany.agents import onboarding as ob_mod

        monkeypatch.setattr(ob_mod, "_CURATED_SKILL_NAMES", ["nonexistent-skill"])
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        ob_mod._inject_curated_skills(skills_dir)

        assert list(skills_dir.iterdir()) == []


class TestCuratedSkillConstants:
    """Verify curated skill constants are properly defined."""

    def test_curated_skills_dir_exists(self):
        from onemancompany.agents.onboarding import _CURATED_SKILLS_DIR
        assert _CURATED_SKILLS_DIR.is_dir(), f"_CURATED_SKILLS_DIR does not exist: {_CURATED_SKILLS_DIR}"

    def test_curated_skill_names_list(self):
        from onemancompany.agents.onboarding import _CURATED_SKILL_NAMES
        assert isinstance(_CURATED_SKILL_NAMES, list)
        assert len(_CURATED_SKILL_NAMES) == 4
        for name in _CURATED_SKILL_NAMES:
            assert isinstance(name, str)

    def test_each_curated_skill_dir_exists(self):
        from onemancompany.agents.onboarding import _CURATED_SKILLS_DIR, _CURATED_SKILL_NAMES
        for name in _CURATED_SKILL_NAMES:
            skill_dir = _CURATED_SKILLS_DIR / name
            assert skill_dir.is_dir(), f"Curated skill directory missing: {skill_dir}"
            assert (skill_dir / "SKILL.md").is_file(), f"SKILL.md missing in {skill_dir}"


class TestSkillsMarketToggle:
    """Verify SkillsMP marketplace is toggle-gated by config mode and API key."""

    def test_no_fastskills_in_local_mode(self):
        from onemancompany.tools.mcp.config_builder import build_mcp_config

        with patch("onemancompany.tools.mcp.config_builder.load_app_config",
                   return_value={"skills_market": {"enabled": True, "mode": "local"}}), \
             patch("onemancompany.tools.mcp.config_builder.settings"):
            config = build_mcp_config("00100")
        assert "fastskills" not in config["mcpServers"]

    def test_fastskills_spawned_in_remote_mode_with_key(self):
        from onemancompany.tools.mcp.config_builder import build_mcp_config

        mock_settings = MagicMock()
        mock_settings.skillsmp_api_key = ""
        with patch("onemancompany.tools.mcp.config_builder.load_app_config",
                   return_value={"skills_market": {"enabled": True, "mode": "remote", "api_key": "sk-test-123"}}), \
             patch("onemancompany.tools.mcp.config_builder.settings", mock_settings), \
             patch("onemancompany.tools.mcp.config_builder.EMPLOYEES_DIR", Path("/tmp/employees")):
            config = build_mcp_config("00100")
        assert "fastskills" in config["mcpServers"]
        assert config["mcpServers"]["fastskills"]["env"]["SKILLSMP_API_KEY"] == "sk-test-123"

    def test_no_fastskills_without_api_key(self):
        from onemancompany.tools.mcp.config_builder import build_mcp_config

        mock_settings = MagicMock()
        mock_settings.skillsmp_api_key = ""
        with patch("onemancompany.tools.mcp.config_builder.load_app_config",
                   return_value={"skills_market": {"enabled": True, "mode": "remote"}}), \
             patch("onemancompany.tools.mcp.config_builder.settings", mock_settings):
            config = build_mcp_config("00100")
        assert "fastskills" not in config["mcpServers"]

    def test_disabled_flag_overrides_mode(self):
        from onemancompany.tools.mcp.config_builder import build_mcp_config

        with patch("onemancompany.tools.mcp.config_builder.load_app_config",
                   return_value={"skills_market": {"enabled": False, "mode": "remote", "api_key": "sk-test"}}), \
             patch("onemancompany.tools.mcp.config_builder.settings"):
            config = build_mcp_config("00100")
        assert "fastskills" not in config["mcpServers"]

    def test_local_remote_mode_with_key_spawns_fastskills(self):
        from onemancompany.tools.mcp.config_builder import build_mcp_config

        mock_settings = MagicMock()
        mock_settings.skillsmp_api_key = ""
        with patch("onemancompany.tools.mcp.config_builder.load_app_config",
                   return_value={"skills_market": {"enabled": True, "mode": "local+remote", "api_key": "sk-lr"}}), \
             patch("onemancompany.tools.mcp.config_builder.settings", mock_settings), \
             patch("onemancompany.tools.mcp.config_builder.EMPLOYEES_DIR", Path("/tmp/employees")):
            config = build_mcp_config("00100")
        assert "fastskills" in config["mcpServers"]

    def test_api_key_falls_back_to_settings(self):
        from onemancompany.tools.mcp.config_builder import build_mcp_config

        mock_settings = MagicMock()
        mock_settings.skillsmp_api_key = "sk-from-settings"
        with patch("onemancompany.tools.mcp.config_builder.load_app_config",
                   return_value={"skills_market": {"enabled": True, "mode": "remote"}}), \
             patch("onemancompany.tools.mcp.config_builder.settings", mock_settings), \
             patch("onemancompany.tools.mcp.config_builder.EMPLOYEES_DIR", Path("/tmp/employees")):
            config = build_mcp_config("00100")
        assert "fastskills" in config["mcpServers"]
        assert config["mcpServers"]["fastskills"]["env"]["SKILLSMP_API_KEY"] == "sk-from-settings"

    def test_skillsmp_api_key_in_settings(self):
        from onemancompany.core.config import Settings
        field_names = {f for f in Settings.model_fields}
        assert "skillsmp_api_key" in field_names, "skillsmp_api_key missing from Settings"

    def test_env_key_constant_exists(self):
        import onemancompany.core.config as cfg_mod
        assert hasattr(cfg_mod, "ENV_KEY_SKILLSMP"), "ENV_KEY_SKILLSMP constant missing"
        assert cfg_mod.ENV_KEY_SKILLSMP == "SKILLSMP_API_KEY"
