"""Model router — resolves which LLM model an employee should use via cognitive budget config."""

from __future__ import annotations

from loguru import logger

from onemancompany.core.config import (
    employee_configs,
    load_cognitive_budget,
)


def resolve_model_for_role(role: str) -> tuple[str, str] | None:
    """Resolve the model ID and provider for a given role using cognitive budget config.

    Returns (model_id, provider_name) if cognitive budgeting is enabled and a
    matching profile exists. Returns None if disabled or no match.
    """
    cb = load_cognitive_budget()
    if not cb.enabled:
        return None

    for profile_name, profile in cb.model_profiles.items():
        if role in profile.roles:
            logger.debug(
                "resolve_model_for_role: role='{}' -> profile='{}' model='{}'",
                role, profile_name, profile.model,
            )
            return (profile.model, cb.provider)

    general = cb.model_profiles.get("general")
    if general:
        logger.debug(
            "resolve_model_for_role: role='{}' -> fallback profile='general' model='{}'",
            role, general.model,
        )
        return (general.model, cb.provider)

    logger.debug("resolve_model_for_role: role='{}' -> no profile match", role)
    return None


def resolve_model_for_profile_hint(hint: str) -> tuple[str, str] | None:
    """Resolve model from a talent's model_profile_hint field.

    Returns (model_id, provider_name) if cognitive budgeting is enabled and
    the hint matches a profile name. Returns None otherwise.
    """
    cb = load_cognitive_budget()
    if not cb.enabled:
        return None

    profile = cb.model_profiles.get(hint)
    if profile:
        logger.debug(
            "resolve_model_for_profile_hint: hint='{}' -> model='{}'",
            hint, profile.model,
        )
        return (profile.model, cb.provider)

    return None


def resolve_model_for_employee(employee_id: str) -> tuple[str, str] | None:
    """Resolve model for an existing employee.

    Only resolves if the employee's current llm_model is empty (using default).
    If the employee already has an explicit model set, returns None (respect override).
    Checks model_profile_hint first, then role-based resolution.
    """
    cfg = employee_configs.get(employee_id)
    if not cfg:
        return None
    if cfg.llm_model:
        return None

    if cfg.model_profile_hint:
        hint_result = resolve_model_for_profile_hint(cfg.model_profile_hint)
        if hint_result:
            return hint_result

    return resolve_model_for_role(cfg.role)


def get_effective_model(employee_id: str) -> tuple[str, str, float]:
    """Get the effective (model, provider, temperature) for an employee.

    Resolution order:
    1. Employee's explicit llm_model + api_provider (from profile.yaml)
    2. Cognitive budget model resolution (from config.yaml)
    3. Company defaults (from settings)

    Returns (model, provider, temperature).
    """
    from onemancompany.core import config as _cfg

    cfg = employee_configs.get(employee_id)
    settings = _cfg.settings

    model = settings.default_llm_model
    provider = settings.default_api_provider or "openrouter"
    temperature = 0.7

    if cfg:
        temperature = cfg.temperature
        provider = cfg.api_provider
        if cfg.llm_model:
            model = cfg.llm_model

    if not cfg or not cfg.llm_model:
        cb_resolution = resolve_model_for_role(cfg.role if cfg else "")
        if cb_resolution:
            model, provider = cb_resolution

    return (model, provider, temperature)
