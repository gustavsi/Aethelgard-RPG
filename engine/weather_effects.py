import random
from engine.dto import VisualEffect, SoundEffect
from engine.enemy import Enemy

def apply_lightning_hazard(combat_system) -> None:
    """Computa a mecânica de raios em combate sob clima Tempestade (15% de chance)."""
    weather = combat_system.state.get_flag("weather")
    if weather != "Tempestade":
        return
        
    if random.random() >= 0.15:
        return
        
    alive_players = [p for p in combat_system.state.party if p.hp > 0]
    alive_enemies = [e for e in combat_system.enemies if e.is_alive()]
    
    all_combatants = alive_players + alive_enemies
    if not all_combatants:
        return
        
    target = random.choice(all_combatants)
    damage = random.randint(15, 25)
    
    res = target.take_damage(damage)
    damage_taken = res.get("damage_taken", damage)
    
    combat_system.add_log(f"⚡ Um raio caiu dos céus e atingiu {target.name}, causando {damage_taken} de dano elétrico!")
    
    if combat_system.adapter:
        if isinstance(target, Enemy):
            target_id = f"enemy_{target.idx}"
        else:
            target_id = getattr(target, 'client_id', 'leader')
            
        combat_system.adapter.emit(SoundEffect("LIGHTNING_BOOM"))
        combat_system.adapter.emit(VisualEffect("lightning", target_id=target_id, duration=1000))
        combat_system.adapter.emit(VisualEffect("shake", target_id=target_id, duration=500))
