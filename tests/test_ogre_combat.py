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
from engine.dto import NarrativeText, CombatNarrativeMoment
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

class TestOgreCombat:
    def test_ogre_combat_ends_via_hook_and_narrative_moment(self):
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

                # Spawn Ogre
                ogre = spawn_enemy("ogro_cabana")

                def ogre_hook(combat_sys):
                    if ogre.hp / ogre.max_hp <= 0.20 and not world.state.get_flag("ogre_dialogue_triggered"):
                        world.state.set_flag("ogre_dialogue_triggered", True)
                        text = "O ogro cai de joelhos..."
                        sub_opt = {
                            "1": "Poupar o Ogro Drogg",
                            "2": "Finalizar o Ogro"
                        }
                        combat_sys.adapter.broadcast(CombatNarrativeMoment(text, sub_opt).to_dict())
                        decision = combat_sys.adapter._wait_for_input()
                        if decision == "1":
                            world.state.set_flag("poupou_ogro", True)
                            combat_sys.adapter.emit(NarrativeText("Poupado!"))
                            return "END_COMBAT"
                        else:
                            world.state.set_flag("poupou_ogro", False)
                            combat_sys.adapter.emit(NarrativeText("Matou!"))
                            ogre.hp = 0
                            return "END_COMBAT"
                    return None

                combat = CombatSystem(world.state, [ogre], can_flee=False, turn_hook=ogre_hook, adapter=world.adapter)
                ogre.hp = 10 # Low HP to trigger the hook immediately on TURN_START
                world.active_combat = combat
                combat.phase = CombatPhase.TURN_START

                # Start advance_state in background thread
                t = threading.Thread(target=combat.advance_state)
                t.start()

                # Expect COMBAT_MOMENT payload on both clients
                msg_a = receive_until_type(ws_a, "COMBAT_MOMENT")
                msg_b = receive_until_type(ws_b, "COMBAT_MOMENT")

                assert "O ogro cai de joelhos..." in msg_a["text"]
                assert "1" in msg_a["options"]

                # Leader A selects "1" (Poupar)
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})

                t.join(timeout=2.0)
                assert not t.is_alive()

                # Verify combat has ended and combat_state is None
                assert world.active_combat is None
                assert world.state.combat_state is None
                assert world.state.get_flag("poupou_ogro") is True

                # Wait for clean state update to make sure it was broadcasted
                msg_a_state = receive_until_type(ws_a, "STATE_UPDATE")
                assert msg_a_state["state"]["combat_state"] is None
