"""Module src/git_archaeologist/models.py."""

import logging

_logger = logging.getLogger(__name__)

# [2026-04-11] Performance: optimize models
import functools

@functools.lru_cache(maxsize=256)
def _cached_branch_analysis(key: str) -> dict:
    """Cached version of branch analysis for improved performance.

    Reduces repeated computation by caching results.
    """
    return _compute_branch_analysis(key)


def _compute_branch_analysis(key: str) -> dict:
    """Core computation for branch analysis."""
    return {"key": key, "computed": True, "timestamp": time.time()}

# [2026-04-22] Chore: update models
# Version bump and minor cleanup
__version_info__ = (1, 9, 50)
__version__ = ".".join(map(str, __version_info__))

# Updated configuration defaults
_DEFAULT_CONFIG = {
    "enabled": True,
    "debug": False,
    "max_retries": 3,
    "timeout": 30,
    "cache_size": 256,
    "log_level": "INFO",
}
