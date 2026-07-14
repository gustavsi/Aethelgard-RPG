import pytest
from engine.player import Player
from engine.constants import CharacterClass
from engine.talents import unlock_talent, TALENTS_LIBRARY

def test_talent_points_on_level_up():
    p = Player("Grom", CharacterClass.GUERREIRO)
    assert p.talent_points == 0
    assert len(p.talents_unlocked) == 0
    
    # Gain enough XP to level up
    p.gain_xp(120)
    assert p.level == 2
    assert p.talent_points == 1

def test_unlock_talent_stat_boost():
    p = Player("Grom", CharacterClass.GUERREIRO)
    p.talent_points = 1
    
    # Try unlocking invalid or other class talent
    assert not unlock_talent(p, "mago_piromante_1")
    assert p.talent_points == 1
    
    # Unlock Colosso 1 (Pele de Ferro) -> max_hp + 20
    initial_max_hp = p.max_hp
    assert unlock_talent(p, "guerreiro_colosso_1")
    assert p.talent_points == 0
    assert "guerreiro_colosso_1" in p.talents_unlocked
    assert p.max_hp == initial_max_hp + 20

def test_unlock_talent_no_points():
    p = Player("Grom", CharacterClass.GUERREIRO)
    p.talent_points = 0
    assert not unlock_talent(p, "guerreiro_colosso_1")

def test_passive_combat_modifiers():
    # Warrior Colosso 2 -> Baluarte (10% damage reduction)
    p = Player("Grom", CharacterClass.GUERREIRO)
    p.talents_unlocked.append("guerreiro_colosso_2")
    
    # Calculate damage with defense = 0 to make math simple
    p.agilidade = 0  # No dodge
    p.armor = None
    
    # Regular take_damage logic: max(1, raw_damage - defense)
    # With Baluarte: max(1, (raw_damage - defense) * 0.9)
    res = p.take_damage(100)
    # base_atk defense is p.get_defense_power()
    expected_def = p.get_defense_power()
    expected_dmg = max(1, int((100 - expected_def) * 0.9))
    assert res["damage_taken"] == expected_dmg
