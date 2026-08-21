"""Adapter interface for pulling records out of a county.

Deliberately CSV-first. Most county clerks either publish bulk exports or
will hand you one on request, and a documented export is far more durable
than a scraper aimed at a docket search page - it does not break on a site
redesign and it does not put you crosswise with a portal's terms of use.

To add a live fetcher for a county that offers a real API or a published
bulk file, subclass `Source`, implement `fetch`, and register it.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

from ..models import Lead

_REGISTRY: dict[str, type["Source"]] = {}


class Source:
    """Base class for anything that yields `Lead` objects."""

    name: str = "base"

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def fetch(self) -> Iterator[Lead]:
        raise NotImplementedError

    def __iter__(self) -> Iterator[Lead]:
        return self.fetch()


def register_source(cls: type[Source]) -> type[Source]:
    """Class decorator that adds a source to the registry."""
    _REGISTRY[cls.name] = cls
    return cls


def get_source(name: str) -> type[Source]:
    if name not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise KeyError(f"unknown source type {name!r}; registered: {known}")
    return _REGISTRY[name]


def available_sources() -> list[str]:
    return sorted(_REGISTRY)
