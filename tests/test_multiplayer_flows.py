import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server import app, active_sessions
from engine.items import create_item
from engine.constants import CharacterClass

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Timeout waiting for message")

def receive_until_type(ws, type_name, prompt_contains=None):
    import signal
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(3)
    try:
        while True:
            data = ws.receive_json()
            if data["type"] == type_name:
                search_in = data.get("prompt", "") or ""
                if data.get("content"):
                    search_in += " " + data["content"]
                if prompt_contains is None or prompt_contains in search_in:
                    return data
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def test_multiplayer_inventories_and_ready():
    client = TestClient(app)
    
    # 1. Create game session
    res = client.post("/api/game/new")
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    lobby_code = res.json()["lobby_code"]
    
    # 2. Leader (Player A) connects
    with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
        # Leader receives LOBBY_UPDATE
        data_a1 = receive_until_type(ws_a, "LOBBY_UPDATE")
        assert data_a1["type"] == "LOBBY_UPDATE"
        
        # 3. Player B joins lobby
        join_res = client.post(f"/api/game/join/{lobby_code}")
        assert join_res.status_code == 200
        
        # B connects
        with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
            # Drain B's connect LOBBY_UPDATE
            receive_until_type(ws_b, "LOBBY_UPDATE")
            
            # Start game (Leader sends START_GAME)
            ws_a.send_json({"action": "START_GAME"})
            
            # Everyone gets GAME_START transition
            receive_until_type(ws_a, "GAME_START")
            receive_until_type(ws_b, "GAME_START")
            
            # Receive initial state updates
            su_a = receive_until_type(ws_a, "STATE_UPDATE")
            assert su_a["type"] == "STATE_UPDATE"
            
            su_b = receive_until_type(ws_b, "STATE_UPDATE")
            assert su_b["type"] == "STATE_UPDATE"
            
            # Wait input is sent to leader (the menu choice)
            wi_menu = receive_until_type(ws_a, "WAITING_INPUT")
            assert wi_menu["type"] == "WAITING_INPUT"
            
            world = active_sessions[session_id]["world"]
            # Trigger ready consensus manually for the test
            world.request_party_ready()
            
            # Now leader A receives the preparation waiting menu
            wi_a = receive_until_type(ws_a, "WAITING_INPUT", "Aguardando a party")
            assert wi_a["type"] == "WAITING_INPUT"
            
            # Non-leader B receives the wait menu
            wi_b = receive_until_type(ws_b, "WAITING_INPUT", "Aguardando o líder")
            assert wi_b["type"] == "WAITING_INPUT"
            # Wait menu should have "Aguardando o líder..." as prompt and option 1/2/3
            assert "Aguardando o líder" in wi_b["prompt"]
            assert "1" in wi_b["options"] # Estou pronto
            
            world = active_sessions[session_id]["world"]
            
            # Let's give some test items:
            # We add a Weapon to B's inventory, and a Consumable to B's inventory.
            potion = create_item("pocao_vida_p")
            sword = create_item("espada_soldado")
            
            player_b = next(p for p in world.party if p.name == "B")
            player_b.inventory.append(sword)
            player_b.inventory.append(potion)
            
            # Check assertion: Sword is in player_b.inventory, but potion went to shared_inventory!
            assert sword in player_b.inventory
            assert potion not in player_b.inventory
            assert potion in world.state.shared_inventory
            
            # Also, individual inventory of B should NOT show potion, and shared inventory should NOT show sword.
            # Let's test opening individual inventory for B:
            # B sends choice "2" (Abrir Inventário) from the waiting menu
            ws_b.send_json({"action": "MENU_CHOICE", "value": "2"})
            
            inv_b = receive_until_type(ws_b, "WAITING_INPUT", "Inventário de B")
            assert inv_b["type"] == "WAITING_INPUT"
            assert "Inventário de B" in inv_b["prompt"]
            # It should list the sword (index 0) but not the potion
            assert "Espada de Soldado" in inv_b["options"]["0"]
            assert "exit" in inv_b["options"]
            
            # Let's equip the sword: B selects option "0"
            player_b.hp = 10
            ws_b.send_json({"action": "MENU_CHOICE", "value": "0"})
            
            # The server equips it, broadcasts STATE_UPDATE, and sends the updated inventory screen
            receive_until_type(ws_a, "STATE_UPDATE")
            receive_until_type(ws_b, "STATE_UPDATE")
            
            inv_b_updated = receive_until_type(ws_b, "WAITING_INPUT", "Inventário de B")
            assert inv_b_updated["type"] == "WAITING_INPUT"
            # Sword is now equipped, so it should not be in the options
            assert "Espada de Soldado" not in str(inv_b_updated["options"])
            
            # B closes individual inventory
            ws_b.send_json({"action": "MENU_CHOICE", "value": "exit"})
            
            # B should receive the wait menu again!
            wi_b_back = receive_until_type(ws_b, "WAITING_INPUT", "Aguardando o líder")
            assert wi_b_back["type"] == "WAITING_INPUT"
            assert "Aguardando o líder" in wi_b_back["prompt"]
            
            # Now let's test party stock:
            # B sends choice "3" (Estoque) from the waiting menu
            ws_b.send_json({"action": "MENU_CHOICE", "value": "3"})
            
            stock_b = receive_until_type(ws_b, "WAITING_INPUT", "Estoque da Party")
            assert stock_b["type"] == "WAITING_INPUT"
            assert "Estoque da Party" in stock_b["prompt"]
            # It should list the potion (index 0)
            assert "Poção de Vida Menor" in stock_b["options"]["0"]
            
            # B uses the potion: selects option "0"
            ws_b.send_json({"action": "MENU_CHOICE", "value": "0"})
            
            # Since party size > 1, B must select a target. Let's select B (index 1)
            target_wi = receive_until_type(ws_b, "WAITING_INPUT", "Escolha o alvo")
            assert "B" in target_wi["options"]["1"]
            ws_b.send_json({"action": "MENU_CHOICE", "value": "1"})
            
            # Server processes it: B is healed by 25 HP. HP goes from 10 to 35.
            receive_until_type(ws_a, "STATE_UPDATE")
            receive_until_type(ws_b, "STATE_UPDATE")
            
            # Re-renders the stock (used potion is removed)
            stock_b_updated = receive_until_type(ws_b, "WAITING_INPUT", "Estoque da Party")
            assert stock_b_updated["type"] == "WAITING_INPUT"
            assert len(world.state.shared_inventory) == 4
            assert player_b.hp == 35
            
            # B closes the stock
            ws_b.send_json({"action": "MENU_CHOICE", "value": "exit"})
            
            # B should get wait menu again
            wi_b_back_again = receive_until_type(ws_b, "WAITING_INPUT", "Aguardando o líder")
            assert "Aguardando o líder" in wi_b_back_again["prompt"]
            
            # Now let's test readiness consenso:
            # A and B mark ready:
            # B sends choice "1" (Estou pronto)
            ws_b.send_json({"action": "MENU_CHOICE", "value": "1"})
            
            # Everyone gets NARRATIVE_TEXT notifying B is ready
            nt_a = receive_until_type(ws_a, "NARRATIVE_TEXT", "está pronto")
            assert nt_a["type"] == "NARRATIVE_TEXT"
            assert "B está pronto" in nt_a["content"]
            
            nt_b = receive_until_type(ws_b, "NARRATIVE_TEXT", "está pronto")
            assert nt_b["type"] == "NARRATIVE_TEXT"
            assert "B está pronto" in nt_b["content"]
            
            # A sends choice "1" (Estou pronto)
            ws_a.send_json({"action": "PLAYER_READY"})
            
            # Everyone gets notification A is ready
            nt_a2 = receive_until_type(ws_a, "NARRATIVE_TEXT", "está pronto")
            assert "A está pronto" in nt_a2["content"]
            
            nt_b2 = receive_until_type(ws_b, "NARRATIVE_TEXT", "está pronto")
            assert "A está pronto" in nt_b2["content"]
            
            # Since all are ready, leader (A) gets the waiting input to advance the journey
            leader_prompt = receive_until_type(ws_a, "WAITING_INPUT")
            assert leader_prompt["type"] == "WAITING_INPUT"
            assert "Escolha uma opção" in leader_prompt["prompt"] or "Toda a party está pronta" in leader_prompt["prompt"]
            
    # Cleanup session
    if session_id in active_sessions:
        active_sessions[session_id]["adapter"].shutdown_event.set()
        active_sessions.pop(session_id, None)

@patch('engine.world.WorldManager.run_game', return_value=None)
def test_multiplayer_voting(mock_run_game):
    client = TestClient(app)
    
    # 1. Create game session
    res = client.post("/api/game/new")
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    lobby_code = res.json()["lobby_code"]
    
    # 2. Leader (Player A) connects
    with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
        receive_until_type(ws_a, "LOBBY_UPDATE")
        
        # 3. Player B joins lobby
        join_res = client.post(f"/api/game/join/{lobby_code}")
        assert join_res.status_code == 200
        
        with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
            receive_until_type(ws_b, "LOBBY_UPDATE")
            
            session = active_sessions[session_id]
            session["game_started"] = True
            
            from server import MulticastWebUIAdapter, send_to_ws_threadsafe, get_actual_leader_id
            
            def broadcast_callback(payload):
                for target_id, (target_ws, _, _) in list(session["connected_clients"].items()):
                    try:
                        payload_copy = dict(payload)
                        payload_copy["my_client_id"] = target_id
                        payload_copy["leader_client_id"] = get_actual_leader_id(session, session.get("world"))
                        send_to_ws_threadsafe(session, target_ws, payload_copy)
                    except Exception:
                        pass
            
            def leader_callback(payload):
                leader_id = get_actual_leader_id(session, session.get("world"))
                if leader_id in session["connected_clients"]:
                    target_ws = session["connected_clients"][leader_id][0]
                    try:
                        payload_copy = dict(payload)
                        payload_copy["my_client_id"] = leader_id
                        payload_copy["leader_client_id"] = leader_id
                        send_to_ws_threadsafe(session, target_ws, payload_copy)
                    except Exception:
                        pass
                        
            adapter = MulticastWebUIAdapter(broadcast_callback, leader_callback)
            session["adapter"] = adapter
            
            from engine.world import WorldManager
            from engine.state import GameState
            from engine.player import Player
            
            cids = list(session["connected_clients"].keys())
            player_a = Player("A", CharacterClass.GUERREIRO)
            player_a.client_id = cids[0]
            player_b = Player("B", CharacterClass.MAGO)
            player_b.client_id = cids[1]
            
            state = GameState(player_a)
            state.party = [player_a, player_b]
            state.session_id = session_id
            
            world = WorldManager(state, adapter=adapter)
            session["world"] = world
            adapter.state = state
            
            # Trigger get_party_vote in a background thread
            import threading
            votes_received = {}
            
            def run_vote():
                nonlocal votes_received
                votes_received = world.get_party_vote({"1": "Sim", "2": "Não"}, "Deseja ajudar o goblin?")
                
            t = threading.Thread(target=run_vote)
            t.start()
            
            # Both players should receive the choice prompt
            wi_a = receive_until_type(ws_a, "WAITING_INPUT", "Deseja ajudar")
            wi_b = receive_until_type(ws_b, "WAITING_INPUT", "Deseja ajudar")
            assert wi_a["type"] == "WAITING_INPUT"
            assert wi_b["type"] == "WAITING_INPUT"
            
            # Player A votes "1", Player B votes "2" (Tie)
            ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
            ws_b.send_json({"action": "MENU_CHOICE", "value": "2"})
            
            # Receive the result narrative text to drive the event loop
            nt_a = receive_until_type(ws_a, "NARRATIVE_TEXT")
            assert "decidiu" in nt_a["content"] or "Empate" in nt_a["content"]
            
            t.join(timeout=1.0)
            assert not t.is_alive()
            
            assert votes_received in ["1", "2"]
            
    # Cleanup session
    if session_id in active_sessions:
        active_sessions[session_id]["adapter"].shutdown_event.set()
        active_sessions.pop(session_id, None)

def test_multiplayer_combat_no_reset():
    client = TestClient(app)
    
    # 1. Create game session
    res = client.post("/api/game/new")
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    lobby_code = res.json()["lobby_code"]
    
    # 2. Leader (Player A) connects
    with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
        receive_until_type(ws_a, "LOBBY_UPDATE")
        
        # 3. Player B joins lobby
        join_res = client.post(f"/api/game/join/{lobby_code}")
        assert join_res.status_code == 200
        
        with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
            receive_until_type(ws_b, "LOBBY_UPDATE")
            
            session = active_sessions[session_id]
            session["game_started"] = True
            
            from server import MulticastWebUIAdapter, send_to_ws_threadsafe, get_actual_leader_id, handle_broadcast_payload
            
            def broadcast_callback(payload):
                handle_broadcast_payload(session, payload)
                for target_id, (target_ws, _, _) in list(session["connected_clients"].items()):
                    try:
                        payload_copy = dict(payload)
                        payload_copy["my_client_id"] = target_id
                        payload_copy["leader_client_id"] = get_actual_leader_id(session, session.get("world"))
                        send_to_ws_threadsafe(session, target_ws, payload_copy)
                    except Exception:
                        pass
            
            def leader_callback(payload):
                leader_id = get_actual_leader_id(session, session.get("world"))
                if leader_id in session["connected_clients"]:
                    target_ws = session["connected_clients"][leader_id][0]
                    try:
                        payload_copy = dict(payload)
                        payload_copy["my_client_id"] = leader_id
                        payload_copy["leader_client_id"] = leader_id
                        send_to_ws_threadsafe(session, target_ws, payload_copy)
                    except Exception:
                        pass
                        
            adapter = MulticastWebUIAdapter(broadcast_callback, leader_callback)
            session["adapter"] = adapter
            
            from engine.world import WorldManager
            from engine.state import GameState
            from engine.player import Player
            from engine.enemy import spawn_enemy
            from engine.combat import CombatSystem, CombatPhase
            
            cids = list(session["connected_clients"].keys())
            player_a = Player("A", CharacterClass.GUERREIRO)
            player_a.client_id = cids[0]
            player_b = Player("B", CharacterClass.MAGO)
            player_b.client_id = cids[1]
            
            state = GameState(player_a)
            state.party = [player_a, player_b]
            state.session_id = session_id
            
            world = WorldManager(state, adapter=adapter)
            session["world"] = world
            adapter.state = state
            
            enemy = spawn_enemy("pirata_mare_negra")
            combat = CombatSystem(state, [enemy], adapter=adapter)
            world.active_combat = combat
            
            # Force phase to WAITING_ALL_PLAYERS and sync
            combat.phase = CombatPhase.WAITING_ALL_PLAYERS
            combat.sync_state()
            adapter.on_state_change(state)
            
            # Both players get "O que deseja fazer?"
            receive_until_type(ws_a, "WAITING_INPUT", "O que deseja fazer?")
            receive_until_type(ws_b, "WAITING_INPUT", "O que deseja fazer?")
            
            # Player A chooses "1" (Atacar) -> enters "target" stage
            ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
            receive_until_type(ws_a, "WAITING_INPUT", "Escolha o alvo:")
            
            assert combat.client_menu_stages[player_a.client_id] == "target"
            
            # Player B chooses "4" (Defender) -> submits Defender action
            ws_b.send_json({"action": "MENU_CHOICE", "value": "4"})
            
            # Wait for the broadcasted STATE_UPDATE on ws_a
            receive_until_type(ws_a, "STATE_UPDATE")
            
            # Now let's check: did combat.client_menu_stages[player_a.client_id] get reset to "main"?
            # Let's assert that it is still "target"!
            assert combat.client_menu_stages[player_a.client_id] == "target"
            
    # Cleanup session
    if session_id in active_sessions:
        active_sessions[session_id]["adapter"].shutdown_event.set()
        active_sessions.pop(session_id, None)
