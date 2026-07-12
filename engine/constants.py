import enum

# ANSI Escape Codes for Terminal Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

class CharacterClass(enum.Enum):
    GUERREIRO = "Guerreiro"
    MAGO = "Mago"
    LADINO = "Ladino"
    CLERIGO = "Clérigo"
    ARQUEIRO = "Arqueiro"

class Rarity(enum.Enum):
    COMUM = ("Comum", Colors.WHITE)
    RARO = ("Raro", Colors.CYAN)
    EPICO = ("Épico", Colors.MAGENTA)
    LENDARIO = ("Lendário", Colors.BRIGHT_YELLOW)
    
    @property
    def name_str(self):
        return self.value[0]
        
    @property
    def color(self):
        return self.value[1]

class ItemType(enum.Enum):
    ARMA = "Arma"
    ARMADURA = "Armadura"
    CONSUMIVEL = "Consumível"
    QUEST = "Item de Missão"

class AIType(enum.Enum):
    AGGRESSIVE = "Agressivo"
    DEFENSIVE = "Defensivo"
    CASTER = "Conjurador"
    COWARD = "Covarde"
    BOSS_OGRE = "Boss: Ogro"
    BOSS_INQUISITOR = "Boss: Inquisidor"
    BOSS_MALAKAR = "Boss: Malakar"
    BOSS_GRUM = "Boss: Grum"
    BOSS_GOLEM = "Boss: Golem"

class StatusEffect(enum.Enum):
    ENVENENADO = ("Envenenado", Colors.GREEN, "Causa dano a cada turno.")
    QUEIMADO = ("Queimado", Colors.RED, "Causa dano e reduz ataque.")
    SANGRAMENTO = ("Sangramento", Colors.BRIGHT_RED, "Dano físico contínuo.")
    ATORDOADO = ("Atordoado", Colors.YELLOW, "Pula o próximo turno.")
    FURIA = ("Fúria", Colors.BRIGHT_MAGENTA, "Aumenta ataque, diminui defesa.")
    ESCUDO_ARCANO = ("Escudo Arcano", Colors.CYAN, "Absorve dano recebido.")
    PROTEGIDO = ("Protegido", Colors.BLUE, "Dano reduzido significativamente.")
    ESQUIVA = ("Esquiva", Colors.BRIGHT_BLACK, "Aumenta chance de evasão em 35%.")
    AFOGAMENTO = ("Afogamento", Colors.BLUE, "Dano de Vazio contínuo e impede uso de Habilidades.")

    @property
    def name_str(self):
        return self.value[0]

    @property
    def color(self):
        return self.value[1]
        
    @property
    def desc(self):
        return self.value[2]

# Game Balance Configuration
GAME_CONFIG = {
    "BASE_XP_LEVEL": 100,
    "XP_MULTIPLIER": 1.5,
    "MAX_LEVEL": 20,
    "DEFAULT_MAX_HP": 100,
    "DEFAULT_MAX_MP": 50,
}
