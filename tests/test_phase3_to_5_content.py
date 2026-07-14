"""PRD Phase 3–5 content systems — unit coverage (no interactive adapter waits)."""
from engine.player import Player
from engine.state import GameState
from engine.constants import CharacterClass, AIType
from engine.class_gate_theater import party_has_class, GateApproach
from engine.cartographer import party_has_reliable_map, apply_cartographer_check
from engine.hub_schedule import oakhaven_menu_options, is_forge_open
from engine.codex import public_view, try_unlock_from_flags
from engine.downed_roles import downed_menu_options, execute_downed_action
from engine.terrain_rules import terrain_for_location
from engine.relic_attunement import record_relic_use, apply_attunement_to_weapon
from engine.vesper_intel import record_tactic
from engine.combat import CombatSystem
from engine.enemy import Enemy
from engine.items import create_item
from engine.party_meta import ensure_meta


class DummyAdapter:
    def __init__(self):
        self.emitted = []

    def emit(self, e):
        self.emitted.append(e)
        return None

    def on_state_change(self, s):
        pass

    def broadcast(self, p):
        pass


def _state(cls=CharacterClass.GUERREIRO):
    p = Player("Hero", cls)
    return GameState(p, adapter=DummyAdapter()), p


def test_party_has_class():
    st, p = _state(CharacterClass.GUERREIRO)
    assert party_has_class([p], CharacterClass.GUERREIRO) is True
    assert party_has_class([p], CharacterClass.MAGO) is False


def test_cartographer_lie_without_scout():
    st, p = _state(CharacterClass.GUERREIRO)

    class W:
        party = [p]
        state = st
        player = p

    w = W()
    assert party_has_reliable_map(w) is False
    assert apply_cartographer_check(w) is True
    assert st.get_flag("cartographer_lie") is True
    assert st.get_flag("cold_debuff_active") is True


def test_cartographer_truth_with_ladino():
    st, p = _state(CharacterClass.LADINO)

    class W:
        party = [p]
        state = st
        player = p

    w = W()
    assert party_has_reliable_map(w) is True
    assert apply_cartographer_check(w) is False
    assert st.get_flag("map_reliable") is True


def test_hub_schedule_night_closes_forge():
    st, _ = _state()
    st.set_flag("time_of_day", "Noite")
    opts = oakhaven_menu_options(st)
    assert "7" in opts
    assert "8" in opts
    assert is_forge_open(st) is False
    st.set_flag("time_of_day", "Dia")
    assert is_forge_open(st) is True


def test_codex_unlocks_on_flags():
    st, _ = _state()
    st.set_flag("poupou_ogro", True)
    try_unlock_from_flags(st)
    view = public_view(st)
    assert view["unlocked"] >= 1
    assert any(e["id"] == "drogg" for e in view["entries"])


def test_downed_bargain_raises_and_corrupts():
    st, p = _state()
    p.hp = 0
    e = Enemy("X", 10, 1, 0, 1, 1, AIType.AGGRESSIVE)
    e.idx = 0
    c = CombatSystem(st, [e], adapter=DummyAdapter())
    opts = downed_menu_options(st)
    assert "bargain" in opts
    assert "shout" in opts
    execute_downed_action(c, p, "bargain")
    assert p.hp == 1
    assert ensure_meta(st)["corruption"] >= 10


def test_downed_shout_sets_flag():
    st, p = _state()
    p.hp = 0
    e = Enemy("X", 10, 1, 0, 1, 1, AIType.AGGRESSIVE)
    e.idx = 0
    c = CombatSystem(st, [e], adapter=DummyAdapter())
    execute_downed_action(c, p, "shout")
    assert st.get_flag("shout_buff_next") is True


def test_terrain_gelido_from_cartographer():
    st, _ = _state()
    st.set_flag("cartographer_lie", True)
    t = terrain_for_location("anywhere", st)
    assert t["id"] == "void_frost"


def test_relic_attunement_advances():
    st, _ = _state()
    w = create_item("espada_soldado")
    assert w is not None
    for _ in range(3):
        record_relic_use(st, w.id, "use")
    entry = ensure_meta(st)["relic_attunement"][w.id]
    assert entry["stage"] >= 1
    apply_attunement_to_weapon(st, w)


def test_vesper_records_tactic():
    st, _ = _state()
    record_tactic(st, "flee")
    assert st.get_flag("last_combat_tactic") == "flee"
    assert st.get_flag("tactic_count_flee") == 1


def test_state_dict_includes_codex():
    st, _ = _state()
    st.set_flag("lacre_sombrio", True)
    d = st.to_dict()
    assert "codex" in d
    assert "party_meta" in d


def test_to_dict_no_deadlock_with_codex_and_meta():
    """Regression: to_dict held state.lock while codex/get_flag re-acquired it."""
    st, _ = _state()
    st.set_flag("poupou_ogro", True)
    st.set_flag("lacre_sombrio", True)
    # Must return (would hang forever if lock re-entered)
    d = st.to_dict()
    assert d["codex"]["unlocked"] >= 1
    assert d["party_meta"]["corruption"]["value"] >= 25


def test_gate_approach_dataclass():
    ap = GateApproach(
        "x", "label", CharacterClass.GUERREIRO, "flag", ("a",), ("b",), ("hp", 1, "r")
    )
    assert ap.ideal_class == CharacterClass.GUERREIRO
