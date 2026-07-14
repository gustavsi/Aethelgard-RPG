"""
Abstract terrain as third faction (PRD B3) — stage modifiers, not a tile grid.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from engine.feature_flags import FLAGS
from engine import telemetry

# location/chapter key -> terrain profile
PROFILES: Dict[str, Dict[str, Any]] = {
    "oakhaven_siege": {
        "id": "rubble",
        "label": "Escombros",
        "desc": "Terreno irregular: −5% esquiva.",
        "dodge_penalty": 0.05,
    },
    "cavernas": {
        "id": "dark",
        "label": "Escuridão",
        "desc": "Sem lâmpada: erros de ataque aumentam levemente.",
        "miss_bonus": 0.05,
    },
    "gelido": {
        "id": "void_frost",
        "label": "Geada do Vazio",
        "desc": "Defender por muito tempo arrisca congelamento.",
        "defend_freeze_chance": 0.15,
    },
    "vaelmoor": {
        "id": "deck",
        "label": "Convés Instável",
        "desc": "Agilidade conta: bônus leve para ladinos.",
        "agility_bonus_class": "Ladino",
    },
    "default": {
        "id": "plain",
        "label": "Campo Aberto",
        "desc": "Sem modificadores especiais.",
    },
}


def terrain_for_location(location: Optional[str], state=None) -> Dict[str, Any]:
    if not FLAGS.content_systems:
        return PROFILES["default"]
    loc = (location or "").lower()
    if state and state.get_flag("cartographer_lie"):
        return PROFILES["gelido"]
    if "oakhaven" in loc and state and state.get_flag("oakhaven_defendida") is False:
        return PROFILES.get("oakhaven_siege", PROFILES["default"])
    if "cavern" in loc or loc in ("cavernas", "whispering"):
        return PROFILES["cavernas"]
    if "gel" in loc or "ice" in loc or loc in ("gelido", "kragmoor"):
        return PROFILES["gelido"]
    if "vael" in loc or "porto" in loc:
        return PROFILES["vaelmoor"]
    return PROFILES["default"]


def attach_terrain_to_combat(combat) -> None:
    if not FLAGS.content_systems:
        return
    loc = getattr(combat.state, "current_location", None)
    profile = terrain_for_location(loc, combat.state)
    combat.terrain = profile
    combat.add_log(f"🗺️ Terreno: {profile['label']} — {profile['desc']}")
    telemetry.track("terrain_applied", terrain=profile["id"])


def public_terrain(combat) -> Optional[Dict[str, Any]]:
    t = getattr(combat, "terrain", None)
    if not t:
        return None
    return {"id": t.get("id"), "label": t.get("label"), "desc": t.get("desc")}
