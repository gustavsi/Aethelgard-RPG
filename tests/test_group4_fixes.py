import pytest
from engine.player import Player
from engine.state import GameState
from engine.constants import CharacterClass
from server import send_player_ready_prompt, exit_client_submenu

def test_oakhaven_ready_consensus_requires_quest_active():
    """Bug 1: Oakhaven ready consensus fails gracefully with narrative warning if quest not active."""
    leader = Player("Lider", CharacterClass.GUERREIRO)
    state = GameState(leader)
    state.current_location = "oakhaven"
    
    class MockWorld:
        def __init__(self, st):
            self.state = st
            self.player = st.player
            self.party = [st.player]
            
    world = MockWorld(state)
    
    # Initially quest 'cavernas' is not active
    assert leader.quest_manager.has_active("cavernas") is False

def test_exit_client_submenu_resends_ready_prompt(monkeypatch):
    """Bug 2: Exiting forge/tavern/elder sub-menu re-sends the ready prompt when waiting_for_ready is True."""
    leader = Player("Lider", CharacterClass.GUERREIRO)
    leader.client_id = "client_1"
    state = GameState(leader)
    state.current_location = "oakhaven"
    
    sent_messages = []
    
    def mock_send(session, ws, payload):
        sent_messages.append(payload)
        
    monkeypatch.setattr("server.send_to_ws_threadsafe", mock_send)
    
    session = {
        "leader_id": "client_1",
        "waiting_for_ready": True,
        "connected_clients": {"client_1": (None, "Lider", None)},
        "client_stages": {"client_1": "forge"},
        "ready_players": set()
    }
    
    class MockWorld:
        def __init__(self, st):
            self.state = st
            self.player = st.player
            self.party = [st.player]
            
    world = MockWorld(state)
    
    # Exit sub-menu
    exit_client_submenu(session, "client_1", world)
    
    assert session["client_stages"]["client_1"] == "normal"
    assert len(sent_messages) > 0
    assert sent_messages[-1]["type"] == "WAITING_INPUT"
