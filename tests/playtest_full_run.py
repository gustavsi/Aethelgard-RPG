import sys
import os
import json
import time
import anyio
import traceback
from fastapi.testclient import TestClient

# Ensure import path is correct
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app, active_sessions
from engine.constants import CharacterClass
from engine.player import Player

# Apply God Stats monkeypatch to ensure players survive all content
def setup_god_stats(self):
    self.max_hp = 9999
    self.max_mp = 9999
    self.forca = 999
    self.inteligencia = 999
    self.agilidade = 999
    self.vitalidade = 999

Player.setup_class_stats = setup_god_stats

def receive_json_nowait(ws):
    try:
        message = ws._send_rx.receive_nowait()
        if message["type"] == "websocket.send":
            if "text" in message:
                return json.loads(message["text"])
            elif "bytes" in message:
                return json.loads(message["bytes"].decode("utf-8"))
    except anyio.WouldBlock:
        return None
    except anyio.ClosedResourceError as e:
        raise e
    except Exception as e:
        print(f"[-] ERROR in receive_json_nowait: {e}")
        traceback.print_exc()
        raise e
    return None

def run_variation(variation_name: str, leader_class: str, member_class: str, recruit_elena: bool):
    print(f"\n==================================================")
    print(f" RUNNING VARIATION: {variation_name}")
    print(f" Leader: {leader_class} | Member: {member_class} | Recruit Elena: {recruit_elena}")
    print(f"==================================================")
    
    client = TestClient(app)
    
    # 1. Create a session
    res = client.post("/api/game/new")
    if res.status_code != 200:
        print(f"[-] Failed to create session: {res.text}")
        return False
        
    res_data = res.json()
    session_id = res_data["session_id"]
    lobby_code = res_data["lobby_code"]
    
    print(f"[+] Session created: {session_id}, Lobby: {lobby_code}")
    
    last_state = {}
    narrative_logs = []
    
    # Track metrics
    hp_history = []
    mp_history = []
    lvl_history = []
    steps_count = 0
    max_steps = 300 # Increased step limit for more complex flows
    
    # Interaction/Validation flags
    leader_options_validated = False
    interacted_forge_a = False
    interacted_elder_b = False
    interacted_tavern_b = False
    
    try:
        # Nest the context managers so they are correctly initialized
        with client.websocket_connect(f"/ws/{session_id}?name=Alpha&class={leader_class}") as ws_a:
            # Drain A connect lobby update
            while receive_json_nowait(ws_a):
                pass
                
            client.post(f"/api/game/join/{lobby_code}")
            with client.websocket_connect(f"/ws/{session_id}?name=Beta&class={member_class}") as ws_b:
                # Drain B connect lobby update
                while receive_json_nowait(ws_b):
                    pass
                    
                # Start game
                ws_a.send_json({"action": "START_GAME"})
                
                sent_ready_a = False
                sent_ready_b = False
                
                # For stuck/liveness checks
                last_prompt_a = ""
                last_prompt_b = ""
                stuck_counter_a = 0
                stuck_counter_b = 0
                
                start_time = time.time()
                while (time.time() - start_time) < 90:
                    
                    # Drain one message from A, then B, until both queues are empty for this tick
                    processed_any = False
                    
                    data_a = receive_json_nowait(ws_a)
                    if data_a:
                        processed_any = True
                        msg_type = data_a.get("type")
                        if msg_type == "STATE_UPDATE":
                            last_state = data_a.get("state", {})
                            p_info = last_state.get("player", {})
                            if p_info:
                                hp_history.append(p_info.get("hp"))
                                mp_history.append(p_info.get("mp"))
                                lvl_history.append(p_info.get("level"))
                        elif msg_type == "NARRATIVE_TEXT":
                            narrative_logs.append(data_a.get("content"))
                        elif msg_type == "ERROR":
                            raise Exception(f"Leader WebSocket received ERROR: {data_a.get('message')}")
                        elif msg_type == "GAME_OVER":
                            raise Exception(f"Game Over reached: {data_a.get('message')}")
                        elif msg_type == "WAITING_INPUT":
                            prompt = data_a.get("prompt", "") or ""
                            options = data_a.get("options") or {}
                            print(f"[Leader Prompt] {prompt} {options}")
                            
                            # Liveness check
                            if prompt == last_prompt_a:
                                stuck_counter_a += 1
                                if stuck_counter_a > 12:  # Same prompt for too long
                                    raise Exception(f"Liveness failure: Leader stuck at prompt '{prompt}'")
                            else:
                                last_prompt_a = prompt
                                stuck_counter_a = 0
                            
                            is_leader_choice = ("Quem será o líder da party" in prompt) or ("Quem deve liderar" in prompt)
                            is_oakhaven = ("Para onde o grupo deseja ir?" in prompt)
                            is_ready_prompt = ("Aguardando" in prompt) and ("Oakhaven" in prompt or "Vila" in prompt)
                            is_generic_ready = ("Aguardando a party se preparar" in prompt) or ("Aguardando o líder" in prompt)
                            
                            val = None
                            is_shop = "comprar" in prompt.lower() or "loja" in prompt.lower() or "vendedor" in prompt.lower()
                            if is_shop:
                                exit_key = next((k for k, v in options.items() if "sair" in v.lower() or "voltar" in v.lower() or k == "exit"), None)
                                if exit_key:
                                    val = exit_key
                            
                            if val is not None:
                                pass
                            elif is_leader_choice:
                                # Validate option length and content
                                if len(options) != 2:
                                    raise Exception(f"Leader Choice option length error. Got: {options}")
                                if not any("Alpha" in str(v) for v in options.values()) or not any("Beta" in str(v) for v in options.values()):
                                    raise Exception(f"Leader Choice values missing Alpha/Beta names. Got: {options}")
                                leader_options_validated = True
                                val = "1"
                            elif is_oakhaven:
                                # Main town loop choices (once ready check is resolved)
                                val = "6" # Travel to Whisper Caves
                            elif is_ready_prompt:
                                if not interacted_forge_a:
                                    val = "4" # Visitar a Forja
                                else:
                                    if not sent_ready_a and "Estou pronto para partir" in str(options):
                                        val = "1"
                                        sent_ready_a = True
                            elif prompt.startswith("⚒️ Forja"):
                                if not interacted_forge_a and "1" in options:
                                    val = "1" # Buy Sword
                                    interacted_forge_a = True
                                else:
                                    val = "exit"
                            elif is_generic_ready:
                                if not sent_ready_a and "Estou pronto para partir" in str(options):
                                    val = "1"
                                    sent_ready_a = True
                            elif options:
                                sent_ready_a = False
                                val = "0" if "0" in options else "1"
                            else:
                                val = "1"
                                
                            if val is not None:
                                print(f"[Leader Sent] Choice: {val}")
                                steps_count += 1
                                ws_a.send_json({"action": "MENU_CHOICE", "value": val})

                    data_b = receive_json_nowait(ws_b)
                    if data_b:
                        processed_any = True
                        msg_type = data_b.get("type")
                        if msg_type == "ERROR":
                            raise Exception(f"Member WebSocket received ERROR: {data_b.get('message')}")
                        elif msg_type == "GAME_OVER":
                            raise Exception(f"Game Over reached on Member side: {data_b.get('message')}")
                        elif msg_type == "WAITING_INPUT":
                            prompt_b = data_b.get("prompt", "") or ""
                            options = data_b.get("options") or {}
                            print(f"[Member Prompt] {prompt_b} {options}")
                            
                            # Liveness check
                            if prompt_b == last_prompt_b:
                                stuck_counter_b += 1
                                if stuck_counter_b > 12:
                                    raise Exception(f"Liveness failure: Member stuck at prompt '{prompt_b}'")
                            else:
                                last_prompt_b = prompt_b
                                stuck_counter_b = 0
                                
                            is_ready_prompt = ("Aguardando" in prompt_b) and ("Oakhaven" in prompt_b or "Vila" in prompt_b)
                            is_generic_ready = ("Aguardando" in prompt_b)
                            val = None
                            is_shop = "comprar" in prompt_b.lower() or "loja" in prompt_b.lower() or "vendedor" in prompt_b.lower()
                            if is_shop:
                                exit_key = next((k for k, v in options.items() if "sair" in v.lower() or "voltar" in v.lower() or k == "exit"), None)
                                if exit_key:
                                    val = exit_key
                            
                            if val is not None:
                                pass
                            elif is_ready_prompt:
                                if not interacted_elder_b:
                                    val = "6" # Speak to Elder Alistair
                                elif recruit_elena and not interacted_tavern_b:
                                    val = "5" # Visitar a Taverna
                                else:
                                    if not sent_ready_b and "Estou pronto para partir" in str(options):
                                        val = "1"
                                        sent_ready_b = True
                            elif "Ancião" in prompt_b:
                                if "1" in options:
                                    val = "1" # Accept quest
                                    interacted_elder_b = True
                                else:
                                    val = "exit"
                            elif prompt_b.startswith("⚒️ Forja"):
                                val = "exit"
                            elif prompt_b.startswith("🍺 Taverna"):
                                if recruit_elena and not interacted_tavern_b:
                                    val = "1" # Falar com Elena
                                else:
                                    val = "exit"
                            elif "Elena" in prompt_b or "Quem é você?" in prompt_b or "relíquia sagrada" in prompt_b:
                                val = "1" # Yes / Accept / Honest
                                # If we are in the last stage of Elena dialogue, set interacted_tavern_b to True
                                if "relíquia sagrada" in prompt_b or "arco está a seu serviço" in prompt_b or "Quem é você?" in prompt_b:
                                    interacted_tavern_b = True
                            elif is_generic_ready:
                                if not sent_ready_b and "Estou pronto para partir" in str(options):
                                    val = "1"
                                    sent_ready_b = True
                            else:
                                sent_ready_b = False
                                val = "0" if "0" in options else "1"
                            
                            if val is not None:
                                print(f"[Member Sent] Choice: {val}")
                                steps_count += 1
                                ws_b.send_json({"action": "MENU_CHOICE", "value": val})
                            
                    if not processed_any:
                        time.sleep(0.01)
                            
                    # 3. Check ending conditions
                    if last_state and last_state.get("flags", {}).get("malakar_derrotado"):
                        print("[+] Defeated Malakar! Ending reached.")
                        break
                    if last_state and (last_state.get("flags", {}).get("dark_lord_ending") or 
                                       last_state.get("flags", {}).get("hero_of_light_ending") or 
                                       last_state.get("flags", {}).get("neutral_wanderer_ending")):
                        print("[+] Ending achieved!")
                        break
                        
                    # Check for thread exceptions
                    world = active_sessions.get(session_id, {}).get("world")
                    if world and getattr(world, "_crash_exception", None):
                        raise Exception(f"Engine thread crashed: {world._crash_exception}")
                        
                    time.sleep(0.01)
                    
    except Exception as e:
        print(f"[-] ERROR IN VARIATION {variation_name}:")
        traceback.print_exc()
        return False
        
    finally:
        # Shutdown sessions safely
        if session_id in active_sessions:
            active_sessions[session_id]["adapter"].shutdown_event.set()
            active_sessions.pop(session_id, None)
            
    # Post-run validation
    print(f"\n--- VARIATION {variation_name} RESULTS ---")
    print(f"Steps run: {steps_count}/{max_steps}")
    print(f"Final Player HP: {last_state.get('player', {}).get('hp')} / {last_state.get('player', {}).get('max_hp')}")
    print(f"Final Player MP: {last_state.get('player', {}).get('mp')} / {last_state.get('player', {}).get('max_mp')}")
    print(f"Final Player Level: {last_state.get('player', {}).get('level')}")
    print(f"Active Flags: {last_state.get('flags', {})}")
    
    # Assertions for our critical validation scenarios
    if not leader_options_validated:
        print("[-] Assert Failure: Leader choice options not validated.")
        return False
    if not interacted_forge_a:
        print("[-] Assert Failure: Leader did not interact with Forge.")
        return False
    if not interacted_elder_b:
        print("[-] Assert Failure: Member did not interact with Elder Alistair.")
        return False
    if recruit_elena and not last_state.get("flags", {}).get("elena_recrutada"):
        print("[-] Assert Failure: Elena recruitment enabled but elena_recrutada is not True in flags.")
        return False
        
    print("[+] All validation assertions passed!")
    
    # Check metric consistency
    print(f"HP History sample: {hp_history[:10]} ... {hp_history[-10:] if len(hp_history) > 10 else ''}")
    print(f"MP History sample: {mp_history[:10]} ... {mp_history[-10:] if len(mp_history) > 10 else ''}")
    print(f"Lvl History sample: {lvl_history[:10]} ... {lvl_history[-10:] if len(lvl_history) > 10 else ''}")
    
    print("\n--- LAST 50 NARRATIVE LOGS ---")
    for log in narrative_logs[-50:]:
        print(log.strip())
        
    is_hero_of_light = last_state.get("flags", {}).get("hero_of_light_ending", False) or last_state.get("flags", {}).get("malakar_derrotado", False)
    print(f"Ending Success: {is_hero_of_light}")
    return True

if __name__ == "__main__":
    # Run Variation 1: Cleric (recruits Elena)
    cleric_success = run_variation("Variation 1: Cleric in Party", "GUERREIRO", "CLERIGO", True)
    
    # Run Variation 2: Ladino (does not recruit Elena)
    ladino_success = run_variation("Variation 2: Ladino in Party", "LADINO", "MAGO", False)
    
    print("\n==================================================")
    print(f"ALL TESTS COMPLETED.")
    print(f"Cleric Run: {'SUCCESS' if cleric_success else 'FAILED'}")
    print(f"Ladino Run: {'SUCCESS' if ladino_success else 'FAILED'}")
    print("==================================================")
