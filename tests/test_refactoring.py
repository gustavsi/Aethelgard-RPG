import os
import threading
import pytest
from engine.adapter import UIAdapter
from engine.player import Player
from engine.constants import CharacterClass
from engine.state import GameState
from engine.save_system import save_game, load_game, get_save_path

try:
    from fastapi.testclient import TestClient
    has_fastapi = True
except ImportError:
    has_fastapi = False

def test_ui_adapter_thread_safety():
    """Verify that UIAdapter.get_instance() is isolated per thread."""
    adapter_t1 = UIAdapter()
    adapter_t2 = UIAdapter()
    
    res = {}
    
    def thread_1_run():
        UIAdapter.set_instance(adapter_t1)
        # Wait a bit to let thread 2 execute
        import time
        time.sleep(0.1)
        res["t1"] = UIAdapter.get_instance()
        
    def thread_2_run():
        UIAdapter.set_instance(adapter_t2)
        res["t2"] = UIAdapter.get_instance()
        
    t1 = threading.Thread(target=thread_1_run)
    t2 = threading.Thread(target=thread_2_run)
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    assert res["t1"] is adapter_t1
    assert res["t2"] is adapter_t2
    assert res["t1"] is not res["t2"]

def test_save_game_isolation():
    """Verify that save_game writes to session-specific paths and loads from them."""
    # Clean up old test saves if any
    save1_path = get_save_path("session_1")
    save2_path = get_save_path("session_2")
    if os.path.exists(save1_path):
        os.remove(save1_path)
    if os.path.exists(save2_path):
        os.remove(save2_path)
        
    player1 = Player("Alpha", CharacterClass.GUERREIRO)
    player2 = Player("Beta", CharacterClass.MAGO)
    
    state1 = GameState(player1)
    state1.session_id = "session_1"
    
    state2 = GameState(player2)
    state2.session_id = "session_2"
    
    save_game(state1)
    save_game(state2)
    
    assert os.path.exists(save1_path)
    assert os.path.exists(save2_path)
    
    loaded_state1 = load_game("session_1")
    loaded_state2 = load_game("session_2")
    
    assert loaded_state1.player.name == "Alpha"
    assert loaded_state2.player.name == "Beta"
    
    # Clean up files
    os.remove(save1_path)
    os.remove(save2_path)

@pytest.mark.skipif(not has_fastapi, reason="fastapi is not installed")
def test_websocket_reconnection():
    """Verify that websocket connection drops can reconnect to active session registries."""
    from server import app, active_sessions
    
    client = TestClient(app)
    
    # 1. Create a session via /api/game/new
    res = client.post("/api/game/new")
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    
    # 2. Connect websocket
    with client.websocket_connect(f"/ws/{session_id}") as websocket:
        # Receive the initial STATE_UPDATE
        data = websocket.receive_json()
        assert data["type"] == "STATE_UPDATE"
        assert data["state"]["player"]["name"] == "Herói Web"
        
    # 3. WebSocket is disconnected. The session must still remain active in active_sessions
    # because of the grace period
    assert session_id in active_sessions
    assert active_sessions[session_id]["connected"] is False
    
    # 4. Reconnect using the same session_id
    with client.websocket_connect(f"/ws/{session_id}") as websocket2:
        # The session should restore its state and send last_state
        data = websocket2.receive_json()
        assert data["type"] == "STATE_UPDATE"
        assert data["state"]["player"]["name"] == "Herói Web"
        
    # Clean up the session manually to stop its thread
    if session_id in active_sessions:
        active_sessions[session_id]["adapter"].shutdown_event.set()
        active_sessions.pop(session_id, None)
