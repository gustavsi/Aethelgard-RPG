import time
from typing import Dict, Any, List
from engine.items import create_item
from engine.shop import Shop
from engine.adapter import get_adapter
from engine.dto import NarrativeText, ChoiceRequested, ClearScreen, PressAnyKey

class NPC:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def interact(self, player) -> None:
        pass

class Blacksmith(NPC):
    def __init__(self):
        super().__init__("Garrett (O Ferreiro)", "Um homem musculoso martelando aço quente sobre uma bigorna.")
        self.shop = Shop("Forja de Garrett", [
            ("espada_soldado", 30),
            ("cota_malha", 50)
        ], "\"Armas afiadas e armaduras fortes! O que precisa?\"")

    def interact(self, player) -> None:
        adapter = get_adapter()
        while True:
            adapter.emit(ClearScreen())
            lines = [
                f"=== {self.name} ===",
                "\"Saudações, viajante! Quer melhorar suas armas ou comprar equipamentos novos?\"",
                f"Seu Ouro atual: {player.gold}g",
                f"Arma equipada: {player.weapon.name if player.weapon else 'Nenhuma'} (Atq: {player.weapon.attack_power if player.weapon else 0})",
                f"Armadura equipada: {player.armor.name if player.armor else 'Nenhuma'} (Def: {player.armor.defense_power if player.armor else 0})"
            ]
            adapter.emit(NarrativeText("\n".join(lines)))
            
            options = {
                "1": "Comprar Equipamentos (Loja)",
                "2": "Melhorar Arma Atual (+4 Dano) - Custo: 35g",
                "3": "Sair"
            }
            
            choice = adapter.emit(ChoiceRequested("O que deseja fazer? ", options))
            
            if choice == "1":
                self.shop.open_shop(player)
            elif choice == "2":
                if player.weapon:
                    if player.gold >= 35:
                        player.gold -= 35
                        player.weapon.attack_power += 4
                        player.weapon.name += " +1"
                        adapter.emit(NarrativeText(f"\nGarrett martela sua arma. O poder de ataque dela aumentou! Nova força: {player.weapon.attack_power}"))
                    else:
                        adapter.emit(NarrativeText("\n\"O preço do carvão está alto. Sem ouro, sem melhoria.\" - diz Garrett."))
                else:
                    adapter.emit(NarrativeText("\n\"Você não tem nenhuma arma equipada para melhorar.\" - diz Garrett."))
                adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            elif choice == "3":
                break

class TavernKeeper(NPC):
    def __init__(self):
        super().__init__("Barnaby (O Taverneiro)", "Limpando copos atrás do balcão de madeira escura.")
        self.shop = Shop("O Javali Saltitante", [
            ("pocao_vida_p", 5),
            ("pocao_mana_p", 5),
            ("pocao_vida_m", 15)
        ], "\"Sente-se! Temos poções e um canto quente. O que vai ser?\"")

    def interact(self, player) -> None:
        adapter = get_adapter()
        while True:
            adapter.emit(ClearScreen())
            lines = [
                f"=== {self.name} ===",
                "\"Bem-vindo à Taverna do Javali Saltitante! Beber ajuda a esquecer as dores.\"",
                f"Seu Ouro atual: {player.gold}g"
            ]
            adapter.emit(NarrativeText("\n".join(lines)))
            
            options = {
                "1": "Comprar Poções/Itens (Loja)",
                "2": "Alugar um quarto para descansar (Cura Total) (15g)",
                "3": "Conversar sobre boatos",
                "4": "Sair"
            }
            
            choice = adapter.emit(ChoiceRequested("O que deseja fazer? ", options))
            
            if choice == "1":
                self.shop.open_shop(player)
            elif choice == "2":
                if player.gold >= 15:
                    player.gold -= 15
                    player.hp = player.max_hp
                    player.mp = player.max_mp
                    player.status_effects.clear()
                    adapter.emit(NarrativeText("\nVocê dormiu profundamente. Vida e Mana totalmente restauradas!"))
                else:
                    adapter.emit(NarrativeText("\n\"Dormir no chão da taverna é de graça, mas no quarto custa 15 ouro.\""))
                adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            elif choice == "3":
                adapter.emit(NarrativeText("\nBarnaby se inclina e cochicha:"))
                adapter.emit(NarrativeText("\"Dizem que o Lorde Malakar no Templo Ancestral está procurando selos sombrios para libertar uma entidade de caos. Dizem que há um desses selos escondido na floresta inicial...\""))
                adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            elif choice == "4":
                break

class ElderAlistair(NPC):
    def __init__(self):
        super().__init__("Ancião Alistair", "Um idoso barbudo com vestes longas e um olhar sábio.")

    def interact(self, player) -> None:
        adapter = get_adapter()
        
        # Check active or completed quest first to avoid duplication (Bug 25)
        quest = player.quest_manager.quests.get("cavernas")
        if quest and quest.is_completed:
            adapter.emit(NarrativeText("\n\"Obrigado por salvar Oakhaven libertando as Cavernas Sussurrantes! Você é um verdadeiro herói!\""))
            adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            return
        elif quest and quest.is_active:
            adapter.emit(NarrativeText("\n\"Como está indo a investigação das Cavernas Sussurrantes? O Inquisidor ainda ameaça a vila.\""))
            adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            return
            
        adapter.emit(ClearScreen())
        
        dialog_lines = [f"=== {self.name} ==="]
        if player.choices.get("poupou_ogro"):
            dialog_lines.append("\"Aquele ogro da cabana... soube que você poupou a vida dele.")
            dialog_lines.append(" Alguns na vila acham loucura, mas talvez haja sabedoria")
            dialog_lines.append(" em não derramar sangue desnecessário.\"")
        else:
            dialog_lines.append("\"Fiquei sabendo que você derrotou a besta da cabana abandonada.")
            dialog_lines.append(" Agradecemos por trazer segurança ao nosso vale!\"")
            
        if player.choices.get("roubou_cabana"):
            dialog_lines.append("")
            dialog_lines.append("\"Porém... ouvi rumores de que itens sagrados de Oakhaven")
            dialog_lines.append(" sumiram da cabana abandonada. Espero que você não")
            dialog_lines.append(" tenha nada a ver com isso.\"")
            
        dialog_lines.append("")
        dialog_lines.append("\"Nossos batedores relataram atividades suspeitas nas")
        dialog_lines.append(" Cavernas Sussurrantes ao norte. O Inquisidor das Sombras")
        dialog_lines.append(" está reunindo escravos e poder. Viajante, você poderia nos")
        dialog_lines.append(" ajudar a investigar o que está acontecendo por lá?\"")
        
        adapter.emit(NarrativeText("\n".join(dialog_lines)))
        
        options = {
            "1": "\"Eu irei investigar as cavernas!\"",
            "2": "\"O que eu ganho com isso?\"",
            "3": "\"Não posso ajudar agora.\""
        }
        
        choice = adapter.emit(ChoiceRequested("Como responder? ", options))
        
        def quest_log_func(msg):
            adapter.emit(NarrativeText(msg))
            
        if choice == "1":
            adapter.emit(NarrativeText("\n\"Que a chama da justiça guie seu caminho. Pegue esta poção para ajudar em sua jornada.\""))
            player.inventory.append(create_item("pocao_vida_m"))
            player.quest_manager.start_quest("cavernas", quest_log_func)
            adapter.emit(NarrativeText("Você recebeu Poção de Vida Média!"))
            adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            
        elif choice == "2":
            adapter.emit(NarrativeText("\n\"Oakhaven não é rica, mas se você nos salvar das garras"))
            adapter.emit(NarrativeText("do inquisidor, lhe daremos acesso ao nosso tesouro secreto"))
            adapter.emit(NarrativeText("e 100 moedas de ouro.\""))
            player.choices["negociou_recompensa"] = True
            
            sub_opt = {
                "1": "\"Tudo bem, aceito a missão.\"",
                "2": "\"Ainda assim, recuso.\""
            }
            sub_ch = adapter.emit(ChoiceRequested("Sua decisão: ", sub_opt))
            if sub_ch == "1":
                player.quest_manager.start_quest("cavernas", quest_log_func)
                adapter.emit(NarrativeText("\n\"Obrigado. Que o destino lhe sorria nas profundezas arcanas.\""))
                adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
            else:
                adapter.emit(NarrativeText("\n\"Entendo. Que pena...\""))
                adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
        else:
            adapter.emit(NarrativeText("\n\"Entendo. Se mudar de ideia, estarei aqui esperando.\""))
            adapter.emit(PressAnyKey("Pressione [ENTER] para continuar..."))
