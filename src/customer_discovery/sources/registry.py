from __future__ import annotations

from typing import Type

from customer_discovery.sources.base import CompanySource

_REGISTRY: dict[str, Type[CompanySource]] = {}


def register_source(source_id: str):
    def decorator(cls: Type[CompanySource]) -> Type[CompanySource]:
        cls.source_id = source_id
        _REGISTRY[source_id] = cls
        return cls

    return decorator


def get_source(source_id: str) -> CompanySource:
    if source_id not in _REGISTRY:
        raise KeyError(f"Unknown source: {source_id}. Available: {', '.join(_REGISTRY)}")
    return _REGISTRY[source_id]()


def list_sources() -> list[str]:
    return sorted(_REGISTRY.keys())
