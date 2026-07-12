from typing import Callable, Any

class SideQuest:
    def __init__(self, quest_id: str, name: str, description: str, giver_npc: str, reward_fn: Callable[[Any], None]):
        self.id = quest_id
        self.name = name
        self.description = description
        self.giver_npc = giver_npc
        self.reward_fn = reward_fn

    def accept(self, world, add_log_func: Callable[[str], None]) -> bool:
        flag_active = f"sidequest_{self.id}_ativa"
        flag_completed = f"sidequest_{self.id}_concluida"
        
        if world.state.get_flag(flag_active) or world.state.get_flag(flag_completed):
            return False
            
        world.state.set_flag(flag_active, True)
        add_log_func(f"\n[Side Quest] Nova missão opcional aceita: {self.name}")
        add_log_func(f"Descrição: {self.description}")
        return True

    def complete(self, world, add_log_func: Callable[[str], None]) -> bool:
        flag_active = f"sidequest_{self.id}_ativa"
        flag_completed = f"sidequest_{self.id}_concluida"
        
        if not world.state.get_flag(flag_active) or world.state.get_flag(flag_completed):
            return False
            
        world.state.set_flag(flag_active, False)
        world.state.set_flag(flag_completed, True)
        add_log_func(f"\n[Side Quest] Missão Concluída: {self.name}")
        
        if self.reward_fn:
            self.reward_fn(world)
            
        return True
