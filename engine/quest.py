from typing import Dict, Any, Callable

class Quest:
    def __init__(self, quest_id: str, name: str, description: str, rewards: Dict[str, Any]):
        self.quest_id = quest_id
        self.name = name
        self.description = description
        self.rewards = rewards
        self.is_completed = False
        self.is_active = False

    def complete(self, player, add_log_func: Callable) -> None:
        if self.is_completed or not self.is_active:
            return
            
        self.is_completed = True
        self.is_active = False
        add_log_func(f"\nMissão Concluída: {self.name}")
        
        if "gold" in self.rewards:
            gold = self.rewards["gold"]
            player.gold += gold
            add_log_func(f"Recompensa: +{gold} Ouro")
            
        if "xp" in self.rewards:
            xp = self.rewards["xp"]
            xp_logs = player.gain_xp(xp)
            for log in xp_logs:
                add_log_func(log)

        if "items" in self.rewards:
            from engine.items import create_item
            for item_id in self.rewards["items"]:
                item = create_item(item_id)
                player.inventory.append(item)
                add_log_func(f"Recompensa: {item.name}")

class QuestManager:
    def __init__(self):
        self.quests: Dict[str, Quest] = {
            "cavernas": Quest(
                "cavernas",
                "As Cavernas Sussurrantes",
                "Investigue a atividade suspeita nas Cavernas Sussurrantes ao norte de Oakhaven.",
                {"gold": 100, "xp": 150}
            )
        }

    def start_quest(self, quest_id: str, add_log_func: Callable):
        if quest_id in self.quests:
            self.quests[quest_id].is_active = True
            add_log_func(f"\nNova Missão: {self.quests[quest_id].name}")

    def complete_quest(self, quest_id: str, player, add_log_func: Callable):
        if quest_id in self.quests:
            self.quests[quest_id].complete(player, add_log_func)

    def get_active_quests(self) -> list:
        return [q for q in self.quests.values() if q.is_active]

    def has_active(self, quest_id: str) -> bool:
        return quest_id in self.quests and self.quests[quest_id].is_active
