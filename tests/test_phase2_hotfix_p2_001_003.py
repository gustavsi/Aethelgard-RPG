"""
Regression tests for engineering review P2-001, P2-002, P2-003.

Each test documents the failure mode of the pre-hotfix implementation.
"""
import os

from engine.player import Player
from engine.state import GameState
from engine.constants import CharacterClass
from engine.party_meta import (
    ensure_meta,
    observe_flag,
    observe_vote,
    record_ogre_killed,
    serialize_meta,
    deserialize_meta,
    grant_bond,
)
from engine.save_system import save_game, load_game, get_save_path


class DummyAdapter:
    def __init__(self):
        self.emitted = []

    def emit(self, e):
        self.emitted.append(e)

    def on_state_change(self, s):
        pass


# ---------------------------------------------------------------------------
# P2-001 — pre-fight False must not award kill corruption
# ---------------------------------------------------------------------------

def test_p2_001_enter_cabin_init_false_does_not_grant_kill_corruption():
    """
    Old bug: enter_cabin called set_flag('poupou_ogro', False) before combat,
    observe_flag treated that as a kill → +5 corruption for every visitor.
    """
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    # Exact cabin pre-fight sequence
    st.set_flag("poupou_ogro", False)
    meta = ensure_meta(st)
    assert meta["corruption"] == 0, "pre-fight default False must not grant corruption"
    assert "flag:kill_ogre" not in meta["granted_keys"]


def test_p2_001_spare_after_init_false_no_corruption():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.set_flag("poupou_ogro", False)  # init
    st.set_flag("poupou_ogro", True)   # spare
    meta = ensure_meta(st)
    assert meta["corruption"] == 0
    assert meta["bonds"]["mercy"] >= 1
    assert any(d["id"] == "drogg_spared" for d in meta["debts"])
    assert "flag:kill_ogre" not in meta["granted_keys"]


def test_p2_001_explicit_kill_grants_corruption_once():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.set_flag("poupou_ogro", False)  # init — no corr
    st.set_flag("ogre_dialogue_triggered", True)
    st.set_flag("poupou_ogro", False)  # kill flag (still no auto corr)
    record_ogre_killed(st)             # explicit kill branch
    meta = ensure_meta(st)
    assert meta["corruption"] == 5
    record_ogre_killed(st)  # idempotent
    assert ensure_meta(st)["corruption"] == 5


def test_p2_001_kill_after_spare_does_not_add_corruption():
    p = Player("A", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.set_flag("poupou_ogro", True)
    record_ogre_killed(st)
    assert ensure_meta(st)["corruption"] == 0


# ---------------------------------------------------------------------------
# P2-002 — post-load votes must still grant bonds
# ---------------------------------------------------------------------------

def test_p2_002_vote_keys_not_persisted_and_load_still_grants():
    """
    Old bug: vote_event:N stored in granted_keys; after load _vote_seq reset to 0
    so the next N votes hit existing keys and granted nothing.
    """
    p = Player("Voter", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.session_id = "p2_002_vote_save"
    for _ in range(5):
        observe_vote(st, {"c1": "1", "c2": "1"}, "1")
    assert ensure_meta(st)["bonds"]["unison"] == 3  # capped

    blob = serialize_meta(st)
    # Must not persist ephemeral vote keys
    assert not any(str(k).startswith("vote_event:") for k in blob["granted_keys"])
    assert not any(str(k).startswith("vote:") for k in blob["granted_keys"])

    path = get_save_path("p2_002_vote_save")
    try:
        save_game(st, add_log_func=lambda m: None, session_id="p2_002_vote_save")
        loaded = load_game("p2_002_vote_save")
        assert loaded is not None
        # Simulate new vote after load — must apply (fracture from split)
        before = ensure_meta(loaded)["bonds"]["fracture"]
        observe_vote(loaded, {"c1": "1", "c2": "2"}, "1")
        after = ensure_meta(loaded)["bonds"]["fracture"]
        assert after == before + 1 or after == 3
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_p2_002_poisoned_save_vote_keys_stripped_on_load():
    p = Player("Poison", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    # Simulate early Phase 2 poisoned meta
    meta = ensure_meta(st)
    meta["granted_keys"] = [f"vote_event:{i}" for i in range(10)] + ["flag:spare_ogre"]
    meta["bonds"]["mercy"] = 1
    meta["_vote_seq"] = 10
    deserialize_meta(st, {
        "bonds": meta["bonds"],
        "debts": [],
        "corruption": 0,
        "granted_keys": meta["granted_keys"],
        "companion_warned_corruption": False,
    })
    cleaned = ensure_meta(st)["granted_keys"]
    assert not any(k.startswith("vote_event:") for k in cleaned)
    assert "flag:spare_ogre" in cleaned
    # Votes work immediately
    observe_vote(st, {"a": "1", "b": "1"}, "1")
    assert ensure_meta(st)["bonds"]["unison"] >= 1


# ---------------------------------------------------------------------------
# P2-003 — granted_keys must not grow with every vote
# ---------------------------------------------------------------------------

def test_p2_003_votes_do_not_grow_granted_keys():
    p = Player("Spam", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.set_flag("lacre_sombrio", True)  # permanent key
    base_len = len(ensure_meta(st)["granted_keys"])
    for _ in range(20):
        observe_vote(st, {"a": "1", "b": "2"}, "1")
    after_len = len(ensure_meta(st)["granted_keys"])
    assert after_len == base_len, "votes must not append granted_keys"
    # serialize also stays clean
    blob = serialize_meta(st)
    assert len(blob["granted_keys"]) == base_len


# ---------------------------------------------------------------------------
# Save repair for P2-001 false positives
# ---------------------------------------------------------------------------

def test_p2_001_repair_false_kill_when_spared():
    p = Player("Repair", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    # Poisoned early Phase 2 state: init False then spare
    meta = ensure_meta(st)
    meta["granted_keys"] = ["flag:kill_ogre", "flag:spare_ogre"]
    meta["corruption"] = 5
    meta["bonds"]["mercy"] = 1
    st.flags["poupou_ogro"] = True
    p.choices["poupou_ogro"] = True
    deserialize_meta(st, {
        "bonds": meta["bonds"],
        "debts": [{"id": "drogg_spared", "title": "Vida de Drogg", "source": "", "status": "open", "created_chapter": 1}],
        "corruption": 5,
        "granted_keys": ["flag:kill_ogre", "flag:spare_ogre"],
        "companion_warned_corruption": False,
    })
    fixed = ensure_meta(st)
    assert "flag:kill_ogre" not in fixed["granted_keys"]
    assert fixed["corruption"] == 0
    assert fixed["bonds"]["mercy"] >= 1


def test_p2_001_repair_false_kill_without_dialogue():
    """Init-only kill grant (never reached ogre dialogue) must be undone."""
    p = Player("Quit", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    deserialize_meta(st, {
        "bonds": {"mercy": 0, "unison": 0, "fracture": 0},
        "debts": [],
        "corruption": 5,
        "granted_keys": ["flag:kill_ogre"],
        "companion_warned_corruption": False,
    })
    # poupou_ogro false, ogre_dialogue never triggered
    fixed = ensure_meta(st)
    assert "flag:kill_ogre" not in fixed["granted_keys"]
    assert fixed["corruption"] == 0


def test_p2_001_real_kill_not_repaired_away():
    """True kill: dialogue triggered, no spare, keep corruption."""
    p = Player("Killer", CharacterClass.GUERREIRO)
    st = GameState(p, adapter=DummyAdapter())
    st.flags["ogre_dialogue_triggered"] = True
    p.choices["ogre_dialogue_triggered"] = True
    st.flags["poupou_ogro"] = False
    deserialize_meta(st, {
        "bonds": {"mercy": 0, "unison": 0, "fracture": 0},
        "debts": [],
        "corruption": 5,
        "granted_keys": ["flag:kill_ogre"],
        "companion_warned_corruption": False,
    })
    fixed = ensure_meta(st)
    assert "flag:kill_ogre" in fixed["granted_keys"]
    assert fixed["corruption"] == 5
