import json
import os
from engine.items import create_item
from engine.constants import CharacterClass
from engine.state import GameState
from engine.player import Player

SAVE_FILE = "savegame.json"

def get_save_path(session_id: str = None) -> str:
    if session_id:
        import re
        clean_sid = re.sub(r'[^a-zA-Z0-9_\-]', '', session_id)
        os.makedirs("saves", exist_ok=True)
        return os.path.join("saves", f"save_{clean_sid}.json")
    return SAVE_FILE

def save_game(state: GameState, add_log_func=None, session_id: str = None):
    """
    Serializa o GameState completo em JSON.
    """
    if add_log_func is None:
        from engine.dto import NarrativeText
        add_log_func = lambda msg: state.adapter.emit(NarrativeText(msg)) if (state and getattr(state, "adapter", None)) else print
        
    player = state.player
    from engine.adapter import WebUIAdapter
    is_web = isinstance(state.adapter, WebUIAdapter)
    sid = session_id
    if not sid:
        sid = getattr(state, "session_id", None)
        if sid and not is_web:
            if len(sid) == 36 and sid.count("-") == 4:
                sid = None
    filepath = get_save_path(sid)
    state.flags.update(player.choices)
    data = {
        "session_id": state.session_id,
        "created_at": state.created_at,
        "current_chapter": state.current_chapter,
        "current_location": state.current_location,
        "flags": state.flags,
        "player": {
            "name": player.name,
            "class": player.char_class.name,
            "level": player.level,
            "xp": player.xp,
            "hp": player.hp,
            "max_hp": player.max_hp,
            "mp": player.mp,
            "max_mp": player.max_mp,
            "forca": player.forca,
            "agilidade": player.agilidade,
            "inteligencia": player.inteligencia,
            "vitalidade": player.vitalidade,
            "gold": player.gold,
            "inventory": [
                {
                    "id": item.id,
                    "name": item.name,
                    "attack_power": getattr(item, "attack_power", None),
                    "defense_power": getattr(item, "defense_power", None)
                } if (getattr(item, "attack_power", None) is not None or getattr(item, "defense_power", None) is not None) else item.id
                for item in player.inventory if item.id
            ],
            "weapon": {
                "id": player.weapon.id,
                "name": player.weapon.name,
                "attack_power": player.weapon.attack_power
            } if player.weapon and player.weapon.id else None,
            "armor": {
                "id": player.armor.id,
                "name": player.armor.name,
                "defense_power": player.armor.defense_power
            } if player.armor and player.armor.id else None,
            "quests_active": [q.quest_id for q in player.quest_manager.quests.values() if q.is_active],
            "quests_completed": [q.quest_id for q in player.quest_manager.quests.values() if q.is_completed],
            "companion": None
        }
    }
    
    if player.companion:
        if "elena" in player.companion.name.lower():
            data["player"]["companion"] = "elena"
        elif "drogg" in player.companion.name.lower():
            data["player"]["companion"] = "drogg"
        elif "ysolde" in player.companion.name.lower():
            data["player"]["companion"] = "ysolde"
            
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    add_log_func("Jogo salvo com sucesso!")
        
def load_game(session_id: str = None) -> GameState:
    """
    Lê o JSON, reconstrói o Player e o GameState.
    Retorna a instância do GameState pronta para uso no world.py.
    """
    filepath = get_save_path(session_id)
    if not os.path.exists(filepath):
        return None
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    p_data = data.get("player", {})
    
    player = Player(p_data.get("name", "Herói"), CharacterClass[p_data.get("class", "GUERREIRO")])
    player.level = p_data.get("level", 1)
    player.xp = p_data.get("xp", 0)
    player.max_hp = p_data.get("max_hp", player.max_hp)
    player.hp = p_data.get("hp", player.max_hp)
    player.max_mp = p_data.get("max_mp", player.max_mp)
    player.mp = p_data.get("mp", player.max_mp)
    player.forca = p_data.get("forca", player.forca)
    player.agilidade = p_data.get("agilidade", player.agilidade)
    player.inteligencia = p_data.get("inteligencia", player.inteligencia)
    player.vitalidade = p_data.get("vitalidade", player.vitalidade)
    player.gold = p_data.get("gold", 0)
    
    player.inventory.clear()
    for item_data in p_data.get("inventory", []):
        if isinstance(item_data, dict):
            item = create_item(item_data["id"])
            if item:
                if "name" in item_data and item_data["name"]:
                    item.name = item_data["name"]
                if "attack_power" in item_data and item_data["attack_power"] is not None:
                    item.attack_power = item_data["attack_power"]
                if "defense_power" in item_data and item_data["defense_power"] is not None:
                    item.defense_power = item_data["defense_power"]
                player.inventory.append(item)
        else:
            item = create_item(item_data)
            if item:
                player.inventory.append(item)
            
    weapon_data = p_data.get("weapon")
    if isinstance(weapon_data, dict):
        item = create_item(weapon_data["id"])
        if item:
            item.name = weapon_data.get("name", item.name)
            item.attack_power = weapon_data.get("attack_power", item.attack_power)
            player.weapon = item
    elif isinstance(weapon_data, str):
        player.weapon = create_item(weapon_data)
    else:
        player.weapon = None
        
    armor_data = p_data.get("armor")
    if isinstance(armor_data, dict):
        item = create_item(armor_data["id"])
        if item:
            item.name = armor_data.get("name", item.name)
            item.defense_power = armor_data.get("defense_power", item.defense_power)
            player.armor = item
    elif isinstance(armor_data, str):
        player.armor = create_item(armor_data)
    else:
        player.armor = None
        
    for qid in p_data.get("quests_active", []):
        if qid in player.quest_manager.quests:
            player.quest_manager.quests[qid].is_active = True
    for qid in p_data.get("quests_completed", []):
        if qid in player.quest_manager.quests:
            player.quest_manager.quests[qid].is_completed = True
            
    comp_id = p_data.get("companion")
    if comp_id:
        from engine.companion import get_companion
        player.companion = get_companion(comp_id)
        
    state = GameState(player)
    state.session_id = data.get("session_id", state.session_id)
    state.created_at = data.get("created_at", state.created_at)
    state.current_chapter = data.get("current_chapter", 1)
    state.current_location = data.get("current_location", "tutorial")
    state.flags = data.get("flags", {})
    
    # Backward compatibility with old saves where choices were in player
    old_choices = data.get("choices")
    if old_choices:
        for k, v in old_choices.items():
            state.flags[k] = v
            
    player.choices = dict(state.flags)
        # Also migrate from p_data if it exists there
    old_p_choices = p_data.get("choices")
    if old_p_choices:
        for k, v in old_p_choices.items():
            state.flags[k] = v
            
    return state
