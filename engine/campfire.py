"""
Campfire / letters home (PRD E2) — optional between-chapter bonding.
"""
from __future__ import annotations

from typing import Dict

from engine.feature_flags import FLAGS
from engine import telemetry
from engine.party_meta import grant_bond


PROMPTS: Dict[str, str] = {
    "1": "Medo — o que a party teme no próximo capítulo",
    "2": "Piada — um momento leve ao redor do fogo",
    "3": "Confissão — um peso que alguém carrega",
    "4": "Pular o acampamento",
}


def run_campfire(world, *, chapter_label: str = "") -> None:
    if not FLAGS.content_systems:
        return
    # Match combat pre_boss_menu: do not consume scripted inputs under pytest
    import sys
    if "pytest" in sys.modules:
        return
    if world.state.get_flag(f"campfire_done_{chapter_label}"):
        return

    from engine.world import clear_screen, typewriter, print_centered, press_any_key

    clear_screen()
    print_centered("=== FOGUEIRA ===", None)
    typewriter("A noite desce. Alguém acende o fogo. Há espaço para falar — ou calar.\n", 0.03)

    choice = world.get_party_vote(PROMPTS, prompt="O que a party compartilha? ")
    if choice == "4" or choice not in PROMPTS:
        typewriter("\nVocês dormem em turnos, em silêncio prático.", 0.03)
        world.state.set_flag(f"campfire_done_{chapter_label}", True)
        press_any_key()
        return

    if choice == "1":
        typewriter("\nAs chamas dançam sobre rostos sérios. Nomear o medo não o afasta — mas une quem o ouve.", 0.03)
        grant_bond(world.state, "unison", 1, reason="campfire_fear")
        for p in world.party:
            p.hp = min(p.max_hp, p.hp + 5)
    elif choice == "2":
        typewriter("\nRisadas abafadas. Até o Vazio parece distante por um instante.", 0.03)
        grant_bond(world.state, "mercy", 1, reason="campfire_joke")
        for p in world.party:
            p.mp = min(p.max_mp, p.mp + 5)
    elif choice == "3":
        typewriter("\nUma confissão pesada cai nas brasas. Ninguém zomba. Alguém aperta o ombro de outro.", 0.03)
        grant_bond(world.state, "unison", 1, reason="campfire_confession")
        # Small lasting flag for narrative
        world.state.set_flag("campfire_confession", True)

    world.state.set_flag(f"campfire_done_{chapter_label}", True)
    telemetry.track("campfire", choice=choice)
    press_any_key()
