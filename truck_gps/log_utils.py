#!/usr/bin/env python3
"""Optional verbose dumps and throttled repeating logs."""

import logging
import threading
import time

from config import LOG_REPEAT_INTERVAL, VERBOSE_LOGS

_lock = threading.Lock()
_last_times = {}


def verbose(logger, msg, *args, **kwargs):
    """Log a debug dump only when VERBOSE_LOGS is True.

    Uses INFO so it shows up without changing LOG_LEVEL.
    """
    if VERBOSE_LOGS:
        logger.info(msg, *args, **kwargs)


def log_repeat(logger, key, level, msg, *args, **kwargs):
    """Log a repeating event without flooding the log file.

    VERBOSE_LOGS=True  → every call
    VERBOSE_LOGS=False → at most once per LOG_REPEAT_INTERVAL seconds
    """
    if VERBOSE_LOGS:
        logger.log(level, msg, *args, **kwargs)
        return

    now = time.time()
    with _lock:
        last = _last_times.get(key, 0.0)
        if now - last < LOG_REPEAT_INTERVAL:
            return
        _last_times[key] = now
    logger.log(level, msg, *args, **kwargs)
