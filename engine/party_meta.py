"""
Party meta facade: bonds + debts + corruption (PRD Phase 2).

Orchestrates grants from flags/votes and provides combat queries.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from engine import bonds as bonds_mod
from engine import debts as debts_mod
from engine import corruption as corruption_mod
from engine.feature_flags import FLAGS
from engine import telemetry


def default_meta() -> Dict[str, Any]:
    return {
        "bonds": bonds_mod.empty_bonds(),
        "debts": debts_mod.empty_debts(),
        "corruption": 0,
        "granted_keys": [],  # idempotent grant markers
        "mercy_revive_used_combat": False,
        "companion_warned_corruption": False,
    }


def ensure_meta(state) -> Dict[str, Any]:
    meta = getattr(state, "party_meta", None)
    if not isinstance(meta, dict):
        meta = default_meta()
        state.party_meta = meta
    # Normalize shape
    meta.setdefault("bonds", bonds_mod.empty_bonds())
    meta["bonds"] = bonds_mod.normalize_bonds(meta["bonds"])
    meta.setdefault("debts", [])
    meta["debts"] = debts_mod.normalize_debts(meta["debts"])
    meta.setdefault("corruption", 0)
    meta["corruption"] = corruption_mod.normalize_corruption(meta["corruption"])
    if not isinstance(meta.get("granted_keys"), list):
        meta["granted_keys"] = []
    meta.setdefault("mercy_revive_used_combat", False)
    meta.setdefault("companion_warned_corruption", False)
    return meta


def _is_ephemeral_grant_key(key: str) -> bool:
    """Vote/seq keys must never be persisted (P2-002 / P2-003)."""
    k = str(key)
    return k.startswith("vote_event:") or k.startswith("vote:") or k == "_vote_seq"


def _sanitize_granted_keys(keys: Any) -> List[str]:
    if not isinstance(keys, list):
        return []
    return [str(k) for k in keys if not _is_ephemeral_grant_key(k)]


def serialize_meta(state) -> Dict[str, Any]:
    meta = ensure_meta(state)
    # Drop ephemeral vote keys so saves cannot poison post-load bond grants
    meta["granted_keys"] = _sanitize_granted_keys(meta.get("granted_keys"))
    meta.pop("_vote_seq", None)
    return {
        "bonds": dict(meta["bonds"]),
        "debts": list(meta["debts"]),
        "corruption": int(meta["corruption"]),
        "granted_keys": list(meta["granted_keys"]),
        "companion_warned_corruption": bool(meta.get("companion_warned_corruption")),
    }


def deserialize_meta(state, raw: Any) -> None:
    base = default_meta()
    if isinstance(raw, dict):
        base["bonds"] = bonds_mod.normalize_bonds(raw.get("bonds"))
        base["debts"] = debts_mod.normalize_debts(raw.get("debts"))
        base["corruption"] = corruption_mod.normalize_corruption(raw.get("corruption"))
        base["granted_keys"] = _sanitize_granted_keys(raw.get("granted_keys") or [])
        base["companion_warned_corruption"] = bool(raw.get("companion_warned_corruption"))
    state.party_meta = base
    # One-time migration from legacy flags + repair known Phase 2 false positives
    bootstrap_from_legacy_flags(state)
    repair_phase2_meta(state)


def _has_grant(meta: Dict[str, Any], key: str) -> bool:
    return key in meta.get("granted_keys", [])


def _mark_grant(meta: Dict[str, Any], key: str) -> None:
    keys: List[str] = meta.setdefault("granted_keys", [])
    if key not in keys:
        keys.append(key)


def _emit(state, msg: str) -> None:
    adapter = getattr(state, "adapter", None)
    if not adapter:
        return
    try:
        from engine.dto import NarrativeText

        adapter.emit(NarrativeText(msg))
    except Exception:
        pass


def _chapter(state) -> int:
    return int(getattr(state, "current_chapter", 1) or 1)


def grant_bond(state, bond_type: str, amount: int = 1, *, reason: str = "") -> None:
    if not FLAGS.party_bonds:
        return
    meta = ensure_meta(state)
    before = meta["bonds"].get(bond_type, 0)
    after = bonds_mod.grant_bond(meta["bonds"], bond_type, amount)
    if after > before:
        label = bonds_mod.BOND_LABELS.get(bond_type, bond_type)
        _emit(state, f"🔗 Vínculo da party: {label} agora está no nível {after}.")
        telemetry.track("bond_granted", bond=bond_type, strength=after, reason=reason)


def grant_debt(state, debt_id: str, *, reason: str = "") -> None:
    if not FLAGS.party_bonds:
        return
    meta = ensure_meta(state)
    entry = debts_mod.grant_debt(meta["debts"], debt_id, chapter=_chapter(state))
    if entry:
        _emit(state, f"📜 Dívida registrada: {entry['title']} — {entry['source']}")
        telemetry.track("debt_granted", debt_id=debt_id, reason=reason)


def add_corruption(state, amount: int, *, reason: str = "") -> None:
    if not FLAGS.void_corruption:
        return
    if amount == 0:
        return
    meta = ensure_meta(state)
    before = meta["corruption"]
    before_tier = corruption_mod.tier_for(before)["id"]
    meta["corruption"] = corruption_mod.add_corruption(before, amount)
    after = meta["corruption"]
    after_tier = corruption_mod.tier_for(after)["id"]
    if after != before:
        _emit(
            state,
            f"🌑 Corrupção do Vazio: {before} → {after} ({corruption_mod.tier_for(after)['label']}).",
        )
        telemetry.track("corruption_gain", amount=amount, value=after, reason=reason)
    if after_tier != before_tier and after > before:
        _emit(state, f"⚠️ Novo patamar de corrupção: {corruption_mod.tier_for(after)['label']}.")
    _maybe_companion_warning(state, meta)


def _maybe_companion_warning(state, meta: Dict[str, Any]) -> None:
    if meta.get("companion_warned_corruption"):
        return
    if corruption_mod.tier_for(meta["corruption"])["id"] not in ("shadowed", "void_touched"):
        return
    player = getattr(state, "player", None)
    companion = getattr(player, "companion", None) if player else None
    if not companion:
        return
    meta["companion_warned_corruption"] = True
    _emit(
        state,
        f"💬 {companion.name} observa a party com inquietação: "
        f"\"Isso… não é só poder. O Vazio está em vocês.\"",
    )
    telemetry.track("corruption_companion_warning")


def observe_flag(state, key: str, value: Any) -> None:
    """Called from GameState.set_flag after write."""
    if not (FLAGS.party_bonds or FLAGS.void_corruption):
        return
    meta = ensure_meta(state)
    # Normalize truthy
    truthy = bool(value)

    # --- Debts + Mercy ---
    if FLAGS.party_bonds and truthy:
        if key in ("poupou_ogro", "ogro_poupado") and not _has_grant(meta, "flag:spare_ogre"):
            _mark_grant(meta, "flag:spare_ogre")
            grant_debt(state, "drogg_spared", reason=key)
            grant_bond(state, "mercy", 1, reason=key)
        if key in ("goblin_ajudado", "ajudou_goblin") and not _has_grant(meta, "flag:aid_goblin"):
            _mark_grant(meta, "flag:aid_goblin")
            grant_debt(state, "zix_aided", reason=key)
            grant_bond(state, "mercy", 1, reason=key)
        if key in ("millhaven_salva",) and not _has_grant(meta, "flag:millhaven"):
            _mark_grant(meta, "flag:millhaven")
            grant_debt(state, "millhaven_child", reason=key)
            grant_bond(state, "mercy", 1, reason=key)

    # --- Corruption sources ---
    # NOTE: poupou_ogro=False is used as a pre-fight default in enter_cabin — it is NOT
    # a kill decision. Kill corruption is applied only via record_ogre_killed() (P2-001).
    if FLAGS.void_corruption:
        if key in ("lacre_sombrio",) and truthy and not _has_grant(meta, "flag:lacre"):
            _mark_grant(meta, "flag:lacre")
            add_corruption(state, 25, reason="lacre_sombrio")


def record_ogre_killed(state) -> None:
    """
    Explicit kill outcome for Drogg (P2-001).
    Call only from the ogre mercy dialogue kill branch — never from flag defaults.
    """
    if not FLAGS.void_corruption:
        return
    meta = ensure_meta(state)
    if _has_grant(meta, "flag:kill_ogre"):
        return
    if _has_grant(meta, "flag:spare_ogre"):
        return
    if state.get_flag("poupou_ogro") or state.get_flag("ogro_poupado"):
        return
    _mark_grant(meta, "flag:kill_ogre")
    add_corruption(state, 5, reason="killed_ogre")


def observe_vote(state, votes: Dict[str, Any], winning_choice: str) -> None:
    """
    Multiplayer vote outcome.
    Unison: all cast votes equal (and ≥2 voters).
    Fracture: ≥2 voters and not unanimous.

    Called once per vote resolution from WorldManager.get_party_vote.
    Does not persist ephemeral keys (P2-002 / P2-003).
    """
    if not FLAGS.party_bonds:
        return
    if not votes or len(votes) < 2:
        return
    values = list(votes.values())
    unanimous = all(v == values[0] for v in values)
    if unanimous:
        grant_bond(state, "unison", 1, reason="unanimous_vote")
    else:
        grant_bond(state, "fracture", 1, reason="split_vote")


def bootstrap_from_legacy_flags(state) -> None:
    """Idempotent: import existing narrative flags into meta without spam."""
    meta = ensure_meta(state)
    # Silent grants — no narrative flood on load
    silent = not FLAGS.party_bonds and not FLAGS.void_corruption

    def _silent_debt(debt_id: str, grant_key: str):
        if _has_grant(meta, grant_key):
            return
        if debts_mod.find_debt(meta["debts"], debt_id):
            _mark_grant(meta, grant_key)
            return
        if FLAGS.party_bonds:
            debts_mod.grant_debt(meta["debts"], debt_id, chapter=_chapter(state))
            bonds_mod.grant_bond(meta["bonds"], "mercy", 1)
        _mark_grant(meta, grant_key)

    if state.get_flag("poupou_ogro") or state.get_flag("ogro_poupado"):
        _silent_debt("drogg_spared", "flag:spare_ogre")
    if state.get_flag("goblin_ajudado") or state.get_flag("ajudou_goblin"):
        _silent_debt("zix_aided", "flag:aid_goblin")
    if state.get_flag("millhaven_salva"):
        _silent_debt("millhaven_child", "flag:millhaven")
    if state.get_flag("lacre_sombrio") and not _has_grant(meta, "flag:lacre"):
        if FLAGS.void_corruption:
            meta["corruption"] = corruption_mod.add_corruption(meta["corruption"], 25)
        _mark_grant(meta, "flag:lacre")


def repair_phase2_meta(state) -> None:
    """
    Repair early Phase 2 saves affected by P2-001 / P2-002 / P2-003.

    - Strip ephemeral vote keys from granted_keys.
    - Undo false kill-corruption when spare was also granted, or when the
      ogre mercy dialogue never ran (init False only).
    """
    meta = ensure_meta(state)
    meta["granted_keys"] = _sanitize_granted_keys(meta.get("granted_keys"))
    meta.pop("_vote_seq", None)

    has_kill = _has_grant(meta, "flag:kill_ogre")
    has_spare = _has_grant(meta, "flag:spare_ogre") or bool(
        state.get_flag("poupou_ogro") or state.get_flag("ogro_poupado")
    )
    dialogue_done = bool(state.get_flag("ogre_dialogue_triggered"))

    false_positive_kill = has_kill and (has_spare or not dialogue_done)
    if false_positive_kill:
        meta["granted_keys"] = [k for k in meta["granted_keys"] if k != "flag:kill_ogre"]
        # Remove the erroneous +5 once (idempotent: only if kill grant was present)
        if meta["corruption"] >= 5:
            meta["corruption"] = corruption_mod.clamp_corruption(meta["corruption"] - 5)
        # Ensure spare debt/bond exist if flags say so (bootstrap may have run already)
        if has_spare and not _has_grant(meta, "flag:spare_ogre"):
            _mark_grant(meta, "flag:spare_ogre")


def on_combat_start(state) -> None:
    meta = ensure_meta(state)
    meta["mercy_revive_used_combat"] = False


def try_mercy_revive(state, player) -> bool:
    """
    If Mercy bond active and not yet used this combat, restore player to 1 HP.
    Returns True if revive applied.
    """
    if not FLAGS.party_bonds:
        return False
    meta = ensure_meta(state)
    if not bonds_mod.mercy_revive_allowed(meta["bonds"]):
        return False
    if meta.get("mercy_revive_used_combat"):
        return False
    if player.hp > 0:
        return False
    # Do not revive if entire party is already wiped (checked by caller after loop)
    meta["mercy_revive_used_combat"] = True
    player.hp = 1
    _emit(
        state,
        f"🔗 Vínculo de Misericórdia! {player.name} recusa a queda e permanece com 1 HP!",
    )
    telemetry.track("bond_mercy_revive", player=getattr(player, "name", "?"))
    return True


def interrupt_chance_bonus(state) -> float:
    if not FLAGS.party_bonds:
        return 0.0
    meta = ensure_meta(state)
    return bonds_mod.interrupt_bonus_from_bonds(meta["bonds"])


def offense_mult(state) -> float:
    if not FLAGS.void_corruption:
        return 1.0
    return corruption_mod.offense_multiplier(ensure_meta(state)["corruption"])


def heal_mult(state) -> float:
    if not FLAGS.void_corruption:
        return 1.0
    return corruption_mod.heal_multiplier(ensure_meta(state)["corruption"])


def damage_taken_mult(state) -> float:
    if not FLAGS.void_corruption:
        return 1.0
    return corruption_mod.damage_taken_multiplier(ensure_meta(state)["corruption"])


def public_view(state) -> Dict[str, Any]:
    meta = ensure_meta(state)
    return {
        "bonds": bonds_mod.bonds_public_view(meta["bonds"]),
        "debts": debts_mod.debts_public_view(meta["debts"]),
        "corruption": corruption_mod.public_view(meta["corruption"]),
        "features": {
            "bonds": FLAGS.party_bonds,
            "corruption": FLAGS.void_corruption,
        },
    }
