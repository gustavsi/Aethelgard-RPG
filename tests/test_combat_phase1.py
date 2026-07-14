"""Unit tests for PRD Phase 1: intent/interrupt + combos."""
import random

from engine.combat import CombatSystem, CombatPhase, Command
from engine.combat_combos import find_combos, COMBO_DEFINITIONS
from engine.combat_intent import interrupt_success_chance, roll_interrupt, build_intent_view
from engine.constants import CharacterClass, StatusEffect, AIType
from engine.player import Player
from engine.state import GameState
from engine.enemy import Enemy
from engine import telemetry
from engine.skills import get_class_skills


class DummyAdapter:
    def __init__(self):
        self.emitted = []
        self.input_queue = None

    def emit(self, e):
        self.emitted.append(e)

    def on_state_change(self, state):
        pass

    def broadcast(self, payload):
        pass


def _enemy(name="Lobo", hp=80, atk=8, defense=2):
    e = Enemy(name, hp, atk, defense, 10, 5, AIType.AGGRESSIVE)
    e.idx = 0
    return e


def test_plan_enemy_intents_sets_view():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p)
    st.party = [p]
    ad = DummyAdapter()
    c = CombatSystem(st, [_enemy()], adapter=ad)
    c.plan_enemy_intents()
    e = c.enemies[0]
    assert e.planned_action is not None
    assert e.intent_view is not None
    assert e.intent_view.category in ("attack", "cast", "guard", "special", "none")
    d = c.state.combat_state
    c.sync_state()
    assert c.state.combat_state["enemies"][0]["intent"] is not None


def test_interrupt_success_cancels_intent():
    p = Player("A", CharacterClass.LADINO)
    p.agilidade = 20  # high interrupt chance
    st = GameState(p)
    st.party = [p]
    ad = DummyAdapter()
    c = CombatSystem(st, [_enemy()], adapter=ad)
    c.plan_enemy_intents()
    e = c.enemies[0]
    # Force interruptable attack intent
    e.planned_action = ("ATTACK", 10, ["prep"])
    e.intent_view = build_intent_view("ATTACK", e)
    # Force success via monkeypatch
    import engine.combat as combat_mod
    original = combat_mod.roll_interrupt
    combat_mod.roll_interrupt = lambda *a, **k: True
    try:
        c.execute_interrupt(p, 0)
    finally:
        combat_mod.roll_interrupt = original
    assert e.planned_action[0] == "SKIP"
    assert e.intent_view.interrupted is True


def test_interrupt_uninterruptible():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p)
    st.party = [p]
    c = CombatSystem(st, [_enemy()], adapter=DummyAdapter())
    e = c.enemies[0]
    e.planned_action = ("TRANSFORM", 0, ["phase"])
    e.intent_view = build_intent_view("TRANSFORM", e)
    assert e.intent_view.uninterruptible is True
    c.execute_interrupt(p, 0)
    assert e.planned_action[0] == "TRANSFORM"


def test_combo_shatterfire_detection():
    g = Player("G", CharacterClass.GUERREIRO)
    m = Player("M", CharacterClass.MAGO)
    g.level = 6
    m.level = 6
    skills_g = get_class_skills(CharacterClass.GUERREIRO, 6)
    skills_m = get_class_skills(CharacterClass.MAGO, 6)
    golpe = next(s for s in skills_g if s.name == "Golpe Poderoso")
    fogo = next(s for s in skills_m if s.name == "Bola de Fogo")
    cmd_g = Command("SKILL", value=golpe)
    cmd_m = Command("SKILL", value=fogo)
    hits = find_combos([(g, cmd_g), (m, cmd_m)])
    assert len(hits) == 1
    assert hits[0].definition.combo_id == "shatterfire"


def test_combo_applies_bonus_damage():
    g = Player("G", CharacterClass.GUERREIRO)
    m = Player("M", CharacterClass.MAGO)
    g.level = 3
    m.level = 3
    g.client_id = "g"
    m.client_id = "m"
    st = GameState(g)
    st.party = [g, m]
    e = _enemy(hp=200)
    c = CombatSystem(st, [e], adapter=DummyAdapter())
    c.phase = CombatPhase.PARTY_EXECUTE
    skills_g = get_class_skills(CharacterClass.GUERREIRO, 3)
    skills_m = get_class_skills(CharacterClass.MAGO, 3)
    golpe = next(s for s in skills_g if s.name == "Golpe Poderoso")
    fogo = next(s for s in skills_m if s.name == "Bola de Fogo")
    g.mp = 99
    m.mp = 99
    c.pending_actions = {
        "g": Command("SKILL", value=golpe),
        "m": Command("SKILL", value=fogo),
    }
    hp_before = e.hp
    telemetry.reset_counters()
    c.resolve_party_turn()
    # Skills + combo bonus should deal damage
    assert e.hp < hp_before
    assert any("Shatterfire" in log or "COMBO" in log for log in c.combat_logs)
    assert telemetry.get_counters().get("combat_combo", 0) >= 1


def test_interrupt_chance_clamped():
    p = Player("A", CharacterClass.GUERREIRO)
    p.agilidade = 1
    e = _enemy()
    assert interrupt_success_chance(p, e) >= 0.15
    p.agilidade = 99
    assert interrupt_success_chance(p, e) <= 0.70


def test_four_combo_definitions_exist():
    assert len(COMBO_DEFINITIONS) >= 4
