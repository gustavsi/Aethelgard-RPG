import time
import random
from enum import Enum
from typing import List, Dict, Any, Union, Callable
from engine.constants import StatusEffect, CharacterClass, AIType
from engine.enemy import Enemy, spawn_enemy
from engine.items import get_random_loot, Consumable
from engine.dto import NarrativeText
from engine.state import GameState

class CombatPhase(Enum):
    INIT = "INIT"
    TURN_START = "TURN_START"
    WAITING_PLAYER_ACTION = "WAITING_PLAYER_ACTION"
    WAITING_ALL_PLAYERS = "WAITING_ALL_PLAYERS"
    PLAYER_EXECUTE = "PLAYER_EXECUTE"
    PARTY_EXECUTE = "PARTY_EXECUTE"
    ENEMY_TURN = "ENEMY_TURN"
    COMPANION_TURN = "COMPANION_TURN"
    TURN_END = "TURN_END"
    VICTORY = "VICTORY"
    DEFEAT = "DEFEAT"
    FLED = "FLED"

class Command:
    def __init__(self, action: str, target: Any = None, value: Any = None):
        self.action = action
        self.target = target
        self.value = value

class CombatSystem:
    def __init__(self, game_state_or_player, enemies: List[Enemy], can_flee: bool = True, turn_hook: Callable = None, adapter=None):
        from engine.player import Player
        from engine.state import GameState
        from engine.adapter import UIAdapter
        if isinstance(game_state_or_player, Player):
            self.state = GameState(game_state_or_player, adapter=adapter)
        else:
            self.state = game_state_or_player
            if adapter and hasattr(self.state, 'adapter'):
                self.state.adapter = adapter
            
        self.player = self.state.player
        self.enemies = enemies
        self.can_flee = can_flee
        self.turn_hook = turn_hook
        self.adapter = adapter or getattr(self.state, 'adapter', None) or UIAdapter.get_instance()
        self.combat_logs: List[str] = ["Início do combate!"]
        self.turn = 1
        self.phase = CombatPhase.INIT
        self.rewards = {"xp": 0, "gold": 0, "loot": []}
        self.rewards_distributed = False
        
        self.pending_actions: dict = {}
        self.client_menu_stages: dict = {}
        
        # Scaling de inimigos por tamanho da party
        party_size = len(getattr(self.state, 'party', [self.player]))
        scaling = 1.0 + (party_size - 1) * 0.6  # +60% HP por jogador adicional
        for i, enemy in enumerate(self.enemies):
            enemy.idx = i
            enemy.max_hp = int(enemy.max_hp * scaling)
            enemy.hp = enemy.max_hp

        # Cache downed players at start
        self._downed_players_cache = {getattr(p, 'client_id', 'leader') for p in getattr(self.state, 'party', [self.player]) if p.hp <= 0}

        # Play boss_roar on boss combat entrance
        is_boss_fight = False
        boss_names = ["ogro", "inquisidor", "paladino", "guardião", "grum", "golem", "malakar"]
        for enemy in self.enemies:
            name_lower = enemy.name.lower()
            if any(bn in name_lower for bn in boss_names) or enemy.ai_type in [AIType.BOSS_OGRE, AIType.BOSS_INQUISITOR, AIType.BOSS_MALAKAR, AIType.BOSS_GRUM, AIType.BOSS_GOLEM]:
                is_boss_fight = True
                break
        
        if is_boss_fight:
            from engine.dto import SoundEffect
            self.adapter.emit(SoundEffect("boss_roar"))

        if hasattr(self.state, 'world') and self.state.world:
            self.state.world.active_combat = self

        self.sync_state()

    def sync_state(self):
        """Updates the GameState's combat_state field."""
        if hasattr(self.state, 'world') and self.state.world and self.state.world.active_combat is None:
            with self.state.lock:
                self.state.combat_state = None
            return
            
        with self.state.lock:
            self.state.combat_state = {
                "phase": self.phase.value,
                "turn": self.turn,
                "logs": list(self.combat_logs),
                "player": {
                    "name": self.player.name,
                    "hp": self.player.hp,
                    "max_hp": self.player.max_hp,
                    "mp": self.player.mp,
                    "max_mp": self.player.max_mp,
                    "attack": self.player.get_attack_power(),
                    "defense": self.player.get_defense_power(),
                    "status": [e.name_str for e in self.player.status_effects.keys()]
                },
                "enemies": [
                    {
                        "idx": i,
                        "name": e.name,
                        "hp": e.hp,
                        "max_hp": e.max_hp,
                        "mp": getattr(e, 'mp', 0),
                        "max_mp": getattr(e, 'max_mp', 0),
                        "alive": e.is_alive(),
                        "defending": e.defending,
                        "status": [k.name_str for k in e.status_effects.keys()]
                    }
                    for i, e in enumerate(self.enemies)
                ],
                "submitted_actions": list(self.pending_actions.keys())
            }

    def add_log(self, text: str):
        from engine.utils import strip_ansi
        self.combat_logs.append(strip_ansi(text))
        while len(self.combat_logs) > 12:
            self.combat_logs.pop(0)

    def is_finished(self) -> bool:
        return self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT, CombatPhase.FLED]
    def advance_state(self):
        """Advances the state machine until it requires player input or ends."""
        self.check_victory_defeat_or_transformation()
        while not self.is_finished() and self.phase not in [CombatPhase.WAITING_PLAYER_ACTION, CombatPhase.WAITING_ALL_PLAYERS]:
            if self.phase == CombatPhase.INIT:
                self.phase = CombatPhase.TURN_START
                
            elif self.phase == CombatPhase.TURN_START:
                self.pending_actions.clear()
                self.client_menu_stages.clear()
                self.sync_state()
                
                if self.turn_hook:
                    res = self.turn_hook(self)
                    if res == "END_COMBAT":
                        self.pending_actions.clear()
                        self.client_menu_stages.clear()
                        self.phase = CombatPhase.VICTORY
                        if hasattr(self.state, 'world') and self.state.world:
                            self.state.world.active_combat = None
                        with self.state.lock:
                            self.state.combat_state = None
                        if self.adapter:
                            self.adapter.on_state_change(self.state)
                        continue
                        
                if StatusEffect.ATORDOADO in self.player.status_effects:
                    self.add_log(f"{self.player.name} está atordoado e pulou o turno!")
                    self.player.status_effects[StatusEffect.ATORDOADO] -= 1
                    if self.player.status_effects[StatusEffect.ATORDOADO] <= 0:
                        del self.player.status_effects[StatusEffect.ATORDOADO]
                    self.phase = CombatPhase.ENEMY_TURN
                else:
                    self.process_target_status_effects(self.player, self.player.name, True)
                    self.check_victory_defeat_or_transformation()
                    if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT]:
                        continue
                    else:
                        self.phase = CombatPhase.WAITING_ALL_PLAYERS
                        
            elif self.phase == CombatPhase.PLAYER_EXECUTE:
                self.check_victory_defeat_or_transformation()
                if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT]:
                    continue
                else:
                    self.phase = CombatPhase.ENEMY_TURN
 
            elif self.phase == CombatPhase.PARTY_EXECUTE:
                self.resolve_party_turn()
                self.check_victory_defeat_or_transformation()
                if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT, CombatPhase.FLED] or self.is_finished():
                    continue
                else:
                    self.phase = CombatPhase.ENEMY_TURN
                    
            elif self.phase == CombatPhase.ENEMY_TURN:
                self.enemy_turn()
                self.check_victory_defeat_or_transformation()
                if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT]:
                    continue
                else:
                    self.phase = CombatPhase.COMPANION_TURN
                    
            elif self.phase == CombatPhase.COMPANION_TURN:
                if self.player.companion:
                    self.companion_action()
                self.check_victory_defeat_or_transformation()
                if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT]:
                    continue
                else:
                    self.phase = CombatPhase.TURN_END
                
            elif self.phase == CombatPhase.TURN_END:
                self.turn += 1
                self.phase = CombatPhase.TURN_START
            
            self.check_victory_defeat_or_transformation()
                
        if self.is_finished() and self.phase == CombatPhase.VICTORY and self.rewards["xp"] == 0:
            self.distribute_rewards()
            
        self.sync_state()

    def process_command(self, cmd: Command):
        if self.phase != CombatPhase.WAITING_PLAYER_ACTION:
            return
            
        if cmd.action == "ATTACK":
            target = self.enemies[cmd.target] if cmd.target is not None else self.get_first_alive_enemy()
            self.player_attack_enemy(target)
            self.phase = CombatPhase.PLAYER_EXECUTE
            
        elif cmd.action == "DEFEND":
            self.player.status_effects[StatusEffect.PROTEGIDO] = 1
            self.add_log(f"{self.player.name} assume uma postura de defesa!")
            self.phase = CombatPhase.PLAYER_EXECUTE
            
        elif cmd.action == "FLEE":
            if not self.can_flee:
                self.add_log("Não pode fugir!")
                self.phase = CombatPhase.WAITING_PLAYER_ACTION
            else:
                flee_chance = 0.4 + (self.player.agilidade * 0.02)
                if random.random() < flee_chance:
                    self.add_log(f"{self.player.name} conseguiu escapar com sucesso!")
                    self.phase = CombatPhase.FLED
                else:
                    self.add_log(f"{self.player.name} falhou em fugir do combate!")
                    self.phase = CombatPhase.PLAYER_EXECUTE
                    
        elif cmd.action == "SKILL":
            skill = cmd.value
            target = self.enemies[cmd.target] if cmd.target is not None else self.get_first_alive_enemy()
            if self.player.mp >= skill.mp:
                self.player.mp -= skill.mp
                self.add_log(f"Usou habilidade: {skill.name}")
                skill.execute(self.player, target, self.add_log, self.turn)
                self.phase = CombatPhase.PLAYER_EXECUTE
            else:
                self.add_log("Mana insuficiente!")
                self.phase = CombatPhase.WAITING_PLAYER_ACTION
                self.sync_state()
                
        elif cmd.action == "ITEM":
            item = cmd.value
            self.player.inventory.remove(item)
            use_log = item.use(self.player)
            self.add_log(f"Usou {item.name}: {use_log}")
            self.phase = CombatPhase.PLAYER_EXECUTE
            
        self.advance_state()

    def submit_player_action(self, client_id: str, command: Command):
        """Armazena a ação de um jogador e avança para PARTY_EXECUTE se todos vivos declararam."""
        self.pending_actions[client_id] = command
        self.sync_state()
        
        # Broadcast imediato para todos verem quem já enviou
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "STATE_UPDATE", 
                "state": self.state.to_dict()
            })
        
        party = getattr(self.state, 'party', [self.player])
        active_party_members = [p for p in party if p.hp > 0]
        active_ids = [getattr(p, 'client_id', None) or 'leader' for p in active_party_members]
        
        if all(cid in self.pending_actions for cid in active_ids):
            self.phase = CombatPhase.PARTY_EXECUTE
            if self.adapter and hasattr(self.adapter, 'input_queue'):
                self.adapter.input_queue.put("ALL_DONE")

    def resolve_party_turn(self):
        party = getattr(self.state, 'party', [self.player])
        active_players = [p for p in party if p.hp > 0 and (getattr(p, 'client_id', None) or 'leader') in self.pending_actions]
        
        leader = self.player
        ordered_players = sorted(
            active_players,
            key=lambda p: (-p.agilidade, 0 if p == leader else 1)
        )
        
        for p in ordered_players:
            if p.hp <= 0:
                continue
                
            cmd = self.pending_actions.get(getattr(p, 'client_id', None) or 'leader')
            if not cmd:
                continue
                
            self.execute_player_command(p, cmd)
            self.check_victory_defeat_or_transformation()
            if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT]:
                break

    def execute_player_command(self, p, cmd: Command):
        if cmd.action == "ATTACK":
            target = self.enemies[cmd.target] if cmd.target is not None else self.get_first_alive_enemy()
            self.execute_player_attack(p, target)
            
        elif cmd.action == "DEFEND":
            p.status_effects[StatusEffect.PROTEGIDO] = 1
            self.add_log(f"{p.name} assume uma postura de defesa!")
            
        elif cmd.action == "FLEE":
            if not self.can_flee:
                self.add_log(f"{p.name} tentou fugir, mas não pode fugir!")
            else:
                flee_chance = 0.4 + (p.agilidade * 0.02)
                if random.random() < flee_chance:
                    self.add_log(f"{p.name} conseguiu escapar com sucesso! A party foge!")
                    self.phase = CombatPhase.FLED
                else:
                    self.add_log(f"{p.name} falhou em fugir do combate!")
                    
        elif cmd.action == "SKILL":
            skill = cmd.value
            target = self.enemies[cmd.target] if cmd.target is not None else self.get_first_alive_enemy()
            if p.mp >= skill.mp:
                p.mp -= skill.mp
                self.add_log(f"{p.name} usou habilidade: {skill.name}")
                skill.execute(p, target, self.add_log, self.turn)
            else:
                self.add_log(f"{p.name} tentou usar {skill.name}, mas tem mana insuficiente!")
                
        elif cmd.action == "ITEM":
            item = cmd.value
            if item in p.inventory:
                p.inventory.remove(item)
                use_log = item.use(p)
                self.add_log(f"{p.name} usou {item.name}: {use_log}")
            else:
                self.add_log(f"{p.name} tentou usar {item.name}, mas não possui mais o item!")

    def execute_player_attack(self, p, target: Enemy):
        base_atk = p.get_attack_power()
        raw_damage = random.randint(int(base_atk * 0.8), int(base_atk * 1.2))
        crit_chance = 0.05 + (p.agilidade * 0.015 if p.char_class == CharacterClass.LADINO else 0.005)
        is_crit = random.random() < crit_chance
        if is_crit:
            raw_damage = int(raw_damage * 1.8)
            
        res = target.take_damage(raw_damage)
        damage_dealt = res["damage_taken"]
        desc = f"Causou {damage_dealt} de dano em {target.name}."
        if res.get("mitigated"):
            desc += " (Mitigado por defesa ativa!)"
        
        crit_str = f" [CRÍTICO]" if is_crit else ""
        self.add_log(f"{p.name} atacou {target.name}!{crit_str}")
        self.add_log(desc)


    def get_first_alive_enemy(self) -> Enemy:
        for e in self.enemies:
            if e.is_alive():
                return e
        return self.enemies[0]

    def process_target_status_effects(self, target, name: str, is_player: bool):
        effects_to_remove = []
        if StatusEffect.ENVENENADO in target.status_effects:
            dmg = 3 + (self.turn // 2)
            target.hp = max(0, target.hp - dmg)
            self.add_log(f"{name} sofre {dmg} de dano por Veneno.")
            target.status_effects[StatusEffect.ENVENENADO] -= 1
            if target.status_effects[StatusEffect.ENVENENADO] <= 0:
                effects_to_remove.append(StatusEffect.ENVENENADO)
                
        if StatusEffect.SANGRAMENTO in target.status_effects:
            dmg = 5
            target.hp = max(0, target.hp - dmg)
            self.add_log(f"{name} sangra por {dmg} de dano.")
            target.status_effects[StatusEffect.SANGRAMENTO] -= 1
            if target.status_effects[StatusEffect.SANGRAMENTO] <= 0:
                effects_to_remove.append(StatusEffect.SANGRAMENTO)
                
        if StatusEffect.QUEIMADO in target.status_effects:
            dmg = int(target.max_hp * 0.05)
            target.hp = max(0, target.hp - dmg)
            self.add_log(f"{name} queima, perdendo {dmg} HP.")
            target.status_effects[StatusEffect.QUEIMADO] -= 1
            if target.status_effects[StatusEffect.QUEIMADO] <= 0:
                effects_to_remove.append(StatusEffect.QUEIMADO)
                
        if StatusEffect.PROTEGIDO in target.status_effects:
            target.status_effects[StatusEffect.PROTEGIDO] -= 1
            if target.status_effects[StatusEffect.PROTEGIDO] <= 0:
                effects_to_remove.append(StatusEffect.PROTEGIDO)
                
        if StatusEffect.ESQUIVA in target.status_effects:
            target.status_effects[StatusEffect.ESQUIVA] -= 1
            if target.status_effects[StatusEffect.ESQUIVA] <= 0:
                effects_to_remove.append(StatusEffect.ESQUIVA)
                
        if StatusEffect.ATORDOADO in target.status_effects:
            target.status_effects[StatusEffect.ATORDOADO] -= 1
            if target.status_effects[StatusEffect.ATORDOADO] <= 0:
                effects_to_remove.append(StatusEffect.ATORDOADO)
                
        if StatusEffect.AFOGAMENTO in target.status_effects:
            dmg = 10
            target.hp = max(0, target.hp - dmg)
            self.add_log(f"{name} sofre {dmg} de dano por Afogamento do Vazio.")
            target.status_effects[StatusEffect.AFOGAMENTO] -= 1
            if target.status_effects[StatusEffect.AFOGAMENTO] <= 0:
                effects_to_remove.append(StatusEffect.AFOGAMENTO)
                
        for effect in effects_to_remove:
            del target.status_effects[effect]
            self.add_log(f"Efeito {effect.name_str} em {name} expirou.")

    def player_attack_enemy(self, target: Enemy):
        from engine.dto import VisualEffect
        target_id = f"enemy_{target.idx}"
        self.adapter.emit(VisualEffect("shake", target_id=target_id, duration=400))
        base_atk = self.player.get_attack_power()
        raw_damage = random.randint(int(base_atk * 0.8), int(base_atk * 1.2))
        crit_chance = 0.05 + (self.player.agilidade * 0.015 if self.player.char_class == CharacterClass.LADINO else 0.005)
        is_crit = random.random() < crit_chance
        if is_crit:
            raw_damage = int(raw_damage * 1.8)
            
        res = target.take_damage(raw_damage)
        damage_dealt = res["damage_taken"]
        desc = f"Causou {damage_dealt} de dano em {target.name}."
        if res.get("mitigated"):
            desc += " (Mitigado por defesa ativa!)"
        
        crit_str = f" [CRÍTICO]" if is_crit else ""
        self.add_log(f"Você atacou {target.name}!{crit_str}")
        self.add_log(desc)

    def check_boss_transformations(self):
        for enemy in self.enemies:
            if enemy.hp <= 0 and enemy.ai_type in [AIType.BOSS_INQUISITOR, AIType.BOSS_MALAKAR] and enemy.phase < enemy.max_phases:
                from engine.dto import SoundEffect
                self.adapter.emit(SoundEffect("boss_phase_change"))
                self.adapter.emit(SoundEffect("boss_roar"))
                action_type, val, logs = enemy.select_action(self.player, self.enemies)
                for log in logs:
                    self.add_log(log)

    def check_is_down_changes(self):
        party = getattr(self.state, 'party', [self.player])
        for p in party:
            p_id = getattr(p, 'client_id', 'leader')
            was_down = p_id in getattr(self, '_downed_players_cache', set())
            is_currently_down = p.hp <= 0
            if is_currently_down and not was_down:
                self._downed_players_cache.add(p_id)
                from engine.dto import SoundEffect
                self.adapter.emit(SoundEffect("party_member_down"))
            elif not is_currently_down and was_down:
                self._downed_players_cache.discard(p_id)
                from engine.dto import SoundEffect
                self.adapter.emit(SoundEffect("revive"))

    def check_victory_defeat_or_transformation(self) -> bool:
        self.check_boss_transformations()
        self.check_is_down_changes()
        
        if not any(e.is_alive() for e in self.enemies):
            self.phase = CombatPhase.VICTORY
            return True
            
        party = getattr(self.state, 'party', [self.player])
        if all(p.hp <= 0 for p in party):
            self.phase = CombatPhase.DEFEAT
            return True
            
        return False

    def select_enemy_target(self, enemy):
        """Seleciona o alvo prioritariamente por menor % HP, com um elemento de aleatoriedade."""
        party = getattr(self.state, 'party', [self.player])
        alive_members = [p for p in party if p.hp > 0]
        if not alive_members:
            return self.player
        # Ordena por % HP (menor primeiro)
        alive_members.sort(key=lambda p: p.hp / p.max_hp)
        # 65% chance de atacar quem tem menor HP, 35% de atacar outro aleatorio
        if random.random() < 0.65:
            return alive_members[0]
        return random.choice(alive_members)

    def enemy_turn(self):
        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            self.process_target_status_effects(enemy, enemy.name, False)
            self.check_victory_defeat_or_transformation()
            if not enemy.is_alive() or self.is_finished():
                if self.is_finished():
                    return
                continue
                
            target_player = self.select_enemy_target(enemy)
            action_type, val, logs = enemy.select_action(target_player, self.enemies)
            for log in logs:
                self.add_log(log)
                
            if action_type in ["ATTACK", "ATTACK_DRAIN"]:
                res = target_player.take_damage(val)
                if res["dodge"]:
                    self.add_log(f"{target_player.name} se esquivou do ataque de {enemy.name}!")
                else:
                    from engine.dto import VisualEffect
                    target_id = getattr(target_player, 'client_id', 'leader')
                    self.adapter.emit(VisualEffect("shake", target_id=target_id, duration=400))
                    self.add_log(f"{enemy.name} causou {res['damage_taken']} de dano em {target_player.name}.")
                    if res["status"]:
                        self.add_log(res["status"])
                    if action_type == "ATTACK_DRAIN":
                        drained = res['damage_taken'] // 2
                        enemy.heal(drained)
                        self.add_log(f"{enemy.name} sugou a essência de {target_player.name} e curou {drained} HP!")
                self.check_victory_defeat_or_transformation()
                if self.is_finished():
                    return
                        
            elif action_type == "HEAL":
                from engine.dto import VisualEffect, SoundEffect
                target_id = f"enemy_{enemy.idx}"
                self.adapter.emit(VisualEffect("heal_glow", target_id=target_id, duration=1200))
                self.adapter.emit(SoundEffect("heal_chime"))
                healed = enemy.heal(val)
                self.add_log(f"{enemy.name} curou {healed} HP.")
                
            elif action_type == "SUMMON":
                new_minion = spawn_enemy("cultista_flamejante")
                if new_minion:
                    self.enemies.append(new_minion)
                    self.add_log(f"Um {new_minion.name} se junta à luta!")
                    
            elif action_type == "FLEE":
                enemy.hp = 0
                enemy.xp_reward = 0
                enemy.gold_reward = 0
                enemy.fled = True
                self.add_log(f"{enemy.name} fugiu covardemente!")
                self.check_victory_defeat_or_transformation()
                if self.is_finished():
                    return

    def companion_action(self):
        alive_enemies = [e for e in self.enemies if e.is_alive()]
        if not alive_enemies:
            return
        self.add_log(f"Turno de {self.player.companion.name}:")
        self.player.companion.act(self.player, self.enemies, self.add_log)

    def distribute_rewards(self):
        if self.rewards_distributed:
            return
        self.rewards_distributed = True
        
        eligible_enemies = [e for e in self.enemies if not getattr(e, "fled", False) and e.hp <= 0]
        
        total_xp = sum(e.xp_reward for e in eligible_enemies)
        total_gold = sum(e.gold_reward for e in eligible_enemies)
        self.rewards["gold"] = total_gold
        self.player.gold += total_gold
        
        xp_logs = self.player.gain_xp(total_xp)
        self.add_log(f"Ouro ganho: {total_gold}g")
        for log in xp_logs:
            self.add_log(log)
            
        self.rewards["xp"] = total_xp
        
        for enemy in eligible_enemies:
            chance = 1.0 if "Ogro" in enemy.name or "Inquisidor" in enemy.name or "Malakar" in enemy.name else 0.45
            if random.random() < chance:
                item = get_random_loot(self.player.level)
                if item:
                    self.rewards["loot"].append(item)
                    self.add_log(f"Loot Encontrado: {item.name}")
                    self.player.inventory.append(item)

    def run(self) -> Union[bool, str]:
        from engine.combat_ui import CombatUI
        ui = CombatUI(self)
        res = ui.run()
        if hasattr(self.state, 'world') and self.state.world:
            self.state.world.active_combat = None
        self.pending_actions.clear()
        self.client_menu_stages.clear()
        with self.state.lock:
            self.state.combat_state = None
        if self.adapter:
            self.adapter.on_state_change(self.state)
        return res
