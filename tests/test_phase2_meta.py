"""PRD Phase 2: bonds, debts, corruption."""
import os
import tempfile

from engine.player import Player
from engine.state import GameState
from engine.constants import CharacterClass
from engine.party_meta import (
    ensure_meta,
    grant_bond,
    observe_vote,
    try_mercy_revive,
    interrupt_chance_bonus,
    offense_mult,
    heal_mult,
    public_view,
    serialize_meta,
    deserialize_meta,
)
from engine import corruption as corruption_mod
from engine.save_system import save_game, load_game, get_save_path
from engine.feature_flags import FLAGS
from engine.combat import CombatSystem, Command
from engine.enemy import Enemy
from engine.constants import AIType
from engine.combat_intent import interrupt_success_chance


class DummyAdapter:
    def __init__(self):
        self.emitted = []

    def emit(self, e):
        self.emitted.append(e)

    def on_state_change(self, s):
        pass


def test_spare_ogre_grants_mercy_and_debt():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.set_flag("poupou_ogro", True)
    meta = ensure_meta(st)
    assert meta["bonds"]["mercy"] >= 1
    assert any(d["id"] == "drogg_spared" for d in meta["debts"])
    # idempotent
    st.set_flag("poupou_ogro", True)
    assert meta["bonds"]["mercy"] == 1


def test_lacre_grants_corruption():
    p = Player("A", CharacterClass.MAGO)
    st = GameState(p, adapter=DummyAdapter())
    st.set_flag("lacre_sombrio", True)
    meta = ensure_meta(st)
    assert meta["corruption"] >= 25
    assert offense_mult(st) > 1.0
    assert heal_mult(st) < 1.0


def test_unanimous_vote_unison():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    observe_vote(st, {"c1": "1", "c2": "1"}, "1")
    assert ensure_meta(st)["bonds"]["unison"] >= 1


def test_split_vote_fracture():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    observe_vote(st, {"c1": "1", "c2": "2"}, "1")
    assert ensure_meta(st)["bonds"]["fracture"] >= 1


def test_mercy_revive_once_per_combat():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    grant_bond(st, "mercy", 1)
    p.hp = 0
    assert try_mercy_revive(st, p) is True
    assert p.hp == 1
    p.hp = 0
    assert try_mercy_revive(st, p) is False


def test_unison_boosts_interrupt_chance():
    p = Player("A", CharacterClass.LADINO)
    p.agilidade = 10
    e = Enemy("X", 10, 1, 0, 1, 1, AIType.AGGRESSIVE)
    st = GameState(p, adapter=DummyAdapter())
    base = interrupt_success_chance(p, e, bond_bonus=0)
    grant_bond(st, "unison", 1)
    bonus = interrupt_chance_bonus(st)
    boosted = interrupt_success_chance(p, e, bond_bonus=bonus)
    assert boosted > base


def test_save_load_roundtrip_meta():
    p = Player("HeroSave", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.session_id = "phase2_meta_test"
    st.set_flag("poupou_ogro", True)
    st.set_flag("lacre_sombrio", True)
    path = get_save_path("phase2_meta_test")
    try:
        save_game(st, add_log_func=lambda m: None, session_id="phase2_meta_test")
        loaded = load_game("phase2_meta_test")
        assert loaded is not None
        meta = ensure_meta(loaded)
        assert meta["bonds"]["mercy"] >= 1
        assert meta["corruption"] >= 25
        assert any(d["id"] == "drogg_spared" for d in meta["debts"])
        view = public_view(loaded)
        assert "corruption" in view
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_old_save_without_meta_bootstraps():
    p = Player("Legacy", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.flags["poupou_ogro"] = True
    p.choices["poupou_ogro"] = True
    deserialize_meta(st, None)
    meta = ensure_meta(st)
    assert meta["bonds"]["mercy"] >= 1 or any(d["id"] == "drogg_spared" for d in meta["debts"])


def test_combat_start_resets_mercy_token():
    from engine.party_meta import on_combat_start, ensure_meta

    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    grant_bond(st, "mercy", 1)
    p.hp = 0
    try_mercy_revive(st, p)
    assert ensure_meta(st)["mercy_revive_used_combat"] is True
    on_combat_start(st)
    assert ensure_meta(st)["mercy_revive_used_combat"] is False


def test_to_dict_includes_party_meta():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.set_flag("goblin_ajudado", True)
    d = st.to_dict()
    assert "party_meta" in d
    assert d["party_meta"]["bonds"]
