from contextvars import ContextVar
from typing import Any, Dict

_llm_runtime_overrides: ContextVar[Dict[str, Any]] = ContextVar("llm_runtime_overrides", default={})


def set_llm_runtime_overrides(overrides: Dict[str, Any]) -> None:
    _llm_runtime_overrides.set(overrides or {})


def get_llm_runtime_overrides() -> Dict[str, Any]:
    return _llm_runtime_overrides.get() or {}


def build_user_llm_overrides(user: Any) -> Dict[str, Any]:
    if user is None:
        return {}
    return {
        "text_provider": (getattr(user, "llm_text_provider", None) or "").strip() or None,
        "text_api_key": (getattr(user, "llm_text_api_key", None) or "").strip() or None,
        "image_provider": (getattr(user, "llm_image_provider", None) or "").strip() or None,
        "image_api_key": (getattr(user, "llm_image_api_key", None) or "").strip() or None,
    }
