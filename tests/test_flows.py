import pytest
from unittest.mock import patch
import builtins

from game import main
from engine.player import Player
from engine.combat import CombatSystem
from engine.enemy import spawn_enemy
from engine.constants import CharacterClass

@pytest.fixture(autouse=True)
def mock_sleep_and_clear():
    with patch('time.sleep', return_value=None), \
         patch('engine.console.clear_screen', return_value=None):
        yield

def test_character_creation():
    """Testa se a criação de personagem flui e inicializa corretamente."""
    # Input sequence:
    # 1. "TestHero"
    # 2. "2" (Mago)
    inputs = ["TestHero", "2"]
    
    # We mock WorldManager.run_game to stop execution after creation
    with patch('builtins.input', side_effect=inputs), \
         patch('engine.world.WorldManager.run_game') as mock_run:
         
         main()
         
         # The world manager should have been instantiated with a Mago named TestHero
         # It's hard to assert directly inside main() without capturing, but mock_run.assert_called_once() confirms it passed creation
         mock_run.assert_called_once()


from engine.state import GameState

def test_combat_victory():
    """Testa o fluxo de um combate vencido."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    enemy = spawn_enemy("lobo_floresta")
    
    state = GameState(player)
    combat = CombatSystem(state, [enemy])
    
    # Combat inputs:
    # 1. "1" (Attack) -> will hit enemy
    # We need enough inputs to kill the enemy. A Guerreiro with 12 strength against Lobo (40 HP).
    # Might take ~4-5 attacks.
    inputs = ["1", "1", "1", "1", "1", "1", "1", "1"]
    
    with patch('builtins.input', side_effect=inputs):
        result = combat.run()
        
    assert result is True # Player won
    assert enemy.hp <= 0
    assert player.xp > 0

def test_combat_flee():
    """Testa a fuga do combate."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    enemy = spawn_enemy("lobo_floresta")
    
    state = GameState(player)
    combat = CombatSystem(state, [enemy])
    
    # Input 5 is "Fugir"
    # We mock random.random to return 0.0 (guaranteed flee)
    with patch('builtins.input', side_effect=["5"]), \
         patch('random.random', return_value=0.0):
        result = combat.run()
        
    assert result == 'FLED'

def test_combat_with_turn_hook():
    """Testa se o combat processa corretamente um turn_hook e encerra a luta se retornar END_COMBAT."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    enemy = spawn_enemy("lobo_floresta")
    
    # Hook that triggers after 2 turns and ends combat
    def my_hook(combat_system):
        if combat_system.turn >= 2:
            return "END_COMBAT"
        return None
        
    state = GameState(player)
    combat = CombatSystem(state, [enemy], turn_hook=my_hook)
    
    # Input sequence for player (ATTACK)
    # The combat will end on turn 2 due to the hook, so we just need a few inputs.
    # On turn 1: Player attacks (input "1"), then Enemy attacks. turn becomes 2.
    # On turn 2: hook returns END_COMBAT. The FSM should transition to VICTORY.
    inputs = ["1", ""]
    
    with patch('builtins.input', side_effect=inputs):
        result = combat.run()
        
    assert result is True # Victory triggered by END_COMBAT
    assert combat.turn == 2 # Ended exactly on turn 2
    assert enemy.hp > 0 # Enemy didn't die by damage

