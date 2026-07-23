import pytest
from engine.player import Player
from engine.enemy import Enemy
from engine.constants import CharacterClass, StatusEffect
from engine.combat import CombatSystem, CombatPhase

def test_furia_modifies_attack_and_defense_for_player_and_enemy():
    """Bug 11: StatusEffect.FURIA increases attack (+30%) and decreases defense (-30%) for Player and Enemy."""
    player = Player("Guerreiro", CharacterClass.GUERREIRO)
    player.forca = 20
    
    base_atk = player.get_attack_power()
    base_def = player.get_defense_power()
    
    # Apply Fúria
    player.status_effects[StatusEffect.FURIA] = 2
    
    furia_atk = player.get_attack_power()
    furia_def = player.get_defense_power()
    
    assert furia_atk > base_atk
    assert furia_atk == int(base_atk * 1.3)
    assert furia_def < base_def or base_def == 0
    assert furia_def == max(0, int(base_def * 0.7))
    
    # Test Enemy Fúria
    enemy = Enemy("Ogro", 100, 20, 10, 50, 50)
    enemy_base_atk = enemy.get_attack_power()
    enemy_base_def = enemy.get_defense_power()
    
    enemy.status_effects[StatusEffect.FURIA] = 2
    
    assert enemy.get_attack_power() == int(enemy_base_atk * 1.3)
    assert enemy.get_defense_power() == max(0, int(enemy_base_def * 0.7))

def test_furia_expires_after_turns():
    """Bug 12: StatusEffect.FURIA decrements each turn and is removed when duration reaches 0."""
    player = Player("Guerreiro", CharacterClass.GUERREIRO)
    player.status_effects[StatusEffect.FURIA] = 1
    
    class MockState:
        def __init__(self, p):
            import threading
            self.party = [p]
            self.player = p
            self.lock = threading.Lock()
            
    state = MockState(player)
    enemy = Enemy("Goblin", 30, 5, 0, 10, 10)
    combat = CombatSystem(state, [enemy])
    
    # Process turn start
    combat.process_target_status_effects(player, player.name, True)
    
    # Duration was 1, so after process_target_status_effects it must be removed
    assert StatusEffect.FURIA not in player.status_effects
