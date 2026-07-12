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

class Chapter7Mixin:
    def chapter_7_start(self):
        from engine.save_system import save_game
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "vaelmoor"
        self.state.current_chapter = 7
        if self.adapter:
            self.adapter.on_state_change(self.state)
            
        clear_screen()
        print_centered("=== CAPÍTULO VII: O PORTO DE VAELMOOR ===", None)
        
        typewriter("O cheiro de sal e óleo de baleia anuncia Vaelmoor antes que vocês a vejam.", 0.03)
        typewriter("É uma cidade de madeira empilhada sobre madeira, guindastes rangendo, e gaivotas gritando.", 0.03)
        typewriter("Nos becos, uma tatuagem de onda negra aparece em mais de um pulso apressado.", 0.03)
        self.request_party_ready()
        press_any_key()
        
        # Encontro com Capitã Ysolde
        clear_screen()
        print_centered("=== A DOCA DE ANCORAGEM ===", None)
        typewriter("Uma mulher de casaco comprido e cicatriz no queixo observa o porto com os braços cruzados.", 0.03)
        typewriter("É a Capitã Ysolde, corsária e mestra do porto de Vaelmoor.", 0.03)
        typewriter("\nYsolde: \"Não me interessa política de deuses mortos, viajantes.\"", 0.03)
        typewriter("\"Me interessa que minha cidade não afunde por causa de uma caixa que ninguém quis abrir.\"", 0.03)
        typewriter("\"A facção Maré Negra está contrabandeando algo envolto em correntes no Armazém 7.\"", 0.03)
        typewriter("\"Ajudem-me a descobrir o que é, e eu ajudo vocês a chegar mais rápido a onde quer que estejam indo.\"", 0.03)
        press_any_key()
        
        # Class Gate - Abordagem ao Armazém 7
        clear_screen()
        print_centered("=== O CLASS GATE DO ARMAZÉM 7 ===", None)
        typewriter("O Armazém 7 é vigiado de perto por guardas armados da Maré Negra.", 0.03)
        typewriter("Como vocês decidem entrar?", 0.03)
        
        options = {}
        if any(p.char_class == CharacterClass.LADINO for p in self.party):
            options["1"] = "[Ladino] Infiltrar-se silenciosamente pelos telhados"
        if any(p.char_class == CharacterClass.GUERREIRO for p in self.party):
            options["2"] = "[Guerreiro] Desafiar o capanga da Maré Negra para um duelo de honra"
        if any(p.char_class == CharacterClass.MAGO for p in self.party):
            options["3"] = "[Mago] Identificar e desativar os selos rúnicos da caixa"
        if any(p.char_class == CharacterClass.CLERIGO for p in self.party):
            options["4"] = "[Clérigo] Sentir e purificar a corrupção do Vazio nos tripulantes"
        options["5"] = "Invasão direta por força bruta (Caminho Difícil)"
        
        choice = self.get_party_vote(options, prompt="Qual abordagem a party escolhe? ")
        
        if choice == "1" and any(p.char_class == CharacterClass.LADINO for p in self.party):
            clear_screen()
            typewriter("[Ladino] Com agilidade silenciosa, o Ladino escala as vigas e desarma os vigias do telhado.", 0.03)
            typewriter("Vocês entram no armazém sem disparar nenhum alarme e pegam as patrulhas desprevenidas.", 0.03)
            self.state.set_flag("vaelmoor_infiltrado", True)
            press_any_key()
        elif choice == "2" and any(p.char_class == CharacterClass.GUERREIRO for p in self.party):
            clear_screen()
            typewriter("[Guerreiro] O Guerreiro avança e desafia o campeão local da Maré Negra para um duelo.", 0.03)
            typewriter("Com golpes brutais e precisos, o Guerreiro derrota o capanga rapidamente. Intimidados, os outros recuam.", 0.03)
            self.state.set_flag("vaelmoor_duelo_vencido", True)
            press_any_key()
        elif choice == "3" and any(p.char_class == CharacterClass.MAGO for p in self.party):
            clear_screen()
            typewriter("[Mago] O Mago detecta as runas de alarme que cercam a entrada e as enfraquece com contra-feitiços.", 0.03)
            typewriter("As runas defensivas do Vazio se dissipam silenciosamente sob o controle do Mago.", 0.03)
            self.state.set_flag("vaelmoor_selo_identificado", True)
            press_any_key()
        elif choice == "4" and any(p.char_class == CharacterClass.CLERIGO for p in self.party):
            clear_screen()
            typewriter("[Clérigo] O Clérigo sente a corrupção fria do Vazio exalando do armazém e entoa preces protetoras.", 0.03)
            typewriter("A luz sagrada purifica a névoa do Vazio, revelando as emboscadas preparadas e enfraquecendo os guardas.", 0.03)
            self.state.set_flag("vaelmoor_corrupcao_sentida", True)
            press_any_key()
        else:
            clear_screen()
            typewriter("Sem uma estratégia sutil, vocês arrombam as portas da frente do Armazém 7!", 0.03)
            typewriter("O alarme soa imediatamente e duas sentinelas armadas da Maré Negra avançam contra a party!", 0.03)
            press_any_key()
            
            pirata1 = spawn_enemy("pirata_mare_negra")
            pirata2 = spawn_enemy("pirata_mare_negra")
            combat = CombatSystem(self.state, [pirata1, pirata2], can_flee=False)
            if not combat.run():
                self.game_over()
            press_any_key()
            
        # Confronto com Vesper
        clear_screen()
        print_centered("=== O ARREPIANTE AVISO ===", None)
        typewriter("No fundo do armazém, cercada por caixas lacradas, uma mulher com máscara cinza observa a party.", 0.03)
        typewriter("É Vesper, a Arauto do Vazio.", 0.03)
        typewriter("\nVesper: \"Vocês mataram um homem que carregava um fardo pesado demais para vocês entenderem.\"", 0.03)
        typewriter("\"Não vão gostar do que sai de baixo dele.\"", 0.03)
        typewriter("\nVesper chuta uma alavanca e desaparece através de um alçapão antes que possam atacá-la.", 0.03)
        self.state.set_flag("vesper_confrontada", True)
        press_any_key()
        
        # Boss Grum
        clear_screen()
        print_centered("=== O INVIOLÁVEL CÁCERE DE GRUM ===", None)
        typewriter("Atrás da cortina, o gigante que guardava a carga se ergue das profundezas da água poluída do porto.", 0.03)
        typewriter("É o Contramestre Grum, o Afogado. Suas carnes estão cobertas por cracas roxas pulsando com o Vazio.", 0.03)
        typewriter("\nGrum: \"O Vazio reclama tudo. Afundem com as docas!\"", 0.03)
        play_sound_effect("VOID SPLASH", None)
        self.pre_boss_menu("o Contramestre Grum, o Afogado")
        
        grum = spawn_enemy("grum_afogado")
        
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "VISUAL_EFFECT",
                "effect_type": "enemy_intro",
                "text": "Contramestre Grum",
                "color": "blood_red",
                "duration": 2500
            })
            import time
            time.sleep(2.0)
            
        # Se um class gate foi bem sucedido, enfraquecemos o Boss Grum
        if (self.state.get_flag("vaelmoor_infiltrado") or 
            self.state.get_flag("vaelmoor_duelo_vencido") or 
            self.state.get_flag("vaelmoor_selo_identificado") or 
            self.state.get_flag("vaelmoor_corrupcao_sentida")):
            typewriter("\n💡 Graças à abordagem estratégica da party, Grum começa a batalha enfraquecido (-40 HP)!", 0.03)
            grum.hp -= 40
            press_any_key()
            
        combat = CombatSystem(self.state, [grum], can_flee=False)
        if not combat.run():
            self.game_over()
            
        clear_screen()
        print_centered("=== A CALMARIA DAS DOCAS ===", None)
        typewriter("Grum cai de joelhos, dissolvendo-se em uma poça de água negra e cracas marinhas sem brilho.", 0.03)
        typewriter("O artefato nas correntes racha, revelando um brilho roxo fraco mas faminto. A ameaça foi contida temporariamente.", 0.03)
        typewriter("\nCapitã Ysolde entra no armazém e olha para os restos do monstro.", 0.03)
        typewriter("Ysolde: \"Vocês limparam as minhas docas de uma sujeira perigosa. Vocês têm a minha gratidão e meu respeito.\"", 0.03)
        press_any_key()
                
        # Trigger the optional Ysolde side quest flow
        self.ysolde_side_quest_flow()
        
        # Transition to Chapter 8
        press_any_key("Pressione [ENTER] para viajar para as Minas de Kragmoor...")
        self.chapter_8_start()

    def ysolde_side_quest_flow(self):
        from engine.side_quests import SideQuest
        from engine.dto import NarrativeText
        
        def reward_ysolde(w):
            w.player.gold += 150
            w.state.set_flag("capitã_ysolde_aliada", True)
            
        quest = SideQuest(
            "ysolde_carga",
            "Carga Recuperada no Porto",
            "Recupere a carga de suprimentos da Capitã Ysolde nas docas leste.",
            "Capitã Ysolde",
            reward_fn=reward_ysolde
        )
        
        flag_active = "sidequest_ysolde_carga_ativa"
        flag_completed = "sidequest_ysolde_carga_concluida"
        
        if self.state.get_flag(flag_completed):
            typewriter("\nYsolde: \"Obrigada novamente por recuperar a minha carga. Vaelmoor está em segurança por enquanto.\"", 0.03)
            return
            
        if self.state.get_flag(flag_active):
            options = {
                "1": "Entregar a carga recuperada para Ysolde",
                "2": "Continuar procurando"
            }
            choice = self.get_party_vote(options, prompt="O que fazer com a missão ativa? ")
            if choice == "1":
                clear_screen()
                typewriter("Vocês entregam a caixa de suprimentos recuperada intacta para a Capitã.", 0.03)
                quest.complete(self, lambda msg: self.adapter.emit(NarrativeText(msg)))
                
                recruit_opt = {
                    "1": "Recrutar Capitã Ysolde como companheira da party",
                    "2": "Despedir-se e seguir viagem"
                }
                rec_choice = self.get_party_vote(recruit_opt, prompt="Recrutar Ysolde? ")
                if rec_choice == "1":
                    typewriter("\nYsolde sorri e limpa o casaco: \"Uma boa tripulação é difícil de achar. Vamos ver do que vocês são capazes na estrada.\"", 0.03)
                    from engine.companion import get_companion
                    self.player.companion = get_companion("ysolde")
                    press_any_key()
            return

        typewriter("\nYsolde: \"Temos um problema adicional. Durante o tumulto, uma carga de suprimentos cruciais caiu no canal leste, e a Maré Negra contratou capangas locais para pegá-la.\"", 0.03)
        typewriter("\"Vocês poderiam me ajudar a recuperar essa carga antes deles?\"", 0.03)
        
        options = {
            "1": "Aceitar a missão (Recuperar a carga)",
            "2": "Recusar a missão e seguir viagem"
        }
        choice = self.get_party_vote(options, prompt="Escolha uma opção: ")
        
        if choice == "1":
            clear_screen()
            quest.accept(self, lambda msg: self.adapter.emit(NarrativeText(msg)))
            typewriter("\nYsolde: \"Excelente. Estarei esperando aqui pelas docas leste. Não deixem que a Maré Negra a pegue primeiro.\"", 0.03)
            press_any_key()
            self.ysolde_side_quest_recovery_combat()
        else:
            typewriter("\nYsolde: \"Compreendo. Vocês têm o seu próprio fardo para carregar. Boa viagem, estrangeiros.\"", 0.03)
            press_any_key()

    def ysolde_side_quest_recovery_combat(self):
        clear_screen()
        print_centered("=== DOCAS LESTE DE VAELMOOR ===", None)
        typewriter("Vocês seguem até o canal leste. Na beira do cais, veem piratas da Maré Negra içando a caixa de Ysolde!", 0.03)
        typewriter("\nPirata: \"Olha só o que pescamos! E parece que temos companhia... Matem-nos e fiquem com a carga!\"", 0.03)
        press_any_key()
        
        pirata = spawn_enemy("pirata_mare_negra")
        combat = CombatSystem(self.state, [pirata], can_flee=False)
        if not combat.run():
            self.game_over()
            
        clear_screen()
        typewriter("Vocês derrotam o pirata e resgatam a carga de suprimentos de Ysolde!", 0.03)
        typewriter("\nRetornem à Doca de Ancoragem e falem com Ysolde para entregar a carga.", 0.03)
        press_any_key()
        
        self.ysolde_side_quest_flow()
