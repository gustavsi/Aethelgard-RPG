"""
Minimal in-process telemetry for PRD success metrics.

Not a product analytics platform — counters + structured log lines
so playtests can measure combo/interrupt rates without external deps.
"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Dict

from engine.feature_flags import FLAGS

logger = logging.getLogger("aethelgard.telemetry")

_lock = threading.Lock()
_counters: Dict[str, int] = defaultdict(int)


def track(event: str, **props: Any) -> None:
    if not FLAGS.combat_telemetry:
        return
    with _lock:
        _counters[event] += 1
        count = _counters[event]
    # Keep logs compact for multiplayer noise
    extra = " ".join(f"{k}={v}" for k, v in props.items()) if props else ""
    logger.info("event=%s count=%s %s", event, count, extra)


def get_counters() -> Dict[str, int]:
    with _lock:
        return dict(_counters)


def reset_counters() -> None:
    with _lock:
        _counters.clear()
