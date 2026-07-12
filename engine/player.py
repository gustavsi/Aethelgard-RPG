import random
from typing import List, Dict, Any, Optional
from engine.constants import Colors, CharacterClass, StatusEffect, GAME_CONFIG
from engine.items import Item, Weapon, Armor, Consumable, create_item
from engine.companion import Companion
from engine.skills import get_class_skills
from engine.quest import QuestManager

class InventoryList(list):
    def __init__(self, player, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = player
        self.state = None

    def append(self, item):
        if isinstance(item, Consumable):
            if self.state:
                self.state.shared_inventory.append(item)
                from engine.dto import NarrativeText
                if hasattr(self.state, 'adapter') and self.state.adapter:
                    self.state.adapter.emit(NarrativeText(f"🧪 {item.name} adicionado ao Estoque da Party"))
            else:
                super().append(item)
        else:
            super().append(item)

class Player:
    @property
    def is_down(self) -> bool:
        return self.hp <= 0

    def __init__(self, name: str, char_class: CharacterClass):
        self.name = name
        self.char_class = char_class
        self.level = 1
        self.xp = 0
        self.gold = 50
        
        # Stats based on class
        self.setup_class_stats()
        
        self.hp = self.max_hp
        self.mp = self.max_mp
        
        self.status_effects: Dict[StatusEffect, int] = {} # Status -> remaining turns
        
        # Equipment
        self.weapon: Optional[Weapon] = None
        self.armor: Optional[Armor] = None
        
        # Inventory
        self.inventory: List[Item] = InventoryList(self)
        
        # Game choices memory
        self.choices: Dict[str, Any] = {}
        
        # Companion
        self.companion: Optional[Companion] = None
        
        # Quests
        self.quest_manager = QuestManager()
        
        # Apply starting gear
        self.equip_starting_gear()

    def setup_class_stats(self):
        """Sets up stats based on class choice."""
        if self.char_class == CharacterClass.GUERREIRO:
            self.max_hp = 120
            self.max_mp = 20
            self.forca = 12
            self.inteligencia = 5
            self.agilidade = 6
            self.vitalidade = 12
        elif self.char_class == CharacterClass.MAGO:
            self.max_hp = 80
            self.max_mp = 60
            self.forca = 4
            self.inteligencia = 15
            self.agilidade = 7
            self.vitalidade = 8
        elif self.char_class == CharacterClass.LADINO:
            self.max_hp = 90
            self.max_mp = 30
            self.forca = 7
            self.inteligencia = 6
            self.agilidade = 16
            self.vitalidade = 9
        elif self.char_class == CharacterClass.CLERIGO:
            self.max_hp = 100
            self.max_mp = 40
            self.forca = 8
            self.inteligencia = 10
            self.agilidade = 6
            self.vitalidade = 10
        elif self.char_class == CharacterClass.ARQUEIRO:
            self.max_hp = 85
            self.max_mp = 25
            self.forca = 8
            self.inteligencia = 5
            self.agilidade = 12
            self.vitalidade = 8

    def equip_starting_gear(self):
        """Gives starter equipment and potions."""
        if self.char_class == CharacterClass.GUERREIRO:
            self.weapon = create_item("espada_enferrujada")
            self.armor = create_item("trapos_velhos")
        elif self.char_class == CharacterClass.MAGO:
            self.weapon = create_item("cajado_iniciante")
            self.armor = create_item("trapos_velhos")
        elif self.char_class == CharacterClass.LADINO:
            self.weapon = create_item("adaga_velha")
            self.armor = create_item("trapos_velhos")
        elif self.char_class == CharacterClass.CLERIGO:
            self.weapon = create_item("martelo_treino")
            self.armor = create_item("trapos_velhos")
        elif self.char_class == CharacterClass.ARQUEIRO:
            self.weapon = create_item("arco_simples")
            self.armor = create_item("trapos_velhos")
            
        self.inventory.append(create_item("pocao_vida_p"))
        self.inventory.append(create_item("pocao_mana_p"))

    def get_attack_power(self) -> int:
        weapon_atk = self.weapon.attack_power if self.weapon else 0
        if self.char_class == CharacterClass.MAGO:
            stat_bonus = self.inteligencia
        elif self.char_class in (CharacterClass.LADINO, CharacterClass.ARQUEIRO):
            stat_bonus = self.agilidade
        else:
            stat_bonus = self.forca
        return weapon_atk + (stat_bonus // 2)

    def get_defense_power(self) -> int:
        armor_def = self.armor.defense_power if self.armor else 0
        stat_bonus = self.vitalidade // 3
        return armor_def + stat_bonus

    def gain_xp(self, amount: int) -> List[str]:
        """Adds XP and handles leveling up. Returns logs of changes."""
        logs = [f"Ganhou {amount} XP!"]
        self.xp += amount
        
        xp_needed = self.get_xp_needed()
        while self.xp >= xp_needed and self.level < GAME_CONFIG["MAX_LEVEL"]:
            self.xp -= xp_needed
            self.level += 1
            
            # Boost stats on level up
            hp_gain = 10 + (self.vitalidade // 2)
            mp_gain = 5 + (self.inteligencia // 2)
            
            self.max_hp += hp_gain
            self.max_mp += mp_gain
            self.hp = self.max_hp
            self.mp = self.max_mp
            
            # Class specific stat boosts
            if self.char_class == CharacterClass.GUERREIRO:
                self.forca += 2
                self.vitalidade += 2
                self.agilidade += 1
            elif self.char_class == CharacterClass.MAGO:
                self.inteligencia += 3
                self.vitalidade += 1
                self.max_mp += 5
            elif self.char_class == CharacterClass.LADINO:
                self.agilidade += 4
                self.forca += 1
                self.vitalidade += 1
            elif self.char_class == CharacterClass.CLERIGO:
                self.inteligencia += 2
                self.vitalidade += 2
                self.forca += 1
            elif self.char_class == CharacterClass.ARQUEIRO:
                self.agilidade += 3
                self.forca += 1
                self.vitalidade += 1
                
            logs.append(f"\n🎉 NÍVEL AUMENTOU! Você agora está no nível {self.level}! 🎉")
            logs.append(f"Vida Máxima aumentada para {self.max_hp}.")
            logs.append(f"Mana Máxima aumentada para {self.max_mp}.")
            xp_needed = self.get_xp_needed()
            
        return logs

    def get_xp_needed(self) -> int:
        return int(GAME_CONFIG["BASE_XP_LEVEL"] * (self.level ** GAME_CONFIG["XP_MULTIPLIER"]))

    def equip(self, item: Item) -> str:
        """Equips a weapon or armor, placing the old one in inventory."""
        if isinstance(item, Weapon):
            old_weapon = self.weapon
            self.weapon = item
            if old_weapon:
                self.inventory.append(old_weapon)
            return f"Equipou {item.get_colored_name()} como arma."
        elif isinstance(item, Armor):
            old_armor = self.armor
            self.armor = item
            if old_armor:
                self.inventory.append(old_armor)
            return f"Equipou {item.get_colored_name()} como armadura."
        return "Este item não pode ser equipado."

    def heal(self, amount: int) -> int:
        """Heals HP, returns amount actually healed."""
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp

    def take_damage(self, raw_damage: int) -> Dict[str, Any]:
        """Calculates defense mitigation, dodge, block. Returns summary dict."""
        result = {
            "dodge": False,
            "block": False,
            "damage_taken": 0,
            "status": ""
        }
        
        # 1. Check Dodge (based on Agility)
        dodge_chance = min(0.40, self.agilidade * 0.02) # Max 40% dodge
        if StatusEffect.ESQUIVA in self.status_effects:
            dodge_chance += 0.35 # Adds 35% dodge
        if random.random() < dodge_chance:
            result["dodge"] = True
            return result
            
        # 2. Check Block (if Defending or having Protect effect)
        block_reduction = 0
        if StatusEffect.PROTEGIDO in self.status_effects:
            block_reduction += 0.50 # 50% mitigation
            result["block"] = True
            
        # Calculate mitigated damage
        defense = self.get_defense_power()
        # Ensure damage is at least 1 unless dodged
        damage_taken = max(1, int(raw_damage * (1 - block_reduction) - defense))
        
        # Arcane Shield absorbs damage first
        if StatusEffect.ESCUDO_ARCANO in self.status_effects:
            shield_value = self.status_effects[StatusEffect.ESCUDO_ARCANO]
            if shield_value >= damage_taken:
                self.status_effects[StatusEffect.ESCUDO_ARCANO] -= damage_taken
                result["damage_taken"] = 0
                result["status"] = f"Escudo Arcano absorveu todos os {damage_taken} de dano!"
                if self.status_effects[StatusEffect.ESCUDO_ARCANO] == 0:
                    del self.status_effects[StatusEffect.ESCUDO_ARCANO]
                return result
            else:
                damage_taken -= shield_value
                del self.status_effects[StatusEffect.ESCUDO_ARCANO]
                result["status"] = f"Escudo Arcano quebrado! Absorveu {shield_value} de dano."

        self.hp = max(0, self.hp - damage_taken)
        result["damage_taken"] = damage_taken
        return result

    def get_skills(self) -> list:
        """Returns the list of skills unlocked by current level."""
        return get_class_skills(self.char_class, self.level)

    def show_status(self) -> List[str]:
        """Returns strings formatted for status panel."""
        weapon_name = self.weapon.name if self.weapon else "Nenhuma"
        armor_name = self.armor.name if self.armor else "Nenhuma"
        
        status_line = ""
        if self.status_effects:
            eff_strs = [f"{eff.color}{eff.name_str}({t})" for eff, t in self.status_effects.items()]
            status_line = ", ".join(eff_strs)
        else:
            status_line = "Nenhum"
            
        companion_str = f" Companheiro: {self.companion.name}" if self.companion else ""
            
        lines = [
            f"Nome: {self.name} | Classe: {self.char_class.value}",
            f"Nível: {self.level} | Ouro: {self.gold}g{companion_str}",
            f"HP: {self.hp}/{self.max_hp}",
            f"MP: {self.mp}/{self.max_mp}",
            f"XP: {self.xp}/{self.get_xp_needed()}",
            f"Força: {self.forca} | Inteligência: {self.inteligencia}",
            f"Agilidade: {self.agilidade} | Vitalidade: {self.vitalidade}",
            f"Ataque total: {self.get_attack_power()} | Defesa total: {self.get_defense_power()}",
            f"Arma: {weapon_name}",
            f"Armadura: {armor_name}",
            f"Status ativos: {status_line}"
        ]
        active_quests = self.quest_manager.get_active_quests()
        if active_quests:
            lines.append("Missões Ativas:")
            for q in active_quests:
                lines.append(f"  - {q.name}")
                
        return lines
