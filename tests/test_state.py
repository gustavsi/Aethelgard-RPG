import pytest
from engine.state import GameState
from engine.player import Player
from engine.constants import CharacterClass

def test_game_state_initialization():
    """Testa se o estado central é inicializado corretamente com UUID único."""
    player1 = Player("Herói 1", CharacterClass.GUERREIRO)
    player2 = Player("Herói 2", CharacterClass.MAGO)
    
    state1 = GameState(player1)
    state2 = GameState(player2)
    
    assert state1.session_id != state2.session_id, "O Session ID deve ser único para cada estado"
    assert state1.player.name == "Herói 1"
    assert state1.current_chapter == 1
    assert state1.current_location == "tutorial"

def test_game_state_flags():
    """Testa o armazenamento e recuperação de escolhas e consequências."""
    player = Player("Arthur", CharacterClass.LADINO)
    state = GameState(player)
    
    assert state.get_flag("ogro_poupado") is None
    
    state.set_flag("ogro_poupado", True)
    assert state.get_flag("ogro_poupado") is True
    
    state.set_flag("ouro_roubado", 500)
    assert state.get_flag("ouro_roubado") == 500

def test_game_state_serialization():
    """Testa se o snapshot de estado retorna um dicionário formatado e correto."""
    player = Player("Merlin", CharacterClass.MAGO)
    state = GameState(player)
    state.set_flag("ajudou_elena", False)
    
    snapshot = state.to_dict()
    
    assert snapshot["session_id"] == state.session_id
    assert "created_at" in snapshot
    assert snapshot["current_chapter"] == 1
    assert snapshot["player"]["name"] == "Merlin"
    assert snapshot["player"]["class"] == "Mago"
    assert snapshot["flags"]["ajudou_elena"] is False
    assert snapshot["in_combat"] is False
