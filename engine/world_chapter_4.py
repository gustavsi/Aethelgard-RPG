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
        
        from engine.class_gate_theater import GateApproach, run_gate_theater

        def hard_siege():
            # Resource costs are applied per-approach via assist_cost when ideal class is missing.
            # Explicit hard-path vote only:
            clear_screen()
            typewriter("\nSem foco ideal, a defesa se espalha demais. As três frentes sangram.", 0.03)
            press_any_key()

        approaches = [
            GateApproach(
                "south_gate",
                "Liderar a defesa no Portão Sul (Ideal para Guerreiro)",
                CharacterClass.GUERREIRO,
                "portao_sul_salvo",
                (
                    "Vocês correm ao Portão Sul.",
                    "\n[Guerreiro] Escudos firmes no barro. Os ogros recuam. Rhea ganha tempo.",
                ),
                (
                    "Sem Guerreiro, a linha segura com improvisos — a muralha racha, mas não cai.",
                ),
                ("hp", 20, "Destroços da muralha"),
            ),
            GateApproach(
                "mage_tower",
                "Restaurar a barreira na Torre do Mago (Ideal para Mago)",
                CharacterClass.MAGO,
                "torre_mago_salva",
                (
                    "Vocês sobem a Torre sob chuva de brasas.",
                    "\n[Mago] Runas corrigidas. A barreira azul desvia o fogo.",
                ),
                (
                    "Sem Mago, alguém força o cristal à mão — a barreira sobe fraca e drena mana.",
                ),
                ("mp", 15, "Explosão de energia mágica"),
            ),
            GateApproach(
                "barn",
                "Impedir sabotadores no Celeiro (Ideal para Ladino)",
                CharacterClass.LADINO,
                "celeiro_salvo",
                (
                    "Vocês se esgueiram até os celeiros.",
                    "\n[Ladino] Pavios cortados. Mantimentos salvos sem chamas.",
                ),
                (
                    "Sem Ladino, o confronto é barulhento — parte dos grãos queima.",
                ),
                ("gold", 30, "Suprimentos queimados"),
            ),
        ]

        run_gate_theater(
            self,
            title="CERCO DE OAKHAVEN — TRÊS FRENTES",
            intro_lines=[
                "\"Três frentes sob ataque. Escolham onde liderar — o resto resiste como puder.\"",
            ],
            approaches=approaches,
            hard_path_fn=hard_siege,
            hard_path_label="Dividir a party sem foco (caminho difícil)",
        )
        
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
