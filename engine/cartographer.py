"""
Cartographer's Lie (PRD F6) — wrong map tax without scout class/companion.
"""
from __future__ import annotations

from engine.constants import CharacterClass
from engine.feature_flags import FLAGS
from engine import telemetry


def party_has_reliable_map(world) -> bool:
    party = getattr(world, "party", []) or []
    if any(getattr(p, "char_class", None) == CharacterClass.LADINO for p in party):
        return True
    # Ulfgar or Elena as scouts
    for p in party:
        comp = getattr(p, "companion", None)
        if not comp:
            continue
        name = (comp.name or "").lower()
        if "ulfgar" in name or "elena" in name:
            return True
    if world.state.get_flag("ulfgar_ajudado") or world.state.get_flag("elena_recrutada"):
        # companion may sit on leader only
        leader = getattr(world, "player", None)
        comp = getattr(leader, "companion", None) if leader else None
        if comp:
            name = (comp.name or "").lower()
            if "ulfgar" in name or "elena" in name:
                return True
    return False


def apply_cartographer_check(world) -> bool:
    """
    Returns True if the lie applied (hazard tax).
    Sets gelido map flags for chapter 9.
    """
    if not FLAGS.content_systems:
        return False
    if party_has_reliable_map(world):
        world.state.set_flag("map_reliable", True)
        world.state.set_flag("cartographer_lie", False)
        telemetry.track("cartographer_truth")
        return False

    world.state.set_flag("map_reliable", False)
    world.state.set_flag("cartographer_lie", True)
    world.state.set_flag("cold_debuff_active", True)
    telemetry.track("cartographer_lie")
    return True


def narrate_cartographer(world) -> None:
    import sys
    from engine.world import typewriter, press_any_key, clear_screen, print_centered

    clear_screen()
    print_centered("=== MAPA DO NORTE ===", None)
    if world.state.get_flag("cartographer_lie"):
        typewriter(
            "O mapa comprado em Vaelmoor marca uma trilha 'segura'. A neve conta outra história.",
            0.03,
        )
        typewriter(
            "Sem um batedor (Ladino) ou guia (Ulfgar/Elena), a party se atrasa na nevasca. O frio se aprofunda.",
            0.03,
        )
    else:
        typewriter(
            "Com um olho treinado no grupo, o mapa é corrigido: a trilha real contorna a fenda oculta.",
            0.03,
        )
    if "pytest" not in sys.modules:
        press_any_key()
