"""
Relic attunement (PRD C2) — usage counters mutate legendary flavor/stats lightly.
"""
from __future__ import annotations

from typing import Any, Dict

from engine.feature_flags import FLAGS
from engine import telemetry


def _meta(state) -> Dict[str, Any]:
    from engine.party_meta import ensure_meta
    m = ensure_meta(state)
    att = m.setdefault("relic_attunement", {})
    if not isinstance(att, dict):
        m["relic_attunement"] = {}
        att = m["relic_attunement"]
    return att


def record_relic_use(state, item_id: str, kind: str = "use") -> None:
    if not FLAGS.content_systems or not item_id:
        return
    att = _meta(state)
    entry = att.setdefault(item_id, {"uses": 0, "heals": 0, "crits": 0, "stage": 0})
    entry["uses"] = int(entry.get("uses", 0)) + 1
    if kind == "heal":
        entry["heals"] = int(entry.get("heals", 0)) + 1
    if kind == "crit":
        entry["crits"] = int(entry.get("crits", 0)) + 1
    _maybe_advance(state, item_id, entry)


def _maybe_advance(state, item_id: str, entry: dict) -> None:
    stage = int(entry.get("stage", 0))
    if stage >= 2:
        return
    uses = int(entry.get("uses", 0))
    heals = int(entry.get("heals", 0))
    crits = int(entry.get("crits", 0))
    new_stage = stage
    path = entry.get("path")
    if stage == 0 and uses >= 3:
        new_stage = 1
        if heals >= crits:
            path = "mercy"
        else:
            path = "blood"
        entry["path"] = path
    elif stage == 1 and uses >= 8:
        new_stage = 2
    if new_stage != stage:
        entry["stage"] = new_stage
        state.set_flag(f"relic_{item_id}_stage", new_stage)
        if path:
            state.set_flag(f"relic_{item_id}_path", path)
        telemetry.track("relic_attune", item=item_id, stage=new_stage, path=path)


def apply_attunement_to_weapon(state, weapon) -> None:
    """Mutate weapon stats in place based on attunement (small)."""
    if not weapon or not FLAGS.content_systems:
        return
    wid = getattr(weapon, "id", None)
    if not wid:
        return
    att = _meta(state).get(wid) or {}
    stage = int(att.get("stage", 0))
    path = att.get("path")
    if stage <= 0:
        return
    base = getattr(weapon, "attack_power", 0) or 0
    if path == "blood" and stage >= 1:
        weapon.attack_power = base + 2 * stage
        if stage >= 2 and "Sangue" not in (weapon.name or ""):
            weapon.name = f"{weapon.name} (Sussurro de Sangue)"
    elif path == "mercy" and stage >= 1:
        # mercy weapons slightly weaker attack, flag for heal bonus elsewhere
        weapon.attack_power = max(1, base + stage)
        if stage >= 2 and "Misericórdia" not in (weapon.name or ""):
            weapon.name = f"{weapon.name} (Fio Misericordioso)"
