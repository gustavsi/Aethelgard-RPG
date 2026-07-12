import pytest
from unittest.mock import patch, MagicMock
from engine.player import Player
from engine.state import GameState
from engine.world import WorldManager
from engine.constants import CharacterClass, StatusEffect
from engine.combat import CombatSystem, Command
from engine.combat_ui import CombatUI
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

def _run_chapter_7(wm, inputs):
    _FakeCombatCapture.reset()
    input_queue = InputQueue(inputs)
    patches = []

    _UI_FNS = ('clear_screen', 'typewriter', 'press_any_key', 'print_centered', 'play_sound_effect')
    _MODULES = ('engine.world_chapter_3', 'engine.world_chapter_4', 'engine.world_chapter_5', 'engine.world', 'engine.world_chapter_7')
    
    for mod in _MODULES:
        for fn in _UI_FNS:
            patches.append(patch(f'{mod}.{fn}', return_value=None))
            
    # No get_menu_choice in world_chapter_7
    patches.append(patch('engine.world_chapter_7.CombatSystem', _FakeCombatCapture))
    patches.append(patch('engine.world.CombatSystem', _FakeCombatCapture))
    patches.append(patch.object(wm, 'chapter_8_start', side_effect=wm.credits))
    patches.append(patch.object(wm, 'get_leader_choice', side_effect=input_queue))
    
    adapter_mock = MagicMock()
    adapter_mock.emit = MagicMock(return_value=None)
    wm.adapter = adapter_mock
    
    patches.append(patch('sys.exit', side_effect=SystemExit(0)))
    
    for p in patches:
        p.__enter__()
        
    try:
        try:
            wm.chapter_7_start()
        except SystemExit:
            pass
    finally:
        for p in reversed(patches):
            p.__exit__(None, None, None)
            
    return wm

# ===========================================================================
# CAPÍTULO 7 — PORTO DE VAELMOOR
# ===========================================================================

class TestChapter7:
    def test_party_ladino_gate(self):
        """1. Party só com Ladino → vaelmoor_infiltrado, sem combate extra."""
        wm = _make_world(CharacterClass.LADINO)
        # Inputs:
        # - Escolha no gate: "1" (Ladino class gate)
        # - Escolha side quest: "2" (Recusar a missão)
        _run_chapter_7(wm, ["1", "2"])
        
        assert wm.state.get_flag("vaelmoor_infiltrado") is True
        assert wm.state.get_flag("vesper_confrontada") is True
        
        # Grum deve começar com HP reduzido (-40 HP -> 160 HP)
        grum_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Grum" in item[0]), None)
        assert grum_entry is not None
        assert grum_entry[1] == 160
        
        # Não deve haver combate extra contra piratas da Maré Negra
        pirates = [item for item in _FakeCombatCapture.captured_enemies if "Pirata" in item[0]]
        assert len(pirates) == 0

    def test_party_guerreiro_gate(self):
        """2. Party só com Guerreiro → vaelmoor_duelo_vencido."""
        wm = _make_world(CharacterClass.GUERREIRO)
        _run_chapter_7(wm, ["2", "2"])
        
        assert wm.state.get_flag("vaelmoor_duelo_vencido") is True
        assert wm.state.get_flag("vesper_confrontada") is True
        
        grum_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Grum" in item[0]), None)
        assert grum_entry is not None
        assert grum_entry[1] == 160

    def test_party_mago_gate(self):
        """3. Party só com Mago → vaelmoor_selo_identificado."""
        wm = _make_world(CharacterClass.MAGO)
        _run_chapter_7(wm, ["3", "2"])
        
        assert wm.state.get_flag("vaelmoor_selo_identificado") is True
        assert wm.state.get_flag("vesper_confrontada") is True
        
        grum_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Grum" in item[0]), None)
        assert grum_entry is not None
        assert grum_entry[1] == 160

    def test_party_clerigo_gate(self):
        """4. Party só com Clérigo → vaelmoor_corrupcao_sentida."""
        wm = _make_world(CharacterClass.CLERIGO)
        _run_chapter_7(wm, ["4", "2"])
        
        assert wm.state.get_flag("vaelmoor_corrupcao_sentida") is True
        assert wm.state.get_flag("vesper_confrontada") is True
        
        grum_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Grum" in item[0]), None)
        assert grum_entry is not None
        assert grum_entry[1] == 160

    def test_party_no_gate_caminho_dificil(self):
        """5. Party sem nenhuma classe gate correspondente → caminho difícil."""
        wm = _make_world(CharacterClass.GUERREIRO)
        # Escolha "5" (Invasão direta)
        _run_chapter_7(wm, ["5", "2"])
        
        assert not wm.state.get_flag("vaelmoor_infiltrado")
        assert not wm.state.get_flag("vaelmoor_duelo_vencido")
        assert not wm.state.get_flag("vaelmoor_selo_identificado")
        assert not wm.state.get_flag("vaelmoor_corrupcao_sentida")
        assert wm.state.get_flag("vesper_confrontada") is True
        
        # Grum deve começar com HP cheio (200 HP)
        grum_entry = next((item for item in _FakeCombatCapture.captured_enemies if "Grum" in item[0]), None)
        assert grum_entry is not None
        assert grum_entry[1] == 200
        
        # Deve ter havido combate extra contra os 2 piratas
        pirates = [item for item in _FakeCombatCapture.captured_enemies if "Pirata" in item[0]]
        assert len(pirates) == 2

    def test_afogamento_blocks_skills(self):
        """O efeito AFOGAMENTO bloqueia habilidades corretamente durante a luta com Grum."""
        player = Player("TestHero", CharacterClass.MAGO)
        player.level = 8
        
        player.status_effects[StatusEffect.AFOGAMENTO] = 2
        
        state = GameState(player)
        enemy = Enemy("Grum", 100, 10, 5, 100, 100)
        combat = CombatSystem(state, [enemy])
        
        ui = CombatUI(combat)
        adapter = MagicMock()
        
        # We need a custom emit logic since ChoiceRequested is called multiple times,
        # plus intermediate calls for NarrativeText / PressAnyKey
        def custom_emit(event):
            from engine.dto import ChoiceRequested
            if isinstance(event, ChoiceRequested):
                if not hasattr(custom_emit, "called"):
                    custom_emit.called = True
                    return "2" # Habilidades (blocked)
                return "1" # Atacar
            return None
            
        adapter.emit.side_effect = custom_emit
        ui.prompt_target = MagicMock(return_value=0)
        combat.adapter = adapter
        
        cmd = ui.prompt_action()
        assert cmd.action == "ATTACK"
        assert cmd.target == 0
        
        # Valida que o aviso de afogamento foi exibido
        from engine.dto import NarrativeText
        emitted_texts = [args[0].content for name, args, kwargs in adapter.emit.mock_calls if isinstance(args[0], NarrativeText)]
        assert any("afogando" in text for text in emitted_texts)

    def test_act_ii_epilogue_hook_from_endings(self):
        """O act_ii_epilogue_hook() funciona a partir dos 3 finais diferentes."""
        # 1. Herói da Luz
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True
        })
        with patch.object(wm, 'chapter_7_start') as mock_c7, \
             patch('engine.world_chapter_5.clear_screen'), \
             patch('engine.world_chapter_5.typewriter'), \
             patch('engine.world_chapter_5.press_any_key'), \
             patch('engine.world.clear_screen'), \
             patch('engine.world.typewriter'), \
             patch('engine.world.press_any_key'), \
             patch('engine.world.print_centered'), \
             patch('engine.world_chapter_7.clear_screen'), \
             patch('engine.world_chapter_7.typewriter'), \
             patch('engine.world_chapter_7.press_any_key'), \
             patch('engine.world_chapter_7.print_centered'):
            wm.ending_sequence()
            mock_c7.assert_called_once()
            
        # 2. Senhor das Sombras
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "guardou_pergaminho": True,
            "lacre_sombrio": True
        })
        with patch.object(wm, 'chapter_7_start') as mock_c7, \
             patch('engine.world_chapter_5.clear_screen'), \
             patch('engine.world_chapter_5.typewriter'), \
             patch('engine.world_chapter_5.press_any_key'), \
             patch('engine.world.clear_screen'), \
             patch('engine.world.typewriter'), \
             patch('engine.world.press_any_key'), \
             patch('engine.world.print_centered'), \
             patch('engine.world_chapter_7.clear_screen'), \
             patch('engine.world_chapter_7.typewriter'), \
             patch('engine.world_chapter_7.press_any_key'), \
             patch('engine.world_chapter_7.print_centered'):
            wm.ending_sequence()
            mock_c7.assert_called_once()
            
        # 3. Andarilho Solitário
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "elena_morta": True
        })
        with patch.object(wm, 'chapter_7_start') as mock_c7, \
             patch('engine.world_chapter_5.clear_screen'), \
             patch('engine.world_chapter_5.typewriter'), \
             patch('engine.world_chapter_5.press_any_key'), \
             patch('engine.world.clear_screen'), \
             patch('engine.world.typewriter'), \
             patch('engine.world.press_any_key'), \
             patch('engine.world.print_centered'), \
             patch('engine.world_chapter_7.clear_screen'), \
             patch('engine.world_chapter_7.typewriter'), \
             patch('engine.world_chapter_7.press_any_key'), \
             patch('engine.world_chapter_7.print_centered'):
            wm.ending_sequence()
            mock_c7.assert_called_once()
