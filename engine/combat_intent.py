"""
Enemy intent telegraph + interrupt contest (PRD B1).

Intents are planned once per round at TURN_START and executed on ENEMY_TURN
unless cancelled by a successful INTERRUPT command.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from engine.constants import AIType

# action_type from Enemy.select_action → player-facing category
_ACTION_TO_CATEGORY = {
    "ATTACK": "attack",
    "ATTACK_DRAIN": "attack",
    "HEAL": "guard",
    "DEFEND": "guard",
    "SKILL": "cast",
    "SUMMON": "special",
    "RAGE": "special",
    "TRANSFORM": "special",
    "SKIP": "none",
    "FLEE": "special",
}

_CATEGORY_LABELS = {
    "attack": "Ataque",
    "cast": "Conjuração",
    "guard": "Guarda",
    "special": "Especial",
    "none": "—",
}

_BOSS_AI = {
    AIType.BOSS_OGRE,
    AIType.BOSS_INQUISITOR,
    AIType.BOSS_MALAKAR,
    AIType.BOSS_GRUM,
    AIType.BOSS_GOLEM,
    AIType.BOSS_UIVADOR,
}


@dataclass
class IntentView:
    category: str
    label: str
    uninterruptible: bool
    interrupted: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "label": self.label,
            "uninterruptible": self.uninterruptible,
            "interrupted": self.interrupted,
        }


def map_action_to_category(action_type: str) -> str:
    return _ACTION_TO_CATEGORY.get(action_type, "special")


def is_uninterruptible(action_type: str, enemy) -> bool:
    if action_type in ("TRANSFORM", "SKIP"):
        return True
    # Phase transitions / ultimate-style boss specials stay readable but firm
    if action_type == "SUMMON" and getattr(enemy, "ai_type", None) in _BOSS_AI:
        return True
    return False


def build_intent_view(action_type: str, enemy, interrupted: bool = False) -> IntentView:
    cat = map_action_to_category(action_type)
    if interrupted:
        return IntentView("none", "Interrompido", False, True)
    return IntentView(
        category=cat,
        label=_CATEGORY_LABELS.get(cat, "Especial"),
        uninterruptible=is_uninterruptible(action_type, enemy),
        interrupted=False,
    )


def plan_action_for_enemy(enemy, primary_target, combat) -> Tuple[str, int, List[str]]:
    """Roll AI once and return the planned action tuple."""
    return enemy.select_action(primary_target, combat)


def interrupt_success_chance(player, enemy, bond_bonus: float = 0.0) -> float:
    """
    Skill-expressive band ~15–70%.
    Assumption (PRD open question): base 35% + 3% per AGI above 8; −15% vs bosses.
    bond_bonus: absolute modifier from Phase 2 Unison/Fracture (applied before clamp).
    """
    agi = getattr(player, "agilidade", 8)
    chance = 0.35 + (agi - 8) * 0.03 + float(bond_bonus or 0.0)
    if getattr(enemy, "ai_type", None) in _BOSS_AI:
        chance -= 0.15
    return max(0.15, min(0.70, chance))


def roll_interrupt(
    player, enemy, rng: Optional[random.Random] = None, bond_bonus: float = 0.0
) -> bool:
    rng = rng or random
    return rng.random() < interrupt_success_chance(player, enemy, bond_bonus=bond_bonus)


def intent_dict_for_enemy(enemy) -> Optional[Dict[str, Any]]:
    view: Optional[IntentView] = getattr(enemy, "intent_view", None)
    if view is None:
        return None
    return view.to_dict()
