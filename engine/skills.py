from typing import Callable
from engine.constants import Colors, StatusEffect, CharacterClass
import random

def play_sound_effect(effect_id: str, color=None):
    from engine.dto import SoundEffect
    from engine.adapter import get_adapter
    get_adapter().emit(SoundEffect(effect_id))

def trigger_combat_effect(player, target, effect_type: str, style: str = None, duration: int = 800, sfx_id: str = None):
    from engine.dto import VisualEffect, SoundEffect
    from engine.adapter import get_adapter
    adapter = get_adapter()
    if adapter:
        if hasattr(target, 'ai_type'):
            target_id = f"enemy_{getattr(target, 'idx', 0)}"
        else:
            target_id = getattr(target, 'client_id', 'leader')
        from_side = "enemy" if hasattr(player, 'ai_type') else "party"
        adapter.emit(VisualEffect(effect_type, target_id=target_id, style=style, duration=duration, from_side=from_side))
        if sfx_id:
            adapter.emit(SoundEffect(sfx_id))

class Skill:
    def __init__(self, name: str, mp: int, desc: str, level: int, requires_target: bool, action: Callable):
        self.name = name
        self.mp = mp
        self.desc = desc
        self.level = level
        self.requires_target = requires_target
        self.action = action

    def execute(self, player, target, add_log_func, turn_number) -> None:
        self.action(player, target, add_log_func, turn_number)

# The logic of each skill:

def golpe_poderoso(player, target, add_log, turn):
    trigger_combat_effect(player, target, "shake", duration=400)
    raw_damage = int(player.forca * 1.8)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    play_sound_effect("POWERFUL SMASH", Colors.BRIGHT_RED)

def muralha_ferro(player, target, add_log, turn):
    player.status_effects[StatusEffect.PROTEGIDO] = 2
    add_log(f"{player.name} ergue uma muralha invisível! Dano recebido reduzido por 2 turnos.")
    play_sound_effect("FORTRESS", Colors.BLUE)

def golpe_devastador(player, target, add_log, turn):
    trigger_combat_effect(player, target, "shake", duration=400)
    raw_damage = int(player.forca * 2.8)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    if random.random() < 0.40:
        target.status_effects[StatusEffect.ATORDOADO] = 1
        add_log(f"{target.name} ficou Atordoado!")
    play_sound_effect("GROUND SMASH", Colors.RED)

def bola_fogo(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="fireball", duration=700, sfx_id="magic_cast")
    raw_damage = int(player.inteligencia * 1.5)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    target.status_effects[StatusEffect.QUEIMADO] = 3
    add_log(f"{target.name} começou a Queimar!")
    play_sound_effect("FIREBALL BURN", Colors.RED)

def escudo_arcano(player, target, add_log, turn):
    player.status_effects[StatusEffect.ESCUDO_ARCANO] = 35
    add_log(f"Cria uma barreira de força arcana em torno de {player.name} (Absorve 35 de dano).")
    play_sound_effect("ARCANE SHIELD", Colors.CYAN)

def trovao_celestial(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="slash", duration=500, sfx_id="magic_cast")
    raw_damage = int(player.inteligencia * 3.0)
    damage_dealt = max(1, raw_damage)
    target.hp = max(0, target.hp - damage_dealt)
    add_log(f"Relâmpago atravessa as defesas! Causou {damage_dealt} de dano em {target.name}.")
    play_sound_effect("THUNDERSTRIKE", Colors.BRIGHT_CYAN)

def ataque_furtivo(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="slash", duration=500, sfx_id="magic_cast")
    mult = 2.5 if turn == 1 else 1.6
    raw_damage = int(player.agilidade * mult)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    if turn == 1:
        add_log("Aproveitou o elemento surpresa!")
    play_sound_effect("SNEAK BLADE", Colors.BRIGHT_BLACK)

def passo_sombras(player, target, add_log, turn):
    player.status_effects[StatusEffect.ESQUIVA] = 3
    add_log(f"{player.name} se move como um vulto! Evasão grandemente aumentada.")
    play_sound_effect("SHADOW WALK", Colors.MAGENTA)

def lamina_venenosa(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="slash", duration=500, sfx_id="magic_cast")
    raw_damage = int(player.agilidade * 1.8)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    target.status_effects[StatusEffect.ENVENENADO] = 3
    add_log(f"{target.name} está Envenenado!")
    play_sound_effect("VENOM CUT", Colors.GREEN)

def luz_sagrada(player, target, add_log, turn):
    trigger_combat_effect(player, player, "heal_glow", duration=1200, sfx_id="heal_chime")
    heal_val = int(player.inteligencia * 2.2)
    healed = player.heal(heal_val)
    negatives = [StatusEffect.ENVENENADO, StatusEffect.QUEIMADO, StatusEffect.SANGRAMENTO, StatusEffect.ATORDOADO]
    removed = []
    for eff in negatives:
        if eff in player.status_effects:
            del player.status_effects[eff]
            removed.append(eff.name_str)
    if removed:
        add_log(f"Curou {healed} HP e removeu efeitos negativos: {', '.join(removed)}")
    else:
        add_log(f"Curou {healed} HP.")
    play_sound_effect("HEAL PULSE", Colors.BRIGHT_GREEN)

def punicao_divina(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="holy_bolt", duration=700, sfx_id="magic_cast")
    raw_damage = int(player.inteligencia * 1.5)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    heal_val = damage_dealt // 2
    healed = player.heal(heal_val)
    add_log(f"Restaurou {healed} HP através do elo de vida.")
    play_sound_effect("HOLY STRIKE", Colors.YELLOW)

def bencao_protetora(player, target, add_log, turn):
    trigger_combat_effect(player, player, "heal_glow", duration=1200, sfx_id="heal_chime")
    healed = player.heal(40)
    player.status_effects[StatusEffect.PROTEGIDO] = 2
    add_log(f"Curou {healed} HP e recebeu a Bênção da Proteção.")
    play_sound_effect("DIVINE SHIELD", Colors.YELLOW)

def flecha_perfurante(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="arrow", duration=600, sfx_id="arrow_release")
    raw_damage = int(player.agilidade * 2.0)
    # Ignore defense entirely by setting raw damage exactly to target's taken
    res = target.take_damage(raw_damage + target.defense)
    damage_dealt = res["damage_taken"]
    add_log(f"A flecha perfurou a armadura! Causou {damage_dealt} de dano.")
    play_sound_effect("ARROW PIERCE", Colors.BRIGHT_WHITE)

def chuva_flechas(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="arrow", duration=600, sfx_id="arrow_release")
    # Simulates hitting multiple times
    raw_damage = int(player.agilidade * 1.2)
    hits = random.randint(2, 4)
    total_dmg = 0
    for _ in range(hits):
        res = target.take_damage(raw_damage)
        total_dmg += res["damage_taken"]
    add_log(f"Chuva de Flechas atingiu {hits} vezes, causando um total de {total_dmg} de dano!")
    play_sound_effect("ARROW RAIN", Colors.YELLOW)

def tiro_preciso(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="arrow", duration=600, sfx_id="arrow_release")
    # Guaranteed high damage and stun
    raw_damage = int(player.agilidade * 3.0)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    target.status_effects[StatusEffect.ATORDOADO] = 1
    add_log(f"Tiro cravou em um ponto vital! {target.name} ficou Atordoado.")
    play_sound_effect("SNIPE", Colors.BRIGHT_YELLOW)

ALL_SKILLS = [
    Skill("Golpe Poderoso", 8, "Um golpe com força total (1.8x Força de dano)", 1, True, golpe_poderoso),
    Skill("Muralha de Ferro", 12, "Entra em postura defensiva. Recebe metade do dano por 2 turnos.", 3, False, muralha_ferro),
    Skill("Golpe Devastador", 20, "Ataque violento (2.8x Força) com 40% de chance de atordoar.", 6, True, golpe_devastador),
    
    Skill("Bola de Fogo", 10, "Lança chamas no inimigo (1.5x Int) e aplica Queimadura.", 1, True, bola_fogo),
    Skill("Escudo Arcano", 15, "Cria um escudo mágico que absorve até 35 de dano.", 3, False, escudo_arcano),
    Skill("Trovão Celestial", 22, "Raio devastador (3.0x Int) que ignora a defesa inimiga.", 6, True, trovao_celestial),
    
    Skill("Ataque Furtivo", 8, "Ataque rápido (1.6x Agi) com chance alta de crítico.", 1, True, ataque_furtivo),
    Skill("Passo de Sombras", 10, "Aumenta a esquiva em 35% por 3 turnos.", 3, False, passo_sombras),
    Skill("Lâmina Venenosa", 18, "Corta o alvo (1.8x Agi) e aplica Envenenamento severo.", 6, True, lamina_venenosa),
    
    Skill("Luz Sagrada", 10, "Cura divina (2.2x Int) e remove efeitos de status negativos.", 1, False, luz_sagrada),
    Skill("Punição Divina", 12, "Dano de luz (1.5x Int). Cura o jogador por metade do dano causado.", 3, True, punicao_divina),
    Skill("Bênção Protetora", 18, "Cura 40 de HP e concede proteção contra danos por 2 turnos.", 6, False, bencao_protetora),

    Skill("Flecha Perfurante", 10, "Ignora a defesa do alvo (2.0x Agi).", 1, True, flecha_perfurante),
    Skill("Chuva de Flechas", 16, "Atinge o alvo 2 a 4 vezes (1.2x Agi por hit).", 3, True, chuva_flechas),
    Skill("Tiro Preciso", 24, "Dano massivo (3.0x Agi) com atordoamento garantido.", 6, True, tiro_preciso)
]

def get_class_skills(char_class: CharacterClass, level: int) -> list:
    class_skill_names = {
        CharacterClass.GUERREIRO: ["Golpe Poderoso", "Muralha de Ferro", "Golpe Devastador"],
        CharacterClass.MAGO: ["Bola de Fogo", "Escudo Arcano", "Trovão Celestial"],
        CharacterClass.LADINO: ["Ataque Furtivo", "Passo de Sombras", "Lâmina Venenosa"],
        CharacterClass.CLERIGO: ["Luz Sagrada", "Punição Divina", "Bênção Protetora"],
        CharacterClass.ARQUEIRO: ["Flecha Perfurante", "Chuva de Flechas", "Tiro Preciso"]
    }
    names = class_skill_names.get(char_class, [])
    skills = [s for s in ALL_SKILLS if s.name in names and s.level <= level]
    return skills
