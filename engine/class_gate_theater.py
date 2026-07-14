"""
Class-gate theater (PRD A2): multi-role approaches with soft-fail forks.

Ideal class → full success flag.
Missing ideal but another class present → assist path (cost, partial flag).
Otherwise → hard path (caller-defined combat/debuff).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from engine.constants import CharacterClass
from engine.feature_flags import FLAGS
from engine import telemetry


@dataclass(frozen=True)
class GateApproach:
    key: str
    label: str
    ideal_class: Optional[CharacterClass]
    success_flag: str
    success_lines: tuple
    assist_lines: tuple
    assist_cost: Optional[tuple] = None  # ("hp"|"mp"|"gold", amount, reason)


def party_has_class(party, char_class: CharacterClass) -> bool:
    return any(getattr(p, "char_class", None) == char_class for p in party)


def any_class_present(party) -> bool:
    return len(party) > 0


def run_gate_theater(
    world,
    *,
    title: str,
    intro_lines: List[str],
    approaches: List[GateApproach],
    hard_path_fn: Callable[[], None],
    hard_path_label: str = "Forçar o caminho difícil (sem especialidade)",
) -> str:
    """
    Returns: "success" | "assist" | "hard"
    """
    from engine.world import clear_screen, typewriter, print_centered, press_any_key

    if not FLAGS.content_systems:
        # Fallback: original-style first ideal class only via vote
        pass

    clear_screen()
    print_centered(f"=== {title} ===", None)
    for line in intro_lines:
        typewriter(line, 0.03)

    options: Dict[str, str] = {}
    for i, ap in enumerate(approaches, start=1):
        options[str(i)] = ap.label
    hard_key = str(len(approaches) + 1)
    options[hard_key] = hard_path_label

    choice = world.get_party_vote(options, prompt="Como a party aborda o desafio? ")
    if choice == hard_key or choice not in {str(i) for i in range(1, len(approaches) + 1)}:
        hard_path_fn()
        telemetry.track("class_gate_hard", gate=title)
        return "hard"

    ap = approaches[int(choice) - 1]
    party = world.party

    import sys
    _skip_key = "pytest" in sys.modules

    if ap.ideal_class and party_has_class(party, ap.ideal_class):
        clear_screen()
        for line in ap.success_lines:
            typewriter(line, 0.03)
        world.state.set_flag(ap.success_flag, True)
        if not _skip_key:
            press_any_key()
        telemetry.track("class_gate_success", gate=title, approach=ap.key)
        return "success"

    # Missing ideal class: pay approach cost (legacy resource loss) then optional hard_path.
    clear_screen()
    typewriter(
        "\nSem a especialidade ideal para esta abordagem, a party enfrenta o pior do obstáculo.",
        0.03,
    )
    for line in ap.assist_lines:
        typewriter(line, 0.03)
    if ap.assist_cost:
        kind, amount, reason = ap.assist_cost
        if kind == "hp":
            world.consume_resource(world.player, "hp", amount, reason)
        elif kind == "mp":
            world.consume_resource(world.player, "mp", amount, reason)
        elif kind == "gold":
            world.consume_resource(world.player, "gold", amount, reason)
    world.state.set_flag(f"{ap.success_flag}_attempted", True)
    if not _skip_key:
        press_any_key()
    # Chapter-specific hard forks (e.g. ch9 extra combat). For ch4, cost is the fork.
    # Call hard_path only when it is not a pure duplicate cost (caller decides).
    hard_path_fn()
    telemetry.track("class_gate_hard", gate=title, approach=ap.key)
    return "hard"
