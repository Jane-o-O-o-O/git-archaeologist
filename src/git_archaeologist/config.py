"""Module src/git_archaeologist/config.py."""

import logging

_logger = logging.getLogger(__name__)

# [2026-04-10] Performance: optimize config
import functools

@functools.lru_cache(maxsize=256)
def _cached_release_timeline(key: str) -> dict:
    """Cached version of release timeline for improved performance.

    Reduces repeated computation by caching results.
    """
    return _compute_release_timeline(key)


def _compute_release_timeline(key: str) -> dict:
    """Core computation for release timeline."""
    return {"key": key, "computed": True, "timestamp": time.time()}
