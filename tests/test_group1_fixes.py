import pytest
from engine.player import Player
from engine.state import GameState
from engine.constants import CharacterClass, StatusEffect
from engine.combat import CombatSystem, CombatPhase
from engine.enemy import Enemy
from engine.items import Weapon, Consumable

class MockAdapter:
    def __init__(self):
        self.logs = []
    def emit(self, dto):
        self.logs.append(dto)
    def on_state_change(self, state):
        pass

def test_status_effects_on_non_leader_party_member():
    """Bug 10: Verify non-leader living party members suffer status effect damage in TURN_START."""
    leader = Player("Leader", CharacterClass.GUERREIRO)
    member = Player("Member", CharacterClass.MAGO)
    
    leader.hp = 100
    member.hp = 50
    member.status_effects[StatusEffect.ENVENENADO] = 2
    
    state = GameState(leader)
    state.party = [leader, member]
    
    enemy = Enemy("Treino", 100, 100, 10, 0, 10, 10)
    combat = CombatSystem(state, [enemy])
    
    # Process turn start
    combat.phase = CombatPhase.TURN_START
    combat.advance_state()
    
    # Non-leader member must have taken poison damage (hp reduced from 50)
    assert member.hp < 50
    assert StatusEffect.ENVENENADO in member.status_effects
    assert member.status_effects[StatusEffect.ENVENENADO] == 1

def test_combat_rewards_split_equally_and_dead_leader_gets_nothing():
    """Bugs 8 & 3: XP and Gold split equally among living members; fallen leader receives 0."""
    leader = Player("Leader", CharacterClass.GUERREIRO)
    member1 = Player("Member1", CharacterClass.MAGO)
    member2 = Player("Member2", CharacterClass.LADINO)
    
    leader.hp = 0  # Dead leader
    member1.hp = 100
    member2.hp = 100
    
    leader.gold = 0
    member1.gold = 0
    member2.gold = 0
    
    leader.xp = 0
    member1.xp = 0
    member2.xp = 0
    
    state = GameState(leader)
    state.party = [leader, member1, member2]
    
    enemy = Enemy("Boss Teste", 100, 10, 0, 100, 100) # 100 HP, 10 Atk, 0 Def, 100 XP, 100 Gold
    combat = CombatSystem(state, [enemy])
    enemy.hp = 0  # Defeated enemy (set after CombatSystem scales HP)
    combat.enemies = [enemy]
    
    combat.distribute_rewards()
    
    # Dead leader gets 0 XP, 0 Gold
    assert leader.gold == 0
    assert leader.xp == 0
    
    # Living members get split XP (50 each) and split Gold (50 each)
    assert member1.gold == 50
    assert member2.gold == 50
    assert member1.xp == 50
    assert member2.xp == 50

def test_loot_item_assigned_to_single_living_recipient():
    """Bug 8: Non-consumable loot goes to single living recipient, not duplicated."""
    leader = Player("Leader", CharacterClass.GUERREIRO)
    member = Player("Member", CharacterClass.MAGO)
    
    state = GameState(leader)
    state.party = [leader, member]
    
    gear_item = Weapon("w1", "Machado Rúnico", 15, "raro")
    
    enemy = Enemy("Ogro da Cabana", 0, 100, 10, 0, 50, 50)
    combat = CombatSystem(state, [enemy])
    
    # Force single loot drop
    with pytest.MonkeyPatch.context() as m:
        m.setattr("engine.combat.get_random_loot", lambda lvl: gear_item)
        m.setattr("random.random", lambda: 0.0) # Ensure chance < 1.0 passes
        combat.distribute_rewards()
        
    # Gear item must appear in exactly ONE member's inventory
    in_leader = gear_item in leader.inventory
    in_member = gear_item in member.inventory
    assert (in_leader or in_member) and not (in_leader and in_member)

def test_quest_completion_for_all_party_members():
    """Bug 9: Quest completion updates quest_manager for every member in party."""
    leader = Player("Leader", CharacterClass.GUERREIRO)
    member = Player("Member", CharacterClass.CLERIGO)
    
    state = GameState(leader)
    state.party = [leader, member]
    
    # Start quest on all members
    for p in state.party:
        p.quest_manager.start_quest("cavernas", lambda msg: None)
        assert p.quest_manager.has_active("cavernas") is True
        
    # Complete quest for all party members
    for p in state.party:
        q = p.quest_manager.quests.get("cavernas")
        if q and not q.is_completed:
            p.quest_manager.complete_quest("cavernas", p, lambda msg: None)
            
    assert leader.quest_manager.quests["cavernas"].is_completed is True
    assert member.quest_manager.quests["cavernas"].is_completed is True
