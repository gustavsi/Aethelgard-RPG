import pytest
from unittest.mock import MagicMock
from engine.player import Player
from engine.constants import CharacterClass, StatusEffect, AIType, Rarity, ItemType
from engine.enemy import Enemy
from engine.combat import CombatSystem, CombatPhase
from engine.companion import ElenaCompanion
from engine.skills import luz_sagrada
from engine.dto import ChoiceRequested
from engine.console import get_menu_choice
from engine.save_system import save_game, load_game
from server import get_actual_leader_id

def test_dot_and_companion_victory_and_transformation():
    # Setup player and enemy
    player = Player("A", CharacterClass.GUERREIRO)
    boss = Enemy("Inquisidor das Sombras", 10, 10, 0, 100, 50, AIType.BOSS_INQUISITOR)
    
    # 1. DoT Victory & Transformation Check
    combat = CombatSystem(player, [boss])
    boss.hp = 1
    boss.status_effects[StatusEffect.ENVENENADO] = 1
    
    # Advance to trigger status effect on enemy. It should die, transform, and restore HP
    combat.phase = CombatPhase.ENEMY_TURN
    combat.advance_state()
    
    assert boss.phase == 2
    assert boss.hp == 200
    assert not combat.is_finished()
    
    # 2. Companion Victory Check
    boss.hp = 5
    boss.phase = 2  # No more transformations
    player.companion = ElenaCompanion()
    
    combat.phase = CombatPhase.COMPANION_TURN
    combat.advance_state()
    
    assert boss.hp == 0
    assert combat.is_finished()
    assert combat.phase == CombatPhase.VICTORY

def test_luz_sagrada_and_item_purge():
    # Luz Sagrada should only purge negatives
    player = Player("A", CharacterClass.CLERIGO)
    player.status_effects[StatusEffect.ENVENENADO] = 3
    player.status_effects[StatusEffect.PROTEGIDO] = 3
    
    logs = []
    def add_log(msg):
        logs.append(msg)
        
    luz_sagrada(player, None, add_log, 1)
    
    assert StatusEffect.ENVENENADO not in player.status_effects
    assert StatusEffect.PROTEGIDO in player.status_effects
    
    # Purge status item should also only purge negatives
    from engine.items import Consumable
    potion = Consumable(
        name="Test Potion",
        item_type=ItemType.CONSUMIVEL,
        rarity=Rarity.COMUM,
        description="Test",
        value=10,
        id="test_potion",
        purge_status=True
    )
    player.status_effects[StatusEffect.ENVENENADO] = 3
    player.status_effects[StatusEffect.PROTEGIDO] = 3
    
    potion.use(player)
    assert StatusEffect.ENVENENADO not in player.status_effects
    assert StatusEffect.PROTEGIDO in player.status_effects

def test_empty_menu_choice_graceful_exit(monkeypatch):
    # empty options in ChoiceRequested should get "exit": "Voltar"
    dto = ChoiceRequested("Test", {})
    assert dto.options == {"exit": "Voltar"}
    
    # Mock the adapter emit to return "exit" directly
    from engine.adapter import get_adapter
    adapter = get_adapter()
    monkeypatch.setattr(adapter, "emit", lambda event: "exit")
    
    choice = get_menu_choice([])
    assert choice == "exit"

def test_upgrade_serialization_and_deserialization():
    player = Player("A", CharacterClass.GUERREIRO)
    weapon = player.weapon
    weapon.attack_power += 4
    weapon.name += " +1"
    
    from engine.items import create_item
    sword_in_inv = create_item("espada_soldado")
    sword_in_inv.attack_power += 4
    sword_in_inv.name += " +1"
    player.inventory.append(sword_in_inv)
    
    from engine.state import GameState
    state = GameState(player)
    state.session_id = "test_serialization_session"
    
    # Save the game
    save_game(state, session_id="test_serialization_session")
    
    # Load the game
    loaded_state = load_game("test_serialization_session")
    loaded_player = loaded_state.player
    
    assert loaded_player.weapon.attack_power == weapon.attack_power
    assert loaded_player.weapon.name == weapon.name
    
    loaded_inv_sword = next(item for item in loaded_player.inventory if item.id == "espada_soldado")
    assert loaded_inv_sword.attack_power == sword_in_inv.attack_power
    assert loaded_inv_sword.name == sword_in_inv.name
    
    # Cleanup save file
    import os
    from engine.save_system import get_save_path
    filepath = get_save_path("test_serialization_session")
    if os.path.exists(filepath):
        os.remove(filepath)

def test_leader_resolution_by_name_or_class():
    session = {
        "leader_id": "client_a",
        "connected_clients": {
            "client_a": (None, "Alice", "GUERREIRO"),
            "client_b": (None, "Bob", "MAGO")
        }
    }
    
    # Mock world and state
    class MockState:
        def __init__(self):
            self.flags = {"party_lider": "bob"}
        def get_flag(self, key):
            return self.flags.get(key)
            
    class MockWorld:
        def __init__(self):
            self.state = MockState()
            
    world = MockWorld()
    
    # Resolve by name "bob"
    leader_id = get_actual_leader_id(session, world)
    assert leader_id == "client_b"
    
    # Resolve by class "mago"
    world.state.flags["party_lider"] = "mago"
    leader_id = get_actual_leader_id(session, world)
    assert leader_id == "client_b"
    
    # Fallback to leader_id if not matched
    world.state.flags["party_lider"] = "nonexistent"
    leader_id = get_actual_leader_id(session, world)
    assert leader_id == "client_a"

def test_antidote_creation():
    from engine.items import create_item
    antidote = create_item("antidoto")
    assert antidote is not None
    assert antidote.name == "Antídoto"
    assert antidote.value == 40
    assert antidote.purge_status is True
    assert antidote.heal_hp == 20

def test_save_path_traversal_protection():
    from engine.save_system import get_save_path
    unsafe_sid = "../../../etc/passwd"
    path = get_save_path(unsafe_sid)
    # The path should be sanitized to a flat filename
    assert "etcpasswd" in path
    assert ".." not in path
    assert "/" not in path or path.startswith("saves/")


