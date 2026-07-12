import pytest
from unittest.mock import patch
from engine.player import Player
from engine.combat import CombatSystem, Command
from engine.enemy import spawn_enemy, Enemy
from engine.constants import CharacterClass, AIType, StatusEffect
from engine.state import GameState
from engine.adapter import UIAdapter
from engine.dto import VisualEffect, SoundEffect
from engine.skills import ALL_SKILLS

class RecordingAdapter(UIAdapter):
    def __init__(self):
        self.emitted = []

    def emit(self, event):
        self.emitted.append(event)
        return super().emit(event)

@pytest.fixture(autouse=True)
def mock_sleep_and_clear():
    orig_instance = UIAdapter.get_instance()
    with patch('time.sleep', return_value=None), \
         patch('engine.console.clear_screen', return_value=None):
        yield
        UIAdapter.set_instance(orig_instance)

def test_boss_roar_on_start():
    """Verify that boss_roar is emitted when starting combat with a boss."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    enemy = spawn_enemy("ogro_cabana")
    
    state = GameState(player)
    adapter = RecordingAdapter()
    combat = CombatSystem(state, [enemy], adapter=adapter)
    
    # Check if boss_roar was emitted
    boss_roar_events = [e for e in adapter.emitted if isinstance(e, SoundEffect) and e.effect_id == "boss_roar"]
    assert len(boss_roar_events) > 0

def test_no_boss_roar_on_normal():
    """Verify that boss_roar is NOT emitted when starting combat with a normal enemy."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    enemy = spawn_enemy("lobo_floresta")
    
    state = GameState(player)
    adapter = RecordingAdapter()
    combat = CombatSystem(state, [enemy], adapter=adapter)
    
    # Check if boss_roar was NOT emitted
    boss_roar_events = [e for e in adapter.emitted if isinstance(e, SoundEffect) and e.effect_id == "boss_roar"]
    assert len(boss_roar_events) == 0

def test_shake_on_player_and_enemy_attack():
    """Verify that a player basic attack and enemy basic attack trigger the shake visual effect."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    enemy = spawn_enemy("lobo_floresta")
    
    state = GameState(player)
    adapter = RecordingAdapter()
    combat = CombatSystem(state, [enemy], adapter=adapter)
    
    # Clear initial emits
    adapter.emitted.clear()
    
    # Player basic attack
    combat.player_attack_enemy(enemy)
    shake_events = [e for e in adapter.emitted if isinstance(e, VisualEffect) and e.effect_type == "shake"]
    assert len(shake_events) == 1
    assert shake_events[0].target_id == f"enemy_{enemy.idx}"
    
    adapter.emitted.clear()
    
    # Enemy turn/attack (we make enemy execute attack)
    # Target player has no dodge to ensure hit
    with patch('random.random', return_value=1.0):
        # We mock select_action to perform an ATTACK
        with patch.object(enemy, 'select_action', return_value=("ATTACK", 5, ["Lobo morde Guz!"])):
            combat.enemy_turn()
            
    enemy_shake_events = [e for e in adapter.emitted if isinstance(e, VisualEffect) and e.effect_type == "shake"]
    assert len(enemy_shake_events) == 1
    assert enemy_shake_events[0].target_id == "leader"

def test_skills_visual_and_sound_effects():
    """Verify projectile style and sfx are emitted correctly for different skills."""
    player = Player("Guz", CharacterClass.MAGO)
    player.inteligencia = 20
    enemy = spawn_enemy("lobo_floresta")
    
    state = GameState(player)
    adapter = RecordingAdapter()
    UIAdapter.set_instance(adapter)
    combat = CombatSystem(state, [enemy], adapter=adapter)
    
    # Find Bola de Fogo skill
    bola_de_fogo = next(s for s in ALL_SKILLS if s.name == "Bola de Fogo")
    
    adapter.emitted.clear()
    bola_de_fogo.execute(player, enemy, lambda text: None, 1)
    
    projectile_events = [e for e in adapter.emitted if isinstance(e, VisualEffect) and e.effect_type == "projectile"]
    sfx_events = [e for e in adapter.emitted if isinstance(e, SoundEffect)]
    
    assert len(projectile_events) == 1
    assert projectile_events[0].style == "fireball"
    assert projectile_events[0].from_side == "party"
    assert any(s.effect_id == "magic_cast" for s in sfx_events)

def test_heal_glow_on_heal_skills_and_items():
    """Verify that heal_glow and heal_chime are triggered on heal skills and consumable use."""
    player = Player("Guz", CharacterClass.CLERIGO)
    player.inteligencia = 20
    player.hp = 10  # damaged
    
    state = GameState(player)
    adapter = RecordingAdapter()
    UIAdapter.set_instance(adapter)
    combat = CombatSystem(state, [spawn_enemy("lobo_floresta")], adapter=adapter)
    
    # Test Luz Sagrada skill
    luz_sagrada = next(s for s in ALL_SKILLS if s.name == "Luz Sagrada")
    
    adapter.emitted.clear()
    luz_sagrada.execute(player, player, lambda text: None, 1)
    
    heal_glow_events = [e for e in adapter.emitted if isinstance(e, VisualEffect) and e.effect_type == "heal_glow"]
    sfx_events = [e for e in adapter.emitted if isinstance(e, SoundEffect)]
    
    assert len(heal_glow_events) == 1
    assert heal_glow_events[0].target_id == "leader"
    assert any(s.effect_id == "heal_chime" for s in sfx_events)

def test_downed_and_revive_sfx():
    """Verify that party_member_down is played when HP drops to 0 and revive plays on revival."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    player.hp = 10
    
    state = GameState(player)
    adapter = RecordingAdapter()
    combat = CombatSystem(state, [spawn_enemy("lobo_floresta")], adapter=adapter)
    
    # Drop player HP to 0
    adapter.emitted.clear()
    player.hp = 0
    combat.check_victory_defeat_or_transformation()
    
    down_sfx = [e for e in adapter.emitted if isinstance(e, SoundEffect) and e.effect_id == "party_member_down"]
    assert len(down_sfx) == 1
    
    # Heal player to revive
    adapter.emitted.clear()
    player.hp = 20
    combat.check_victory_defeat_or_transformation()
    
    revive_sfx = [e for e in adapter.emitted if isinstance(e, SoundEffect) and e.effect_id == "revive"]
    assert len(revive_sfx) == 1

def test_boss_transformation_sfx():
    """Verify that boss phase change triggers boss_phase_change and boss_roar SFX."""
    player = Player("Guz", CharacterClass.GUERREIRO)
    
    # Use a mock Inquisidor das Sombras (BOSS_INQUISITOR)
    enemy = Enemy("Inquisidor", hp=50, attack=10, defense=2, xp_reward=100, gold_reward=100, ai_type=AIType.BOSS_INQUISITOR)
    enemy.max_phases = 2
    enemy.phase = 1
    
    state = GameState(player)
    adapter = RecordingAdapter()
    combat = CombatSystem(state, [enemy], adapter=adapter)
    
    # Set enemy HP to 0 to trigger phase transformation
    enemy.hp = 0
    adapter.emitted.clear()
    
    # Mock Select Action to avoid actual transition print crashes during test
    with patch.object(enemy, 'select_action', return_value=("ATTACK", 10, ["Transformou!"])):
        combat.check_boss_transformations()
        
    sfx_events = [e for e in adapter.emitted if isinstance(e, SoundEffect)]
    assert any(s.effect_id == "boss_phase_change" for s in sfx_events)
    assert any(s.effect_id == "boss_roar" for s in sfx_events)
