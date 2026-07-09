"""Lightweight logging helpers.

Two distinct kinds of logging are used in this project and must not be
confused:

* **Human/diagnostic logging** (this module's :func:`get_logger`) -- ordinary
  stderr logging for developers.
* **Structured experiment logging** (:mod:`se_support.runner.run_dir`) -- append
  only JSONL capture of every agent step / command, which is the raw data new
  metrics are computed from.
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def get_logger(name: str = "se_support") -> logging.Logger:
    """Return a configured stderr logger.

    Level is controlled by the ``SE_SUPPORT_LOG_LEVEL`` env var (default INFO).
    """
    global _CONFIGURED
    if not _CONFIGURED:
        level = os.environ.get("SE_SUPPORT_LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        _CONFIGURED = True
    return logging.getLogger(name)
