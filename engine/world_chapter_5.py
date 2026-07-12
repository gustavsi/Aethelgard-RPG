import random
from engine.dto import NarrativeText, ChoiceRequested, ClearScreen, PressAnyKey, SoundEffect, AsciiArt
from engine.art import TEMPLE_ART, VICTORY_ART
from engine.enemy import spawn_enemy, Enemy
from engine.combat import CombatSystem
from engine.constants import CharacterClass, StatusEffect, AIType

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

class Chapter5Mixin:
    def chapter_5_start(self):
        from engine.save_system import save_game
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "corrompidas"
        self.state.current_chapter = 5
        if self.adapter:
            self.adapter.on_state_change(self.state)
        clear_screen()
        print_centered("=== CAPÍTULO V: AS TERRAS CORROMPIDAS ===", None)
        self.adapter.emit(AsciiArt(TEMPLE_ART))
        
        typewriter("A estrada deixa de parecer estrada e se torna uma cicatriz.", 0.03)
        typewriter("O solo das Terras Corrompidas é vermelho, rachado e quente, como se respirasse febre.", 0.03)
        typewriter("Árvores carbonizadas se inclinam todas na mesma direção.", 0.03)
        typewriter("Ao longe, uma fortaleza negra parece mudar de lugar sempre que o grupo pisca.", 0.03)
        press_any_key()
        
        # Evento 1 - Acampamento de Sobreviventes
        clear_screen()
        typewriter("Vocês encontram um pequeno acampamento escondido atrás de rochas vermelhas.", 0.03)
        typewriter("Famílias exaustas, um guarda ferido e crianças famintas tentam sobreviver ao vento de cinzas.", 0.03)
        typewriter("O líder deles implora por ajuda para atravessar uma ravina patrulhada pelas forças de Malakar.", 0.03)
        
        options = {
            "1": "Ajudar os sobreviventes a atravessar com segurança (Gasta energia física: Custo 15 HP)",
            "2": "Negar ajuda e seguir viagem direto para a fortaleza"
        }
        
        choice = self.get_party_vote(options, prompt="A decisão da party: ")
        if choice == "1":
            typewriter("\nVocês desviam pelas patrulhas carregando feridos. O esforço debilita a saúde de vocês, mas eles chegam em segurança.", 0.03)
            typewriter("Daren, um dos sobreviventes, promete espalhar alertas e ajudar no que puder.", 0.03)
            self.consume_resource(self.player, "hp", 15, "Ajudar sobreviventes")
            self.state.set_flag("ajudou_sobreviventes", True)
        else:
            typewriter("\nVocês decidem focar na urgência de parar Malakar. Os pedidos de ajuda morrem no vento atrás de vocês.", 0.03)
            typewriter("Mais tarde, vocês encontram destroços da patrulha e uma fita de cabelo infantil presa a um galho queimado.", 0.03)
            self.state.set_flag("ignorou_sobreviventes", True)
            
        press_any_key()
        
        # Evento 2 - Santuário Profanado
        clear_screen()
        typewriter("Vocês passam por um antigo santuário quebrado, semi-enterrado sob cinzas vermelhas.", 0.03)
        typewriter("Três pilares cercam um mosaico destruído representando um abismo e uma figura coroada.", 0.03)
        
        if any(p.char_class == CharacterClass.MAGO for p in self.party):
            typewriter("\n[Mago] Os olhos arcanos do Mago decifram os restos das inscrições ancestrais.", 0.03)
            typewriter("O grupo compreende a verdade: Veyr Malakar dividiu sua imortalidade em três selos arcanos:", 0.03)
            typewriter("1. Sangue (a linhagem inocente - que se manifestou em Millhaven).", 0.03)
            typewriter("2. Fé (o juramento do cavaleiro - o Paladino Corrompido).", 0.03)
            typewriter("3. Chama (o portal rúnico da fortaleza final).", 0.03)
            typewriter("Essa revelação fortalece a compreensão de vocês do combate final.", 0.03)
            self.state.set_flag("revelacao_selos", True)
        else:
            typewriter("\nVocês veem apenas ruínas e runas ilegíveis. Vocês sabem que o local guarda segredos de Malakar, mas não conseguem lê-los.", 0.03)
            
        press_any_key()
        
        # Evento 3 - Emboscada de Assassinos
        clear_screen()
        typewriter("O caminho afunila entre duas paredes rochosas de basalto.", 0.03)
        
        if any(p.char_class == CharacterClass.LADINO for p in self.party):
            typewriter("\n[Ladino] Os instintos do Ladino alertam para fios de gatilho ocultos no pó de cinza.", 0.03)
            typewriter("Vocês sinalizam para parar e contornam a ravina, surpreendendo os assassinos de Malakar pelas costas!", 0.03)
            typewriter("O grupo desfere um golpe de emboscada antes de começarem a lutar!", 0.03)
            assassino1 = spawn_enemy("assassino_malakar")
            assassino2 = spawn_enemy("assassino_malakar")
            # Advantage: start them with lower HP
            assassino1.hp -= 25
            assassino2.hp -= 25
        else:
            typewriter("\nVocês pisam em um fio de armadilha oculto! Dardos venenosos disparam das rochas!", 0.03)
            self.consume_resource(self.player, "hp", 25, "Armadilha de dardos venenosos")
            assassino1 = spawn_enemy("assassino_malakar")
            assassino2 = spawn_enemy("assassino_malakar")
            
        combat = CombatSystem(self.state, [assassino1, assassino2], can_flee=False)
        if not combat.run():
            self.game_over()
            
        press_any_key()
        
        # Se Lacre Sombrio
        if self.state.get_flag("lacre_sombrio"):
            clear_screen()
            typewriter("O Lacre das Sombras no peito de vocês arde violentamente.", 0.03)
            typewriter("A realidade desmorona por um segundo. A voz de Lorde Malakar ressoa na mente de vocês:", 0.03)
            typewriter("\n\"Vocês carregam uma lasca da porta que fingem querer fechar.\"", 0.03)
            typewriter("\"O lacre sabe que vocês já usaram as trevas quando a luz falhou. Venham a mim e governaremos juntos.\"", 0.03)
            press_any_key()
            
        # Se Elena traiu (Mini-boss opcional antes de Theron)
        # Elena traiu se o pergaminho foi guardado e a cabana roubada
        if self.state.get_flag("roubou_cabana") and self.state.get_flag("guardou_pergaminho") and not self.state.get_flag("elena_morta"):
            clear_screen()
            typewriter("Entre as árvores mortas e queimadas, uma figura conhecida surge no caminho de vocês.", 0.03)
            typewriter("É Elena, vestida com trajes de arco arruinados por magia roxa.", 0.03)
            typewriter("\n\"Eu esperava odiar vocês. Teria sido mais fácil.\"", 0.03)
            typewriter("\"Vocês roubaram nossas relíquias e guardaram o pergaminho maligno. Vocês são apenas mais monstros!\"", 0.03)
            typewriter("\"Eu não permitirei que vocês cheguem ao portal!\"", 0.03)
            play_sound_effect("ELENA ANGER", None)
            self.pre_boss_menu("Elena (A Traída)")
            
            elena_boss = Enemy("Elena (A Traída)", 130, 20, 4, 250, 100, AIType.AGGRESSIVE)
            combat = CombatSystem(self.state, [elena_boss], can_flee=False)
            if not combat.run():
                self.game_over()
                
            self.state.set_flag("elena_morta", True)
            typewriter("\nElena cai ajoelhada, com os olhos lacrimejando.", 0.03)
            typewriter("\"Se vocês vencerem... provem que eu estava errada. Por favor...\"", 0.03)
            press_any_key()
            
        # Encontro com Theron
        clear_screen()
        typewriter("Uma figura esguia e cansada surge de uma fenda de basalto, apontando uma tocha trêmula.", 0.03)
        typewriter("É Theron, o guia sobrevivente de uma antiga expedição arruinada.", 0.03)
        typewriter("\n\"Não dê mais um passo se ainda gosta de seu próprio nome.\"", 0.03)
        typewriter("\"Eu vi Malakar. Ele morreu dividido em três partes e exige três mortes antes do fim.\"", 0.03)
        typewriter("\"Primeiro, o rei de armadura. Segundo, o feiticeiro do Vazio. Por fim, a essência frágil de Veyr Malakar.\"", 0.03)
        typewriter("\"O portal dele está guardado por um gigante de pedra e sombras. Destrua o Guardião para passar.\"", 0.03)
        press_any_key()
        
        import sys
        if 'pytest' not in sys.modules:
            shop_choice = self.get_leader_choice(
                {
                    "1": "Comprar suprimentos",
                    "2": "Continuar a jornada"
                },
                prompt="Theron abre uma mochila surrada: 'Peguei isso dos mortos no caminho. Vocês vão precisar mais do que eu.'"
            )
            if shop_choice == "1":
                self.theron_shop()
        
        # Boss - Guardião do Portal
        clear_screen()
        print_centered("=== O GUARDIÃO DO PORTAL ===", None)
        typewriter("Um gigante de rochas flutuantes ergue-se diante de um arco de pedra quebrado.", 0.03)
        typewriter("Não possui rosto, apenas uma cavidade negra que atrai toda a luz.", 0.03)
        typewriter("\n\"Nenhum mortal passa inteiro. Entregue sua carne e suas memórias.\"", 0.03)
        play_sound_effect("PORTAL GUARDIAN AWAKEN", None)
        self.pre_boss_menu("o Guardião do Portal")
        
        portal_boss = spawn_enemy("guardiao_portal")
        
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "VISUAL_EFFECT",
                "effect_type": "enemy_intro",
                "text": "Guardião do Portal",
                "color": "shadow_purple",
                "duration": 2500
            })
            import time
            time.sleep(2.0)
            
        combat = CombatSystem(self.state, [portal_boss], can_flee=False)
        if not combat.run():
            self.game_over()
            
        typewriter("\nCom a queda do Guardião, as pedras arcanas desabam. O caminho para as salas finais está aberto.", 0.03)
        press_any_key()
        self.chapter_6_start()

    def theron_shop(self):
        from engine.items import create_item
        while True:
            clear_screen()
            print_centered("=== MOCHILA DE THERON ===", None)
            typewriter(f"Seu Ouro: {self.player.gold}g\n", 0.02)
            
            options = {
                "1": "Poção de Vida Média (80g)",
                "2": "Poção de Mana (60g)",
                "3": "Antídoto (40g)",
                "4": "Sair da loja"
            }
            
            ch = self.get_leader_choice(options, prompt="O que deseja comprar? ")
            if ch == "4" or not ch:
                break
                
            items_db = {
                "1": ("Poção de Vida Média", 80, "pocao_vida_m"),
                "2": ("Poção de Mana", 60, "pocao_mana_m"),
                "3": ("Antídoto", 40, "antidoto")
            }
            
            if ch in items_db:
                name, cost, item_id = items_db[ch]
                if self.player.gold >= cost:
                    self.player.gold -= cost
                    new_item = create_item(item_id)
                    self.player.inventory.append(new_item)
                    typewriter(f"\nVocês compraram {name} por {cost}g!", 0.03)
                else:
                    typewriter("\n\"Vocês não têm ouro suficiente para isso.\" - diz Theron.", 0.03)
                press_any_key()

    def chapter_6_start(self):
        from engine.save_system import save_game
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "templo"
        self.state.current_chapter = 6
        if self.adapter:
            self.adapter.on_state_change(self.state)
        # Sala 1: Enigmas
        clear_screen()
        print_centered("=== A SALA DOS ENIGMAS ===", None)
        typewriter("A primeira sala do templo final é circular e coberta por espelhos escuros de obsidiana.", 0.03)
        typewriter("Um enigma brilha no chão de pedra em letras de luz roxa:", 0.03)
        typewriter("\n\"Sou porta quando fechado, prisão quando aberto, promessa quando quebrado.", 0.03)
        typewriter("Reis me usam para mentir, mortos me usam para ficar. O que sou?\"", 0.03)
        
        options = {}
        if any(p.char_class == CharacterClass.MAGO for p in self.party):
            options["1"] = "[Mago] Escrever a resposta 'selo' com mana no ar"
            
        options["2"] = "Escolher a Chave de Osso"
        options["3"] = "Escolher a Chave de Vidro"
        options["4"] = "Tentar responder verbalmente: 'selo'"
        
        choice = self.get_party_vote(options, prompt="Qual a resposta da party? ")
        if choice == "1" or choice == "4":
            typewriter("\nA resposta está correta! As runas se dissipam e a porta de obsidiana se abre.", 0.03)
            self.state.set_flag("sala_enigmas_mago", True)
        else:
            self.consume_resource(self.player, "hp", 20, "Espelhos de obsidiana quebrados")
            self.state.set_flag("sala_enigmas_falha", True)
            
        press_any_key()
        
        # Sala 2: Mortos
        clear_screen()
        print_centered("=== A SALA DOS MORTOS ===", None)
        typewriter("A segunda sala assemelha-se a uma cripta repleta de guerreiros caídos amarrados por fios roxos.", 0.03)
        typewriter("Ao entrar, os olhos vazios deles se acendem e eles se erguem segurando armas.", 0.03)
        
        options = {}
        if any(p.char_class == CharacterClass.CLERIGO for p in self.party):
            options["1"] = "[Clérigo] Invocar purificação sagrada para desatar os fios dos mortos"
            
        options["2"] = "Combater as sentinelas e abrir caminho à força"
        
        choice = self.get_party_vote(options, prompt="O que a party decide? ")
        if choice == "1":
            typewriter("\nVocês erguem seus amuletos sagrados e entoam orações ancestrais.", 0.03)
            typewriter("Os fios roxos derretem em luz branca. Os guerreiros descansam em paz, sussurrando preces.", 0.03)
            typewriter("Uma benção sagrada envolve o grupo (Imunidade temporária no chefe).", 0.03)
            self.state.set_flag("sala_mortos_clerigo", True)
        else:
            typewriter("\nOs mortos atacam sem alma ou medo!", 0.03)
            enemy1 = Enemy("Sentinela Involuntário", 70, 14, 3, 50, 10)
            combat = CombatSystem(self.state, [enemy1], can_flee=False)
            if not combat.run():
                self.game_over()
            self.state.set_flag("sala_mortos_falha", True)
            
        press_any_key()
        
        # Sala 3: Silêncio
        clear_screen()
        print_centered("=== A SALA DO SILÊNCIO ===", None)
        typewriter("A terceira sala é totalmente silenciosa. Nenhum som de respiração ou passos é audível.", 0.03)
        typewriter("Um baú rúnico preto está no centro, conectado a fios tensionados nas paredes.", 0.03)
        
        options = {}
        if any(p.char_class == CharacterClass.LADINO for p in self.party):
            options["1"] = "[Ladino] Desarmar os fios silenciosamente e destrancar o baú"
            
        options["2"] = "Tentar destrancar o baú à força"
        options["3"] = "Ignorar o baú e seguir para a câmara final"
        
        choice = self.get_party_vote(options, prompt="Como a party decide agir? ")
        if choice == "1":
            typewriter("\nCom movimentos precisos, o grupo desarma os fios e destranca o baú.", 0.03)
            typewriter("Dentro há um fragmento de ferro gélido que reduzirá a defesa de Malakar.", 0.03)
            self.state.set_flag("sala_silencio_ladrao", True)
        elif choice == "2":
            self.consume_resource(self.player, "hp", 25, "Lâminas ocultas do baú rúnico")
            self.state.set_flag("sala_silencio_falha", True)
        else:
            typewriter("\nVocês contornam o baú cautelosamente e seguem em frente.", 0.03)
            
        press_any_key()
        self.final_confrontation()

    def final_confrontation(self):
        clear_screen()
        print_centered("=== ALTAR DO CAOS ANCESTRAL ===", None)
        self.adapter.emit(AsciiArt(TEMPLE_ART))
        
        typewriter("Vocês entram na câmara rúnica central. Lorde Malakar flutua sobre o abismo de chamas.", 0.03)
        typewriter("\"Aventureiros. Vocês derrotaram meus servos, mas eu sou a ordem que Aethelgard precisa!\"", 0.03)
        
        # Suporte de Aliados
        has_support = False
        if self.state.get_flag("poupou_ogro"):
            typewriter("\nDrogg surge escorando as rochas do teto, garantindo que vocês não sejam esmagados!", 0.03)
            typewriter("Ele joga uma poção de vida gigante para vocês!", 0.03)
            self.player.hp = min(self.player.max_hp, self.player.hp + 50)
            has_support = True
            
        if self.state.get_flag("ajudou_goblin"):
            typewriter("\nDropp surge de um atalho secreto arremessando bombinhas que distraem Malakar!", 0.03)
            has_support = True
            
        if self.state.get_flag("ajudou_sobreviventes"):
            typewriter("\nOs sobreviventes guiados por Daren acendem as runas de cura das colunas da sala.", 0.03)
            typewriter("A mana de vocês é regenerada em 20 MP.", 0.03)
            self.player.mp = min(self.player.max_mp, self.player.mp + 20)
            has_support = True
            
        if self.state.get_flag("oakhaven_defendida"):
            typewriter("\nA Capitã Rhea e seus soldados barram as portas externas contra o reforço das sombras.", 0.03)
            has_support = True
            
        if not has_support:
            typewriter("\nNenhum aliado veio apoiar vocês. A câmara está fria e silenciosa.", 0.03)
            
        self.pre_boss_menu("Lorde Malakar")
        
        # Boss Setup
        boss = spawn_enemy("lorde_malakar")
        
        # Apply Room Advantages
        if self.state.get_flag("sala_silencio_ladrao"):
            boss.defense = max(0, boss.defense - 3)
            typewriter("🗡️ O fragmento gélido do baú enfraquece a couraça de Malakar! Sua defesa foi reduzida.", 0.03)
            
        if self.state.get_flag("sala_enigmas_mago"):
            boss.hp -= 40
            typewriter("🔮 As runas escritas no ar rompem parte da barreira protetora de Malakar! Ele perdeu 40 HP.", 0.03)
            
        if self.state.get_flag("sala_mortos_clerigo"):
            self.player.status_effects[StatusEffect.PROTEGIDO] = 5
            typewriter("🛡️ A benção dos mortos libertados concede a vocês proteção contra danos por 5 turnos.", 0.03)
            
        press_any_key()
        
        # Boss Battle
        combat = CombatSystem(self.state, [boss], can_flee=False)
        if not combat.run():
            self.game_over()
            
        self.state.set_flag("malakar_derrotado", True)
        
        # Fase 3 diálogo final
        clear_screen()
        typewriter("A armadura de Malakar se parte completamente. A coroa de espinhos cai no chão e queima sem fogo.", 0.03)
        typewriter("O que resta diante de vocês não parece um deus sombrio, mas um homem antigo sustentado por ódio demais para morrer.", 0.03)
        typewriter("Atrás dele, o portal pulsa como um coração doente.", 0.03)
        
        typewriter("\nMalakar: \"Eu dei séculos ao mundo. Ordem. Medo. Continuidade.\"", 0.03)
        typewriter("\nVocês: \"Você deu correntes.\"", 0.03)
        typewriter("\nMalakar: \"Correntes seguram pontes. Seguram reinos. Seguram pessoas longe do abismo que fingem não desejar.\"", 0.03)
        
        if self.state.get_flag("lacre_sombrio"):
            typewriter("\nO Lacre das Sombras no peito de vocês reage ao portal. A luz roxa envolve a câmara.", 0.03)
            typewriter("\nMalakar: \"Aí está. O poder que vocês juraram controlar. O pergaminho não corrompe. Ele traduz. Ele mostra o que a alma pediria se não temesse testemunhas.\"", 0.03)
            typewriter("\"Usem-no. Quebrem o portal com minha própria língua. Salvem todos do jeito que eu salvaria. Não um mundo bom. Bondade é frágil. Darei um mundo obediente.\"", 0.03)
            
            if any(p.char_class == CharacterClass.CLERIGO for p in self.party):
                typewriter("\n[Clérigo]: \"Isso não é salvação.\"", 0.03)
                typewriter("\nMalakar: \"Salvação é o nome que os vencedores dão ao método que sobreviveram para defender.\"", 0.03)
            elif any(p.char_class == CharacterClass.MAGO for p in self.party):
                typewriter("\n[Mago]: \"Se usarmos isso, continuamos o ciclo.\"", 0.03)
                typewriter("\nMalakar: \"Ciclos são apenas eternidade vista por olhos pequenos.\"", 0.03)
            elif any(p.char_class == CharacterClass.LADINO for p in self.party):
                typewriter("\n[Ladino]: \"Você fala demais para alguém com medo.\"", 0.03)
                typewriter("\nMalakar: \"Tenho medo, sim. Foi por isso que venci a morte. Coragem é uma virtude inventada por mortais sem alternativa.\"", 0.03)
            elif any(p.char_class == CharacterClass.GUERREIRO for p in self.party):
                typewriter("\n[Guerreiro]: \"Então morra com medo.\"", 0.03)
                typewriter("\nMalakar: \"Tentem.\"", 0.03)
                
        press_any_key()
        self.ending_sequence()

    def ending_sequence(self):
        clear_screen()
        if self.state.get_flag("guardou_pergaminho") and self.state.get_flag("lacre_sombrio"):
            self.ending_dark_lord()
        elif not self.state.get_flag("elena_morta") and not self.state.get_flag("roubou_cabana"):
            self.ending_hero_of_light()
        else:
            self.ending_neutral_wanderer()

    def ending_hero_of_light(self):
        clear_screen()
        self.adapter.emit(AsciiArt(VICTORY_ART))
        print_centered("=== FINAIS: HERÓI DA LUZ ===", None)
        typewriter("Com a queda de Lorde Malakar, a chama ancestral brilha com luz azul celestial pura.", 0.03)
        typewriter("As sombras recuam de Oakhaven e a floresta volta a florescer sob a luz do sol.", 0.03)
        typewriter("Vocês retornam à vila como uma lenda viva. Ancião Alistair entrega-lhes as chaves da prosperidade.", 0.03)
        typewriter("Vocês salvaram Aethelgard mantendo a honra e a luz de vocês intactas.", 0.03)
        press_any_key("Pressione [ENTER] para continuar...")
        self.act_ii_epilogue_hook()

    def ending_dark_lord(self):
        clear_screen()
        self.adapter.emit(AsciiArt(VICTORY_ART))
        print_centered("=== FINAIS: O NOVO SENHOR DAS SOMBRAS ===", None)
        typewriter("Com Malakar derrotado, vocês olham para a chama rúnica enfraquecida.", 0.03)
        typewriter("O poder do Lacre no peito de vocês clama por domínio total.", 0.03)
        typewriter("Vocês consomem a chama divina, fundindo-a com o Pergaminho de Sangue das Sombras.", 0.03)
        typewriter("\nVocês se erguem como o novo Imperador das Sombras de Aethelgard.", 0.03)
        typewriter("Todos se ajoelharão diante da sua ordem inquebrável, ou queimarão no vazio.", 0.03)
        press_any_key("Pressione [ENTER] para continuar...")
        self.act_ii_epilogue_hook()

    def ending_neutral_wanderer(self):
        clear_screen()
        self.adapter.emit(AsciiArt(VICTORY_ART))
        print_centered("=== FINAIS: O ANDARILHO SOLITÁRIO ===", None)
        typewriter("Lorde Malakar está morto. O perigo iminente foi contido e Oakhaven está a salvo por hora.", 0.03)
        typewriter("No entanto, o preço pago por suas escolhas escuras pesa nas costas de vocês.", 0.03)
        if self.state.get_flag("elena_morta"):
            typewriter("A morte de Elena assombra as mentes de vocês. Vocês salvaram o mundo, mas perderam quem confiava em vocês.", 0.03)
        typewriter("Vocês recolhem suas moedas silenciosamente e partem sob a névoa do amanhecer.", 0.03)
        press_any_key("Pressione [ENTER] para continuar...")
        self.act_ii_epilogue_hook()

    def credits(self):
        clear_screen()
        print_centered("=== CRÉDITOS ===", None)
        typewriter("AETHELGARD RPG - CRÔNICAS DE AVENTURA (v1.0)", 0.03)
        typewriter("Desenvolvido por: Antigravity AI & Chewbaccaun", 0.03)
        typewriter("\nObrigado por jogar!", 0.04)
        press_any_key("Pressione [ENTER] para finalizar.")
        import sys
        sys.exit(0)
