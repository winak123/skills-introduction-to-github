"""Source adapters that turn county records into `Lead` objects."""

from .base import Source, register_source, get_source, available_sources
from .csv_source import CsvSource  # noqa: F401  (registers itself on import)

__all__ = ["Source", "register_source", "get_source", "available_sources", "CsvSource"]
