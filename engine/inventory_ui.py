from engine.items import Weapon, Armor
from engine.adapter import get_adapter
from engine.dto import NarrativeText, ClearScreen, PressAnyKey, ChoiceRequested

def manage_inventory(player):
    adapter = get_adapter()
    while True:
        adapter.emit(ClearScreen())
        status_lines = player.show_status()
        
        # Show character status
        adapter.emit(NarrativeText("=== Status do Personagem ==="))
        adapter.emit(NarrativeText("\n".join(status_lines)))
        
        equipable = [item for item in player.inventory if isinstance(item, (Weapon, Armor))]
        
        if not equipable:
            adapter.emit(NarrativeText("\nNenhum equipamento na bolsa."))
            adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            break
            
        options = {}
        for idx, item in enumerate(equipable):
            type_str = "Arma" if isinstance(item, Weapon) else "Armadura"
            stat_str = f"Atq: {item.attack_power}" if isinstance(item, Weapon) else f"Def: {item.defense_power}"
            options[str(idx+1)] = f"Equipar {item.name} ({type_str} | {stat_str})"
            
        options[str(len(equipable)+1)] = "Voltar"
        
        choice = adapter.emit(ChoiceRequested("\nEscolha um item para equipar: ", options))
        
        if choice == str(len(equipable)+1):
            break
            
        item = equipable[int(choice)-1]
        player.inventory.remove(item)
        msg = player.equip(item)
        adapter.emit(NarrativeText(f"\n{msg}"))
        adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
