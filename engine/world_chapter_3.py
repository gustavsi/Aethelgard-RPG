import random
from engine.dto import NarrativeText, ChoiceRequested, ClearScreen, PressAnyKey, SoundEffect, AsciiArt
from engine.art import TOWN_ART
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

def get_menu_choice(options, prompt="Escolha uma opção: "):
    from engine.adapter import get_adapter
    from engine.dto import ChoiceRequested
    return get_adapter().emit(ChoiceRequested(prompt, options))

class Chapter3Mixin:
    def chapter_3_start(self):
        from engine.save_system import save_game
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "millhaven"
        self.state.current_chapter = 3
        if self.adapter:
            self.adapter.on_state_change(self.state)
        clear_screen()
        print_centered("=== CAPÍTULO III: VILA DE MILLHAVEN ===", None)
        self.adapter.emit(AsciiArt(TOWN_ART))
        
        typewriter("A estrada para Millhaven abandona qualquer sinal de vida antes mesmo de chegar aos portões.", 0.03)
        typewriter("Casas fechadas observam o grupo com janelas pregadas por dentro, e uma névoa roxa escorre pelas ruas.", 0.03)
        typewriter("No centro da vila, o sino da capela balança sozinho, mas não emite som algum.", 0.03)
        typewriter("A lua cheia parece grande demais sobre os telhados, branca como um olho doente.", 0.03)
        press_any_key()
        
        # Encontro com Padre Elias
        clear_screen()
        typewriter("Vocês encontram Padre Elias ajoelhado diante da capela.", 0.03)
        typewriter("Ele é idoso, cego, vestido com panos brancos gastos, e segura um símbolo sagrado rachado.", 0.03)
        typewriter("Apesar dos olhos esbranquiçados, ele vira o rosto exatamente na direção de vocês.", 0.03)
        typewriter("\n\"A roda enfim rangeu até minha porta. Entrem, viajantes. A noite já pronunciou seu nome.\"", 0.03)
        
        options = {
            "1": "\"Você me conhece?\"",
            "2": "\"A vila está sob maldição. Que tipo de ritual causou isso?\"",
            "3": "\"Onde está o inimigo?\""
        }
        
        choice = self.get_party_vote(options, prompt="O que perguntar? ")
        
        if choice == "1":
            typewriter("\n\"Não como homens conhecem rostos. Conheço vocês como o sino conhece o vento: pelo peso que trazem.\"", 0.03)
        elif choice == "2":
            typewriter("\n\"Ritual é palavra pequena. Isto é uma raiz. Foi plantada quando Veyr Malakar, o Nome Primeiro, recusou a morte e pediu ao vazio que lhe ensinasse a permanecer.\"", 0.03)
            typewriter("\"Veyr Malakar é o homem que queimou a própria alma para que a máscara nunca caísse.\"", 0.03)
        else:
            typewriter("\n\"O inimigo está no altar, na rua, no porão, no berço. Ele veste a pele dos lugares que desistiram de resistir.\"", 0.03)
            
        typewriter("\n\"Uma vela ainda arde quando a cera já chora. Salve a criança na casa do poço, e Millhaven talvez lembre como se respira.\"", 0.03)
        typewriter("\"Mas cuidado. O santo que a guarda caiu antes de vocês chegarem. Agora ele marcha com a espada baixa e a auréola suja.\"", 0.03)
        press_any_key()
        
        # A Criança Corrompida
        clear_screen()
        typewriter("Vocês entram na casa do poço no fim da rua principal.", 0.03)
        typewriter("No quarto superior, vocês encontram uma criança sentada de costas, cantando uma cantiga antiga.", 0.03)
        typewriter("A pele dela está fria e marcada por veios roxos. Brinquedos quebrados flutuam ao redor.", 0.03)
        typewriter("\nPadre Elias sussurra na entrada: \"Não a fira. O mal a usa como lamparina.\"", 0.03)
        
        child_options = {}
        # Cleric class gate!
        if any(p.char_class == CharacterClass.CLERIGO for p in self.party):
            child_options["1"] = "[Clérigo] Purificar a criança (Sacrificar 15 HP e 10 MP para absorver a corrupção)"
            
        child_options["2"] = "Tentar conter a criança usando força de vontade"
        child_options["3"] = "Ignorar a criança e seguir direto para a capela"
        
        child_choice = self.get_party_vote(child_options, prompt="A decisão da party: ")
        
        if child_choice == "1":
            clear_screen()
            typewriter("Vocês se ajoelham no círculo de brinquedos flutuantes.", 0.03)
            typewriter("\"Eu não vim expulsar uma sombra com violência. Vim lembrar esta casa de que ela já teve amanhecer.\"", 0.03)
            typewriter("\nA criança vira o rosto. Seus olhos são negros, cheios de lágrimas.", 0.03)
            typewriter("\"Ele disse que, se eu dormir, meus pais voltam...\"", 0.03)
            typewriter("\nO Clérigo responde: \"Ele mentiu. Mas se você acordar, eu fico até o medo passar.\"", 0.03)
            
            typewriter("\nA névoa roxa engrossa, vozes imitam seus entes queridos pedindo para o grupo desistir.", 0.03)
            typewriter("Vocês erguem o símbolo rachado de Padre Elias e seu próprio cajado sagrado, brilhando intensamente.", 0.03)
            typewriter("\"Pela chama que resta nos lares vazios, pela vida que ainda não aprendeu a se defender: saia dela!\"", 0.03)
            
            play_sound_effect("HOLY PURIFICATION", None)
            self.consume_resource(self.player, "hp", 15, "Purificação da criança")
            self.consume_resource(self.player, "mp", 10, "Purificação da criança")
            self.state.set_flag("millhaven_salva", True)
            
            typewriter("\nA corrupção explode e se dissipa. A criança desaba chorando nos seus braços, livre da possessão.", 0.03)
            typewriter("\"Obrigado... O cavaleiro negro está na capela. Ele quer matar a luz que sobrou.\"", 0.03)
        else:
            clear_screen()
            typewriter("Vocês tentam conter a criança, mas a névoa escura se infiltra nas paredes.", 0.03)
            typewriter("A voz de Malakar fala diretamente pela boca da criança:", 0.03)
            typewriter("\"Tarde demais. A porta abriu por dentro.\"", 0.03)
            self.state.set_flag("millhaven_perdida", True)
            typewriter("\nA criança volta a cantar, e cada nota faz a casa ranger como um caixão fechando.", 0.03)
            
        press_any_key()
        
        # Confronto com Paladino Corrompido
        clear_screen()
        print_centered("=== A CAPELA PROFANADA ===", None)
        typewriter("Na capela, diante do altar de Millhaven, o Paladino Corrompido aguarda de joelhos.", 0.03)
        typewriter("Sua armadura negra reflete as velas roxas, e uma auréola de ferro quebrada gira atrás de seu elmo.", 0.03)
        typewriter("Ele se levanta vagarosamente, arrastando sua espada negra pelo chão de pedra.", 0.03)
        typewriter("\n\"Ajoelhem-se, ou vejam como a fé soa ao quebrar!\"", 0.03)
        play_sound_effect("PALADIN CHALLENGE", None)
        self.pre_boss_menu("o Paladino Corrompido")
        
        # Boss Battle
        boss = spawn_enemy("paladino_corrompido")
        
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "VISUAL_EFFECT",
                "effect_type": "enemy_intro",
                "text": "Paladino Corrompido",
                "color": "shadow_purple",
                "duration": 2500
            })
            import time
            time.sleep(2.0)
            
        combat = CombatSystem(self.state, [boss], can_flee=False)
        if not combat.run():
            self.game_over()
            
        clear_screen()
        if self.state.get_flag("millhaven_salva"):
            typewriter("Padre Elias toca o sino da capela. Desta vez ele soa real. Portas de casas se abrem aos poucos.", 0.03)
            typewriter("Os aldeões sobreviventes saem de seus esconderijos, com medo, mas finalmente respirando livremente.", 0.03)
            typewriter("O grupo recebe 100 de Ouro como agradecimento da vila sagrada.", 0.03)
            self.player.gold += 100
        else:
            typewriter("A névoa continua escura. A cantiga da criança ecoa nos ouvidos de vocês enquanto deixam a vila.", 0.03)
            typewriter("Millhaven foi consumida pelo vazio, mas vocês carregam o conhecimento necessário para seguir em frente.", 0.03)
            
        press_any_key()
        self.chapter_4_start()
