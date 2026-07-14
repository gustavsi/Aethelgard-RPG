"""
Downed roles (PRD B4) — limited actions when HP <= 0.
"""
from __future__ import annotations

from engine.feature_flags import FLAGS
from engine import telemetry
from engine.party_meta import add_corruption


def downed_menu_options(state) -> dict:
    if not FLAGS.content_systems:
        return {}
    opts = {
        "wait": "⌛ Aguardar (sem ação)",
        "shout": "📢 Gritar (aliado +ataque no próximo golpe)",
    }
    # Dark bargain only if corruption system on and not used this combat
    meta = getattr(state, "party_meta", {}) or {}
    if FLAGS.void_corruption and not meta.get("dark_bargain_used_combat"):
        opts["bargain"] = "🌑 Pacto Sombrio (1 HP agora; +10 Corrupção)"
    return opts


def execute_downed_action(combat, player, action: str) -> None:
    if not FLAGS.content_systems:
        return
    if player.hp > 0:
        return
    if action == "wait":
        combat.add_log(f"{player.name} permanece caído, respirando com dificuldade.")
        telemetry.track("downed_wait")
        return
    if action == "shout":
        combat.state.set_flag("shout_buff_next", True)
        combat.state.set_flag("shout_buff_from", player.name)
        combat.add_log(f"📢 {player.name} grita com a última força! O próximo aliado a atacar golpeia com fúria!")
        telemetry.track("downed_shout")
        return
    if action == "bargain":
        meta = getattr(combat.state, "party_meta", None) or {}
        if meta.get("dark_bargain_used_combat"):
            combat.add_log(f"{player.name} tenta outro pacto, mas o Vazio já cobrou o preço deste combate.")
            return
        try:
            from engine.party_meta import ensure_meta
            ensure_meta(combat.state)["dark_bargain_used_combat"] = True
        except Exception:
            pass
        player.hp = 1
        add_corruption(combat.state, 10, reason="dark_bargain")
        combat.add_log(f"🌑 {player.name} assina um pacto silencioso e ergue-se com 1 HP — o Vazio sorri.")
        telemetry.track("downed_bargain")
