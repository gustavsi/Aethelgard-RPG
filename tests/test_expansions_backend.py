import pytest
from unittest.mock import MagicMock, patch
from engine.player import Player
from engine.constants import CharacterClass, StatusEffect, AIType
from engine.enemy import Enemy
from engine.combat import CombatSystem, Command
from engine.state import GameState
from engine.skills import bola_fogo, luz_sagrada, passo_sombras, check_nevoeiro_miss
from engine.weather_effects import apply_lightning_hazard
from engine.arena_rules import apply_arena_hazard
from engine.items import Item, ItemType, Rarity

def test_apply_lightning_hazard():
    p = Player("Grom", CharacterClass.GUERREIRO)
    state = GameState(p)
    state.set_flag("weather", "Tempestade")
    
    # Mock combat system
    combat = MagicMock()
    combat.state = state
    enemy = Enemy("Goblin", 50, 10, 2, 10, 10)
    enemy.idx = 0
    combat.enemies = [enemy]
    combat.adapter = MagicMock()
    
    # Force 15% trigger chance by mocking random.random to return 0.0
    with patch("random.random", return_value=0.0):
        # Trigger multiple times to ensure hitting someone
        # Let's test the hazard directly
        apply_lightning_hazard(combat)
        combat.add_log.assert_called()
        combat.adapter.emit.assert_called()

def test_items_weather_mitigation():
    p = Player("Grom", CharacterClass.GUERREIRO)
    state = GameState(p)
    state.set_flag("weather", "Chuvoso")
    
    # Without Capa Impermeável
    raw_damage_no_coat = int(p.inteligencia * 1.5)
    # Fire damage reduction by 20%
    expected_no_coat = int(raw_damage_no_coat * 0.8)
    
    enemy = Enemy("Goblin", 100, 10, 2, 10, 10)
    
    # Mock adapter
    adapter = MagicMock()
    adapter.state = state
    
    with patch("engine.adapter.get_adapter", return_value=adapter):
        # We manually test fire skill effect
        # Under Chuvoso, fire damage is reduced by 20%
        # Let's call bola_fogo
        enemy.hp = 100
        logs = []
        bola_fogo(p, enemy, logs.append, 1)
        # Verify reduced damage was dealt
        assert enemy.hp < 100
        assert "🌧️ A chuva enfraqueceu as chamas!" in logs
        
        # With Capa Impermeável
        coat = Item("Capa Impermeável", ItemType.QUEST, Rarity.RARO, "Mitigate rain", id="capa_impermeavel")
        state.shared_inventory.append(coat)
        
        enemy2 = Enemy("Goblin 2", 100, 10, 2, 10, 10)
        logs2 = []
        bola_fogo(p, enemy2, logs2.append, 1)
        assert "🌧️ A chuva enfraqueceu as chamas!" not in logs2

def test_lampeao_eter_mitigation():
    p = Player("Grom", CharacterClass.GUERREIRO)
    state = GameState(p)
    state.set_flag("weather", "Nevoeiro")
    
    adapter = MagicMock()
    adapter.state = state
    
    with patch("engine.adapter.get_adapter", return_value=adapter), patch("random.random", return_value=0.0):
        # Without Lampião -> miss is triggered
        assert check_nevoeiro_miss(p, None, lambda x: None)
        
        # With Lampião -> no miss
        lamp = Item("Lampião de Éter", ItemType.QUEST, Rarity.RARO, "Mitigate fog", id="lampeao_eter")
        state.shared_inventory.append(lamp)
        assert not check_nevoeiro_miss(p, None, lambda x: None)

def test_hybrid_talents_warrior():
    # Warrior Sinergy Juggernaut Calejado: Colosso 2 + Berserker 2
    p = Player("Grom", CharacterClass.GUERREIRO)
    p.talents_unlocked = ["guerreiro_colosso_2", "guerreiro_berserker_2"]
    p.max_hp = 100
    p.hp = 50
    
    state = GameState(p)
    enemy = Enemy("Goblin", 100, 0, 0, 0, 0)
    combat = CombatSystem(state, [enemy])
    
    # Trigger critical physical attack to heal Grom
    with patch("random.random", return_value=0.0): # Force critical hit
        combat.execute_player_attack(p, enemy)
        assert p.hp == 55 # Grom healed 5% (5 HP) on crit!
        assert any("Juggernaut Calejado" in log for log in combat.combat_logs)

def test_hybrid_talents_mage():
    # Mage Sinergy Tempestade de Gelo: Piromante 2 + Criomante 2
    p = Player("Ignis", CharacterClass.MAGO)
    p.talents_unlocked = ["mago_piromante_2", "mago_criomante_2"]
    
    state = GameState(p)
    enemy = Enemy("Goblin", 100, 0, 0, 0, 0)
    
    adapter = MagicMock()
    adapter.state = state
    with patch("engine.adapter.get_adapter", return_value=adapter):
        logs = []
        bola_fogo(p, enemy, logs.append, 1)
        # Should apply freeze (Atordoado) for 1 turn
        assert enemy.status_effects[StatusEffect.ATORDOADO] == 1
        assert any("Tempestade de Gelo" in log for log in logs)

def test_hybrid_talents_cleric():
    # Cleric Sinergy Cruzado: Santo 2 + Inquisidor 2
    p = Player("Uther", CharacterClass.CLERIGO)
    p.talents_unlocked = ["clerigo_santo_2", "clerigo_inquisidor_2"]
    
    state = GameState(p)
    adapter = MagicMock()
    adapter.state = state
    with patch("engine.adapter.get_adapter", return_value=adapter):
        logs = []
        luz_sagrada(p, p, logs.append, 1)
        # Should apply Furia
        assert p.status_effects[StatusEffect.FURIA] == 1


def test_hybrid_talents_rogue():
    # Rogue Sinergy Dança das Sombras: Assassino 2 + Trapaceiro 2
    p = Player("Valeera", CharacterClass.LADINO)
    p.talents_unlocked = ["ladino_assassino_2", "ladino_trapaceiro_2"]
    
    state = GameState(p)
    logs = []
    passo_sombras(p, None, logs.append, 1)
    # Should apply Furia for 2 turns
    assert p.status_effects[StatusEffect.FURIA] == 2
    assert any("Dança das Sombras" in log for log in logs)

def test_apply_arena_hazard():
    p = Player("Grom", CharacterClass.GUERREIRO)
    state = GameState(p)
    state.set_flag("is_arena", True)
    
    enemy = Enemy("Goblin", 100, 10, 2, 10, 10)
    combat = CombatSystem(state, [enemy])
    
    # Turn 3 is a hazard turn!
    combat.turn = 3
    
    # Mock random.choice to return the Spikes hazard
    with patch("random.choice", return_value=("Chão de Espinhos", "Espinhos brotam do solo!", lambda c: [p.take_damage(10) for p in c.state.party])):
        p.hp = 100
        apply_arena_hazard(combat)
        assert p.hp < 100
