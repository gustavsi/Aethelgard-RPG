import time
from typing import Union
from engine.combat import CombatSystem, CombatPhase, Command
from engine.adapter import get_adapter
from engine.console import clear_screen, draw_box, make_bar, press_any_key, play_sound_effect
from engine.art import get_enemy_art
from engine.constants import Colors

class CombatUI:
    """
    Temporary shim to run CombatSystem in Terminal mode, preserving old world.py usage.
    """
    def __init__(self, combat: CombatSystem):
        self.combat = combat

    def draw_screen(self):
        from engine.adapter import WebUIAdapter
        if isinstance(self.combat.adapter, WebUIAdapter):
            return
            
        state = self.combat.state.combat_state
        if not state:
            return
            
        clear_screen()
        
        enemy_lines = []
        for e in state["enemies"]:
            if not e["alive"]:
                continue
            hp_bar = make_bar(e["hp"], e["max_hp"], Colors.RED, length=15)
            status_str = " | " + ", ".join(e["status"]) if e["status"] else ""
            defense_str = " [ESCUDADO]" if e["defending"] else ""
            enemy_lines.append(f"({e['idx']+1}) {e['name']} - HP: {hp_bar}{defense_str}{status_str}")
            
        draw_box("Inimigos", enemy_lines, Colors.RED, width=78)

        for e in state["enemies"]:
            if e["alive"]:
                from engine.dto import AsciiArt
                self.combat.adapter.emit(AsciiArt(get_enemy_art(e["name"])))
                break

        player_lines = []
        p = state["player"]
        hp_bar = make_bar(p["hp"], p["max_hp"], Colors.GREEN, length=12)
        mp_bar = make_bar(p["mp"], p["max_mp"], Colors.CYAN, length=12)
        status_line = ", ".join(p["status"]) if p["status"] else "Nenhum"
        
        player_lines.append(f"HP: {hp_bar} {p['hp']}/{p['max_hp']}")
        player_lines.append(f"MP: {mp_bar} {p['mp']}/{p['max_mp']}")
        player_lines.append(f"Ataque: {p['attack']} | Defesa: {p['defense']}")
        player_lines.append(f"Efeitos: {status_line}")
        player_lines.append("")
        
        log_lines = state["logs"]
        
        from engine.console import draw_two_columns
        draw_two_columns(f"Player: {p['name']}", player_lines, "Registros de Combate (Logs)", log_lines)

    def run(self) -> Union[bool, str]:
        from engine.adapter import WebUIAdapter
        is_web = isinstance(self.combat.adapter, WebUIAdapter)
        
        # Advance to first wait state
        self.combat.advance_state()
        
        while not self.combat.is_finished():
            if not is_web:
                self.draw_screen()
            
            # The only blocking state is WAITING_PLAYER_ACTION
            # Any other state means we're animating or processing
            if self.combat.phase == CombatPhase.WAITING_PLAYER_ACTION:
                cmd = self.prompt_action()
                self.combat.process_command(cmd)
            elif self.combat.phase == CombatPhase.WAITING_ALL_PLAYERS:
                if is_web:
                    self.combat.sync_state()
                    if hasattr(self.combat.adapter, 'broadcast'):
                        self.combat.adapter.broadcast({"type": "STATE_UPDATE", "state": self.combat.state.to_dict()})
                    self.combat.adapter._wait_for_input()
                    self.combat.advance_state()
                else:
                    cmd = self.prompt_action()
                    self.combat.submit_player_action(getattr(self.combat.player, 'client_id', 'leader'), cmd)
                    self.combat.advance_state()
                
            if not is_web:
                time.sleep(0.5)
            else:
                time.sleep(0.05)

        if not is_web:
            self.draw_screen()
        
        if self.combat.phase == CombatPhase.VICTORY:
            reward_lines = [
                f"Combate vencido! Todos os inimigos foram derrotados.",
                f"Ouro ganho: {self.combat.rewards['gold']}g",
                f"Ganhou {self.combat.rewards['xp']} XP!",
            ]
            if self.combat.rewards["loot"]:
                reward_lines.append("Loot Encontrado:")
                for item in self.combat.rewards["loot"]:
                    reward_lines.append(f" - {item.name}")
            
            if not is_web:
                draw_box("Resultados do Combate", reward_lines, Colors.GREEN, width=78)
                
            if self.combat.adapter:
                self.combat.adapter.press_any_key("\nPressione [ENTER] para continuar...")
            return True
            
        elif self.combat.phase == CombatPhase.DEFEAT:
            return False
            
        elif self.combat.phase == CombatPhase.FLED:
            return "FLED"

    def prompt_action(self) -> Command:
        from engine.dto import ChoiceRequested
        options = {"1": "Atacar", "2": "Habilidades", "3": "Itens", "4": "Defender"}
        if self.combat.can_flee:
            options["5"] = "Fugir"
            
        choice = self.combat.adapter.emit(ChoiceRequested("O que deseja fazer? ", options))
        
        if choice == "1":
            target_idx = self.prompt_target()
            return Command(action="ATTACK", target=target_idx)
        elif choice == "2":  # Habilidades
            from engine.constants import StatusEffect
            if StatusEffect.AFOGAMENTO in self.combat.player.status_effects:
                from engine.dto import NarrativeText
                self.combat.adapter.emit(NarrativeText("⚠️ Você está se afogando e não pode usar Habilidades!"))
                self.combat.adapter.press_any_key("Pressione [ENTER] para voltar...")
                return self.prompt_action()
            skills = self.combat.player.get_skills()
            if not skills:
                from engine.dto import NarrativeText
                self.combat.adapter.emit(NarrativeText("Você não possui habilidades ainda!"))
                self.combat.adapter.press_any_key("Pressione [ENTER] para voltar...")
                return self.prompt_action()
            skill_opts = {str(i+1): f"{s.name} (MP: {s.mp})" for i, s in enumerate(skills)}
            skill_opts["0"] = "← Voltar"
            skill_choice = self.combat.adapter.emit(ChoiceRequested("Qual habilidade usar?", skill_opts))
            if skill_choice == "0":
                return self.prompt_action()
            try:
                skill = skills[int(skill_choice) - 1]
                target_idx = self.prompt_target() if skill.requires_target else None
                return Command(action="SKILL", target=target_idx, value=skill)
            except (IndexError, ValueError):
                return self.prompt_action()
        elif choice == "3":  # Itens
            from engine.items import Consumable
            consumables = [i for i in self.combat.player.inventory if isinstance(i, Consumable)]
            if not consumables:
                from engine.dto import NarrativeText
                self.combat.adapter.emit(NarrativeText("Sem itens consumíveis no inventário!"))
                self.combat.adapter.press_any_key("Pressione [ENTER] para voltar...")
                return self.prompt_action()
            item_opts = {str(i+1): item.name for i, item in enumerate(consumables)}
            item_opts["0"] = "← Voltar"
            item_choice = self.combat.adapter.emit(ChoiceRequested("Qual item usar?", item_opts))
            if item_choice == "0":
                return self.prompt_action()
            try:
                item = consumables[int(item_choice) - 1]
                return Command(action="ITEM", value=item)
            except (IndexError, ValueError):
                return self.prompt_action()
        elif choice == "4":
            return Command(action="DEFEND")
        elif choice == "5" and self.combat.can_flee:
            return Command(action="FLEE")

    def prompt_target(self) -> int:
        from engine.dto import ChoiceRequested
        state = self.combat.state.combat_state
        alive = [e for e in state["enemies"] if e["alive"]]
        if len(alive) == 1:
            return alive[0]["idx"]
            
        options = {str(i+1): f"{e['name']}" for i, e in enumerate(alive)}
        choice = self.combat.adapter.emit(ChoiceRequested("Selecione o alvo: ", options))
        return alive[int(choice)-1]["idx"]
