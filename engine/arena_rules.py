import random
from engine.constants import StatusEffect

def apply_arena_hazard(combat_system) -> None:
    """Aplica perigos e efeitos ambientais rotativos a cada 3 turnos de combate na Arena."""
    if not combat_system.state.get_flag("is_arena"):
        return
        
    turn = combat_system.turn
    if turn < 3 or (turn % 3 != 0):
        return
        
    hazards = [
        ("Chão de Espinhos", "Espinhos brotam do solo! Todos os combatentes sofrem 10 de dano físico.", apply_spikes_hazard),
        ("Ventania Impetuosa", "Uma forte ventania sopra pela arena, reduzindo a precisão física geral neste turno!", apply_wind_hazard),
        ("Névoa de Cura", "Uma névoa restauradora envolve a arena, curando 15 HP de todos os combatentes!", apply_mist_hazard),
        ("Clamor do Público", "A plateia grita em frenesi! Todos os combatentes ganham Fúria por 1 turno!", apply_crowd_hazard)
    ]
    
    hazard_name, description, effect_fn = random.choice(hazards)
    combat_system.add_log(f"⚠️ [ARENA] {hazard_name.upper()}: {description}")
    effect_fn(combat_system)

def apply_spikes_hazard(combat_system):
    for p in [p for p in combat_system.state.party if p.hp > 0]:
        res = p.take_damage(10)
        combat_system.add_log(f"💥 {p.name} sofreu {res['damage_taken']} de dano.")
    for e in [e for e in combat_system.enemies if e.is_alive()]:
        res = e.take_damage(10)
        combat_system.add_log(f"💥 {e.name} sofreu {res['damage_taken']} de dano.")

def apply_wind_hazard(combat_system):
    combat_system.state.set_flag("arena_wind_active", combat_system.turn)

def apply_mist_hazard(combat_system):
    for p in [p for p in combat_system.state.party if p.hp > 0]:
        healed = p.heal(15)
        combat_system.add_log(f"💖 {p.name} curou {healed} HP.")
    for e in [e for e in combat_system.enemies if e.is_alive()]:
        healed = e.heal(15)
        combat_system.add_log(f"💖 {e.name} curou {healed} HP.")

def apply_crowd_hazard(combat_system):
    for p in [p for p in combat_system.state.party if p.hp > 0]:
        p.status_effects[StatusEffect.FURIA] = 1
    for e in [e for e in combat_system.enemies if e.is_alive()]:
        e.status_effects[StatusEffect.FURIA] = 1
