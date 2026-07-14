import random
from typing import List, Dict, Any, Tuple, Optional
from engine.constants import Colors, StatusEffect, AIType

class Enemy:
    def __init__(self, name: str, hp: int, attack: int, defense: int, xp_reward: int, gold_reward: int, ai_type: AIType = AIType.AGGRESSIVE):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.xp_reward = xp_reward
        self.gold_reward = gold_reward
        self.ai_type = ai_type
        
        self.status_effects: Dict[StatusEffect, int] = {}
        self.defending: bool = False
        
        # Boss specific variables
        self.phase = 1
        self.max_phases = 1
        if ai_type == AIType.BOSS_INQUISITOR:
            self.max_phases = 2
        elif ai_type == AIType.BOSS_MALAKAR:
            self.max_phases = 3
            
        self.transformed = False
        self.fled = False

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, raw_damage: int) -> Dict[str, Any]:
        """Takes damage, applying defense and status effects. Returns dictionary."""
        mitigation = self.defense
        if self.defending:
            mitigation = int(mitigation * 1.5) + 5
            
        damage_taken = max(1, raw_damage - mitigation)
        self.hp = max(0, self.hp - damage_taken)
        
        return {
            "damage_taken": damage_taken,
            "mitigated": self.defending,
            "target_name": self.name
        }

    def heal(self, amount: int) -> int:
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp

    def select_action(self, player, combat_state) -> Tuple[str, int, List[str]]:
        """
        Determines what the enemy will do.
        Returns: (action_type, raw_value, logs)
        action_type can be: "ATTACK", "HEAL", "DEFEND", "SKILL", "SUMMON", "RAGE", "TRANSFORM"
        """
        self.defending = False # Reset defense status at start of action Selection
        logs = []
        
        # Check stunned
        if StatusEffect.ATORDOADO in self.status_effects:
            logs.append(f"{self.name} está atordoado e não pode agir!")
            return "SKIP", 0, logs
            
        # Execute archetype decision trees
        if self.ai_type == AIType.BOSS_OGRE:
            return self._ai_boss_ogre(player, combat_state)
        elif self.ai_type == AIType.BOSS_INQUISITOR:
            return self._ai_boss_inquisitor(player, combat_state)
        elif self.ai_type == AIType.BOSS_MALAKAR:
            return self._ai_boss_malakar(player, combat_state)
        elif self.ai_type == AIType.BOSS_GRUM:
            return self._ai_boss_grum(player, combat_state)
        elif self.ai_type == AIType.BOSS_GOLEM:
            return self._ai_boss_golem(player, combat_state)
        elif self.ai_type == AIType.BOSS_UIVADOR:
            return self._ai_boss_uivador(player, combat_state)
        elif self.ai_type == AIType.DEFENSIVE:
            return self._ai_defensive(player, combat_state)
        elif self.ai_type == AIType.CASTER:
            return self._ai_caster(player, combat_state)
        elif self.ai_type == AIType.COWARD:
            return self._ai_coward(player, combat_state)
        else: # AGGRESSIVE or default
            return self._ai_aggressive(player, combat_state)

    def _ai_aggressive(self, player, combat_state) -> Tuple[str, int, List[str]]:
        # 80% normal attack, 20% heavy attack (does 1.4x attack)
        logs = []
        if random.random() < 0.25:
            dmg = int(self.attack * 1.4)
            logs.append(f"{self.name} realiza um Ataque Pesado!")
            return "ATTACK", dmg, logs
        else:
            logs.append(f"{self.name} avança atacando ferozmente!")
            return "ATTACK", self.attack, logs

    def _ai_defensive(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        hp_percent = self.hp / self.max_hp
        
        # Defend if health is low, otherwise alternate
        if hp_percent < 0.4 and not self.defending and random.random() < 0.6:
            self.defending = True
            logs.append(f"{self.name} entra em postura defensiva total!")
            return "DEFEND", 0, logs
            
        if random.random() < 0.3:
            self.defending = True
            logs.append(f"{self.name} ergue seu escudo para se defender.")
            return "DEFEND", 0, logs
            
        logs.append(f"{self.name} contra-ataca cautelosamente.")
        return "ATTACK", int(self.attack * 0.9), logs

    def _ai_caster(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        # Casts spells: Burn, Poison, or pure energy
        roll = random.random()
        if roll < 0.3:
            logs.append(f"{self.name} conjura uma Esfera de Fogo!")
            player.status_effects[StatusEffect.QUEIMADO] = 3
            return "ATTACK", int(self.attack * 1.2), logs
        elif roll < 0.6:
            logs.append(f"{self.name} lança uma Nuvem Tóxica!")
            player.status_effects[StatusEffect.ENVENENADO] = 3
            return "ATTACK", int(self.attack * 0.8), logs
        else:
            logs.append(f"{self.name} dispara um Projétil de Energia Pura!")
            return "ATTACK", self.attack, logs

    def _ai_coward(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        hp_percent = self.hp / self.max_hp
        
        if hp_percent < 0.15 and random.random() < 0.5:
            # Escapes
            logs.append(f"{self.name} se desespera e tenta fugir do combate!")
            return "FLEE", 0, logs
        elif hp_percent < 0.3:
            # Try to heal
            heal_amt = int(self.max_hp * 0.3)
            logs.append(f"{self.name} toma uma poção suspeita e se encolhe.")
            return "HEAL", heal_amt, logs
            
        logs.append(f"{self.name} ataca tremendo de medo.")
        return "ATTACK", int(self.attack * 0.8), logs

    def _ai_boss_ogre(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        hp_percent = self.hp / self.max_hp
        
        # Ogre Phase/Rage transition
        if hp_percent < 0.4 and StatusEffect.FURIA not in self.status_effects:
            self.status_effects[StatusEffect.FURIA] = 99 # Permanent rage
            self.attack = int(self.attack * 1.5)
            self.defense = max(1, self.defense - 3)
            logs.append(f"\n🔥 RAAARRRRHHH! {self.name} entra em FÚRIA! Seu ataque aumentou e defesa diminuiu!\n")
            
        roll = random.random()
        if StatusEffect.FURIA in self.status_effects:
            if roll < 0.4:
                logs.append(f"{self.name} desfere um Golpe Esmagador de Fúria!")
                return "ATTACK", int(self.attack * 1.6), logs
            else:
                logs.append(f"{self.name} ataca loucamente com os punhos!")
                return "ATTACK", self.attack, logs
        else:
            if roll < 0.3:
                logs.append(f"{self.name} balança seu clava pesada em um arco largo!")
                return "ATTACK", int(self.attack * 1.3), logs
            elif roll < 0.5:
                self.defending = True
                logs.append(f"{self.name} se protege atrás dos braços maciços.")
                return "DEFEND", 0, logs
            else:
                logs.append(f"{self.name} investe de cabeça em sua direção!")
                return "ATTACK", self.attack, logs

    def _ai_boss_inquisitor(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        # Phase 1: Caster & Shields
        if self.phase == 1:
            if self.hp <= 0:
                # Triggers Phase 2 Transformation!
                self.phase = 2
                self.max_hp = 200
                self.hp = 200
                self.attack = 22
                self.defense = 5
                self.name = "Inquisidor Demoníaco (Fase 2)"
                self.transformed = True
                logs.append(f"\n🔥 O Inquisidor solta uma gargalhada macabra enquanto sua carne rasga, revelando um DEMÔNIO DAS SOMBRAS!")
                logs.append(f"Sua vida foi totalmente restaurada e seus poderes aumentaram!\n")
                return "TRANSFORM", 0, logs
                
            roll = random.random()
            if self.hp < 60 and roll < 0.4:
                # Heal
                logs.append(f"{self.name} murmura preces sombrias, curando suas feridas.")
                return "HEAL", 40, logs
            elif roll < 0.7:
                # Shadow Bolt
                logs.append(f"{self.name} dispara uma Seta de Sombra!")
                return "ATTACK", self.attack, logs
            else:
                # Shield self
                logs.append(f"{self.name} ergue uma Barreira de Ossos.")
                self.defending = True
                return "DEFEND", 0, logs
        else:
            # Phase 2: Demon combat
            roll = random.random()
            if roll < 0.4:
                # Life drain
                logs.append(f"{self.name} usa Dreno de Alma! Causa dano e cura a si mesmo.")
                return "ATTACK_DRAIN", int(self.attack * 1.2), logs
            elif roll < 0.7:
                # Bleeding physical slash
                logs.append(f"{self.name} retalha você com Garras Sombrias! Sangramento aplicado.")
                player.status_effects[StatusEffect.SANGRAMENTO] = 3
                return "ATTACK", self.attack, logs
            else:
                # Heavy charge
                logs.append(f"{self.name} canaliza energia de puro caos e explode em uma onda de choque!")
                return "ATTACK", int(self.attack * 1.5), logs

    def _ai_boss_malakar(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        # Lord Malakar (3 Phases)
        if self.phase == 1:
            if self.hp <= 0:
                self.phase = 2
                self.max_hp = 250
                self.hp = 250
                self.attack = 26
                self.defense = 6
                self.name = "Lorde Malakar - Forma Caótica (Fase 2)"
                logs.append(f"\n💥 O Templo treme! Lorde Malakar absorve as chamas do altar!")
                logs.append(f"\"Contemplem o verdadeiro poder do fogo primordial!\"\n")
                return "TRANSFORM", 0, logs
                
            # Phase 1 logic: attacks + shield + summon
            roll = random.random()
            # If no cultists exist, summon one (check in active combat_state.enemies)
            cultists = [e for e in combat_state if e.name == "Cultista Flamejante"]
            if not cultists and roll < 0.35:
                logs.append(f"{self.name} entoa um cântico profano e invoca um Cultista Flamejante!")
                return "SUMMON", 0, logs
            elif roll < 0.7:
                logs.append(f"{self.name} canaliza um raio de fogo concentrado.")
                return "ATTACK", self.attack, logs
            else:
                self.defending = True
                logs.append(f"{self.name} cruza os braços, criando uma muralha de chamas.")
                return "DEFEND", 0, logs
                
        elif self.phase == 2:
            if self.hp <= 0:
                self.phase = 3
                self.max_hp = 300
                self.hp = 300
                self.attack = 35
                self.defense = 2
                self.name = "Lorde Malakar - Essência da Destruição (Fase Final)"
                logs.append(f"\n🌋 OBRIGAÇÃO FINAL! A armadura de Malakar derrete, revelando uma entidade de lava pura!")
                logs.append(f"Ele está instável e extremamente violento!\n")
                return "TRANSFORM", 0, logs
                
            # Phase 2 logic: Burns and high attack
            roll = random.random()
            if roll < 0.4:
                logs.append(f"{self.name} libera uma Explosão de Lava! Causa queimaduras críticas!")
                player.status_effects[StatusEffect.QUEIMADO] = 4
                return "ATTACK", int(self.attack * 1.3), logs
            else:
                logs.append(f"{self.name} chicoteia você com correntes flamejantes!")
                return "ATTACK", self.attack, logs
                
        else:
            # Phase 3 logic: Ultimate boss phase. Very high attack, applies stun or random status
            roll = random.random()
            if roll < 0.3:
                logs.append(f"{self.name} conjura Cometa do Apocalipse! Causa dano esmagador!")
                return "ATTACK", int(self.attack * 1.8), logs
            elif roll < 0.6:
                logs.append(f"{self.name} ataca com Chama do Caos! Chance de Atordoar.")
                if random.random() < 0.4:
                    player.status_effects[StatusEffect.ATORDOADO] = 1
                return "ATTACK", self.attack, logs
            else:
                logs.append(f"{self.name} ataca furiosamente em sequência!")
                return "ATTACK", int(self.attack * 1.1), logs

    def _ai_boss_grum(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        roll = random.random()
        if roll < 0.35:
            from engine.constants import StatusEffect
            logs.append(f"🌊 {self.name} conjura uma Onda de Vazio sobre {player.name}!")
            player.status_effects[StatusEffect.AFOGAMENTO] = 3
            return "ATTACK", int(self.attack * 0.9), logs
        elif roll < 0.65:
            logs.append(f"⚓ {self.name} gira uma âncora enferrujada e desfere um golpe brutal!")
            return "ATTACK", int(self.attack * 1.4), logs
        elif roll < 0.85:
            from engine.constants import StatusEffect
            logs.append(f"🛡️ {self.name} endurece suas cracas marinhas, preparando-se para defender.")
            self.defending = True
            self.status_effects[StatusEffect.PROTEGIDO] = 2
            return "DEFEND", 0, logs
        else:
            logs.append(f"⚔️ {self.name} avança com uma marreta de naufrágio!")
            return "ATTACK", self.attack, logs

    def _ai_boss_golem(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        roll = random.random()
        if roll < 0.35:
            from engine.constants import StatusEffect
            logs.append(f"🌋 {self.name} bate os punhos de pedra e invoca uma Tempestade de Lava!")
            player.status_effects[StatusEffect.QUEIMADO] = 3
            return "ATTACK", int(self.attack * 1.3), logs
        elif roll < 0.65:
            logs.append(f"🔨 {self.name} desfere um soco sísmico esmagador!")
            return "ATTACK", int(self.attack * 1.5), logs
        elif roll < 0.85:
            from engine.constants import StatusEffect
            logs.append(f"🧱 {self.name} se fecha em uma carapaça de rochas rúnicas.")
            self.defending = True
            self.status_effects[StatusEffect.PROTEGIDO] = 2
            return "DEFEND", 0, logs
        else:
            logs.append(f"⚔️ {self.name} avança esmagando o chão de Kragmoor!")
            return "ATTACK", self.attack, logs

    def _ai_boss_uivador(self, player, combat_state) -> Tuple[str, int, List[str]]:
        logs = []
        roll = random.random()
        if roll < 0.35:
            from engine.constants import StatusEffect
            logs.append(f"🔊 {self.name} solta um Uivo do Silêncio ensurdecedor!")
            player.status_effects[StatusEffect.ATORDOADO] = 1
            return "ATTACK", int(self.attack * 1.1), logs
        elif roll < 0.65:
            logs.append(f"❄️ {self.name} expele um Sopro Gélido do Vazio!")
            return "ATTACK", int(self.attack * 1.5), logs
        elif roll < 0.85:
            logs.append(f"💨 {self.name} se camufla sob a névoa fria da montanha.")
            self.defending = True
            return "DEFEND", 0, logs
        else:
            logs.append(f"⚔️ {self.name} avança com garras congeladas!")
            return "ATTACK", self.attack, logs

# Library of enemies
ENEMIES_LIBRARY = {
    # Chapter 1 standard
    "lobo_floresta": lambda: Enemy("Lobo da Floresta", 40, 10, 1, 20, 10, AIType.AGGRESSIVE),
    "salteador": lambda: Enemy("Salteador do Caminho", 55, 12, 2, 30, 25, AIType.DEFENSIVE),
    "morcego_gigante": lambda: Enemy("Morcego Gigante", 35, 9, 0, 18, 5, AIType.COWARD),
    "guardiao_floresta": lambda: Enemy("Guardião da Floresta", 130, 15, 6, 120, 60, AIType.DEFENSIVE),
    
    # Chapter 1 Boss
    "ogro_cabana": lambda: Enemy("Ogro da Cabana", 150, 18, 4, 150, 80, AIType.BOSS_OGRE),
    
    # Chapter 2 standard
    "goblin_caverna": lambda: Enemy("Goblin Saqueador", 65, 14, 2, 45, 15, AIType.COWARD),
    "xama_goblin": lambda: Enemy("Xamã Goblin", 55, 12, 1, 55, 30, AIType.CASTER),
    "verme_rocha": lambda: Enemy("Verme das Rochas", 90, 18, 5, 60, 20, AIType.DEFENSIVE),
    
    # Chapter 2 Boss
    "inquisidor_sombrio": lambda: Enemy("Inquisidor das Sombras", 120, 16, 3, 300, 150, AIType.BOSS_INQUISITOR),
    
    # Chapter 3 standard
    "cultista_flamejante": lambda: Enemy("Cultista Flamejante", 80, 18, 3, 70, 30, AIType.CASTER),
    "golem_pedra": lambda: Enemy("Golem de Pedra Ancestral", 140, 24, 8, 90, 40, AIType.DEFENSIVE),
    "demonio_fogo": lambda: Enemy("Demônio do Fogo", 110, 25, 4, 100, 50, AIType.AGGRESSIVE),
    "paladino_corrompido": lambda: Enemy("Paladino Corrompido", 140, 22, 5, 200, 80, AIType.DEFENSIVE),
    "ent_corrompido": lambda: Enemy("Ent Corrompido", 120, 20, 6, 120, 50, AIType.DEFENSIVE),
    "guardiao_portal": lambda: Enemy("Guardião do Portal", 160, 24, 8, 250, 100, AIType.DEFENSIVE),
    "assassino_malakar": lambda: Enemy("Assassino de Malakar", 90, 20, 3, 90, 40, AIType.AGGRESSIVE),
    
    # Chapter 3 Boss
    "lorde_malakar": lambda: Enemy("Lorde Malakar", 180, 22, 6, 1000, 500, AIType.BOSS_MALAKAR),
    
    # Chapter 7
    "pirata_mare_negra": lambda: Enemy("Pirata da Maré Negra", 95, 18, 3, 60, 25, AIType.AGGRESSIVE),
    "grum_afogado": lambda: Enemy("Contramestre Grum, o Afogado", 200, 26, 6, 400, 200, AIType.BOSS_GRUM),
    
    # Chapter 8
    "golem_kragmoor": lambda: Enemy("Golem de Kragmoor, o Corrompido", 240, 28, 8, 500, 250, AIType.BOSS_GOLEM),
    
    # Chapter 9
    "espectro_gelo": lambda: Enemy("Espectro do Gelo", 90, 15, 3, 70, 30, AIType.AGGRESSIVE),
    "lobo_gelo_quest": lambda: Enemy("Lobo do Gelo Ancestral", 70, 12, 2, 45, 15, AIType.AGGRESSIVE),
    "uivador_vazio": lambda: Enemy("Uivador do Vazio, Fera do Norte", 250, 24, 6, 500, 250, AIType.BOSS_UIVADOR)
}

def spawn_enemy(enemy_id: str) -> Optional[Enemy]:
    if enemy_id in ENEMIES_LIBRARY:
        return ENEMIES_LIBRARY[enemy_id]()
    return None
