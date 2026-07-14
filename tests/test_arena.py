import pytest
from unittest.mock import MagicMock, patch
from engine.player import Player
from engine.constants import CharacterClass, AIType
from engine.world import WorldManager
from engine.arena import generate_arena_enemies, run_arena_loop
from engine.state import GameState

def test_generate_arena_enemies():
    # Wave 1 -> 1-3 normal enemies
    enemies_w1 = generate_arena_enemies(1)
    assert len(enemies_w1) >= 1
    assert len(enemies_w1) <= 3
    assert enemies_w1[0].attack >= 5
    
    # Wave 3 -> 1 Ogro
    enemies_w3 = generate_arena_enemies(3)
    assert len(enemies_w3) == 1
    assert enemies_w3[0].name == "Ogro de Guerra"
    assert enemies_w3[0].ai_type == AIType.BOSS_OGRE
    
    # Wave 5 -> 1 Boss
    enemies_w5 = generate_arena_enemies(5)
    assert len(enemies_w5) == 1
    assert enemies_w5[0].ai_type in [AIType.BOSS_MALAKAR, AIType.BOSS_INQUISITOR, AIType.BOSS_GOLEM, AIType.BOSS_OGRE]

@patch("engine.arena.typewriter")
@patch("engine.arena.press_any_key")
def test_arena_loop_flow(mock_press, mock_typewrite):
    # Setup player and world
    p = Player("Grom", CharacterClass.GUERREIRO)
    state = GameState(p)
    world = WorldManager(p)
    world.state = state
    world.party = [p]
    
    # Mock adapter
    adapter = MagicMock()
    
    # Mock get_leader_choice to select "1" (first draft choice)
    world.get_leader_choice = MagicMock(return_value="1")
    
    # Mock CombatSystem to run and return True (victory) on first wave, then False (defeat) on second wave
    # We do this by mocking CombatSystem's run method using a side_effect
    with patch("engine.arena.CombatSystem") as MockCombatSystem:
        mock_combat_instance = MagicMock()
        mock_combat_instance.run.side_effect = [True, False]  # Victory w1, Defeat w2
        MockCombatSystem.return_value = mock_combat_instance
        
        # Run arena loop
        run_arena_loop(world, adapter)
        
        # Check wave state
        assert world.state.get_flag("arena_wave") == 2
        
        # Verify that get_leader_choice was called once (after wave 1 victory)
        world.get_leader_choice.assert_called_once()
        
        # Verify that GAME_OVER event was dispatched
        adapter.ws_callback.assert_called_with({"type": "GAME_OVER", "prompt": "Você sucumbiu ao Coliseu na Onda 2."})
