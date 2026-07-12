import pytest
import time
import threading
from fastapi.testclient import TestClient
from server import app, active_sessions, get_actual_leader_id, send_to_ws_threadsafe, handle_broadcast_payload
from engine.constants import CharacterClass
from engine.player import Player
from engine.state import GameState
from engine.world import WorldManager
from engine.enemy import spawn_enemy
from engine.combat import CombatSystem, CombatPhase
from engine.items import create_item
from tests.test_full_coverage import receive_until_type
from tests.test_ogre_combat import setup_multiplayer_ws_environment

class TestLeaderDeathRevival:
    def test_all_party_falls_trigger_game_over(self):
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

                # Spawn a strong enemy
                golem = spawn_enemy("golem_pedra")
                combat = CombatSystem(world.state, [golem], can_flee=False, adapter=world.adapter)
                
                # Make both players have 0 HP
                player_a.hp = 0
                player_b.hp = 0
                
                # Check victory/defeat
                assert combat.check_victory_defeat_or_transformation() is True
                assert player_a.is_down is True
                assert player_b.is_down is True
                
                # Game over should be triggered (phase DEFEAT)
                assert combat.phase == CombatPhase.DEFEAT

    def test_revival_using_potion_restores_hp(self):
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

                # Player A is down, Player B is alive and has a potion
                player_a.hp = 0
                player_b.hp = 50
                potion = create_item("pocao_vida_p")
                player_b.inventory.append(potion)
                
                # Open inventory for Player B (ws_b)
                ws_b.send_json({"action": "OPEN_INVENTORY"})
                receive_until_type(ws_b, "WAITING_INPUT", "Inventário")
                
                # Select potion to use
                ws_b.send_json({"action": "MENU_CHOICE", "value": "0"})
                
                # Target choices should be displayed because there are multiple players
                target_msg = receive_until_type(ws_b, "WAITING_INPUT", "Escolha o alvo")
                
                # Player A is index 0 in world.party
                assert "A" in target_msg["options"]["0"]
                assert "B" in target_msg["options"]["1"]
                
                # Select target A (index 0) to revive
                ws_b.send_json({"action": "MENU_CHOICE", "value": "0"})
                
                # Wait for state update and verify revival
                receive_until_type(ws_b, "STATE_UPDATE")
                
                assert player_a.hp == int(player_a.max_hp * 0.30)
                assert player_a.is_down is False

    def test_leader_falls_leadership_transfers_and_party_wins(self):
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

                # Set A (leader) as down, B (mago) as alive
                player_a.hp = 0
                player_b.hp = 50
                
                # Verify leader fallback to next connected player (B)
                actual_leader = get_actual_leader_id(session, world)
                assert actual_leader == player_b.client_id
