"""
Void Corruption meter (PRD E1).

Range 0–100. Tiers drive modest combat multipliers (double-edged).
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

CORRUPTION_MIN = 0
CORRUPTION_MAX = 100

# (min_inclusive, max_inclusive, tier_id, label)
TIERS: Tuple[Tuple[int, int, str, str], ...] = (
    (0, 24, "clean", "Puro"),
    (25, 49, "whisper", "Sussurro"),
    (50, 74, "shadowed", "Sombreado"),
    (75, 100, "void_touched", "Tocado pelo Vazio"),
)


def clamp_corruption(value: int) -> int:
    return max(CORRUPTION_MIN, min(CORRUPTION_MAX, int(value)))


def tier_for(value: int) -> Dict[str, Any]:
    v = clamp_corruption(value)
    for lo, hi, tid, label in TIERS:
        if lo <= v <= hi:
            return {"id": tid, "label": label, "min": lo, "max": hi}
    return {"id": "clean", "label": "Puro", "min": 0, "max": 24}


def add_corruption(current: int, amount: int) -> int:
    return clamp_corruption(current + amount)


def normalize_corruption(raw: Any) -> int:
    try:
        return clamp_corruption(int(raw))
    except (TypeError, ValueError):
        return 0


def public_view(value: int) -> Dict[str, Any]:
    v = clamp_corruption(value)
    t = tier_for(v)
    return {
        "value": v,
        "max": CORRUPTION_MAX,
        "tier": t["id"],
        "tier_label": t["label"],
        "offense_mult": offense_multiplier(v),
        "heal_mult": heal_multiplier(v),
        "damage_taken_mult": damage_taken_multiplier(v),
    }


def offense_multiplier(value: int) -> float:
    """Outgoing skill/attack damage from party."""
    t = tier_for(value)["id"]
    if t == "whisper":
        return 1.08
    if t == "shadowed":
        return 1.15
    if t == "void_touched":
        return 1.20
    return 1.0


def heal_multiplier(value: int) -> float:
    """Holy / cleric-style healing."""
    t = tier_for(value)["id"]
    if t == "whisper":
        return 0.90
    if t == "shadowed":
        return 0.80
    if t == "void_touched":
        return 0.70
    return 1.0


def damage_taken_multiplier(value: int) -> float:
    t = tier_for(value)["id"]
    if t == "void_touched":
        return 1.05
    return 1.0


def is_holy_skill_name(name: str) -> bool:
    n = (name or "").lower()
    return any(
        k in n
        for k in (
            "sagrada",
            "divina",
            "bênção",
            "bencao",
            "luz",
            "holy",
            "cura",
            "protetora",
        )
    )
