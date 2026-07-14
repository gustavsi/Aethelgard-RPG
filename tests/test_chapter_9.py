import pytest
from unittest.mock import patch, MagicMock
from engine.player import Player
from engine.state import GameState
from engine.world import WorldManager
from engine.constants import CharacterClass
from engine.enemy import Enemy
from tests.test_chapters import InputQueue, _make_world

class _FakeCombatCapture:
    captured_enemies = []
    
    @classmethod
    def reset(cls):
        cls.captured_enemies = []

    def __init__(self, state, enemies, **kw):
        self.state = state
        self.enemies = enemies
        for e in enemies:
            self.captured_enemies.append((e.name, e.hp))
            e.hp = 0

    def run(self):
        return True

def _run_chapter_9(wm, inputs):
    _FakeCombatCapture.reset()
    input_queue = InputQueue(inputs)
    patches = []

    _UI_FNS = ('clear_screen', 'typewriter', 'press_any_key', 'print_centered', 'play_sound_effect')
    _MODULES = ('engine.world_chapter_3', 'engine.world_chapter_4', 'engine.world_chapter_5', 'engine.world', 'engine.world_chapter_9')
    
    for mod in _MODULES:
        for fn in _UI_FNS:
            patches.append(patch(f'{mod}.{fn}', return_value=None))
            
    patches.append(patch('engine.world_chapter_9.CombatSystem', _FakeCombatCapture))
    patches.append(patch('engine.world.CombatSystem', _FakeCombatCapture))
    patches.append(patch.object(wm, 'get_leader_choice', side_effect=input_queue))
    
    adapter_mock = MagicMock()
    adapter_mock.emit = MagicMock(return_value=None)
    wm.adapter = adapter_mock
    
    patches.append(patch('sys.exit', side_effect=SystemExit(0)))
    
    for p in patches:
        p.__enter__()
        
    try:
        try:
            wm.chapter_9_start()
        except SystemExit:
            pass
    finally:
        for p in reversed(patches):
            p.__exit__(None, None, None)
            
    return wm

# ===========================================================================
# CAPÍTULO 9 — O GÉLIDO SILÊNCIO
# ===========================================================================

class TestChapter9:
    def test_party_guerreiro_gate(self):
        """1. Party com Guerreiro → gelido_totem_erguido, Uivador enfraquecido."""
        wm = _make_world(CharacterClass.GUERREIRO)
        # Inputs:
        # - Escolha no gate: "1" (Guerreiro)
        # - Aceitar Side Quest: "1" (Sim)
        # - Entregar pingente: "1" (Sim)
        # - Recrutar Ulfgar: "1" (Sim)
        _run_chapter_9(wm, ["1", "1", "1", "1"])
        
        assert wm.state.get_flag("gelido_totem_erguido") is True
        assert wm.state.get_flag("vesper_gelido_confrontada") is True
        assert wm.state.get_flag("ulfgar_ajudado") is True
        assert wm.player.companion.name == "Ulfgar"
        
        # Uivador deve começar com HP reduzido (-50 HP -> 200 HP)
        uivador_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Uivador" in item[0]), None)
        assert uivador_entry is not None
        assert uivador_entry[1] == 200

    def test_party_mago_gate(self):
        """2. Party com Mago → gelido_gelo_derretido, recusa side quest."""
        wm = _make_world(CharacterClass.MAGO)
        # Inputs:
        # - Escolha no gate: "2" (Mago)
        # - Recusar Side Quest: "2" (Não)
        _run_chapter_9(wm, ["2", "2"])
        
        assert wm.state.get_flag("gelido_gelo_derretido") is True
        assert not wm.state.get_flag("ulfgar_ajudado")
        
        uivador_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Uivador" in item[0]), None)
        assert uivador_entry is not None
        assert uivador_entry[1] == 200

    def test_party_ladino_gate(self):
        """3. Party com Ladino → gelido_trilha_furtiva."""
        wm = _make_world(CharacterClass.LADINO)
        _run_chapter_9(wm, ["3", "2"])
        
        assert wm.state.get_flag("gelido_trilha_furtiva") is True

    def test_party_clerigo_gate(self):
        """4. Party com Clérigo → gelido_totem_purificado."""
        wm = _make_world(CharacterClass.CLERIGO)
        _run_chapter_9(wm, ["4", "2"])
        
        assert wm.state.get_flag("gelido_totem_purificado") is True

    def test_party_no_gate_caminho_dificil(self):
        """5. Party sem a classe correspondente ao voto → combate extra, HP reduzido (-20 HP)."""
        wm = _make_world(CharacterClass.MAGO)
        wm.player.hp = 100
        # Inputs:
        # - Escolha no gate: "1" (Voto em Guerreiro, mas party só tem Mago!)
        # - Recusar Side Quest: "2"
        _run_chapter_9(wm, ["1", "2"])
        
        # Como a classe Guerreiro não estava presente, deve ativar o debuff de frio extremo
        assert wm.state.get_flag("cold_debuff_active") is True
        
        # Jogador deve começar com HP reduzido (-20 HP)
        assert wm.player.hp == 80
        
        # Uivador deve começar com HP cheio (250 HP)
        uivador_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Uivador" in item[0]), None)
        assert uivador_entry is not None
        assert uivador_entry[1] == 250
        
        # Deve ter havido combate extra contra o espectro
        espectros = [item for item in _FakeCombatCapture.captured_enemies if "Espectro" in item[0]]
        assert len(espectros) == 1

    def test_companion_replacement(self):
        """6. Regra de substituição de companheiro: Elena deixa a party ao recrutar Ulfgar."""
        from engine.companion import get_companion
        wm = _make_world(CharacterClass.GUERREIRO)
        wm.player.companion = get_companion("elena")
        assert wm.player.companion.name == "Elena"
        
        # Inputs:
        # - Escolha no gate: "1" (Guerreiro)
        # - Aceitar Side Quest: "1" (Sim)
        # - Entregar pingente: "1" (Sim)
        # - Recrutar Ulfgar: "1" (Sim)
        _run_chapter_9(wm, ["1", "1", "1", "1"])
        
        # Companheiro agora deve ser Ulfgar
        assert wm.player.companion.name == "Ulfgar"
