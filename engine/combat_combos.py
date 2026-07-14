"""
Party combo detection and bonuses (PRD B2).

MVP: four class-pair combos. Both participants still execute their own
commands; a modest bonus is applied once when a pair matches.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Set, Tuple

from engine.constants import CharacterClass, StatusEffect


@dataclass(frozen=True)
class ComboMatcher:
    char_class: CharacterClass
    skill_names: Tuple[str, ...] = ()
    actions: Tuple[str, ...] = ("SKILL",)


@dataclass(frozen=True)
class ComboDefinition:
    combo_id: str
    name: str
    description: str
    matchers: Tuple[ComboMatcher, ComboMatcher]
    apply: Callable


def _skill_name(cmd) -> Optional[str]:
    if cmd is None or cmd.action != "SKILL":
        return None
    skill = cmd.value
    return getattr(skill, "name", None)


def _matches(player, cmd, matcher: ComboMatcher) -> bool:
    if player is None or cmd is None:
        return False
    if player.char_class != matcher.char_class:
        return False
    if cmd.action not in matcher.actions:
        return False
    if matcher.skill_names:
        return _skill_name(cmd) in matcher.skill_names
    return True


def _bonus_burn(combat, _a, _b, _ca, _cb):
    target = combat.get_first_alive_enemy()
    if not target or not target.is_alive():
        return
    target.status_effects[StatusEffect.QUEIMADO] = max(
        target.status_effects.get(StatusEffect.QUEIMADO, 0), 3
    )
    extra = max(8, int(target.max_hp * 0.06))
    res = target.take_damage(extra)
    combat.add_log(
        f"💥 COMBO Shatterfire! Queimadura reforçada e +{res['damage_taken']} dano de estilhaço!"
    )


def _bonus_cauterize(combat, a, b, _ca, _cb):
    target = combat.get_first_alive_enemy()
    if target and target.is_alive():
        extra = 18
        res = target.take_damage(extra)
        combat.add_log(
            f"💥 COMBO Cauterizar! Explosão de luz e veneno: +{res['damage_taken']} dano!"
        )
    for p in (a, b):
        for eff in (StatusEffect.ENVENENADO, StatusEffect.SANGRAMENTO, StatusEffect.QUEIMADO):
            if eff in p.status_effects:
                del p.status_effects[eff]
                combat.add_log(f"✨ {p.name} teve {eff.name_str} purificado pelo combo!")


def _bonus_thunderfang(combat, _a, _b, _ca, _cb):
    target = combat.get_first_alive_enemy()
    if not target or not target.is_alive():
        return
    extra = max(20, int(target.max_hp * 0.08))
    res = target.take_damage(extra + target.defense // 2)
    combat.add_log(f"💥 COMBO Presa do Trovão! Impacto preciso: +{res['damage_taken']} dano!")


def _bonus_aegis(combat, a, b, _ca, _cb):
    party = list(getattr(combat.state, "party", None) or [combat.player])
    for p in party:
        if p.hp > 0:
            p.status_effects[StatusEffect.PROTEGIDO] = max(
                p.status_effects.get(StatusEffect.PROTEGIDO, 0), 2
            )
    combat.add_log("💥 COMBO Corrente de Égide! A party recebe Proteção por 2 turnos!")


COMBO_DEFINITIONS: Tuple[ComboDefinition, ...] = (
    ComboDefinition(
        combo_id="shatterfire",
        name="Shatterfire",
        description="Golpe de guerreiro + Bola de Fogo",
        matchers=(
            ComboMatcher(
                CharacterClass.GUERREIRO,
                skill_names=("Golpe Poderoso", "Golpe Devastador"),
            ),
            ComboMatcher(CharacterClass.MAGO, skill_names=("Bola de Fogo",)),
        ),
        apply=_bonus_burn,
    ),
    ComboDefinition(
        combo_id="cauterize",
        name="Cauterizar",
        description="Lâmina venenosa + magia sagrada",
        matchers=(
            ComboMatcher(CharacterClass.LADINO, skill_names=("Lâmina Venenosa",)),
            ComboMatcher(
                CharacterClass.CLERIGO,
                skill_names=("Punição Divina", "Luz Sagrada", "Bênção Protetora"),
            ),
        ),
        apply=_bonus_cauterize,
    ),
    ComboDefinition(
        combo_id="thunderfang",
        name="Presa do Trovão",
        description="Ataque furtivo + Trovão Celestial",
        matchers=(
            ComboMatcher(CharacterClass.LADINO, skill_names=("Ataque Furtivo",)),
            ComboMatcher(CharacterClass.MAGO, skill_names=("Trovão Celestial",)),
        ),
        apply=_bonus_thunderfang,
    ),
    ComboDefinition(
        combo_id="aegis_chain",
        name="Corrente de Égide",
        description="Muralha de Ferro + Bênção Protetora",
        matchers=(
            ComboMatcher(CharacterClass.GUERREIRO, skill_names=("Muralha de Ferro",)),
            ComboMatcher(CharacterClass.CLERIGO, skill_names=("Bênção Protetora",)),
        ),
        apply=_bonus_aegis,
    ),
)


@dataclass
class ComboHit:
    definition: ComboDefinition
    player_a: Any
    player_b: Any
    cmd_a: Any
    cmd_b: Any


def find_combos(
    participants: Sequence[Tuple[Any, Any]],
    definitions: Sequence[ComboDefinition] = COMBO_DEFINITIONS,
) -> List[ComboHit]:
    """Greedy pairing: each player at most one combo per round."""
    remaining = list(enumerate(participants))
    hits: List[ComboHit] = []
    used: Set[int] = set()

    for definition in definitions:
        m0, m1 = definition.matchers
        found = None
        for i, (p, cmd) in remaining:
            if i in used:
                continue
            for j, (q, cmd2) in remaining:
                if j in used or j == i:
                    continue
                if _matches(p, cmd, m0) and _matches(q, cmd2, m1):
                    found = (i, j, p, q, cmd, cmd2)
                    break
                if _matches(p, cmd, m1) and _matches(q, cmd2, m0):
                    found = (i, j, p, q, cmd, cmd2)
                    break
            if found:
                break
        if not found:
            continue
        i, j, p, q, cmd, cmd2 = found
        hits.append(ComboHit(definition, p, q, cmd, cmd2))
        used.add(i)
        used.add(j)

    return hits


def apply_combo_hit(combat, hit: ComboHit) -> None:
    combat.add_log(f"⚔️ {hit.player_a.name} + {hit.player_b.name} → {hit.definition.name}!")
    hit.definition.apply(combat, hit.player_a, hit.player_b, hit.cmd_a, hit.cmd_b)
    try:
        from engine.dto import SoundEffect, VisualEffect

        if combat.adapter:
            combat.adapter.emit(SoundEffect("HIT_CRITICAL"))
            combat.adapter.emit(VisualEffect("crit_burst", target_id="global", duration=600))
    except Exception:
        pass
