import time
from engine.constants import Colors, CharacterClass
from engine.console import clear_screen, draw_box, get_menu_choice, press_any_key, typewriter
from engine.art import TITLE_ART
from engine.player import Player
from engine.world import WorldManager

def main():
    clear_screen()
    print(TITLE_ART)
    
    typewriter("Bem-vindo ao reino de Aethelgard!", 0.03, Colors.BRIGHT_CYAN)
    print_divider_simple()
    
    # 1. Choose Name
    from engine.adapter import get_adapter
    name = get_adapter().get_input(f"\n{Colors.BOLD}Digite o nome do seu aventureiro (ou aperte Enter para 'Anthony'): {Colors.RESET}").strip()
    if not name:
        name = "Anthony"
        
    clear_screen()
    print(TITLE_ART)
    print(f"Olá, {Colors.BOLD}{name}{Colors.RESET}! Agora escolha a sua classe para iniciar a aventura.\n")
    
    # 2. Show Classes Details
    class_details = [
        f" {Colors.BRIGHT_RED}1. Guerreiro{Colors.RESET}: Especialista em combate físico. Alta vida e força.",
        f"    {Colors.BRIGHT_BLACK}- Atributos iniciais: Força 12, Agi 6, Vit 12, HP 120, MP 20{Colors.RESET}",
        f"    {Colors.BRIGHT_BLACK}- Habilidades: Golpe Poderoso, Muralha de Ferro, Golpe Devastador{Colors.RESET}\n",
        
        f" {Colors.BRIGHT_CYAN}2. Mago{Colors.RESET}: Mestre das artes arcanas. Altíssima mana e inteligência.",
        f"    {Colors.BRIGHT_BLACK}- Atributos iniciais: Força 4, Agi 7, Vit 8, HP 80, MP 60{Colors.RESET}",
        f"    {Colors.BRIGHT_BLACK}- Habilidades: Bola de Fogo, Escudo Arcano, Trovão Celestial{Colors.RESET}\n",
        
        f" {Colors.BRIGHT_GREEN}3. Ladino{Colors.RESET}: Silencioso e ágil. Alta esquiva e taxa de crítico.",
        f"    {Colors.BRIGHT_BLACK}- Atributos iniciais: Força 7, Agi 14, Vit 9, HP 90, MP 30{Colors.RESET}",
        f"    {Colors.BRIGHT_BLACK}- Habilidades: Ataque Furtivo, Passo de Sombras, Lâmina Venenosa{Colors.RESET}\n",
        
        f" {Colors.BRIGHT_YELLOW}4. Clérigo{Colors.RESET}: Servo divino. Dano mágico e curas de purificação.",
        f"    {Colors.BRIGHT_BLACK}- Atributos iniciais: Força 8, Agi 6, Vit 10, HP 100, MP 40{Colors.RESET}",
        f"    {Colors.BRIGHT_BLACK}- Habilidades: Luz Sagrada, Punição Divina, Bênção Protetora{Colors.RESET}\n",
        
        f" {Colors.BRIGHT_MAGENTA}5. Arqueiro{Colors.RESET}: Caçador de precisão. Ataques penetrantes.",
        f"    {Colors.BRIGHT_BLACK}- Atributos iniciais: Força 8, Agi 12, Vit 8, HP 85, MP 25{Colors.RESET}",
        f"    {Colors.BRIGHT_BLACK}- Habilidades: Flecha Perfurante, Chuva de Flechas, Tiro Preciso{Colors.RESET}"
    ]
    
    draw_box("Classes Disponíveis", class_details, Colors.YELLOW, width=78)
    
    class_choice = get_menu_choice(["Guerreiro", "Mago", "Ladino", "Clérigo", "Arqueiro"], prompt="Selecione sua classe: ")
    
    if class_choice == "1":
        selected_class = CharacterClass.GUERREIRO
    elif class_choice == "2":
        selected_class = CharacterClass.MAGO
    elif class_choice == "3":
        selected_class = CharacterClass.LADINO
    elif class_choice == "4":
        selected_class = CharacterClass.CLERIGO
    else:
        selected_class = CharacterClass.ARQUEIRO
        
    player = Player(name, selected_class)
    
    clear_screen()
    print(TITLE_ART)
    print_divider_simple()
    typewriter(f"Personagem {Colors.GREEN}{player.name}{Colors.RESET} ({player.char_class.value}) criado com sucesso!", 0.03)
    typewriter("Sua jornada começará em instantes...", 0.03)
    time.sleep(1.5)
    
    # 3. Start World Manager
    world = WorldManager(player)
    try:
        world.run_game()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}Jogo encerrado pelo jogador. Até a próxima!{Colors.RESET}")
    except Exception as e:
        print(f"\n\n{Colors.RED}Ocorreu um erro inesperado: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()

def print_divider_simple():
    print(f"{Colors.BRIGHT_BLACK}{'─' * 80}{Colors.RESET}")

if __name__ == "__main__":
    main()
