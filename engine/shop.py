from typing import List, Tuple
from engine.items import Item, create_item
from engine.adapter import get_adapter
from engine.dto import NarrativeText, ClearScreen, PressAnyKey, ChoiceRequested

class Shop:
    def __init__(self, name: str, items: List[Tuple[str, int]], greet_msg: str):
        self.name = name
        self.inventory_blueprint = items
        self.greet_msg = greet_msg

    def open_shop(self, player):
        adapter = get_adapter()
        while True:
            adapter.emit(ClearScreen())
            adapter.emit(NarrativeText(f"=== {self.name} ==="))
            adapter.emit(NarrativeText(self.greet_msg))
            adapter.emit(NarrativeText(f"Seu Ouro: {player.gold}g\n"))
            
            options = {}
            stock = []
            for idx, (item_id, price) in enumerate(self.inventory_blueprint):
                item = create_item(item_id)
                stock.append((item, price))
                options[str(idx+1)] = f"Comprar {item.name} ({price}g) - {item.description}"
                
            options[str(len(stock)+1)] = "Sair"
            
            choice = adapter.emit(ChoiceRequested("O que deseja comprar? ", options))
            if choice == str(len(stock)+1):
                break
                
            selected_idx = int(choice) - 1
            item, price = stock[selected_idx]
            
            if player.gold >= price:
                player.gold -= price
                player.inventory.append(item)
                adapter.emit(NarrativeText(f"\nVocê comprou {item.name} por {price}g!"))
                adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            else:
                adapter.emit(NarrativeText("\nOuro insuficiente!"))
                adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
