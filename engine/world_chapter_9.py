import random
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

class Chapter9Mixin:
    def chapter_9_start(self):
        from engine.save_system import save_game
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "gelido"
        self.state.current_chapter = 9
        if self.adapter:
            self.adapter.on_state_change(self.state)

        clear_screen()
        print_centered("=== CAPÍTULO IX: O GÉLIDO SILÊNCIO ===", None)

        typewriter("A jornada leva vocês para os cumes mais elevados e congelados do norte.", 0.03)
        typewriter("O ar é rarefeito, a nevasca é implacável e o silêncio é absoluto.", 0.03)
        typewriter("O vento congelante carrega sussurros estranhos vindos das sombras roxas na neve.", 0.03)
        self.request_party_ready()
        press_any_key()

        # Encontro com Xamã Kaelen
        clear_screen()
        print_centered("=== O ACAMPAMENTO DOS ANCESTRAIS ===", None)
        typewriter("Vocês encontram um ancião bárbaro, cego pelos ventos frios, cujos olhos agora brilham com um tom pálido do Vazio.", 0.03)
        typewriter("É o Xamã Kaelen, o último guardião do selo do norte.", 0.03)
        typewriter("\nKaelen: \"Viajantes, a bruxa de máscara cinza derreteu o gelo do selo com o calor do próprio caos.\"", 0.03)
        typewriter("\"A Fenda do Gelo está aberta e o Uivador está livre. Se a fera não for contida, a nevasca corrompida consumirá todo o norte.\"", 0.03)
        press_any_key()

        # Class Gate
        self.chapter_9_class_gate()

    def chapter_9_class_gate(self):
        from engine.cartographer import apply_cartographer_check, narrate_cartographer
        from engine.class_gate_theater import GateApproach, run_gate_theater
        from engine.constants import CharacterClass

        apply_cartographer_check(self)
        narrate_cartographer(self)

        def hard_path():
            clear_screen()
            typewriter("\nSem a especialidade ideal, a party enfrenta a fúria total do cume congelado!", 0.03)
            typewriter("A nevasca penetra em suas armaduras e espectros gélidos cercam o grupo!", 0.03)
            press_any_key()
            self.gelido_extra_combat()
            self.state.set_flag("cold_debuff_active", True)

        approaches = [
            GateApproach(
                "totem",
                "🛡️ Guerreiro: Erguer o totem ancestral de pedra como quebra-vento",
                CharacterClass.GUERREIRO,
                "gelido_totem_erguido",
                (
                    "\n🛡️ Com sua força titânica, o Guerreiro ergue e estabiliza o antigo totem de pedra!",
                    "O totem serve como quebra-vento. A party sobe em segurança.",
                ),
                (
                    "Sem um Guerreiro, o grupo improvisa alavancas e cordas — o totem sobe, mas alguém se machuca.",
                ),
                None,  # hard path = combat/debuff (no extra resource cost here)
            ),
            GateApproach(
                "melt",
                "🔥 Mago: Derreter a muralha de gelo com chamas arcanas",
                CharacterClass.MAGO,
                "gelido_gelo_derretido",
                (
                    "\n🔥 O Mago derrete e fragmenta a barreira de gelo eterno!",
                    "Uma brisa quente suaviza o frio severo.",
                ),
                (
                    "Sem um Mago, a barreira não cede — a party enfrenta o cume exposto.",
                ),
                None,
            ),
            GateApproach(
                "trail",
                "👣 Ladino: Seguir trilha oculta evitando patrulhas",
                CharacterClass.LADINO,
                "gelido_trilha_furtiva",
                (
                    "\n👣 O Ladino lidera por pegadas antigas na neve!",
                    "O grupo desvia de fendas e espectros.",
                ),
                (
                    "Sem um Ladino, a trilha se perde na nevasca.",
                ),
                None,
            ),
            GateApproach(
                "altar",
                "✨ Clérigo: Purificar o altar da nevasca",
                CharacterClass.CLERIGO,
                "gelido_totem_purificado",
                (
                    "\n✨ O Clérigo purifica as runas do altar!",
                    "A luz sagrada afasta a nevasca do Vazio.",
                ),
                (
                    "Sem um Clérigo, o altar permanece corrompido.",
                ),
                None,
            ),
        ]

        run_gate_theater(
            self,
            title="A SUBIDA DA MONTANHA",
            intro_lines=[
                "Uma imensa muralha de gelo eterno e ventos cortantes bloqueia a trilha para o cume.",
                "Como a party pretende superar essa barreira?",
            ],
            approaches=approaches,
            hard_path_fn=hard_path,
            hard_path_label="❄️ Seguir pelo caminho difícil (sem especialidade)",
        )

        self.chapter_9_vesper_confrontation()

    def gelido_extra_combat(self):
        espectro = spawn_enemy("espectro_gelo")
        combat = CombatSystem(self.state, [espectro], can_flee=False)
        if not combat.run():
            self.game_over()
        clear_screen()
        typewriter("\nVocês derrotam o espectro, mas o frio severo congelou seus ossos.", 0.03)
        press_any_key()

    def chapter_9_vesper_confrontation(self):
        try:
            from engine.vesper_intel import run_vesper_interlude
            run_vesper_interlude(self, context="gelido")
        except Exception:
            pass
        clear_screen()
        print_centered("=== A FENDA DO GELO ===", None)
        typewriter("No topo do cume gélido, uma fenda vertical rasga o espaço, brilhando com chamas roxas congelantes.", 0.03)
        typewriter("Diante dela está Vesper, flutuando levemente sobre a neve.", 0.03)
        typewriter("\nVesper: \"Vocês carregam as relíquias de Brokk como se fossem heróis.\"", 0.03)
        typewriter("\"Mas o aço comum não pode consertar o que a própria alma do mundo deseja rasgar.\"", 0.03)
        typewriter("\"Sintam a dor do silêncio!\"", 0.03)
        
        self.state.set_flag("vesper_gelido_confrontada", True)
        press_any_key()
        self.chapter_9_boss_fight()

    def chapter_9_boss_fight(self):
        clear_screen()
        print_centered("=== O CONFRONTO CONTRA O UIVADOR ===", None)
        
        uivador = spawn_enemy("uivador_vazio")
        
        # Debuff / Buff applications
        has_gate_buff = (
            self.state.get_flag("gelido_totem_erguido") or
            self.state.get_flag("gelido_gelo_derretido") or
            self.state.get_flag("gelido_trilha_furtiva") or
            self.state.get_flag("gelido_totem_purificado")
        )
        if has_gate_buff:
            typewriter("\n💡 Graças à abordagem estratégica anterior, o Uivador do Vazio começa enfraquecido (-50 HP)!", 0.03)
            uivador.hp -= 50
            press_any_key()
            
        if self.state.get_flag("cold_debuff_active"):
            typewriter("\n❄️ Devido ao frio extremo da nevasca, toda a party começa o combate ferida (-20 HP)!", 0.03)
            for p in self.party:
                p.hp = max(1, p.hp - 20)
            press_any_key()

        combat = CombatSystem(self.state, [uivador], can_flee=False)
        if not combat.run():
            self.game_over()

        # Victory narrative
        clear_screen()
        print_centered("=== A FERA ADORMECIDA ===", None)
        typewriter("O Uivador do Vazio solta um último suspiro congelante e desaba sobre a neve antiga.", 0.03)
        typewriter("As chamas roxas da Fenda começam a vacilar, mas não se apagam por completo.", 0.03)
        press_any_key()
        self.ulfgar_side_quest_flow()

    def ulfgar_side_quest_flow(self):
        from engine.side_quests import SideQuest
        
        def reward_ulfgar(w):
            w.player.gold += 150
            from engine.items import create_item
            item = create_item("minerio_gelo_eterno")
            if item:
                w.player.inventory.append(item)
                typewriter(f"\nO grupo recebeu: {item.get_colored_name()}!", 0.03)
            w.state.set_flag("ulfgar_ajudado", True)

        quest = SideQuest(
            "coracao_gelo",
            "O Coração de Gelo",
            "Recupere o pingente Coração de Gelo roubado por um Lobo do Gelo nas cavernas.",
            "Ulfgar",
            reward_fn=reward_ulfgar
        )

        flag_active = "sidequest_coracao_gelo_ativa"
        flag_completed = "sidequest_coracao_gelo_concluida"

        if self.state.get_flag(flag_completed):
            typewriter("\nUlfgar: \"Obrigado novamente por recuperar o Coração de Gelo da minha família.\"", 0.03)
            return

        if self.state.get_flag(flag_active):
            options = {
                "1": "Entregar o Coração de Gelo para Ulfgar",
                "2": "Continuar procurando"
            }
            choice = self.get_party_vote(options, prompt="O que fazer com a missão ativa? ")
            if choice == "1":
                clear_screen()
                typewriter("Vocês entregam o pingente sagrado para Ulfgar.", 0.03)
                quest.complete(self, lambda msg: self.adapter.emit(NarrativeText(msg)))
                
                recruit_opt = {
                    "1": "Recrutar Ulfgar como companheiro da party",
                    "2": "Despedir-se e seguir viagem"
                }
                rec_choice = self.get_party_vote(recruit_opt, prompt="Recrutar Ulfgar? ")
                if rec_choice == "1":
                    typewriter("\nUlfgar sorri tristemente: \"Meu arco e meu conhecimento destas montanhas agora são de vocês. Vamos colocar fim a essa corrupção.\"", 0.03)
                    self.recruit_companion("ulfgar")
                    press_any_key()
            return

        typewriter("\nUlfgar: \"Estrangeiros, a nevasca enfraqueceu, mas as cavernas adjacentes ainda estão repletas de perigos.\"", 0.03)
        typewriter("\"Lobos do Gelo Ancestrais roubaram o pingente 'Coração de Gelo' da minha família durante a invasão do Vazio.\"", 0.03)
        typewriter("\"Poderiam me ajudar a recuperá-lo?\"", 0.03)

        options = {
            "1": "Aceitar a missão (Recuperar o Coração de Gelo)",
            "2": "Recusar a missão e seguir viagem"
        }
        choice = self.get_party_vote(options, prompt="Escolha uma opção: ")

        if choice == "1":
            clear_screen()
            quest.accept(self, lambda msg: self.adapter.emit(NarrativeText(msg)))
            typewriter("\nUlfgar: \"Muito obrigado. As cavernas de gelo ficam logo a leste. Eu aguardo aqui.\"", 0.03)
            press_any_key()
            self.ulfgar_side_quest_combat()
        else:
            typewriter("\nUlfgar: \"Compreendo. Que os espíritos da montanha protejam sua jornada.\"", 0.03)
            press_any_key()
            self.chapter_9_end()

    def ulfgar_side_quest_combat(self):
        clear_screen()
        print_centered("=== CAVERNA CONGELADA LESTE ===", None)
        typewriter("Vocês entram em uma caverna cheia de estalactites de gelo. Um Lobo do Gelo enorme rosna protegendo um pingente azul!", 0.03)
        press_any_key()

        lobo = spawn_enemy("lobo_gelo_quest")
        combat = CombatSystem(self.state, [lobo], can_flee=False)
        if not combat.run():
            self.game_over()

        clear_screen()
        typewriter("Vocês derrotam o Lobo do Gelo e recuperam o pingente Coração de Gelo!", 0.03)
        typewriter("\nRetornem ao acampamento e falem com Ulfgar para entregar a missão.", 0.03)
        press_any_key()
        self.ulfgar_side_quest_flow()
        self.chapter_9_end()

    def chapter_9_end(self):
        clear_screen()
        print_centered("=== FIM DO CAPÍTULO IX ===", None)
        typewriter("Com a fera derrotada e as montanhas em silêncio parcial, o norte respira.", 0.03)
        typewriter("O destino final contra Vesper nas Ruínas de Vaelthir aproxima-se...", 0.03)
        press_any_key("Pressione [ENTER] para ver os créditos...")
        self.credits()
