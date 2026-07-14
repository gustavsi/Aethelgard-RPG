"""
Runtime feature flags for staged rollout and kill-switches.

Override via environment variables (0/false/off to disable):

  AETHEL_FF_COMBAT_INTENT=0
  AETHEL_FF_COMBAT_COMBOS=0
  AETHEL_FF_COMBAT_TELEMETRY=0
  AETHEL_FF_PARTY_BONDS=0
  AETHEL_FF_VOID_CORRUPTION=0
  AETHEL_FF_CONTENT_SYSTEMS=0
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class FeatureFlags:
    combat_intent: bool = True
    combat_combos: bool = True
    combat_telemetry: bool = True
    party_bonds: bool = True
    void_corruption: bool = True
    content_systems: bool = True  # Phase 3–5 narrative systems


def load_feature_flags() -> FeatureFlags:
    return FeatureFlags(
        combat_intent=_env_bool("AETHEL_FF_COMBAT_INTENT", True),
        combat_combos=_env_bool("AETHEL_FF_COMBAT_COMBOS", True),
        combat_telemetry=_env_bool("AETHEL_FF_COMBAT_TELEMETRY", True),
        party_bonds=_env_bool("AETHEL_FF_PARTY_BONDS", True),
        void_corruption=_env_bool("AETHEL_FF_VOID_CORRUPTION", True),
        content_systems=_env_bool("AETHEL_FF_CONTENT_SYSTEMS", True),
    )


# Process-wide defaults (tests may replace FLAGS)
FLAGS = load_feature_flags()


def reload_flags() -> FeatureFlags:
    global FLAGS
    FLAGS = load_feature_flags()
    return FLAGS
