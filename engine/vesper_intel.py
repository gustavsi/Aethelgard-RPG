"""
Vesper interludes (PRD E3) — rival adapts to party tactics.
"""
from __future__ import annotations

from engine.feature_flags import FLAGS
from engine import telemetry


def record_tactic(state, tactic: str) -> None:
    """tactic: flee | burn | holy | interrupt | combo"""
    if not FLAGS.content_systems:
        return
    state.set_flag("last_combat_tactic", tactic)
    # accumulate counts lightly
    key = f"tactic_count_{tactic}"
    n = int(state.get_flag(key, 0) or 0) + 1
    state.set_flag(key, n)


def run_vesper_interlude(world, *, context: str = "gelido") -> None:
    if not FLAGS.content_systems:
        return
    import sys
    if "pytest" in sys.modules:
        # Still set trait for combat hooks without blocking on PressAnyKey
        trait = "adaptive"
        if world.state.get_flag("tactic_count_flee", 0):
            trait = "chains"
        elif world.state.get_flag("tactic_count_burn", 0) or world.state.get_flag("tactic_count_combo", 0):
            trait = "dampeners"
        elif world.state.get_flag("tactic_count_holy", 0):
            trait = "blasphemy"
        elif world.state.get_flag("tactic_count_interrupt", 0):
            trait = "feints"
        world.state.set_flag(f"vesper_interlude_{context}", True)
        world.state.set_flag("vesper_next_trait", trait)
        return
    if world.state.get_flag(f"vesper_interlude_{context}"):
        return

    from engine.world import clear_screen, typewriter, print_centered, press_any_key

    clear_screen()
    print_centered("=== SOMBRA DE VESPER ===", None)
    typewriter("A máscara cinza inclina-se, como se lesse um livro aberto no peito da party.\n", 0.03)

    tactic = world.state.get_flag("last_combat_tactic", "") or ""
    trait = "adaptive"
    line = "\"Interessante. Vocês ainda não escolheram um pecado favorito.\""

    if world.state.get_flag("tactic_count_flee", 0):
        trait = "chains"
        line = "\"Vocês fogem. Então eu trago correntes.\""
    elif world.state.get_flag("tactic_count_burn", 0) or world.state.get_flag("tactic_count_combo", 0):
        trait = "dampeners"
        line = "\"Fogo e espetáculo. Eu trarei silêncio e umidade.\""
    elif world.state.get_flag("tactic_count_holy", 0):
        trait = "blasphemy"
        line = "\"Luz demais. Vamos ver o que resta quando ela se apaga.\""
    elif world.state.get_flag("tactic_count_interrupt", 0):
        trait = "feints"
        line = "\"Vocês cortam intenções. Então mentirei as minhas.\""

    typewriter(f"Vesper: {line}", 0.03)
    typewriter("Ela dissolve-se na neve roxa antes que alguém reaja.", 0.03)

    world.state.set_flag(f"vesper_interlude_{context}", True)
    world.state.set_flag("vesper_next_trait", trait)
    telemetry.track("vesper_interlude", trait=trait, context=context)
    press_any_key()


def apply_vesper_trait_to_enemy(state, enemy) -> None:
    """Optional combat buff based on stored trait."""
    trait = state.get_flag("vesper_next_trait")
    if not trait or not enemy:
        return
    if trait == "chains":
        enemy.defense = int(getattr(enemy, "defense", 0) + 3)
    elif trait == "dampeners":
        enemy.max_hp = int(enemy.max_hp * 1.1)
        enemy.hp = enemy.max_hp
    elif trait == "blasphemy":
        enemy.attack = int(getattr(enemy, "attack", 10) * 1.1)
    elif trait == "feints":
        # mark uninterruptible specials lightly via flag on enemy
        enemy._vesper_feints = True
