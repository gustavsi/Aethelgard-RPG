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

class Chapter4Mixin:
    def chapter_4_start(self):
        from engine.save_system import save_game
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "cerco"
        self.state.current_chapter = 4
        if self.adapter:
            self.adapter.on_state_change(self.state)
        clear_screen()
        print_centered("=== CAPÍTULO IV: O CERCO A OAKHAVEN ===", None)
        self.adapter.emit(AsciiArt(TOWN_ART))
        
        typewriter("O caminho de volta a Oakhaven está marcado por cinzas.", 0.03)
        typewriter("A cada colina vencida, o clarão no horizonte cresce. Não é o amanhecer: são as muralhas queimando.", 0.03)
        typewriter("Catapultas rugem além dos campos, e sombras se movem contra os portões.", 0.03)
        typewriter("O sino de alerta toca sem ritmo. Oakhaven, seu refúgio, está cercado por lobos.", 0.03)
        press_any_key()
        
        # Encontro com Capitã Rhea
        clear_screen()
        typewriter("A Capitã Rhea encontra o grupo perto do portão interno, com uma bandagem fresca e sangue na armadura.", 0.03)
        typewriter("\n\"Vocês chegaram no pior momento possível. O que, hoje, significa a hora certa.\"", 0.03)
        typewriter("\"Três frentes sob ataque. Se uma cair, a cidade abre. Se duas caírem, Oakhaven vira cinza antes da meia-noite.\"", 0.03)
        
        options = {
            "1": "Liderar a defesa no Portão Sul (Ideal para Guerreiro)",
            "2": "Restaurar a barreira na Torre do Mago (Ideal para Mago)",
            "3": "Impedir sabotadores no Celeiro (Ideal para Ladino)"
        }
        
        choice = self.get_party_vote(options, prompt="Onde o grupo liderará a defesa? ")
        
        if choice == "1":
            clear_screen()
            typewriter("Vocês correm em direção ao barulhento Portão Sul.", 0.03)
            if any(p.char_class == CharacterClass.GUERREIRO for p in self.party):
                typewriter("\n[Guerreiro] O grupo assume a linha de frente, pega o escudo de um soldado caído e firma os pés no barro.", 0.03)
                typewriter("Os ogros de Malakar avançam com aríetes, mas sua resiliência reorganiza os defensores.", 0.03)
                typewriter("O portão resiste com baixas mínimas. Rhea ganha tempo valioso.", 0.03)
                self.state.set_flag("portao_sul_salvo", True)
            else:
                typewriter("\nOs defensores tentam segurar a linha sem um campeão para inspirá-los.", 0.03)
                typewriter("Os ogros atingem o portão violentamente antes de recuar. Parte da muralha racha.", 0.03)
                self.consume_resource(self.player, "hp", 20, "Destroços da muralha")
                
        elif choice == "2":
            clear_screen()
            typewriter("Vocês sobem as escadas da Torre do Mago sob uma chuva de brasas.", 0.03)
            if any(p.char_class == CharacterClass.MAGO for p in self.party):
                typewriter("\n[Mago] O grupo encontra o cristal da barreira pulsando fora de ritmo, com runas invertidas.", 0.03)
                typewriter("O grupo lê o padrão, corrige a sequência de runas e usa a própria mana para canalizar o escudo rúnico.", 0.03)
                typewriter("A barreira se reergue em placas azuladas, desviando projéteis flamejantes.", 0.03)
                self.state.set_flag("torre_mago_salva", True)
            else:
                typewriter("\nSem conhecimento arcano para reconfigurar as runas, a barreira oscila e desaba.", 0.03)
                self.consume_resource(self.player, "mp", 15, "Explosão de energia mágica")
                
        else:
            clear_screen()
            typewriter("Vocês se esgueiram silenciosamente até os celeiros de mantimentos.", 0.03)
            if any(p.char_class == CharacterClass.LADINO for p in self.party):
                typewriter("\n[Ladino] O grupo nota marcas de arrombamento na porta e guias de pegadas no feno.", 0.03)
                typewriter("O grupo surpreende os sabotadores por trás antes que acendam os barris de óleo, cortando os pavios.", 0.03)
                typewriter("Os mantimentos de Oakhaven são salvos sem chamas.", 0.03)
                self.state.set_flag("celeiro_salvo", True)
            else:
                typewriter("\nVocês confrontam os sabotadores tarde demais.", 0.03)
                typewriter("Os inimigos são derrotados, mas parte dos suprimentos queima, reduzindo os recursos de Oakhaven.", 0.03)
                self.consume_resource(self.player, "gold", 30, "Suprimentos queimados")
                
        press_any_key()
        
        # Consequências especiais de aliados
        clear_screen()
        has_ally = False
        if self.state.get_flag("poupou_ogro"):
            typewriter("Um rugido conhecido atravessa o campo! Drogg, o Ogro, surge usando uma roda de carroça como escudo!", 0.03)
            typewriter("\"Drogg lembrar humano que poupou! Hoje Drogg bate em ogro errado!\"", 0.03)
            typewriter("Drogg arremessa inimigos no fosso, restaurando sua coragem e curando 30 HP.", 0.03)
            self.player.hp = min(self.player.max_hp, self.player.hp + 30)
            has_ally = True
            
        if self.state.get_flag("millhaven_salva"):
            typewriter("\nAldeões de Millhaven chegam trazendo estacas, cordas e suprimentos médicos.", 0.03)
            typewriter("\"Vocês nos deram uma manhã. Viemos pagar com esta noite!\"", 0.03)
            typewriter("O suporte médico cura o grupo em 20 HP.", 0.03)
            self.player.hp = min(self.player.max_hp, self.player.hp + 20)
            has_ally = True
            
        if not has_ally:
            typewriter("As tropas de Oakhaven lutam sozinhas e cansadas contra as ondas incessantes de atacantes.", 0.03)
            
        press_any_key()
        
        # Boss Battle - Inquisidor Sombrio
        clear_screen()
        print_centered("=== A PRAÇA DA CONDECORAÇÃO ===", None)
        typewriter("A praça central escurece de repente. O Inquisidor Sombrio surge no topo da fonte.", 0.03)
        typewriter("Correntes negras se movem ao seu redor como serpentes sob comando.", 0.03)
        typewriter("\n\"Oakhaven caiu. Vocês apenas confundem atraso com vitória!\"", 0.03)
        play_sound_effect("INQUISITOR APPARITION", None)
        self.pre_boss_menu("o Inquisidor Sombrio")
        
        boss = spawn_enemy("inquisidor_sombrio")
        
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "VISUAL_EFFECT",
                "effect_type": "enemy_intro",
                "text": "Inquisidor Sombrio",
                "color": "shadow_purple",
                "duration": 2500
            })
            import time
            time.sleep(2.0)
            
        combat = CombatSystem(self.state, [boss], can_flee=False)
        if not combat.run():
            self.game_over()
            
        clear_screen()
        typewriter("Com o Inquisidor Sombrio destruído, as correntes se desfazem em fumaça negra.", 0.03)
        typewriter("A Capitã Rhea finca sua espada no chão da praça e respira aliviada.", 0.03)
        typewriter("\n\"Contem os vivos primeiro. Depois contaremos os mortos. Hoje Oakhaven não caiu.\"", 0.03)
        typewriter("\"Mas a fonte da corrupção continua ativa. Vocês devem cruzar as Terras Corrompidas e fechar o portal final.\"", 0.03)
        
        self.state.set_flag("oakhaven_defendida", True)
        press_any_key()
        self.chapter_5_start()
