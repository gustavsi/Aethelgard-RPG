import random
from dataclasses import dataclass
from typing import Dict, Any, Optional
from engine.constants import Colors, Rarity, ItemType

@dataclass
class Item:
    name: str
    item_type: ItemType
    rarity: Rarity
    description: str
    value: int = 0
    id: str = ""
    
    def get_colored_name(self) -> str:
        return f"{self.rarity.color}{self.name}"

@dataclass
class Weapon(Item):
    attack_power: int = 0
    durability: int = 100
    max_durability: int = 100

@dataclass
class Armor(Item):
    defense_power: int = 0
    durability: int = 100
    max_durability: int = 100

@dataclass
class Consumable(Item):
    heal_hp: int = 0
    heal_mp: int = 0
    stat_boost_type: str = "" # e.g. "forca", "vida"
    stat_boost_amount: int = 0
    purge_status: bool = False
    
    def use(self, target) -> str:
        logs = []
        was_down = getattr(target, 'is_down', False)
        
        if self.heal_hp > 0 or self.heal_mp > 0:
            from engine.adapter import get_adapter
            from engine.dto import VisualEffect, SoundEffect
            adapter = get_adapter()
            if adapter:
                target_id = getattr(target, 'client_id', 'leader')
                if hasattr(target, 'ai_type'):
                    target_id = f"enemy_{getattr(target, 'idx', 0)}"
                
                if was_down:
                    adapter.emit(SoundEffect("revive"))
                else:
                    adapter.emit(VisualEffect("heal_glow", target_id=target_id, duration=1200))
                    adapter.emit(SoundEffect("heal_chime"))
                    
        if self.heal_hp > 0:
            if was_down:
                revive_hp = int(target.max_hp * 0.30)
                target.hp = min(target.max_hp, revive_hp)
                logs.append(f"Reanimou {target.name} com {target.hp} HP!")
            else:
                healed = target.heal(self.heal_hp)
                logs.append(f"Curou {healed} HP.")
        if self.heal_mp > 0:
            target.mp = min(target.max_mp, target.mp + self.heal_mp)
            logs.append(f"Restaurou {self.heal_mp} MP.")
        if self.purge_status and target.status_effects:
            from engine.constants import StatusEffect
            negatives = [StatusEffect.ENVENENADO, StatusEffect.QUEIMADO, StatusEffect.SANGRAMENTO, StatusEffect.ATORDOADO]
            removed = []
            for eff in negatives:
                if eff in target.status_effects:
                    del target.status_effects[eff]
                    removed.append(eff.name_str)
            if removed:
                logs.append(f"Efeitos de status negativos purificados: {', '.join(removed)}")
        if self.stat_boost_type:
            # Apply permanent or temporary boost (here let's make it temporary/permanent based on design)
            if self.stat_boost_type == "forca":
                target.forca += self.stat_boost_amount
                logs.append(f"Força aumentada permanentemente em {self.stat_boost_amount}!")
            elif self.stat_boost_type == "inteligencia":
                target.inteligencia += self.stat_boost_amount
                logs.append(f"Inteligência aumentada permanentemente em {self.stat_boost_amount}!")
            elif self.stat_boost_type == "agilidade":
                target.agilidade += self.stat_boost_amount
                logs.append(f"Agilidade aumentada permanentemente em {self.stat_boost_amount}!")
        return " ".join(logs)

# Predefined Items Library
ITEMS_LIBRARY = {
    # Weapons
    "espada_enferrujada": lambda: Weapon("Espada Enferrujada", ItemType.ARMA, Rarity.COMUM, "Uma espada velha e cheia de ferrugem.", 5, attack_power=4),
    "cajado_iniciante": lambda: Weapon("Cajado de Iniciante", ItemType.ARMA, Rarity.COMUM, "Um cajado simples feito de carvalho.", 5, attack_power=3),
    "adaga_velha": lambda: Weapon("Adaga Velha", ItemType.ARMA, Rarity.COMUM, "Uma adaga cega, mas ainda pontiaguda.", 4, attack_power=3),
    "martelo_treino": lambda: Weapon("Martelo de Treino", ItemType.ARMA, Rarity.COMUM, "Pesado, mas de madeira.", 5, attack_power=4),
    "arco_simples": lambda: Weapon("Arco Simples", ItemType.ARMA, Rarity.COMUM, "Arco curto de caça com algumas flechas gastas.", 6, attack_power=4),
    
    "espada_soldado": lambda: Weapon("Espada de Soldado", ItemType.ARMA, Rarity.RARO, "Uma boa espada de aço.", 30, attack_power=10),
    "cajado_fogo": lambda: Weapon("Cajado de Fogo", ItemType.ARMA, Rarity.RARO, "Cajado encantado com brasas eternas.", 35, attack_power=8),
    "adaga_assassina": lambda: Weapon("Adaga do Assassino", ItemType.ARMA, Rarity.RARO, "Equilibrada e muito afiada.", 32, attack_power=9),
    "arco_elfico": lambda: Weapon("Arco Élfico", ItemType.ARMA, Rarity.RARO, "Feito com madeira flexível da floresta profunda.", 38, attack_power=11),
    
    "lamina_runica": lambda: Weapon("Lâmina Rúnica", ItemType.ARMA, Rarity.EPICO, "Uma espada com runas mágicas brilhantes.", 100, attack_power=22),
    "cajado_arquimago": lambda: Weapon("Cajado do Arquimago", ItemType.ARMA, Rarity.EPICO, "Canaliza grandes quantidades de energia arcana.", 110, attack_power=18),
    "machado_executor": lambda: Weapon("Machado do Executor", ItemType.ARMA, Rarity.EPICO, "Muito pesado, mas causa estrago colossal.", 120, attack_power=26),
    
    "excalibur": lambda: Weapon("Excalibur de Aethelgard", ItemType.ARMA, Rarity.LENDARIO, "A lendária espada dos reis. Brilha com luz celestial.", 500, attack_power=45),
    "cajado_cosmico": lambda: Weapon("Cajado do Infinito", ItemType.ARMA, Rarity.LENDARIO, "Diz-se que foi esculpido de uma estrela cadente.", 550, attack_power=40),

    # Kragmoor Legendaries
    "martelo_brokk": lambda: Weapon("Martelo de Brokk", ItemType.ARMA, Rarity.LENDARIO, "Forjado pelo mestre ferreiro de Kragmoor.", 450, attack_power=25),
    "manto_estrelas": lambda: Armor("Manto das Estrelas", ItemType.ARMADURA, Rarity.LENDARIO, "Brilha com constelações antigas. Concede grande proteção.", 400, defense_power=18),
    "lamina_eclipse": lambda: Weapon("Lâmina do Eclipse", ItemType.ARMA, Rarity.LENDARIO, "Uma lâmina escura que absorve a luz ambiente.", 420, attack_power=22),
    "cetro_solar": lambda: Weapon("Cetro Solar", ItemType.ARMA, Rarity.LENDARIO, "Cetro feito de ouro puro de Kragmoor, brilha como o dia.", 420, attack_power=18),

    # Armors
    "trapos_velhos": lambda: Armor("Trapos Velhos", ItemType.ARMADURA, Rarity.COMUM, "Praticamente não oferece proteção.", 2, defense_power=1),
    "armadura_couro": lambda: Armor("Armadura de Couro", ItemType.ARMADURA, Rarity.COMUM, "Leve e flexível.", 15, defense_power=3),
    "cota_malha": lambda: Armor("Cota de Malha", ItemType.ARMADURA, Rarity.RARO, "Boa proteção metálica.", 50, defense_power=8),
    "armadura_placas": lambda: Armor("Armadura de Placas", ItemType.ARMADURA, Rarity.EPICO, "Aço reforçado. Muito pesada.", 150, defense_power=18),
    "armadura_dragao": lambda: Armor("Égide de Dragão", ItemType.ARMADURA, Rarity.LENDARIO, "Forjada com escamas de um dragão ancião.", 600, defense_power=35),

    # Consumables
    "pocao_vida_p": lambda: Consumable("Poção de Vida Menor", ItemType.CONSUMIVEL, Rarity.COMUM, "Cura 25 HP.", 5, heal_hp=25),
    "pocao_vida_m": lambda: Consumable("Poção de Vida", ItemType.CONSUMIVEL, Rarity.RARO, "Cura 60 HP.", 15, heal_hp=60),
    "pocao_vida_g": lambda: Consumable("Poção de Vida Maior", ItemType.CONSUMIVEL, Rarity.EPICO, "Cura 150 HP.", 40, heal_hp=150),
    
    "pocao_mana_p": lambda: Consumable("Poção de Mana Menor", ItemType.CONSUMIVEL, Rarity.COMUM, "Restaura 15 MP.", 5, heal_mp=15),
    "pocao_mana_m": lambda: Consumable("Poção de Mana", ItemType.CONSUMIVEL, Rarity.RARO, "Restaura 40 MP.", 15, heal_mp=40),
    "pocao_mana_g": lambda: Consumable("Poção de Mana Maior", ItemType.CONSUMIVEL, Rarity.EPICO, "Restaura 80 MP.", 40, heal_mp=80),
    
    "elixir_forca": lambda: Consumable("Elixir de Força", ItemType.CONSUMIVEL, Rarity.EPICO, "Aumenta Força permanentemente em 2.", 100, stat_boost_type="forca", stat_boost_amount=2),
    "elixir_inteligencia": lambda: Consumable("Elixir de Inteligência", ItemType.CONSUMIVEL, Rarity.EPICO, "Aumenta Inteligência permanentemente em 2.", 100, stat_boost_type="inteligencia", stat_boost_amount=2),
    
    "erva_cura": lambda: Consumable("Erva de Cura", ItemType.CONSUMIVEL, Rarity.COMUM, "Cura 10 HP e remove efeitos de status negativos.", 8, heal_hp=10, purge_status=True),
    "antidoto": lambda: Consumable("Antídoto", ItemType.CONSUMIVEL, Rarity.RARO, "Remove todos os efeitos de status negativos e cura 20 HP.", 40, heal_hp=20, purge_status=True),
    "lampeao_eter": lambda: Item("Lampião de Éter", ItemType.QUEST, Rarity.RARO, "Anula a penalidade de precisão sob Nevoeiro.", 50),
    "capa_impermeavel": lambda: Item("Capa Impermeável", ItemType.QUEST, Rarity.RARO, "Anula a penalidade de dano de fogo sob Chuva.", 50),
    "minerio_gelo_eterno": lambda: Item("Minério de Gelo Eterno", ItemType.QUEST, Rarity.EPICO, "Minério rústico que pulsa com o frio do norte.", 200),
}

def create_item(item_id: str) -> Optional[Item]:
    """Factory to create items by ID."""
    if item_id in ITEMS_LIBRARY:
        item = ITEMS_LIBRARY[item_id]()
        item.id = item_id
        return item
    return None

def get_random_loot(level: int) -> Item:
    """Generates random loot based on player level."""
    # Determine rarity probabilities
    roll = random.random()
    if roll < 0.02 and level >= 10:
        rarity_pool = [Rarity.LENDARIO]
    elif roll < 0.10 and level >= 5:
        rarity_pool = [Rarity.EPICO]
    elif roll < 0.35:
        rarity_pool = [Rarity.RARO]
    else:
        rarity_pool = [Rarity.COMUM]
        
    chosen_rarity = rarity_pool[0]
    
    # Filter library by chosen rarity and filter out quest items
    candidates = []
    for item_id, builder in ITEMS_LIBRARY.items():
        item = builder()
        if item.rarity == chosen_rarity and item.item_type != ItemType.QUEST:
            candidates.append(item_id)
            
    if not candidates:
        # Fallback to common HP potion
        return create_item("pocao_vida_p")
        
    return create_item(random.choice(candidates))
