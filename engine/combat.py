import time
import random
from enum import Enum
from typing import List, Dict, Any, Union, Callable
from engine.constants import StatusEffect, CharacterClass, AIType
from engine.enemy import Enemy, spawn_enemy
from engine.items import get_random_loot, Consumable
from engine.dto import NarrativeText
from engine.state import GameState
from engine.feature_flags import FLAGS
from engine.combat_intent import (
    build_intent_view,
    plan_action_for_enemy,
    roll_interrupt,
    intent_dict_for_enemy,
)
from engine.combat_combos import find_combos, apply_combo_hit
from engine import telemetry

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

        # Phase 2: reset per-combat mercy revive token
        try:
            from engine.party_meta import on_combat_start
            on_combat_start(self.state)
        except Exception:
            pass
        try:
            from engine.party_meta import ensure_meta
            ensure_meta(self.state)["dark_bargain_used_combat"] = False
        except Exception:
            pass
        try:
            from engine.terrain_rules import attach_terrain_to_combat
            attach_terrain_to_combat(self)
        except Exception:
            pass

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
                        "status": [k.name_str for k in e.status_effects.keys()],
                        "intent": intent_dict_for_enemy(e),
                    }
                    for i, e in enumerate(self.enemies)
                ],
                "submitted_actions": list(self.pending_actions.keys()),
                "features": {
                    "intent": FLAGS.combat_intent,
                    "combos": FLAGS.combat_combos,
                },
                "terrain": getattr(self, "terrain", None) and {
                    "id": self.terrain.get("id"),
                    "label": self.terrain.get("label"),
                    "desc": self.terrain.get("desc"),
                },
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
                
                from engine.weather_effects import apply_lightning_hazard
                apply_lightning_hazard(self)
                from engine.arena_rules import apply_arena_hazard
                apply_arena_hazard(self)
                self.check_victory_defeat_or_transformation()
                if self.is_finished():
                    continue
                
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
                        
                # Process status effects for the entire party (not only the leader)
                party = getattr(self.state, 'party', [self.player])
                for p in party:
                    if p.hp > 0:
                        self.process_target_status_effects(p, p.name, True)
                self.check_victory_defeat_or_transformation()
                if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT]:
                    continue

                # Telegraph next enemy actions for the player decision phase
                self.plan_enemy_intents()

                # If every living member is stunned, skip straight to enemies
                living = [p for p in party if p.hp > 0]
                can_act = [p for p in living if StatusEffect.ATORDOADO not in p.status_effects]
                if living and not can_act:
                    for p in living:
                        if StatusEffect.ATORDOADO in p.status_effects:
                            self.add_log(f"{p.name} está atordoado e pulou o turno!")
                    self.phase = CombatPhase.ENEMY_TURN
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
        # Living non-stunned must act; downed may submit DOWNED actions (PRD B4)
        active_party_members = [
            p for p in party
            if (p.hp > 0 and StatusEffect.ATORDOADO not in p.status_effects)
            or (p.hp <= 0 and FLAGS.content_systems)
        ]
        # If content_systems off, ignore downed for wait-gate
        if not FLAGS.content_systems:
            active_party_members = [
                p for p in party
                if p.hp > 0 and StatusEffect.ATORDOADO not in p.status_effects
            ]
        active_ids = [getattr(p, 'client_id', None) or 'leader' for p in active_party_members]
        
        if not active_ids or all(cid in self.pending_actions for cid in active_ids):
            self.phase = CombatPhase.PARTY_EXECUTE
            if self.adapter and hasattr(self.adapter, 'input_queue'):
                self.adapter.input_queue.put("ALL_DONE")

    def plan_enemy_intents(self):
        """Roll AI once per living enemy; store for telegraph + later execution."""
        if not FLAGS.combat_intent:
            for e in self.enemies:
                e.planned_action = None
                e.intent_view = None
            return
        primary = self.player
        party = getattr(self.state, "party", [self.player])
        living = [p for p in party if p.hp > 0]
        if living:
            primary = living[0]
        for e in self.enemies:
            e.intent_interrupted = False
            if not e.is_alive():
                e.planned_action = None
                e.intent_view = build_intent_view("SKIP", e)
                continue
            action_type, val, logs = plan_action_for_enemy(e, primary, self)
            e.planned_action = (action_type, val, logs)
            e.intent_view = build_intent_view(action_type, e, interrupted=False)
        self.sync_state()

    def resolve_party_turn(self):
        party = getattr(self.state, 'party', [self.player])
        active_players = [p for p in party if p.hp > 0 and (getattr(p, 'client_id', None) or 'leader') in self.pending_actions]
        
        leader = self.player
        ordered_players = sorted(
            active_players,
            key=lambda p: (-p.agilidade, 0 if p == leader else 1)
        )

        # Interrupts first (by AGI), so cancelled intents never fire
        for p in ordered_players:
            if p.hp <= 0 or StatusEffect.ATORDOADO in p.status_effects:
                continue
            cmd = self.pending_actions.get(getattr(p, 'client_id', None) or 'leader')
            if cmd and cmd.action == "INTERRUPT":
                self.execute_player_command(p, cmd)
                self.check_victory_defeat_or_transformation()
                if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT]:
                    return

        # Combo detection (bonus applied after individual skills still run)
        combo_hits = []
        if FLAGS.combat_combos and len(active_players) >= 2:
            participants = []
            for p in active_players:
                cmd = self.pending_actions.get(getattr(p, 'client_id', None) or 'leader')
                if cmd and cmd.action != "INTERRUPT":
                    participants.append((p, cmd))
            combo_hits = find_combos(participants)
        
        for p in ordered_players:
            if p.hp <= 0:
                continue
            if StatusEffect.ATORDOADO in p.status_effects:
                self.add_log(f"{p.name} está atordoado e não age neste turno!")
                continue
                
            cmd = self.pending_actions.get(getattr(p, 'client_id', None) or 'leader')
            if not cmd:
                continue
            if cmd.action == "INTERRUPT":
                continue  # already resolved
                
            self.execute_player_command(p, cmd)
            self.check_victory_defeat_or_transformation()
            if self.phase in [CombatPhase.VICTORY, CombatPhase.DEFEAT, CombatPhase.FLED]:
                break

        if combo_hits and self.phase not in [CombatPhase.VICTORY, CombatPhase.DEFEAT, CombatPhase.FLED]:
            for hit in combo_hits:
                apply_combo_hit(self, hit)
                telemetry.track("combat_combo", combo_id=hit.definition.combo_id)
                try:
                    from engine.vesper_intel import record_tactic
                    record_tactic(self.state, "combo")
                except Exception:
                    pass
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
            terrain = getattr(self, "terrain", None) or {}
            if terrain.get("defend_freeze_chance") and random.random() < float(terrain["defend_freeze_chance"]):
                p.status_effects[StatusEffect.ATORDOADO] = 1
                self.add_log(f"❄️ O terreno gélido entorpece {p.name} ao se proteger!")
        elif cmd.action == "DOWNED":
            try:
                from engine.downed_roles import execute_downed_action
                execute_downed_action(self, p, cmd.value or "wait")
            except Exception:
                self.add_log(f"{p.name} permanece caído.")
            
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

        elif cmd.action == "INTERRUPT":
            self.execute_interrupt(p, cmd.target)

    def execute_interrupt(self, p, target_idx):
        if not FLAGS.combat_intent:
            self.add_log(f"{p.name} tentou interromper, mas a mecânica está desativada.")
            return
        telemetry.track("combat_interrupt_attempt")
        if target_idx is None:
            self.add_log(f"{p.name} falhou ao interromper (sem alvo).")
            return
        try:
            enemy = self.enemies[int(target_idx)]
        except (ValueError, IndexError, TypeError):
            self.add_log(f"{p.name} falhou ao interromper (alvo inválido).")
            return
        if not enemy.is_alive():
            self.add_log(f"{p.name} tentou interromper {enemy.name}, mas o alvo já caiu!")
            return
        planned = getattr(enemy, "planned_action", None)
        view = getattr(enemy, "intent_view", None)
        if not planned or (view and view.interrupted):
            self.add_log(f"{p.name} tentou interromper {enemy.name}, mas não havia ação a cancelar.")
            return
        if view and view.uninterruptible:
            self.add_log(f"⛔ A ação de {enemy.name} é ininterrupível!")
            telemetry.track("combat_interrupt_fail", reason="uninterruptible")
            return
        bond_bonus = 0.0
        try:
            from engine.party_meta import interrupt_chance_bonus
            bond_bonus = interrupt_chance_bonus(self.state)
        except Exception:
            pass
        if roll_interrupt(p, enemy, bond_bonus=bond_bonus):
            enemy.planned_action = (
                "SKIP",
                0,
                [f"{enemy.name} foi interrompido por {p.name} e perdeu o ímpeto!"],
            )
            enemy.intent_view = build_intent_view("SKIP", enemy, interrupted=True)
            enemy.intent_interrupted = True
            self.add_log(f"🛑 {p.name} interrompeu {enemy.name} com sucesso!")
            telemetry.track("combat_interrupt_success")
            try:
                from engine.vesper_intel import record_tactic
                record_tactic(self.state, "interrupt")
            except Exception:
                pass
            try:
                from engine.dto import SoundEffect, VisualEffect
                self.adapter.emit(SoundEffect("HIT_CRITICAL"))
                self.adapter.emit(VisualEffect("shake", target_id=f"enemy_{enemy.idx}", duration=350))
            except Exception:
                pass
        else:
            self.add_log(f"{p.name} tentou interromper {enemy.name}, mas falhou!")
            telemetry.track("combat_interrupt_fail", reason="roll")

    def execute_player_attack(self, p, target: Enemy):
        # Clima Modifiers
        weather = self.state.get_flag("weather", "Ensolarado")
        has_lamp = any(getattr(item, 'id', '') == 'lampeao_eter' for item in getattr(self.state, 'shared_inventory', []))
        if weather == "Nevoeiro" and not has_lamp and random.random() < 0.20:
            self.add_log(f"{p.name} tentou atacar {target.name}, mas errou devido à névoa densa!")
            from engine.dto import SoundEffect
            self.adapter.emit(SoundEffect("SWOOSH!"))
            return
            
        wind_active = self.state.get_flag("arena_wind_active", -1)
        if wind_active == self.turn and random.random() < 0.20:
            self.add_log(f"{p.name} tentou atacar {target.name}, mas errou devido à ventania impetuosa!")
            from engine.dto import SoundEffect
            self.adapter.emit(SoundEffect("SWOOSH!"))
            return
            
        base_atk = p.get_attack_power()
        raw_damage = random.randint(int(base_atk * 0.8), int(base_atk * 1.2))
        crit_chance = 0.05 + (p.agilidade * 0.015 if p.char_class == CharacterClass.LADINO else 0.005)
        unlocked = getattr(p, "talents_unlocked", [])
        if "guerreiro_berserker_2" in unlocked:
            crit_chance += 0.15
        if "guerreiro_colosso_2" in unlocked and "guerreiro_berserker_2" in unlocked:
            crit_chance += 0.10
        is_crit = random.random() < crit_chance
        if is_crit:
            raw_damage = int(raw_damage * 1.8)
            if "guerreiro_colosso_2" in unlocked and "guerreiro_berserker_2" in unlocked:
                heal_amt = int(p.max_hp * 0.05)
                p.heal(heal_amt)
                self.add_log(f"🛡️ Juggernaut Calejado: {p.name} curou {heal_amt} HP ao desferir um golpe crítico!")

        # Phase 2 Void Corruption: slight offense scaling
        try:
            from engine.party_meta import offense_mult
            raw_damage = max(1, int(raw_damage * offense_mult(self.state)))
        except Exception:
            pass
        # Shout buff from downed ally
        if self.state.get_flag("shout_buff_next"):
            raw_damage = int(raw_damage * 1.25)
            self.state.set_flag("shout_buff_next", False)
            self.add_log("📢 O grito de um aliado caído impulsa o golpe!")
            
        res = target.take_damage(raw_damage)
        damage_dealt = res["damage_taken"]
        desc = f"Causou {damage_dealt} de dano em {target.name}."
        if res.get("mitigated"):
            desc += " (Mitigado por defesa ativa!)"
        
        crit_str = f" [CRÍTICO]" if is_crit else ""
        self.add_log(f"{p.name} atacou {target.name}!{crit_str}")
        self.add_log(desc)
        if p.weapon and getattr(p.weapon, "id", None):
            try:
                from engine.relic_attunement import record_relic_use, apply_attunement_to_weapon
                record_relic_use(self.state, p.weapon.id, "crit" if is_crit else "use")
                apply_attunement_to_weapon(self.state, p.weapon)
            except Exception:
                pass


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

        # Fúria: expire over turns; value >= 99 = permanent (e.g. boss ogre)
        if StatusEffect.FURIA in target.status_effects:
            if target.status_effects[StatusEffect.FURIA] < 99:
                target.status_effects[StatusEffect.FURIA] -= 1
                if target.status_effects[StatusEffect.FURIA] <= 0:
                    effects_to_remove.append(StatusEffect.FURIA)
                
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
                # Phase 2 Mercy bond: one free stay-at-1-HP per combat
                revived = False
                try:
                    from engine.party_meta import try_mercy_revive
                    revived = try_mercy_revive(self.state, p)
                except Exception:
                    revived = False
                if revived:
                    self._downed_players_cache.discard(p_id)
                    from engine.dto import SoundEffect
                    self.adapter.emit(SoundEffect("revive"))
                    continue

                self._downed_players_cache.add(p_id)
                from engine.dto import SoundEffect
                self.adapter.emit(SoundEffect("party_member_down"))
                # If the engine leader fell, try to retarget world.player to a living member
                if p is self.player:
                    alive = next((x for x in party if x.hp > 0), None)
                    if alive:
                        companion = getattr(self.player, "companion", None)
                        self.player = alive
                        self.state.player = alive
                        if companion and not getattr(alive, "companion", None):
                            alive.companion = companion
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
            planned = getattr(enemy, "planned_action", None)
            if FLAGS.combat_intent and planned is not None:
                action_type, val, logs = planned
            else:
                action_type, val, logs = enemy.select_action(target_player, self)
            # Clear plan after consumption
            enemy.planned_action = None

            for log in logs:
                self.add_log(log)

            if action_type == "SKIP":
                continue
                
            if action_type in ["ATTACK", "ATTACK_DRAIN"]:
                # Night-time Boss/Shadow damage boost
                time_of_day = self.state.get_flag("time_of_day", "Dia")
                is_boss = "boss" in str(enemy.ai_type).lower()
                is_shadow = "sombra" in enemy.name.lower() or "espectro" in enemy.name.lower() or "sombrio" in enemy.name.lower()
                if time_of_day == "Noite" and (is_boss or is_shadow):
                    val = int(val * 1.2)
                    self.add_log(f"🌙 O poder da noite fortalece o ataque de {enemy.name}!")
                    
                # Phase 2: corruption can slightly increase damage taken
                try:
                    from engine.party_meta import damage_taken_mult
                    val = max(1, int(val * damage_taken_mult(self.state)))
                except Exception:
                    pass
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
                    new_minion.idx = len(self.enemies)
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
            elif action_type == "DEFEND":
                enemy.defending = True
                # logs already emitted from plan

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
        self.rewards["xp"] = total_xp

        party = list(getattr(self.state, 'party', None) or [self.player])
        # Prefer living members; fall back to full party so someone always gets rewards
        recipients = [p for p in party if p.hp > 0] or party or [self.player]
        n = max(1, len(recipients))

        # Full XP to each party member (co-op), gold split evenly
        gold_each = total_gold // n
        gold_remainder = total_gold - (gold_each * n)
        self.add_log(f"Ouro ganho: {total_gold}g (dividido entre {n})")
        for i, p in enumerate(recipients):
            share = gold_each + (gold_remainder if i == 0 else 0)
            p.gold += share
            for log in p.gain_xp(total_xp):
                # Prefix non-leader logs so multi-player level-ups are clear
                if p is not self.player and log:
                    self.add_log(f"[{p.name}] {log}")
                else:
                    self.add_log(log)
        
        for enemy in eligible_enemies:
            chance = 1.0 if "Ogro" in enemy.name or "Inquisidor" in enemy.name or "Malakar" in enemy.name else 0.45
            if random.random() < chance:
                ref_level = max(p.level for p in recipients)
                item = get_random_loot(ref_level)
                if item:
                    self.rewards["loot"].append(item)
                    self.add_log(f"Loot Encontrado: {item.name}")
                    # Consumables go to shared stock via InventoryList; gear to a random recipient
                    if isinstance(item, Consumable):
                        if hasattr(self.state, "shared_inventory"):
                            self.state.shared_inventory.append(item)
                        else:
                            recipients[0].inventory.append(item)
                    else:
                        random.choice(recipients).inventory.append(item)

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
