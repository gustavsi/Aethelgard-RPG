import json
import os
from engine.items import create_item
from engine.constants import CharacterClass
from engine.state import GameState
from engine.player import Player

SAVE_FILE = "savegame.json"

COMPANION_NAME_TO_ID = {
    "elena": "elena",
    "drogg": "drogg",
    "ysolde": "ysolde",
    "ulfgar": "ulfgar",
}


def get_save_path(session_id: str = None) -> str:
    if session_id:
        import re
        clean_sid = re.sub(r'[^a-zA-Z0-9_\-]', '', session_id)
        os.makedirs("saves", exist_ok=True)
        return os.path.join("saves", f"save_{clean_sid}.json")
    return SAVE_FILE


def _companion_id_from_player(player) -> str | None:
    if not player or not player.companion:
        return None
    name = player.companion.name.lower()
    for key, cid in COMPANION_NAME_TO_ID.items():
        if key in name:
            return cid
    return None


def _serialize_item(item) -> dict | str | None:
    if not item or not getattr(item, "id", None):
        return None
    if getattr(item, "attack_power", None) is not None or getattr(item, "defense_power", None) is not None:
        return {
            "id": item.id,
            "name": item.name,
            "attack_power": getattr(item, "attack_power", None),
            "defense_power": getattr(item, "defense_power", None),
        }
    return item.id


def _deserialize_item(item_data):
    if isinstance(item_data, dict):
        item = create_item(item_data["id"])
        if item:
            if item_data.get("name"):
                item.name = item_data["name"]
            if item_data.get("attack_power") is not None:
                item.attack_power = item_data["attack_power"]
            if item_data.get("defense_power") is not None:
                item.defense_power = item_data["defense_power"]
        return item
    if isinstance(item_data, str):
        return create_item(item_data)
    return None


def serialize_player(player) -> dict:
    """Full player snapshot for save (leader or any party member)."""
    data = {
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
        "talent_points": getattr(player, "talent_points", 0),
        "talents_unlocked": list(getattr(player, "talents_unlocked", []) or []),
        "inventory": [
            s for s in (_serialize_item(item) for item in player.inventory) if s
        ],
        "weapon": _serialize_item(player.weapon) if player.weapon else None,
        "armor": _serialize_item(player.armor) if player.armor else None,
        "quests_active": [q.quest_id for q in player.quest_manager.quests.values() if q.is_active],
        "quests_completed": [q.quest_id for q in player.quest_manager.quests.values() if q.is_completed],
        "companion": _companion_id_from_player(player),
        "client_id": getattr(player, "client_id", None),
    }
    return data


def apply_player_data(player: Player, p_data: dict) -> Player:
    """Apply serialized fields onto an existing Player instance."""
    if p_data.get("class"):
        try:
            player.char_class = CharacterClass[p_data["class"]]
        except Exception:
            pass
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
    player.talent_points = p_data.get("talent_points", 0)
    player.talents_unlocked = list(p_data.get("talents_unlocked", []) or [])

    player.inventory.clear()
    for item_data in p_data.get("inventory", []):
        item = _deserialize_item(item_data)
        if item:
            list.append(player.inventory, item)

    weapon_data = p_data.get("weapon")
    if weapon_data:
        player.weapon = _deserialize_item(weapon_data)
    else:
        player.weapon = None

    armor_data = p_data.get("armor")
    if armor_data:
        player.armor = _deserialize_item(armor_data)
    else:
        player.armor = None

    for qid in p_data.get("quests_active", []):
        if qid in player.quest_manager.quests:
            player.quest_manager.quests[qid].is_active = True
            player.quest_manager.quests[qid].is_completed = False
    for qid in p_data.get("quests_completed", []):
        if qid in player.quest_manager.quests:
            player.quest_manager.quests[qid].is_completed = True
            player.quest_manager.quests[qid].is_active = False

    comp_id = p_data.get("companion")
    if comp_id:
        from engine.companion import get_companion
        player.companion = get_companion(comp_id)
    else:
        player.companion = None

    if p_data.get("client_id"):
        player.client_id = p_data["client_id"]

    return player


def deserialize_player(p_data: dict) -> Player:
    player = Player(p_data.get("name", "Herói"), CharacterClass[p_data.get("class", "GUERREIRO")])
    return apply_player_data(player, p_data)


def save_game(state: GameState, add_log_func=None, session_id: str = None):
    """
    Serializa o GameState completo em JSON (líder + party + talentos + companheiros).
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

    party = list(getattr(state, "party", None) or [player])
    # Ensure leader is included
    if player not in party:
        party = [player] + party

    from engine.party_meta import serialize_meta

    data = {
        "session_id": state.session_id,
        "created_at": state.created_at,
        "current_chapter": state.current_chapter,
        "current_location": state.current_location,
        "flags": state.flags,
        "player": serialize_player(player),
        "party": [serialize_player(p) for p in party],
        "shared_inventory": [
            s for s in (_serialize_item(item) for item in getattr(state, "shared_inventory", []) or []) if s
        ],
        "party_meta": serialize_meta(state),
        "save_schema_version": 2,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    add_log_func("Jogo salvo com sucesso!")


def load_game(session_id: str = None) -> GameState:
    """
    Lê o JSON, reconstrói o Player, a party e o GameState.
    """
    filepath = get_save_path(session_id)
    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    p_data = data.get("player", {})
    player = deserialize_player(p_data)

    state = GameState(player)
    state.session_id = data.get("session_id", state.session_id)
    state.created_at = data.get("created_at", state.created_at)
    state.current_chapter = data.get("current_chapter", 1)
    state.current_location = data.get("current_location", "tutorial")
    state.flags = data.get("flags", {})

    # Restore full party if present; fall back to leader-only
    party_data = data.get("party") or [p_data]
    restored_party = []
    for pd in party_data:
        if pd.get("name", "").lower() == player.name.lower() and pd.get("class") == player.char_class.name:
            if player not in restored_party:
                restored_party.append(player)
                apply_player_data(player, pd)
            continue
        restored_party.append(deserialize_player(pd))
    if player not in restored_party:
        restored_party.insert(0, player)
    state.party = restored_party

    # Shared inventory
    state.shared_inventory = []
    for item_data in data.get("shared_inventory", []) or []:
        item = _deserialize_item(item_data)
        if item:
            state.shared_inventory.append(item)

    # Backward compatibility with old saves where choices were in player
    old_choices = data.get("choices")
    if old_choices:
        for k, v in old_choices.items():
            state.flags[k] = v

    player.choices = dict(state.flags)
    old_p_choices = p_data.get("choices")
    if old_p_choices:
        for k, v in old_p_choices.items():
            state.flags[k] = v

    from engine.party_meta import deserialize_meta
    deserialize_meta(state, data.get("party_meta"))

    return state


def merge_lobby_party_with_save(loaded_state: GameState, lobby_players: list) -> list:
    """
    Match lobby-connected Player shells to saved party members by name (then class).
    Restores stats/talents/gear onto the live objects and assigns client_ids from lobby.
    Preserves any saved party members that are not connected in the lobby.
    """
    if not loaded_state:
        return lobby_players

    saved = list(getattr(loaded_state, "party", None) or [loaded_state.player])
    used = set()
    merged = []

    for live in lobby_players:
        match = None
        # Exact name match first
        for i, sp in enumerate(saved):
            if i in used:
                continue
            if sp.name.lower() == live.name.lower():
                match = (i, sp)
                break
        # Fallback: same class unused
        if not match:
            for i, sp in enumerate(saved):
                if i in used:
                    continue
                if sp.char_class == live.char_class:
                    match = (i, sp)
                    break
        if match:
            idx, sp = match
            used.add(idx)
            # Copy saved progress onto live lobby player (keeps live client_id)
            cid = getattr(live, "client_id", None)
            apply_player_data(live, serialize_player(sp))
            if cid:
                live.client_id = cid
            merged.append(live)
        else:
            # New join — keep level-1 lobby shell
            merged.append(live)

    # Preserve any saved members not connected in current lobby session
    for i, sp in enumerate(saved):
        if i not in used:
            merged.append(sp)

    if not merged:
        return saved

    # Ensure leader (state.player) points at matching live member
    leader_name = loaded_state.player.name.lower()
    for p in merged:
        if p.name.lower() == leader_name:
            loaded_state.player = p
            break
    else:
        loaded_state.player = merged[0]

    loaded_state.party = merged
    return merged
