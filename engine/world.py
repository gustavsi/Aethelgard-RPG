import time
import random
from engine.constants import CharacterClass, AIType, Colors
from engine.dto import NarrativeText, ChoiceRequested, ClearScreen, PressAnyKey, SoundEffect

def clear_screen():
    from engine.adapter import get_adapter
    get_adapter().emit(ClearScreen())

def typewriter(text, delay=0.02, color=None):
    from engine.adapter import get_adapter
    get_adapter().emit(NarrativeText(text))

def press_any_key(msg="Pressione [ENTER] para continuar..."):
    from engine.adapter import get_adapter
    get_adapter().emit(PressAnyKey(msg))

def print_centered(text, color=None):
    from engine.adapter import get_adapter
    get_adapter().emit(NarrativeText(text))

def play_sound_effect(effect_text, color=None):
    from engine.adapter import get_adapter
    get_adapter().emit(SoundEffect(effect_text))

def get_menu_choice(options, prompt="Escolha uma opção: ", error_msg="Opção inválida. Tente novamente."):
    from engine.adapter import get_adapter
    return get_adapter().emit(ChoiceRequested(prompt, options))

from engine.items import create_item
from engine.enemy import spawn_enemy, Enemy
from engine.companion import get_companion
from engine.combat import CombatSystem
from engine.npc import Blacksmith, TavernKeeper, ElderAlistair
from engine.save_system import save_game, load_game
from engine.inventory_ui import manage_inventory
from engine.art import FOREST_ART, CABIN_ART, TOWN_ART, CAVES_ART, TEMPLE_ART, VICTORY_ART, GAME_OVER_ART
from engine.dto import NarrativeText, AsciiArt

from engine.world_chapter_3 import Chapter3Mixin
from engine.world_chapter_4 import Chapter4Mixin
from engine.world_chapter_5 import Chapter5Mixin
from engine.world_chapter_7 import Chapter7Mixin
from engine.world_chapter_8 import Chapter8Mixin
from engine.world_chapter_9 import Chapter9Mixin

class WorldManager(Chapter3Mixin, Chapter4Mixin, Chapter5Mixin, Chapter7Mixin, Chapter8Mixin, Chapter9Mixin):
    def __init__(self, player, adapter=None, party=None):
        from engine.state import GameState
        from engine.adapter import UIAdapter
        self.adapter = adapter or UIAdapter.get_instance()
        if isinstance(player, GameState):
            self.state = player
            self.player = self.state.player
            if adapter:
                self.state.adapter = adapter
        else:
            self.state = GameState(player, adapter=self.adapter)
            self.player = self.state.player
        
        if party is not None:
            self.state.party = party
        elif isinstance(player, GameState):
            if not getattr(self.state, "party", None):
                self.state.party = [self.player]
        else:
            self.state.party = [self.player]
            
        self.state.world = self
        self.adapter.state = self.state

    @property
    def party(self):
        return self.state.party

    @party.setter
    def party(self, value):
        self.state.party = value

    def recruit_companion(self, companion_id: str):
        from engine.companion import get_companion
        new_companion = get_companion(companion_id)
        if not new_companion:
            return
        if self.player.companion:
            old_name = self.player.companion.name
            typewriter(f"\n⚠️ {old_name} deixa o grupo para abrir espaço para {new_companion.name}.", 0.03)
        self.player.companion = new_companion
        typewriter(f"\n✨ {new_companion.name} juntou-se ao grupo!", 0.03)

    def update_environment(self):
        """Atualiza dinamicamente o clima e o ciclo dia/noite."""
        # 1. Ciclo Dia/Noite
        current_time = self.state.get_flag("time_of_day", "Dia")
        new_time = "Noite" if current_time == "Dia" else "Dia"
        
        # 2. Clima Dinâmico
        weathers = ["Ensolarado", "Chuvoso", "Nevoeiro", "Tempestade"]
        weights = [0.5, 0.25, 0.15, 0.10]
        new_weather = random.choices(weathers, weights=weights)[0]
        
        self.state.set_flag("time_of_day", new_time)
        self.state.set_flag("weather", new_weather)
        
        # Emitir log informando a mudança de clima
        emoji_time = "☀️" if new_time == "Dia" else "🌙"
        emoji_weather = {
            "Ensolarado": "☀️",
            "Chuvoso": "🌧️",
            "Nevoeiro": "🌫️",
            "Tempestade": "⛈️"
        }.get(new_weather, "☀️")
        
        typewriter(f"\n🌍 {Colors.BOLD}O clima mudou!{Colors.RESET} Agora é {new_time} {emoji_time} e o tempo está {new_weather} {emoji_weather}.", 0.02)

    def get_leader_choice(self, options, prompt="Escolha uma opção: "):
        # Future multiplayer routing will check self.state.get_flag("party_lider")
        # and emit the request to the specific leader connection.
        from engine.console import get_menu_choice
        return get_menu_choice(options, prompt)

    def get_party_vote(self, options: dict, prompt: str):
        """Envia a escolha para TODOS os jogadores simultaneamente,
        aguarda todos votarem, resolve por maioria. Empate = d20."""
        if self.adapter.__class__.__name__ != "MulticastWebUIAdapter":
            # Single-player / pytest fallback: leader decides
            return self.get_leader_choice(options, prompt)

        from engine.dto import ChoiceRequested, NarrativeText
        import random

        event = ChoiceRequested(prompt, options)
        event.broadcast_to_all = True
        self.adapter.emit(event)

        votes = self.adapter.collect_all_votes(self.state.session_id)

        counts = {}
        for v in votes.values():
            counts[v] = counts.get(v, 0) + 1
            
        if not counts:
            return random.choice(list(options.keys()))
            
        max_votes = max(counts.values())
        winners = [k for k, v in counts.items() if v == max_votes]

        if len(winners) == 1:
            winning_choice = winners[0]
            self.adapter.emit(NarrativeText(f"🗳️ A party decidiu: {options[winning_choice]}"))
        else:
            winning_choice = random.choice(winners)
            d20 = random.randint(1, 20)
            self.adapter.emit(NarrativeText(f"🎲 Empate! Rolando um d20... ({d20}) — decisão: {options[winning_choice]}"))

        # Phase 2: Unison / Fracture bonds from multiplayer votes
        try:
            from engine.party_meta import observe_vote
            observe_vote(self.state, votes, winning_choice)
        except Exception:
            pass

        return winning_choice

    def request_party_ready(self):
        """Chame isso apenas em pontos narrativos específicos onde faz sentido dar tempo aos jogadores (ex: chegada em Oakhaven, Millhaven)."""
        session_id = getattr(self.state, "session_id", None)
        if session_id:
            from server import active_sessions, send_player_ready_prompt
            session = active_sessions.get(session_id)
            if session:
                session["waiting_for_ready"] = True
                session["ready_players"] = set()
                
                # If there's an active waiting input, intercept it immediately
                adapter = session.get("adapter")
                last_input = adapter.last_waiting_input if adapter else None
                if last_input:
                    session["pending_leader_choice"] = last_input
                    
                # Broadcast ready prompts to everyone
                for cid in list(session["connected_clients"].keys()):
                    send_player_ready_prompt(session, cid, self)

    def run_game(self):
        """Starts the narrative game loop."""
        clear_screen()
        print_centered("=== MENU PRINCIPAL ===", None)
        options = {
            "1": "Novo Jogo",
            "2": "Carregar Jogo Salvo"
        }
        choice = self.get_leader_choice(options)
        
        start_state = "intro"
        if choice == "2":
            loaded_state = load_game()
            if loaded_state:
                self.state = loaded_state
                self.player = self.state.player
                start_state = self.state.current_location
                self.adapter.emit(NarrativeText(f"\nJogo carregado com sucesso!"))
                press_any_key()
            else:
                self.adapter.emit(NarrativeText(f"\nNenhum save encontrado. Iniciando novo jogo."))
                press_any_key()
                
        if start_state == "intro":
            self.intro_sequence()
            self.chapter_1_start()
            self.chapter_2_start()
            self.chapter_3_start()
            self.ending_sequence()
        elif start_state == "oakhaven":
            self.visit_oakhaven()
            self.chapter_2_start()
            self.chapter_3_start()
            self.ending_sequence()

    def pre_boss_menu(self, boss_name: str):
        import sys
        if 'pytest' in sys.modules:
            return
        from engine.inventory_ui import manage_inventory
        while True:
            choice = self.get_leader_choice(
                {"1": "⚔️ Entrar em combate", "2": "🎒 Gerenciar inventário"},
                prompt=f"Vocês estão prestes a enfrentar {boss_name}. Preparem-se."
            )
            if choice == "1":
                break
            elif choice == "2":
                manage_inventory(self.player)

    def consume_resource(self, player, resource: str, amount: int, reason: str):
        if resource == "hp":
            player.hp = max(0, player.hp - amount)
            self.adapter.emit(NarrativeText(f"⚠️ {player.name} perdeu {amount} HP ({reason})"))
        elif resource == "mp":
            player.mp = max(0, player.mp - amount)
            self.adapter.emit(NarrativeText(f"⚠️ {player.name} perdeu {amount} MP ({reason})"))
        elif resource == "item":
            self.adapter.emit(NarrativeText(f"⚠️ {player.name} usou: {reason}"))
        elif resource == "gold":
            player.gold = max(0, player.gold - amount)
            self.adapter.emit(NarrativeText(f"⚠️ {player.name} gastou {amount}G ({reason})"))

    def intro_sequence(self):
        clear_screen()
        typewriter("O mundo de Aethelgard está em declínio...", 0.04, None)
        typewriter("As chamas arcanas dos templos sagrados estão se apagando...", 0.04, None)
        typewriter("E das profundezas da terra, a escuridão começa a sussurrar.", 0.04, None)
        time.sleep(1.0)
        
        # Tavern opening prologue
        self.state.current_location = "taverna"
        clear_screen()
        print_centered("=== PRÓLOGO: A TAVERNA DO INÍCIO ===", None)
        self.adapter.emit(AsciiArt(TOWN_ART))
        
        typewriter("A chuva cai grossa sobre a estrada real, transformando a noite em um borrão de lama, vento e relâmpagos.", 0.03)
        typewriter("A única luz confiável vem da Taverna do Início, uma construção de pedra e madeira onde viajantes se escondem.", 0.03)
        typewriter("Naquela noite, quatro estranhos são empurrados para o mesmo canto da taverna por uma sucessão de presságios.", 0.03)
        typewriter("O taberneiro fecha as janelas com pressa e avisa: \"Nenhuma estrada está segura. Se quiserem chegar vivos a Oakhaven, viajem em grupo.\"", 0.03)
        press_any_key()
        
        clear_screen()
        print_centered("=== MONÓLOGOS DAS CLASSES ===", None)
        typewriter("\nGuerreiro:\n\"Eu já vi muralhas caírem e homens melhores do que eu desaparecerem na poeira. Ainda assim, uma lâmina firme resolve problemas que orações e mapas não resolvem. Se essa estrada quer sangue, que venha buscar o meu primeiro.\"", 0.03)
        typewriter("\nMago:\n\"As estrelas estão desalinhadas. Há uma força antiga se movendo sob a terra, e ela não se esconde mais de quem sabe ler seus sinais. Não viajo por coragem. Viajo porque o conhecimento que ignoramos sempre volta como condenação.\"", 0.03)
        typewriter("\nLadrão:\n\"Estradas perigosas são boas para dois tipos de gente: mortos e oportunistas. Eu prefiro continuar no segundo grupo. Se há armadilhas, fechaduras ou mentiras no caminho, deixem comigo.\"", 0.03)
        typewriter("\nClérigo:\n\"Toda chama sagrada treme antes de se apagar. Hoje, até minha fé pareceu projetar sombra. Se Malakar é mesmo o nome por trás dessa escuridão, então alguém precisa carregar luz até onde ela não quer entrar.\"", 0.03)
        press_any_key()
        
        clear_screen()
        print_centered("=== ESCOLHA DO LÍDER ===", None)
        typewriter("O taberneiro coloca uma moeda antiga sobre a mesa e diz: \"Grupos sem voz única morrem discutindo. Quem deve liderar a party?\"", 0.03)
        
        options = {str(i+1): f"{p.name} ({p.char_class.value})" 
                   for i, p in enumerate(self.party)}
        
        lead_choice = self.get_leader_choice(options, prompt="Quem será o líder da party? ")
        leader = self.party[int(lead_choice) - 1]
        lider_name = leader.name
        
        typewriter(f"\nO taberneiro lança a moeda. A decisão está tomada. O {lider_name} liderará a party!", 0.03)
        self.state.set_flag("party_lider", lider_name.lower())
        press_any_key()

    def game_over(self):
        # Reset combat states so the frontend transitions back to NarrativeView
        self.state.in_combat = False
        self.state.combat_state = None
        
        # Send state update so React knows we are out of combat
        if self.adapter:
            self.adapter.on_state_change(self.state)
        
        clear_screen()
        typewriter("A jornada do grupo terminou de forma trágica...", 0.05, None)
        typewriter("O destino de Aethelgard está selado sob as sombras...", 0.05, None)
        
        # Wait for user input to confirm reading the messages
        press_any_key("Pressione [ENTER] para recomeçar...")
        
        from engine.exceptions import GameOverException
        raise GameOverException("A jornada do grupo terminou de forma trágica...")

    # ================= CHAPTER 1 =================
    def chapter_1_start(self):
        self.state.current_location = "floresta"
        self.state.current_chapter = 1
        if self.adapter:
            self.adapter.on_state_change(self.state)
        clear_screen()
        print_centered("=== CAPÍTULO I: A FLORESTA SOMBRIA ===", None)
        self.adapter.emit(AsciiArt(FOREST_ART))
        
        typewriter("Vocês despertam em uma clareira de uma floresta fria e escura.", 0.03)
        typewriter("A cabeça de vocês dói. A última coisa de que se lembram é de uma emboscada na estrada real.", 0.03)
        typewriter("Olhando ao redor, o grupo avista uma estrada antiga de terra batida que parece cortar a floresta.", 0.03)
        
        options = {
            "1": "Seguir pela estrada antiga (Rápido, mas exposto)",
            "2": "Explorar a densa floresta escura (Perigoso, mas misterioso)",
            "3": "Permanecer parado e aguardar por socorro",
            "4": "Entrar no Bosque Sagrado (Muito Perigoso - Oculto)"
        }
        
        choice = self.get_leader_choice(options, prompt="O que o grupo deseja fazer? ")
        
        if choice == "1":
            self.chapter_1_road()
        elif choice == "2":
            self.chapter_1_forest()
        elif choice == "4":
            self.chapter_1_secret_boss()
        else:
            self.chapter_1_wait()

    def chapter_1_road(self):
        self.state.current_location = "estrada"
        clear_screen()
        typewriter("Vocês decidem caminhar pela estrada aberta.", 0.03)
        typewriter("O vento uiva por entre as copas das árvores secas. *Fshhhhh...*", 0.03)
        typewriter("De repente, passos rápidos surgem dos arbustos! Um salteador armado salta na frente de vocês!", 0.03)
        play_sound_effect("HA-HA! Entregue o ouro!", None)
        
        enemy = spawn_enemy("salteador")
        combat = CombatSystem(self.state, [enemy])
        res = combat.run()
        
        if res == False:
            self.game_over()
        elif res == "FLED":
            typewriter("\nVocês correm desesperadamente pelos arbustos, despistando o ladrão.", 0.03)
            self.state.set_flag("fugiu_salteador", True)
            
        typewriter("\nApós a escaramuça, vocês continuam caminhando e avistam uma cabana velha.", 0.03)
        press_any_key()
        self.chapter_1_cabin()

    def chapter_1_forest(self):
        self.state.current_location = "floresta"
        clear_screen()
        typewriter("Vocês entram mata adentro, desviando de galhos espinhosos.", 0.03)
        typewriter("*CRACK* - Vocês pisam em um galho seco. Algo se esconde nas sombras.", 0.03)
        
        # 50% encounter wolf, 50% find relic
        if random.random() < 0.5:
            typewriter("Um Lobo da Floresta de olhos vermelhos brilha no escuro e rosna!", 0.03)
            play_sound_effect("GRRRRRRR!", None)
            enemy = spawn_enemy("lobo_floresta")
            combat = CombatSystem(self.state, [enemy])
            if not combat.run():
                self.game_over()
        else:
            typewriter("Vocês encontram o cadáver de um antigo cultista caído perto de um carvalho negro.", 0.03)
            typewriter("Em sua mão fria, há um amuleto esculpido com símbolos proibidos.", 0.03)
            
            sub_opt = {
                "1": "Pegar o Amuleto Sombrio (Lacre das Sombras)",
                "2": "Deixar o amuleto em paz e seguir adiante"
            }
            ch = self.get_leader_choice(sub_opt, prompt="A escolha do líder: ")
            if ch == "1":
                self.state.set_flag("lacre_sombrio", True)
                typewriter(f"\nVocês sentem um arrepio gélido ao guardar o Lacre das Sombras.", 0.03)
            else:
                typewriter("\nVocês fazem uma prece rápida e continuam o caminho.", 0.03)
                
        typewriter("\nEventualmente, vocês saem perto de uma clareira onde encontram uma cabana abandonada.", 0.03)
        press_any_key()
        self.chapter_1_cabin()

    def chapter_1_secret_boss(self):
        self.state.current_location = "bosque"
        clear_screen()
        print_centered("=== O BOSQUE SAGRADO ===", None)
        typewriter("Vocês ignoram a estrada principal e entram em um bosque onde as árvores parecem respirar.", 0.03)
        typewriter("No centro de um círculo de pedras, um majestoso Ent corrupto por magia negra se ergue!", 0.03)
        typewriter("\"Quem ousa perturbar o sono da floresta?\" - ruge a criatura.", 0.03, None)
        play_sound_effect("ROAR OF THE WOODS!", None)
        
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "VISUAL_EFFECT",
                "effect_type": "enemy_intro",
                "text": "Guardião da Floresta",
                "color": "blood_red",
                "duration": 2500
            })
            import time
            time.sleep(2.0)
            
        guardian = spawn_enemy("guardiao_floresta")
        combat = CombatSystem(self.state, [guardian])
        if not combat.run():
            self.game_over()
            
        typewriter("\nO Guardião cai despedaçado. Em seu núcleo, o grupo encontra um cristal antigo de puro poder.", 0.03)
        typewriter("A floresta ao redor parece suspirar aliviada com a morte da corrupção.", 0.03)
        xp_logs = self.player.gain_xp(100)
        for log in xp_logs:
            self.adapter.emit(NarrativeText(log))
        
        loot = create_item("elixir_forca")
        self.player.inventory.append(loot)
        self.adapter.emit(NarrativeText(f"\nO grupo encontrou: {loot.get_colored_name()}!"))
        
        typewriter("\nVocês retornam à trilha principal e avistam uma cabana velha.", 0.03)
        press_any_key()
        self.chapter_1_cabin()

    def chapter_1_wait(self):
        clear_screen()
        typewriter("Vocês decidem sentar-se em um tronco e esperar.", 0.03)
        typewriter("Os minutos passam... O silêncio da floresta é opressor. *Tik-tok, tik-tok...*", 0.03)
        typewriter("Atraído pelo cheiro de vida, um Lobo faminto surge das folhagens e ataca o grupo de surpresa!", 0.03)
        play_sound_effect("AOUUUUUUU!", None)
        
        # Surprise attack: Player starts damaged
        dmg = int(self.player.max_hp * 0.15)
        self.consume_resource(self.player, "hp", dmg, "Ataque surpresa do Lobo")
        
        enemy = spawn_enemy("lobo_floresta")
        combat = CombatSystem(self.state, [enemy], can_flee=False)
        if not combat.run():
            self.game_over()
            
        typewriter("\nFeridos e assustados, vocês decidem se mover rapidamente e acabam encontrando uma cabana velha.", 0.03)
        press_any_key()
        self.chapter_1_cabin()

    def chapter_1_cabin(self):
        self.state.current_location = "cabana"
        clear_screen()
        print_centered("=== A CABANA ABANDONADA ===", None)
        self.adapter.emit(AsciiArt(CABIN_ART))
        
        typewriter("A cabana parece velha e abandonada, com tábuas podres e poeira.", 0.03)
        typewriter("Uma aura estranha e pesada paira sobre a entrada.", 0.03)
        
        options = {
            "1": "Entrar na cabana para buscar abrigo ou suprimentos",
            "2": "Ignorar a cabana e continuar seguindo pela estrada",
            "3": "Procurar ao redor da cabana antes de entrar"
        }
        
        choice = self.get_leader_choice(options, prompt="O que o grupo deseja fazer? ")
        
        if choice == "1":
            self.enter_cabin()
        elif choice == "2":
            self.ignore_cabin()
        else:
            self.search_around_cabin()

    def enter_cabin(self):
        clear_screen()
        typewriter("Vocês empurram a porta rangente. *Creak...*", 0.03)
        typewriter("O cheiro de mofo e sangue velho invade as narinas de vocês.", 0.03)
        typewriter("De repente, o teto e as paredes da cabana começam a rachar! *CRASH!*", 0.03)
        typewriter("Uma figura colossal surge rasgando a madeira. Um Ogro gigante ruge com fúria!", 0.03)
        play_sound_effect("AAAARRRRRHHHH!", None)
        
        ogre = spawn_enemy("ogro_cabana")
        
        def ogre_hook(combat_sys):
            if ogre.hp / ogre.max_hp <= 0.20 and not self.state.get_flag("ogre_dialogue_triggered"):
                self.state.set_flag("ogre_dialogue_triggered", True)
                
                text = "O ogro cai de joelhos, soltando sua clava pesada. Suas feridas sangram abundantemente.\n\n\"Humano... forte. Drogg não querer morrer. Drogg ter medo... Por favor, poupar Drogg!\""
                sub_opt = {
                    "1": "Poupar o Ogro Drogg (Elena apoia, Drogg ajudará depois)",
                    "2": "Finalizar o Ogro sem piedade (+XP/Ouro)"
                }
                from engine.dto import CombatNarrativeMoment, NarrativeText
                combat_sys.adapter.broadcast(CombatNarrativeMoment(text, sub_opt).to_dict())
                
                decision = combat_sys.adapter._wait_for_input()
                if decision == "1":
                    self.state.set_flag("poupou_ogro", True)
                    combat_sys.adapter.emit(NarrativeText("Vocês abaixaram as armas. Drogg chora de alívio.\n\"Obrigado, Humano... Drogg lembrar disso. Se precisar, Drogg ajudar!\""))
                    return "END_COMBAT"
                else:
                    self.state.set_flag("poupou_ogro", False)
                    # P2-001: kill corruption must NOT come from set_flag(False) init —
                    # only from this explicit kill branch.
                    try:
                        from engine.party_meta import record_ogre_killed
                        record_ogre_killed(self.state)
                    except Exception:
                        pass
                    combat_sys.adapter.emit(NarrativeText("Vocês ignoram as súplicas da criatura e desferem o golpe final!"))
                    ogre.hp = 0
                    return "END_COMBAT"
            return None

        self.state.set_flag("poupou_ogro", False)
        if self.adapter and hasattr(self.adapter, 'broadcast'):
            self.adapter.broadcast({
                "type": "VISUAL_EFFECT",
                "effect_type": "enemy_intro",
                "text": "Ogro Drogg",
                "color": "blood_red",
                "duration": 2500
            })
            import time
            time.sleep(2.0)
        combat = CombatSystem(self.state, [ogre], can_flee=False, turn_hook=ogre_hook)
        combat.run()
        
        if self.player.hp <= 0:
            self.game_over()
            
        if not self.state.get_flag("poupou_ogro"):
            # Killed the ogre, give rewards manually if not spared
            combat.distribute_rewards()
            
        # Loot the cabin
        clear_screen()
        typewriter("Após o confronto com o ogro, vocês exploram a cabana destruída.", 0.03)
        typewriter("Em um baú escondido sob tábuas caídas, vocês encontram um altar com uma relíquia antiga de ouro.", 0.03)
        
        sub_opt = {
            "1": "Pegar a Relíquia Ancestral de Oakhaven (Cuidado: NPCs podem notar)",
            "2": "Deixar a relíquia no altar (Atitude honrada)"
        }
        dec = self.get_leader_choice(sub_opt, prompt="O que o líder decide? ")
        if dec == "1":
            self.state.set_flag("roubou_cabana", True)
            typewriter(f"\nVocês pegaram a Relíquia Ancestral!", 0.03)
        else:
            typewriter("\nVocês decidem não saquear o item de adoração.", 0.03)
            
        # Give some consumables anyway
        player_pot = create_item("pocao_vida_m")
        self.player.inventory.append(player_pot)
        self.adapter.emit(NarrativeText(f"Encontrou uma {player_pot.get_colored_name()} nos escombros."))
        
        press_any_key()
        self.reach_oakhaven()

    def ignore_cabin(self):
        clear_screen()
        typewriter("Vocês decidem ignorar a cabana e acelerar o passo pela estrada.", 0.03)
        typewriter("Porém, a escuridão atrai salteadores famintos. Dois ladrões de estrada saltam de uma clareira!", 0.03)
        play_sound_effect("Cercado!", None)
        
        b1 = spawn_enemy("salteador")
        b2 = spawn_enemy("salteador")
        b2.name = "Salteador Emboscador"
        
        combat = CombatSystem(self.state, [b1, b2])
        if not combat.run():
            self.game_over()
            
        typewriter("\nFeridos da emboscada, vocês continuam a trilha até o Vale de Oakhaven.", 0.03)
        press_any_key()
        self.reach_oakhaven()

    def search_around_cabin(self):
        clear_screen()
        typewriter("Vocês caminham com cuidado ao redor da cabana, olhando pelas frestas.", 0.03)
        typewriter("Vocês encontram uma armadilha de urso desativada e um pequeno esconderijo sob as janelas arrombadas.", 0.03)
        
        item = create_item("erva_cura")
        self.player.inventory.append(item)
        self.adapter.emit(NarrativeText(f"Você encontrou uma {item.get_colored_name()} e algumas moedas de ouro (20g)."))
        self.player.gold += 20
        
        typewriter("\nAo terminar de vasculhar, um barulho terrível vem de dentro da cabana!", 0.03)
        typewriter("O ogro sai quebrando a porta principal irritado com a sua presença!", 0.03)
        press_any_key()
        self.enter_cabin()

    def reach_oakhaven(self):
        clear_screen()
        print_centered("=== VALE DE OAKHAVEN ===", None)
        self.adapter.emit(AsciiArt(TOWN_ART))
        
        self.request_party_ready()
        self.visit_oakhaven()

    def visit_oakhaven(self):
        self.state.current_location = "oakhaven"
        while True:
            clear_screen()
            print_centered("=== VILA DE OAKHAVEN ===", None)
            self.adapter.emit(AsciiArt(TOWN_ART))
            try:
                from engine.hub_schedule import oakhaven_menu_options, schedule_blurb, is_forge_open
                typewriter(schedule_blurb(self.state), 0.02)
                options = oakhaven_menu_options(self.state)
            except Exception:
                options = {
                    "1": "Visitar a Taverna do Javali Saltitante",
                    "2": "Visitar a Forja de Garrett",
                    "3": "Falar com o Ancião Alistair",
                    "4": "Salvar Jogo",
                    "5": "Gerenciar Equipamentos e Status",
                    "6": "Viajar para as Cavernas Sussurrantes (Seguir a Missão)",
                }
                def is_forge_open(_s):
                    return True
            
            choice = self.get_leader_choice(options, prompt="Para onde o grupo deseja ir? ")
            if choice == "1":
                self.tavern_interaction()
            elif choice == "2":
                if not is_forge_open(self.state):
                    typewriter("\nA forja está fechada à noite. Garrett deixou um bilhete: \"Voltem ao amanhecer.\"", 0.03)
                    press_any_key()
                else:
                    forge = Blacksmith()
                    forge.interact(self.player)
            elif choice == "3":
                elder = ElderAlistair()
                elder.interact(self.player)
            elif choice == "4":
                self.state.current_location = "oakhaven"
                save_game(self.state, lambda msg: self.adapter.emit(NarrativeText(msg)))
                press_any_key()
            elif choice == "5":
                manage_inventory(self.player)
            elif choice == "7":
                try:
                    from engine.rumor_board import present_rumor_board
                    present_rumor_board(self)
                except Exception:
                    typewriter("O quadro de rumores está ilegível sob a chuva.", 0.03)
                    press_any_key()
            elif choice == "8":
                try:
                    from engine.codex import show_codex
                    show_codex(self)
                except Exception:
                    pass
            else:
                # Check if player accepted the quest
                if not self.player.quest_manager.has_active("cavernas"):
                    clear_screen()
                    typewriter("Vocês precisam falar com o Ancião Alistair para obter as diretrizes da missão antes de partir.", 0.03)
                    press_any_key()
                else:
                    typewriter("\nVocês arrumam suas malas, se despedem da vila e seguem em direção ao norte.", 0.03)
                    press_any_key()
                    break

    def tavern_interaction(self):
        clear_screen()
        typewriter("Vocês entram na taverna calorosa. O som de risadas e copos se chocando traz um alívio temporário.", 0.03)
        
        # Meet Elena (companion check)
        if not self.player.companion and not self.state.get_flag("elena_confronted"):
            typewriter("\nUma arqueira ruiva de olhar afiado está sentada em uma mesa de canto, limpando seu arco recurvo.", 0.03)
            
            options = {
                "1": "Sentar-se ao lado dela e se apresentar",
                "2": "Ignorá-la e ir falar com o taverneiro Barnaby"
            }
            ch = self.get_party_vote(options, prompt="Ação da party: ")
            
            if ch == "1":
                self.elena_dialogue()
                return
                
        # If no dialogue or already met, open shop
        tavern = TavernKeeper()
        tavern.interact(self.player)

    def elena_dialogue(self):
        clear_screen()
        typewriter("Vocês se aproximam e se senta. Ela olha para vocês de soslaio, friamente.", 0.03)
        typewriter("\"Quem são vocês? Não parecem ser daqui... O que querem comigo?\" - ela pergunta.", 0.03, None)
        
        options = {
            "1": "\"Estou ajudando a vila investigando as cavernas. Poderia usar uma batedora talentosa como você.\"",
            "2": "\"Sou apenas um viajante em busca de riquezas e glória.\"",
            "3": "\"Não importa. Queria apenas pagar uma bebida para uma bela guerreira.\""
        }
        
        choice = self.get_party_vote(options, prompt="O que responder? ")
        
        if choice == "1":
            # Consequence of stealing:
            if self.state.get_flag("roubou_cabana"):
                typewriter("\nElena estreita os olhos e repara na sua bolsa.", 0.03)
                typewriter("\"Você fala em ajudar... mas esse brilho dourado na sua bolsa parece muito com a relíquia sagrada da nossa cabana de culto. Você roubou nosso patrimônio?\"", 0.03, None)
                
                sub_opt = {
                    "1": "\"Sim, achei que estaria mais segura comigo.\" (Honestidade arriscada)",
                    "2": "\"Não! Encontrei isso jogado na floresta.\" (Mentira)"
                }
                ans = self.get_party_vote(sub_opt, prompt="Sua resposta: ")
                
                if ans == "1":
                    typewriter("\nElena suspira, com raiva, mas impressionada com a honestidade.", 0.03)
                    typewriter("\"Pelo menos é sincero. Mas você devolverá isso à vila depois. Vou com você para garantir que faça a coisa certa.\"", 0.03, None)
                    self.recruit_companion("elena")
                else:
                    typewriter("\nElena se levanta e coloca a mão na adaga.", 0.03)
                    typewriter("\"Miro em mentirosos de longe. Saiam da minha frente antes que eu teste minha flecha em seus pescoços!\"", 0.03, None)
                    self.state.set_flag("elena_confronted", True)
                    self.state.set_flag("inimiga_elena", True)
            else:
                typewriter("\nElena sorri levemente e guarda o arco.", 0.03)
                typewriter("\"Ajudar Oakhaven? Raro ver alguém com espírito de herói hoje em dia. Muito bem, meu arco está a serviço de vocês. Vamos caçar essas sombras nas cavernas.\"", 0.03, None)
                self.recruit_companion("elena")
                
        elif choice == "2":
            typewriter("\n\"Glória só traz túmulos vazios. Prefiro trabalhar sozinha.\" - diz ela friamente.", 0.03, None)
            self.state.set_flag("elena_confronted", True)
            
        else:
            typewriter("\nEla dá a vocês um olhar de desprezo total.", 0.03)
            typewriter("\"Guardem seu ouro para pagar seus caixões nas cavernas, aventureiros.\" - e ignora vocês.", 0.03, None)
            self.state.set_flag("elena_confronted", True)
            
        press_any_key()

    # ================= CHAPTER 2 =================
    def chapter_2_start(self):
        try:
            from engine.campfire import run_campfire
            run_campfire(self, chapter_label="pre_ch2")
        except Exception:
            pass
        save_game(self.state, lambda msg: self.adapter.emit(NarrativeText("💾 [Auto-Salvar] Jogo salvo com sucesso.")))
        self.state.current_location = "caverna"
        self.state.current_chapter = 2
        if self.adapter:
            self.adapter.on_state_change(self.state)
        clear_screen()
        print_centered("=== CAPÍTULO II: AS CAVERNAS SUSSURRANTES ===", None)
        self.adapter.emit(AsciiArt(CAVES_ART))
        
        typewriter("A umidade do ar aumenta conforme vocês sobem a trilha da montanha do norte.", 0.03)
        typewriter("A entrada das cavernas parece a bocarra de um monstro escuro esculpido na rocha calcária.", 0.03)
        typewriter("Ecoando de dentro, sons estranhos e sussurros perturbam a mente de vocês.", 0.03)
        
        options = {
            "1": "Trilhar o Caminho da Esquerda (Cheio de estalagmites e sombrio)",
            "2": "Trilhar o Caminho da Direita (Ecoando barulho de asas)",
            "3": "Investigar uma fenda escura secreta entre as rochas"
        }
        
        choice = self.get_party_vote(options, prompt="Qual caminho o grupo escolhe? ")
        
        if choice == "1":
            self.chapter_2_left()
        elif choice == "2":
            self.chapter_2_right()
        else:
            self.chapter_2_dark_crevice()

    def chapter_2_left(self):
        clear_screen()
        typewriter("Vocês seguem pelo caminho estreito da esquerda.", 0.03)
        typewriter("O chão está coberto de poças de água e limo escorregadio. *Drip, drop...*", 0.03)
        typewriter("De repente, vocês ouvem um clique! Uma armadilha de estacas de ferro cai do teto!", 0.03)
        play_sound_effect("SWOOSH!", None)
        
        evasion_chance = 0.3 + (self.player.agilidade * 0.02)
        if random.random() < evasion_chance:
            typewriter("\nCom reflexos rápidos, vocês se jogam para trás, esquivando-se por centímetros!", 0.03, None)
        else:
            dmg = int(self.player.max_hp * 0.20)
            self.consume_resource(self.player, "hp", dmg, "Armadilha de estacas")
            
        typewriter("\nAo se recompor, você avista um baú de ferro trancado.", 0.03)
        # Lockpick check based on class
        if any(p.char_class == CharacterClass.LADINO for p in self.party):
            typewriter("Como Ladino, o grupo usa suas ferramentas e abre a tranca facilmente!", 0.03, None)
            item = create_item("adaga_assassina")
            self.player.inventory.append(item)
            self.adapter.emit(NarrativeText(f"Encontrou uma {item.get_colored_name()} no baú!"))
        else:
            typewriter("Vocês não têm ferramentas para abrir o baú e decide não arriscar quebrá-lo.", 0.03)
            
        press_any_key()
        self.chapter_2_deep()

    def chapter_2_right(self):
        clear_screen()
        typewriter("Vocês seguem pelo caminho da direita, onde a caverna é mais ampla.", 0.03)
        typewriter("De repente, um Morcego Gigante surge mergulhando do teto escuro para atacar o grupo!", 0.03)
        play_sound_effect("Screeech!", None)
        
        enemy = spawn_enemy("morcego_gigante")
        combat = CombatSystem(self.state, [enemy])
        if not combat.run():
            self.game_over()
            
        typewriter("\nVocês encontram os restos mortais de aventureiros anteriores.", 0.03)
        item = create_item("cota_malha")
        self.player.inventory.append(item)
        self.adapter.emit(NarrativeText(f"Vocês vasculham o corpo e encontram uma {item.get_colored_name()}"))
        
        press_any_key()
        self.chapter_2_deep()

    def chapter_2_dark_crevice(self):
        clear_screen()
        typewriter("Vocês espremem seus corpos por uma abertura estreita na parede rochosa.", 0.03)
        typewriter("Lá dentro, em uma pequena caverna isolada, vocês encontram um Goblin ferido.", 0.03)
        typewriter("A criatura está encolhida, segurando a perna quebrada e tremendo muito.", 0.03)
        typewriter("\"Humano... por favor... não machucar Dropp. Dropp só querer ir embora... Dói muito...\"", 0.03, None)
        
        # Check if player has potions in inventory
        potions = [i for i in self.player.inventory if i.name == "Poção de Vida Menor"]
        
        options = {}
        if potions:
            options["1"] = "Dar uma Poção de Vida Menor para curar o goblin"
        options["2"] = "Finalizar o goblin para roubar o que ele tem"
        options["3"] = "Ignorar o goblin e continuar investigando as cavernas"
        
        choice = self.get_party_vote(options, prompt="Qual a escolha da party? ")
        
        if choice == "1":
            # Spent potion
            potion_to_remove = potions[0]
            self.player.inventory.remove(potion_to_remove)
            self.consume_resource(self.player, "item", 1, "Poção de Vida Menor")
            self.state.set_flag("ajudou_goblin", True)
            
            typewriter("\nVocês entregam a poção de vida ao pequeno Goblin. Ele a bebe avidamente.", 0.03)
            typewriter("\"Ohhh! Dor sumindo... Goblin se sentir forte! Humano ser bom amigo de Dropp!\"", 0.03, None)
            typewriter("\"Pegue isso, amigo Humano. Chave brilhante abre baú grande de ouro lá na frente!\"", 0.03, None)
            self.state.set_flag("chave_caves", True)
            self.adapter.emit(NarrativeText(f"\nO grupo recebeu Chave Enferrujada!"))
            
        elif choice == "2":
            typewriter("\nVocês sacam suas armas. O goblin tenta se arrastar, mas é inútil.", 0.03)
            enemy = Enemy("Goblin Encurralado", 30, 6, 1, 15, 45, AIType.COWARD)
            combat = CombatSystem(self.state, [enemy], can_flee=False)
            if not combat.run():
                self.game_over()
            typewriter("\nVocês vasculham o corpo do goblin.", 0.03)
            
        else:
            typewriter("\nVocês viram as costas e deixam o goblin gemendo de dor no escuro.", 0.03)
            
        press_any_key()
        self.chapter_2_deep()

    def chapter_2_deep(self):
        clear_screen()
        print_centered("=== PROFUNDEZAS DAS CAVERNAS ===", None)
        typewriter("O ar está carregado de enxofre e um calor estranho sobe do chão.", 0.03)
        
        # Gold Chest room
        typewriter("Em uma alcova de pedra polida, vocês avistam um Baú de Ouro ornamental.", 0.03)
        
        if self.state.get_flag("chave_caves"):
            sub_opt = {
                "1": "Usar a Chave Enferrujada do Goblin para abrir",
                "2": "Ignorar"
            }
            dec = self.get_party_vote(sub_opt, prompt="O que a party decide? ")
            if dec == "1":
                clear_screen()
                typewriter("A chave gira com um *clique* perfeito!", 0.03)
                loot = create_item("lamina_runica") if not any(p.char_class == CharacterClass.MAGO for p in self.party) else create_item("cajado_arquimago")
                self.player.inventory.append(loot)
                self.adapter.emit(NarrativeText(f"\nRECOMPENSA ÉPICA! O grupo encontrou {loot.get_colored_name()}!"))
                typewriter(f"Descrição: {loot.description}", 0.03)
                press_any_key()
        else:
            typewriter("O baú está trancado por magia ou chave complexa. Vocês não conseguem abri-lo sem a chave apropriada.", 0.03)
            
        # Mandatory fight
        typewriter("\nDe repente, um gigantesco Verme das Rochas surge do solo rochoso à frente de vocês!", 0.03)
        play_sound_effect("RUUUMBLE!", None)
        
        verme = spawn_enemy("verme_rocha")
        combat = CombatSystem(self.state, [verme])
        if not combat.run():
            self.game_over()
            
        self.shadow_sanctum()

    def shadow_sanctum(self):
        clear_screen()
        print_centered("=== SANTUÁRIO DAS SOMBRAS ===", None)
        
        typewriter("Vocês chegam ao coração das cavernas. As paredes são esculpidas com altares dedicados a demônios antigos.", 0.03)
        typewriter("No centro da sala de ritual, um homem magro de capuz negro ergue as mãos.", 0.03)
        typewriter("\"Mais insetos no meu altar... Vocês chegaram tarde!\" - diz ele.", 0.03, None)
        
        press_any_key()
        
        # Shadow Inquisitor boss fight
        inquisitor = spawn_enemy("inquisidor_sombrio")
        
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
            
        # Use Custom Boss battle to execute phase 2 logic
        combat = CombatSystem(self.state, [inquisitor], can_flee=False)
        if not combat.run():
            self.game_over()
            
        clear_screen()
        print_centered("=== OS SEGREDOS DO RITUAL ===", None)
        typewriter("O corpo do Inquisidor das Sombras se dissolve em cinzas, deixando cair um pergaminho antigo de couro negro.", 0.03)
        typewriter("Esse é o 'Pergaminho de Sangue', que contém instruções de como usar a Relíquia para invocar o Caos primordial.", 0.03)
        
        options = {
            "1": "Queimar o Pergaminho de Sangue imediatamente (Evita corrupção)",
            "2": "Guardar o Pergaminho de Sangue com você (Poder sombrio oculto)"
        }
        
        choice = self.get_party_vote(options, prompt="O que a party decide? ")
        
        if choice == "1":
            self.state.set_flag("queimou_pergaminho", True)
            typewriter(f"\nVocês queimam o pergaminho nas chamas de um altar. Cinzas flutuam no ar.", 0.03)
        else:
            self.state.set_flag("guardou_pergaminho", True)
            typewriter(f"\nVocês guardam o Pergaminho de Sangue. Sentem as sombras sussurrarem em suas mentes...", 0.03)
            
        # Complete quest rewards for every party member (not only the leader)
        log_fn = lambda msg: self.adapter.emit(NarrativeText(msg))
        for p in self.party:
            q = p.quest_manager.quests.get("cavernas")
            if q and not q.is_completed:
                if not q.is_active:
                    q.is_active = True
                p.quest_manager.complete_quest("cavernas", p, log_fn)
        press_any_key()
            
        typewriter("\nCom as cavernas pacificadas, vocês decidem seguir viagem em direção à Vila de Millhaven.", 0.03)
        press_any_key()

    def act_ii_epilogue_hook(self):
        from engine.world_chapter_7 import clear_screen, typewriter, press_any_key, print_centered
        clear_screen()
        print_centered("=== ATO II: O DESPERTAR DO VAZIO ===", None)
        typewriter("\nO tempo passou, mas as consequências do que ocorreu no altar rúnico ecoam...", 0.03)
        
        if self.state.get_flag("guardou_pergaminho") and self.state.get_flag("lacre_sombrio"):
            # Senhor das Sombras
            typewriter("\nO poder de Malakar corre agora nas veias de vocês, mas com ele veio o peso de saber a verdade:", 0.03)
            typewriter("Vocês não herdaram um trono, herdaram uma guarda. Algo abaixo do trono sente a fraqueza de vocês e testa os limites do selo.", 0.03)
        elif not self.state.get_flag("elena_morta") and not self.state.get_flag("roubou_cabana"):
            # Herói da Luz
            typewriter("\nMeses depois de Oakhaven ser reconstruída, os templos voltam a acender suas chamas.", 0.03)
            typewriter("Mas em uma noite sem lua, um mensageiro chega maltrapilho de Vaelmoor:", 0.03)
            typewriter("\"Algo mais fundo do que Malakar está se mexendo. E ele sabia. Por isso queimou a própria alma.\"", 0.03)
        else:
            # Andarilho Solitário
            typewriter("\nVocês seguiram sozinhos, longe de Oakhaven, tentando esquecer. Mas os pesadelos não pararam...", 0.03)
            typewriter("E um deles trouxe consigo o nome de um porto que vocês nunca visitaram: Vaelmoor.", 0.03)
            
        press_any_key("Pressione [ENTER] para viajar para o Porto de Vaelmoor...")
        self.chapter_7_start()
