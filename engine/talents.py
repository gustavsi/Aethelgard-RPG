from typing import Dict, List, Any
from engine.constants import CharacterClass

TALENTS_LIBRARY: Dict[str, Dict[str, Any]] = {
    # GUERREIRO
    "guerreiro_colosso_1": {
        "id": "guerreiro_colosso_1",
        "name": "Pele de Ferro",
        "desc": "Aumenta a Vida Máxima permanentemente em 20.",
        "class": CharacterClass.GUERREIRO,
        "effect_type": "stat_boost",
        "stats": {"max_hp": 20}
    },
    "guerreiro_colosso_2": {
        "id": "guerreiro_colosso_2",
        "name": "Baluarte",
        "desc": "Reduz passivamente todo dano recebido em combate em 10%.",
        "class": CharacterClass.GUERREIRO,
        "effect_type": "passive"
    },
    "guerreiro_berserker_1": {
        "id": "guerreiro_berserker_1",
        "name": "Fúria Incontrolável",
        "desc": "Aumenta a Força permanentemente em 4.",
        "class": CharacterClass.GUERREIRO,
        "effect_type": "stat_boost",
        "stats": {"forca": 4}
    },
    "guerreiro_berserker_2": {
        "id": "guerreiro_berserker_2",
        "name": "Sangue nos Olhos",
        "desc": "Aumenta a chance de acerto crítico físico em 15%.",
        "class": CharacterClass.GUERREIRO,
        "effect_type": "passive"
    },

    # MAGO
    "mago_piromante_1": {
        "id": "mago_piromante_1",
        "name": "Chamas Intensas",
        "desc": "Aumenta a Inteligência permanentemente em 4.",
        "class": CharacterClass.MAGO,
        "effect_type": "stat_boost",
        "stats": {"inteligencia": 4}
    },
    "mago_piromante_2": {
        "id": "mago_piromante_2",
        "name": "Conflagração",
        "desc": "O feitiço Bola de Fogo causa 25% a mais de dano.",
        "class": CharacterClass.MAGO,
        "effect_type": "passive"
    },
    "mago_criomante_1": {
        "id": "mago_criomante_1",
        "name": "Mente Fria",
        "desc": "Aumenta a Mana Máxima permanentemente em 20.",
        "class": CharacterClass.MAGO,
        "effect_type": "stat_boost",
        "stats": {"max_mp": 20}
    },
    "mago_criomante_2": {
        "id": "mago_criomante_2",
        "name": "Escudo de Gelo",
        "desc": "Aumenta a absorção do Escudo Arcano em +15.",
        "class": CharacterClass.MAGO,
        "effect_type": "passive"
    },

    # LADINO
    "ladino_assassino_1": {
        "id": "ladino_assassino_1",
        "name": "Lâmina Afiada",
        "desc": "Aumenta a Agilidade permanentemente em 4.",
        "class": CharacterClass.LADINO,
        "effect_type": "stat_boost",
        "stats": {"agilidade": 4}
    },
    "ladino_assassino_2": {
        "id": "ladino_assassino_2",
        "name": "Passo Furtivo",
        "desc": "Aumenta o multiplicador de dano crítico do Ataque Furtivo em +0.5x.",
        "class": CharacterClass.LADINO,
        "effect_type": "passive"
    },
    "ladino_trapaceiro_1": {
        "id": "ladino_trapaceiro_1",
        "name": "Reflexos Rápidos",
        "desc": "Aumenta a Esquiva passiva em 10%.",
        "class": CharacterClass.LADINO,
        "effect_type": "passive"
    },
    "ladino_trapaceiro_2": {
        "id": "ladino_trapaceiro_2",
        "name": "Veneno Mortal",
        "desc": "Habilidade Lâmina Venenosa causa 30% a mais de dano físico inicial.",
        "class": CharacterClass.LADINO,
        "effect_type": "passive"
    },

    # CLERIGO
    "clerigo_santo_1": {
        "id": "clerigo_santo_1",
        "name": "Fé Inabalável",
        "desc": "Aumenta Inteligência permanentemente em 3 e Vida em 10.",
        "class": CharacterClass.CLERIGO,
        "effect_type": "stat_boost",
        "stats": {"inteligencia": 3, "max_hp": 10}
    },
    "clerigo_santo_2": {
        "id": "clerigo_santo_2",
        "name": "Prece de Cura",
        "desc": "Todas as suas habilidades de cura curam 25% a mais.",
        "class": CharacterClass.CLERIGO,
        "effect_type": "passive"
    },
    "clerigo_inquisidor_1": {
        "id": "clerigo_inquisidor_1",
        "name": "Zelo de Luz",
        "desc": "Aumenta a Força permanentemente em 4.",
        "class": CharacterClass.CLERIGO,
        "effect_type": "stat_boost",
        "stats": {"forca": 4}
    },
    "clerigo_inquisidor_2": {
        "id": "clerigo_inquisidor_2",
        "name": "Julgamento Celestial",
        "desc": "A habilidade Punição Divina causa 30% a mais de dano.",
        "class": CharacterClass.CLERIGO,
        "effect_type": "passive"
    }
}

def unlock_talent(player, talent_id: str) -> bool:
    """Tenta desbloquear o talento para o jogador. Retorna True se sucesso."""
    if talent_id not in TALENTS_LIBRARY:
        return False
    talent = TALENTS_LIBRARY[talent_id]
    
    # Valida classe
    if talent["class"] != player.char_class:
        return False
        
    # Valida pontos e se já está desbloqueado
    if player.talent_points < 1 or talent_id in player.talents_unlocked:
        return False
        
    # Desbloqueia
    player.talent_points -= 1
    player.talents_unlocked.append(talent_id)
    
    # Aplica modificações permanentes de atributos
    if talent["effect_type"] == "stat_boost" and "stats" in talent:
        for stat_name, amount in talent["stats"].items():
            if hasattr(player, stat_name):
                current_val = getattr(player, stat_name)
                setattr(player, stat_name, current_val + amount)
                
                # Se mudou HP ou MP, ajusta os valores atuais
                if stat_name == "max_hp":
                    player.hp = min(player.max_hp, player.hp + amount)
                elif stat_name == "max_mp":
                    player.mp = min(player.max_mp, player.mp + amount)
                    
    return True
