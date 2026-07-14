import random
from engine.constants import Colors

def play_sound_effect(effect_id: str, color=None):
    from engine.dto import SoundEffect
    from engine.adapter import get_adapter
    get_adapter().emit(SoundEffect(effect_id))

class Companion:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def act(self, player, enemies, add_log_func):
        pass

class ElenaCompanion(Companion):
    def __init__(self):
        super().__init__("Elena", "Arqueira habilidosa de Oakhaven.")

    def act(self, player, enemies, add_log_func):
        alive_enemies = [e for e in enemies if e.is_alive()]
        if not alive_enemies:
            return
            
        if player.hp / player.max_hp < 0.45:
            healed = player.heal(25)
            add_log_func(f"Elena usa Poção de Cura em {player.name}! Curou {Colors.GREEN}{healed} HP{Colors.RESET}.")
            play_sound_effect("HEAL PULSE", Colors.GREEN)
        else:
            target = random.choice(alive_enemies)
            dmg = 12 + player.level * 2
            res = target.take_damage(dmg)
            damage_dealt = res["damage_taken"]
            desc = f"Causou {damage_dealt} de dano em {target.name}."
            if res.get("mitigated"):
                desc += " (Mitigado por defesa ativa!)"
            add_log_func(f"Elena atira uma flecha rápida em {target.name}!")
            add_log_func(desc)
            play_sound_effect("ARROW WHOOSH", Colors.CYAN)

class DroggCompanion(Companion):
    def __init__(self):
        super().__init__("Drogg (Ogro)", "Ogro corpulento empunhando um porrete.")

    def act(self, player, enemies, add_log_func):
        alive_enemies = [e for e in enemies if e.is_alive()]
        if not alive_enemies:
            return
            
        target = random.choice(alive_enemies)
        dmg = 20 + player.level * 3
        res = target.take_damage(dmg)
        damage_dealt = res["damage_taken"]
        desc = f"Causou {damage_dealt} de dano em {target.name}."
        if res.get("mitigated"):
            desc += " (Mitigado por defesa ativa!)"
        add_log_func(f"Drogg esmaga {target.name} com um porrete pesado!")
        add_log_func(desc)
        play_sound_effect("HEAVY CRASH", Colors.RED)

class YsoldeCompanion(Companion):
    def __init__(self):
        super().__init__("Capitã Ysolde", "Corsária destemida de Vaelmoor, especialista em combate e tiro de arpéu.")

    def act(self, player, enemies, add_log_func):
        alive_enemies = [e for e in enemies if e.is_alive()]
        if not alive_enemies:
            return
            
        target = random.choice(alive_enemies)
        dmg = 15 + player.level * 2
        res = target.take_damage(dmg)
        damage_dealt = res["damage_taken"]
        desc = f"Causou {damage_dealt} de dano em {target.name}."
        if res.get("mitigated"):
            desc += " (Mitigado por defesa ativa!)"
        add_log_func(f"Capitã Ysolde atira seu arpéu com força em {target.name}!")
        add_log_func(desc)
        
        # 30% chance to stun
        if random.random() < 0.35:
            from engine.constants import StatusEffect
            target.status_effects[StatusEffect.ATORDOADO] = 1
            add_log_func(f"🔗 O arpéu prende e deixa {target.name} Atordoado por 1 turno!")
            
        play_sound_effect("GRAPPLE PULL", Colors.CYAN)

class UlfgarCompanion(Companion):
    def __init__(self):
        super().__init__("Ulfgar", "Caçador experiente do norte, mestre em tiros de precisão gélidos.")

    def act(self, player, enemies, add_log_func):
        alive_enemies = [e for e in enemies if e.is_alive()]
        if not alive_enemies:
            return
            
        target = random.choice(alive_enemies)
        dmg = 16 + player.level * 3
        res = target.take_damage(dmg)
        damage_dealt = res["damage_taken"]
        desc = f"Causou {damage_dealt} de dano em {target.name}."
        if res.get("mitigated"):
            desc += " (Mitigado por defesa ativa!)"
        add_log_func(f"Ulfgar faz um disparo de precisão com flecha congelante em {target.name}!")
        add_log_func(desc)
        
        # 30% chance to freeze/stun
        if random.random() < 0.30:
            from engine.constants import StatusEffect
            target.status_effects[StatusEffect.ATORDOADO] = 1
            add_log_func(f"❄️ O frio da flecha congelou e deixou {target.name} Atordoado por 1 turno!")
            
        play_sound_effect("ARROW WHOOSH", Colors.CYAN)

def get_companion(companion_id: str) -> Companion:
    if companion_id == "elena":
        return ElenaCompanion()
    elif companion_id == "drogg":
        return DroggCompanion()
    elif companion_id == "ysolde":
        return YsoldeCompanion()
    elif companion_id == "ulfgar":
        return UlfgarCompanion()
    return None
