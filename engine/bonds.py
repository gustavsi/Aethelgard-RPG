"""
Party-global bond strengths (PRD A1).

Types: mercy, unison, fracture — each capped at BOND_MAX.
Mechanical effects are queried by combat; grants go through party_meta.
"""
from __future__ import annotations

from typing import Any, Dict, List

BOND_TYPES = ("mercy", "unison", "fracture")
BOND_MAX = 3

BOND_LABELS = {
    "mercy": "Misericórdia",
    "unison": "Uníssono",
    "fracture": "Fratura",
}

BOND_DESCRIPTIONS = {
    "mercy": "A party escolhe poupar e proteger. Uma vez por combate, o primeiro aliado a cair é erguido com 1 HP.",
    "unison": "Decisões unânimes. Bônus de +8% em interrupções.",
    "fracture": "Votos divididos. Pequena penalidade (−5%) em interrupções.",
}


def empty_bonds() -> Dict[str, int]:
    return {k: 0 for k in BOND_TYPES}


def clamp_strength(value: int) -> int:
    return max(0, min(BOND_MAX, int(value)))


def grant_bond(bonds: Dict[str, int], bond_type: str, amount: int = 1) -> int:
    """Increase bond; returns new strength."""
    if bond_type not in BOND_TYPES:
        return bonds.get(bond_type, 0)
    bonds[bond_type] = clamp_strength(bonds.get(bond_type, 0) + amount)
    return bonds[bond_type]


def normalize_bonds(raw: Any) -> Dict[str, int]:
    out = empty_bonds()
    if not isinstance(raw, dict):
        return out
    for k in BOND_TYPES:
        if k in raw:
            out[k] = clamp_strength(raw[k])
    return out


def bonds_public_view(bonds: Dict[str, int]) -> List[Dict[str, Any]]:
    """UI-friendly list (only non-zero or all with strength)."""
    view = []
    for k in BOND_TYPES:
        s = bonds.get(k, 0)
        view.append(
            {
                "id": k,
                "name": BOND_LABELS[k],
                "strength": s,
                "max": BOND_MAX,
                "description": BOND_DESCRIPTIONS[k],
                "active": s > 0,
            }
        )
    return view


def interrupt_bonus_from_bonds(bonds: Dict[str, int]) -> float:
    """Absolute modifier to interrupt chance (before clamp)."""
    bonus = 0.0
    if bonds.get("unison", 0) >= 1:
        bonus += 0.08
    if bonds.get("fracture", 0) >= 1:
        bonus -= 0.05
    return bonus


def mercy_revive_allowed(bonds: Dict[str, int]) -> bool:
    return bonds.get("mercy", 0) >= 1
