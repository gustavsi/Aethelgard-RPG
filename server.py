import asyncio
import json
import threading
import os
import string
import random
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging

from engine.world import WorldManager
from engine.player import Player
from engine.constants import CharacterClass
from engine.adapter import UIAdapter, WebUIAdapter
from engine.dto import ChoiceRequested, PressAnyKey, NarrativeText, ClearScreen, SoundEffect, AsciiArt, VisualEffect
from engine.exceptions import EngineShutdownException, GameOverException
from engine.save_system import load_game, get_save_path, merge_lobby_party_with_save
from engine.utils import strip_ansi
from engine.combat import CombatPhase, Command
from engine.items import Weapon, Armor, Consumable
import engine.menu_manager as menu_mgr

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn")

background_tasks = set()

def send_to_ws_threadsafe(session, ws, payload):
    try:
        target_loop = None
        for cid, (target_ws, _, _) in list(session.setdefault("connected_clients", {}).items()):
            if target_ws == ws:
                target_loop = session.setdefault("client_loops", {}).get(cid)
                break
        if target_loop is None:
            target_loop = session["loop"]
            
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
            
        import inspect
        coro = ws.send_json(payload)
        if inspect.iscoroutine(coro):
            if current_loop is not None and current_loop == target_loop:
                task = current_loop.create_task(coro)
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)
            else:
                def schedule():
                    task = target_loop.create_task(coro)
                    background_tasks.add(task)
                    task.add_done_callback(background_tasks.discard)
                target_loop.call_soon_threadsafe(schedule)
        else:
            pass
    except Exception as ex:
        print(f"[-] Error in send_to_ws_threadsafe: {ex}")
        logger.error(f"Error in send_to_ws_threadsafe: {ex}")

def get_actual_leader_id(session, world):
    base_leader = session["leader_id"]
    if world and world.state.get_flag("party_lider"):
        leader_name = world.state.get_flag("party_lider")
        for cid, (ws, name, cls) in session["connected_clients"].items():
            if name and name.lower() == leader_name.lower():
                base_leader = cid
                break
            if cls and cls.lower() == leader_name.lower():
                base_leader = cid
                break

    if world and getattr(world, 'party', None):
        leader_player = next((p for p in world.party if getattr(p, 'client_id', None) == base_leader or (base_leader == 'leader' and getattr(p, 'client_id', None) is None)), None)
        if leader_player and leader_player.hp > 0:
            return base_leader
            
        for cid in list(session["connected_clients"].keys()):
            p = next((x for x in world.party if getattr(x, 'client_id', None) == cid or (cid == 'leader' and getattr(x, 'client_id', None) is None)), None)
            if p and p.hp > 0:
                return cid
                
    return base_leader

class MulticastWebUIAdapter(WebUIAdapter):
    def __init__(self, broadcast_callback, leader_callback):
        super().__init__(ws_callback=broadcast_callback)
        self.leader_callback = leader_callback
        self.broadcast = broadcast_callback

    def emit(self, event) -> any:
        if isinstance(event, (ChoiceRequested, PressAnyKey)):
            # STATE_UPDATE para todos
            if getattr(self, 'state', None):
                self.broadcast({"type": "STATE_UPDATE", "state": self.state.to_dict()})
            
            broadcast_to_all = getattr(event, "broadcast_to_all", False)
            payload = event.to_dict()
            if isinstance(event, ChoiceRequested):
                payload["prompt"] = strip_ansi(payload["prompt"])
                if "options" in payload:
                    payload["options"] = {k: strip_ansi(v) for k, v in payload["options"].items()}
            else:
                payload["prompt"] = strip_ansi(payload["prompt"])
            
            if broadcast_to_all:
                session_id = getattr(self.state, "session_id", None)
                if session_id:
                    session = active_sessions.get(session_id)
                    if session:
                        client_stages = session.setdefault("client_stages", {})
                        for cid in list(session["connected_clients"].keys()):
                            client_stages[cid] = "voting"
                self.broadcast(payload)
                return None
                
            self.last_waiting_input = payload
            self.leader_callback(payload)
            return self._wait_for_input()
        elif isinstance(event, NarrativeText):
            payload = event.to_dict()
            payload["content"] = strip_ansi(payload["content"])
            self.broadcast(payload)
            return None
        elif isinstance(event, SoundEffect):
            self.broadcast(event.to_dict())
            return None
        elif isinstance(event, VisualEffect):
            self.broadcast(event.to_dict())
            return None
        # AsciiArt / ClearScreen: web client ignores (uses images + no terminal clear)
        return None

    def collect_all_votes(self, session_id: str) -> dict:
        import time
        session = active_sessions.get(session_id)
        if not session:
            return {}
        
        session["votes"] = {}
        
        start_time = time.time()
        timeout = getattr(self, "voting_timeout", 10.0)
        
        while not self.shutdown_event.is_set():
            connected = list(session["connected_clients"].keys())
            votes = session.get("votes", {})
            if len(votes) >= len(connected):
                break
            if time.time() - start_time > timeout:
                break
            time.sleep(0.1)
            
        return session.get("votes", {})

def run_engine_thread(world: WorldManager, adapter: WebUIAdapter, output_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    original_ws_callback = adapter.ws_callback
    
    # This is a fallback wrapper if standard emit is called by code outside MulticastWebUIAdapter
    def send_to_ws(payload: dict):
        if payload.get("type") == "STATE_UPDATE":
            adapter.last_state = payload
        elif payload.get("type") == "WAITING_INPUT":
            adapter.last_waiting_input = payload
        loop.call_soon_threadsafe(output_queue.put_nowait, payload)
        if original_ws_callback:
            original_ws_callback(payload)
        
    adapter.ws_callback = send_to_ws
    
    from engine.console import WebBridgeStorage
    
    class BridgeWrapper:
        def send_to_client(self, msg_type, content):
            # Fallback console bridge mapping
            if msg_type == "TEXT":
                adapter.ws_callback({"type": "NARRATIVE_TEXT", "content": strip_ansi(content)})
            elif msg_type == "INPUT":
                adapter.ws_callback({"type": "STATE_UPDATE", "state": world.state.to_dict()})
                adapter.ws_callback({"type": "WAITING_INPUT", "prompt": strip_ansi(content)})
            elif msg_type == "PRESS_KEY":
                adapter.ws_callback({
                    "type": "WAITING_INPUT",
                    "subtype": "PRESS_ANY_KEY",
                    "prompt": strip_ansi(content) if isinstance(content, str) else "Pressione para continuar..."
                })
            elif msg_type == "MENU":
                adapter.ws_callback({"type": "STATE_UPDATE", "state": world.state.to_dict()})
                prompt = strip_ansi(content.get("prompt", ""))
                opts = {k: strip_ansi(v) for k, v in content.get("options", {}).items()}
                adapter.ws_callback({"type": "WAITING_INPUT", "prompt": prompt, "options": opts})
            elif msg_type == "ERROR":
                adapter.ws_callback({"type": "ERROR", "message": strip_ansi(content)})
            elif msg_type == "BOX":
                lines = content.get("lines", []) if isinstance(content, dict) else []
                title = content.get("title", "") if isinstance(content, dict) else str(content)
                separator = "─" * 40
                full_text = f"\n✨ {title} ✨\n{separator}\n" + "\n".join(lines) + f"\n{separator}"
                adapter.ws_callback({"type": "NARRATIVE_TEXT", "content": strip_ansi(full_text)})
                
        def receive_from_client(self):
            return adapter._wait_for_input()
            
    WebBridgeStorage.set_bridge(BridgeWrapper())
    UIAdapter.set_instance(adapter)

    try:
        # Initial trigger
        adapter.ws_callback({"type": "STATE_UPDATE", "state": world.state.to_dict()})
        if world.state.get_flag("is_arena"):
            from engine.arena import run_arena_loop
            run_arena_loop(world, adapter)
        else:
            world.run_game()
        adapter.ws_callback({"type": "GAME_OVER", "message": "Fim de jogo."})
    except EngineShutdownException:
        logger.info("Engine thread shutting down gracefully.")
    except GameOverException as e:
        logger.info(f"Player defeated: {e}")
        adapter.ws_callback({"type": "GAME_OVER", "message": str(e)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Engine crashed: {e}")
        adapter.ws_callback({"type": "ERROR", "message": str(e)})

from datetime import datetime, timedelta

def save_lobby_code(lobby_code: str, session_id: str):
    path = os.path.join("saves", "lobby_codes.json")
    os.makedirs("saves", exist_ok=True)
    
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
            
    data[lobby_code] = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save lobby codes: {e}")

def load_lobby_codes() -> dict:
    path = os.path.join("saves", "lobby_codes.json")
    if not os.path.exists(path):
        return {}
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
        
    filtered = {}
    now = datetime.now()
    for code, entry in data.items():
        try:
            created_at = datetime.fromisoformat(entry["created_at"])
            if now - created_at < timedelta(hours=2):
                filtered[code] = entry
        except Exception:
            pass
            
    # Write back clean filtered list
    try:
        os.makedirs("saves", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save cleaned lobby codes: {e}")
        
    return {code: entry["session_id"] for code, entry in filtered.items()}

def handle_broadcast_payload(session, payload):
    if payload.get("type") == "STATE_UPDATE":
        session["adapter"].last_state = payload
        state_data = payload.get("state", {})
        combat_state_data = state_data.get("combat_state") or {}
        phase = combat_state_data.get("phase")
        logger.info(f"handle_broadcast_payload: combat phase={phase}")
        if phase == "WAITING_ALL_PLAYERS":
            logger.info(f"DISPATCHING WAITING_INPUT to {len(session['connected_clients'])} clients")
            world = session.get("world")
            combat = getattr(world, 'active_combat', None) if world else None
            if combat:
                from engine.constants import StatusEffect
                sync_engine_leader(session, world)
                for target_id, (target_ws, _, _) in list(session["connected_clients"].items()):
                    if target_id in combat.pending_actions:
                        continue
                    player = next((p for p in world.party if getattr(p, 'client_id', None) == target_id), None)
                    # Stunned living players skip; downed get limited menu (PRD B4)
                    if player and player.hp > 0 and StatusEffect.ATORDOADO in player.status_effects:
                        continue
                    if player and player.hp <= 0:
                        from engine.feature_flags import FLAGS as _FF
                        if not _FF.content_systems:
                            continue
                        if target_id not in combat.client_menu_stages:
                            from engine.downed_roles import downed_menu_options
                            opts = downed_menu_options(world.state)
                            combat.client_menu_stages[target_id] = "downed"
                            send_to_ws_threadsafe(session, target_ws, {
                                "type": "WAITING_INPUT",
                                "prompt": f"{player.name} está caído. O que fazer?",
                                "options": opts,
                                "my_client_id": target_id,
                                "leader_client_id": get_actual_leader_id(session, world),
                            })
                        continue
                    
                    if target_id not in combat.client_menu_stages:
                        from engine.feature_flags import FLAGS as _FF
                        options = {"1": "Atacar"}
                        if player:
                            skills = player.get_skills()
                            if skills:
                                options["2"] = "Habilidades"
                        options["4"] = "Defender"
                        if combat.can_flee:
                            options["5"] = "Fugir"
                        if _FF.combat_intent:
                            options["6"] = "🛑 Interromper"
                            
                        combat.client_menu_stages[target_id] = "main"
                        
                        input_payload = {
                            "type": "WAITING_INPUT",
                            "prompt": "O que deseja fazer?",
                            "options": options,
                            "my_client_id": target_id,
                            "leader_client_id": get_actual_leader_id(session, world)
                        }
                        send_to_ws_threadsafe(session, target_ws, input_payload)
    elif payload.get("type") == "WAITING_INPUT":
        session["adapter"].last_waiting_input = payload
    elif payload.get("type") == "COMBAT_MOMENT":
        session["adapter"].last_waiting_input = payload
    elif payload.get("type") == "NARRATIVE_TEXT":
        log = session.setdefault("narrative_log", [])
        log.append(payload["content"])
        if len(log) > NARRATIVE_LOG_MAX:
            session["narrative_log"] = log[-NARRATIVE_LOG_MAX:]

def refresh_client_ui(session, client_id, world):
    combat = getattr(world, 'active_combat', None) if world else None
    if combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS:
        stage = combat.client_menu_stages.get(client_id, "main")
        if stage == "main":
            from engine.feature_flags import FLAGS as _FF
            options = {"1": "Atacar"}
            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
            if player:
                skills = player.get_skills()
                if skills:
                    options["2"] = "Habilidades"
            options["4"] = "Defender"
            if combat.can_flee:
                options["5"] = "Fugir"
            if _FF.combat_intent:
                options["6"] = "🛑 Interromper"
            
            payload = {
                "type": "WAITING_INPUT",
                "prompt": "O que deseja fazer?",
                "options": options,
                "my_client_id": client_id,
                "leader_client_id": get_actual_leader_id(session, world)
            }
        elif stage == "target":
            alive = [e for e in combat.enemies if e.is_alive()]
            opts = {str(i): e.name for i, e in enumerate(alive)}
            payload = {"type": "WAITING_INPUT", "prompt": "Escolha o alvo:", "options": opts,
                       "my_client_id": client_id, "leader_client_id": get_actual_leader_id(session, world)}
        elif stage == "skill":
            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
            skills = player.get_skills() if player else []
            opts = {str(i): f"{s.name} (MP:{s.mp})" for i, s in enumerate(skills)}
            payload = {"type": "WAITING_INPUT", "prompt": "Qual habilidade?", "options": opts,
                       "my_client_id": client_id, "leader_client_id": get_actual_leader_id(session, world)}
        else:
            payload = {"type": "WAITING_INPUT", "prompt": "", "options": None}
            
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)
    else:
        actual_leader = get_actual_leader_id(session, world)
        stage = session.setdefault("client_stages", {}).get(client_id, "normal")
        if stage == "inventory":
            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
            if not player:
                player = world.player
            opts = {str(i): f"{item.name} ({item.description})" for i, item in enumerate(player.inventory)}
            opts["exit"] = "Fechar Inventário"
            payload = {
                "type": "WAITING_INPUT",
                "prompt": f"🎒 Inventário de {player.name} (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um item:",
                "options": opts,
                "my_client_id": client_id,
                "leader_client_id": actual_leader
            }
            if client_id in session["connected_clients"]:
                ws = session["connected_clients"][client_id][0]
                send_to_ws_threadsafe(session, ws, payload)
        elif stage == "talents":
            send_talents_menu(session, client_id, world)
        elif stage == "party_stock":
            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
            if not player:
                player = world.player
            opts = {str(i): f"{item.name} ({item.description})" for i, item in enumerate(world.state.shared_inventory)}
            opts["exit"] = "Fechar Estoque"
            payload = {
                "type": "WAITING_INPUT",
                "prompt": f"🧪 Estoque da Party (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um consumível:",
                "options": opts,
                "my_client_id": client_id,
                "leader_client_id": actual_leader
            }
            if client_id in session["connected_clients"]:
                ws = session["connected_clients"][client_id][0]
                send_to_ws_threadsafe(session, ws, payload)
        elif session.get("waiting_for_ready", False):
            send_player_ready_prompt(session, client_id, world)
        else:
            if client_id == actual_leader and session["adapter"].last_waiting_input:
                ws = session["connected_clients"][client_id][0]
                payload = session["adapter"].last_waiting_input
                send_to_ws_threadsafe(session, ws, payload)
            else:
                payload = {
                    "type": "WAITING_INPUT",
                    "prompt": "Aguardando o líder...",
                    "options": {
                        "2": "🎒 Abrir Inventário",
                        "3": "🧪 Estoque da Party"
                    },
                    "my_client_id": client_id,
                    "leader_client_id": actual_leader
                }
                if client_id in session["connected_clients"]:
                    ws = session["connected_clients"][client_id][0]
                    send_to_ws_threadsafe(session, ws, payload)

def set_client_stage(session, client_id, world, stage):
    session.setdefault("client_stages", {})[client_id] = stage
    if stage not in ["normal", "voting"] and world and world.state:
        player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
        name_key = player.name.lower() if player else "herói"
        session.setdefault("ready_players", set()).discard(name_key)

def exit_client_submenu(session, client_id, world):
    """Return client to hub/ready UI after leaving a sub-menu (inventory, forge, etc.)."""
    session.setdefault("client_stages", {})[client_id] = "normal"
    refresh_client_ui(session, client_id, world)
    # Explicit re-send: if still waiting for ready, ensure prompt is not blank
    if session.get("waiting_for_ready", False):
        send_player_ready_prompt(session, client_id, world)

def sync_engine_leader(session, world):
    """Keep world.player / state.player aligned with the living actual leader (Bug #3)."""
    if not world or not getattr(world, "party", None):
        return
    actual_id = get_actual_leader_id(session, world)
    new_leader = next(
        (p for p in world.party if getattr(p, "client_id", None) == actual_id
         or (actual_id == "leader" and getattr(p, "client_id", None) is None)),
        None,
    )
    if not new_leader or new_leader is world.player:
        return
    # Move party companion to the active leader so narrative/combat still use it
    old = world.player
    companion = getattr(old, "companion", None)
    if companion and not getattr(new_leader, "companion", None):
        new_leader.companion = companion
        old.companion = None
    world.player = new_leader
    if world.state:
        world.state.player = new_leader

def migrate_combat_client_id(world, old_id, new_id):
    """Remap pending combat actions/menus when a player reconnects with a new UUID (Bug #4)."""
    if not world or not old_id or old_id == new_id:
        return
    combat = getattr(world, "active_combat", None)
    if not combat:
        return
    if old_id in combat.pending_actions:
        combat.pending_actions[new_id] = combat.pending_actions.pop(old_id)
    if old_id in combat.client_menu_stages:
        combat.client_menu_stages[new_id] = combat.client_menu_stages.pop(old_id)
    cache = getattr(combat, "_downed_players_cache", None)
    if cache is not None and old_id in cache:
        cache.discard(old_id)
        cache.add(new_id)

NARRATIVE_LOG_MAX = 100

def send_player_ready_prompt(session, client_id, world):
    if not world or not world.state:
        return
    if not session.get("waiting_for_ready", False):
        return
    stage = session.setdefault("client_stages", {}).get(client_id, "normal")
    if stage in ["inventory", "party_stock", "talents", "forge", "tavern", "elder", "elena_dialogue", "elena_dialogue_relic", "elder_recompensa", "legendary_draft", "voting"]:
        return
    actual_leader = get_actual_leader_id(session, world)
    
    player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
    name_key = player.name.lower() if player else "herói"
    is_ready = name_key in session.setdefault("ready_players", set())
    loc = world.state.current_location or "Mundo"
    
    if loc == "oakhaven":
        loc_name = "Vila de Oakhaven"
    elif loc == "vaelmoor":
        loc_name = "Porto de Vaelmoor"
    elif loc == "kragmoor":
        loc_name = "Minas de Kragmoor"
    else:
        loc_name = loc.capitalize() if loc else "Mundo"
    
    options = {
        "1": "⌛ Pronto! (Aguardando os outros)" if is_ready else "✅ Estou pronto para partir",
        "2": "🎒 Abrir Inventário",
        "3": "🧪 Estoque da Party"
    }
    
    # Semantic keys (forge/tavern/elder) — must NOT use "4"/"5"/"6".
    # Those numeric keys are reserved for the engine Oakhaven leader menu
    # (where "6" = travel to Whispering Caves). Colliding them blocked story progress.
    if loc == "oakhaven":
        options["forge"] = "⚒️ Visitar a Forja de Garrett"
        options["tavern"] = "🍺 Visitar a Taverna do Javali Saltitante"
        options["elder"] = "📜 Falar com o Ancião Alistair"
    elif loc == "vaelmoor":
        options["forge"] = "⚓ Visitar o Estaleiro de Vaelmoor"
        options["tavern"] = "🍺 Visitar a Taverna da Sereia Bêbada"
        options["elder"] = "⚓ Falar com a Capitã Ysolde"
    elif loc == "kragmoor":
        options["forge"] = "⚒️ Visitar a Forja Rúnica de Brokk"
        options["tavern"] = "🍺 Visitar a Taverna Subterrânea"
        options["elder"] = "⚒️ Falar com o Ferreiro Brokk"
        
    payload = {
        "type": "WAITING_INPUT",
        "prompt": f"Aguardando a party se preparar... ({loc_name})" if client_id == actual_leader else f"Aguardando o líder... ({loc_name})",
        "options": options,
        "my_client_id": client_id,
        "leader_client_id": actual_leader
    }
    if client_id in session["connected_clients"]:
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)

def send_forge_menu(session, client_id, world):
    player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None) or world.player
    loc = world.state.current_location if world else "oakhaven"
    leader_id = get_actual_leader_id(session, world)
    payload = menu_mgr.get_forge_menu(player, loc, client_id, leader_id)
    if client_id in session["connected_clients"]:
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)

def send_talents_menu(session, client_id, world):
    player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None) or world.player
    leader_id = get_actual_leader_id(session, world)
    payload, idx_to_talent = menu_mgr.get_talents_menu(player, client_id, leader_id)
    session.setdefault("client_talent_maps", {})[client_id] = idx_to_talent
    set_client_stage(session, client_id, world, "talents")
    if client_id in session["connected_clients"]:
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)

def send_tavern_menu(session, client_id, world):
    player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None) or world.player
    loc = world.state.current_location if world else "oakhaven"
    leader_id = get_actual_leader_id(session, world)
    elena_confronted = world.state.get_flag("elena_confronted")
    elena_recrutada = world.state.get_flag("elena_recrutada")
    payload = menu_mgr.get_tavern_menu(player, loc, client_id, leader_id, elena_confronted, elena_recrutada)
    if client_id in session["connected_clients"]:
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)

def send_elena_dialogue(session, client_id, world, step):
    leader_id = get_actual_leader_id(session, world)
    payload = menu_mgr.get_elena_dialogue(step, client_id, leader_id)
    if client_id in session["connected_clients"]:
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)

def send_elder_menu(session, client_id, world):
    player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None) or world.player
    loc = world.state.current_location if world else "oakhaven"
    leader_id = get_actual_leader_id(session, world)
    payload = menu_mgr.get_elder_menu(player, loc, client_id, leader_id)
    if client_id in session["connected_clients"]:
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)

def send_elder_recompensa_menu(session, client_id, world):
    leader_id = get_actual_leader_id(session, world)
    payload = menu_mgr.get_elder_recompensa_menu(client_id, leader_id)
    if client_id in session["connected_clients"]:
        ws = session["connected_clients"][client_id][0]
        send_to_ws_threadsafe(session, ws, payload)

# Session registries
sessions: dict = {}
active_sessions: dict = {}
lobby_codes = load_lobby_codes()

def generate_lobby_code() -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if code not in lobby_codes:
            return code

@app.post("/api/game/new")
async def start_new_game():
    session_id = str(uuid.uuid4())
    lobby_code = generate_lobby_code()
    
    lobby_codes[lobby_code] = session_id
    save_lobby_code(lobby_code, session_id)
    
    sessions[session_id] = {"type": "new", "lobby_code": lobby_code}
    return {"session_id": session_id, "lobby_code": lobby_code}

@app.post("/api/game/join/{lobby_code}")
async def join_lobby(lobby_code: str):
    code_upper = lobby_code.upper().strip()
    
    # 1. Verify code exists on disk and is not expired (< 2h)
    path = os.path.join("saves", "lobby_codes.json")
    exists_on_disk = False
    session_id = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
            if code_upper in disk_data:
                entry = disk_data[code_upper]
                created_at = datetime.fromisoformat(entry["created_at"])
                if datetime.now() - created_at < timedelta(hours=2):
                    exists_on_disk = True
                    session_id = entry["session_id"]
        except Exception:
            pass
            
    if not exists_on_disk:
        raise HTTPException(status_code=404, detail="Código inválido ou sessão expirada. Volte ao menu e peça um novo código.")
        
    # 2. Verify that the session is still active in memory
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="A sessão não está ativa em memória.")
        
    return {"session_id": session_id}

@app.post("/api/game/load")
async def load_game_route(session_id: str = None):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required to load game")
    
    save_path = get_save_path(session_id)
    if not os.path.exists(save_path):
        raise HTTPException(status_code=404, detail="Save file not found")
        
    sessions[session_id] = {"type": "load"}
    return {"session_id": session_id}

async def broadcast_lobby_update(session_id: str):
    session = active_sessions.get(session_id)
    if not session:
        return
        
    players = []
    leader_name = "Líder"
    for client_id, (_, p_name, p_class) in session["connected_clients"].items():
        is_leader = (client_id == session["leader_id"])
        if is_leader:
            leader_name = p_name
        players.append({
            "client_id": client_id,
            "name": p_name,
            "class": p_class,
            "is_leader": is_leader
        })
        
    payload = {
        "type": "LOBBY_UPDATE",
        "lobby_code": session["lobby_code"],
        "leader_id": session["leader_id"],
        "leader_name": leader_name,
        "players": players,
        "can_start": len(players) >= 1  # For testing/dev, allow 1+ players
    }
    
    # Broadcast to all connected sockets
    for client_id, (ws, _, _) in list(session["connected_clients"].items()):
        try:
            payload_copy = dict(payload)
            payload_copy["my_client_id"] = client_id
            await ws.send_json(payload_copy)
        except Exception as e:
            logger.error(f"Error broadcasting lobby update: {e}")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, name: str = None, char_class: str = None):
    await websocket.accept()
    
    player_class = websocket.query_params.get("class") or websocket.query_params.get("char_class") or "GUERREIRO"
    char_class = player_class
    
    is_test_client = (name is None)
    if not name:
        name = "Herói Web"
        
    logger.info(f"WebSocket connected for session: {session_id} (name: {name}, class: {char_class}, is_test: {is_test_client})")
    
    loop = asyncio.get_running_loop()
    
    if session_id not in active_sessions:
        session_info = sessions.get(session_id, {"type": "new"})
        lobby_code = session_info.get("lobby_code", "LOBBY1")
        
        active_sessions[session_id] = {
            "world": None,
            "adapter": None,
            "output_queue": asyncio.Queue(),
            "connected_clients": {},  # client_id -> (websocket, name, char_class)
            "client_loops": {},      # client_id -> loop
            "client_stages": {},     # client_id -> stage
            "leader_id": None,
            "game_started": False,
            "lobby_code": lobby_code,
            "engine_thread": None,
            "session_type": session_info["type"],
            "loop": loop,
            "connected": True,
            "narrative_log": [],
            "ready_players": set(),
            "waiting_for_ready": False
        }
        
    session = active_sessions[session_id]
    session["connected"] = True
    client_id = str(uuid.uuid4())
    
    # Assign leader if none exists
    if not session["leader_id"]:
        session["leader_id"] = client_id
        
    session["connected_clients"][client_id] = (websocket, name, char_class)
    session.setdefault("client_loops", {})[client_id] = loop
    print(f"[DEBUG websocket_endpoint] WebSocket connected: session {session_id}, client_id {client_id}, name {name}, class {char_class}")
    
    # Auto-start for test clients
    if is_test_client and not session["game_started"]:
        session["game_started"] = True
        
        # Build cooperative players list
        party_players = [Player(name, CharacterClass[char_class.upper()])]
        party_players[0].client_id = client_id
        leader_player = party_players[0]
        
        def broadcast_callback(payload):
            for target_id, (target_ws, _, _) in list(session["connected_clients"].items()):
                try:
                    payload_copy = dict(payload)
                    payload_copy["my_client_id"] = target_id
                    payload_copy["leader_client_id"] = get_actual_leader_id(session, session.get("world"))
                    send_to_ws_threadsafe(session, target_ws, payload_copy)
                except Exception:
                    pass
            handle_broadcast_payload(session, payload)
                    
        def leader_callback(payload):
            for target_id, (target_ws, _, _) in list(session["connected_clients"].items()):
                try:
                    payload_copy = dict(payload)
                    payload_copy["my_client_id"] = target_id
                    payload_copy["leader_client_id"] = get_actual_leader_id(session, session.get("world"))
                    send_to_ws_threadsafe(session, target_ws, payload_copy)
                except Exception:
                    pass
                    
        adapter = MulticastWebUIAdapter(broadcast_callback, leader_callback)
        session["adapter"] = adapter
        
        world = WorldManager(leader_player, adapter=adapter, party=party_players)
        world.state.session_id = session_id
        world.state.migrate_party_consumables()
        session["world"] = world
        
        engine_thread = threading.Thread(
            target=run_engine_thread,
            args=(world, adapter, session["output_queue"], loop),
            daemon=True
        )
        engine_thread.start()
        session["engine_thread"] = engine_thread
        
    # Broadcast or restore game
    elif not session["game_started"]:
        await broadcast_lobby_update(session_id)
    else:
        # Reconnection
        world = session.get("world")
        if world:
            for p in world.party:
                if p.name.lower() == name.lower():
                    old_cid = getattr(p, "client_id", None)
                    logger.info(f"Player {p.name} reconnected. Updating client_id to {client_id}")
                    migrate_combat_client_id(world, old_cid, client_id)
                    p.client_id = client_id
            if world.player and world.player.name.lower() == name.lower():
                logger.info(f"Leader reconnected. Updating leader_id to {client_id}")
                session["leader_id"] = client_id
            sync_engine_leader(session, world)
            
        adapter = session["adapter"]
        if adapter:
            if getattr(adapter, "last_state", None):
                await websocket.send_json(adapter.last_state)
            # Only replay a capped tail of narrative (Bug #13)
            for text in session.get("narrative_log", [])[-NARRATIVE_LOG_MAX:]:
                await websocket.send_json({"type": "NARRATIVE_TEXT", "content": text})
            
            combat = getattr(world, "active_combat", None) if world else None
            if combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS:
                refresh_client_ui(session, client_id, world)
            elif session.get("waiting_for_ready", False):
                send_player_ready_prompt(session, client_id, world)
            elif client_id == get_actual_leader_id(session, world):
                if getattr(adapter, "last_waiting_input", None):
                    await websocket.send_json(adapter.last_waiting_input)
            else:
                world = session.get("world")
                if world and not world.state.combat_state:
                    actual_leader = get_actual_leader_id(session, world)
                    payload = {
                        "type": "WAITING_INPUT",
                        "prompt": "Aguardando o líder...",
                        "options": {
                            "2": "🎒 Abrir Inventário",
                            "3": "🧪 Estoque da Party"
                        },
                        "my_client_id": client_id,
                        "leader_client_id": actual_leader
                    }
                    await websocket.send_json(payload)
                elif getattr(adapter, "last_waiting_input", None):
                    await websocket.send_json(adapter.last_waiting_input)
                
    try:
        while True:
            active_loop = asyncio.get_running_loop()
            session["loop"] = active_loop
            session.setdefault("client_loops", {})[client_id] = active_loop
            data = await websocket.receive_text()
            logger.info(f"Received from client {client_id}: {data}")
            
            try:
                parsed = json.loads(data)
                
                # Check for start game action in lobby
                if parsed.get("action") == "START_GAME":
                    if client_id == session["leader_id"] and not session["game_started"]:
                        session["game_started"] = True
                        
                        # Build cooperative players list
                        party_players = []
                        leader_player = None
                        for c_id, (_, p_name, p_class) in session["connected_clients"].items():
                            try:
                                cc = CharacterClass[p_class.upper()]
                            except Exception:
                                cc = CharacterClass.GUERREIRO
                            p = Player(p_name, cc)
                            p.client_id = c_id
                            party_players.append(p)
                            if c_id == session["leader_id"]:
                                leader_player = p
                                
                        if not leader_player:
                            leader_player = party_players[0]
                            
                        def broadcast_callback(payload):
                            # Send to all connected players
                            for target_id, (target_ws, _, _) in list(session["connected_clients"].items()):
                                try:
                                    payload_copy = dict(payload)
                                    payload_copy["my_client_id"] = target_id
                                    payload_copy["leader_client_id"] = get_actual_leader_id(session, session.get("world"))
                                    send_to_ws_threadsafe(session, target_ws, payload_copy)
                                except Exception as e:
                                    logger.error(f"Failed to multicast: {e}")
                            handle_broadcast_payload(session, payload)
                                    
                        def leader_callback(payload):
                            leader_id = get_actual_leader_id(session, session.get("world"))
                            
                            # Check for ready consensus intercept
                            world = session.get("world")
                            in_combat = (world.state.combat_state is not None) if (world and world.state) else False
                            total_players = len(session["connected_clients"])
                            connected_names = {name.lower() for (_, name, _) in session["connected_clients"].values() if name}
                            ready_players = len(session.setdefault("ready_players", set()).intersection(connected_names))
                            
                            is_waiting = session.get("waiting_for_ready", False)
                            if world and world.state and world.state.current_location == "tutorial":
                                is_waiting = False
                                
                            if not in_combat and total_players > 1 and is_waiting and ready_players < total_players:
                                session["pending_leader_choice"] = payload
                                for cid in list(session["connected_clients"].keys()):
                                    send_player_ready_prompt(session, cid, world)
                                return

                            if leader_id in session["connected_clients"]:
                                target_ws = session["connected_clients"][leader_id][0]
                                try:
                                    payload_copy = dict(payload)
                                    payload_copy["my_client_id"] = leader_id
                                    payload_copy["leader_client_id"] = leader_id
                                    send_to_ws_threadsafe(session, target_ws, payload_copy)
                                except Exception as e:
                                    logger.error(f"Failed to send to leader: {e}")
                                    
                        adapter = MulticastWebUIAdapter(broadcast_callback, leader_callback)
                        session["adapter"] = adapter
                        
                        if session["session_type"] == "load":
                            loaded_state = load_game(session_id)
                            if loaded_state:
                                # Restore saved stats onto lobby shells (Bug #5/#6)
                                merge_lobby_party_with_save(loaded_state, party_players)
                                world = WorldManager(loaded_state, adapter=adapter, party=loaded_state.party)
                                # Re-point leader after merge
                                leader_player = loaded_state.player
                            else:
                                world = WorldManager(leader_player, adapter=adapter, party=party_players)
                        else:
                            world = WorldManager(leader_player, adapter=adapter, party=party_players)
                        world.state.session_id = session_id
                        world.state.migrate_party_consumables()
                        if parsed.get("mode") == "arena":
                            world.state.set_flag("is_arena", True)
                        session["world"] = world
                        sync_engine_leader(session, world)
                        
                        # Send GAME_START screen transition to everyone
                        for target_id, (target_ws, _, _) in list(session["connected_clients"].items()):
                            await target_ws.send_json({
                                "type": "GAME_START",
                                "my_client_id": target_id,
                                "leader_client_id": get_actual_leader_id(session, world)
                            })
                            
                        # Spawn engine thread
                        engine_thread = threading.Thread(
                            target=run_engine_thread,
                            args=(world, adapter, session["output_queue"], loop),
                            daemon=True
                        )
                        engine_thread.start()
                        session["engine_thread"] = engine_thread
                    continue
                
                if session["game_started"]:
                    world = session.get("world")
                    combat = getattr(world, 'active_combat', None) if world else None
                    if world:
                        sync_engine_leader(session, world)
                    action = parsed.get("action", "")
                    value = parsed.get("value", "")
                    user_input = parsed.get("value", "")
                    
                    session.setdefault("client_stages", {})
                    
                    if session["client_stages"].get(client_id) == "voting":
                        session.setdefault("votes", {})[client_id] = value
                        target_ws = session["connected_clients"][client_id][0]
                        send_to_ws_threadsafe(session, target_ws, {
                            "type": "WAITING_INPUT",
                            "prompt": "⌛ Voto registrado. Aguardando outros jogadores...",
                            "options": {}
                        })
                        session["client_stages"][client_id] = "normal"
                        continue
                        
                    if session["client_stages"].get(client_id) == "legendary_draft":
                        item_id = world.state.get_flag("legendary_draft_item")
                        from engine.items import create_item, ItemType
                        item = create_item(item_id)
                        item_name = item.name if item else "Item Lendário"
                        
                        if value == "1":
                            claimed_by = world.state.get_flag("legendary_draft_claimed_by")
                            if not claimed_by:
                                world.state.set_flag("legendary_draft_claimed_by", name)
                                player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                                if not player:
                                    player = world.player
                                if item:
                                    if item.item_type == ItemType.ARMA:
                                        player.weapon = item
                                    else:
                                        player.armor = item
                                        
                                session["adapter"].broadcast({
                                    "type": "NARRATIVE_TEXT",
                                    "content": f"🎉 {name} equipou o item lendário: {item_name}!"
                                })
                                
                                # Clear draft stage for all connected clients
                                for cid in list(session["connected_clients"].keys()):
                                    session["client_stages"][cid] = "normal"
                                    
                                session["adapter"].on_state_change(world.state)
                            else:
                                target_ws = session["connected_clients"][client_id][0]
                                send_to_ws_threadsafe(session, target_ws, {
                                    "type": "NARRATIVE_TEXT",
                                    "content": f"❌ Tarde demais! {claimed_by} já ficou com o item."
                                })
                                session["client_stages"][client_id] = "normal"
                        else:
                            # Passed
                            target_ws = session["connected_clients"][client_id][0]
                            send_to_ws_threadsafe(session, target_ws, {
                                    "type": "NARRATIVE_TEXT",
                                    "content": "Você passou o item lendário."
                            })
                            session["client_stages"][client_id] = "normal"
                        continue
                    actual_leader = get_actual_leader_id(session, world)
                    if session.get("waiting_for_ready", False) and not (combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS) and session.setdefault("client_stages", {}).get(client_id, "normal") == "normal":
                        if value == "2":
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                            opts = {str(i): f"{item.name} ({item.description})" for i, item in enumerate(player.inventory)}
                            opts["exit"] = "Fechar Inventário"
                            set_client_stage(session, client_id, world, "inventory")
                            payload = {
                                "type": "WAITING_INPUT",
                                "prompt": f"🎒 Inventário de {player.name} (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um item:",
                                "options": opts,
                                "my_client_id": client_id,
                                "leader_client_id": actual_leader
                            }
                            send_to_ws_threadsafe(session, websocket, payload)
                            continue
                        elif value == "3":
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                            opts = {str(i): f"{item.name} ({item.description})" for i, item in enumerate(world.state.shared_inventory)}
                            opts["exit"] = "Fechar Estoque"
                            set_client_stage(session, client_id, world, "party_stock")
                            payload = {
                                "type": "WAITING_INPUT",
                                "prompt": f"🧪 Estoque da Party (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um consumível:",
                                "options": opts,
                                "my_client_id": client_id,
                                "leader_client_id": actual_leader
                            }
                            send_to_ws_threadsafe(session, websocket, payload)
                            continue
                        elif value == "forge" and world.state.current_location == "oakhaven":
                            set_client_stage(session, client_id, world, "forge")
                            send_forge_menu(session, client_id, world)
                            continue
                        elif value == "tavern" and world.state.current_location == "oakhaven":
                            set_client_stage(session, client_id, world, "tavern")
                            send_tavern_menu(session, client_id, world)
                            continue
                        elif value == "elder" and world.state.current_location == "oakhaven":
                            set_client_stage(session, client_id, world, "elder")
                            send_elder_menu(session, client_id, world)
                            continue

                    if action == "PLAYER_READY" or (
                        session.get("waiting_for_ready", False)
                        and not (combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS)
                        and session.get("client_stages", {}).get(client_id, "normal") == "normal"
                        and value == "1"
                    ):
                        player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                        name_key = player.name.lower() if player else "herói"
                        session.setdefault("ready_players", set()).add(name_key)
                        total = len(session["connected_clients"])
                        connected_names = {n.lower() for (_, n, _) in session["connected_clients"].values() if n}
                        ready = len(session["ready_players"].intersection(connected_names))
                        
                        player_name = name or "Aventureiro"
                        
                        if session.get("adapter"):
                            session["adapter"].broadcast({
                                "type": "NARRATIVE_TEXT",
                                "content": f"✅ {player_name} está pronto! ({ready}/{total})"
                            })
                            
                        if ready == total:
                            session["ready_players"].clear()
                            session["waiting_for_ready"] = False
                            for cid in list(session["connected_clients"].keys()):
                                old_stage = session.setdefault("client_stages", {}).get(cid, "normal")
                                session["client_stages"][cid] = "normal"
                                if old_stage in ["forge", "tavern", "elder", "inventory", "party_stock", "talents"]:
                                    target_ws = session["connected_clients"][cid][0]
                                    shop_names = {
                                        "forge": "da forja",
                                        "tavern": "da taverna",
                                        "elder": "do ancião",
                                        "inventory": "do seu inventário",
                                        "party_stock": "do estoque da party",
                                        "talents": "da árvore de talentos"
                                    }
                                    shop_name = shop_names.get(old_stage, "do menu")
                                    send_to_ws_threadsafe(session, target_ws, {
                                        "type": "NARRATIVE_TEXT",
                                        "content": f"⚠️ A party partiu! Você foi retirado {shop_name}."
                                    })
                            
                            if world and world.state and world.state.current_location == "oakhaven":
                                session.pop("pending_leader_choice", None)
                                session["adapter"].input_queue.put("6")
                            else:
                                pending = session.pop("pending_leader_choice", None)
                                if pending:
                                    leader_id = get_actual_leader_id(session, world)
                                    if leader_id in session["connected_clients"]:
                                        target_ws = session["connected_clients"][leader_id][0]
                                        payload_copy = dict(pending)
                                        payload_copy["my_client_id"] = leader_id
                                        payload_copy["leader_client_id"] = leader_id
                                        send_to_ws_threadsafe(session, target_ws, payload_copy)
                        else:
                            for cid in list(session["connected_clients"].keys()):
                                send_player_ready_prompt(session, cid, world)
                        continue

                    if action == "OPEN_INVENTORY" or (client_id != get_actual_leader_id(session, world) and not (combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS) and value == "2" and session.setdefault("client_stages", {}).get(client_id, "normal") == "normal"):
                        player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                        if not player:
                            player = world.player
                        
                        opts = {}
                        for i, item in enumerate(player.inventory):
                            opts[str(i)] = f"{item.name} ({item.description})"
                        opts["exit"] = "Fechar Inventário"
                        
                        set_client_stage(session, client_id, world, "inventory")
                        
                        payload = {
                            "type": "WAITING_INPUT",
                            "prompt": f"🎒 Inventário de {player.name} (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um item para usar/equipar:",
                            "options": opts,
                            "my_client_id": client_id,
                            "leader_client_id": get_actual_leader_id(session, world)
                        }
                        send_to_ws_threadsafe(session, websocket, payload)
                        continue

                    if action == "OPEN_PARTY_STOCK" or (client_id != get_actual_leader_id(session, world) and not (combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS) and value == "3" and session.setdefault("client_stages", {}).get(client_id, "normal") == "normal"):
                        player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                        if not player:
                            player = world.player
                        
                        opts = {}
                        for i, item in enumerate(world.state.shared_inventory):
                            opts[str(i)] = f"{item.name} ({item.description})"
                        opts["exit"] = "Fechar Estoque"
                        
                        set_client_stage(session, client_id, world, "party_stock")
                        
                        payload = {
                            "type": "WAITING_INPUT",
                            "prompt": f"🧪 Estoque da Party (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um consumível para usar em {player.name}:",
                            "options": opts,
                            "my_client_id": client_id,
                            "leader_client_id": get_actual_leader_id(session, world)
                        }
                        send_to_ws_threadsafe(session, websocket, payload)
                        continue

                    if action == "OPEN_TALENTS" or (client_id != get_actual_leader_id(session, world) and not (combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS) and value == "7" and session.setdefault("client_stages", {}).get(client_id, "normal") == "normal"):
                        send_talents_menu(session, client_id, world)
                        continue

                    if session["client_stages"].get(client_id) == "inventory":
                        if value == "exit":
                            exit_client_submenu(session, client_id, world)
                        else:
                            try:
                                idx = int(value)
                                player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                                if not player:
                                    player = world.player
                                
                                item = player.inventory[idx]
                                if isinstance(item, (Weapon, Armor)):
                                    player.inventory.pop(idx)
                                    result_log = player.equip(item)
                                    session["adapter"].emit(NarrativeText(f"🛡️ {player.name} equipou: {item.name}"))
                                elif isinstance(item, Consumable):
                                    if len(world.party) > 1:
                                        session.setdefault("item_target_pending", {})[client_id] = {
                                            "item": item,
                                            "source": "inventory",
                                            "idx": idx
                                        }
                                        opts = {str(i): f"{p.name} (HP: {p.hp}/{p.max_hp} {'[CAÍDO]' if p.is_down else ''})" for i, p in enumerate(world.party)}
                                        opts["exit"] = "Cancelar"
                                        set_client_stage(session, client_id, world, "item_target")
                                        payload = {
                                            "type": "WAITING_INPUT",
                                            "prompt": f"Escolha o alvo para usar {item.name}:",
                                            "options": opts,
                                            "my_client_id": client_id,
                                            "leader_client_id": get_actual_leader_id(session, world)
                                        }
                                        send_to_ws_threadsafe(session, websocket, payload)
                                        continue
                                    else:
                                        player.inventory.pop(idx)
                                        result_log = item.use(player)
                                        session["adapter"].emit(NarrativeText(f"🧪 {player.name} usou {item.name}: {result_log}"))
                                    
                                session["adapter"].on_state_change(world.state)
                            except (ValueError, IndexError):
                                pass
                            
                            # Refresh inventory
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                            opts = {}
                            for i, it in enumerate(player.inventory):
                                opts[str(i)] = f"{it.name} ({it.description})"
                            opts["exit"] = "Fechar Inventário"
                            
                            payload = {
                                "type": "WAITING_INPUT",
                                "prompt": f"🎒 Inventário de {player.name} (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um item para usar/equipar:",
                                "options": opts,
                                "my_client_id": client_id,
                                "leader_client_id": get_actual_leader_id(session, world)
                            }
                            send_to_ws_threadsafe(session, websocket, payload)
                        continue

                    if session["client_stages"].get(client_id) == "party_stock":
                        if value == "exit":
                            exit_client_submenu(session, client_id, world)
                        else:
                            try:
                                idx = int(value)
                                player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                                if not player:
                                    player = world.player
                                
                                item = world.state.shared_inventory[idx]
                                if isinstance(item, Consumable):
                                    if len(world.party) > 1:
                                        session.setdefault("item_target_pending", {})[client_id] = {
                                            "item": item,
                                            "source": "party_stock",
                                            "idx": idx
                                        }
                                        opts = {str(i): f"{p.name} (HP: {p.hp}/{p.max_hp} {'[CAÍDO]' if p.is_down else ''})" for i, p in enumerate(world.party)}
                                        opts["exit"] = "Cancelar"
                                        set_client_stage(session, client_id, world, "item_target")
                                        payload = {
                                            "type": "WAITING_INPUT",
                                            "prompt": f"Escolha o alvo para usar {item.name} do Estoque:",
                                            "options": opts,
                                            "my_client_id": client_id,
                                            "leader_client_id": get_actual_leader_id(session, world)
                                        }
                                        send_to_ws_threadsafe(session, websocket, payload)
                                        continue
                                    else:
                                        world.state.shared_inventory.pop(idx)
                                        result_log = item.use(player)
                                        session["adapter"].emit(NarrativeText(f"🧪 {player.name} usou {item.name} do Estoque: {result_log}"))
                                    
                                session["adapter"].on_state_change(world.state)
                            except (ValueError, IndexError):
                                pass
                            
                            # Refresh party stock
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                            opts = {}
                            for i, it in enumerate(world.state.shared_inventory):
                                opts[str(i)] = f"{it.name} ({it.description})"
                            opts["exit"] = "Fechar Estoque"
                            
                            payload = {
                                "type": "WAITING_INPUT",
                                "prompt": f"🧪 Estoque da Party (HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}) - Escolha um consumível para usar em {player.name}:",
                                "options": opts,
                                "my_client_id": client_id,
                                "leader_client_id": get_actual_leader_id(session, world)
                            }
                            send_to_ws_threadsafe(session, websocket, payload)
                        continue
                     
                    if session["client_stages"].get(client_id) == "talents":
                        if value == "exit":
                            exit_client_submenu(session, client_id, world)
                        else:
                            try:
                                idx_map = session.get("client_talent_maps", {}).get(client_id, {})
                                talent_id = idx_map.get(value)
                                player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                                if not player:
                                    player = world.player
                                
                                if talent_id:
                                    from engine.talents import unlock_talent, TALENTS_LIBRARY
                                    talent = TALENTS_LIBRARY[talent_id]
                                    if talent_id in player.talents_unlocked:
                                        send_to_ws_threadsafe(session, websocket, {
                                            "type": "NARRATIVE_TEXT",
                                            "content": f"⚠️ Você já desbloqueou o talento: {talent['name']}."
                                        })
                                    elif player.talent_points < 1:
                                        send_to_ws_threadsafe(session, websocket, {
                                            "type": "NARRATIVE_TEXT",
                                            "content": "❌ Você não possui Pontos de Talento suficientes!"
                                        })
                                    else:
                                        success = unlock_talent(player, talent_id)
                                        if success:
                                            session["adapter"].emit(NarrativeText(f"🌳 {player.name} desbloqueou o talento: {talent['name']}!"))
                                            session["adapter"].on_state_change(world.state)
                                        else:
                                            send_to_ws_threadsafe(session, websocket, {
                                                "type": "NARRATIVE_TEXT",
                                                "content": "❌ Falha ao desbloquear o talento."
                                            })
                            except Exception as e:
                                logger.error(f"Error unlocking talent: {e}")
                            
                            # Re-send talents menu to show updated status
                            send_talents_menu(session, client_id, world)
                        continue

                    if session["client_stages"].get(client_id) == "item_target":
                        pending = session.setdefault("item_target_pending", {}).get(client_id)
                        if value == "exit" or not pending:
                            session["client_stages"][client_id] = pending["source"] if pending else "normal"
                            session["item_target_pending"].pop(client_id, None)
                            refresh_client_ui(session, client_id, world)
                        else:
                            try:
                                target_idx = int(value)
                                target_player = world.party[target_idx]
                                item = pending["item"]
                                source = pending["source"]
                                idx = pending["idx"]
                                
                                player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None) or world.player
                                if source == "inventory":
                                    if idx < len(player.inventory) and player.inventory[idx] == item:
                                        player.inventory.pop(idx)
                                        result_log = item.use(target_player)
                                        session["adapter"].emit(NarrativeText(f"🧪 {player.name} usou {item.name} em {target_player.name}: {result_log}"))
                                if source == "party_stock":
                                    if idx < len(world.state.shared_inventory) and world.state.shared_inventory[idx] == item:
                                        world.state.shared_inventory.pop(idx)
                                        result_log = item.use(target_player)
                                        session["adapter"].emit(NarrativeText(f"🧪 {player.name} usou {item.name} do Estoque em {target_player.name}: {result_log}"))
                                
                                session["client_stages"][client_id] = source
                                session["item_target_pending"].pop(client_id, None)
                                session["adapter"].on_state_change(world.state)
                                refresh_client_ui(session, client_id, world)
                            except (ValueError, IndexError):
                                pass
                        continue

                    current_stage = session["client_stages"].get(client_id)
                    if current_stage in ["forge", "tavern", "elena_dialogue", "elena_dialogue_relic", "elder", "elder_recompensa"]:
                        if not (world and world.state and world.state.current_location == "oakhaven" and session.get("waiting_for_ready", False)):
                            exit_client_submenu(session, client_id, world)
                            continue
                            
                    if session["client_stages"].get(client_id) == "forge":
                        if value == "exit":
                            exit_client_submenu(session, client_id, world)
                        else:
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                            
                            from engine.items import create_item
                            if value == "1" and player.gold >= 30:
                                player.gold -= 30
                                item = create_item("espada_soldado")
                                player.inventory.append(item)
                                session["adapter"].emit(NarrativeText(f"⚒️ {player.name} comprou Espada de Soldado na Forja."))
                            elif value == "2" and player.gold >= 50:
                                player.gold -= 50
                                item = create_item("cota_malha")
                                player.inventory.append(item)
                                session["adapter"].emit(NarrativeText(f"⚒️ {player.name} comprou Cota de Malha na Forja."))
                            
                            session["adapter"].on_state_change(world.state)
                            send_forge_menu(session, client_id, world)
                        continue

                    if session["client_stages"].get(client_id) == "tavern":
                        if value == "exit":
                            exit_client_submenu(session, client_id, world)
                        elif value == "1":
                            elena_confronted = world.state.get_flag("elena_confronted")
                            elena_recrutada = world.state.get_flag("elena_recrutada")
                            if not elena_recrutada and not elena_confronted:
                                session["client_stages"][client_id] = "elena_dialogue"
                                send_elena_dialogue(session, client_id, world, 1)
                            else:
                                send_tavern_menu(session, client_id, world)
                        else:
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                                
                            from engine.items import create_item
                            if value == "2" and player.gold >= 5:
                                player.gold -= 5
                                world.state.shared_inventory.append(create_item("pocao_vida_p"))
                                session["adapter"].emit(NarrativeText(f"🍺 {player.name} comprou Poção de Vida Menor."))
                            elif value == "3" and player.gold >= 5:
                                player.gold -= 5
                                world.state.shared_inventory.append(create_item("pocao_mana_p"))
                                session["adapter"].emit(NarrativeText(f"🍺 {player.name} comprou Poção de Mana Menor."))
                            elif value == "4" and player.gold >= 15:
                                player.gold -= 15
                                world.state.shared_inventory.append(create_item("pocao_vida_m"))
                                session["adapter"].emit(NarrativeText(f"🍺 {player.name} comprou Poção de Vida."))
                            
                            session["adapter"].on_state_change(world.state)
                            send_tavern_menu(session, client_id, world)
                        continue

                    if session["client_stages"].get(client_id) == "elena_dialogue":
                        if value == "1":
                            if world.state.get_flag("roubou_cabana"):
                                session["client_stages"][client_id] = "elena_dialogue_relic"
                                send_elena_dialogue(session, client_id, world, 2)
                            else:
                                from engine.companion import get_companion
                                world.player.companion = get_companion("elena")
                                world.state.set_flag("elena_recrutada", True)
                                session["adapter"].emit(NarrativeText(f"🏹 Elena juntou-se à party como companheira!"))
                                session["client_stages"][client_id] = "tavern"
                                session["adapter"].on_state_change(world.state)
                                send_tavern_menu(session, client_id, world)
                        elif value in ["2", "3"]:
                            world.state.set_flag("elena_confronted", True)
                            session["client_stages"][client_id] = "tavern"
                            session["adapter"].on_state_change(world.state)
                            send_tavern_menu(session, client_id, world)
                        else:
                            session["client_stages"][client_id] = "tavern"
                            send_tavern_menu(session, client_id, world)
                        continue

                    if session["client_stages"].get(client_id) == "elena_dialogue_relic":
                        if value == "1":
                            from engine.companion import get_companion
                            world.player.companion = get_companion("elena")
                            world.state.set_flag("elena_recrutada", True)
                            session["adapter"].emit(NarrativeText(f"🏹 Elena juntou-se à party como companheira!"))
                        else:
                            world.state.set_flag("elena_confronted", True)
                            world.state.set_flag("inimiga_elena", True)
                            session["adapter"].emit(NarrativeText(f"🏹 Elena se afasta zangada."))
                        session["client_stages"][client_id] = "tavern"
                        session["adapter"].on_state_change(world.state)
                        send_tavern_menu(session, client_id, world)
                        continue

                    if session["client_stages"].get(client_id) == "elder":
                        if value == "exit":
                            exit_client_submenu(session, client_id, world)
                        elif value == "1":
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                            from engine.items import create_item
                            player.inventory.append(create_item("pocao_vida_m"))
                            for p in world.party:
                                p.quest_manager.start_quest("cavernas", lambda msg: session["adapter"].emit(NarrativeText(msg)))
                            session["adapter"].on_state_change(world.state)
                            send_elder_menu(session, client_id, world)
                        elif value == "2":
                            session["client_stages"][client_id] = "elder_recompensa"
                            send_elder_recompensa_menu(session, client_id, world)
                        else:
                            exit_client_submenu(session, client_id, world)
                        continue

                    if session["client_stages"].get(client_id) == "elder_recompensa":
                        if value == "1":
                            player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                            if not player:
                                player = world.player
                            from engine.items import create_item
                            player.inventory.append(create_item("pocao_vida_m"))
                            for p in world.party:
                                p.quest_manager.start_quest("cavernas", lambda msg: session["adapter"].emit(NarrativeText(msg)))
                                p.choices["negociou_recompensa"] = True
                            session["adapter"].on_state_change(world.state)
                        session["client_stages"][client_id] = "elder"
                        send_elder_menu(session, client_id, world)
                        continue
                    

                    
                    if combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS:
                        # Modo combate multiplayer — cada jogador envia sua ação
                        action = parsed.get("action", "")
                        value = parsed.get("value", "")
                        
                        # Sub-menus por jogador (alvo, habilidade, item, interrupt)
                        stage = combat.client_menu_stages.get(client_id, "main")
                        from engine.feature_flags import FLAGS as _FF

                        def _combat_main_options():
                            opts = {"1": "Atacar", "2": "Habilidades", "4": "Defender"}
                            if combat.can_flee:
                                opts["5"] = "Fugir"
                            if _FF.combat_intent:
                                opts["6"] = "🛑 Interromper"
                            return opts
                        
                        if stage == "main":
                            if value == "1":  # Atacar
                                # Enviar lista de alvos só para este jogador
                                alive = [e for e in combat.enemies if e.is_alive()]
                                opts = {str(i): e.name for i, e in enumerate(alive)}
                                combat.client_menu_stages[client_id] = "target"
                                personal_callback = session["connected_clients"][client_id][0]
                                payload = {"type": "WAITING_INPUT", "prompt": "Escolha o alvo:", "options": opts,
                                           "my_client_id": client_id, "leader_client_id": get_actual_leader_id(session, world)}
                                send_to_ws_threadsafe(session, personal_callback, payload)
                            elif value == "2":  # Habilidades
                                 player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                                 if player:
                                     from engine.constants import StatusEffect
                                     if StatusEffect.AFOGAMENTO in player.status_effects:
                                         session["adapter"].emit(NarrativeText(f"⚠️ {player.name} está se afogando e não pode usar Habilidades!"))
                                         personal_ws = session["connected_clients"][client_id][0]
                                         payload = {"type": "WAITING_INPUT", "prompt": "O que deseja fazer? ", "options": _combat_main_options(),
                                                    "my_client_id": client_id, "leader_client_id": get_actual_leader_id(session, world)}
                                         send_to_ws_threadsafe(session, personal_ws, payload)
                                         continue
                                     skills = player.get_skills()
                                     if skills:
                                         opts = {str(i): f"{s.name} (MP:{s.mp})" for i, s in enumerate(skills)}
                                         combat.client_menu_stages[client_id] = "skill"
                                         personal_ws = session["connected_clients"][client_id][0]
                                         payload = {"type": "WAITING_INPUT", "prompt": "Qual habilidade?", "options": opts,
                                                    "my_client_id": client_id, "leader_client_id": get_actual_leader_id(session, world)}
                                         send_to_ws_threadsafe(session, personal_ws, payload)
                            elif value == "4":  # Defender
                                cmd = Command(action="DEFEND")
                                combat.submit_player_action(client_id, cmd)
                                combat.advance_state()
                            elif value == "5":  # Fugir
                                cmd = Command(action="FLEE")
                                combat.submit_player_action(client_id, cmd)
                                combat.advance_state()
                            elif value == "6" and _FF.combat_intent:  # Interromper
                                alive = [e for e in combat.enemies if e.is_alive()]
                                opts = {}
                                for i, e in enumerate(alive):
                                    intent = getattr(e, "intent_view", None)
                                    label = intent.label if intent else "?"
                                    lock = " ⛔" if intent and intent.uninterruptible else ""
                                    opts[str(i)] = f"{e.name} [{label}]{lock}"
                                combat.client_menu_stages[client_id] = "interrupt_target"
                                personal_ws = session["connected_clients"][client_id][0]
                                payload = {
                                    "type": "WAITING_INPUT",
                                    "prompt": "Interromper qual inimigo?",
                                    "options": opts,
                                    "my_client_id": client_id,
                                    "leader_client_id": get_actual_leader_id(session, world),
                                }
                                send_to_ws_threadsafe(session, personal_ws, payload)
                                
                        elif stage == "target":
                            # Jogador escolheu o alvo
                            try:
                                target_idx = int(value)
                                alive = [e for e in combat.enemies if e.is_alive()]
                                enemy = alive[target_idx]
                                main_idx = combat.enemies.index(enemy)
                                cmd = Command(action="ATTACK", target=main_idx)
                                combat.client_menu_stages[client_id] = "main"
                                combat.submit_player_action(client_id, cmd)
                                combat.advance_state()
                            except (ValueError, IndexError):
                                pass

                        elif stage == "interrupt_target":
                            try:
                                target_idx = int(value)
                                alive = [e for e in combat.enemies if e.is_alive()]
                                enemy = alive[target_idx]
                                main_idx = combat.enemies.index(enemy)
                                cmd = Command(action="INTERRUPT", target=main_idx)
                                combat.client_menu_stages[client_id] = "main"
                                combat.submit_player_action(client_id, cmd)
                                combat.advance_state()
                            except (ValueError, IndexError):
                                pass
                                
                        elif stage == "skill":
                            try:
                                player = next((p for p in world.party if getattr(p, 'client_id', None) == client_id), None)
                                if player:
                                    skills = player.get_skills()
                                    skill = skills[int(value)]
                                    cmd = Command(action="SKILL", value=skill)
                                    combat.client_menu_stages[client_id] = "main"
                                    combat.submit_player_action(client_id, cmd)
                                    combat.advance_state()
                            except (ValueError, IndexError):
                                pass

                        elif stage == "downed":
                            # PRD B4 — limited actions while HP <= 0
                            action_key = value if value in ("wait", "shout", "bargain") else "wait"
                            cmd = Command(action="DOWNED", value=action_key)
                            combat.client_menu_stages[client_id] = "main"
                            combat.submit_player_action(client_id, cmd)
                            combat.advance_state()
                    else:
                        # Modo narrativa — só o líder envia input
                        actual_leader = get_actual_leader_id(session, world)
                        if client_id == actual_leader:
                            session["waiting_for_ready"] = False
                            session["adapter"].input_queue.put(user_input)
                            
            except json.JSONDecodeError:
                if session["game_started"]:
                    world = session.get("world")
                    combat = getattr(world, 'active_combat', None) if world else None
                    if not (combat and combat.phase == CombatPhase.WAITING_ALL_PLAYERS):
                        actual_leader = get_actual_leader_id(session, world)
                        if client_id == actual_leader:
                            session["waiting_for_ready"] = False
                            session["adapter"].input_queue.put(data)
                    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected.")
        session = active_sessions.get(session_id)
        if session:
            # Remove client
            session["connected_clients"].pop(client_id, None)
            session["connected"] = False
            
            if not session["game_started"]:
                # If leader leaves, designate a new leader
                if session["leader_id"] == client_id:
                    if session["connected_clients"]:
                        session["leader_id"] = list(session["connected_clients"].keys())[0]
                    else:
                        session["leader_id"] = None
                        
                if session["connected_clients"]:
                    # Broadcast lobby update
                    await broadcast_lobby_update(session_id)
                else:
                    # Cleanup empty lobby
                    active_sessions.pop(session_id, None)
            else:
                # Active game session grace period (only cleans up if all left)
                if not session["connected_clients"]:
                    async def grace_period():
                        await asyncio.sleep(60)
                        sess = active_sessions.get(session_id)
                        if sess and not sess["connected_clients"]:
                            logger.info(f"Session {session_id} abandoned. Shutting down engine.")
                            if sess["adapter"]:
                                sess["adapter"].shutdown_event.set()
                            active_sessions.pop(session_id, None)
                            
                    session["cleanup_task"] = asyncio.create_task(grace_period())
                else:
                    # Some clients remain connected, re-evaluate ready consensus
                    if session.get("waiting_for_ready", False):
                        world = session.get("world")
                        total = len(session["connected_clients"])
                        connected_names = {n.lower() for (_, n, _) in session["connected_clients"].values() if n}
                        ready = len(session.setdefault("ready_players", set()).intersection(connected_names))
                        if ready >= total:
                            session["ready_players"].clear()
                            session["waiting_for_ready"] = False
                            for cid in list(session["connected_clients"].keys()):
                                session.setdefault("client_stages", {})[cid] = "normal"
                            
                            if world and world.state and world.state.current_location == "oakhaven":
                                session.pop("pending_leader_choice", None)
                                session["adapter"].input_queue.put("6")
                            else:
                                pending = session.pop("pending_leader_choice", None)
                                if pending:
                                    leader_id = get_actual_leader_id(session, world)
                                    if leader_id in session["connected_clients"]:
                                        target_ws = session["connected_clients"][leader_id][0]
                                        payload_copy = dict(pending)
                                        payload_copy["my_client_id"] = leader_id
                                        payload_copy["leader_client_id"] = leader_id
                                        send_to_ws_threadsafe(session, target_ws, payload_copy)

# Serve static React UI files in production build
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Ensure static files fallback to SPA routing
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    raise HTTPException(status_code=404, detail="SPA static directory not initialized.")
