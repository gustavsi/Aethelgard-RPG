import random
import time
from engine.dto import NarrativeText, ChoiceRequested, ClearScreen, PressAnyKey, SoundEffect, AsciiArt
from engine.enemy import spawn_enemy
from engine.combat import CombatSystem
from engine.constants import CharacterClass

def clear_screen():
    from engine.adapter import get_adapter
    from engine.dto import ClearScreen
    get_adapter().emit(ClearScreen())

def typewriter(text, delay=0.02, color=None):
    from engine.adapter import get_adapter
    from engine.dto import NarrativeText
    get_adapter().emit(NarrativeText(text))

def press_any_key(msg="Pressione [ENTER] para continuar..."):
    from engine.adapter import get_adapter
    from engine.dto import PressAnyKey
    get_adapter().emit(PressAnyKey(msg))

def print_centered(text, color=None):
    from engine.adapter import get_adapter
    from engine.dto import NarrativeText
    get_adapter().emit(NarrativeText(text))

def play_sound_effect(effect_text, color=None):
    from engine.adapter import get_adapter
    from engine.dto import SoundEffect
    get_adapter().emit(SoundEffect(effect_text))

class Chapter8Mixin:
    def chapter_8_start(self):
        from engine.save_system import save_game
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "kragmoor"
        self.state.current_chapter = 8
        if self.adapter:
            self.adapter.on_state_change(self.state)
            
        clear_screen()
        print_centered("=== CAPÍTULO VIII: AS MINAS DE KRAGMOOR ===", None)
        
        typewriter("A jornada leva vocês para os picos congelados das Montanhas de Ferro.", 0.03)
        typewriter("O ar fica denso com fumaça preta e cinzas vulcânicas expelidas da terra.", 0.03)
        typewriter("Diante de vocês erguem-se as colossais portas de Kragmoor, a antiga cidade-forja anã.", 0.03)
        self.request_party_ready()
        press_any_key()
        
        # Encontro com Brokk
        clear_screen()
        print_centered("=== A FORJA BARREADA ===", None)
        typewriter("Brokk: \"Pelos martelos dos ancestrais! Viajantes reais nesta hora sombria?\"", 0.03)
        typewriter("\"O Portão dos Selos foi corrompido. O Golem de Kragmoor enlouqueceu com energia roxa.\"", 0.03)
        typewriter("\"E aquela bruxa de máscara cinza entrou lá para alimentar a forja com o Vazio!\"", 0.03)
        press_any_key()
        
        # Class Gate
        clear_screen()
        print_centered("=== PORTÃO DOS SELOS ANCESTRAIS ===", None)
        typewriter("O enorme portão rúnico está bloqueado por rifts do Vazio e armadilhas anãs ativas.", 0.03)
        
        options = {}
        if any(p.char_class == CharacterClass.LADINO for p in self.party):
            options["1"] = "[Ladino] Sabotar os mecanismos de contrapeso físicos silenciosamente"
        if any(p.char_class == CharacterClass.GUERREIRO for p in self.party):
            options["2"] = "[Guerreiro] Escorar a grade de ferro cadente com escudo reforçado"
        if any(p.char_class == CharacterClass.MAGO for p in self.party):
            options["3"] = "[Mago] Realinhar o fluxo das runas elementares de tranca"
        if any(p.char_class == CharacterClass.CLERIGO for p in self.party):
            options["4"] = "[Clérigo] Purificar a barreira de energia do Vazio com luz sagrada"
        options["5"] = "Invasão direta pelas docas de lava (Caminho Difícil)"
        
        choice = self.get_party_vote(options, prompt="Qual abordagem a party escolhe? ")
        
        if choice == "1" and any(p.char_class == CharacterClass.LADINO for p in self.party):
            clear_screen()
            typewriter("[Ladino] Com movimentos cirúrgicos, o Ladino desarma as engrenagens rúnicas do portão.", 0.03)
            self.state.set_flag("kragmoor_infiltrado", True)
            press_any_key()
        elif choice == "2" and any(p.char_class == CharacterClass.GUERREIRO for p in self.party):
            clear_screen()
            typewriter("[Guerreiro] O Guerreiro escora a grade de ferro cadente nos ombros, permitindo a travessia.", 0.03)
            self.state.set_flag("kragmoor_portão_erguido", True)
            press_any_key()
        elif choice == "3" and any(p.char_class == CharacterClass.MAGO for p in self.party):
            clear_screen()
            typewriter("[Mago] O Mago reescreve a sequência mágica rúnica, forçando a abertura do metal.", 0.03)
            self.state.set_flag("kragmoor_selo_realinhado", True)
            press_any_key()
        elif choice == "4" and any(p.char_class == CharacterClass.CLERIGO for p in self.party):
            clear_screen()
            typewriter("[Clérigo] A prece protetora do Clérigo dispersa o plasma escuro, liberando os trincos.", 0.03)
            self.state.set_flag("kragmoor_purificado", True)
            press_any_key()
        else:
            clear_screen()
            typewriter("A party arromba o portão rúnico, ativando os alarmes de segurança da forja!", 0.03)
            typewriter("Duas feras do Vazio saltam da escuridão para emboscar a party!", 0.03)
            press_any_key()
            
            uivador1 = spawn_enemy("uivador_vazio")
            uivador2 = spawn_enemy("uivador_vazio")
            combat = CombatSystem(self.state, [uivador1, uivador2], can_flee=False)
            if not combat.run():
                self.game_over()
            press_any_key()
            
        # Vesper Confrontation
        clear_screen()
        print_centered("=== A CÂMARA DE MAGMA ===", None)
        typewriter("Diante do caldeirão de magma profundo, Vesper flutua em meio a faíscas arroxeadas.", 0.03)
        typewriter("Vesper: \"Vocês acham que pararam Grum? Kragmoor é apenas o forno. A gravidade puxa tudo.\"", 0.03)
        typewriter("\nEla conjura um portal sombrio e desaparece no abismo vulcânico.", 0.03)
        self.state.set_flag("vesper_kragmoor_confrontada", True)
        press_any_key()
        
        # Boss Fight
        clear_screen()
        print_centered("=== O GOLEM CORROMPIDO ===", None)
        typewriter("Do tanque de lava, o guardião rúnico se ergue, coberto por minério bruto e energia cósmica.", 0.03)
        
        golem = spawn_enemy("golem_kragmoor")
        
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "VISUAL_EFFECT",
                "effect_type": "enemy_intro",
                "text": "Golem de Kragmoor",
                "color": "blood_red",
                "duration": 2500
            })
            import time
            time.sleep(2.0)
            
        if (self.state.get_flag("kragmoor_infiltrado") or
            self.state.get_flag("kragmoor_portão_erguido") or
            self.state.get_flag("kragmoor_selo_realinhado") or
            self.state.get_flag("kragmoor_purificado")):
            typewriter("\n💡 Graças à abordagem estratégica anterior, o núcleo do Golem começa danificado (-40 HP)!", 0.03)
            golem.hp -= 40
            press_any_key()
            
        combat = CombatSystem(self.state, [golem], can_flee=False)
        if not combat.run():
            self.game_over()
            
        # Crafting sequence
        clear_screen()
        print_centered("=== A RESTAURADA FORJA ANÃ ===", None)
        typewriter("O Golem desaba em blocos de minério fumegante. No chão, brilha uma Runa de Aço Negro.", 0.03)
        typewriter("Brokk retorna e seus olhos brilham ao ver a runa.", 0.03)
        typewriter("Brokk: \"Vocês salvaram a minha vida e a forja! Entreguem-me essa runa e farei a minha melhor obra!\"", 0.03)
        press_any_key()
        
        options = {
            "1": "Martelo de Brokk (Arma Lendária - Guerreiro/Clérigo)",
            "2": "Manto das Estrelas (Armadura Lendária - Mago/Ladino)",
            "3": "Lâmina do Eclipse (Arma Lendária - Ladino/Guerreiro)",
            "4": "Cetro Solar (Arma Lendária - Clérigo/Mago)"
        }
        choice = self.get_party_vote(options, prompt="Qual item lendário a party deseja forjar? ")
        
        item_id = "martelo_brokk"
        if choice == "2":
            item_id = "manto_estrelas"
        elif choice == "3":
            item_id = "lamina_eclipse"
        elif choice == "4":
            item_id = "cetro_solar"
            
        # Trigger legendary draft flow
        self.legendary_draft_flow(item_id)
        
        clear_screen()
        typewriter("Brokk: \"Uma verdadeira obra-prima! Que ela guie seus passos contra as trevas.\"", 0.03)
        press_any_key()
        
        # Transição para o Capítulo 9
        press_any_key("Pressione [ENTER] para viajar para o Gélido Silêncio...")
        self.chapter_9_start()

    def legendary_draft_flow(self, item_id: str):
        self.state.set_flag("legendary_draft_item", item_id)
        self.state.set_flag("legendary_draft_claimed_by", "")
        
        session_id = getattr(self.state, "session_id", None)
        if session_id:
            from server import active_sessions, send_to_ws_threadsafe
            session = active_sessions.get(session_id)
            if session:
                # Put all connected clients in the legendary_draft stage
                for cid in session["connected_clients"]:
                    session["client_stages"][cid] = "legendary_draft"
                
                # Broadcast the legendary draft prompt
                from engine.items import create_item
                item = create_item(item_id)
                item_name = item.name if item else "Item Lendário"
                
                session["adapter"].broadcast({
                    "type": "WAITING_INPUT",
                    "prompt": f"🎁 Brokk forjou o item lendário: {item_name}!\nDeseja equipar o item? Isso substituirá seu equipamento atual.",
                    "options": {
                        "1": f"✅ Sim, equipar o {item_name}",
                        "2": "❌ Não, passar para outro"
                    }
                })
                
                # Wait until all clients exit legendary_draft stage (someone claimed or everyone passed)
                while True:
                    stages = [session["client_stages"].get(cid, "normal") for cid in session["connected_clients"]]
                    if not any(s == "legendary_draft" for s in stages):
                        break
                    time.sleep(0.1)
                return
                
        # Fallback for single-player / test mode: directly equip it on leader
        from engine.items import create_item, ItemType
        item = create_item(item_id)
        if item:
            if item.item_type == ItemType.ARMA:
                self.player.weapon = item
            else:
                self.player.armor = item
            self.state.set_flag("legendary_draft_claimed_by", self.player.name)
