import pytest
from unittest.mock import patch, MagicMock
from engine.constants import CharacterClass
from engine.player import Player
from engine.state import GameState
from engine.side_quests import SideQuest
from tests.test_chapter_7 import _run_chapter_7, _FakeCombatCapture
from tests.test_chapters import _make_world

# ===========================================================================
# SIDE QUESTS & RECRUTAMENTO DE YSOLDE
# ===========================================================================

class TestSideQuests:
    def test_unit_accept_twice_and_complete(self):
        """Teste unitário: aceitar, aceitar duas vezes (retorna False) e completar a quest."""
        player = Player("Hero", CharacterClass.MAGO)
        state = GameState(player)
        
        # Criação de um WorldManager/mock simples para representar o ambiente
        world = MagicMock()
        world.state = state
        world.player = player
        
        rewards_called = 0
        def reward_test(w):
            nonlocal rewards_called
            rewards_called += 1
            w.player.gold += 100
            
        quest = SideQuest(
            "test_quest",
            "Test Name",
            "Test Description",
            "Test Giver",
            reward_fn=reward_test
        )
        
        logs = []
        add_log = lambda msg: logs.append(msg)
        
        # 1. Primeira aceitação
        assert quest.accept(world, add_log) is True
        assert state.get_flag("sidequest_test_quest_ativa") is True
        assert not state.get_flag("sidequest_test_quest_concluida")
        assert any("Nova missão opcional aceita" in l for l in logs)
        
        # 2. Segunda aceitação (não deve permitir)
        assert quest.accept(world, add_log) is False
        
        # 3. Conclusão da missão
        assert quest.complete(world, add_log) is True
        assert state.get_flag("sidequest_test_quest_ativa") is False
        assert state.get_flag("sidequest_test_quest_concluida") is True
        assert rewards_called == 1
        assert player.gold == 150 # Default starts at 50 for MAGO
        assert any("Missão Concluída" in l for l in logs)
        
        # 4. Tentar concluir novamente (não deve permitir)
        assert quest.complete(world, add_log) is False
        assert rewards_called == 1

    def test_ysolde_quest_accept_and_complete(self):
        """Integração: aceitar a quest de Ysolde, completar e recrutar como companheira."""
        wm = _make_world(CharacterClass.MAGO)
        # Inputs:
        # 1. "3" -> Class Gate Mago
        # 2. "1" -> Entrar em combate contra Grum
        # 3. "1" -> Aceitar a side quest de Ysolde
        # 4. "1" -> Entregar a carga recuperada para Ysolde
        # 5. "1" -> Recrutar Ysolde
        _run_chapter_7(wm, ["3", "1", "1", "1", "1"])
        
        # Validações
        assert wm.state.get_flag("sidequest_ysolde_carga_concluida") is True
        assert wm.state.get_flag("capitã_ysolde_aliada") is True
        
        # Valida que ganhou ouro da recompensa (+150 gold)
        # Gold inicial do Mago é 50
        assert wm.player.gold == 200
        
        # Valida que Ysolde agora é a companheira do player
        assert wm.player.companion is not None
        assert wm.player.companion.name == "Capitã Ysolde"

    def test_ysolde_quest_refuse(self):
        """Integração: recusar a quest de Ysolde e seguir viagem diretamente."""
        wm = _make_world(CharacterClass.MAGO)
        # Inputs:
        # 1. "3" -> Class Gate Mago
        # 2. "1" -> Entrar em combate contra Grum
        # 3. "2" -> Recusar a missão e seguir viagem
        _run_chapter_7(wm, ["3", "1", "2"])
        
        # Validações
        assert not wm.state.get_flag("sidequest_ysolde_carga_concluida")
        assert not wm.state.get_flag("capitã_ysolde_aliada")
        assert wm.player.gold == 50 # Mantém ouro inicial
        assert wm.player.companion is None
