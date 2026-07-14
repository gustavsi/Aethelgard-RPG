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

def check_nevoeiro_miss(player, target, add_log, is_physical_or_arrow=True) -> bool:
    if not is_physical_or_arrow:
        return False
    from engine.adapter import get_adapter
    state = getattr(get_adapter(), "state", None)
    weather = state.get_flag("weather", "Ensolarado") if state else "Ensolarado"
    has_lamp = any(getattr(item, 'id', '') == 'lampeao_eter' for item in getattr(state, 'shared_inventory', [])) if state else False
    if weather == "Nevoeiro" and not has_lamp and random.random() < 0.20:
        add_log(f"🌫️ {player.name} tentou desferir a habilidade, mas errou devido à névoa densa!")
        play_sound_effect("SWOOSH!", Colors.BRIGHT_BLACK)
        return True
        
    turn = state.combat_state.get("turn", -1) if (state and state.combat_state) else -1
    wind_active = state.get_flag("arena_wind_active", -2) if state else -2
    if turn != -1 and wind_active == turn and random.random() < 0.20:
        add_log(f"💨 {player.name} tentou desferir a habilidade, mas errou devido à ventania impetuosa!")
        play_sound_effect("SWOOSH!", Colors.BRIGHT_BLACK)
        return True
    return False

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

def _scale_offense(raw_damage: int) -> int:
    """Phase 2 Void Corruption offense mult (no-op if disabled)."""
    try:
        from engine.adapter import get_adapter
        from engine.party_meta import offense_mult
        state = getattr(get_adapter(), "state", None)
        if state:
            return max(1, int(raw_damage * offense_mult(state)))
    except Exception:
        pass
    return raw_damage


def _scale_heal(amount: int, skill_name: str = "") -> int:
    """Phase 2: holy heals reduced by corruption."""
    try:
        from engine.adapter import get_adapter
        from engine.party_meta import heal_mult
        from engine.corruption import is_holy_skill_name
        state = getattr(get_adapter(), "state", None)
        if state and is_holy_skill_name(skill_name):
            return max(1, int(amount * heal_mult(state)))
    except Exception:
        pass
    return amount


def golpe_poderoso(player, target, add_log, turn):
    if check_nevoeiro_miss(player, target, add_log): return
    trigger_combat_effect(player, target, "shake", duration=400)
    raw_damage = _scale_offense(int(player.forca * 1.8))
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    play_sound_effect("POWERFUL SMASH", Colors.BRIGHT_RED)

def muralha_ferro(player, target, add_log, turn):
    player.status_effects[StatusEffect.PROTEGIDO] = 2
    add_log(f"{player.name} ergue uma muralha invisível! Dano recebido reduzido por 2 turnos.")
    play_sound_effect("FORTRESS", Colors.BLUE)

def golpe_devastador(player, target, add_log, turn):
    if check_nevoeiro_miss(player, target, add_log): return
    trigger_combat_effect(player, target, "shake", duration=400)
    raw_damage = _scale_offense(int(player.forca * 2.8))
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
    
    # Clima Modifiers
    from engine.adapter import get_adapter
    state = getattr(get_adapter(), "state", None)
    weather = state.get_flag("weather", "Ensolarado") if state else "Ensolarado"
    has_coat = any(getattr(item, 'id', '') == 'capa_impermeavel' for item in getattr(state, 'shared_inventory', [])) if state else False
    if weather in ["Chuvoso", "Tempestade"] and not has_coat:
        raw_damage = int(raw_damage * 0.8)
        add_log("🌧️ A chuva enfraqueceu as chamas!")
        
    if "mago_piromante_2" in getattr(player, "talents_unlocked", []):
        raw_damage = int(raw_damage * 1.25)
        add_log("🔥 Conflagração amplificou a bola de fogo!")

    raw_damage = _scale_offense(raw_damage)
        
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    target.status_effects[StatusEffect.QUEIMADO] = 3
    add_log(f"{target.name} começou a Queimar!")
    try:
        from engine.vesper_intel import record_tactic
        from engine.adapter import get_adapter
        st = getattr(get_adapter(), "state", None)
        if st:
            record_tactic(st, "burn")
    except Exception:
        pass
    unlocked = getattr(player, "talents_unlocked", [])
    if "mago_piromante_2" in unlocked and "mago_criomante_2" in unlocked:
        target.status_effects[StatusEffect.ATORDOADO] = 1
        add_log(f"❄️ Tempestade de Gelo: {target.name} ficou congelado (Atordoado) por 1 turno!")
    play_sound_effect("FIREBALL BURN", Colors.RED)

def escudo_arcano(player, target, add_log, turn):
    shield_val = 35
    if "mago_criomante_2" in getattr(player, "talents_unlocked", []):
        shield_val += 15
        add_log("❄️ Escudo de Gelo fortaleceu a barreira!")
    player.status_effects[StatusEffect.ESCUDO_ARCANO] = shield_val
    add_log(f"Cria uma barreira de força arcana em torno de {player.name} (Absorve {shield_val} de dano).")
    unlocked = getattr(player, "talents_unlocked", [])
    if "mago_piromante_2" in unlocked and "mago_criomante_2" in unlocked:
        from engine.adapter import get_adapter
        state = getattr(get_adapter(), "state", None)
        if state and state.combat_state:
            for enemy in [e for e in state.combat_state.enemies if e.is_alive()]:
                enemy.status_effects[StatusEffect.QUEIMADO] = 2
                add_log(f"🔥 Tempestade de Gelo: {enemy.name} foi atingido por estilhaços flamejantes e começou a queimar!")
    play_sound_effect("ARCANE SHIELD", Colors.CYAN)

def trovao_celestial(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="slash", duration=500, sfx_id="magic_cast")
    raw_damage = int(player.inteligencia * 3.0)
    
    # Clima Modifiers
    from engine.adapter import get_adapter
    state = getattr(get_adapter(), "state", None)
    weather = state.get_flag("weather", "Ensolarado") if state else "Ensolarado"
    if weather == "Chuvoso":
        raw_damage = int(raw_damage * 1.2)
        add_log("🌧️ A chuva conduz a eletricidade!")
    elif weather == "Tempestade":
        raw_damage = int(raw_damage * 1.4)
        add_log("⛈️ A tempestade amplifica o relâmpago celestial!")

    raw_damage = _scale_offense(raw_damage)
        
    damage_dealt = max(1, raw_damage)
    target.hp = max(0, target.hp - damage_dealt)
    add_log(f"Relâmpago atravessa as defesas! Causou {damage_dealt} de dano em {target.name}.")
    play_sound_effect("THUNDERSTRIKE", Colors.BRIGHT_CYAN)

def ataque_furtivo(player, target, add_log, turn):
    if check_nevoeiro_miss(player, target, add_log): return
    trigger_combat_effect(player, target, "projectile", style="slash", duration=500, sfx_id="magic_cast")
    mult = 2.5 if turn == 1 else 1.6
    if "ladino_assassino_2" in getattr(player, "talents_unlocked", []):
        mult += 0.5
        add_log("🗡️ Passo Furtivo aumentou a precisão e letalidade do golpe!")
    raw_damage = _scale_offense(int(player.agilidade * mult))
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    if turn == 1:
        add_log("Aproveitou o elemento surpresa!")
    play_sound_effect("SNEAK BLADE", Colors.BRIGHT_BLACK)

def passo_sombras(player, target, add_log, turn):
    player.status_effects[StatusEffect.ESQUIVA] = 3
    add_log(f"{player.name} se move como um vulto! Evasão grandemente aumentada.")
    unlocked = getattr(player, "talents_unlocked", [])
    if "ladino_assassino_2" in unlocked and "ladino_trapaceiro_2" in unlocked:
        player.status_effects[StatusEffect.FURIA] = 2
        add_log(f"👥 Dança das Sombras: {player.name} entrou em Fúria ao se mover pelas sombras (+ataque, -defesa) por 2 turnos!")
    play_sound_effect("SHADOW WALK", Colors.MAGENTA)

def lamina_venenosa(player, target, add_log, turn):
    if check_nevoeiro_miss(player, target, add_log): return
    trigger_combat_effect(player, target, "projectile", style="slash", duration=500, sfx_id="magic_cast")
    raw_damage = int(player.agilidade * 1.8)
    if "ladino_trapaceiro_2" in getattr(player, "talents_unlocked", []):
        raw_damage = int(raw_damage * 1.30)
        add_log("🧪 Veneno Mortal potencializou a lâmina!")
    raw_damage = _scale_offense(raw_damage)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    target.status_effects[StatusEffect.ENVENENADO] = 3
    add_log(f"{target.name} está Envenenado!")
    play_sound_effect("VENOM CUT", Colors.GREEN)

def luz_sagrada(player, target, add_log, turn):
    trigger_combat_effect(player, player, "heal_glow", duration=1200, sfx_id="heal_chime")
    heal_val = int(player.inteligencia * 2.2)
    if "clerigo_santo_2" in getattr(player, "talents_unlocked", []):
        heal_val = int(heal_val * 1.25)
        add_log("✨ Prece de Cura potencializou a cura da Luz Sagrada!")
    heal_val = _scale_heal(heal_val, "Luz Sagrada")
    healed = player.heal(heal_val)
    try:
        from engine.vesper_intel import record_tactic
        from engine.adapter import get_adapter
        st = getattr(get_adapter(), "state", None)
        if st:
            record_tactic(st, "holy")
    except Exception:
        pass
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
    unlocked = getattr(player, "talents_unlocked", [])
    if "clerigo_santo_2" in unlocked and "clerigo_inquisidor_2" in unlocked:
        player.status_effects[StatusEffect.FURIA] = 1
        add_log(f"⚔️ Cruzado: {player.name} recebeu Fúria celestial (+ataque, -defesa) por 1 turno!")
    play_sound_effect("HEAL PULSE", Colors.BRIGHT_GREEN)

def punicao_divina(player, target, add_log, turn):
    trigger_combat_effect(player, target, "projectile", style="holy_bolt", duration=700, sfx_id="magic_cast")
    raw_damage = int(player.inteligencia * 1.5)
    if "clerigo_inquisidor_2" in getattr(player, "talents_unlocked", []):
        raw_damage = int(raw_damage * 1.30)
        add_log("⚡ Julgamento Celestial fortaleceu a punição divina!")
    raw_damage = _scale_offense(raw_damage)
    res = target.take_damage(raw_damage)
    damage_dealt = res["damage_taken"]
    add_log(f"Causou {damage_dealt} de dano em {target.name}.")
    heal_val = _scale_heal(damage_dealt // 2, "Punição Divina")
    healed = player.heal(heal_val)
    add_log(f"Restaurou {healed} HP através do elo de vida.")
    play_sound_effect("HOLY STRIKE", Colors.YELLOW)

def bencao_protetora(player, target, add_log, turn):
    trigger_combat_effect(player, player, "heal_glow", duration=1200, sfx_id="heal_chime")
    heal_val = 40
    if "clerigo_santo_2" in getattr(player, "talents_unlocked", []):
        heal_val = int(heal_val * 1.25)
        add_log("✨ Prece de Cura potencializou a Bênção da Proteção!")
    heal_val = _scale_heal(heal_val, "Bênção Protetora")
    healed = player.heal(heal_val)
    player.status_effects[StatusEffect.PROTEGIDO] = 2
    add_log(f"Curou {healed} HP e recebeu a Bênção da Proteção.")
    unlocked = getattr(player, "talents_unlocked", [])
    if "clerigo_santo_2" in unlocked and "clerigo_inquisidor_2" in unlocked:
        player.status_effects[StatusEffect.FURIA] = 1
        add_log(f"⚔️ Cruzado: {player.name} recebeu Fúria celestial (+ataque, -defesa) por 1 turno!")
    play_sound_effect("DIVINE SHIELD", Colors.YELLOW)


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
    Skill("Bênção Protetora", 18, "Cura 40 de HP e concede proteção contra danos por 2 turnos.", 6, False, bencao_protetora)
]

def get_class_skills(char_class: CharacterClass, level: int) -> list:
    class_skill_names = {
        CharacterClass.GUERREIRO: ["Golpe Poderoso", "Muralha de Ferro", "Golpe Devastador"],
        CharacterClass.MAGO: ["Bola de Fogo", "Escudo Arcano", "Trovão Celestial"],
        CharacterClass.LADINO: ["Ataque Furtivo", "Passo de Sombras", "Lâmina Venenosa"],
        CharacterClass.CLERIGO: ["Luz Sagrada", "Punição Divina", "Bênção Protetora"],

    }
    names = class_skill_names.get(char_class, [])
    skills = [s for s in ALL_SKILLS if s.name in names and s.level <= level]
    return skills
