import pytest
import asyncio
import threading
import time
from fastapi.testclient import TestClient
from server import app, active_sessions, get_actual_leader_id, send_to_ws_threadsafe, handle_broadcast_payload
from engine.constants import CharacterClass
from engine.player import Player
from engine.state import GameState
from engine.world import WorldManager
from engine.enemy import spawn_enemy
from engine.combat import CombatSystem, CombatPhase
from engine.dto import NarrativeText
from tests.test_full_coverage import receive_until_type

def setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b):
    session["game_started"] = True

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

    from server import MulticastWebUIAdapter
    adapter = MulticastWebUIAdapter(broadcast_callback, leader_callback)
    session["adapter"] = adapter

    cids = list(session["connected_clients"].keys())
    player_a = Player("A", CharacterClass.GUERREIRO)
    player_a.client_id = cids[0]
    player_b = Player("B", CharacterClass.MAGO)
    player_b.client_id = cids[1]

    state = GameState(player_a)
    state.party = [player_a, player_b]
    state.session_id = session_id

    world = WorldManager(state, adapter=adapter, party=[player_a, player_b])
    session["world"] = world
    adapter.state = state

    return world, player_a, player_b


class TestVillageStress:
    # 1. Concorrência de estágio (client_stage)
    def test_client_stage_persistence_during_state_update(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True
                
                # A opens forge
                ws_a.send_json({"action": "MENU_CHOICE", "value": "4"})
                receive_until_type(ws_a, "WAITING_INPUT", "Forja")

                cids = list(session["connected_clients"].keys())
                assert session["client_stages"].get(cids[0]) == "forge"

                # Trigger state update broadcast from another context
                world.adapter.on_state_change(world.state)

                # A's stage must persist as "forge"
                assert session["client_stages"].get(cids[0]) == "forge"

    def test_forge_concurrency_no_crosstalk(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True
                player_a.gold = 100
                player_b.gold = 100

                # Both open forge
                ws_a.send_json({"action": "MENU_CHOICE", "value": "4"})
                receive_until_type(ws_a, "WAITING_INPUT", "Forja")
                ws_b.send_json({"action": "MENU_CHOICE", "value": "4"})
                receive_until_type(ws_b, "WAITING_INPUT", "Forja")

                # Both buy different items simultaneously
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"}) # Soldier Sword (30 gold)
                ws_b.send_json({"action": "MENU_CHOICE", "value": "2"}) # Chainmail (50 gold)

                time.sleep(0.1)

                # Verify gold counts without cross-talk
                assert player_a.gold == 70
                assert player_b.gold == 50
                assert any(item.id == "espada_soldado" for item in player_a.inventory)
                assert any(item.id == "cota_malha" for item in player_b.inventory)

    # 2. Navegação fora de ordem
    def test_switch_menu_without_closing(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True
                cids = list(session["connected_clients"].keys())

                # A opens inventory
                ws_a.send_json({"action": "OPEN_INVENTORY"})
                receive_until_type(ws_a, "WAITING_INPUT", "Inventário")
                assert session["client_stages"].get(cids[0]) == "inventory"

                # A switches directly to party stock without closing inventory
                ws_a.send_json({"action": "OPEN_PARTY_STOCK"})
                receive_until_type(ws_a, "WAITING_INPUT", "Estoque da Party")
                assert session["client_stages"].get(cids[0]) == "party_stock"

                # A closes stock
                ws_a.send_json({"action": "MENU_CHOICE", "value": "exit"})
                time.sleep(0.1)
                assert session["client_stages"].get(cids[0]) == "normal"

    def test_ignore_invalid_stage_actions(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True

                # A opens forge
                ws_a.send_json({"action": "MENU_CHOICE", "value": "4"})
                receive_until_type(ws_a, "WAITING_INPUT", "Forja")

                # A sends a choice "5" (not valid in forge, would open tavern in town)
                ws_a.send_json({"action": "MENU_CHOICE", "value": "5"})
                time.sleep(0.1)

                # Forge stage should remain unchanged, no tavern should be opened
                cids = list(session["connected_clients"].keys())
                assert session["client_stages"].get(cids[0]) == "forge"

    def test_double_click_exit(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True
                cids = list(session["connected_clients"].keys())

                # A opens forge
                ws_a.send_json({"action": "MENU_CHOICE", "value": "4"})
                receive_until_type(ws_a, "WAITING_INPUT", "Forja")

                # Sends exit twice in rapid succession
                ws_a.send_json({"action": "MENU_CHOICE", "value": "exit"})
                ws_a.send_json({"action": "MENU_CHOICE", "value": "exit"})
                time.sleep(0.1)

                assert session["client_stages"].get(cids[0]) == "normal"

    # 3. Prontidão com comportamento adversarial
    def test_inventory_during_ready_removes_ready(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True

                # A marks ready
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                time.sleep(0.1)
                assert "a" in session["ready_players"]

                # A opens inventory
                ws_a.send_json({"action": "OPEN_INVENTORY"})
                time.sleep(0.1)

                # A must be automatically removed from ready list
                assert "a" not in session["ready_players"]

    def test_ready_consensus_after_disconnect(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True

                # B marks ready
                ws_b.send_json({"action": "MENU_CHOICE", "value": "1"})
                time.sleep(0.1)
                assert "b" in session["ready_players"]

                # A disconnects (simulate timeout/disconnect)
                ws_a.close()
                time.sleep(0.2)

                # Ready consensus must trigger immediately (waiting_for_ready becomes False)
                assert session.get("waiting_for_ready") is False

    def test_reconnect_preserves_ready(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True

                # A marks ready
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                time.sleep(0.1)
                assert "a" in session["ready_players"]

                # A disconnects
                ws_a.close()
                time.sleep(0.1)

                # A reconnects
                with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a_new:
                    time.sleep(0.1)
                    # A must still be marked as ready since ready state maps by name "a"
                    assert "a" in session["ready_players"]

    # 4. Ordem de mensagens fora de sequência (race condition real)
    @pytest.mark.anyio
    async def test_race_condition_buying_legendary(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                cids = list(session["connected_clients"].keys())

                # Set legendary draft stage
                session["client_stages"][cids[0]] = "legendary_draft"
                session["client_stages"][cids[1]] = "legendary_draft"
                world.state.set_flag("legendary_draft_item", "espada_lendaria")
                world.state.set_flag("legendary_draft_claimed_by", None)

                errors = []
                def claim_a():
                    try:
                        ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                    except Exception as e:
                        errors.append(e)

                def claim_b():
                    try:
                        ws_b.send_json({"action": "MENU_CHOICE", "value": "1"})
                    except Exception as e:
                        errors.append(e)

                t1 = threading.Thread(target=claim_a)
                t2 = threading.Thread(target=claim_b)
                t1.start()
                t2.start()
                t1.join()
                t2.join()

                time.sleep(0.1)

                # Verify only one claimed it
                claimed_by = world.state.get_flag("legendary_draft_claimed_by")
                assert claimed_by in ["A", "B"]

    # 5. Estado inconsistente entre GameState e frontend
    def test_reconnect_syncs_persisted_state(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True
                player_a.gold = 100

                # A opens forge
                ws_a.send_json({"action": "MENU_CHOICE", "value": "4"})
                receive_until_type(ws_a, "WAITING_INPUT", "Forja")

                # A buys Soldier Sword
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                time.sleep(0.05)

                # A disconnects immediately
                ws_a.close()
                time.sleep(0.1)

                # A reconnects
                with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a_new:
                    # Sync state should be received
                    state_msg = receive_until_type(ws_a_new, "STATE_UPDATE")
                    player_data = state_msg["state"]["player"]
                    
                    # Gold and item must reflect the persisted state
                    assert player_data["gold"] == 70
                    assert any(item["id"] == "espada_soldado" for item in player_data["inventory"])

    # 6. Sair da vila com estados pendentes
    def test_travel_start_forces_menu_exit_with_warning(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]

        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            receive_until_type(ws_a, "LOBBY_UPDATE")
            client.post(f"/api/game/join/{lobby_code}")

            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                receive_until_type(ws_b, "LOBBY_UPDATE")

                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)

                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True
                cids = list(session["connected_clients"].keys())

                # B opens forge
                ws_b.send_json({"action": "MENU_CHOICE", "value": "4"})
                receive_until_type(ws_b, "WAITING_INPUT", "Forja")
                assert session["client_stages"].get(cids[1]) == "forge"

                # A marks ready
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                time.sleep(0.05)

                # B marks ready from within forge menu (forces travel start)
                ws_b.send_json({"action": "PLAYER_READY"})
                
                # B must receive warning narrative text
                warning_msg = receive_until_type(ws_b, "NARRATIVE_TEXT", "A party partiu! Você foi retirado da forja")
                assert warning_msg is not None

                # B's stage must be reset to normal
                assert session["client_stages"].get(cids[1]) == "normal"
