import os
import pytest
from engine.player import Player
from engine.state import GameState
from engine.constants import CharacterClass
from engine.save_system import save_game, load_game, merge_lobby_party_with_save, get_save_path
from engine.companion import get_companion

SESSION_TEST_ID = "test_group2_session"

@pytest.fixture(autouse=True)
def cleanup_save_file():
    path = get_save_path(SESSION_TEST_ID)
    if os.path.exists(path):
        os.remove(path)
    yield
    if os.path.exists(path):
        os.remove(path)

def test_secondary_party_members_persisted_and_restored():
    """Bug 5: Non-leader party members retain their level, stats, and class on save/load and lobby merge."""
    leader = Player("Lider", CharacterClass.GUERREIRO)
    member2 = Player("MagoAux", CharacterClass.MAGO)
    member2.level = 5
    member2.xp = 120
    member2.forca = 20
    member2.gold = 350
    
    state = GameState(leader)
    state.party = [leader, member2]
    
    # Save game
    save_game(state, session_id=SESSION_TEST_ID)
    
    # Load game
    loaded = load_game(session_id=SESSION_TEST_ID)
    assert loaded is not None
    assert len(loaded.party) == 2
    
    restored_m2 = loaded.party[1]
    assert restored_m2.name == "MagoAux"
    assert restored_m2.char_class == CharacterClass.MAGO
    assert restored_m2.level == 5
    assert restored_m2.xp == 120
    assert restored_m2.forca == 20
    assert restored_m2.gold == 350

def test_talents_persisted_and_restored():
    """Bug 6: talents_unlocked and talent_points are saved and restored for all party members."""
    leader = Player("Lider", CharacterClass.GUERREIRO)
    member2 = Player("Aliado", CharacterClass.CLERIGO)
    
    leader.talent_points = 2
    leader.talents_unlocked = ["guerreiro_berserker_1"]
    
    member2.talent_points = 1
    member2.talents_unlocked = ["clerigo_santo_1"]
    
    state = GameState(leader)
    state.party = [leader, member2]
    
    save_game(state, session_id=SESSION_TEST_ID)
    loaded = load_game(session_id=SESSION_TEST_ID)
    
    assert loaded.player.talent_points == 2
    assert loaded.player.talents_unlocked == ["guerreiro_berserker_1"]
    
    restored_m2 = loaded.party[1]
    assert restored_m2.talent_points == 1
    assert restored_m2.talents_unlocked == ["clerigo_santo_1"]

def test_ulfgar_companion_persisted_and_restored():
    """Bug 7: Ulfgar companion specifically is saved and restored properly without being lost."""
    leader = Player("Lider", CharacterClass.GUERREIRO)
    leader.companion = get_companion("ulfgar")
    assert leader.companion is not None
    assert leader.companion.name == "Ulfgar"
    
    state = GameState(leader)
    save_game(state, session_id=SESSION_TEST_ID)
    loaded = load_game(session_id=SESSION_TEST_ID)
    
    assert loaded.player.companion is not None
    assert loaded.player.companion.name == "Ulfgar"

def test_merge_lobby_party_preserves_offline_members():
    """Bug 5: Merging lobby connections preserves saved secondary members if offline."""
    leader = Player("Lider", CharacterClass.GUERREIRO)
    member2 = Player("MagoAux", CharacterClass.MAGO)
    member2.level = 4
    
    state = GameState(leader)
    state.party = [leader, member2]
    save_game(state, session_id=SESSION_TEST_ID)
    
    loaded = load_game(session_id=SESSION_TEST_ID)
    # Simulate single player reconnecting in lobby
    lobby = [Player("Lider", CharacterClass.GUERREIRO)]
    merged = merge_lobby_party_with_save(loaded, lobby)
    
    assert len(merged) == 2
    assert merged[0].name == "Lider"
    assert merged[1].name == "MagoAux"
    assert merged[1].level == 4
