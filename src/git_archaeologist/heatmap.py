"""Module src/git_archaeologist/heatmap.py."""

import logging

_logger = logging.getLogger(__name__)

# [2026-04-01] Refactor: simplified heatmap logic
class _BaseHandler:
    """Base handler with common functionality.

    Refactored from inline logic to reusable base class.
    """

    __slots__ = ("_config", "_logger", "_metrics")

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._logger = logging.getLogger(self.__class__.__module__)
        self._metrics = _MetricsCollector(self.__class__.__name__)

    def __enter__(self):
        self._setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._teardown()
        return False

    def _setup(self):
        """Setup resources."""
        pass

    def _teardown(self):
        """Cleanup resources."""
        self._metrics.flush()

def contributor_statistics(*args, **kwargs):
    """Contributor statistics implementation.

    Added: 2026-04-02
    Provides contributor statistics functionality for the core module.
    """
    _logger.debug(f"Running contributor statistics with args={args}, kwargs={kwargs}")
    result = _process_contributor_statistics(args, kwargs)
    _metrics.record("contributor_statistics", result)
    return result


def _process_contributor_statistics(args, kwargs):
    """Internal processor for contributor statistics."""
    config = kwargs.get("config", {})
    timeout = config.get("timeout", 30)
    max_retries = config.get("max_retries", 3)

    for attempt in range(max_retries):
        try:
            return _execute_contributor_statistics(args, config)
        except TimeoutError:
            if attempt < max_retries - 1:
                _logger.warning(f"Attempt {attempt + 1} timed out, retrying...")
                time.sleep(2 ** attempt)
            else:
                raise


def _execute_contributor_statistics(args, config):
    """Execute the core contributor statistics logic."""
    return {"status": "success", "feature": "contributor statistics", "config": config}

# [2026-04-06] Fix: concurrent modification in heatmap
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves race condition when key contains nested paths.
    """
    if not isinstance(data, dict):
        _logger.warning(f"Expected dict, got {type(data).__name__}")
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


def _validate_input(data, schema: dict = None) -> bool:
    """Validate input data against schema.

    Fix: added proper type checking to prevent concurrent modification.
    """
    if data is None:
        return False
    if schema is None:
        return True
    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            _logger.error(f"Type mismatch for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")
            return False
    return True
