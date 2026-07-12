import pytest
import time
import threading
import random
import copy
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from engine.player import Player
from engine.state import GameState
from engine.world import WorldManager
from engine.constants import CharacterClass, StatusEffect
from engine.enemy import Enemy, spawn_enemy
from engine.combat import CombatSystem, CombatPhase, Command
from engine.items import create_item, ItemType, Weapon, Armor
from server import app, active_sessions, MulticastWebUIAdapter, send_to_ws_threadsafe, get_actual_leader_id, handle_broadcast_payload

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeCombat:
    """Fake CombatSystem that completes successfully."""
    def __init__(self, state, enemies, can_flee=False, turn_hook=None, **kw):
        self.state = state
        self.enemies = enemies
        self.turn_hook = turn_hook
        self.phase = CombatPhase.WAITING_ALL_PLAYERS
        self.client_menu_stages = {}
        self.pending_actions = {}
        for e in enemies:
            e.hp = 0

    def run(self):
        return True

    def distribute_rewards(self):
        pass

    def sync_state(self):
        pass


class InputQueue:
    """Input Queue helper to simulate user choices sequentially."""
    def __init__(self, inputs):
        self._inputs = list(inputs)
        self._idx = 0

    def __call__(self, options, prompt="Escolha:", **kwargs):
        if self._idx < len(self._inputs):
            val = self._inputs[self._idx]
            self._idx += 1
            return val
        return list(options.keys())[0]


def _make_world(char_class: CharacterClass, flags: dict | None = None, level: int = 5):
    player = Player("Herói", char_class)
    for _ in range(level - 1):
        player.gain_xp(player.get_xp_needed())
    player.hp = player.max_hp
    player.mp = player.max_mp

    state = GameState(player)
    if flags:
        for k, v in flags.items():
            state.set_flag(k, v)

    wm = WorldManager(state)
    return wm


def run_chapter_flow(wm, chapter_fn_name, inputs, next_chapter_fn_name=None):
    input_queue = InputQueue(inputs)
    patches = []

    mock_typewriter = MagicMock()
    _UI_FNS = ('clear_screen', 'press_any_key', 'print_centered', 'play_sound_effect')
    _MODULES = ('engine.world', 'engine.world_chapter_3', 'engine.world_chapter_4', 
                'engine.world_chapter_5', 'engine.world_chapter_7', 'engine.world_chapter_8')
    
    for mod in _MODULES:
        for fn in _UI_FNS:
            patches.append(patch(f'{mod}.{fn}', return_value=None))
        patches.append(patch(f'{mod}.typewriter', mock_typewriter))
            
    patches.append(patch('engine.world.CombatSystem', _FakeCombat))
    patches.append(patch('engine.world_chapter_3.CombatSystem', _FakeCombat))
    patches.append(patch('engine.world_chapter_4.CombatSystem', _FakeCombat))
    patches.append(patch('engine.world_chapter_5.CombatSystem', _FakeCombat))
    patches.append(patch('engine.world_chapter_7.CombatSystem', _FakeCombat))
    patches.append(patch('engine.world_chapter_8.CombatSystem', _FakeCombat))
    
    if next_chapter_fn_name:
        patches.append(patch.object(wm, next_chapter_fn_name, return_value=None))
        
    patches.append(patch.object(wm, 'get_leader_choice', side_effect=input_queue))
    patches.append(patch.object(wm, 'get_party_vote', side_effect=input_queue))
    patches.append(patch('sys.exit', side_effect=SystemExit(0)))
    
    for p in patches:
        p.__enter__()
        
    try:
        try:
            fn = getattr(wm, chapter_fn_name)
            fn()
        except SystemExit:
            pass
    finally:
        for p in reversed(patches):
            p.__exit__(None, None, None)
            
    return mock_typewriter


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


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestTodosOsFinais:
    @patch('engine.world_chapter_7.typewriter')
    @patch('engine.world_chapter_7.press_any_key')
    @patch('engine.world_chapter_7.clear_screen')
    @patch('engine.world_chapter_7.print_centered')
    def test_ending_senhor_das_sombras(self, mock_print, mock_clear, mock_press, mock_typewriter):
        """Senhor das Sombras: pergaminho guardado + lacre sombrio."""
        wm = _make_world(CharacterClass.GUERREIRO, {"guardou_pergaminho": True, "lacre_sombrio": True})
        with patch.object(wm, 'chapter_7_start') as mock_ch7:
            wm.act_ii_epilogue_hook()
            mock_ch7.assert_called_once()
            calls = [c[0][0] for c in mock_typewriter.call_args_list]
            assert any("O poder de Malakar corre agora nas veias de vocês" in s for s in calls)

    @patch('engine.world_chapter_7.typewriter')
    @patch('engine.world_chapter_7.press_any_key')
    @patch('engine.world_chapter_7.clear_screen')
    @patch('engine.world_chapter_7.print_centered')
    def test_ending_heroi_da_luz(self, mock_print, mock_clear, mock_press, mock_typewriter):
        """Herói da Luz: Elena viva + cabana não roubada."""
        wm = _make_world(CharacterClass.GUERREIRO, {"elena_morta": False, "roubou_cabana": False})
        with patch.object(wm, 'chapter_7_start') as mock_ch7:
            wm.act_ii_epilogue_hook()
            mock_ch7.assert_called_once()
            calls = [c[0][0] for c in mock_typewriter.call_args_list]
            assert any("Meses depois de Oakhaven ser reconstruída" in s for s in calls)

    @patch('engine.world_chapter_7.typewriter')
    @patch('engine.world_chapter_7.press_any_key')
    @patch('engine.world_chapter_7.clear_screen')
    @patch('engine.world_chapter_7.print_centered')
    def test_ending_andarilho_solitario(self, mock_print, mock_clear, mock_press, mock_typewriter):
        """Andarilho Solitário: Elena morta ou cabana roubada."""
        wm = _make_world(CharacterClass.GUERREIRO, {"elena_morta": True, "roubou_cabana": True})
        with patch.object(wm, 'chapter_7_start') as mock_ch7:
            wm.act_ii_epilogue_hook()
            mock_ch7.assert_called_once()
            calls = [c[0][0] for c in mock_typewriter.call_args_list]
            assert any("Vocês seguiram sozinhos, longe de Oakhaven" in s for s in calls)


class TestTodasAsClasses:
    @pytest.mark.parametrize("char_class,chapter_fn,inputs,expected_flag", [
        # Chapter 7
        (CharacterClass.LADINO, "chapter_7_start", ["1", "2"], "vaelmoor_infiltrado"),
        (CharacterClass.GUERREIRO, "chapter_7_start", ["2", "2"], "vaelmoor_duelo_vencido"),
        (CharacterClass.MAGO, "chapter_7_start", ["3", "2"], "vaelmoor_selo_identificado"),
        (CharacterClass.CLERIGO, "chapter_7_start", ["4", "2"], "vaelmoor_corrupcao_sentida"),
        (CharacterClass.GUERREIRO, "chapter_7_start", ["5", "2"], None),
        # Chapter 8
        (CharacterClass.LADINO, "chapter_8_start", ["1", "1", "1"], "kragmoor_infiltrado"),
        (CharacterClass.GUERREIRO, "chapter_8_start", ["2", "1", "1"], "kragmoor_portão_erguido"),
        (CharacterClass.MAGO, "chapter_8_start", ["3", "1", "1"], "kragmoor_selo_realinhado"),
        (CharacterClass.CLERIGO, "chapter_8_start", ["4", "1", "1"], "kragmoor_purificado"),
        (CharacterClass.GUERREIRO, "chapter_8_start", ["5", "1", "1"], None),
    ])
    def test_class_gates(self, char_class, chapter_fn, inputs, expected_flag):
        wm = _make_world(char_class)
        next_fn = "chapter_8_start" if chapter_fn == "chapter_7_start" else "credits"
        run_chapter_flow(wm, chapter_fn, inputs, next_chapter_fn_name=next_fn)
        if expected_flag:
            assert wm.state.get_flag(expected_flag) is True
        else:
            for flag in ["vaelmoor_infiltrado", "vaelmoor_duelo_vencido", "vaelmoor_selo_identificado", "vaelmoor_corrupcao_sentida",
                         "kragmoor_infiltrado", "kragmoor_portão_erguido", "kragmoor_selo_realinhado", "kragmoor_purificado"]:
                assert wm.state.get_flag(flag) is not True

    @pytest.mark.parametrize("leader_class", [
        CharacterClass.GUERREIRO,
        CharacterClass.MAGO,
        CharacterClass.LADINO,
        CharacterClass.CLERIGO
    ])
    def test_leader_specific_branches(self, leader_class):
        wm = _make_world(leader_class)
        inputs_3 = ["1", "1"] if leader_class == CharacterClass.CLERIGO else ["1", "2"]
        run_chapter_flow(wm, "chapter_3_start", inputs_3, next_chapter_fn_name="chapter_4_start")
        if leader_class == CharacterClass.CLERIGO:
            assert wm.state.get_flag("millhaven_salva") is True
        else:
            assert wm.state.get_flag("millhaven_perdida") is True


class TestTodasAsFlagsDeConsequencia:
    def test_ogre_spared_heals(self):
        wm = _make_world(CharacterClass.GUERREIRO, {"poupou_ogro": True})
        wm.player.hp = 10
        run_chapter_flow(wm, "chapter_4_start", ["1"], next_chapter_fn_name="chapter_5_start")
        assert wm.player.hp == 40  # 10 + 30 heal from Drogg

    def test_ogre_killed_no_heals(self):
        wm = _make_world(CharacterClass.GUERREIRO, {"poupou_ogro": False})
        wm.player.hp = 10
        run_chapter_flow(wm, "chapter_4_start", ["1"], next_chapter_fn_name="chapter_5_start")
        assert wm.player.hp == 10  # No heal

    def test_goblin_helped_distracts(self):
        wm = _make_world(CharacterClass.GUERREIRO, {"ajudou_goblin": True})
        mock_type = run_chapter_flow(wm, "final_confrontation", [], next_chapter_fn_name="ending_sequence")
        calls = [c[0][0] for c in mock_type.call_args_list]
        assert any("Dropp surge de um atalho secreto" in s for s in calls)


class TestSistemasDeInventario:
    def test_equip_and_to_dict(self):
        wm = _make_world(CharacterClass.GUERREIRO)
        item = create_item("espada_soldado")
        wm.player.inventory.append(item)
        wm.player.equip(item)
        
        data = wm.state.to_dict()
        assert data["player"]["weapon"]["name"] == "Espada de Soldado"
        assert data["player"]["weapon"]["attack_power"] == 10

    def test_shared_inventory_usage(self):
        wm = _make_world(CharacterClass.GUERREIRO)
        potion = create_item("pocao_vida_m")
        wm.state.shared_inventory.append(potion)
        
        # Test using shared inventory
        assert potion in wm.state.shared_inventory
        wm.player.hp = 10
        
        # Simulating stock UI consumption
        potion.use(wm.player)
        wm.state.shared_inventory.remove(potion)
        
        assert wm.player.hp == 70  # 10 + 60
        assert potion not in wm.state.shared_inventory

    def test_legendary_draft_dispute(self):
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
                
                # Mock draft item
                world.state.set_flag("legendary_draft_item", "lamina_eclipse")
                world.state.set_flag("legendary_draft_claimed_by", "")
                
                session["client_stages"][player_a.client_id] = "legendary_draft"
                session["client_stages"][player_b.client_id] = "legendary_draft"
                
                # A claims the item first
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                receive_until_type(ws_a, "STATE_UPDATE")
                
                # B gets the broadcasted item equipped message
                msg_b = receive_until_type(ws_b, "NARRATIVE_TEXT", "equipou o item lendário")
                
                # Assert A got it, and B's stage is now normal
                assert world.state.get_flag("legendary_draft_claimed_by") == "A"
                assert session["client_stages"][player_b.client_id] == "normal"


class TestVotacaoDaParty:
    def test_unanimous_vote(self):
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
                
                votes_received = None
                def run_vote():
                    nonlocal votes_received
                    votes_received = world.get_party_vote({"1": "Sim", "2": "Não"}, "Deseja avançar?")
                
                t = threading.Thread(target=run_vote)
                t.start()
                
                # Drain prompt
                receive_until_type(ws_a, "WAITING_INPUT", "Deseja avançar")
                receive_until_type(ws_b, "WAITING_INPUT", "Deseja avançar")
                
                # Both vote "1"
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                ws_b.send_json({"action": "MENU_CHOICE", "value": "1"})
                
                # Wait for outcome
                receive_until_type(ws_a, "NARRATIVE_TEXT", "decidiu")
                
                t.join(timeout=1.0)
                assert votes_received == "1"

    def test_voting_timeout(self):
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
                
                # Setup short timeout in multicast adapter to speed up test
                world.adapter.voting_timeout = 0.5
                
                votes_received = None
                def run_vote():
                    nonlocal votes_received
                    votes_received = world.get_party_vote({"1": "Sim", "2": "Não"}, "Deseja avançar?")
                
                t = threading.Thread(target=run_vote)
                t.start()
                
                receive_until_type(ws_a, "WAITING_INPUT", "Deseja avançar")
                receive_until_type(ws_b, "WAITING_INPUT", "Deseja avançar")
                
                # Only B votes "2", A does not vote (times out)
                ws_b.send_json({"action": "MENU_CHOICE", "value": "2"})
                
                # Wait outcome
                receive_until_type(ws_a, "NARRATIVE_TEXT")
                
                t.join(timeout=1.5)
                # Since only B voted, B's vote ("2") should win
                assert votes_received == "2"


class TestCombateMultiplayerCompleto:
    def test_multiplayer_combat_turn(self):
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
                
                enemy = spawn_enemy("pirata_mare_negra")
                combat = CombatSystem(world.state, [enemy], adapter=world.adapter)
                world.active_combat = combat
                
                combat.phase = CombatPhase.WAITING_ALL_PLAYERS
                combat.sync_state()
                world.adapter.on_state_change(world.state)
                
                # Expect WAITING_INPUT
                receive_until_type(ws_a, "WAITING_INPUT", "O que deseja fazer?")
                receive_until_type(ws_b, "WAITING_INPUT", "O que deseja fazer?")
                
                # A attacks
                ws_a.send_json({"action": "MENU_CHOICE", "value": "1"})
                receive_until_type(ws_a, "WAITING_INPUT", "Escolha o alvo")
                ws_a.send_json({"action": "MENU_CHOICE", "value": "0"}) # chooses first enemy
                
                # B defends
                ws_b.send_json({"action": "MENU_CHOICE", "value": "4"})
                
                # Let B's thread finish executing advance_state
                time.sleep(0.1)
                
                # Manually sync and trigger broadcast for next round
                combat.sync_state()
                world.adapter.on_state_change(world.state)
                
                # Expect next round's action menus
                receive_until_type(ws_a, "WAITING_INPUT", "O que deseja fazer?")
                receive_until_type(ws_b, "WAITING_INPUT", "O que deseja fazer?")
                
                assert len(combat.pending_actions) == 0  # cleared for next round


class TestNavegacaoDeVilaIndependente:
    def test_independent_shops_oakhaven(self):
        client = TestClient(app)
        res = client.post("/api/game/new")
        session_id = res.json()["session_id"]
        lobby_code = res.json()["lobby_code"]
        
        print("[TRACE] WS connecting A")
        with client.websocket_connect(f"/ws/{session_id}?name=A&class=GUERREIRO") as ws_a:
            print("[TRACE] A connected, waiting LOBBY_UPDATE")
            receive_until_type(ws_a, "LOBBY_UPDATE")
            print("[TRACE] A got LOBBY_UPDATE, joining lobby")
            client.post(f"/api/game/join/{lobby_code}")
            
            print("[TRACE] WS connecting B")
            with client.websocket_connect(f"/ws/{session_id}?name=B&class=MAGO") as ws_b:
                print("[TRACE] B connected, waiting LOBBY_UPDATE")
                receive_until_type(ws_b, "LOBBY_UPDATE")
                
                print("[TRACE] Setting up multiplayer WS env")
                session = active_sessions[session_id]
                world, player_a, player_b = setup_multiplayer_ws_environment(session_id, session, ws_a, ws_b)
                
                print("[TRACE] Configuring state")
                world.state.current_location = "oakhaven"
                session["waiting_for_ready"] = True
                
                # A and B are in the preparation menu
                print("[TRACE] Sending WAITING_INPUT to A and B")
                ws_a_server = session["connected_clients"][player_a.client_id][0]
                ws_b_server = session["connected_clients"][player_b.client_id][0]
                send_to_ws_threadsafe(session, ws_a_server, {
                    "type": "WAITING_INPUT",
                    "prompt": "Aguardando",
                    "options": {"1": "Pronto", "4": "Forja", "5": "Taverna", "6": "Alistair"}
                })
                send_to_ws_threadsafe(session, ws_b_server, {
                    "type": "WAITING_INPUT",
                    "prompt": "Aguardando",
                    "options": {"1": "Pronto", "4": "Forja", "5": "Taverna", "6": "Alistair"}
                })
                
                # A visits the forge
                print("[TRACE] A choosing 4")
                ws_a.send_json({"action": "MENU_CHOICE", "value": "4"})
                print("[TRACE] A waiting for WAITING_INPUT Forja")
                wi_forge = receive_until_type(ws_a, "WAITING_INPUT", "Forja")
                assert "Forja" in wi_forge["prompt"]
                assert session["client_stages"][player_a.client_id] == "forge"
                
                # B visits the tavern
                print("[TRACE] B choosing 5")
                ws_b.send_json({"action": "MENU_CHOICE", "value": "5"})
                print("[TRACE] B waiting for WAITING_INPUT Taverna")
                wi_tavern = receive_until_type(ws_b, "WAITING_INPUT", "Taverna")
                assert "Taverna" in wi_tavern["prompt"]
                assert session["client_stages"][player_b.client_id] == "tavern"
                
                # A exits the forge
                print("[TRACE] A choosing exit")
                ws_a.send_json({"action": "MENU_CHOICE", "value": "exit"})
                print("[TRACE] Asserting A is normal")
                
                # wait to avoid race condition
                for _ in range(50):
                    if session["client_stages"][player_a.client_id] == "normal":
                        break
                    time.sleep(0.05)
                assert session["client_stages"][player_a.client_id] == "normal"
                
                # B exits the tavern
                print("[TRACE] B choosing exit")
                ws_b.send_json({"action": "MENU_CHOICE", "value": "exit"})
                print("[TRACE] Asserting B is normal")
                
                # wait to avoid race condition
                for _ in range(50):
                    if session["client_stages"][player_b.client_id] == "normal":
                        break
                    time.sleep(0.05)
                assert session["client_stages"][player_b.client_id] == "normal"
                print("[TRACE] Finished test_independent_shops_oakhaven successfully")
