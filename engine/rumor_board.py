"""
Rumor board — party commits to one side path (PRD D2).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from engine.feature_flags import FLAGS
from engine import telemetry

# id -> (title, description, commit_flag, expire_flag for others)
RUMORS: List[Tuple[str, str, str, str]] = [
    (
        "smugglers",
        "Rotas da Maré Negra",
        "Contrabanistas no litoral falam de um porto-fantasma. Compromisso: investigar rotas em Vaelmoor.",
        "rumor_smugglers",
    ),
    (
        "mines",
        "Eco nas Minas",
        "Anões de Kragmoor pedem escolta. Compromisso: priorizar as minas quando chegarem.",
        "rumor_mines",
    ),
    (
        "ice",
        "Silêncio de Gelo",
        "Caçadores falam de uma fenda no norte. Compromisso: acelerar para o Gélido Silêncio.",
        "rumor_ice",
    ),
]


def is_committed(state) -> bool:
    return bool(state.get_flag("rumor_committed"))


def present_rumor_board(world) -> None:
    if not FLAGS.content_systems:
        return
    if is_committed(world.state):
        return

    from engine.world import clear_screen, typewriter, print_centered, press_any_key

    clear_screen()
    print_centered("=== QUADRO DE RUMORES ===", None)
    typewriter(
        "No mural da praça, três bilhetes competem por atenção. A party só pode se comprometer com um.",
        0.03,
    )
    typewriter("Os outros envelhecerão — ou piorarão — sem vocês.\n", 0.03)

    options: Dict[str, str] = {}
    for i, (rid, title, desc, _flag) in enumerate(RUMORS, start=1):
        options[str(i)] = f"{title}: {desc}"
    options[str(len(RUMORS) + 1)] = "Ignorar o quadro por agora"

    choice = world.get_party_vote(options, prompt="Com qual rumor a party se compromete? ")
    if choice == str(len(RUMORS) + 1) or choice not in options:
        typewriter("\nVocês deixam os bilhetes balançarem ao vento. Por enquanto.", 0.03)
        press_any_key()
        return

    idx = int(choice) - 1
    rid, title, desc, flag = RUMORS[idx]
    world.state.set_flag("rumor_committed", True)
    world.state.set_flag(flag, True)
    world.state.set_flag("rumor_active_id", rid)
    # Expire others
    for j, (oid, _t, _d, oflag) in enumerate(RUMORS):
        if j != idx:
            world.state.set_flag(f"{oflag}_expired", True)

    typewriter(f"\n📜 Compromisso selado: {title}.", 0.03)
    typewriter("A party marca o mapa. Os outros rumores começam a amarelar no mural.", 0.03)
    press_any_key()
    telemetry.track("rumor_committed", rumor=rid)
