import uuid
import threading
import copy
from typing import Dict, Any, Optional
from datetime import datetime
from engine.player import Player

class GameState:
    """
    Mantém o estado consolidado de uma sessão de jogo.
    Projetado para facilitar serialização (Snapshots) e reconexão (GET_STATE).
    """
    def __init__(self, player: Player, adapter=None):
        from engine.adapter import UIAdapter
        self.session_id: str = str(uuid.uuid4())
        self.created_at: str = datetime.now().isoformat()
        self.adapter = adapter or UIAdapter.get_instance()
        self.adapter.state = self
        
        # Entidade Principal
        self.player: Player = player
        
        # Estado do Mundo
        self.current_chapter: int = 1
        self._current_location: str = "tutorial"
        
        # Flags Narrativas (Consequências e Decisões)
        self.flags: Dict[str, Any] = {
            "time_of_day": "Dia",
            "weather": "Ensolarado"
        }
        
        # Estado de Batalha (None se estiver explorando pacificamente)
        self.combat_state: Optional[Dict[str, Any]] = None
        
        # Lock for thread safety between Engine and Web Server
        self.lock = threading.Lock()
        
        # Grupo de Jogadores Cooperativo (Party)
        self.party = [self.player]
        self.shared_inventory: list = []
        # PRD Phase 2: bonds / debts / corruption (see engine/party_meta.py)
        from engine.party_meta import default_meta
        self.party_meta: dict = default_meta()
        if hasattr(self.player.inventory, 'state'):
            self.player.inventory.state = self
        self.migrate_party_consumables()

    def migrate_party_consumables(self):
        from engine.items import Consumable
        for player in self.party:
            if hasattr(player, 'inventory') and hasattr(player.inventory, 'state'):
                player.inventory.state = self
            for item in list(player.inventory):
                if isinstance(item, Consumable):
                    player.inventory.remove(item)
                    self.shared_inventory.append(item)
        
    @property
    def current_location(self) -> str:
        return self._current_location

    @current_location.setter
    def current_location(self, value: str):
        old_val = getattr(self, "_current_location", None)
        self._current_location = value
        if old_val is not None and old_val != value:
            world = getattr(self, "world", None)
            if world:
                world.update_environment()

    def set_flag(self, key: str, value: Any):
        """Armazena uma escolha ou evento que persistirá no save."""
        if key == "ogro_poupado":
            self.flags["poupou_ogro"] = value
        elif key == "poupou_ogro":
            self.flags["ogro_poupado"] = value
        elif key == "goblin_ajudado":
            self.flags["ajudou_goblin"] = value
        elif key == "ajudou_goblin":
            self.flags["goblin_ajudado"] = value
        elif key == "elena_traiu":
            self.flags["elena_morta"] = value
        elif key == "elena_morta":
            self.flags["elena_traiu"] = value
            
        with self.lock:
            self.flags[key] = value
            if self.player:
                self.player.choices[key] = value
                if key == "ogro_poupado":
                    self.player.choices["poupou_ogro"] = value
                elif key == "poupou_ogro":
                    self.player.choices["ogro_poupado"] = value
                elif key == "goblin_ajudado":
                    self.player.choices["ajudou_goblin"] = value
                elif key == "ajudou_goblin":
                    self.player.choices["goblin_ajudado"] = value
                elif key == "elena_traiu":
                    self.player.choices["elena_morta"] = value
                elif key == "elena_morta":
                    self.player.choices["elena_traiu"] = value
        # Phase 2 meta hooks (outside lock to avoid re-entrancy deadlocks)
        try:
            from engine.party_meta import observe_flag
            observe_flag(self, key, value)
        except Exception:
            pass

    def get_flag(self, key: str, default: Any = None) -> Any:
        """Recupera uma flag narrativa."""
        with self.lock:
            search_keys = [key]
            if key == "ogro_poupado":
                search_keys.append("poupou_ogro")
            elif key == "poupou_ogro":
                search_keys.append("ogro_poupado")
            elif key == "goblin_ajudado":
                search_keys.append("ajudou_goblin")
            elif key == "ajudou_goblin":
                search_keys.append("goblin_ajudado")
            elif key == "elena_traiu":
                search_keys.append("elena_morta")
            elif key == "elena_morta":
                search_keys.append("elena_traiu")
                
            for k in search_keys:
                if self.player and k in self.player.choices:
                    return self.player.choices[k]
                if k in self.flags:
                    return self.flags[k]
            return default
        
    def to_dict(self) -> dict:
        """
        Gera um snapshot do estado atual para ser enviado à Web ou salvo no banco.
        """
        # Build derived views OUTSIDE the lock: they call get_flag/ensure_meta which
        # also take the lock (non-reentrant). Holding lock here caused deadlocks.
        party_meta_view = self._party_meta_public()
        codex_view = self._codex_public()
        with self.lock:
            return {
                "session_id": self.session_id,
                "created_at": self.created_at,
                "current_chapter": self.current_chapter,
                "current_location": self.current_location,
                "flags": self.flags.copy(),
                "player": {
                    "name": self.player.name,
                    "level": self.player.level,
                    "hp": self.player.hp,
                    "max_hp": self.player.max_hp,
                    "mp": self.player.mp,
                    "max_mp": self.player.max_mp,
                    "gold": self.player.gold,
                    "class": self.player.char_class.value,
                    "xp": self.player.xp,
                    "xp_next_level": self.player.get_xp_needed(),
                    "forca": self.player.forca,
                    "agilidade": self.player.agilidade,
                    "inteligencia": self.player.inteligencia,
                    "vitalidade": self.player.vitalidade,
                    "inventory": [{"id": item.id, "name": item.name, "description": item.description} for item in self.player.inventory if item.id],
                    "weapon": {
                        "id": self.player.weapon.id,
                        "name": self.player.weapon.name,
                        "attack_power": self.player.weapon.attack_power
                    } if self.player.weapon and self.player.weapon.id else None,
                    "armor": {
                        "id": self.player.armor.id,
                        "name": self.player.armor.name,
                        "defense_power": self.player.armor.defense_power
                    } if self.player.armor and self.player.armor.id else None,
                    "quests_active": [q.quest_id for q in self.player.quest_manager.quests.values() if q.is_active],
                    "quests_completed": [q.quest_id for q in self.player.quest_manager.quests.values() if q.is_completed],
                    "companion": {
                        "name": self.player.companion.name,
                        "description": self.player.companion.description
                    } if self.player.companion else None,
                    "status_effects": [eff.name_str for eff in self.player.status_effects.keys()],
                    "talents_unlocked": getattr(self.player, "talents_unlocked", [])
                },
                "in_combat": self.combat_state is not None,
                "combat_state": copy.deepcopy(self.combat_state) if self.combat_state else None,
                "party": [
                    {
                        "client_id": getattr(p, "client_id", None),
                        "name": p.name,
                        "char_class": p.char_class.value,
                        "hp": p.hp,
                        "max_hp": p.max_hp,
                        "mp": p.mp,
                        "max_mp": p.max_mp,
                        "level": p.level,
                        "gold": p.gold,
                        "talents_unlocked": getattr(p, "talents_unlocked", [])
                    }
                    for p in self.party
                ],
                "shared_inventory": [{"id": i.id, "name": i.name, "description": getattr(i, 'description', '')} for i in self.shared_inventory if hasattr(i, 'id')],
                "party_meta": party_meta_view,
                "codex": codex_view,
            }

    def _party_meta_public(self) -> dict:
        try:
            from engine.party_meta import public_view
            return public_view(self)
        except Exception:
            return {"bonds": [], "debts": [], "corruption": {"value": 0, "max": 100}}

    def _codex_public(self) -> dict:
        try:
            from engine.codex import public_view, try_unlock_from_flags
            try_unlock_from_flags(self)
            return public_view(self)
        except Exception:
            return {"entries": [], "unlocked": 0, "total": 0}
