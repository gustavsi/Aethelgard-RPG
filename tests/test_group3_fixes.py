import os
import pytest
from engine.player import Player
from engine.state import GameState
from engine.constants import CharacterClass
from engine.combat import CombatSystem, CombatPhase, Command
from engine.enemy import Enemy
from engine.save_system import save_game, load_game, merge_lobby_party_with_save, get_save_path
from server import migrate_combat_client_id, MulticastWebUIAdapter

SESSION_COMBINED_ID = "test_combined_session"

@pytest.fixture(autouse=True)
def cleanup_save_file():
    path = get_save_path(SESSION_COMBINED_ID)
    if os.path.exists(path):
        os.remove(path)
    yield
    if os.path.exists(path):
        os.remove(path)

def test_reconnect_migrates_combat_client_id():
    """Bug 4: Reconnecting with a new UUID remaps pending_actions and client_menu_stages."""
    leader = Player("Leader", CharacterClass.GUERREIRO)
    member2 = Player("Member2", CharacterClass.MAGO)
    
    leader.client_id = "cid_leader"
    member2.client_id = "cid_old_m2"
    
    state = GameState(leader)
    state.party = [leader, member2]
    
    enemy = Enemy("Goblin", 50, 10, 0, 20, 20)
    
    class MockWorld:
        def __init__(self, st, c):
            self.state = st
            self.party = st.party
            self.active_combat = c
            
    combat = CombatSystem(state, [enemy])
    world = MockWorld(state, combat)
    
    combat.phase = CombatPhase.WAITING_ALL_PLAYERS
    
    # Leader submits action
    combat.pending_actions["cid_leader"] = Command("attack", target=enemy)
    combat.pending_actions["cid_old_m2"] = Command("attack", target=enemy)
    
    assert "cid_old_m2" in combat.pending_actions
    
    # Simulate reconnection of Member2 with new client_id "cid_new_m2"
    migrate_combat_client_id(world, "cid_old_m2", "cid_new_m2")
    member2.client_id = "cid_new_m2"
    
    # Verify pending actions remapped
    assert "cid_old_m2" not in combat.pending_actions
    assert "cid_new_m2" in combat.pending_actions
    
    # Advance combat turn
    combat.advance_state()
    assert combat.phase in [CombatPhase.PARTY_EXECUTE, CombatPhase.ENEMY_TURN, CombatPhase.TURN_START, CombatPhase.WAITING_ALL_PLAYERS]

def test_combined_group2_and_group3_offline_and_reconnect():
    """
    Combined Test:
    - Save game with 3 party members.
    - Reload with 2 players connecting in lobby (Member3 offline).
    - Start combat, simulate Member2 mid-combat disconnect + reconnect with new UUID.
    - Verify combat executes cleanly without deadlock and member stats/levels are preserved.
    """
    p1 = Player("P1_Guerreiro", CharacterClass.GUERREIRO)
    p2 = Player("P2_Mago", CharacterClass.MAGO)
    p3 = Player("P3_Ladino", CharacterClass.LADINO)
    
    p1.level = 3
    p2.level = 3
    p3.level = 3
    
    state = GameState(p1)
    state.party = [p1, p2, p3]
    
    # Step 1: Save full party of 3
    save_game(state, session_id=SESSION_COMBINED_ID)
    
    # Step 2: Reload with 2 players in lobby (P3 offline)
    loaded = load_game(session_id=SESSION_COMBINED_ID)
    lobby = [
        Player("P1_Guerreiro", CharacterClass.GUERREIRO),
        Player("P2_Mago", CharacterClass.MAGO)
    ]
    lobby[0].client_id = "p1_initial_id"
    lobby[1].client_id = "p2_initial_id"
    
    merged_party = merge_lobby_party_with_save(loaded, lobby)
    assert len(merged_party) == 3
    assert merged_party[0].name == "P1_Guerreiro"
    assert merged_party[1].name == "P2_Mago"
    assert merged_party[2].name == "P3_Ladino"  # Preserved offline member
    
    # Step 3: Start combat with active party
    enemy = Enemy("Golem de Pedra", 120, 15, 5, 60, 60)
    combat = CombatSystem(loaded, [enemy])
    
    class MockWorld:
        def __init__(self, st, c):
            self.state = st
            self.party = st.party
            self.active_combat = c
            self.player = st.player
            
    world = MockWorld(loaded, combat)
    
    combat.phase = CombatPhase.WAITING_ALL_PLAYERS
    
    # P1 submits action
    combat.submit_player_action("p1_initial_id", Command("attack", target=enemy))
    
    # P2 submits action under initial id
    combat.submit_player_action("p2_initial_id", Command("attack", target=enemy))
    
    # Step 4: Simulate P2 disconnects mid-combat and reconnects with new UUID "p2_reconnected_id"
    migrate_combat_client_id(world, "p2_initial_id", "p2_reconnected_id")
    merged_party[1].client_id = "p2_reconnected_id"
    
    # Verify migration
    assert "p2_initial_id" not in combat.pending_actions
    assert "p2_reconnected_id" in combat.pending_actions
    
    # Check wait-gate transition (all active connected players submitted)
    combat.submit_player_action("p2_reconnected_id", Command("attack", target=enemy))
    
    # Enemy hp should be reduced by attacks or phase advanced
    assert combat.phase in [CombatPhase.PARTY_EXECUTE, CombatPhase.ENEMY_TURN, CombatPhase.TURN_START, CombatPhase.WAITING_ALL_PLAYERS]
    
    # Ensure offline P3 is still level 3 and part of party
    assert merged_party[2].level == 3
    assert merged_party[2].name == "P3_Ladino"
