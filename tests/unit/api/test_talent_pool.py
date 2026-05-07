"""Tests for GET /api/talent-pool endpoint — dual-source (local always, cloud optional)."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestTalentPoolLocalOnly:
    @pytest.mark.asyncio
    async def test_local_only_returns_dual_source(self, monkeypatch):
        """Returns dual-source with local talents when cloud not connected."""
        from onemancompany.agents import recruitment
        from onemancompany.core import config as config_mod

        monkeypatch.setattr(recruitment.talent_market, "_session", None)
        monkeypatch.setattr(config_mod, "list_available_talents", lambda: [
            {"id": "local1", "name": "Local Dev", "tier": "builtin"},
        ])
        monkeypatch.setattr(config_mod, "load_talent_profile", lambda tid: {
            "id": "local1", "name": "Local Dev", "role": "Engineer", "skills": ["python"],
        })

        from onemancompany.api.routes import get_talent_pool
        result = await get_talent_pool()

        assert result["source"] == "dual"
        assert result["local"]["count"] == 1
        assert result["local"]["talents"][0]["talent_id"] == "local1"
        assert result["local"]["talents"][0]["source"] == "local"
        assert result["local"]["talents"][0]["status"] == "local"
        assert result["cloud"]["connected"] is False
        assert result["cloud"]["count"] == 0
        assert len(result["talents"]) == 1

    @pytest.mark.asyncio
    async def test_empty_local(self, monkeypatch):
        """No local talents returns empty local list."""
        from onemancompany.agents import recruitment
        from onemancompany.core import config as config_mod

        monkeypatch.setattr(recruitment.talent_market, "_session", None)
        monkeypatch.setattr(config_mod, "list_available_talents", lambda: [])

        from onemancompany.api.routes import get_talent_pool
        result = await get_talent_pool()

        assert result["source"] == "dual"
        assert result["local"]["count"] == 0
        assert result["cloud"]["connected"] is False


class TestTalentPoolWithCloud:
    @pytest.mark.asyncio
    async def test_cloud_augments_local(self, monkeypatch):
        """Both local and cloud talents present when connected."""
        from onemancompany.agents import recruitment
        from onemancompany.core import config as config_mod

        monkeypatch.setattr(recruitment.talent_market, "_session", MagicMock())
        recruitment.talent_market.list_my_talents = AsyncMock(return_value={
            "talents": [
                {"talent_id": "api1", "name": "API Dev", "role": "Engineer",
                 "skills": ["react"], "purchased_at": "2026-03-10T12:00:00Z"},
            ]
        })
        monkeypatch.setattr(config_mod, "list_available_talents", lambda: [
            {"id": "local1", "name": "Local Dev", "tier": "builtin"},
        ])
        monkeypatch.setattr(config_mod, "load_talent_profile", lambda tid: {
            "id": "local1", "name": "Local Dev", "role": "Engineer", "skills": ["python"],
        })

        from onemancompany.api.routes import get_talent_pool
        result = await get_talent_pool()

        assert result["source"] == "dual"
        assert result["local"]["count"] == 1
        assert result["local"]["talents"][0]["source"] == "local"
        assert result["cloud"]["connected"] is True
        assert result["cloud"]["count"] == 1
        assert result["cloud"]["talents"][0]["source"] == "cloud"
        assert result["cloud"]["talents"][0]["status"] == "purchased"
        assert len(result["talents"]) == 2  # local + cloud

        # Cleanup
        recruitment.talent_market._session = None

    @pytest.mark.asyncio
    async def test_cloud_error_still_has_local(self, monkeypatch):
        """When cloud API call fails, local talents still returned."""
        from onemancompany.agents import recruitment
        from onemancompany.core import config as config_mod

        monkeypatch.setattr(recruitment.talent_market, "_session", MagicMock())
        recruitment.talent_market.list_my_talents = AsyncMock(side_effect=RuntimeError("API error"))

        monkeypatch.setattr(config_mod, "list_available_talents", lambda: [
            {"id": "local1", "name": "Local Dev", "tier": "builtin"},
        ])
        monkeypatch.setattr(config_mod, "load_talent_profile", lambda tid: {
            "id": "local1", "name": "Local Dev", "role": "Engineer", "skills": ["python"],
        })

        from onemancompany.api.routes import get_talent_pool
        result = await get_talent_pool()

        assert result["source"] == "dual"
        assert result["local"]["count"] == 1
        assert result["cloud"]["connected"] is False

        # Cleanup
        recruitment.talent_market._session = None
